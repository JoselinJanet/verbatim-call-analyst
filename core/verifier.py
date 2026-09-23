"""
Code-side verification layer.

This is the anti-hallucination backbone of the app: the LLM only ever
proposes sentence IDs. This module is the sole place allowed to turn an
ID into an actual quote, by looking up the verbatim text and timestamp
from the parsed transcripts. Any ID that doesn't exist, or that points
at an interviewer sentence, is rejected outright.
"""
from typing import List, Tuple
from models.schemas import Quote


def verify_sentence_ids(sentence_ids: List[str], lookup: dict) -> Tuple[List[Quote], List[str]]:
    """
    Given a list of sentence IDs proposed by the LLM and the
    {sentence_id: (Sentence, Turn, Transcript)} lookup built by the parser,
    return (verified_quotes, rejected_ids).

    A sentence ID is rejected if:
      - it does not exist in the parsed transcripts, or
      - it resolves to a non-expert (interviewer) sentence.
    """
    verified: List[Quote] = []
    rejected: List[str] = []

    for sid in sentence_ids:
        entry = lookup.get(sid)
        if entry is None:
            rejected.append(sid)
            continue
        sentence, turn, transcript = entry
        if not sentence.is_expert:
            rejected.append(sid)
            continue
        verified.append(
            Quote(
                sentence_id=sentence.id,
                turn_id=turn.id,
                text=sentence.text,          # verbatim, from the parsed file
                timestamp=turn.timestamp,     # verbatim, from the parsed file
                country=transcript.country,
                verified=True,
            )
        )

    return verified, rejected