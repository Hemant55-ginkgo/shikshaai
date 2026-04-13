# ShikshaAI — Architecture Decision Log
**Version:** 1.0  
**Stage:** Pre-user, prototype deployment  
**Last updated:** April 2026

---

## The Founder's North Star

> Before every feature decision, ask:
> **"Does this make the data richer?"** — not just "does this make the tool more useful?"
>
> You are not building a Streamlit app or an LLM wrapper.
> You are building a **data engine for a vertical AI system.**
>
> — The brain (Claude, Gemini, LLaMA) can be swapped.  
> — The memory (logs, edits, feedback) cannot be replicated.  
> — The structure (schema, validation, workflow) is your product.
>
> Every edit a teacher makes is a free training example.  
> Every session logged is a future fine-tuning dataset.  
> Every prompt versioned is a regression test suite.  
> The flywheel: more teachers → richer data → better local model → lower cost → more teachers.

---

## Mental Model

```
BRAIN (swappable)          STRUCTURE (permanent)       MEMORY (permanent)
llm_service/               contract/                   data/
  base.py                    schema.py                   curriculum.py
  claude.py                  prompts.py                  logger.py
  gemini.py (future)                                     Supabase
  ollama.py (future)
  factory.py
  config.py

app.py — UI only. Owns nothing. Imports everything.
```

---

## File Structure (Target)

```
shikshaai/
├── app.py                        ← UI only, no business logic
├── requirements.txt
├── config.py                     ← model switch flag (Decision 10)
│
├── contract/                     ← STRUCTURE layer
│   ├── __init__.py
│   ├── schema.py                 ← LessonPlan dataclass + validation
│   └── prompts.py                ← versioned prompt templates
│
├── data/                         ← MEMORY layer
│   ├── curriculum.py             ← NCERT chapter maps (moved from app.py)
│   └── logger.py                 ← Supabase write functions
│
├── llm_service/                  ← BRAIN layer
│   ├── __init__.py
│   ├── base.py                   ← abstract interface
│   ├── claude.py                 ← Claude implementation
│   ├── factory.py                ← picks brain from config
│   └── validator.py              ← repair → retry → escalate logic
│
└── .streamlit/
    └── secrets.toml              ← never committed to GitHub
```

---

## Decision Log

### Decision 1 — Freeze the Input → Prompt → Output contract
**Status:** Agreed · Partially built (`contract/schema.py` exists)  
**What:** `LessonPlan` dataclass is the single source of truth for output shape. All fields typed and required. Model name lives in config, not scattered in code.  
**Why:** The schema is your most durable asset. Models change. The schema should not.  
**Files:** `contract/schema.py`

---

### Decision 2 — Extract prompt logic into `llm_service/`
**Status:** Agreed · Pending deployment  
**What:** `app.py` never imports `anthropic` directly. All model calls go through `llm_service/factory.py` → `claude.py`. API key is passed in, never fetched inside the service layer (no `st.secrets` in service files).  
**Why:** Swapping Claude for Gemini or a fine-tuned local model must not require touching the UI.  
**Files:** `llm_service/base.py`, `llm_service/claude.py`, `llm_service/factory.py`

---

### Decision 3 — FastAPI backend
**Status:** Agreed · Deferred until prototype has real users  
**What:** Service layer is designed as a drop-in. `generate_lesson_plan(input_json) → output_json` will be callable from both Streamlit and a future FastAPI route without modification.  
**Why:** No complexity cost now. No rewrite cost later.  
**Trigger to build:** First institutional customer (school chain) or concurrent user issues.

---

### Decision 4 — Log everything to Supabase
**Status:** Agreed · Pending deployment  
**What:** Two tables. Every generation and every feedback event stored separately.

```sql
sessions:   id, created_at, grade, subject, topic,
            duration_min, class_size, chapter_index,
            model_id, prompt_version,
            input_tokens, output_tokens, cache_tokens,
            prompt_sent, raw_model_output,
            parsed_successfully, lesson_plan_json,
            error_message

feedback:   id, session_id, created_at,
            rating,              -- 1=thumbs up / 0=thumbs down
            field_edited,        -- which section
            original_value,      -- model output
            edited_value,        -- teacher version
            edit_type,           -- inferred by code
            time_to_edit_seconds,
            feedback_note
```

**Why:** This is the fine-tuning dataset, the evaluation dataset, and the regression test suite — being built passively by teachers using the product naturally.  
**Storage:** Supabase free tier (500MB, unlimited rows). Queryable via SQL. Connect to Metabase for analysis.  
**Files:** `data/logger.py`

---

### Decision 5 — Strict output validation + recovery
**Status:** Agreed · Pending deployment  
**What:** Model output never trusted directly. Recovery hierarchy:

```
1. REPAIR    — strip markdown, coerce types, fill safe defaults (free, no API call)
2. RETRY     — same model, stricter prompt, max 2 attempts
3. ESCALATE  — Claude Sonnet, single attempt, silent (teacher sees "Taking a little longer...")
4. FAIL CLEAN — log full error, show clear message, never a raw stack trace
```

