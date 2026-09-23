from __future__ import annotations
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class Sentence(BaseModel):
    id: str
    turn_id: str
    text: str
    is_expert: bool


class Turn(BaseModel):
    id: str
    call: str
    country: str
    country_code: str
    expert_name: str
    expert_role: str
    timestamp: str
    speaker: str
    text: str
    is_expert: bool
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
    transcripts: List[Transcript] = Field(default_factory=list)
    guide_questions: List[GuideQuestion] = Field(default_factory=list)
    answer_grid: List[AnswerCell] = Field(default_factory=list)
    synthesis: Optional[SynthesisResult] = None