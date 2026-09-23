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
        # Dispatch is enqueued, never inline. A synchronous call here would
        # stall every application submission by the engine's response time,
        # and would run inside the transaction that saves the applicant.
        "after_insert": "adamson_screening_bridge.tasks.dispatch_screening",
    },
    "Job Opening": {
        "on_update": "adamson_screening_bridge.tasks.handle_requisition_closed",
    },
}
