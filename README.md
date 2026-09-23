# Verbatim Call Analyst

---

## 1. Scope

### What This Project Does

Verbatim Call Analyst is a local tool that takes a set of expert interview transcripts and an interview guide, and produces a **source-linked research summary** where every claim is backed by an exact, verbatim quote and timestamp from the original transcript files.

It was built to analyse 3 expert interviews (France, Germany, United Kingdom) on European robotic surgery adoption.

### Problem It Solves

Manual analysis of interview transcripts is slow and prone to paraphrasing errors. AI-assisted summaries are fast but risk hallucinating quotes or misattributing statements. This tool solves both problems by:

- Letting the LLM handle **reasoning** (answering, synthesising, comparing) but never the **quoting**
- Every quote is extracted directly from the parsed transcript file — the model only selects a sentence ID, not the text itself
- This makes all citations **verbatim by construction**, regardless of model size or temperature

### What It Covers

| Feature | Description |
|---|---|
| Guide Answers Matrix | Per-question, per-expert answer grid with status (Answered / Partial / Not Discussed) and cited quotes |
| Cross-Market Themes | Common themes identified across all experts, backed by verified quotes |
| Cross-Market Disagreements | Typed disagreements (Contradiction / Emphasis / Scope) between experts |
| Ask Chat | Free-form Q&A grounded in transcript content, with citation trail |
| General Chat | Conversational replies and context-aware follow-ups (e.g. "what did he mean by that?") |
| Citation Drilldown | Click any quote to see the full surrounding conversation context |

### What It Does Not Cover

- Multi-user authentication or internet-facing deployment (single local user only)
- Semantic / embedding-based retrieval (uses keyword BM25 only at this scale)
- Mid-sentence quote extraction (sentence-level granularity)

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| Web Framework | Flask 3.x |
| Frontend | Vanilla HTML/CSS/JS (single-page app) |
| Data Models | Pydantic v2 |
| LLM Runtime | llama-cpp-python (local GGUF inference) |
| LLM Model | Qwen2.5-1.5B-Instruct-GGUF (Q4_K_M, ~1.1GB) |
| Model Download | huggingface_hub |
| Keyword Retrieval | rank_bm25 (BM25Okapi) |
| Cross-Origin Support | flask-cors |
| Language | Python 3.10+ |
| Persistence | JSON files (no database) |

---

## 3. Why That Stack

### Flask — not Streamlit or FastAPI

The app started as Streamlit but was migrated to Flask. Streamlit is fast to prototype but tightly couples the UI to Python, making it hard to build a rich, interactive frontend. Flask gives full control over the REST API and lets the UI be a proper single-page application with modals, tabs, animated quote drawers, and live chat — impossible to achieve cleanly in Streamlit.

FastAPI was considered but Flask was preferred because the app has no async I/O bottleneck (the LLM is CPU-bound and synchronous anyway), and Flask's simplicity reduces boilerplate.

### Vanilla HTML/CSS/JS — not React or Vue

No JavaScript framework was needed because the app is a single page with a fixed set of components. Vanilla JS keeps the project dependency-free on the frontend side, faster to load, and easier for anyone to read and modify without knowing a framework.

### Pydantic v2 — for data models

Every object flowing through the pipeline (Sentence, Turn, Transcript, AnswerCell, Quote) is a Pydantic model. This gives:
- Runtime type validation (catches malformed LLM output early)
- Clean `.model_dump()` serialization for JSON API responses
- Self-documenting schemas

### llama-cpp-python + GGUF — not OpenAI or HuggingFace Transformers

The model runs **fully locally** with no API key, no internet after first download, and no data leaves the machine. GGUF quantization (Q4_K_M) keeps the model at ~1.1GB and runs comfortably on 8GB RAM with no GPU.

Using Transformers would require PyTorch and ~4x more RAM for the same model. llama-cpp-python uses the optimized llama.cpp C++ backend which is significantly faster for CPU inference.

### Qwen2.5-1.5B-Instruct — not a larger model

A larger model would improve synthesis prose quality but **not citation accuracy**, because the model never types out quotes — it only selects sentence IDs. A small model that follows the JSON instruction format reliably is sufficient for this task.

### rank_bm25 — not a vector database

BM25 is keyword-based, runs in memory, and needs no embedding model or external service. At 3 transcripts (~150 expert sentences), it is fast and accurate enough. The tradeoff (no semantic matching) is documented and the upgrade path (sqlite-vec) is straightforward.

### JSON files — not SQLite or PostgreSQL

The app's entire state (parsed transcripts, answers, themes, chat history) fits in two JSON files under 1MB. A database would add setup friction with no benefit at this scale. The persistence layer (`core/cache.py`, `core/chat_store.py`) is isolated enough that swapping to SQLite is a single-module change.

---

## 4. Implementation

### Quick Start

**Step 1 — Create virtual environment**

