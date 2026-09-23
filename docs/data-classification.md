# Data Classification and Handling Standard

> **Ported from the `HR-Screening` repo**, where it was written against a
> FastAPI + SQLAlchemy implementation. The requirements, threat analysis,
> security model and privacy rules still hold. Anything naming FastAPI
> routers, SQLAlchemy models, Alembic or arq queues describes the previous
> implementation and is now Frappe's responsibility — see
> [frappe-mapping.md](frappe-mapping.md). Not yet revised.

> This document defines how the platform classifies, stores, accesses, logs, exports, retains, and deletes data. It is an engineering control document, not legal advice.

## 1. Classification levels

| Level | Definition | Examples | Minimum handling |
|---|---|---|---|
| Public | Approved for unrestricted public disclosure | Published job title, public job description, approved AI disclosure text | Integrity protection; no candidate data |
| Internal | Non-public operational information with limited harm if disclosed | Non-sensitive service configuration, aggregate non-PII metrics | Authenticated access; approved sharing only |
| Confidential | Business-sensitive or security-relevant information | Job rubrics, model configuration, internal templates, audit metadata | Need-to-know access, encryption at rest/in transit, audit significant access |
| Restricted | Personal information, credentials, or high-impact records | Resumes, contact details, parsed profiles, embeddings, scorecards, tokens, keys | Strongest controls: least privilege, encryption, access audit, data minimization, retention/deletion management |

## 2. Data inventory

| Data category | Classification | System of record | Access | Logging rule | Retention/deletion |
|---|---|---|---|---|---|
| Public job posting | Public / Confidential before publication | PostgreSQL/object storage | Authorized HR before publish; public after publish | Log publish/change events | Retain as required by applicable policy/law |
| Candidate application form | Restricted | PostgreSQL | Candidate self-service scope; authorized HR/privacy roles | Never log field values | Delete/minimize per retention policy; segregate statutory record if required |
| Resume and attachments | Restricted | Quarantine and processing object storage | Scanner/renderer/parser; HR only when authorized | Never log content or signed URLs | Delete from all object stores by retention deadline |
| Rendered pages/OCR text | Restricted | Restricted object storage | Parser/authorized review only | Never log text | Delete with source document |
| Parsed candidate profile | Restricted | PostgreSQL | Authorized HR, privacy workflow, scoped services | Log access event, not profile values | Delete/anonymize with application |
| Embeddings/search metadata | Restricted | Vector store | Search service only; scoped HR query results | Log query/access metadata, not vector values | Delete with candidate/application |
| Scorecards/evidence/notes | Restricted | PostgreSQL | Assigned HR, auditor as permitted | Log read/write action; minimize free-text logs | Delete/anonymize according to retention policy except legally required minimal record |
| Model prompts/responses with PII | Restricted | Restricted processing store only if required | Scoring/evaluation services, tightly limited debugging access | Log template/version/hash; not raw content | Avoid persistent storage; delete with application |
| Consent/opt-out/privacy request | Restricted | PostgreSQL | Candidate self scope; privacy officer; limited services | Log workflow action without sensitive details | Retain only as required for proof/obligation |
| Outreach content and delivery events | Restricted | PostgreSQL/email provider | Authorized HR and support/privacy roles | Log metadata, not full body | Delete/minimize with candidate unless a lawful exception applies |
| Audit event | Confidential; may contain restricted metadata | Append-oriented audit store | Auditor/security/privacy roles | Do not store raw resume/body/secret values | Retain under audit policy; pseudonymize where possible |
| Credentials/keys | Restricted | Secrets manager/KMS | Workload identity or tightly scoped admins | Log secret access, never secret value | Rotate/revoke; never archive in application backups |
| Aggregated operational metrics | Internal | Metrics backend | Engineering/operations | No PII labels or high-cardinality candidate identifiers | Bounded retention per observability policy |

## 3. Data handling rules

### Collection

- Collect only fields necessary for a specific recruiting purpose.
- Make optional fields explicit; do not convert optional personal preferences into scoring inputs.
- Do not collect or infer protected characteristics for screening unless an approved, lawful, documented process explicitly requires it.
- Maintain a versioned candidate notice and consent record where consent is the selected legal basis.

### Storage

- Encrypt Restricted and Confidential data at rest and in transit.
- Separate quarantine, clean-processing, and final document stores.
- Do not place raw resumes in source repositories, test fixtures, CI artifacts, shared developer machines, issue trackers, or generic analytics platforms.
- Use production data only in production unless a formally approved, minimized, controlled exception exists.
- Enforce tenant isolation in relational, object, vector, cache, and queue storage.

### Access

- Enforce access server-side with role, tenant, job, application, and purpose scope.
- Default platform administrators to no resume-content access.
- Require step-up authentication and audit for bulk exports, wide searches, privacy actions, retention changes, and privileged operations.
- Use expiring signed links for authorized file download; never expose permanent object URLs.

### Logging and telemetry

- Do not log resumes, OCR text, complete parsed profiles, email content, access tokens, passwords, API keys, signed URLs, or full prompt/response payloads containing PII.
- Use opaque IDs, hashes, field-presence flags, template versions, model versions, and event metadata for debugging.
- Run PII/secret detection on logs and traces; alert and remediate accidental capture.
- Bound observability retention and document it in the retention policy.

### Export and sharing

- Exports require authorization, purpose confirmation, audit, encryption, short-lived links, and expiration.
- Minimize export fields; do not export raw documents by default.
- Third-party processors require a documented security/privacy review and a data-processing agreement where applicable.

## 4. Sensitive-field policy

The following must not be used as automated scoring inputs unless there is a documented, lawful, reviewed exception:

- Name, photo, date of birth, age, gender/pronouns, race, ethnicity, religion, disability, marital/family status.
- Address/postal code beyond strictly necessary job-location eligibility.
- Nationality/citizenship beyond a lawful work-authorization workflow.
- Graduation years, school prestige, hobbies, social links, or inferred personality traits.
- Language style or accent unless a role-specific language requirement is approved and assessed using a justified process.

The system must not infer these attributes from free text, images, or embeddings for ranking.

## 5. Data lineage requirements

For each application, maintain a restricted lineage record:

```text
application_id
  -> source document ID + checksum
  -> scan result
  -> rendered-page artifact IDs
  -> extraction ID + parser model/schema/prompt version
  -> profile version
  -> active job criteria version
  -> eligibility evaluation version
  -> scorecard/model/prompt version
  -> human decision and override reason
  -> outreach approval/message ID
  -> retention date and deletion result
```

Lineage enables reproducibility, correction, privacy response, and deletion without retaining unnecessary raw content in routine logs.

## 6. Data quality and correction

- Parsed data is model-generated and may be incorrect.
- Recruiters must be able to correct extraction errors while preserving original extraction version and edit provenance.
- Candidate correction requests are routed to the privacy workflow and are never silently applied without review.
- A correction that materially affects an active evaluation triggers a re-evaluation under the applicable criteria version and records the change.

## 7. Data handling acceptance checklist

- [ ] Every stored field has an owner, classification, purpose, storage location, access policy, and deletion path.
- [ ] No Restricted data appears in source control, default logs, metrics labels, or test fixtures.
- [ ] All vector records carry and enforce tenant/application access metadata.
- [ ] Backup data follows the documented encryption and expiration policy.
- [ ] Export, download, and privacy workflows are access-controlled and audited.
- [ ] A new vendor/integration cannot receive candidate data without a documented review.
- [ ] Data lineage can locate all derived artifacts required for correction or deletion.
