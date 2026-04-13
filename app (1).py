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

# ── Curriculum map (zero API tokens — lives in app memory) ──────────────────
CURRICULUM = {
    "Science": {
        "6": [
            "Food: Where Does It Come From?",
            "Components of Food",
            "Fibre to Fabric",
            "Sorting Materials into Groups",
            "Separation of Substances",
            "Changes Around Us",
            "Getting to Know Plants",
            "Body Movements",
            "The Living Organisms and Their Surroundings",
            "Motion and Measurement of Distances",
            "Light, Shadows and Reflections",
            "Electricity and Circuits",
            "Fun with Magnets",
            "Water",
            "Air Around Us",
            "Garbage In, Garbage Out",
        ],
        "7": [
            "Nutrition in Plants",
            "Nutrition in Animals",
            "Fibre to Fabric",
            "Heat",
            "Acids, Bases and Salts",
            "Physical and Chemical Changes",
            "Weather, Climate and Adaptations",
            "Winds, Storms and Cyclones",
            "Soil",
            "Respiration in Organisms",
            "Transportation in Animals and Plants",
            "Reproduction in Plants",
            "Motion and Time",
            "Electric Current and Its Effects",
            "Light",
            "Water: A Precious Resource",
            "Forests: Our Lifeline",
            "Wastewater Story",
        ],
        "8": [
            "Crop Production and Management",
            "Microorganisms: Friend and Foe",
            "Synthetic Fibres and Plastics",
            "Materials: Metals and Non-Metals",
            "Coal and Petroleum",
            "Combustion and Flame",
            "Conservation of Plants and Animals",
            "Cell — Structure and Functions",
            "Reproduction in Animals",
            "Reaching the Age of Adolescence",
            "Force and Pressure",
            "Friction",
            "Sound",
            "Chemical Effects of Electric Current",
            "Some Natural Phenomena",
            "Light",
            "Stars and the Solar System",
            "Pollution of Air and Water",
        ],
    },
    "Mathematics": {
        "6": [
            "Knowing Our Numbers",
            "Whole Numbers",
            "Playing with Numbers",
            "Basic Geometrical Ideas",
            "Understanding Elementary Shapes",
            "Integers",
            "Fractions",
            "Decimals",
            "Data Handling",
            "Mensuration",
            "Algebra",
            "Ratio and Proportion",
            "Symmetry",
            "Practical Geometry",
        ],
        "7": [
            "Integers",
            "Fractions and Decimals",
            "Data Handling",
            "Simple Equations",
            "Lines and Angles",
            "The Triangle and Its Properties",
            "Congruence of Triangles",
            "Comparing Quantities",
            "Rational Numbers",
            "Practical Geometry",
            "Perimeter and Area",
            "Algebraic Expressions",
            "Exponents and Powers",
            "Symmetry",
            "Visualising Solid Shapes",
        ],
        "8": [
            "Rational Numbers",
            "Linear Equations in One Variable",
            "Understanding Quadrilaterals",
            "Practical Geometry",
            "Data Handling",
            "Squares and Square Roots",
            "Cubes and Cube Roots",
            "Comparing Quantities",
            "Algebraic Expressions and Identities",
            "Visualising Solid Shapes",
            "Mensuration",
            "Exponents and Powers",
            "Direct and Inverse Proportions",
            "Factorisation",
            "Introduction to Graphs",
            "Playing with Numbers",
        ],
    },
    "Social Science": {
        "6": [
            "History: What, Where, How and When?",
            "On the Trail of the Earliest People",
            "From Gathering to Growing Food",
            "In the Earliest Cities",
            "What Books and Burials Tell Us",
            "Kingdoms, Kings and an Early Republic",
            "New Questions and Ideas",
            "Ashoka, The Emperor Who Gave Up War",
            "Vital Villages, Thriving Towns",
            "Traders, Kings and Pilgrims",
            "New Empires and Kingdoms",
            "Buildings, Paintings and Books",
            "Geography: The Earth in the Solar System",
            "Globe: Latitudes and Longitudes",
            "Motions of the Earth",
            "Maps",
            "Major Domains of the Earth",
            "Major Landforms of the Earth",
            "Our Country — India",
            "India: Climate, Vegetation and Wildlife",
            "Civics: Understanding Diversity",
            "Diversity and Discrimination",
            "What is Government?",
            "Key Elements of a Democratic Government",
            "Panchayati Raj",
            "Rural Administration",
            "Urban Administration",
            "Rural Livelihoods",
            "Urban Livelihoods",
        ],
        "7": [
            "History: Tracing Changes through a Thousand Years",
            "New Kings and Kingdoms",
            "The Delhi Sultans",
            "The Mughal Empire",
            "Rulers and Buildings",
            "Towns, Traders and Craftspersons",
            "Tribes, Nomads and Settled Communities",
            "Devotional Paths to the Divine",
            "The Making of Regional Cultures",
            "Eighteenth-Century Political Formations",
            "Geography: Environment",
            "Inside Our Earth",
            "Our Changing Earth",
            "Air",
            "Water",
            "Natural Vegetation and Wildlife",
            "Human Environment — Settlement, Transport and Communication",
            "Human-Environment Interactions: The Tropical and Subtropical Region",
            "Life in the Temperate Grasslands",
            "Life in the Deserts",
            "Civics: On Equality",
            "Role of the Government in Health",
            "How the State Government Works",
            "Growing up as Boys and Girls",
            "Women Change the World",
            "Understanding Media",
            "Understanding Advertising",
            "Markets Around Us",
            "A Shirt in the Market",
        ],
        "8": [
            "History: How, When and Where",
            "From Trade to Territory",
            "Ruling the Countryside",
            "Tribals, Dikus and the Vision of a Golden Age",
            "When People Rebel — 1857 and After",
            "Colonialism and the City",
            "Weavers, Iron Smelters and Factory Owners",
            "Civilising the Native, Educating the Nation",
            "Women, Caste and Reform",
            "The Changing World of Visual Arts",
            "The Making of the National Movement: 1870s–1947",
            "India After Independence",
            "Geography: Resources",
            "Land, Soil, Water, Natural Vegetation and Wildlife Resources",
            "Mineral and Power Resources",
            "Agriculture",
            "Industries",
            "Human Resources",
            "Civics: The Indian Constitution",
            "Understanding Secularism",
            "Why Do We Need a Parliament?",
            "Understanding Laws",
            "Judiciary",
            "Understanding Our Criminal Justice System",
            "Understanding Marginalisation",
            "Confronting Marginalisation",
            "Public Facilities",
            "Law and Social Justice",
        ],
    },
    "English": {
        "6": ["Grammar", "Essay Writing", "Comprehension", "Poetry Appreciation",
              "Letter Writing", "Story Writing", "Vocabulary Building", "Reading Skills"],
        "7": ["Grammar", "Essay Writing", "Comprehension", "Poetry Appreciation",
              "Letter Writing", "Story Writing", "Vocabulary Building", "Debate & Speech"],
        "8": ["Grammar", "Essay Writing", "Comprehension", "Poetry Appreciation",
              "Formal Letter Writing", "Story Writing", "Vocabulary & Idioms",
              "Debate & Speech", "Notice & Message Writing"],
    },
    "Hindi": {
        "6": ["व्याकरण (Grammar)", "निबंध लेखन (Essay)", "पत्र लेखन (Letter Writing)",
              "कविता (Poetry)", "गद्यांश (Comprehension)", "कहानी लेखन (Story Writing)",
              "शब्द भंडार (Vocabulary)"],
        "7": ["व्याकरण (Grammar)", "निबंध लेखन (Essay)", "पत्र लेखन (Letter Writing)",
              "कविता (Poetry)", "गद्यांश (Comprehension)", "कहानी लेखन (Story Writing)",
              "अनुच्छेद लेखन (Paragraph)", "शब्द भंडार (Vocabulary)"],
        "8": ["व्याकरण (Grammar)", "निबंध लेखन (Essay)", "पत्र लेखन (Letter Writing)",
              "कविता (Poetry)", "गद्यांश (Comprehension)", "कहानी लेखन (Story Writing)",
              "अनुच्छेद लेखन (Paragraph)", "विज्ञापन लेखन (Ad Writing)", "शब्द भंडार (Vocabulary)"],
    },
}

