"""
Parses the interview guide and transcript .txt files into structured objects.

Transcript file shape (as given in the case):

    Expert 1 – Dr. Jean Martin
    Role: Head of Urology
    Market: France

    00:00
    Interviewer: Thanks for joining...

    00:18
    Dr. Martin: Adoption is growing...

Rules:
- A block is: a timestamp line (MM:SS) followed by one "Speaker: text" line
  (text may itself contain multiple sentences).
- Any speaker literally named "Interviewer" is marked is_expert=False.
  Every other speaker in the file is treated as the expert being interviewed.
- Turn IDs are sequential across the WHOLE transcript (interviewer included),
  using the country code prefix, e.g. FR-01, FR-02, FR-03 ...
  This matches the numbering used during design (Dr. Martin's 00:18 line = FR-02).
- Sentences are only extracted (and only given IDs) for expert turns.
  Interviewer sentences are never quotable.
"""
import re
from pathlib import Path
from typing import List

from config import COUNTRY_CODES
from models.schemas import Turn, Sentence, Transcript, GuideQuestion

TIMESTAMP_RE = re.compile(r"^(\d{1,2}:\d{2})$")
HEADER_MARKET_RE = re.compile(r"^Market:\s*(.+)$", re.IGNORECASE)
HEADER_ROLE_RE = re.compile(r"^Role:\s*(.+)$", re.IGNORECASE)
HEADER_EXPERT_RE = re.compile(r"^Expert\s+\d+\s*[–-]\s*(.+)$", re.IGNORECASE)
SPEAKER_LINE_RE = re.compile(r"^([^:]+):\s*(.+)$")

# naive but adequate sentence splitter for short, clean interview sentences
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def _country_code(country: str) -> str:
    return COUNTRY_CODES.get(country.strip(), country.strip()[:2].upper())


def parse_guide(path: Path) -> List[GuideQuestion]:
    """Extract numbered questions from the interview guide file."""
    text = Path(path).read_text(encoding="utf-8")
    questions = []
    # matches lines like "1. How would you describe..."
    pattern = re.compile(r"^\s*(\d+)\.\s+(.*\S)\s*$", re.MULTILINE)
    for match in pattern.finditer(text):
        num = int(match.group(1))
        q_text = match.group(2).strip()
        questions.append(GuideQuestion(number=num, text=q_text))
    if not questions:
        raise ValueError(f"No numbered questions found in guide file: {path}")
    return sorted(questions, key=lambda q: q.number)


def parse_transcript(path: Path) -> Transcript:
    """Parse one transcript .txt file into a Transcript of Turns/Sentences."""
    raw_lines = [l.rstrip() for l in Path(path).read_text(encoding="utf-8").splitlines()]
    lines = [l for l in raw_lines]  # keep blank lines as separators, filter below

    expert_name = None
    expert_role = None
    country = None

    i = 0
    # ---- parse header block (first few non-blank lines) ----
    while i < len(lines):
        if expert_name and expert_role and country:
            break
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        m_expert = HEADER_EXPERT_RE.match(line)
        m_role = HEADER_ROLE_RE.match(line)
        m_market = HEADER_MARKET_RE.match(line)
        if m_expert:
            expert_name = m_expert.group(1).strip()
        elif m_role:
            expert_role = m_role.group(1).strip()
        elif m_market:
            country = m_market.group(1).strip()
        else:
            # header section ended (hit the first timestamp or dialogue)
            if TIMESTAMP_RE.match(line):
                break
        i += 1

    if not (expert_name and expert_role and country):
        raise ValueError(f"Could not parse header (Expert/Role/Market) from {path}")

    country_code = _country_code(country)
    call_label = Path(path).stem

    # ---- parse timestamp/speaker blocks ----
    turns: List[Turn] = []
    turn_counter = 0
    n = len(lines)
    while i < n:
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        ts_match = TIMESTAMP_RE.match(line)
        if not ts_match:
            i += 1
            continue
        timestamp = ts_match.group(1)
        i += 1
        # collect following non-blank lines until next timestamp or EOF as the turn text
        text_parts = []
        speaker = None
        while i < n:
            nxt = lines[i].strip()
            if not nxt:
                i += 1
                continue
            if TIMESTAMP_RE.match(nxt):
                break
            speaker_match = SPEAKER_LINE_RE.match(nxt)
            if speaker_match and speaker is None:
                speaker = speaker_match.group(1).strip()
                text_parts.append(speaker_match.group(2).strip())
            else:
                text_parts.append(nxt)
            i += 1
        if speaker is None:
            continue  # malformed block, skip defensively

        turn_counter += 1
        turn_id = f"{country_code}-{turn_counter:02d}"
        full_text = " ".join(text_parts).strip()
        is_expert = speaker.strip().lower() != "interviewer"

        sentences: List[Sentence] = []
        if is_expert and full_text:
            raw_sentences = SENTENCE_SPLIT_RE.split(full_text)
            for s_idx, sent in enumerate(raw_sentences, start=1):
                sent = sent.strip()
                if not sent:
                    continue
                sentences.append(
                    Sentence(
                        id=f"{turn_id}-s{s_idx}",
                        turn_id=turn_id,
                        text=sent,
                        is_expert=True,
                    )
                )

        turns.append(
            Turn(
                id=turn_id,
                call=call_label,
                country=country,
                country_code=country_code,
                expert_name=expert_name,
                expert_role=expert_role,
                timestamp=timestamp,
                speaker=speaker,
                text=full_text,
                is_expert=is_expert,
                sentences=sentences,
            )
        )

    if not turns:
        raise ValueError(f"No turns parsed from {path}. Check file formatting.")

    return Transcript(
        country=country,
        country_code=country_code,
        expert_name=expert_name,
        expert_role=expert_role,
        call=call_label,
        turns=turns,
    )


def parse_all_transcripts(paths: List[Path]) -> List[Transcript]:
    return [parse_transcript(p) for p in paths]


def all_sentences(transcripts: List[Transcript], expert_only: bool = True) -> List[Sentence]:
    """Flatten sentences across transcripts, optionally filtering to expert-only."""
    out: List[Sentence] = []
    for t in transcripts:
        for turn in t.turns:
            if expert_only and not turn.is_expert:
                continue
            out.extend(turn.sentences)
    return out


def sentence_lookup(transcripts: List[Transcript]) -> dict:
    """Build a {sentence_id: (Sentence, Turn, Transcript)} map for O(1) verification lookups."""
    lookup = {}
    for t in transcripts:
        for turn in t.turns:
            for sent in turn.sentences:
                lookup[sent.id] = (sent, turn, t)
    return lookup