```bash
python -m venv venv
```

Activate:
- Windows (PowerShell): `.\venv\Scripts\Activate.ps1`
- Windows (Git Bash): `source venv/Scripts/activate`
- macOS / Linux: `source venv/bin/activate`

**Step 2 — Install dependencies**

```bash
pip install -r requirements.txt
```

> **Windows note:** If `llama-cpp-python` fails to build from source, install a prebuilt CPU wheel:
> ```bash
> pip install llama-cpp-python --prefer-binary --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
> pip install -r requirements.txt
> ```

**Step 3 — Run the app**

```bash
python app.py
```

Open **http://localhost:5000** in your browser. Login:
- Username: `admin`
- Password: `hasamex2026`

The first run downloads the GGUF model (~1.1GB). After that it runs fully offline.

---

### Architecture & Pipeline

```
data/ (Interview Guide + Transcripts)
        │
        ▼
core/parser.py          Parse files → Turns and Sentences with stable IDs (e.g. FR-02-s1)
        │
        ▼
core/relevance.py       Fast keyword-overlap guard — rejects obviously off-topic uploads
        │
        ▼
core/answer_engine.py   LLM proposes answer + sentence IDs per (question, expert) pair
        │
        ▼
core/verifier.py        Code verifies each sentence ID → rejects hallucinated IDs
        │                 Quote text and timestamps always come from parsed files, never from LLM
        ▼
core/synthesis.py       LLM synthesises themes and disagreements from verified answers only
        │
        ▼
core/cache.py           Persist everything to cache/cache.json (skip LLM on next run)
        │
        ▼
app.py                  Flask REST API serves the full state to the web UI
        │
        ▼
templates/index.html    Single-page web app renders the Guide Answers Matrix, Themes,
+ static/js/app.js      Disagreements, Ask Chat, and Citation Drilldown
```

---

### Hallucination Controls

1. **Sentence-ID citation** — the LLM never types a quote, it only references IDs like `FR-02-s1`
2. **Code-side verification** — every ID is checked against the parsed transcript; unknown IDs are silently rejected
3. **Interviewer sentences excluded** — only expert sentences are in the citable pool
4. **Status downgrade** — if all proposed IDs are rejected, the status drops from `answered` → `partial`
5. **Synthesis from verified data only** — themes/disagreements are built from the answer grid, not raw transcripts
6. **Typed disagreements** — forced to one of: `contradiction`, `emphasis`, `scope`
7. **Ask refusal** — returns "Not covered in these calls" when BM25 score is below threshold

---

### Chat Modes

**Research questions** (with source citations):
- Retrieves top-k relevant sentences via BM25
- LLM selects sentence IDs that answer the question
- Verified quotes are returned with `[Country TurnID @ Timestamp]` citations

**General conversation** (context-aware):
- Detects greetings, small talk, and short non-research messages
- Passes the last 4–6 messages of conversation history to the LLM
- Resolves follow-up references ("he", "it", "that expert") from prior context

---

### Project Structure

```
verbatim-call-analyst/
├── app.py                    # Flask REST API + web server entry point
├── config.py                 # all paths, model settings, and constants
├── requirements.txt
├── test_flask_api.py         # automated API tests
├── data/                     # interview guide + 3 transcripts
├── cache/                    # cache.json + chat_history.json (auto-generated)
├── models_bin/               # GGUF model weights (git-ignored, ~1.1GB)
├── models/
│   └── schemas.py            # Pydantic models: Sentence, Turn, Quote, AnswerCell, ...
├── core/
│   ├── pipeline.py           # orchestrates the full parse → answer → synthesise run
│   ├── parser.py             # transcript/guide files → typed Python objects with stable IDs
│   ├── llm.py                # local GGUF model wrapper (generate_json + generate_text)
│   ├── answer_engine.py      # per-question/per-expert answer generation
│   ├── verifier.py           # sentence-ID → verified Quote lookup
│   ├── synthesis.py          # cross-expert themes & disagreements
│   ├── retrieval.py          # BM25 index + Ask answering + general chat routing
│   ├── relevance.py          # fast keyword-overlap relevance guard
│   ├── cache.py              # cache.json read/write
│   ├── chat_store.py         # chat history persistence (chat_history.json)
│   └── auth.py               # credential checking
├── templates/
│   └── index.html            # single-page web UI
├── static/
│   ├── css/style.css
│   └── js/app.js
└── prompts/
    ├── answer_prompt.txt
    ├── synthesis_prompt.txt
    └── ask_prompt.txt
```

---

### Running Tests

```bash
.\venv\Scripts\python.exe -m pytest test_flask_api.py -v
```

---

### Known Limitations

- Quotes are at sentence granularity — a mid-sentence fragment cannot be extracted
- BM25 is keyword-based; a paraphrased question with no shared vocabulary may under-retrieve
- Single hardcoded user — not suitable for multi-user or internet-facing deployment