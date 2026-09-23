# Transcript Insight App

A tool that takes expert-call transcripts and an interview guide, and produces a
source-linked research summary — every claim points to an exact, verbatim quote
and timestamp — plus a chat to ask follow-up questions.

Built for the Hasamex AI Engineer technical case (3 transcripts: France, Germany, UK
on European robotic surgery adoption).

## Quick start

**1. Create and activate a virtual environment**

```bash
python -m venv venv
```

Activate it:
- Windows (Git Bash / MINGW64): `source venv/Scripts/activate`
- Windows (PowerShell): `venv\Scripts\Activate.ps1`
- macOS / Linux: `source venv/bin/activate`

Your prompt should now show `(venv)` at the start of the line.

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

> **Windows note:** `llama-cpp-python` ships no prebuilt wheel for every Python
> version, so pip may try to build it from source. That build pulls in the
> full `llama.cpp` source tree, and one of its nested file paths can exceed
> Windows' 260-character path limit, failing with an error like:
> `OSError: [Errno 2] No such file or directory: ...\ChatAttachmentsListItemMcpPrompt.svelte`
>
> Fix it with either of these, in order of preference:
>
> **Option A — install a prebuilt CPU wheel instead of building from source:**
> ```bash
> pip install llama-cpp-python --prefer-binary --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
> pip install streamlit pydantic rank_bm25 huggingface_hub
> ```
>
> **Option B — enable Windows long paths (needs admin + a reboot):**
> ```powershell
> New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
> git config --system core.longpaths true
> ```
> Reboot, then retry `pip install -r requirements.txt`.

**3. Run the app**

```bash
streamlit run app.py
```

The app defaults to the 3 case transcripts and guide already in `data/`. You can
upload your own `.txt` files from the sidebar to analyse a different set instead.

First run downloads the local GGUF model (a few GB) via `huggingface_hub` — after
that it's cached locally and runs fully offline. No API keys required.

## Architecture

```
data/ (guide + transcripts)
   -> core/parser.py            parses files into Turns and Sentences with stable IDs
   -> core/answer_engine.py     LLM proposes answer + sentence IDs, per (question, expert)
   -> core/verifier.py          code looks up each ID's verbatim text + timestamp, rejects invalid IDs
   -> core/synthesis.py         LLM synthesises themes/disagreements from VERIFIED answers only
   -> core/retrieval.py         BM25 search + LLM answer for free-form "Ask" questions
   -> core/cache.py             persists everything to cache.json so reruns don't re-call the LLM
   -> app.py + ui/*.py          Streamlit screens: Guide Answers, Themes, Ask, Citation Viewer
```

## Model choice

Local, small instruction-tuned model (~3-4B parameters) via `llama-cpp-python`,
quantized to run comfortably on 8GB RAM with no GPU or internet dependency after
the first download.

**Why a small local model is enough here:** the model is never trusted to write
out a quote. Every expert turn is split into sentences at parse time, and each
sentence gets a stable ID (e.g. `FR-02-s1`). The model only ever returns which
sentence IDs support its answer — the actual quote text and timestamp are always
looked up from the parsed file in code. This makes quotes verbatim *by
construction*, regardless of model size. A larger/cloud model would mainly
improve synthesis prose quality, not citation accuracy, so there's no strong
case for the added cost/latency/data-sharing here.

## How hallucination is controlled

1. **Sentence-ID citation, not free-text quoting.** The LLM can't paraphrase,
   shorten, or smooth a quote it never has to type out.
2. **Code-side verification.** Every ID the model proposes is checked against
   the parsed transcript. Unknown IDs are rejected; timestamps always come from
   the turn's own metadata, never from the model.
3. **Interviewer sentences are excluded** from the citable sentence pool, so
   questions can never be misattributed as expert answers.
4. **Status downgrade on empty evidence.** If a cell is marked "answered" but
   every proposed sentence ID gets rejected, it's automatically downgraded to
   "partial" rather than shown as a fully-evidenced answer.
