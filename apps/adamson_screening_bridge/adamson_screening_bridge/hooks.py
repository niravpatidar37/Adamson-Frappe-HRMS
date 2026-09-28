app_name = "adamson_screening_bridge"
app_title = "Adamson Screening Bridge"
app_publisher = "Adamson"
app_description = "Dispatches applicants to the screening engine and records results"
app_email = "it@adamson.ai"
app_license = "MIT"

# Job Applicant and Job Opening come from hrms. Without this, installing onto
# a site that lacks it fails later and less clearly.
required_apps = ["frappe", "hrms"]

# Custom fields on the stock Job Applicant. Shipped as a fixture so the
# schema travels with the app instead of being clicked in per environment.
fixtures = [
    {
        "dt": "Custom Field",
        "filters": [["module", "=", "Adamson Screening Bridge"]],
    }
]

doc_events = {
    "Job Applicant": {
        # Knockout result from the applicant's own answers (v1, Frappe-native).
        "validate": "adamson_screening_bridge.knockout.set_knockout_result",
        # Dispatch is enqueued, never inline. A synchronous call here would
        # stall every application submission by the engine's response time,
        # and would run inside the transaction that saves the applicant.
        "after_insert": "adamson_screening_bridge.tasks.dispatch_screening",
    },
    "Job Opening": {
        # Re-sorts applicants when a knockout requirement changes.
        # handle_requisition_closed is deliberately NOT registered: it still
        # raises NotImplementedError, and a hook that raises would make every
        # edit to a job opening fail in the UI. Register it in the same commit
        # that implements it.
        "on_update": "adamson_screening_bridge.knockout.recompute_for_opening",
    },
}

# Recruiter list ordering; extends hrms's own list settings.
doctype_list_js = {"Job Applicant": "public/js/job_applicant_list.js"}

# Every migrate, not a one-off patch: an hrms update can re-sync its standard
# application web form and drop the knockout questions.
after_migrate = ["adamson_screening_bridge.knockout.ensure_web_form"]
