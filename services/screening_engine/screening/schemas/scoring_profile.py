"""Scoring-safe projection of a candidate profile.

This is the data-minimization boundary described in system-design.md
section 12: only this projection may reach the scoring model, semantic
embeddings, or search ranking. Direct identifiers (name, email, phone)
and prohibited features (DOB, address, hobbies, and any protected-
characteristic proxies) must never be added to this type.
"""

from typing import Literal

from pydantic import BaseModel, Field

from screening.schemas.candidate_profile import CandidateProfile


class ScoringEvidenceItem(BaseModel):
    source_ref: str
    text_excerpt: str = Field(max_length=500)
    confidence: float = Field(ge=0.0, le=1.0)


class EmploymentInterval(BaseModel):
    title: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class ScoringProfile(BaseModel):
    application_id: str
    tenant_id: str
    job_id: str
    skills: list[str] = Field(default_factory=list)
    verified_certifications: list[str] = Field(default_factory=list)
    employment_intervals: list[EmploymentInterval] = Field(default_factory=list)
    work_authorization_status: Literal["eligible", "ineligible", "unknown"] = "unknown"
    location_eligibility: Literal["eligible", "ineligible", "unknown"] = "unknown"
    evidence: list[ScoringEvidenceItem] = Field(default_factory=list)


def build_scoring_profile(
    *,
    application_id: str,
    tenant_id: str,
    job_id: str,
    profile: CandidateProfile,
    work_authorization_status: Literal["eligible", "ineligible", "unknown"] = "unknown",
    location_eligibility: Literal["eligible", "ineligible", "unknown"] = "unknown",
) -> ScoringProfile:
    """Deterministic transformation from the full parser profile to the
    scoring-safe projection. This function, not a model, decides what is
    excluded: no name, contact info, date of birth, address, or hobbies.
    """
    return ScoringProfile(
        application_id=application_id,
        tenant_id=tenant_id,
        job_id=job_id,
        skills=[s.name for s in profile.skills],
        verified_certifications=[c.name for c in profile.certificates],
        employment_intervals=[
            EmploymentInterval(
                title=e.title,
                start_date=e.start_date.isoformat() if e.start_date else None,
                end_date=e.end_date.isoformat() if e.end_date else None,
            )
            for e in profile.experiences
        ],
        work_authorization_status=work_authorization_status,
        location_eligibility=location_eligibility,
    )