5. **Themes/disagreements are built only from the verified grid**, not raw
   transcripts, so synthesis can't resurrect a claim that failed verification.
6. **Disagreement typing is explicit** (contradiction / emphasis / scope) and
   prompted with a worked example, so a scope difference (e.g. "15-20% in
   strong centres" vs. "not 20% across the whole market") isn't flattened into
   a false contradiction.
7. **The "Ask" feature refuses to answer** when BM25 retrieval doesn't clear a
   relevance floor, or when the model reports the retrieved sentences don't
   actually cover the question — it returns "Not covered in these calls."
   instead of guessing.

## Storage

Everything runs in-memory plus a single `cache.json` (see `core/cache.py`).
No database is used or needed at this scale — nothing to install, nothing to
migrate. `sqlite3` ships with Python's standard library if it's ever wanted,
and `sqlite-vec` is a small pip package for vector search, but neither is used
in this build.

## Scaling from 3 transcripts to 30+

This build's persistence and retrieval choices are intentionally the simplest
thing that works at 3-transcript scale. They don't need to be re-architected to
scale, only swapped:

- **Turns move into SQLite** (with the standard-library `sqlite3` module),
  using FTS5 for keyword search — replacing the in-memory turn list.
- **`sqlite-vec` adds semantic (embedding) retrieval** alongside FTS5/BM25 for
  true hybrid search, which matters more once queries need to match paraphrased
  or conceptually-related content rather than shared keywords.
- **Per-question retrieval instead of full-context prompts.** At 3 transcripts,
  each expert's full sentence list fits comfortably in context. At 30+, answer
  generation switches to retrieving only the top-k relevant sentences per
  question before prompting.
- **Themes/disagreements move to map-reduce.** Synthesise per-transcript (or
  per-batch) first, then reduce those partial syntheses into a final
  cross-expert result, rather than passing the entire verified grid in one
  prompt.

This is described here rather than built, since it isn't needed for the
3-transcript case — but every piece above is a drop-in replacement for a single
module (`parser.py`'s storage, `retrieval.py`'s index, `synthesis.py`'s prompt
strategy) rather than a redesign of the pipeline.

## Project structure

```
transcript_insight_app/
├── app.py                    # Streamlit entry point
├── config.py                  # paths, model settings, constants
├── requirements.txt
├── data/                        # default guide + transcripts
├── cache/cache.json              # generated on first run
├── models/
│   └── schemas.py                  # pydantic models (Turn, Sentence, Quote, AnswerCell, ...)
├── core/
│   ├── parser.py                     # files -> Turns/Sentences with stable IDs
│   ├── llm.py                          # local GGUF model wrapper (llama-cpp-python)
│   ├── verifier.py                       # sentence-ID -> verified Quote lookup
│   ├── answer_engine.py                    # per-question/per-expert generation
│   ├── synthesis.py                          # themes & disagreements
│   ├── retrieval.py                            # BM25 + Ask answering
│   ├── cache.py                                  # cache.json read/write
│   └── pipeline.py                                 # orchestrates the full run
├── ui/
│   ├── guide_answers.py     # Screen 1
│   ├── themes.py              # Screen 2
│   ├── ask.py                   # Screen 3
│   └── citation_viewer.py         # Screen 4
└── prompts/
    ├── answer_prompt.txt
    ├── synthesis_prompt.txt
    └── ask_prompt.txt
```

## Known limitations

- Quotes are extractive at sentence granularity — a mid-sentence fragment can't
  be pulled out. For these transcripts (1-3 sentences per turn) this is a
  non-issue, and it's a stronger claim in a demo: quotes are verbatim *by
  design*, not just by careful prompting.
- BM25 retrieval is keyword-based; a paraphrased question that shares no
  vocabulary with the transcript may under-retrieve. This is exactly what
  `sqlite-vec` addresses in the scaling path above.