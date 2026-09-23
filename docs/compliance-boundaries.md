# Compliance Boundaries and Product Commitments

> **Ported from the `HR-Screening` repo**, where it was written against a
> FastAPI + SQLAlchemy implementation. The requirements, threat analysis,
> security model and privacy rules still hold. Anything naming FastAPI
> routers, SQLAlchemy models, Alembic or arq queues describes the previous
> implementation and is now Frappe's responsibility — see
> [frappe-mapping.md](frappe-mapping.md). Not yet revised.

> **Important:** This document is an engineering/compliance-planning artifact, not legal advice. It identifies product controls that require validation by qualified employment, privacy, accessibility, security, and procurement counsel for each jurisdiction and customer deployment.

## 1. Product position

The platform is an AI-assisted applicant-tracking and recruiting decision-support system.

It is designed to:

- Parse documents and organize candidate information.
- Apply approved, explicit job criteria.
- Present evidence-backed scorecards and review queues.
- Support authorized recruiter search and candidate communications.
- Maintain audit trails and privacy workflows.

It is not designed to:

- Make autonomous employment decisions.
- Infer protected characteristics.
- Use opaque black-box scoring as the sole basis for rejection.
- Send external recruitment messages without human approval.

## 2. Engineering controls mapped to obligations

| Control area | Product commitment | Evidence maintained |
|---|---|---|
| AI transparency | Display AI-assistance disclosure where required and maintain notice versions | Published job/application page version, notice acceptance record |
| Human oversight | Recruiter makes final shortlist/rejection/outreach decision | Human decision event, approver, timestamp, override reason |
| Explainability | Show job-specific criteria, evidence, gaps, and uncertainty | Criteria version, scorecard evidence, source references |
| Privacy | Minimize collection, restrict access, provide rights workflow, delete on schedule | Data inventory, access audit, request records, deletion ledger |
| Security | Encrypt data, use least privilege, secure uploads, segment networks, scan supply chain | IaC, scan results, role review, security logs, incident records |
| Fairness | Exclude prohibited/proxy signals, evaluate quality and fairness risks | Rubric approval, model-evaluation report, override/false-negative sampling |
| Accessibility | Provide an accessible candidate flow and accommodation contact/process | Accessibility tests, candidate notice, accommodation workflow |
| Email communications | Validate consent/preferences and apply suppression/idempotency controls | Template version, approval, send/delivery/opt-out record |
| Recordkeeping | Segregate and retain required minimal records based on jurisdiction | Retention policy, exception approval, record inventory |

## 3. Ontario/Canada deployment considerations

For Ontario deployments, public job-posting requirements in force from January 1, 2026 include obligations for covered employers to disclose the use of AI when AI is used to screen, assess, or select applicants in publicly advertised job postings. The platform supports this through versioned job-posting and application notices, but the employer remains responsible for determining applicability and correct wording. [Ontario Employment Standards Act, 2000, s. 8.4; Ontario Regulation 476/24.]

The platform must not assume its default 60-day candidate-PII deletion schedule overrides statutory employment recordkeeping or other legal obligations. The system therefore supports data minimization, segregation of required records, legal holds, documented exceptions, and time-bound deletion of non-required candidate content. Legal review must define the deployment-specific retention schedule.

Canadian privacy obligations can arise federally, provincially, contractually, and sectorally. A deployment must identify controller/processor roles, data residency, cross-border transfer implications, security safeguards, notice/consent requirements, access/correction processes, and breach response obligations before production use.

## 4. Required pre-production reviews

Before processing real candidate data, obtain and document:

- Employment-law review for each targeted hiring jurisdiction.
- Privacy impact assessment or equivalent review.
- Security architecture review and penetration-test plan.
- Accessibility review for public candidate application experience.
- Vendor/processor assessment for identity, email, ATS, hosting, security, analytics, and any model provider.
- AI governance approval for model, prompt, rubric, and evaluation evidence.
- Data retention and backup-retention approval.
- Incident response and breach-notification ownership.

## 5. Customer/employer responsibilities

The platform can enforce workflow controls, but each employer/customer remains responsible for:

- Defining lawful, job-related criteria.
- Approving postings, notices, compensation/location information, and AI disclosure wording.
- Making final employment decisions.
- Ensuring recruiters use the tool according to training and policy.
- Determining required records, retention periods, legal holds, and candidate notices.
- Handling accommodation, discrimination, complaint, and appeal obligations.
- Maintaining required email and communication consents/preferences.

## 6. Controls that must not be bypassed

- No production use without approved candidate notice and privacy contact.
- No active AI scoring without a human-approved job-criteria version.
- No autonomous rejection, hiring, or candidate communication.
- No model training on candidate data by default.
- No external candidate-data transfer without approved data-flow review.
- No unscanned document enters parser/scoring workflow.
- No cross-tenant search or export without server-side authorization.
- No deletion exception without documented reason, owner, approval, and review date.

## 7. Evidence package for audit or enterprise review

Maintain an exportable evidence package containing:

- Current architecture and data-flow diagram.
- Data inventory/classification and retention schedule.
- Threat model, security testing, penetration test summary, and remediation status.
- Model inventory, evaluation reports, prompt/rubric change history, and rollback records.
- Access-control matrix and periodic access review evidence.
- Audit-log retention/integrity design.
- Incident response and disaster-recovery test evidence.
- Vendor/processor security and privacy assessments.
- Candidate notice and AI disclosure versions.

## 8. Open legal/compliance questions

Track these before launch:

- Which jurisdictions and employer sizes are in scope?
- What job-posting/application-form records must be retained, for how long, and in what form?
- Is candidate consent required or is another lawful basis relied upon for each processing purpose?
- What are the cross-border storage/model-processing restrictions?
- What accessibility accommodations and alternate application channels are required?
- What bias/adverse-impact testing is lawful, feasible, and appropriate for the organization?
- What communication rules apply to recruiting email/SMS and candidate opt-out handling?
- What breach reporting, notification, and audit obligations apply?
