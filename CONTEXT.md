# ShikshaAI — Founder context bundle v1.0

## Product
AI-powered lesson plan generator for CBSE K-12 teachers in India.
Modelled after MagicSchool AI, localised for Indian classrooms.
Prototype live on Streamlit. Moving toward FastAPI + fine-tuned local model.

## Founder
Solo, bootstrapped mindset, early stage.
First markets: Delhi NCR, Mumbai, Bengaluru.
Target school chains: DPS, Ryan, DAV.

## Users
CBSE/ICSE teachers, English-medium schools, Grade 6–8 primary focus.
Classroom context: 40–60 students, blackboard only, limited devices.
Distribution channel: WhatsApp teacher groups.

## Revenue model
Freemium → ₹200–500/teacher/yr premium.
Free tier: 5 uses/tool/month.
School chain bulk: ₹150/teacher/yr.

## Strategic framing
We are building a data engine for a vertical AI system.
  Brain (Claude/Gemini/local model) = temporary, swappable.
  Memory (Supabase logs, teacher edits, feedback) = permanent, the moat.
  Structure (schema, validation, workflow) = permanent, the product.
Before every feature decision ask: "Does this make the data richer?"

## Active role system
[PRODUCT] — feature prioritisation, user stories, India localisation
[GTM]     — go-to-market, school outreach, pricing
[TECH]    — architecture, prompt engineering, token efficiency
[CONTENT] — sample tool outputs for demos
[RESEARCH]— competitive analysis, NEP 2020, DIKSHA

## Token efficiency rules
1. Never repeat context already in this bundle
2. Structured output preferred — JSON or bullets over prose
3. Batch related questions — answer multiple asks in one pass
4. Produce minimum viable output first, expand only if asked
5. For architecture: analyse first, deploy only when explicitly asked

## India localisation defaults
Curriculum: NCERT-aligned, CBSE primary.
Languages: English first, Hindi second.
Pedagogy: NEP 2020 competency-based learning.
Examples: Indian names (Priya, Arjun, Raju), Indian cities, Indian context.

## Current stack
UI:       Streamlit (prototype) → FastAPI (future)
Model:    Claude Haiku 4.5 (now) → fine-tuned LLaMA/Mistral (future)
Storage:  Supabase (logging + feedback)
Deploy:   Streamlit Cloud (now) → VPS/Railway (future)

## File structure (target)
shikshaai/
├── app.py                  ← UI only, no business logic
├── config.py               ← model switch flag
├── contract/
│   ├── schema.py           ← LessonPlan dataclass + validation (built)
│   └── prompts.py          ← versioned prompt templates
├── data/
│   ├── curriculum.py       ← NCERT chapter maps
│   └── logger.py           ← Supabase write functions
├── llm_service/
│   ├── base.py             ← abstract interface
│   ├── claude.py           ← Claude implementation
│   ├── factory.py          ← picks brain from config
│   └── validator.py        ← repair → retry → escalate
└── .streamlit/
    └── secrets.toml        ← never commit to GitHub

## Architecture decisions summary
10 decisions made — see DECISIONS.md for full detail.
Pending deployment: 2, 4, 5, 8, 9, 10
Deferred: 3 (FastAPI), 6 (reasoning vs formatting split)
Built: 1 (schema.py)

## What we do NOT do yet
- FastAPI backend
- Per-section star ratings (👍/👎 first)
- Model selection UI for teachers
- Fine-tuning pipeline (need ~10,000 sessions first)
- Reasoning vs formatting split (deferred to tool #2)
