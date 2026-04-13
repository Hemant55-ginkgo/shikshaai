# contract/prompts.py
# STRUCTURE layer — versioned prompt templates
# Decision 9 — Downward compatible prompts
#
# Rules:
# 1. Positive instructions only ("Start response with {" not "Do not add markdown")
# 2. Typed schema with examples — show the model a good value, not an empty string
# 3. Prompt variants by model tier: standard (Haiku/Sonnet), compact (local/LLaMA)
# 4. Version every prompt — logged with every session in Supabase
#
# Do NOT import anthropic here. Do NOT import st here.

PROMPT_VERSION = "v1.0"

# ── System prompts by tier ───────────────────────────────────────────────────
#
# "standard" — used by Claude Haiku (primary) and Claude Sonnet (escalation)
# "compact"  — shorter, used by local/LLaMA when MODEL_BACKEND = "local"
#
# Both must produce output parseable by contract/schema.py → from_dict()

SYSTEM_PROMPTS = {

    "standard": (
        "CBSE lesson plan generator for Indian K-12 teachers.\n"
        "Start your response with { and end with }. Output ONLY valid JSON. "
        "No markdown, no backticks, no explanation outside the JSON.\n"
        "\n"
        "Required JSON schema with example values:\n"
        "{\n"
        '  "topic": "Fractions",\n'
        '  "grade": "6",\n'
        '  "subject": "Mathematics",\n'
        '  "ncert_ref": "Ch.7 Fractions",\n'
        '  "nep_competency": "Critical Thinking",\n'
        '  "duration_min": 40,\n'
        '  "class_size": 45,\n'
        '  "learning_objectives": [\n'
        '    "Students will define a fraction and identify numerator and denominator.",\n'
        '    "Students will compare fractions using the number line.",\n'
        '    "Students will solve two real-life problems involving fractions."\n'
        '  ],\n'
        '  "warm_up_activity": "Teacher draws a chapati on the board, divides it into 4 equal parts, asks: Priya ate 1 part — what fraction did she eat?",\n'
        '  "main_activity": "Teacher explains numerator and denominator using blackboard diagrams. Students solve 3 problems in pairs. Arjun presents one solution to the class.",\n'
        '  "assessment_question": "If Raju has 3/8 of a pizza and Priya has 5/8, who has more and by how much?",\n'
        '  "homework": "NCERT Exercise 7.1 — questions 1 to 4."\n'
        "}\n"
        "\n"
        "Rules: blackboard only (no projector/laptop), Indian names (Priya/Arjun/Raju), "
        "total JSON under 280 words, "
        "nep_competency must be one of: "
        "Critical Thinking | Experiential Learning | Collaborative Learning | "
        "Inquiry-Based Learning | Creative Expression, "
        "ncert_ref = chapter number + chapter name."
    ),

    "compact": (
        "CBSE lesson plan generator. "
        "Start response with {. Output ONLY valid JSON, no markdown.\n"
        "Schema: {\"topic\":\"\",\"grade\":\"\",\"subject\":\"\",\"ncert_ref\":\"\","
        "\"nep_competency\":\"\",\"duration_min\":0,\"class_size\":0,"
        "\"learning_objectives\":[\"\",\"\",\"\"],\"warm_up_activity\":\"\","
        "\"main_activity\":\"\",\"assessment_question\":\"\",\"homework\":\"\"}\n"
        "Rules: blackboard only, Indian names, under 200 words, "
        "nep_competency: Critical Thinking|Experiential Learning|"
        "Collaborative Learning|Inquiry-Based Learning|Creative Expression."
    ),

}


# ── Retry system prompt (Decision 5 — stricter on second attempt) ────────────

RETRY_SUFFIX = (
    " IMPORTANT: Your previous response could not be parsed as valid JSON. "
    "Start your response with { and end with }. "
    "Every key in the schema must be present. "
    "learning_objectives must be a JSON array of exactly 3 strings."
)

SYSTEM_PROMPTS_RETRY = {
    tier: prompt + RETRY_SUFFIX
    for tier, prompt in SYSTEM_PROMPTS.items()
}


# ── User message builder ─────────────────────────────────────────────────────

def build_user_message(
    grade: str,
    subject: str,
    topic: str,
    duration_min: str,
    class_size: str,
    chapters: list,
) -> str:
    """
    Builds the user-turn message injecting only the relevant curriculum slice.
    Keeps the prompt small — the system prompt is cached, user message is not.
    """
    chap_hint = ""
    from data.curriculum import LANGUAGE_SUBJECTS
    if chapters and subject not in LANGUAGE_SUBJECTS:
        try:
            idx = chapters.index(topic) + 1
            chap_hint = f" | NCERT Ch.{idx}"
        except ValueError:
            chap_hint = ""

    return (
        f"Grade {grade} {subject} | Topic: {topic}{chap_hint} | "
        f"{duration_min} min | {class_size} students"
    )


def get_system_prompt(tier: str, retry: bool = False) -> str:
    """
    Returns the system prompt string for a given tier.
    tier: "standard" | "compact"
    retry: True returns the stricter retry variant
    """
    prompts = SYSTEM_PROMPTS_RETRY if retry else SYSTEM_PROMPTS
    if tier not in prompts:
        raise ValueError(f"Unknown prompt tier '{tier}'. Valid: {list(prompts.keys())}")
    return prompts[tier]
