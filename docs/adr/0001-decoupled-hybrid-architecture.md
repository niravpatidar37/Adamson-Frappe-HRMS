# ADR 0001 — Decoupled hybrid architecture

**Status:** accepted · 2026-09-23

## Context

Adamson needs AI resume screening at volume, on its own server, with candidate
data never leaving the building. Two approaches were built far enough to judge.

A full custom stack (FastAPI, SQLAlchemy, Postgres, Next.js) reached a working
rules engine, data-minimization boundary and read API with 92 tests, but still
lacked authentication, audit logging, background workers and an admin UI.

Frappe HR provides all four and a recruitment module — Job Opening, Job
Applicant, Job Offer, Interview, verified present in the `hr` module. It
provides nothing for AI screening.

## Decision

Frappe HR is the system of record and the recruiter UI. A separate FastAPI
service is the screening engine. They communicate over signed HTTP on the
internal network.

## Rationale

**Failure isolation.** A VLM fails in ways ordinary web code does not: GPU
out-of-memory, token timeouts, corrupt PDFs, context saturation. Inside
Frappe's RQ workers those failures compete with payroll runs and attendance
logging. Outside, a dead GPU worker degrades screening and nothing else.

**Data minimization stays enforceable.** Frappe's ORM writes field changes
into `tabVersion`. Keeping the parsed 23-field profile and the evidence in the
engine means they never enter that history. Frappe receives a score, a
recommendation and a link.

To be accurate about the limit: candidates apply through Frappe's careers
page, so the resume PDF lives in Frappe's File doctype, and Job Applicant
holds name, email and phone by design. What is kept out is the parsed profile
and the evidence, not all PII.

**GPL-3.0 containment.** Internal-only deployment means GPL imposes no
obligations. But a bridge app of a few hundred lines is replaceable; a rules
engine entangled with Frappe doctypes is not. If Adamson moves to another HR
platform, `apps/` is rewritten and `services/` is untouched.

**The domain core stays framework-free.** Nothing under `screening/` imports
Frappe, FastAPI or SQLAlchemy. 39 unit tests run in under a second with no
database and no web server. That property is what made this decision cheap to
make and would make the next one cheap too.

## Consequences

The bridge must be kept thin. The moment parsing or scoring logic appears in
`apps/`, the isolation is gone and the GPL boundary blurs.

Two systems to operate, with a network hop and an authentication scheme
between them. Both directions are HMAC-signed: network position is not
authentication, and a score feeds a hiring decision.

Cohort ranking happens at requisition close, not during intake. Ranking a
moving population means a candidate's position changes as others apply.

## Superseded

Earlier work assumed a single custom stack. The read API, `JobScope`
authorization and the Next.js shell in `HR-Screening` are replaced by Frappe
and are not carried forward. The domain core is.
