# Verbatim Call Analyst

A tool that takes expert-call transcripts and an interview guide, and produces a
source-linked research summary — every claim points to an exact, verbatim quote
and timestamp — plus a chat interface to ask follow-up questions.

Built for analysis of 3 transcripts (France, Germany, UK) on European robotic surgery adoption.

## Quick Start

**1. Create and activate a virtual environment**

```bash
python -m venv venv
```

Activate it:
- Windows (PowerShell): `.\venv\Scripts\Activate.ps1`
- Windows (Git Bash): `source venv/Scripts/activate`
- macOS / Linux: `source venv/bin/activate`

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

> **Windows note:** `llama-cpp-python` may try to build from source and fail due to
> Windows' 260-character path limit. Fix with a prebuilt CPU wheel:
> ```bash
> pip install llama-cpp-python --prefer-binary --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
> pip install -r requirements.txt
> ```

**3. Run the app**

```bash
python app.py
```

Open your browser at **http://localhost:5000**. Log in with:
- Username: `admin`
- Password: `hasamex2026`

The app uses the 3 transcripts and guide already in `data/`. The first run downloads
the local GGUF model (~1.5GB) via `huggingface_hub` — after that it runs fully offline.
No API keys required.

## Architecture

```
data/ (guide + transcripts)
   -> core/parser.py            parses files into Turns and Sentences with stable IDs
   -> core/answer_engine.py     LLM proposes answer + sentence IDs, per (question, expert)
   -> core/verifier.py          code looks up each ID's verbatim text + timestamp, rejects invalid IDs
   -> core/synthesis.py         LLM synthesises themes/disagreements from verified answers only
   -> core/retrieval.py         BM25 search + LLM answer for free-form Ask questions
   -> core/cache.py             persists everything to cache.json so reruns skip the LLM
   -> app.py                    Flask REST API + serves the web UI
   -> templates/index.html      single-page web application
```

## Model Choice

Local Qwen2.5-1.5B-Instruct GGUF (~1.1GB), quantized to run on 8GB RAM with no GPU.

The model is never trusted to write out a quote. Every expert turn is split into
sentences at parse time, each given a stable ID (e.g. `FR-02-s1`). The model only
returns which sentence IDs support its answer — the actual quote text and timestamp
are always looked up from the parsed file in code. Quotes are verbatim by construction,
regardless of model size.

## Hallucination Controls

1. **Sentence-ID citation** — the LLM never types a quote, it only references IDs.
2. **Code-side verification** — every proposed ID is checked against the parsed transcript; unknown IDs are rejected.
3. **Interviewer sentences excluded** from the citable pool so questions can't be misattributed.
4. **Status downgrade** — if all proposed IDs are rejected, status is downgraded from `answered` to `partial`.
5. **Synthesis from verified data only** — themes and disagreements are built from the verified answer grid, not raw transcripts.
6. **Typed disagreements** — `contradiction`, `emphasis`, or `scope`, prompted with worked examples.
7. **Ask refusal** — returns "Not covered in these calls" when BM25 retrieval doesn't clear a relevance threshold.

## Storage

Everything runs in-memory plus a single `cache/cache.json`. No database required.
Chat history is persisted to `cache/chat_history.json` across sessions.

## Project Structure

```
verbatim-call-analyst/
├── app.py                    # Flask REST API + web server entry point
├── config.py                 # paths, model settings, constants
├── requirements.txt
├── test_flask_api.py         # automated API tests
├── data/                     # interview guide + transcripts
├── cache/                    # generated on first run (cache.json, chat_history.json)
├── models_bin/               # downloaded GGUF model weights (git-ignored)
├── models/
│   └── schemas.py            # Pydantic models (Sentence, Turn, Quote, AnswerCell, ...)
├── core/
│   ├── parser.py             # files -> Turns/Sentences with stable IDs
│   ├── llm.py                # local GGUF model wrapper (llama-cpp-python)
│   ├── verifier.py           # sentence-ID -> verified Quote lookup
│   ├── answer_engine.py      # per-question/per-expert generation
│   ├── synthesis.py          # themes & disagreements
│   ├── retrieval.py          # BM25 + Ask answering
│   ├── cache.py              # cache.json read/write
│   ├── chat_store.py         # chat history persistence
│   ├── relevance.py          # relevance filtering
│   ├── auth.py               # credential checking
│   └── pipeline.py           # orchestrates the full run
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

## Running Tests

```bash
.\venv\Scripts\python.exe -m pytest test_flask_api.py -v
```

## Chat Capabilities

The Ask chat supports two modes:

**Research questions** (with source citations):
- Ask anything about the transcripts (e.g. *"What did the France expert say about adoption barriers?"*)
- Answers are grounded in verified transcript sentences with citations (`[FR-04 @ 00:18]`)
- Returns *"Not covered in these calls"* when the transcripts don't address the question

**General conversation** (context-aware):
- Greetings and small talk: *"Hi"*, *"Hello"*, *"Thanks"*, *"What can you do?"*
- Follow-up references: *"What did he say about that?"*, *"Can you expand on it?"*, *"What was that expert's role?"*
- The last 4-6 messages of conversation history are passed to the LLM so pronouns and references like *"he"*, *"it"*, *"that"*, *"this"* are resolved correctly from earlier in the same chat thread

## Known Limitations

- Quotes are extractive at sentence granularity — a mid-sentence fragment cannot be pulled out.
- BM25 retrieval is keyword-based; a paraphrased question with no shared vocabulary may under-retrieve.
- Single hardcoded user — not suitable for multi-user or internet-facing deployment.