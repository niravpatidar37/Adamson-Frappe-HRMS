from adamson_screening_bridge.knockout_rules import (
    DECLARED_INELIGIBLE,
    ELIGIBLE,
    UNANSWERED,
    knockout_result,
    sort_key,
)

NIGHT_SHIFT_AND_FORKLIFT = {
    "custom_ko_shift": "Night shift 22:00-06:00",
    "custom_ko_certification": "Forklift licence",
}


def test_all_yes_is_eligible():
    answers = {"custom_ko_shift_ok": "Yes", "custom_ko_certification_ok": "Yes"}
    assert knockout_result(NIGHT_SHIFT_AND_FORKLIFT, answers) == ELIGIBLE


def test_any_no_is_declared_ineligible():
    answers = {"custom_ko_shift_ok": "Yes", "custom_ko_certification_ok": "No"}
    assert knockout_result(NIGHT_SHIFT_AND_FORKLIFT, answers) == DECLARED_INELIGIBLE


def test_no_wins_over_missing():
    answers = {"custom_ko_shift_ok": "No"}
    assert knockout_result(NIGHT_SHIFT_AND_FORKLIFT, answers) == DECLARED_INELIGIBLE


def test_missing_answer_is_unanswered_never_no():
    answers = {"custom_ko_shift_ok": "Yes"}
    assert knockout_result(NIGHT_SHIFT_AND_FORKLIFT, answers) == UNANSWERED


def test_blank_answer_is_unanswered():
    answers = {"custom_ko_shift_ok": "Yes", "custom_ko_certification_ok": ""}
    assert knockout_result(NIGHT_SHIFT_AND_FORKLIFT, answers) == UNANSWERED


def test_answer_to_a_question_the_opening_does_not_ask_is_ignored():
    answers = {
        "custom_ko_shift_ok": "Yes",
        "custom_ko_certification_ok": "Yes",
        "custom_ko_site_ok": "No",
    }
    assert knockout_result(NIGHT_SHIFT_AND_FORKLIFT, answers) == ELIGIBLE


def test_unset_requirements_count_as_not_asked():
    # Frappe returns 0 for an unticked Check and None for an empty Date.
    requirements = {"custom_ko_right_to_work": 0, "custom_ko_start_by": None}
    assert knockout_result(requirements, {"custom_ko_right_to_work_ok": "No"}) is None


def test_opening_with_no_requirements_has_no_result():
    assert knockout_result({}, {"custom_ko_shift_ok": "No"}) is None


def test_sort_key_orders_by_result_then_time():
    rows = [
        (DECLARED_INELIGIBLE, "2026-09-01 09:00:00"),
        (UNANSWERED, "2026-09-02 09:00:00"),
        (ELIGIBLE, "2026-09-03 09:00:00"),
        (ELIGIBLE, "2026-09-01 08:00:00"),
        (None, "2026-09-01 10:00:00"),
    ]
    ordered = sorted(rows, key=lambda row: sort_key(*row))
    assert ordered == [
        (ELIGIBLE, "2026-09-01 08:00:00"),
        (ELIGIBLE, "2026-09-03 09:00:00"),
        (None, "2026-09-01 10:00:00"),
        (UNANSWERED, "2026-09-02 09:00:00"),
        (DECLARED_INELIGIBLE, "2026-09-01 09:00:00"),
    ]
