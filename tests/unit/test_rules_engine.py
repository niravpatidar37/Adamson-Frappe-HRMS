from datetime import date

from screening.schemas.candidate_profile import CandidateProfile, Experience, Skill
from screening.schemas.job_blueprint import (
    CriterionType,
    JobBlueprint,
    MustHaveCriterion,
    ScoringWeights,
)
from screening.services.rules_engine import RuleOutcome, evaluate_eligibility


def _blueprint(**must_have_kwargs) -> JobBlueprint:
    return JobBlueprint(
        role_id="role_1",
        version=1,
        must_haves=[MustHaveCriterion(**must_have_kwargs)],
        weights=ScoringWeights(
            required=0.55, relevant_experience=0.25, nice_to_have=0.15, evidence_quality=0.05
        ),
    )


def test_experience_criterion_passes_when_years_met() -> None:
    profile = CandidateProfile(
        experiences=[
            Experience(
                company="Example Co.",
                start_date=date(2018, 1, 1),
                end_date=date(2023, 1, 1),
            )
        ]
    )
    blueprint = _blueprint(
        criterion="backend development", type=CriterionType.EXPERIENCE, minimum_years=3
    )
    result = evaluate_eligibility(profile, blueprint)
    assert result.outcome == RuleOutcome.PASS
    assert result.needs_review is False


def test_skill_criterion_routes_to_review_when_missing() -> None:
    profile = CandidateProfile(skills=[Skill(name="Java")])
    blueprint = _blueprint(criterion="Python", type=CriterionType.SKILL)
    result = evaluate_eligibility(profile, blueprint)
    # Absence of a skill in the resume is not proof of absence, so this is
    # UNKNOWN (review), never an automatic FAIL.
    assert result.outcome == RuleOutcome.UNKNOWN
    assert result.needs_review is True


def test_authorization_criterion_routes_to_review() -> None:
    profile = CandidateProfile()
    blueprint = _blueprint(criterion="Work authorization", type=CriterionType.AUTHORIZATION)
    result = evaluate_eligibility(profile, blueprint)
    assert result.outcome == RuleOutcome.UNKNOWN
    assert result.needs_review is True


def test_incomplete_experience_dates_route_to_review_not_fail() -> None:
    profile = CandidateProfile(experiences=[Experience(company="Example Co.")])
    blueprint = _blueprint(
        criterion="backend development", type=CriterionType.EXPERIENCE, minimum_years=3
    )
    result = evaluate_eligibility(profile, blueprint)
    assert result.outcome == RuleOutcome.UNKNOWN


def test_experience_below_minimum_fails() -> None:
    profile = CandidateProfile(
        experiences=[
            Experience(
                company="Example Co.",
                start_date=date(2023, 1, 1),
                end_date=date(2023, 6, 1),
            )
        ]
    )
    blueprint = _blueprint(
        criterion="backend development", type=CriterionType.EXPERIENCE, minimum_years=3
    )
    result = evaluate_eligibility(profile, blueprint)
    assert result.outcome == RuleOutcome.FAIL

