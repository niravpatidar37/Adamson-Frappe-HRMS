"""Scorecard schema returned by the LLM scoring service (section 7.8)."""

from enum import StrEnum

from pydantic import BaseModel, Field


class Recommendation(StrEnum):
    STRONG_MATCH = "strong_match"
    REVIEW = "review"
    NOT_CURRENTLY_SHORTLISTED = "not_currently_shortlisted"


class MustHaveStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNCERTAIN = "uncertain"


class EvidenceItem(BaseModel):
    criterion: str
    status: str
    source: str


class Scorecard(BaseModel):
    score: int = Field(ge=0, le=100)
    recommendation: Recommendation
    must_have_status: MustHaveStatus
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    model_id: str
    prompt_version: str
