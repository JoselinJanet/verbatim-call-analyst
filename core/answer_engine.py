"""
Stage 2 of the pipeline: for each (question, expert) pair, ask the LLM
for a short answer + supporting sentence IDs, verify those IDs in code,
and produce a verified AnswerCell.
"""
from pathlib import Path
from typing import List

from config import PROMPTS_DIR, STATUS_VALUES
from core.llm import generate_json
from core.verifier import verify_sentence_ids
from models.schemas import Transcript, GuideQuestion, AnswerCell

_ANSWER_PROMPT_TEMPLATE = (PROMPTS_DIR / "answer_prompt.txt").read_text(encoding="utf-8")

_SYSTEM_PROMPT = (
    "You are a careful research assistant. You only ever cite by sentence ID. "
    "You never invent facts, quotes, or timestamps."
)


def _numbered_sentences_block(transcript: Transcript) -> str:
    lines = []
    for turn in transcript.turns:
        if not turn.is_expert:
            continue
        for sent in turn.sentences:
            lines.append(f"[{sent.id}] {sent.text}")
    return "\n".join(lines)


def generate_answer_cell(
    question: GuideQuestion,
    transcript: Transcript,
    lookup: dict,
) -> AnswerCell:
    """Generate and verify one grid cell (one question, one expert)."""
    numbered_sentences = _numbered_sentences_block(transcript)

    prompt = (
        _ANSWER_PROMPT_TEMPLATE
        .replace("{question_text}", question.text)
        .replace("{expert_name}", transcript.expert_name)
        .replace("{country}", transcript.country)
        .replace("{numbered_sentences}", numbered_sentences)
    )

    result = generate_json(_SYSTEM_PROMPT, prompt)

    if result is None:
        return AnswerCell(
            question_number=question.number,
            country=transcript.country,
            expert_name=transcript.expert_name,
            short_answer="(Generation failed - flagged for manual review)",
            status="not_discussed",
            quotes=[],
            generation_failed=True,
        )

    short_answer = str(result.get("short_answer", "")).strip()
    status = result.get("status", "not_discussed")
    if status not in STATUS_VALUES:
        status = "partial"
    raw_sentence_ids = result.get("sentence_ids", []) or []

    verified_quotes, rejected_ids = verify_sentence_ids(raw_sentence_ids, lookup)

    if not verified_quotes and status == "answered":
        status = "partial"

    return AnswerCell(
        question_number=question.number,
        country=transcript.country,
        expert_name=transcript.expert_name,
        short_answer=short_answer or "(No answer text returned)",
        status=status,
        quotes=verified_quotes[:3],
        generation_failed=False,
    )


def build_answer_grid(
    questions: List[GuideQuestion],
    transcripts: List[Transcript],
    lookup: dict,
    on_progress=None,
) -> List[AnswerCell]:
    """
    Build the full 6-questions x 3-experts grid.

    on_progress: optional callback(done: int, total: int, label: str),
    called after each cell so the caller (e.g. Streamlit) can show a
    live progress bar instead of one silent spinner for the whole run.
    """
    grid: List[AnswerCell] = []
    total = len(questions) * len(transcripts)
    done = 0
    for question in questions:
        for transcript in transcripts:
            cell = generate_answer_cell(question, transcript, lookup)
            grid.append(cell)
            done += 1
            if on_progress:
                on_progress(done, total, f"Q{question.number} — {transcript.country}")
    return grid