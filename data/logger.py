# data/logger.py
# MEMORY layer — Supabase write functions
# Decision 4 — Log everything to Supabase
# Decision 8 — Capture edits passively
#
# Two tables:
#   sessions  — one row per generation attempt
#   feedback  — one row per field edit or thumbs up/down
#
# Do NOT import anthropic here. Do NOT import st here.
# supabase_client is passed in — never fetched inside this file.

import json
from datetime import datetime, timezone
from typing import Optional

from contract.schema import LessonPlan, to_dict
from contract.prompts import PROMPT_VERSION
from llm_service.base import LLMUsage


# ── Edit type inference (Decision 8) ─────────────────────────────────────────

def infer_edit_type(original: str, edited: str) -> str:
    """
    Classifies the kind of edit a teacher made to a generated field.
    Used to label rows in the feedback table for fine-tuning analysis.

    delete   — teacher cleared the field entirely
    addition — field was empty, teacher added content
    append   — edited text is >50% longer (teacher expanded)
    truncate — edited text is <50% as long (teacher cut down)
    minor_fix — edited text is a substring of original (small correction)
    rewrite  — everything else (most valuable fine-tuning signal)
    """
    if not edited:
        return "delete"
    if not original:
        return "addition"
    ratio = len(edited) / len(original)
    if ratio > 1.5:
        return "append"
    if ratio < 0.5:
        return "truncate"
    if edited in original:
        return "minor_fix"
    return "rewrite"


# ── Sessions table ────────────────────────────────────────────────────────────

def log_session(
    supabase_client,
    *,
    grade: str,
    subject: str,
    topic: str,
    duration_min: int,
    class_size: int,
    chapter_index: Optional[int],
    model_id: str,
    usage: LLMUsage,
    prompt_sent: str,
    raw_model_output: str,
    parsed_successfully: bool,
    plan: Optional[LessonPlan],
    error_message: Optional[str] = None,
) -> Optional[str]:
    """
    Writes one row to the sessions table.
    Returns the session id (UUID string) on success, None on failure.
    Never raises — a logging failure must not crash the teacher's session.

    Schema:
        id, created_at, grade, subject, topic,
        duration_min, class_size, chapter_index,
        model_id, prompt_version,
        input_tokens, output_tokens, cache_tokens,
        prompt_sent, raw_model_output,
        parsed_successfully, lesson_plan_json,
        error_message
    """
    try:
        row = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "grade": grade,
            "subject": subject,
            "topic": topic,
            "duration_min": duration_min,
            "class_size": class_size,
            "chapter_index": chapter_index,
            "model_id": model_id,
            "prompt_version": PROMPT_VERSION,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cache_tokens": usage.cache_read_tokens,
            "prompt_sent": prompt_sent,
            "raw_model_output": raw_model_output,
            "parsed_successfully": parsed_successfully,
            "lesson_plan_json": json.dumps(to_dict(plan)) if plan else None,
            "error_message": error_message,
        }

        result = supabase_client.table("sessions").insert(row).execute()

        # supabase-py v2 returns data as a list of inserted rows
        if result.data:
            return result.data[0].get("id")
        return None

    except Exception as e:
        # Log to console for developer visibility — never raise to caller
        print(f"[logger] log_session failed: {e}")
        return None


# ── Feedback table ────────────────────────────────────────────────────────────

def log_feedback_rating(
    supabase_client,
    *,
    session_id: str,
    rating: int,                    # 1 = thumbs up, 0 = thumbs down
    feedback_note: Optional[str] = None,
) -> None:
    """
    Writes a thumbs up/down rating row to the feedback table.
    field_edited, original_value, edited_value are null for rating-only rows.
    Never raises.
    """
    try:
        row = {
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "rating": rating,
            "field_edited": None,
            "original_value": None,
            "edited_value": None,
            "edit_type": None,
            "time_to_edit_seconds": None,
            "feedback_note": feedback_note,
        }
        supabase_client.table("feedback").insert(row).execute()

    except Exception as e:
        print(f"[logger] log_feedback_rating failed: {e}")


def log_feedback_edit(
    supabase_client,
    *,
    session_id: str,
    field_edited: str,              # e.g. "warm_up_activity"
    original_value: str,
    edited_value: str,
    time_to_edit_seconds: Optional[float] = None,
    feedback_note: Optional[str] = None,
) -> None:
    """
    Writes one field-edit row to the feedback table.
    Called automatically when a teacher edits any output section (Decision 8).
    edit_type is inferred — teacher never sees or sets it.
    Never raises.
    """
    try:
        edit_type = infer_edit_type(original_value, edited_value)

        row = {
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "rating": None,
            "field_edited": field_edited,
            "original_value": original_value,
            "edited_value": edited_value,
            "edit_type": edit_type,
            "time_to_edit_seconds": time_to_edit_seconds,
            "feedback_note": feedback_note,
        }
        supabase_client.table("feedback").insert(row).execute()

    except Exception as e:
        print(f"[logger] log_feedback_edit failed: {e}")


# ── Supabase client factory ───────────────────────────────────────────────────

def get_supabase_client(url: str, key: str):
    """
    Constructs and returns a Supabase client.
    url and key come from st.secrets in app.py — never hardcoded here.

    Requires: supabase-py  (pip install supabase)
    """
    try:
        from supabase import create_client
        return create_client(url, key)
    except ImportError:
        raise ImportError(
            "supabase-py is not installed. "
            "Add 'supabase' to requirements.txt and run pip install supabase."
        )
