# Verbatim Call Analyst
## Project Scope Document

**Document Type:** Pre-Development Scope & Architecture Definition
**Status:** Approved — Development Complete
**Prepared by:** Joselin Janet J
**Submission:** Case Study — AI-Powered Research Tool

---

## 1. Problem Statement

### 1.1 Context

The business requirement was to extract meaningful insights from a set of expert interview transcripts — reliably, at scale, without loss of citation accuracy.

### 1.2 Identified Pain Points

| Pain Point | Description |
|---|---|
| **Manual analysis is slow** | Researchers spend hours reading transcripts and writing summaries |
| **Paraphrasing distorts meaning** | Human note-taking rewrites what experts actually said |
| **AI summaries hallucinate** | LLMs fabricate quotes, misattribute statements, or blend speakers |
| **No citation trail** | Existing approaches cannot link a claim back to an exact source moment |

### 1.3 Core Problem Definition

> **Can we achieve AI-speed analysis with human-level citation accuracy?**

The answer this project proposes: **yes — but only by changing what the AI is asked to do.**

Instead of asking the model to write quotes, the model is asked only to *select sentence IDs.* The actual quote text is always pulled from the real parsed file. This means every citation is **verbatim by construction**, not by trust.

---

## 2. Scope of Work

### 2.1 What This Tool Covers

| Feature | Description |
|---|---|
| **Guide Answers Matrix** | Per-question, per-expert answer grid with status (Answered / Partial / Not Discussed) and cited verbatim quotes |
| **Cross-Market Themes** | Common patterns identified across all experts, backed by verified quotes |
| **Cross-Market Disagreements** | Typed disagreements (Contradiction / Emphasis / Scope) between experts, with quotes from both sides |
| **Ask Chat** | Free-form Q&A grounded in transcript content, with a full citation trail |
| **General Chat** | Conversational replies and context-aware follow-ups |
| **Citation Drilldown** | Click any quote to see the full surrounding conversation context |

### 2.2 What This Tool Does Not Cover

- Multi-user authentication or internet-facing deployment (single local user only)
- Semantic / embedding-based retrieval (uses keyword BM25 at this scale)
- Mid-sentence quote extraction (sentence-level granularity)

---

## 3. Architecture & Pipeline Design

> **Design Principle: The LLM reasons — the code quotes. Always.**

The pipeline was designed before development began. The following stages were defined:

```
data/ (Interview Guide + 3 Transcripts)
        │
        ▼
STAGE 1 — core/parser.py
Parse files → Turns and Sentences with stable IDs (e.g. FR-02-s1)
        │
        ▼
STAGE 2 — core/relevance.py
Fast keyword-overlap guard — rejects obviously off-topic uploads early
        │
        ▼
STAGE 3 — core/answer_engine.py
LLM proposes sentence IDs per (question, expert) pair — no quote text
        │
        ▼
STAGE 4 — core/verifier.py
Code verifies each sentence ID → rejects hallucinated IDs
Quote text and timestamps come from parsed files, never from LLM
        │
        ▼
STAGE 5 — core/synthesis.py
LLM synthesises themes and disagreements from verified answers only
        │
        ▼
STAGE 6 — app.py + templates/index.html
Flask REST API → Single-page web UI
```

### 3.1 Hallucination Controls (Pre-Defined)

These controls were designed into the architecture from day one:

1. **Sentence-ID citation** — the LLM never types a quote; it only returns IDs like `FR-02-s1`
2. **Code-side verification** — every ID is checked against the parsed transcript; unknown IDs are silently rejected
3. **Interviewer sentences excluded** — only expert sentences are in the citable pool
4. **Status downgrade** — if all proposed IDs are rejected, status drops from `answered` → `partial`
5. **Synthesis from verified data only** — themes/disagreements are built from the answer grid, not raw transcripts
6. **Typed disagreements** — forced to one of: `contradiction`, `emphasis`, `scope`
7. **Ask refusal** — returns "Not covered in these calls" when BM25 score is below threshold

---

## 4. Technical Stack Decisions

Each technology was selected for a specific, documented reason.

| Layer | Technology | Why |
|---|---|---|
| Web Framework | **Flask 3.x** | Full REST API control; Streamlit couldn't support rich interactive UI (modals, animated drawers, tabs) |
| Frontend | **Vanilla HTML/CSS/JS** | Single-page app with fixed components — no framework needed; zero build step, fast load |
| Data Models | **Pydantic v2** | Runtime type validation; catches malformed LLM output before it reaches the UI |
| LLM Runtime | **llama-cpp-python (GGUF)** | Fully local, no API key, no internet after first download, optimised C++ backend for CPU |
| LLM Model | **Qwen2.5-1.5B-Instruct Q4_K_M** | 1.1GB, runs on 8GB RAM, no GPU — model never types quotes so size doesn't affect citation accuracy |
| Keyword Retrieval | **rank_bm25** | Fast, in-memory, no vector DB needed; at ~150 expert sentences BM25 is accurate enough |
| Persistence | **JSON files** | Full state fits under 1MB; no database setup needed; `pip install` + `python app.py` is the entire setup |

### 4.1 Alternatives Considered and Rejected

