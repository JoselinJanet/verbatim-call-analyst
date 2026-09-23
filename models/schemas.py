"""
Data models for the Transcript Insight app.

Design principle: the LLM is only ever allowed to produce free-text
(short answers, theme prose) and *sentence IDs*. Verbatim quote text
and timestamps always come from these structures, populated directly
from the parsed transcript files, never from the model.
"""
from __future__ import annotations
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class Sentence(BaseModel):
    """A single quotable (or context-only) sentence inside a turn."""
    id: str                 # e.g. "FR-02-s1"
    turn_id: str             # e.g. "FR-02"
    text: str                # verbatim sentence text
    is_expert: bool           # False for interviewer sentences (not quotable)


class Turn(BaseModel):
    """One speaker turn in a transcript, tagged with metadata."""
    id: str                  # e.g. "FR-02"
    call: str                 # transcript filename / call label
    country: str               # "France", "Germany", "United Kingdom"
    country_code: str           # "FR", "DE", "UK"
    expert_name: str
    expert_role: str
    timestamp: str                # "00:18"
    speaker: str                    # "Dr. Martin" or "Interviewer"
    text: str                        # full turn text (verbatim)
    is_expert: bool                   # False for interviewer turns
    sentences: List[Sentence] = Field(default_factory=list)


class Transcript(BaseModel):
    country: str
    country_code: str
    expert_name: str
    expert_role: str
    call: str
    turns: List[Turn]


class GuideQuestion(BaseModel):
    number: int
    text: str


class Quote(BaseModel):
    sentence_id: str
    turn_id: str
    text: str
    timestamp: str
    country: str
    verified: bool = True


class AnswerCell(BaseModel):
    """One cell in the Guide Answers grid: (question, expert)."""
    question_number: int
    country: str
    expert_name: str
    short_answer: str
    status: Literal["answered", "partial", "not_discussed"]
    quotes: List[Quote] = Field(default_factory=list)
    generation_failed: bool = False


class Theme(BaseModel):
    title: str
    description: str
    supporting_quotes: List[Quote] = Field(default_factory=list)
    countries: List[str] = Field(default_factory=list)


class Disagreement(BaseModel):
    title: str
    type: Literal["contradiction", "emphasis", "scope"]
    description: str
    quotes_by_country: List[Quote] = Field(default_factory=list)
    needs_review: bool = False


class SynthesisResult(BaseModel):
    themes: List[Theme] = Field(default_factory=list)
    disagreements: List[Disagreement] = Field(default_factory=list)


class AskAnswer(BaseModel):
    answer: str
    citations: List[Quote] = Field(default_factory=list)
    covered: bool = True


class AppState(BaseModel):
    """Everything persisted to cache.json between runs."""
    transcripts: List[Transcript] = Field(default_factory=list)
    guide_questions: List[GuideQuestion] = Field(default_factory=list)
    answer_grid: List[AnswerCell] = Field(default_factory=list)
    synthesis: Optional[SynthesisResult] = None