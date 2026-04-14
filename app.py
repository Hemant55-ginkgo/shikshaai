# app.py
# UI layer — owns nothing, imports everything
# Decision 7 — Brain / Memory / Structure separation
#
# This file is allowed to import:
#   st, st.secrets
#   data.curriculum, data.logger
#   contract.schema, contract.prompts
#   llm_service.factory, llm_service.validator
#
# This file must NEVER import: anthropic, supabase directly

import time
import streamlit as st

from data.curriculum import CURRICULUM, LANGUAGE_SUBJECTS
from data.logger import (
    get_supabase_client,
    log_session,
    log_feedback_rating,
    log_feedback_edit,
)
from contract.schema import LessonPlan, to_dict
from contract.prompts import build_user_message, get_system_prompt
from llm_service.base import LLMUsage
from llm_service.factory import get_primary_brain, get_escalation_brain
from llm_service.validator import generate_with_recovery, GenerationError

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ShikshaAI — Lesson Plan Generator",
    page_icon="📚",
    layout="centered"
)

st.markdown("""
<style>
.block-container { max-width: 720px; padding-top: 2rem; }
.stButton > button {
    width: 100%; background: #1a6b4a; color: white;
    border: none; border-radius: 8px; padding: 0.6rem;
    font-size: 1rem; font-weight: 600;
}
.stButton > button:hover { background: #155c3e; border: none; }
.sec-label {
    font-size: 11px; font-weight: 600; letter-spacing: 0.06em;
    text-transform: uppercase; color: #888; margin-bottom: 4px;
}
.badge {
    display: inline-block; background: #1a6b4a; color: white;
    font-size: 11px; padding: 3px 10px; border-radius: 20px;
    font-weight: 500; margin-bottom: 1rem;
}
.cost-note { font-size: 11px; color: #bbb; text-align: right; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)


# ── Clients (constructed once per session) ────────────────────────────────────

@st.cache_resource
def get_clients():
    api_key = st.secrets["ANTHROPIC_API_KEY"]
    primary = get_primary_brain(api_key)
    escalation = get_escalation_brain(api_key)

    try:
        supabase = get_supabase_client(
            url=st.secrets["SUPABASE_URL"],
            key=st.secrets["SUPABASE_KEY"],
        )
    except Exception:
        supabase = None

    return primary, escalation, supabase


# ── Helpers ───────────────────────────────────────────────────────────────────

def plan_to_text(p: LessonPlan) -> str:
    return "\n".join([
        f"LESSON PLAN — {p.topic}",
        f"{p.ncert_ref} | Grade {p.grade} | {p.subject} | {p.duration_min} min | {p.class_size} students",
        f"NEP Competency: {p.nep_competency}", "",
        "LEARNING OBJECTIVES:",
        *[f"{i+1}. {o}" for i, o in enumerate(p.learning_objectives)], "",
        "WARM-UP (5 min):", p.warm_up_activity, "",
        "MAIN ACTIVITY:", p.main_activity, "",
        "ASSESSMENT:", p.assessment_question, "",
        "HOMEWORK:", p.homework,
    ])


def get_chapter_index(topic: str, chapters: list, subject: str):
    if subject in LANGUAGE_SUBJECTS or not chapters:
        return None
    try:
        return chapters.index(topic) + 1
    except ValueError:
        return None


# ── Initialise session state ──────────────────────────────────────────────────
# These persist across Streamlit reruns so the plan survives field edits.

if "current_plan" not in st.session_state:
    st.session_state.current_plan = None
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "current_usage" not in st.session_state:
    st.session_state.current_usage = None
if "current_model_id" not in st.session_state:
    st.session_state.current_model_id = None
if "original_field_values" not in st.session_state:
    st.session_state.original_field_values = {}


# ── UI — inputs ───────────────────────────────────────────────────────────────

st.markdown("## 📚 ShikshaAI")
st.markdown("**CBSE Lesson Plan Generator** · NCERT-aligned · NEP 2020 · Indian classroom defaults")
st.divider()

col1, col2 = st.columns(2)
with col1:
    grade = st.selectbox("Grade", ["6", "7", "8"], index=1)
with col2:
    subject = st.selectbox("Subject", list(CURRICULUM.keys()))

chapters = CURRICULUM.get(subject, {}).get(grade, [])
is_language = subject in LANGUAGE_SUBJECTS

if chapters:
    topic_label = "Topic / Skill area" if is_language else "Chapter"
    help_text = None if is_language else f"{len(chapters)} NCERT chapters for Grade {grade} {subject}"
    topic = st.selectbox(topic_label, chapters, help=help_text)
    custom = st.text_input(
        "Or type a custom topic (overrides selection above)",
        placeholder="Leave blank to use selection above"
    )
    if custom.strip():
        topic = custom.strip()
else:
    topic = st.text_input("Chapter / Topic", placeholder="Enter topic name")

col3, col4 = st.columns(2)
with col3:
    duration = st.selectbox("Period duration", ["35 minutes", "40 minutes", "45 minutes"], index=1)
with col4:
    strength = st.selectbox("Class strength", ["~35 students", "~45 students", "~55 students"], index=1)

duration_min = duration.split()[0]
class_size = strength.replace("~", "").split()[0]

st.markdown("")
go = st.button("Generate lesson plan")

# ── Generation ────────────────────────────────────────────────────────────────

if go:
    if not topic:
        st.error("Please select or enter a topic.")
    else:
        primary, escalation, supabase = get_clients()

        prompt_sent = build_user_message(
            grade=grade,
            subject=subject,
            topic=topic,
            duration_min=duration_min,
            class_size=class_size,
            chapters=chapters,
        )

        with st.spinner("Writing your lesson plan..."):
            plan = None
            usage = None
            model_id_used = None
            error_message = None

            try:
                plan, usage, model_id_used = generate_with_recovery(
                    primary_brain=primary,
                    escalation_brain=escalation,
                    grade=grade,
                    subject=subject,
                    topic=topic,
                    duration_min=duration_min,
                    class_size=class_size,
                    chapters=chapters,
                )

            except GenerationError as e:
                error_message = str(e)
                st.error(error_message)

            except Exception as e:
                error_message = f"Unexpected error: {e}"
                st.error("Something went wrong. Please try again.")

        # ── Log session ───────────────────────────────────────────────────────
        session_id = None
        if supabase:
            session_id = log_session(
                supabase,
                grade=grade,
                subject=subject,
                topic=topic,
                duration_min=int(duration_min),
                class_size=int(class_size),
                chapter_index=get_chapter_index(topic, chapters, subject),
                model_id=model_id_used or "unknown",
                usage=usage or LLMUsage(0, 0),
                prompt_sent=prompt_sent,
                raw_model_output="",
                parsed_successfully=plan is not None,
                plan=plan,
                error_message=error_message,
            )

        # ── Persist to session_state so plan survives reruns ──────────────────
        if plan:
            st.session_state.current_plan = plan
            st.session_state.current_session_id = session_id
            st.session_state.current_usage = usage
            st.session_state.current_model_id = model_id_used

            # Store original field values for edit detection on rerun
            st.session_state.original_field_values = {
                "learning_objectives": "\n".join(plan.learning_objectives),
                "warm_up_activity": plan.warm_up_activity,
                "main_activity": plan.main_activity,
                "assessment_question": plan.assessment_question,
                "homework": plan.homework,
            }


# ── Render output ─────────────────────────────────────────────────────────────
# Runs on every rerun — not just when button is clicked.
# This keeps the plan visible while the teacher edits fields.

if st.session_state.current_plan:
    plan          = st.session_state.current_plan
    session_id    = st.session_state.current_session_id
    usage         = st.session_state.current_usage
    model_id_used = st.session_state.current_model_id
    originals     = st.session_state.original_field_values

    _, _, supabase = get_clients()

    st.markdown(f"### {plan.topic}")
    meta_parts = [
        plan.ncert_ref,
        f"Grade {plan.grade} {plan.subject}",
        f"{plan.duration_min} min",
        f"{plan.class_size} students",
        plan.nep_competency,
    ]
    st.caption(" · ".join(p for p in meta_parts if p))
    st.markdown('<span class="badge">CBSE ready</span>', unsafe_allow_html=True)

    # ── Editable fields ───────────────────────────────────────────────────────

    st.markdown('<div class="sec-label">Learning objectives</div>', unsafe_allow_html=True)
    edited_objectives = st.text_area(
        "learning_objectives",
        value=originals["learning_objectives"],
        height=100,
        label_visibility="collapsed",
        key="edit_objectives",
    )

    editable_fields = [
        ("Warm-up activity (5 min)", "warm_up_activity",   plan.warm_up_activity,    80),
        ("Main activity",            "main_activity",       plan.main_activity,       120),
        ("Assessment question",      "assessment_question", plan.assessment_question, 68),
        ("Homework",                 "homework",            plan.homework,            68),
    ]

    for label, key, _, height in editable_fields:
        st.markdown(f'<div class="sec-label">{label}</div>', unsafe_allow_html=True)
        st.text_area(
            key,
            value=originals[key],
            height=height,
            label_visibility="collapsed",
            key=f"edit_{key}",
        )
        st.markdown("")

    # ── Log edits silently ────────────────────────────────────────────────────
    # Compares current widget values against originals on every rerun.
    # A changed field writes one feedback row to Supabase.

    if supabase and session_id:
        if edited_objectives != originals["learning_objectives"]:
            log_feedback_edit(
                supabase,
                session_id=session_id,
                field_edited="learning_objectives",
                original_value=originals["learning_objectives"],
                edited_value=edited_objectives,
            )

        for _, key, _, _ in editable_fields:
            current_value  = st.session_state.get(f"edit_{key}", "")
            original_value = originals.get(key, "")
            if current_value != original_value:
                log_feedback_edit(
                    supabase,
                    session_id=session_id,
                    field_edited=key,
                    original_value=original_value,
                    edited_value=current_value,
                )

    # ── Rating buttons ────────────────────────────────────────────────────────
    st.divider()
    r1, r2 = st.columns(2)
    with r1:
        if st.button("👍  Looks good", use_container_width=True):
            if supabase and session_id:
                log_feedback_rating(supabase, session_id=session_id, rating=1)
            st.success("Thanks! Feedback saved.")
    with r2:
        if st.button("👎  Needs work", use_container_width=True):
            if supabase and session_id:
                log_feedback_rating(supabase, session_id=session_id, rating=0)
            st.warning("Got it. We'll use this to improve.")

    # ── Download + share ──────────────────────────────────────────────────────
    plain = plan_to_text(plan)
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "Download as .txt", plain,
            file_name=f"lesson_{plan.topic[:20].replace(' ', '_')}.txt",
            use_container_width=True,
        )
    with c2:
        st.link_button(
            "Share on WhatsApp",
            f"https://wa.me/?text={plain[:1000]}",
            use_container_width=True,
        )

    # ── Cost note ─────────────────────────────────────────────────────────────
    if usage:
        cache_note = f" · {usage.cache_read_tokens} cached" if usage.cache_read_tokens else ""
        st.markdown(
            f'<div class="cost-note">'
            f'Tokens: {usage.input_tokens} in + {usage.output_tokens} out{cache_note} · '
            f'Est. cost: ${usage.estimated_cost_usd:.5f} · '
            f'Model: {model_id_used}'
            f'</div>',
            unsafe_allow_html=True,
        )

    with st.expander("View raw JSON"):
        st.json(to_dict(plan))
