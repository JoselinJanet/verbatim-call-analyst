"""
Stage 3 of the pipeline: synthesise cross-expert themes and disagreements
from the VERIFIED answer grid only (never from raw transcripts directly),
so synthesis can't introduce facts that didn't survive verification.
"""
import json
from pathlib import Path
from typing import List

from config import PROMPTS_DIR, DISAGREEMENT_TYPES
from core.llm import generate_json
from core.verifier import verify_sentence_ids
from models.schemas import AnswerCell, Theme, Disagreement, SynthesisResult

_SYNTH_PROMPT_TEMPLATE = (PROMPTS_DIR / "synthesis_prompt.txt").read_text(encoding="utf-8")

_SYSTEM_PROMPT = (
    "You are a careful research analyst synthesising verified interview findings. "
    "You only cite by sentence ID and never invent facts."
)


def _grid_to_payload(grid: List[AnswerCell]) -> list:
    """Serialize the verified grid (with each cell's available sentence IDs) for the prompt."""
    payload = []
    for cell in grid:
        if cell.generation_failed:
            continue
        payload.append({
            "question_number": cell.question_number,
            "country": cell.country,
            "expert": cell.expert_name,
            "short_answer": cell.short_answer,
            "status": cell.status,
            "available_sentence_ids": [q.sentence_id for q in cell.quotes],
        })
    return payload


def synthesize(grid: List[AnswerCell], lookup: dict) -> SynthesisResult:
    payload = _grid_to_payload(grid)
    prompt = _SYNTH_PROMPT_TEMPLATE.replace(
        "{verified_answers_json}", json.dumps(payload, indent=2)
    )

    result = generate_json(_SYSTEM_PROMPT, prompt, max_tokens=2000)
    if result is None:
        return SynthesisResult(themes=[], disagreements=[])

    themes: List[Theme] = []
    for raw_theme in result.get("themes", []) or []:
        quotes, _rejected = verify_sentence_ids(raw_theme.get("sentence_ids", []) or [], lookup)
        if not quotes:
            continue  # no verifiable evidence -> drop the theme rather than show it unsupported
        themes.append(
            Theme(
                title=raw_theme.get("title", "").strip(),
                description=raw_theme.get("description", "").strip(),
                supporting_quotes=quotes,
                countries=raw_theme.get("countries", []) or [],
            )
        )

    disagreements: List[Disagreement] = []
    for raw_dis in result.get("disagreements", []) or []:
        quotes, _rejected = verify_sentence_ids(raw_dis.get("sentence_ids", []) or [], lookup)
        dtype = raw_dis.get("type", "emphasis")
        needs_review = dtype not in DISAGREEMENT_TYPES
        if needs_review:
            dtype = "emphasis"
        if not quotes:
            continue
        disagreements.append(
            Disagreement(
                title=raw_dis.get("title", "").strip(),
                type=dtype,
                description=raw_dis.get("description", "").strip(),
                quotes_by_country=quotes,
                needs_review=needs_review,
            )
        )

    return SynthesisResult(themes=themes, disagreements=disagreements)