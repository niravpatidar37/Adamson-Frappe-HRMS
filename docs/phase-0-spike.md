# Phase 0 — spike

Answer five questions before porting anything. Timebox: two days.

Each has an abort condition. Discovering a failure here costs a day;
discovering it after porting costs weeks.

---

## 1. Get Frappe HR running locally

```bash
git clone https://github.com/frappe/frappe_docker
cd frappe_docker
# follow their development or pwd.yml setup
```

**Done when:** the desk UI loads and you can log in as Administrator.

**If it fights you for more than half a day:** that difficulty does not go
away in production. Note what broke before moving on.

---

## 2. Do the recruitment doctypes exist?  ← **FUNDAMENTAL**

This is the assumption everything rests on, and it is **unverified**. The
Frappe HR README does not list a recruitment module, and the repository tree
could not be read to confirm it.

Look in the desk UI for:

- [ ] Job Opening
- [ ] Job Applicant
- [ ] Job Offer
- [ ] Interview / Interview Round / Interview Feedback
- [ ] Staffing Plan

Also check whether they live in `hrms` or in ERPNext, because that changes
what you install.

**ABORT IF ABSENT.** Without these you are adopting a payroll and leave
system to get authentication and a UI, and paying a whole framework for it.
If they are missing, the right answer is probably to keep building
`HR-Screening` and add Keycloak.

---

## 3. Can Frappe express job-scoped permissions?

`HR-Screening` enforces three states, tested in `tests/test_job_scope.py`:

- `ALL_TENANT_JOBS` — sees every job
- `ASSIGNED_JOBS_ONLY` — sees only assigned reqs
- `NO_JOBS` — sees nothing, and this must be a denial rather than an
  unfiltered query

Try to reproduce that with User Permissions on Job Opening:

- [ ] Recruiter A sees only their assigned opening
- [ ] Recruiter A is denied a direct URL to Recruiter B's opening
- [ ] A recruiter with no assignment sees an empty list, not all of them
- [ ] Applicants inherit the restriction from their opening

**Abort if:** the third case leaks. "No assignments" silently meaning "no
filter" is the exact bug that was fixed in `HR-Screening`, and inheriting it
from a framework is worse than owning it.

---

## 4. Does a background job survive a 180-second model call?

`ResumeParserClient` has a 180-second timeout, and a job can receive 1,000+
applicants. This has to run on the queue, not in a request.

```bash
bench new-app hr_screening
```

Then prove the smallest end-to-end path:

- [ ] A custom doctype saves
- [ ] `hooks.py` `doc_events` fires on Job Applicant update
- [ ] `frappe.enqueue(..., queue="long", timeout=900)` runs
- [ ] The job makes an HTTP call taking 180s and completes
- [ ] A failure lands somewhere visible, not silently

Check the default `long` queue timeout — it may need raising in
`common_site_config.json`.

**Abort if:** long jobs cannot be made reliable. Parsing is the product.

---

## 5. What does upload handling look like?

Frappe stores uploads through its `File` doctype, not through the quarantine
bucket `HR-Screening` uses. That code has real security work in it —
magic-byte validation, a path-traversal fix with regression tests, size
capping before allocation.

- [ ] Where does an attachment physically land?
- [ ] Can a file be held unscanned before anything else reads it?
- [ ] Can uploads be restricted by content type and size?
- [ ] Are files under the web root, and are they access-controlled?

**Not an abort condition**, but budget real time for it. This is where a
mistake matters most, and it must be redesigned against Frappe rather than
translated across.

---

## Decision

Record the outcome here before writing any porting code.

- Date:
- Frappe HR version:
- Recruitment doctypes present: yes / no
- Job-scoped permissions reproducible: yes / no
- Long background jobs reliable: yes / no
- Decision: proceed / abort / revisit
- Notes:
