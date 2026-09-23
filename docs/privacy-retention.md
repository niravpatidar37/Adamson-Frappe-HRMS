# Privacy and Retention Design

> **Ported from the `HR-Screening` repo**, where it was written against a
> FastAPI + SQLAlchemy implementation. The requirements, threat analysis,
> security model and privacy rules still hold. Anything naming FastAPI
> routers, SQLAlchemy models, Alembic or arq queues describes the previous
> implementation and is now Frappe's responsibility — see
> [frappe-mapping.md](frappe-mapping.md). Not yet revised.

> **Purpose:** Define the platform's candidate-data privacy workflow, retention schedule, deletion design, exceptions, backup treatment, and verification controls.
>
> **Important:** This is an engineering baseline, not legal advice. Privacy counsel must validate the final policy for every supported jurisdiction, employer, collective agreement, and regulator-specific obligation.

## 1. Privacy commitments

The platform is designed to:

- Collect only information needed for a stated recruitment purpose.
- Clearly inform candidates about data collection, AI-assisted screening, human decision-making, retention, and privacy contacts.
- Keep recruiters responsible for consequential employment decisions.
- Limit access to candidate data by role, tenant, job, and business purpose.
- Process candidate PII in private/self-hosted systems where feasible.
- Support access, correction, deletion, and opt-out/suppression workflows where applicable.
- Delete candidate PII and derived artifacts within the configured schedule, with a default product target of 60 days after job closure.

## 2. Candidate notice requirements

The public job/application experience must display a versioned notice in clear language before submission. At minimum, it should state:

- The organization collecting the information and a privacy contact.
- What information is collected and why.
- That uploaded resumes may be processed using automated tools to extract structured information and support recruiter review.
- That authorized human recruiters make final shortlist/rejection and communication decisions.
- The categories of recipients/processors, if any.
- The retention period or how it is determined.
- How the candidate can request access, correction, deletion, accommodation, or raise concerns.
- The contact channel for communication preferences and opt-out where applicable.

Where laws require disclosure of AI use in public job postings or application forms, show that disclosure directly in the relevant experience—not only in a linked privacy policy.

## 3. Retention policy

### Default product target

```text
Candidate PII retention deadline = job_closed_at + 60 calendar days
```

At or before the deadline, the system deletes or irreversibly anonymizes candidate PII and all derived artifacts unless a documented exception applies.

### Data that must be included

- Original résumé, cover letter, attachments, portfolio files, and applicant-uploaded content.
- Rendered pages, OCR text, parser artifacts, extracted structured profile, and correction history containing PII.
- Candidate embeddings, vector metadata, search-index documents, caches, and derived features.
- LLM prompts, outputs, traces, and evaluation records that contain candidate content.
- Candidate-specific scorecards, free-text reviewer notes, communication content, and delivery metadata.
- Candidate payloads in queues, retries, dead-letter queues, and temporary files.

### Exceptions

An exception must have an owner, reason, approval, scope, expiry/review date, and audit trail. Permitted exception categories are limited to:

- Legal hold, active complaint, litigation, investigation, or security incident.
- Statutory recordkeeping requirement.
- Candidate's separate, explicit talent-pool consent with a stated retention period.
- A documented contractual obligation reviewed by privacy/legal stakeholders.

Do not use a generic “business need” exception. A closed job is not by itself a reason to retain candidate PII indefinitely.

## 4. Statutory record separation

Recruiting laws may impose recordkeeping obligations that do not align with a 60-day PII deletion objective. Treat this as a design constraint rather than a reason to retain all candidate data.

1. Identify records that must be retained for each jurisdiction.
2. Segregate those records from recruiter working data and model artifacts.
3. Retain the minimum fields and artifacts required.
4. Restrict access to privacy/legal/audit roles where feasible.
5. Document retention duration, legal basis, review owner, and deletion date.
6. Do not retain raw résumés, embeddings, prompts, or complete scorecards merely because a minimal job-posting or application record must be retained.

## 5. Deletion architecture

### State machine