Every failure at every stage logged to Supabase.  
**Why:** A teacher in a school day getting a broken output with no recovery is a permanent churn event.  
**Files:** `llm_service/validator.py`, extends `contract/schema.py`

---

### Decision 6 — Separate reasoning vs formatting
**Status:** Agreed in principle · Deferred to tool #2 (worksheet / rubric generator)  
**Design rule locked in now:**
> The model is responsible for content and reasoning.  
> Your code is responsible for structure and formatting.  
> Never ask the model to do both if your code can do the formatting deterministically.

**Why deferred:** Lesson plan output is constrained enough that the repair layer (Decision 5) handles formatting failures. The split becomes essential for more complex tools.

---

### Decision 7 — Brain / Memory / Structure separation
**Status:** Agreed · Guides all future file placement  
**Filter for every new file:**

```
Does this file still make sense if you deleted the Anthropic SDK tomorrow?
  Yes → it is Memory or Structure → lives in data/ or contract/
  No  → it is Brain work → lives in llm_service/
```

**Immediate action:** Move `CURRICULUM` dict out of `app.py` into `data/curriculum.py`.  
**Files:** `data/curriculum.py`

---

### Decision 8 — Capture edits passively
**Status:** Agreed · Pending deployment  
**What:** Every output section is an editable text field from day one. Edits silently logged to `feedback` table. No "submit feedback" button — capture happens automatically on change.

```python
def infer_edit_type(original, edited):
    if not edited:            return "delete"
    if not original:          return "addition"
    ratio = len(edited) / len(original)
    if ratio > 1.5:           return "append"
    if ratio < 0.5:           return "truncate"
    if edited in original:    return "minor_fix"
    return                           "rewrite"
```

`time_to_edit_seconds` logged as proxy for teacher confidence.  
**Why:** A rewrite is one supervised fine-tuning example. 10,000 rewrites from Indian CBSE teachers is a dataset no competitor can buy.  
**Files:** `app.py` (UI edit fields), `data/logger.py` (write to feedback table)

---

### Decision 9 — Downward compatible prompts
**Status:** Agreed · Pending deployment  
**Four rules:**

1. **Positive instructions only** — "Start response with `{`" not "Do not add markdown"
2. **Typed schema with examples** — show the model what a good value looks like, not an empty string
3. **Prompt variants by model tier** — `full` (Sonnet), `standard` (Haiku), `compact` (local/LLaMA)
4. **Version every prompt** — `PROMPT_VERSION = "v1.2"` logged with every session

**Prompt regression testing:** Once 50+ sessions logged, run any prompt change against historical inputs before deploying. Validate structurally — did all required fields survive? Did quality drop?  
**Files:** `contract/prompts.py`, `data/logger.py` (prompt_version column)

---

### Decision 10 — Model switch flag via `config.py`
**Status:** Agreed · Pending deployment  
**What:**

```python
# config.py
MODEL_BACKEND = "claude"       # "claude" | "gemini" | "local"
LOCAL_MODEL_ENDPOINT = None    # "http://localhost:11434" for Ollama
LOCAL_MODEL_NAME = None        # "llama3.1" or "mistral-7b-shikshaai-v1"

TIER_MAP = {
    "claude":  "standard",
    "gemini":  "standard",
    "local":   "compact",
}
```

No UI. Changed by developer only. Invisible to teachers.  
**Why:** The day a fine-tuned ShikshaAI model exists, the entire system switches with one line. Nothing else changes.  
**Files:** `config.py`, `llm_service/factory.py`

---

## What Is NOT Being Built Yet
- FastAPI backend (Decision 3 — deferred)
- Reasoning vs formatting split (Decision 6 — deferred to tool #2)
- Per-section star ratings (deferred to v2 after 👍/👎 baseline)
- Model selection UI for teachers (never, or much later as admin feature)
- Fine-tuning pipeline (needs ~10,000 logged sessions first)

---

## The Flywheel

```
More teachers use ShikshaAI
          ↓
More edits captured passively
          ↓
Richer fine-tuning dataset in Supabase
          ↓
Fine-tuned local model (LLaMA / Mistral) on Indian curriculum
          ↓
Lower cost per generation + higher quality output
          ↓
More teachers use ShikshaAI
```

At scale: fine-tuned local model handles 80% of requests.
Claude handles edge cases only.
Marginal cost per teacher approaches zero.
₹200/teacher/year becomes extraordinarily profitable.

---

## For the Next Developer / Technical Co-founder

This codebase is built around one principle:

> The AI model is a temporary dependency.
> The data is the permanent asset.

Do not add model-specific code outside `llm_service/`.  
Do not add curriculum or session data inside `app.py`.  
Do not skip logging — even in development.  
Do not trust model output — always validate through `schema.py`.

Every shortcut taken against these rules makes the brain harder to swap
and the data harder to use. The architecture exists to prevent that.
