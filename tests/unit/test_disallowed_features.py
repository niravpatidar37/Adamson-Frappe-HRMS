"""Disallowed-feature screening for recruiter-authored criteria.

Ported from HR-Screening. The API-level tests were left behind with FastAPI;
this is the guard itself, which is where the logic lives.
"""

import pytest

from screening.core.exceptions import ValidationFailedError
from screening.schemas.job_blueprint import (
    CriterionType,
    JobBlueprint,
    MustHaveCriterion,
    ScoringWeights,
    find_disallowed_feature,
)

_WEIGHTS = ScoringWeights(
    required=0.55, relevant_experience=0.25, nice_to_have=0.15, evidence_quality=0.05
)


# --- disallowed features ----------------------------------------------------

@pytest.mark.parametrize(
    "text,feature",
    [
        ("Must be under 40", "age"),
        ("Recent graduate preferred", "age"),
        ("Looking for a young team player", "age"),
        ("Salesman with 5 years experience", "gender"),
        ("Must be married", "marital_status"),
        ("No childcare commitments", "marital_status"),
        ("Christian values important", "religion"),
        ("Able-bodied candidates only", "disability"),
    ],
)
def test_disallowed_features_are_detected(text: str, feature: str) -> None:
    hit = find_disallowed_feature(text)
    assert hit is not None and hit[0] == feature


@pytest.mark.parametrize(
    "text",
    [
        "5 years of Python experience",
        "Willing to travel occasionally",
        "Security clearance required",
        "Comfortable with on-call rotation",
        # Each of these contains a substring that a naive word list would
        # flag. The filter has to be usable, or it gets switched off.
        "Experience managing ageing infrastructure",   # 'ageing', not 'age'
        "Over 10 years of backend experience",         # a duration, not an age
        "Under 40 hours per week",                     # hours, not an age
        "Black box testing experience",                # not race
        "Single sign-on integration experience",       # not marital status
        "Experience working with children",            # legitimate for care roles
        "Manages a team of 12 people",
    ],
)
def test_legitimate_requirements_are_not_flagged(text: str) -> None:
    assert find_disallowed_feature(text) is None


def test_blueprint_rejects_a_disallowed_must_have() -> None:
    with pytest.raises(ValidationFailedError):
        JobBlueprint(
            role_id="r", version=1, weights=_WEIGHTS,
            must_haves=[MustHaveCriterion(criterion="Under 30", type=CriterionType.OTHER)],
        )


def test_blueprint_rejects_a_disallowed_other_requirement() -> None:
    with pytest.raises(ValidationFailedError):
        JobBlueprint(role_id="r", version=1, weights=_WEIGHTS,
                     other_requirements=["No pregnant applicants"])
