# Adamson Frappe HRMS

HR platform for Adamson, built on [Frappe HR](https://github.com/frappe/hrms),
with AI resume screening added as a custom app.

> **Status: evaluation.** Nothing is committed to this approach yet. Work
> through `docs/phase-0-spike.md` first — it has abort conditions, and one of
> them is fundamental.

## Why this exists

Adamson needs an HR system that screens resumes at volume using a local
vision-language model, with candidate data never leaving the building.

Two routes were considered:

**Build it all** — the existing [`HR-Screening`](../HR-Screening) repo:
FastAPI, SQLAlchemy, Postgres. Has a working rules engine, scoring-profile
data-minimization boundary, resume-parser client and 92 tests. Missing
authentication, audit logging, background workers and an admin UI.

**Adopt Frappe HR** — a mature open-source HRMS that already provides
authentication, roles and permissions, audit trails, workflow and a UI.
Provides nothing for AI resume screening, which is the actual point of the
project.

The deciding factors:

- Deployment is **internal only**, on Adamson's own server at headquarters.
  GPL-3.0 therefore imposes no obligations: internal use is not distribution,
  and Frappe HR is GPL-3.0, not AGPL-3.0. Source never has to be published,
  even with heavy modification.
- The code that matters — rules engine, candidate profile schema, scoring
  profile, parser client — is framework-independent and ports unchanged.
- The code that would be discarded is the code Frappe already provides:
  the read API, `JobScope` authorization, Alembic migrations, the Next.js shell.

## What carries over from HR-Screening

| Module | Ports? |
|---|---|
| `services/rules_engine.py` | Yes, with its tests |
| `schemas/candidate_profile.py` | Yes |
| `schemas/scoring_profile.py` | Yes — the data-minimization boundary |
| `services/parser_service.py` | Yes |
| `model_serving/` | Yes — an HTTP call to the local model server |
| `schemas/job_blueprint.py` | Yes, including the disallowed-features guard |
| SQLAlchemy models | No — become doctypes |
| Alembic migrations | No — Frappe manages its own schema |
| FastAPI routers | No — become whitelisted methods |
| `core/security.py` JobScope | No — Frappe's permission system replaces it |
| `apps/web` (Next.js) | No — Frappe's desk UI replaces it |

**`HR-Screening` is not deleted.** It stays as a working system and as the
source for the ported logic until this repo replaces it in practice.

## Architecture (intended)

```
Adamson HQ server
  Frappe HR              employees, recruitment, auth, roles, audit, UI
    └─ hr_screening      custom app: parsing, rules, scoring
  Model server           qwen3vl-resume-parser on a private GPU node
  PostgreSQL / MariaDB
```

Nothing leaves the network.
