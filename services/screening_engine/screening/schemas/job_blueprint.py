"""Job blueprint schema (system-design.md section 7.6).

Criteria are authored by a human. `draft_blueprint_from_description` only
proposes them; what a recruiter actually submits is what binds. Every
criterion string is screened against `disallowed_features` before it can be
stored, because a free-text requirement is exactly where a protected
characteristic enters a screening system.
"""

import re
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from screening.core.exceptions import ValidationFailedError


class CriterionType(StrEnum):
    SKILL = "skill"
    EXPERIENCE = "experience"
    CERTIFICATION = "certification"
    AUTHORIZATION = "authorization"
    LOCATION = "location"
    OTHER = "other"


class MustHaveCriterion(BaseModel):
    criterion: str
    type: CriterionType
    required: bool = True
    minimum_years: float | None = None


class ScoringWeights(BaseModel):
    required: float
    relevant_experience: float
    nice_to_have: float
    evidence_quality: float


DEFAULT_SCORING_WEIGHTS = ScoringWeights(
    required=0.55, relevant_experience=0.25, nice_to_have=0.15, evidence_quality=0.05
)


DISALLOWED_FEATURES_DEFAULT = (
    "age",
    "gender",
    "race",
    "ethnicity",
    "religion",
    "disability",
    "marital_status",
)

# Patterns that signal a protected characteristic or a common proxy.
#
# A guard rail, not a compliance control: it catches the obvious cases and
# leaves judgement to human review. Deliberately tuned to avoid false
# positives, because a filter that blocks legitimate postings gets switched
# off. Bare "white"/"black" are excluded ("black box testing"), as are
# "single" ("single sign-on"), "he"/"she", and "children" (legitimate in
# childcare and education roles).
_DISALLOWED_PATTERNS: dict[str, tuple[str, ...]] = {
    "age": (
        r"\bages?\b",
        r"\baged\b",
        r"\byoung(?:er|est)?\b",
        r"\byouthful\b",
        r"\bolder\b",
        r"\brecent grad(?:uate)?s?\b",
        r"\bdigital native\b",
        r"\bborn (?:after|before)\b",
        r"\bage (?:limit|range|requirement)\b",
        r"\bmax(?:imum)? age\b",
        r"\b\d{1,2}\s*years?\s*old\b",
        # "under 40" is an age bound; "over 10 years" and "under 40 hours"
        # are not, so units that make it something else are excluded.
        (
            r"\b(?:under|over|below|above|younger than|older than|no older than|"
            r"no younger than)\s+\d{1,2}\b"
            r"(?!\s*(?:years?|yrs?|months?|mos?|hours?|hrs?|days?|weeks?|"
            r"percent|%|k\b|people|candidates|applicants|users|clients))"
        ),
    ),
    "gender": (
        r"\bgenders?\b",
        r"\b(?:fe)?male\b",
        r"\b(?:wo)?man\b",
        r"\b(?:wo)?men\b",
        r"\bsales(?:man|woman)\b",
    ),
    "race": (
        r"\braces?\b",
        r"\bracial\b",
        r"\bcaucasian\b",
        r"\basian\b",
        r"\bhispanic\b",
        r"\blatin[oax]\b",
        r"\bskin colou?r\b",
    ),
    "ethnicity": (
        r"\bethnic(?:ity)?\b",
        r"\bnational origin\b",
        r"\bnationality\b",
    ),
    "religion": (
        r"\breligious?\b",
        r"\bchristian\b",
        r"\bmuslim\b",
        r"\bjewish\b",
        r"\bhindu\b",
        r"\bsikh\b",
        r"\bbuddhist\b",
        r"\batheist\b",
        r"\bchurch\b",
        r"\bmosque\b",
        r"\bsynagogue\b",
    ),
    "disability": (
        r"\bdisabilit(?:y|ies)\b",
        r"\bdisabled\b",
        r"\bhandicapp?(?:ed)?\b",
        r"\bable.bodied\b",
        r"\bneurotypical\b",
    ),
    "marital_status": (
        r"\bmarital\b",
        r"\bmarried\b",
        r"\bdivorced\b",
        r"\bwidowed\b",
        r"\bspouse\b",
        r"\bpregnan(?:t|cy)\b",
        r"\bfamily status\b",
        r"\bno children\b",
        r"\bchildcare (?:commitments?|responsibilit(?:y|ies)|arrangements?)\b",
    ),
}


def find_disallowed_feature(text: str) -> tuple[str, str] | None:
    """Return (feature, matched text) when text names a disallowed feature."""
    lowered = text.lower()
    for feature, patterns in _DISALLOWED_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if match is not None:
                return feature, match.group(0)
    return None


def reject_disallowed_features(values: list[str], *, field_name: str) -> None:
    """Raise if any entry names a protected characteristic.

    Fails the whole submission rather than silently dropping the offending
    line: a recruiter must see that the criterion was refused and why.
    """
    for value in values:
        hit = find_disallowed_feature(value)
        if hit is not None:
            feature, term = hit
            raise ValidationFailedError(
                f"{field_name} entry {value!r} refers to {feature} "
                f"(matched {term!r}), which may not be used as a screening criterion"
            )


class JobBlueprint(BaseModel):
    role_id: str
    version: int
    must_haves: list[MustHaveCriterion] = Field(default_factory=list)
    nice_to_haves: list[str] = Field(default_factory=list)
    # Requirements that are not skills, experience or credentials: shift
    # patterns, travel, on-call, security clearance. Structured as a list
    # rather than prose so each entry is individually reviewable.
    other_requirements: list[str] = Field(default_factory=list)
    disallowed_features: tuple[str, ...] = DISALLOWED_FEATURES_DEFAULT
    weights: ScoringWeights
    approved_by: str | None = None
    approved_at: str | None = None

    @field_validator("nice_to_haves", "other_requirements")
    @classmethod
    def _screen_free_text(cls, value: list[str]) -> list[str]:
        reject_disallowed_features(value, field_name="criterion")
        return value

    @field_validator("must_haves")
    @classmethod
    def _screen_must_haves(cls, value: list[MustHaveCriterion]) -> list[MustHaveCriterion]:
        reject_disallowed_features([c.criterion for c in value], field_name="must-have")
        return value
