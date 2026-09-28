"""Knockout result from an applicant's own declared answers.

No frappe import: this is the only decision logic in v1 and it is unit-tested
without a site (tests/unit/test_knockout_rules.py).

Nothing here rejects anyone. A declared "No" only moves the applicant into a
list the recruiter confirms by hand. A missing answer is never read as "No".
"""

ELIGIBLE = "Eligible"
UNANSWERED = "Unanswered"
DECLARED_INELIGIBLE = "Declared Ineligible"

# Requirement field on Job Opening -> answer field on Job Applicant. The five
# vetted question types (design doc R4); there is deliberately no free-text
# question, because postcode- or address-style questions proxy protected traits.
QUESTIONS = {
    "custom_ko_shift": "custom_ko_shift_ok",
    "custom_ko_site": "custom_ko_site_ok",
    "custom_ko_certification": "custom_ko_certification_ok",
    "custom_ko_right_to_work": "custom_ko_right_to_work_ok",
    "custom_ko_start_by": "custom_ko_start_by_ok",
}

# Openings that ask nothing share the Unanswered rank, so they sit with
# unscreened applicants rather than below declared-ineligible ones.
_RANK = {ELIGIBLE: 1, UNANSWERED: 2, None: 2, DECLARED_INELIGIBLE: 3}


def knockout_result(requirements: dict, answers: dict) -> str | None:
    """None when the opening sets no knockout requirement."""
    asked = [answer for requirement, answer in QUESTIONS.items() if requirements.get(requirement)]
    if not asked:
        return None
    values = [answers.get(field) for field in asked]
    if "No" in values:
        return DECLARED_INELIGIBLE
    if any(value != "Yes" for value in values):
        return UNANSWERED
    return ELIGIBLE


def sort_key(result: str | None, created: str) -> str:
    """Rank first, then application time: Frappe's list sorts on one field only."""
    return f"{_RANK[result]}|{created}"
