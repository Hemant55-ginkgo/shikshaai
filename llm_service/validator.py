# llm_service/validator.py
# BRAIN layer — repair → retry → escalate → fail clean
# Decision 5 — Strict output validation + recovery
#
# Recovery hierarchy (in order, cheapest first):
#   1. REPAIR    — strip markdown, coerce types, fill safe defaults (free, no API call)
#   2. RETRY     — same model, stricter prompt, max 2 attempts
#   3. ESCALATE  — Claude Sonnet, single attempt, silent
#   4. FAIL CLEAN — log full error, raise clean exception, never a raw stack trace
#
# This file owns the full generation lifecycle.
# app.py calls generate_with_recovery() and gets back (LessonPlan, LLMUsage, str)
# or a clean GenerationError it can display safely to a teacher.

import json
import re
from typing import Tuple

from contract.schema import (
    LessonPlan,
    ValidationError,
    SAFE_DEFAULTS,
    VALID_NEP_COMPETENCIES,
    from_dict,
    validate,
)
from contract.prompts import (
    PROMPT_VERSION,
    get_system_prompt,
    build_user_message,
)
from llm_service.base import BaseLLM, LLMUsage, LLMResponse


# ── Clean exception shown to teachers ────────────────────────────────────────

class GenerationError(Exception):
    """
    Raised when all recovery attempts are exhausted.
    Message is safe to display in the UI — no raw stack traces.
    Caller should log the full context to Supabase before surfacing this.
    """
    pass


# ── Step 1: REPAIR ───────────────────────────────────────────────────────────

def _extract_json(raw: str) -> str:
    """Pull the first {...} block out of raw text, stripping markdown fences."""
    raw = raw.replace("```json", "").replace("```", "").strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        return match.group(0)
    return raw


def _repair(d: dict, grade: str, subject: str, topic: str) -> dict:
    """
    Fill missing or invalid fields with safe defaults.
    Coerces types where possible. Never calls the API.
    """
    # Scalar string fields
    if not d.get("topic", "").strip():
        d["topic"] = topic
    if not d.get("grade", "").strip():
        d["grade"] = grade
    if not d.get("subject", "").strip():
        d["subject"] = subject
    if not d.get("ncert_ref", "").strip():
        d["ncert_ref"] = SAFE_DEFAULTS["ncert_ref"]

    # NEP competency — coerce to valid value or use default
    nep = str(d.get("nep_competency", "")).strip()
    if nep not in VALID_NEP_COMPETENCIES:
        d["nep_competency"] = SAFE_DEFAULTS["nep_competency"]

    # Numeric fields
    try:
        d["duration_min"] = int(d.get("duration_min", 0))
        if d["duration_min"] <= 0:
            raise ValueError
    except (ValueError, TypeError):
        d["duration_min"] = 40  # sensible default

    try:
        d["class_size"] = int(d.get("class_size", 0))
        if d["class_size"] <= 0:
            raise ValueError
    except (ValueError, TypeError):
        d["class_size"] = 40

    # Learning objectives — must be a list of 3 non-empty strings
    objs = d.get("learning_objectives", [])
    if not isinstance(objs, list):
        objs = []
    objs = [str(o).strip() for o in objs if str(o).strip()]
    while len(objs) < 3:
        objs.append(SAFE_DEFAULTS["learning_objectives"][len(objs)])
    d["learning_objectives"] = objs[:3]

    # Free-text fields
    for key in ("warm_up_activity", "main_activity", "assessment_question", "homework"):
        if not str(d.get(key, "")).strip():
            d[key] = SAFE_DEFAULTS[key]

    return d


def _parse_and_repair(
    raw: str,
    grade: str,
    subject: str,
    topic: str,
) -> Tuple[LessonPlan, bool]:
    """
    Attempt to parse raw model output into a LessonPlan.
    Returns (plan, repaired) where repaired=True means defaults were used.
    Raises ValueError if JSON cannot be extracted at all.
    """
    json_str = _extract_json(raw)
    try:
        d = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON parse failed: {e} | Extracted: {json_str[:200]}")

    repaired = False
    original = json.dumps(d)
    d = _repair(d, grade, subject, topic)
    if json.dumps(d) != original:
        repaired = True

    plan = from_dict(d, fallback_grade=grade, fallback_subject=subject)
    validate(plan)   # hard gate — raises ValidationError if still broken after repair
    return plan, repaired


# ── Full generation lifecycle ─────────────────────────────────────────────────

def generate_with_recovery(
    primary_brain: BaseLLM,
    escalation_brain: BaseLLM,
    grade: str,
    subject: str,
    topic: str,
    duration_min: str,
    class_size: str,
    chapters: list,
) -> Tuple[LessonPlan, LLMUsage, str]:
    """
    Full generation lifecycle with repair → retry → escalate → fail clean.

    Returns:
        (LessonPlan, LLMUsage, model_id_used)

    Raises:
        GenerationError — safe to display in UI, log context before surfacing.

    All intermediate failures should be logged by the caller (app.py / logger.py).
    """
    user_msg = build_user_message(
        grade=grade,
        subject=subject,
        topic=topic,
        duration_min=duration_min,
        class_size=class_size,
        chapters=chapters,
    )

    errors = []

    # ── Attempt 1 & 2: primary brain, standard then retry prompt ────────────
    for attempt in range(2):
        retry = attempt > 0
        system_prompt = get_system_prompt(tier=primary_brain.prompt_tier, retry=retry)

        try:
            response: LLMResponse = primary_brain.generate(
                system_prompt=system_prompt,
                user_message=user_msg,
            )
            plan, _ = _parse_and_repair(response.raw_text, grade, subject, topic)
            return plan, response.usage, response.model_id

        except (ValueError, ValidationError) as e:
            errors.append(f"Primary attempt {attempt + 1}: {e}")
            continue

        except Exception as e:
            # Network / auth error — no point retrying same model
            errors.append(f"Primary attempt {attempt + 1} network error: {e}")
            break

    # ── Attempt 3: escalate to Sonnet, single try ───────────────────────────
    system_prompt = get_system_prompt(tier=escalation_brain.prompt_tier, retry=True)

    try:
        response: LLMResponse = escalation_brain.generate(
            system_prompt=system_prompt,
            user_message=user_msg,
        )
        plan, _ = _parse_and_repair(response.raw_text, grade, subject, topic)
        return plan, response.usage, response.model_id

    except (ValueError, ValidationError) as e:
        errors.append(f"Escalation attempt: {e}")

    except Exception as e:
        errors.append(f"Escalation network error: {e}")

    # ── Attempt 4: FAIL CLEAN ────────────────────────────────────────────────
    raise GenerationError(
        "We could not generate a lesson plan right now. "
        "Please try again in a moment. "
        f"(Debug — {len(errors)} attempts failed: {errors[-1]})"
    )
