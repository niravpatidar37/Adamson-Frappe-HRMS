# Documentation

## This project

| Document | Covers |
|---|---|
| [frappe-mapping.md](frappe-mapping.md) | How our model maps onto Frappe's Job Opening and Job Applicant, and what Frappe does not provide |
| [phase-0-spike.md](phase-0-spike.md) | Evaluation checklist with abort conditions. Question 2 answered; 3-5 open |

## Ported from HR-Screening

Written against the previous FastAPI implementation. The requirements,
threat analysis and privacy rules still hold; anything describing routers,
SQLAlchemy models or arq queues is now Frappe's job. Each carries a banner
saying so. None has been revised yet.

| Document | Covers |
|---|---|
| [system-design.md](system-design.md) | Architecture, components, data model, security and privacy design |
| [threat-model.md](threat-model.md) | Threats, trust boundaries, mitigations |
| [data-classification.md](data-classification.md) | What data exists and how sensitive it is |
| [privacy-retention.md](privacy-retention.md) | Retention, deletion, candidate rights |
| [compliance-boundaries.md](compliance-boundaries.md) | Regulatory scope and limits |
| [ai-governance.md](ai-governance.md) | Model use, human authority, fairness |
| [model-evaluation.md](model-evaluation.md) | How model output is evaluated |
| [architecture-decision-records.md](architecture-decision-records.md) | Decisions and rationale |

## Not ported

`api-spec.md`, `deployment.md`, `runbook.md` and `openapi.json` described the
FastAPI stack specifically. They stay in `HR-Screening`; Frappe generates its
own API surface and `deploy/` covers running it.
