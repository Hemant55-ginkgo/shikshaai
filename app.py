import streamlit as st
import anthropic
import json

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
.output-section {
    background: #f0faf5; border: 1px solid #d1ead9;
    border-radius: 10px; padding: 1.2rem 1.4rem; margin-bottom: 1rem;
}
.sec-label {
    font-size: 11px; font-weight: 600; letter-spacing: 0.06em;
    text-transform: uppercase; color: #888; margin-bottom: 6px;
}
.badge {
    display: inline-block; background: #1a6b4a; color: white;
    font-size: 11px; padding: 3px 10px; border-radius: 20px;
    font-weight: 500; margin-bottom: 1rem;
}
.cost-note {
    font-size: 11px; color: #bbb; text-align: right; margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)

SYSTEM_PROMPT = """You are a CBSE curriculum expert. Output ONLY valid JSON, no markdown, no backticks, no preamble. Keep total word count under 300 words across all values.
Return this exact structure:
{"topic":"","grade":"","subject":"","ncert_ref":"","nep_competency":"","duration_min":0,"class_size":0,"learning_objectives":["","",""],"warm_up_activity":"","main_activity":"","assessment_question":"","homework":""}"""

def generate_plan(grade, subject, topic, duration, strength):
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    user_msg = f"Grade {grade} {subject} | Topic: {topic} | Duration: {duration} min | Class size: {strength} students | Blackboard only, no projector | Use Indian names in examples"
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=700,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}]
    )
    raw = message.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    plan = json.loads(raw)
    usage = message.usage
    return plan, usage.input_tokens, usage.output_tokens

def plan_to_text(p):
    lines = [
        f"LESSON PLAN — {p.get('topic','')}",
        f"{p.get('ncert_ref','')} | Grade {p.get('grade','')} | {p.get('subject','')} | {p.get('duration_min','')} min | {p.get('class_size','')} students",
        f"NEP Competency: {p.get('nep_competency','')}",
        "",
        "LEARNING OBJECTIVES:",
        *[f"{i+1}. {o}" for i, o in enumerate(p.get('learning_objectives', []))],
        "",
        "WARM-UP (5 min):",
        p.get('warm_up_activity', ''),
        "",
        "MAIN ACTIVITY:",
        p.get('main_activity', ''),
        "",
        "ASSESSMENT:",
        p.get('assessment_question', ''),
        "",
        "HOMEWORK:",
        p.get('homework', '')
    ]
    return "\n".join(lines)

# --- UI ---
st.markdown("## 📚 ShikshaAI")
st.markdown("**CBSE Lesson Plan Generator** · NCERT-aligned · NEP 2020 · Indian classroom defaults")
st.divider()

col1, col2 = st.columns(2)
with col1:
    grade = st.selectbox("Grade", ["6", "7", "8"], index=1)
with col2:
    subject = st.selectbox("Subject", ["Science", "Mathematics", "Social Science", "English", "Hindi"])

topic = st.text_input("Chapter / Topic", placeholder="e.g. Nutrition in Plants, Fractions, The Mughal Empire", value="Nutrition in Plants")

col3, col4 = st.columns(2)
with col3:
    duration = st.selectbox("Period duration", ["35 minutes", "40 minutes", "45 minutes"], index=1)
with col4:
    strength = st.selectbox("Class strength", ["~35 students", "~45 students", "~55 students"], index=1)

duration_min = duration.split()[0]
strength_num = strength.replace("~","").split()[0]

st.markdown("")
generate = st.button("Generate lesson plan")

if generate:
    if not topic.strip():
        st.error("Please enter a topic.")
    else:
        with st.spinner("Writing your lesson plan..."):
            try:
                plan, in_t, out_t = generate_plan(grade, subject, topic.strip(), duration_min, strength_num)
                cost = (in_t * 0.0000008) + (out_t * 0.000001)

                st.markdown(f"### {plan.get('topic',topic)} — Grade {plan.get('grade',grade)} {plan.get('subject',subject)}")
                st.markdown(f"`{plan.get('ncert_ref','')}` &nbsp; `{plan.get('nep_competency','')}` &nbsp; `{plan.get('duration_min','')} min` &nbsp; `{plan.get('class_size','')} students`", unsafe_allow_html=True)
                st.markdown('<span class="badge">CBSE ready</span>', unsafe_allow_html=True)

                objectives = plan.get('learning_objectives', [])
                st.markdown('<div class="sec-label">Learning objectives</div>', unsafe_allow_html=True)
                for obj in objectives:
                    st.markdown(f"- {obj}")

                sections = [
                    ("Warm-up activity (5 min)", plan.get('warm_up_activity','')),
                    ("Main activity", plan.get('main_activity','')),
                    ("Assessment question", plan.get('assessment_question','')),
                    ("Homework", plan.get('homework',''))
                ]
                for label, content in sections:
                    st.markdown(f'<div class="sec-label">{label}</div>', unsafe_allow_html=True)
                    st.markdown(content)
                    st.markdown("")

                plain = plan_to_text(plan)
                st.divider()
                col5, col6 = st.columns(2)
                with col5:
                    st.download_button("Download as .txt", plain, file_name=f"lesson_{topic[:20].replace(' ','_')}.txt", use_container_width=True)
                with col6:
                    wa_url = f"https://wa.me/?text={plain[:1000]}"
                    st.link_button("Share on WhatsApp", wa_url, use_container_width=True)

                st.markdown(f'<div class="cost-note">Tokens: {in_t} in + {out_t} out · Est. cost: ${cost:.5f}</div>', unsafe_allow_html=True)

                with st.expander("View raw JSON"):
                    st.json(plan)

            except json.JSONDecodeError as e:
                st.error(f"JSON parse error: {e}. Try generating again.")
            except Exception as e:
                st.error(f"Error: {e}")
