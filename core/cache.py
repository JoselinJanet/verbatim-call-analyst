"""
Lightweight persistence: a single cache.json holding the parsed
transcripts, guide questions, answer grid, and synthesis result, so
Streamlit reruns / restarts don't re-trigger LLM generation unless
the user explicitly asks to regenerate.

No SQLite is used here by design (see README) - it's unnecessary at
3-transcript scale and adds nothing but an install step.
"""
import json
from pathlib import Path
from typing import Optional

from config import CACHE_FILE
from models.schemas import AppState


def load_cache() -> Optional[AppState]:
    if not CACHE_FILE.exists():
        return None
    try:
        raw = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        return AppState.model_validate(raw)
    except Exception:
        return None  # corrupt/old cache -> treat as absent, caller regenerates


def save_cache(state: AppState) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(state.model_dump_json(indent=2), encoding="utf-8")


def clear_cache() -> None:
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()
