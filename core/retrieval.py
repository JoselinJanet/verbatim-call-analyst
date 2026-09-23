import json
import re
from pathlib import Path
from typing import List, Optional

from rank_bm25 import BM25Okapi

from config import PROMPTS_DIR, TOP_K_RETRIEVAL, BM25_SCORE_MIN
from core.llm import generate_json, generate_text
from core.verifier import verify_sentence_ids
from models.schemas import Transcript, AskAnswer
from core.parser import all_sentences

_ASK_PROMPT_TEMPLATE = (PROMPTS_DIR / "ask_prompt.txt").read_text(encoding="utf-8")

_SYSTEM_PROMPT = (
    "You are a careful research assistant answering only from the transcript "
    "excerpts you are given. You only cite by sentence ID and never invent facts."
)

_GENERAL_CHAT_SYSTEM = (
    "You are a helpful assistant for a transcript analysis tool called Verbatim Call Analyst. "
    "You help users analyse expert interview transcripts. "
    "Answer conversationally and helpfully. When the user refers to something mentioned earlier "
    "(e.g. 'he said', 'that expert', 'it', 'this'), use the conversation history to understand what they mean. "
    "Keep replies concise. If the user asks a research question about transcripts, let them know they can "
    "type it in the Ask tab for a source-cited answer."
)

_GENERAL_PATTERNS = re.compile(
    r"^\s*(hi|hello|hey|howdy|good\s*(morning|afternoon|evening|day)|thanks?|thank\s+you|"
    r"ok|okay|great|sure|nice|cool|alright|got\s+it|understood|yes|no|yep|nope|"
    r"who\s+are\s+you|what\s+(can|do)\s+you\s+do|help(\s+me)?|what('s|\s+is)\s+(this|that|it))\b",
    re.IGNORECASE,
)


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def is_general_chat(question: str) -> bool:
    stripped = question.strip()
    if _GENERAL_PATTERNS.match(stripped):
        return True
    if len(stripped.split()) <= 4 and not any(
        kw in stripped.lower() for kw in ["transcript", "expert", "market", "surgery", "robot", "france", "germany", "uk"]
    ):
        return True
    return False


class BM25Index:
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
    hits = index.search(question)
    if not hits or hits[0][1] < BM25_SCORE_MIN:
        return []
    return hits


def _numbered_sentences_block(hits, transcripts_by_country_code: dict) -> str:
    lines = []
    for sent, _score in hits:
        lines.append(f"[{sent.id}] {sent.text}")
    return "\n".join(lines)


def answer_general(question: str, history: Optional[List[dict]] = None) -> str:
    messages = []
    if history:
        for msg in history[-6:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question})
    return generate_text(_GENERAL_CHAT_SYSTEM, messages)


def answer_question(
    question: str,
    index: BM25Index,
    transcripts: List[Transcript],
    lookup: dict,
    history: Optional[List[dict]] = None,
) -> AskAnswer:
    if is_general_chat(question):
        reply = answer_general(question, history)
        return AskAnswer(answer=reply, citations=[], covered=False)

    hits = retrieve(index, question)
    if not hits:
        if history:
            reply = answer_general(question, history)
            return AskAnswer(answer=reply, citations=[], covered=False)
        return AskAnswer(answer="Not covered in these calls.", citations=[], covered=False)

    numbered = _numbered_sentences_block(hits, {})

    context_block = ""
    if history:
        recent = [
            f"{m['role'].capitalize()}: {m['content']}"
            for m in history[-4:]
            if m.get("role") in ("user", "assistant") and m.get("content")
        ]
        if recent:
            context_block = "\n\nCONVERSATION HISTORY (for resolving references like 'he', 'it', 'that expert'):\n" + "\n".join(recent)

    prompt = (
        _ASK_PROMPT_TEMPLATE
        .replace("{question_text}", question)
        .replace("{numbered_sentences}", numbered)
    ) + context_block

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