| Alternative | Reason Rejected |
|---|---|
| Streamlit | Tightly couples UI to Python; cannot build modals, animated quote drawers, or tabbed layouts cleanly |
| FastAPI | No async I/O bottleneck; LLM is CPU-bound and synchronous — Flask's simplicity was preferred |
| React / Vue | Overkill for a single-page app with fixed components; adds a build step and dependency chain |
| OpenAI API | Requires API key, sends data to the cloud, costs money per call — violates local-only constraint |
| HuggingFace Transformers | Requires PyTorch; ~4x more RAM for the same model; slower CPU inference than llama.cpp |
| Vector Database | No semantic retrieval needed at 3 transcripts / ~150 sentences; BM25 is sufficient |
| SQLite / PostgreSQL | Full state under 1MB; database would add setup friction with zero benefit at this scale |

---

## 5. Use of AI

AI was used in two distinct capacities in this project:

### 5.1 AI Within the Product (Local LLM)

The **Qwen2.5-1.5B-Instruct** model (running locally via llama-cpp-python) is used for:

| Task | What the Model Does | What the Model Does NOT Do |
|---|---|---|
| Guide Q&A | Selects which sentence IDs from an expert are relevant to a question | Writes or paraphrases any quote text |
| Synthesis | Identifies cross-market themes and disagreements from verified answer data | Reads raw transcripts directly |
| Ask Chat | Selects sentence IDs that answer a free-form research question | Fabricates answers when coverage is below threshold |

### 5.2 AI in Development

AI coding assistants were used during development to accelerate boilerplate, debug prompt formats, and iterate on pipeline logic. This is disclosed transparently.

> **The core architectural decision — separating reasoning from quoting, and using sentence-ID verification as a hallucination firewall — is an original design decision, not AI-generated.**

---

## 6. Anticipated Challenges & Mitigations

These challenges were anticipated during planning and addressed in the design:

| Challenge | Risk | Mitigation Designed |
|---|---|---|
| **LLM hallucination** | Model writes plausible but fabricated quotes | Model outputs IDs only; code fetches real text; unknown IDs are rejected |
| **Running locally without GPU** | Large models too slow on CPU | Qwen2.5-1.5B Q4_K_M — 1.1GB, CPU-optimised, sufficient for ID-selection tasks |
| **Framework limitations** | Streamlit couldn't support required UI components | Designed for Flask + Vanilla JS from the start (with Streamlit as prototype) |
| **Misattribution between speakers** | LLM may confuse expert and interviewer turns | Interviewer sentences excluded from the citable pool at parse time |
| **Out-of-context quotes** | A quote pulled alone may be misleading | Citation Drilldown shows full surrounding conversation context |

---

## 7. Project Structure

```
verbatim-call-analyst/
├── app.py                    # Flask REST API + web server entry point
├── config.py                 # All paths, model settings, and constants
├── requirements.txt
├── test_flask_api.py         # Automated API tests
├── data/                     # Interview guide + 3 transcripts (FR, DE, UK)
├── cache/                    # cache.json + chat_history.json (auto-generated)
├── models_bin/               # GGUF model weights (~1.1GB, git-ignored)
├── models/
│   └── schemas.py            # Pydantic models: Sentence, Turn, Quote, AnswerCell
├── core/
│   ├── pipeline.py           # Orchestrates full parse → answer → synthesise run
│   ├── parser.py             # Transcript/guide → typed Python objects with stable IDs
│   ├── llm.py                # Local GGUF model wrapper (generate_json + generate_text)
│   ├── answer_engine.py      # Per-question / per-expert answer generation
│   ├── verifier.py           # Sentence-ID → verified Quote lookup
│   ├── synthesis.py          # Cross-expert themes & disagreements
│   ├── retrieval.py          # BM25 index + Ask answering + general chat routing
│   ├── relevance.py          # Fast keyword-overlap relevance guard
│   ├── cache.py              # cache.json read/write
│   ├── chat_store.py         # Chat history persistence
│   └── auth.py               # Credential checking
├── templates/
│   └── index.html            # Single-page web UI
├── static/
│   ├── css/style.css
│   └── js/app.js
└── prompts/
    ├── answer_prompt.txt
    ├── synthesis_prompt.txt
    └── ask_prompt.txt
```

---

## 8. Defined Output Deliverables

| Deliverable | Description |
|---|---|
| Guide Answers Matrix | Interactive grid — per question, per expert, with status and verbatim quotes |
| Themes Report | Cross-market patterns with quote evidence |
| Disagreements Report | Typed expert divergences with quotes from both sides |
| Ask Chat Interface | Free-form research Q&A with citation trail |
| Citation Drilldown | Full conversation context for any cited sentence |
| Locally Runnable App | Single command setup — `pip install -r requirements.txt` → `python app.py` |

---

## 9. Known Limitations (Documented Pre-Delivery)

| Limitation | Notes |
|---|---|
| Sentence-level quote granularity | Mid-sentence fragment extraction is not supported |
| BM25 keyword matching only | Paraphrased questions with no shared vocabulary may under-retrieve; upgrade path to sqlite-vec is straightforward |
| Single hardcoded user | Not suitable for multi-user or internet-facing deployment |

---

*This document represents the scope and design intent defined before development commenced. All major architectural decisions listed here were made prior to writing production code.*