# ── Compressed system prompt (prompt-cached) ────────────────────────────────
SYSTEM_PROMPT = """CBSE lesson plan generator. Output ONLY valid JSON under 280 words total. No markdown, no backticks.
Schema: {"topic":"","grade":"","subject":"","ncert_ref":"","nep_competency":"","duration_min":0,"class_size":0,"learning_objectives":["","",""],"warm_up_activity":"","main_activity":"","assessment_question":"","homework":""}
Rules: blackboard only, Indian names (Priya/Arjun/Raju), NEP tag from [Critical Thinking|Experiential Learning|Collaborative Learning|Inquiry-Based Learning|Creative Expression], ncert_ref = chapter number + name."""

def build_user_message(grade, subject, topic, duration, strength, chapters):
    """Inject only the relevant curriculum slice — not the full syllabus."""
    chap_hint = ""
    if chapters and subject not in ("English", "Hindi"):
        try:
            idx = chapters.index(topic) + 1
            chap_hint = f" | NCERT Ch.{idx}"
        except ValueError:
            chap_hint = ""
    return (
        f"Grade {grade} {subject} | Topic: {topic}{chap_hint} | "
        f"{duration} min | {strength} students"
    )

def generate_plan(grade, subject, topic, duration, strength, chapters):
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    user_msg = build_user_message(grade, subject, topic, duration, strength, chapters)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"}  # prompt caching — ~90% cheaper on repeats
            }
        ],
        messages=[{"role": "user", "content": user_msg}]
    )
    raw = message.content[0].text.strip().replace("```json","").replace("```","").strip()
    try:
        plan = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON parse failed: {e} | Raw: {raw[:200]}")
    return plan, message.usage

