"""Frappe glue for v1 knockout screening. The decision itself is knockout_rules.

v1 is Frappe-native (design doc D8): answers are fields on Job Applicant and
the engine is not involved until the v2 scorer.
"""

import frappe

from adamson_screening_bridge.knockout_rules import QUESTIONS, knockout_result, sort_key

WEB_FORM = "job-application"
_SCRIPT_START = "// adamson-knockout:start"
_SCRIPT_END = "// adamson-knockout:end"

_ANSWER_LABELS = {
    "custom_ko_shift_ok": "Can you work the required shift?",
    "custom_ko_site_ok": "Can you travel to the work site?",
    "custom_ko_certification_ok": "Do you hold the required certification?",
    "custom_ko_right_to_work_ok": "Are you legally authorized to work in this country?",
    "custom_ko_start_by_ok": "Can you start by the required date?",
}


def _apply(doc, requirements: dict) -> None:
    result = knockout_result(requirements, {field: doc.get(field) for field in QUESTIONS.values()})
    doc.custom_knockout_result = result or ""
    doc.custom_knockout_sort_key = sort_key(result, str(doc.creation or frappe.utils.now()))


def set_knockout_result(doc, method=None):
    """Job Applicant validate: recomputed on every save, never trusted from the form."""
    requirements = {}
    if doc.get("job_title"):
        requirements = frappe.db.get_value(
            "Job Opening", doc.job_title, list(QUESTIONS), as_dict=True
        ) or {}
    _apply(doc, requirements)


def recompute_for_opening(doc, method=None):
    """Job Opening on_update: a changed requirement re-sorts its applicants.

    Cheap in v1 (no model call), so it runs on every change rather than
    waiting for a recruiter to ask. Written with set_value so applicants'
    version history does not fill with re-sorts.
    """
    if not any(doc.has_value_changed(field) for field in QUESTIONS):
        return
    requirements = {field: doc.get(field) for field in QUESTIONS}
    for row in frappe.get_all(
        "Job Applicant",
        filters={"job_title": doc.name},
        fields=["name", "creation", *QUESTIONS.values()],
    ):
        _apply(row, requirements)
        frappe.db.set_value(
            "Job Applicant",
            row.name,
            {
                "custom_knockout_result": row.custom_knockout_result,
                "custom_knockout_sort_key": row.custom_knockout_sort_key,
            },
            update_modified=False,
        )


@frappe.whitelist(allow_guest=True)
def get_knockout_questions(job_opening: str) -> dict:
    """Requirement values for the application form.

    Guest-readable, but only for a published, open opening: the same facts the
    careers page already shows. Returns {answer_field: requirement value}.
    """
    row = frappe.db.get_value(
        "Job Opening",
        {"name": job_opening, "publish": 1, "status": "Open"},
        list(QUESTIONS),
        as_dict=True,
    )
    if not row:
        return {}
    return {QUESTIONS[field]: str(value) for field, value in row.items() if value}


def ensure_web_form():
    """after_migrate: put the answer fields and script on hrms's application form.

    Runs on every migrate rather than as a one-off patch, because an hrms
    update can re-sync its standard web form and drop these additions.
    Idempotent: fields are added only if missing, the script block is replaced
    between its markers.
    """
    if not frappe.db.exists("Web Form", WEB_FORM):
        frappe.log_error(title="knockout: web form missing", message=WEB_FORM)
        return

    # Direct writes, not web_form.save(): the form is standard (owned by hrms),
    # so save() refuses outside developer mode and, inside it, would export
    # these additions into hrms's own source files.
    web_form = frappe.get_doc("Web Form", WEB_FORM)
    present = {field.fieldname for field in web_form.web_form_fields}
    for fieldname, label in _ANSWER_LABELS.items():
        if fieldname not in present:
            # Hidden until the script shows the questions this opening asks.
            web_form.append(
                "web_form_fields",
                {
                    "fieldname": fieldname,
                    "fieldtype": "Select",
                    "label": label,
                    "options": "\nYes\nNo",
                    "hidden": 1,
                },
            ).db_insert()

    path = frappe.get_app_path("adamson_screening_bridge", "public", "js", "knockout_web_form.js")
    with open(path) as handle:
        block = f"{_SCRIPT_START}\n{handle.read()}\n{_SCRIPT_END}"
    script = web_form.client_script or ""
    if _SCRIPT_START in script:
        head, rest = script.split(_SCRIPT_START, 1)
        script = head + block + rest.split(_SCRIPT_END, 1)[-1]
    else:
        script = f"{script}\n{block}" if script else block
    frappe.db.set_value("Web Form", WEB_FORM, "client_script", script, update_modified=False)
    frappe.clear_cache(doctype="Web Form")
