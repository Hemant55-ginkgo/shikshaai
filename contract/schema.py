# contract/schema.py
# STRUCTURE layer — LessonPlan dataclass + validation
# This is the single source of truth for output shape.
# The schema must not change when the model changes.
# Decision 1 — Freeze the Input → Prompt → Output contract

from dataclasses import dataclass, field
from typing import List


# ── Output contract ──────────────────────────────────────────────────────────

@dataclass
class LessonPlan:
    topic: str
    grade: str
    subject: str
    ncert_ref: str
    nep_competency: str
    duration_min: int
    class_size: int
    learning_objectives: List[str]
    warm_up_activity: str
    main_activity: str
    assessment_question: str
    homework: str


# ── Valid values ─────────────────────────────────────────────────────────────

VALID_GRADES = {"6", "7", "8"}

VALID_NEP_COMPETENCIES = {
    "Critical Thinking",
    "Experiential Learning",
    "Collaborative Learning",
    "Inquiry-Based Learning",
    "Creative Expression",
}


# ── Safe defaults (used by repair layer — Decision 5) ────────────────────────

SAFE_DEFAULTS = {
    "ncert_ref": "See NCERT textbook",
    "nep_competency": "Critical Thinking",
    "learning_objectives": [
        "Students will understand the core concept of the topic.",
        "Students will be able to apply key ideas with examples.",
        "Students will reflect on real-life connections.",
    ],
    "warm_up_activity": "Teacher asks students to recall prior knowledge with a brief question.",
    "main_activity": "Teacher explains the topic using blackboard examples and student discussion.",
    "assessment_question": "What is the most important thing you learned today?",
    "homework": "Read the relevant NCERT chapter section and answer the exercise questions.",
}


# ── Validation ───────────────────────────────────────────────────────────────

class ValidationError(Exception):
    pass


def validate(plan: LessonPlan) -> None:
    """
    Raises ValidationError if the plan violates any hard contract rule.
    Call after repair — this is the last gate before showing output to a teacher.
    """
    errors = []

    if not plan.topic or not plan.topic.strip():
        errors.append("topic is empty")

    if plan.grade not in VALID_GRADES:
        errors.append(f"grade '{plan.grade}' not in {VALID_GRADES}")

    if not plan.subject or not plan.subject.strip():
        errors.append("subject is empty")

    if plan.nep_competency not in VALID_NEP_COMPETENCIES:
        errors.append(f"nep_competency '{plan.nep_competency}' not valid")

    if not isinstance(plan.duration_min, int) or plan.duration_min <= 0:
        errors.append(f"duration_min must be positive int, got '{plan.duration_min}'")

    if not isinstance(plan.class_size, int) or plan.class_size <= 0:
        errors.append(f"class_size must be positive int, got '{plan.class_size}'")

    if not isinstance(plan.learning_objectives, list) or len(plan.learning_objectives) == 0:
        errors.append("learning_objectives must be a non-empty list")

    for key in ("warm_up_activity", "main_activity", "assessment_question", "homework"):
        if not getattr(plan, key, "").strip():
            errors.append(f"{key} is empty")

    if errors:
        raise ValidationError(f"LessonPlan validation failed: {'; '.join(errors)}")


# ── Deserialise from raw dict ────────────────────────────────────────────────

def from_dict(d: dict, fallback_grade: str = "", fallback_subject: str = "") -> LessonPlan:
    """
    Build a LessonPlan from a raw dict (model output).
    Coerces types. Does NOT fill defaults — that is the repair layer's job.
    Raises KeyError / TypeError if a required field is completely missing.
    """
    return LessonPlan(
        topic=str(d.get("topic", "")).strip(),
        grade=str(d.get("grade", fallback_grade)).strip(),
        subject=str(d.get("subject", fallback_subject)).strip(),
        ncert_ref=str(d.get("ncert_ref", "")).strip(),
        nep_competency=str(d.get("nep_competency", "")).strip(),
        duration_min=int(d.get("duration_min", 0)),
        class_size=int(d.get("class_size", 0)),
        learning_objectives=list(d.get("learning_objectives", [])),
        warm_up_activity=str(d.get("warm_up_activity", "")).strip(),
        main_activity=str(d.get("main_activity", "")).strip(),
        assessment_question=str(d.get("assessment_question", "")).strip(),
        homework=str(d.get("homework", "")).strip(),
    )


def to_dict(plan: LessonPlan) -> dict:
    """Serialise LessonPlan back to dict for Supabase logging."""
    return {
        "topic": plan.topic,
        "grade": plan.grade,
        "subject": plan.subject,
        "ncert_ref": plan.ncert_ref,
        "nep_competency": plan.nep_competency,
        "duration_min": plan.duration_min,
        "class_size": plan.class_size,
        "learning_objectives": plan.learning_objectives,
        "warm_up_activity": plan.warm_up_activity,
        "main_activity": plan.main_activity,
        "assessment_question": plan.assessment_question,
        "homework": plan.homework,
    }
