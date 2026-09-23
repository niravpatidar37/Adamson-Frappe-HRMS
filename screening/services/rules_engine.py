"""Deterministic rules engine (system-design.md section 7.7).

Evaluates activated job criteria against a candidate profile before any
LLM scoring occurs. Implemented as plain, testable code rather than
hidden inside a prompt.

Outcomes are three-valued: FAIL is only ever emitted for an explicit,
high-confidence disqualifier. Anything derived from incomplete,
ambiguous, or probabilistic (parser-extracted) data resolves to
UNKNOWN and routes to human review rather than auto-rejection.
"""

import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum

from screening.schemas.candidate_profile import CandidateProfile
from screening.schemas.job_blueprint import CriterionType, JobBlueprint, MustHaveCriterion


class RuleOutcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


class ReasonCode(StrEnum):
    MET = "MET"
    NOT_MET = "NOT_MET"
    INCOMPLETE_DATE_RANGE = "INCOMPLETE_DATE_RANGE"
    SKILL_NOT_FOUND = "SKILL_NOT_FOUND"
    SKILL_MATCHED = "SKILL_MATCHED"
    CREDENTIAL_NOT_PRESENT_IN_RESUME = "CREDENTIAL_NOT_PRESENT_IN_RESUME"
    INSUFFICIENT_STRUCTURED_DATA = "INSUFFICIENT_STRUCTURED_DATA"


@dataclass(frozen=True, slots=True)
class RuleResult:
    """Immutable evidence bundle for a single evaluated rule."""

    rule_id: str
    criteria_version: int
    outcome: RuleOutcome
    reason_code: ReasonCode
    confidence: float
    evidence_refs: list[str] = field(default_factory=list)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class EligibilityResult:
    outcome: RuleOutcome
    results: list[RuleResult] = field(default_factory=list)

    @property
    def needs_review(self) -> bool:
        return self.outcome == RuleOutcome.UNKNOWN


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _years_of_experience(profile: CandidateProfile, today: date | None = None) -> float | None:
    today = today or datetime.now(UTC).date()
    total_days = 0
    has_complete_interval = False
    for exp in profile.experiences:
        if exp.start_date is None:
            continue
        has_complete_interval = True
        end = exp.end_date or today
        total_days += max((end - exp.start_date).days, 0)
    if not has_complete_interval:
        return None
    return round(total_days / 365.25, 2)


def _evaluate_criterion(
    profile: CandidateProfile, criterion: MustHaveCriterion, criteria_version: int
) -> RuleResult:
    rule_id = f"{_slugify(criterion.criterion)}_v{criteria_version}"

    if criterion.type == CriterionType.EXPERIENCE and criterion.minimum_years is not None:
        years = _years_of_experience(profile)
        if years is None:
            return RuleResult(
                rule_id=rule_id,
                criteria_version=criteria_version,
                outcome=RuleOutcome.UNKNOWN,
                reason_code=ReasonCode.INCOMPLETE_DATE_RANGE,
                confidence=0.5,
                evidence_refs=["profile.experiences"],
            )
        outcome = RuleOutcome.PASS if years >= criterion.minimum_years else RuleOutcome.FAIL
        reason = ReasonCode.MET if outcome == RuleOutcome.PASS else ReasonCode.NOT_MET
        return RuleResult(
            rule_id=rule_id,
            criteria_version=criteria_version,
            outcome=outcome,
            reason_code=reason,
            confidence=0.9,
            evidence_refs=["profile.experiences"],
        )

    if criterion.type == CriterionType.SKILL:
        skill_names = {s.name.lower() for s in profile.skills}
        matched = criterion.criterion.lower() in skill_names
        return RuleResult(
            rule_id=rule_id,
            criteria_version=criteria_version,
            outcome=RuleOutcome.PASS if matched else RuleOutcome.UNKNOWN,
            reason_code=ReasonCode.SKILL_MATCHED if matched else ReasonCode.SKILL_NOT_FOUND,
            confidence=0.9 if matched else 0.5,
            evidence_refs=["profile.skills"],
        )

    # Authorization/location/certification checks require structured
    # application fields not present on the parser profile alone; "not
    # present in resume" is not the same as "credential absent", so this
    # always routes to human review rather than a deterministic fail.
    return RuleResult(
        rule_id=rule_id,
        criteria_version=criteria_version,
        outcome=RuleOutcome.UNKNOWN,
        reason_code=ReasonCode.INSUFFICIENT_STRUCTURED_DATA,
        confidence=0.3,
        evidence_refs=[],
    )


def evaluate_eligibility(
    profile: CandidateProfile, blueprint: JobBlueprint, criteria_version: int | None = None
) -> EligibilityResult:
    version = criteria_version if criteria_version is not None else blueprint.version
    results = [
        _evaluate_criterion(profile, c, version) for c in blueprint.must_haves if c.required
    ]
    if any(r.outcome == RuleOutcome.FAIL for r in results):
        overall = RuleOutcome.FAIL
    elif any(r.outcome == RuleOutcome.UNKNOWN for r in results):
        overall = RuleOutcome.UNKNOWN
    else:
        overall = RuleOutcome.PASS
    return EligibilityResult(outcome=overall, results=results)
