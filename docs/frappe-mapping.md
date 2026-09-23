# Mapping HR-Screening onto Frappe HR

Verified against `frappe/hrms@develop` on 2026-09-23 by reading the doctype
definitions directly. Re-check after upgrading Frappe HR.

## Recruitment doctypes exist

`modules.txt` lists only **HR** and **Payroll**, and the README never mentions
recruitment — which is misleading. The recruitment doctypes live inside the
`hr` module:

```
hrms/hr/doctype/
  job_opening/  job_applicant/  job_offer/  interview/
  interview_feedback/  job_requisition/  staffing_plan/  appointment_letter/
```

This was the fundamental abort condition in the spike. It is cleared.

## Job Opening vs our Job

| Ours | Frappe `Job Opening` | Note |
|---|---|---|
| `title` | `job_title` | |
| `description` | `description` (Text Editor) | rich text, not plain |
| `status` draft/published/closed | `status` Open/Closed + `publish` (Check) | two flags rather than three states |
| `posted_at` | **`posted_on`** (Datetime) | already exists |
| — | `closes_on`, `closed_on` | we never modelled closing |
| — | `vacancies`, `planned_vacancies` | |
| — | `location`, `department`, `designation`, `employment_type` | |
| — | `lower_range` / `upper_range` / `currency` | salary, with `publish_salary_range` |
| — | `route`, `job_application_route`, `publish` | **a public careers page already exists** |
| — | `prevent_duplicate_applicant` | |
| `active_criteria_version` | — | **ours, keep** |

Naming: `HR-OPN-.YYYY.-.####`.

## Job Applicant vs our Candidate + Application

Ours splits `Candidate`, `CandidateContact`, `ConsentRecord`, `ResumeDocument`
and `Application`. Frappe collapses most of that into one doctype.

| Ours | Frappe `Job Applicant` |
|---|---|
| `Candidate.first_name` / `last_name` | `applicant_name` (single field) |
| `CandidateContact.email` | `email_id` |
| `CandidateContact.phone` | `phone_number` |
| `Application.job_id` | `job_title` → Job Opening |
| `Application.status` | `status`: Open / Replied / Shortlisted / Rejected / Hold / Accepted |
| `ResumeDocument` | `resume_attachment` (Attach) + `resume_link` |
| — | `applicant_rating`, `source`, `employee_referral`, `country` |
| `ConsentRecord` | **absent — ours, and required** |

Naming: `HR-APP-.YYYY.-.#####`.

## What Frappe does not have — the custom app

Everything that makes this project what it is:

- **Job criteria** — `JobBlueprint`, must-haves, nice-to-haves, other
  requirements, weights, versioning and approval. Frappe's Job Opening has a
  free-text description and nothing structured.
- **Disallowed-feature screening** — rejecting criteria that name a protected
  characteristic.
- **Parsed candidate profile** — the validated 23-field schema.
- **Rules engine** — three-valued eligibility, `UNKNOWN` routes to review.
- **Scoring profile** — the data-minimization boundary that decides what may
  reach the model.
- **Scorecard** — score with evidence, strengths, gaps, uncertainties.
- **Consent records** — Frappe has no consent model.
- **Retention policy** — per jurisdiction and record class.

All of it ported already, in `screening/`.

## Consequences worth deciding early

**Two gaps that matter**, both in doctypes Frappe owns:

`Job Applicant` has no consent field. Privacy notice acceptance is a legal
requirement in our design and there is nowhere to put it — a custom field or
a child table is needed, and it has to be recorded at intake, not later.

`applicant_name` is one field where we had first and last name separately.
The parser produces both. Decide whether to concatenate or add custom fields;
concatenating loses information that the parser extracted.

**Things we planned to build that already exist:** the public careers page
(`publish`, `route`, `job_application_route`), duplicate applicant prevention,
and an applicant status pipeline. The Next.js candidate portal may be
unnecessary.

**Still unverified** — spike questions 3, 4 and 5: job-scoped permissions,
long background jobs, and upload handling.
