"""
Orchestrates the full pipeline described in the flow diagram:
parse -> per-question/per-expert answers -> verify -> synthesize -> cache.

This is the single entry point the Streamlit UI calls; it hides the
stage-by-stage wiring of parser / answer_engine / synthesis / cache.
"""
from pathlib import Path
from typing import List

from core.parser import parse_guide, parse_all_transcripts, sentence_lookup
from core.answer_engine import build_answer_grid
from core.synthesis import synthesize
from core.cache import load_cache, save_cache
from core.relevance import check_relevance, IrrelevantContentError
from models.schemas import AppState


def run_pipeline(guide_path: Path, transcript_paths: List[Path], force_regenerate: bool = False, on_progress=None) -> AppState:
    """
    Runs (or loads from cache) the full analysis pipeline.
    Set force_regenerate=True to ignore any existing cache.json.
    on_progress: optional callback(done, total, label) forwarded to build_answer_grid,
    so the UI can show live progress instead of one silent spinner.

    Raises IrrelevantContentError before any LLM call happens if the uploaded
    transcripts don't share enough vocabulary with the guide questions to
    plausibly be answering them (see core/relevance.py).
    """
    if not force_regenerate:
        cached = load_cache()
        if cached is not None:
            return cached

    guide_questions = parse_guide(guide_path)
    transcripts = parse_all_transcripts(transcript_paths)

    is_relevant, ratio, message = check_relevance(guide_questions, transcripts)
    if not is_relevant:
        raise IrrelevantContentError(message)

    lookup = sentence_lookup(transcripts)

    answer_grid = build_answer_grid(guide_questions, transcripts, lookup, on_progress=on_progress)
    synthesis_result = synthesize(answer_grid, lookup)

    state = AppState(
        transcripts=transcripts,
        guide_questions=guide_questions,
        answer_grid=answer_grid,
        synthesis=synthesis_result,
    )
    save_cache(state)
    return state