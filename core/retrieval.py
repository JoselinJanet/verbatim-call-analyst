"""
Stage 4 of the pipeline: free-form question answering.

Retrieval note: the install list settled on for this build is
rank_bm25 only (no embedding/vector library), so retrieval here is
BM25 keyword search over expert sentences. This is sufficient at the
3-transcript / ~45-sentence scale used in this case. The README's
scaling section describes adding sqlite-vec for semantic (embedding)
retrieval once the corpus grows past ~30 transcripts - that upgrade
is a drop-in replacement for this module's `retrieve()` function,
not a redesign of the pipeline around it.
"""
import json
import re
from pathlib import Path
from typing import List

from rank_bm25 import BM25Okapi

from config import PROMPTS_DIR, TOP_K_RETRIEVAL, BM25_SCORE_MIN
from core.llm import generate_json
from core.verifier import verify_sentence_ids
from models.schemas import Transcript, AskAnswer
from core.parser import all_sentences

_ASK_PROMPT_TEMPLATE = (PROMPTS_DIR / "ask_prompt.txt").read_text(encoding="utf-8")

_SYSTEM_PROMPT = (
    "You are a careful research assistant answering only from the transcript "
    "excerpts you are given. You only cite by sentence ID and never invent facts."
)


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class BM25Index:
    """Wraps rank_bm25 over the pool of quotable (expert-only) sentences."""

    def __init__(self, transcripts: List[Transcript]):
        self.sentences = all_sentences(transcripts, expert_only=True)
        corpus = [_tokenize(s.text) for s in self.sentences]
        self._bm25 = BM25Okapi(corpus) if corpus else None

    def search(self, query: str, top_k: int = TOP_K_RETRIEVAL):
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(zip(self.sentences, scores), key=lambda x: x[1], reverse=True)
        return [(s, score) for s, score in ranked[:top_k] if score > 0]


def retrieve(index: BM25Index, question: str):
    """Return top-k (sentence, score) hits, or [] if nothing clears the relevance floor."""
    hits = index.search(question)
    if not hits or hits[0][1] < BM25_SCORE_MIN:
        return []
    return hits


def _numbered_sentences_block(hits, transcripts_by_country_code: dict) -> str:
    lines = []
    for sent, _score in hits:
        lines.append(f"[{sent.id}] {sent.text}")
    return "\n".join(lines)


def answer_question(question: str, index: BM25Index, transcripts: List[Transcript], lookup: dict) -> AskAnswer:
    hits = retrieve(index, question)
    if not hits:
        return AskAnswer(answer="Not covered in these calls.", citations=[], covered=False)

    numbered = _numbered_sentences_block(hits, {})
    prompt = (
        _ASK_PROMPT_TEMPLATE
        .replace("{question_text}", question)
        .replace("{numbered_sentences}", numbered)
    )

    result = generate_json(_SYSTEM_PROMPT, prompt)
    if result is None:
        return AskAnswer(answer="Not covered in these calls.", citations=[], covered=False)

    covered = bool(result.get("covered", True))
    answer_text = str(result.get("answer", "")).strip() or "Not covered in these calls."
    raw_ids = result.get("sentence_ids", []) or []

    quotes, _rejected = verify_sentence_ids(raw_ids, lookup)

    if not covered or not quotes:
        return AskAnswer(answer="Not covered in these calls.", citations=[], covered=False)

    return AskAnswer(answer=answer_text, citations=quotes, covered=True)