"""
Lightweight relevance guard.

Runs in milliseconds, right after parsing, BEFORE the slow/expensive LLM
pipeline starts. It is NOT an AI check - it's a fast keyword-overlap check
between the guide questions and the transcript content, purely to catch
obviously mismatched uploads (e.g. movie trivia uploaded instead of
interview transcripts) before burning minutes of LLM time generating a
grid full of "not_discussed" cells against irrelevant content.

This deliberately stays simple: it is a guard rail, not a topic classifier.
It will not catch subtly-off-topic content, and it can be fooled by content
that happens to share vocabulary. That's an acceptable trade-off for a
check that costs ~0ms and runs before every single expensive pipeline run.
"""
import re
from typing import List, Tuple

from models.schemas import GuideQuestion, Transcript

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "be",
    "been", "being", "to", "of", "in", "on", "for", "with", "as", "by", "at",
    "from", "that", "this", "these", "those", "it", "its", "you", "your",
    "how", "what", "would", "do", "does", "did", "about", "over", "next",
    "current", "describe", "important", "main", "typical", "between",
    "could", "should", "their", "they", "them", "i", "we", "our", "us",
}

MIN_OVERLAP_RATIO = 0.12  # below this, treat the upload as likely off-topic


class IrrelevantContentError(Exception):
    """Raised when uploaded transcripts don't plausibly relate to the guide questions."""
    pass


def _keywords(text: str) -> set:
    words = re.findall(r"[a-z]{3,}", text.lower())
    return {w for w in words if w not in _STOPWORDS}


def check_relevance(
    guide_questions: List[GuideQuestion],
    transcripts: List[Transcript],
) -> Tuple[bool, float, str]:
    """
    Returns (is_relevant, overlap_ratio, message).

    is_relevant=False means too few of the guide question's keywords appear
    anywhere in the uploaded transcripts for them to plausibly be answering
    those questions.
    """
    question_words: set = set()
    for q in guide_questions:
        question_words |= _keywords(q.text)

    transcript_words: set = set()
    for t in transcripts:
        for turn in t.turns:
            if turn.is_expert:
                transcript_words |= _keywords(turn.text)

    if not question_words:
        return True, 1.0, "No guide keywords to check against; skipping relevance check."

    overlap = question_words & transcript_words
    ratio = len(overlap) / len(question_words)

    if ratio < MIN_OVERLAP_RATIO:
        message = (
            f"Only {len(overlap)}/{len(question_words)} guide keywords "
            f"({ratio:.0%}) appear anywhere in the uploaded transcripts. "
            "This usually means the uploaded transcripts don't relate to the "
            "uploaded interview guide - e.g. the wrong files were uploaded, "
            "or the content is off-topic (movie trivia, unrelated meeting notes, etc.). "
            "Double-check your uploads before regenerating."
        )
        return False, ratio, message

    return True, ratio, f"Relevance check passed ({ratio:.0%} guide-keyword overlap found in transcripts)."