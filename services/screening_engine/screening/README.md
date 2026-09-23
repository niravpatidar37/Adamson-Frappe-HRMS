# screening

The framework-independent core, ported from `HR-Screening`. Depends on
`pydantic` and `httpx` and nothing else — no web framework, no ORM, no
database. That is deliberate: it made the port possible and it keeps this
logic testable without standing up Frappe.

```
exceptions.py          domain errors
schemas/               pydantic models
  candidate_profile      the validated 23-field parser output
  job_blueprint          criteria, weights, disallowed-feature screening
  scoring_profile        the data-minimization boundary
  scorecard              model output shape
services/
  criteria_drafting      keyword extraction from a JD; blueprint authoring
  rules_engine           three-valued eligibility; UNKNOWN routes to review
  intake                 upload validation (content type, size, magic bytes)
  capacity_planning      drain-time forecasting
  parser                 orchestrates the parser client and validates output
model_serving/
  client                 HTTP client for the local VLM endpoint
  prompts                fixed prompt templates
```

## Rules

**Nothing here imports Frappe.** When this becomes a Frappe app, the glue —
doctypes, hooks, background jobs — lives outside this package and calls in.
Keeping the boundary means this code stays portable if Frappe is ever
replaced, and testable without it.

**`ResumeParserClient` takes its endpoint as an argument.** It does not read
global settings. Under Frappe the value comes from site config; the client
should not know that.