```text
active
  -> job_closed
  -> retention_scheduled
  -> deletion_due
  -> deletion_in_progress
  -> deleted

Exception path:
  deletion_due -> legal_hold / statutory_retention / talent_pool_consent
  -> periodic_review -> deletion_in_progress -> deleted
```

### Workflow

1. Job closure calculates a deletion deadline for each linked application.
2. A daily scheduler identifies due records and validates there is no active exception.
3. Application status changes to `deletion_in_progress`; application pages, recruiter access, search, and outreach are blocked.
4. The orchestrator invokes idempotent deletion adapters for every primary and derived data store.
5. Each adapter returns a completion status, time, and non-PII evidence.
6. The orchestrator verifies all required stores completed.
7. The system writes a deletion ledger event containing opaque identifier/hash, result, timestamps, policy version, and exception state; no candidate content.
8. Failures retry with backoff and alert before the deadline breach. Repeated failure opens an incident.

### Required deletion adapters

| Store | Required deletion action |
|---|---|
| PostgreSQL | Delete PII fields, application/profile rows, scorecards, messages, and PII notes; retain only approved minimal non-PII audit/record data |
| Quarantine/processing object storage | Delete source files, pages, OCR outputs, temporary conversions, and attachments |
| Vector database | Delete vectors and metadata using application/candidate IDs; verify no orphan records |
| Search indexes/cache | Purge document text, cached profile/evaluation data, and search metadata |
| Queue/DLQ | Remove or expire PII-bearing event payloads; design events to contain references rather than full candidate data |
| Model artifacts | Purge persistent PII prompts, outputs, traces, and caches |
| Email/outreach | Remove or minimize candidate-specific message body and provider metadata subject to approved policy |
| Observability | Redact/purge accidental PII capture; routine logs should not contain PII by design |

## 6. Backup and disaster-recovery treatment

Primary deletion does not automatically erase old backups. The privacy notice and internal policy must state the maximum backup expiration period.

- Encrypt backups with separate keys and separate access controls.
- Use a short, documented backup retention window compatible with the product deletion commitment and recovery requirements.
- Do not restore deleted candidate data into production during a normal recovery. Restoration procedures must reapply deletion tombstones/ledger state before records become accessible.
- Test backup expiry and restore procedures at least quarterly.
- If immutable backups temporarily retain deleted data, restrict access, prevent ordinary use, and ensure expiry is automatic and verifiable.

## 7. Privacy request handling

### Request types

- Access/export.
- Correction.
- Deletion.
- Withdrawal of talent-pool consent.
- Communication opt-out.
- Question, complaint, or request for accommodation.

### Workflow

1. Authenticate the requester proportionately and avoid collecting excessive identity data.
2. Create a tracked privacy request with a deadline based on the applicable policy/law.
3. Locate the candidate/application using the data-lineage inventory.
4. Route to privacy officer; restrict routine processing while request is active where appropriate.
5. Perform approved action, including re-evaluation if corrected data changes an active assessment.
6. Record outcome, legal/operational basis, and completion evidence.

## 8. Privacy metrics and alerts

Monitor:

- Number and age of pending privacy requests.
- Applications approaching retention deadline.
- Deletion completion rate and deletion failures by store.
- Orphan vector/document/search records discovered by reconciliation jobs.
- PII/secret detections in logs, traces, CI artifacts, and support systems.
- Wide recruiter searches, exports, document downloads, and denied access attempts.
- Legal-hold/exception inventory and overdue exception reviews.

## 9. Acceptance checklist

- [ ] Candidate notice is versioned, displayed before submission, and includes AI-assistance/human-review information.
- [ ] Every PII field and derived artifact has a retention/deletion path.
- [ ] The 60-day deadline is computed, scheduled, monitored, and tested end to end.
- [ ] Deletion includes documents, parsed data, embeddings, prompts/outputs, queues, caches, indexes, and outreach artifacts.
- [ ] Legal holds and statutory records are minimized, segregated, approved, and reviewed.
- [ ] Backup retention and restore behavior are documented and tested.
- [ ] Access, correction, deletion, opt-out, and accommodation requests have a staffed workflow.
- [ ] Privacy incidents and deadline breaches have clear escalation paths.