def plan_to_text(p):
    return "\n".join([
        f"LESSON PLAN — {p.get('topic','')}",
        f"{p.get('ncert_ref','')} | Grade {p.get('grade','')} | {p.get('subject','')} | {p.get('duration_min','')} min | {p.get('class_size','')} students",
        f"NEP Competency: {p.get('nep_competency','')}","",
        "LEARNING OBJECTIVES:",
        *[f"{i+1}. {o}" for i,o in enumerate(p.get('learning_objectives',[]))], "",
        "WARM-UP (5 min):", p.get('warm_up_activity',''), "",
        "MAIN ACTIVITY:", p.get('main_activity',''), "",
        "ASSESSMENT:", p.get('assessment_question',''), "",
        "HOMEWORK:", p.get('homework','')
    ])

# ── UI ───────────────────────────────────────────────────────────────────────
st.markdown("## 📚 ShikshaAI")
st.markdown("**CBSE Lesson Plan Generator** · NCERT-aligned · NEP 2020 · Indian classroom defaults")
st.divider()

col1, col2 = st.columns(2)
with col1:
    grade = st.selectbox("Grade", ["6", "7", "8"], index=1)
with col2:
    subject = st.selectbox("Subject", list(CURRICULUM.keys()))

chapters = CURRICULUM.get(subject, {}).get(grade, [])
is_language = subject in ("English", "Hindi")

if chapters:
    if is_language:
        topic_label = "Topic / Skill area"
        help_text = None
    else:
        topic_label = "Chapter"
        help_text = f"{len(chapters)} NCERT chapters for Grade {grade} {subject}"

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
strength_num = strength.replace("~","").split()[0]

st.markdown("")
go = st.button("Generate lesson plan")

if go:
    if not topic:
        st.error("Please select or enter a topic.")
    else:
        with st.spinner("Writing your lesson plan..."):
            try:
                plan, usage = generate_plan(grade, subject, topic, duration_min, strength_num, chapters)

                in_t = usage.input_tokens
                out_t = usage.output_tokens
                cache_read = getattr(usage, 'cache_read_input_tokens', 0)
                cache_created = getattr(usage, 'cache_creation_input_tokens', 0)
                cost = (in_t * 0.0000008) + (out_t * 0.000001) + (cache_read * 0.00000008)

                st.markdown(f"### {plan.get('topic', topic)}")
                meta_parts = [
                    plan.get('ncert_ref',''),
                    f"Grade {plan.get('grade', grade)} {plan.get('subject', subject)}",
                    f"{plan.get('duration_min', duration_min)} min",
                    f"{plan.get('class_size', strength_num)} students",
                    plan.get('nep_competency','')
                ]
                st.caption(" · ".join(p for p in meta_parts if p))
                st.markdown('<span class="badge">CBSE ready</span>', unsafe_allow_html=True)

                st.markdown('<div class="sec-label">Learning objectives</div>', unsafe_allow_html=True)
                for obj in plan.get('learning_objectives', []):
                    st.markdown(f"- {obj}")

                for label, key in [
                    ("Warm-up activity (5 min)", "warm_up_activity"),
                    ("Main activity", "main_activity"),
                    ("Assessment question", "assessment_question"),
                    ("Homework", "homework"),
                ]:
                    st.markdown(f'<div class="sec-label">{label}</div>', unsafe_allow_html=True)
                    st.markdown(plan.get(key, ''))
                    st.markdown("")

                plain = plan_to_text(plan)
                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    st.download_button(
                        "Download as .txt", plain,
                        file_name=f"lesson_{topic[:20].replace(' ','_')}.txt",
                        use_container_width=True
                    )
                with c2:
                    st.link_button(
                        "Share on WhatsApp",
                        f"https://wa.me/?text={plain[:1000]}",
                        use_container_width=True
                    )

                cache_note = f" · {cache_read} cached" if cache_read else ""
                st.markdown(
                    f'<div class="cost-note">Tokens: {in_t} in + {out_t} out{cache_note} · Est. cost: ${cost:.5f}</div>',
                    unsafe_allow_html=True
                )

                with st.expander("View raw JSON"):
                    st.json(plan)

            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Error: {e}")
