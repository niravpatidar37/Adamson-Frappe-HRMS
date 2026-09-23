from screening.schemas.candidate_profile import CandidateProfile, Experience, Skill
from screening.schemas.scoring_profile import ScoringProfile, build_scoring_profile


def test_scoring_profile_excludes_direct_identifiers_and_prohibited_fields() -> None:
    profile = CandidateProfile(
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone="+1-555-0100",
        skills=[Skill(name="Python")],
        experiences=[Experience(company="Analytical Engines Ltd", title="Engineer")],
        hobbies=["mathematics"],
    )

    scoring_profile = build_scoring_profile(
        application_id="app_1", tenant_id="tenant_1", job_id="job_1", profile=profile
    )

    dumped = scoring_profile.model_dump()
    for prohibited_field in ("first_name", "last_name", "email", "phone", "hobbies", "address"):
        assert prohibited_field not in dumped

    assert scoring_profile.skills == ["Python"]
    assert scoring_profile.employment_intervals[0].title == "Engineer"
    assert isinstance(scoring_profile, ScoringProfile)
