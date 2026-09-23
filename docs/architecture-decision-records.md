# Architecture Decision Records

> **Ported from the `HR-Screening` repo**, where it was written against a
> FastAPI + SQLAlchemy implementation. The requirements, threat analysis,
> security model and privacy rules still hold. Anything naming FastAPI
> routers, SQLAlchemy models, Alembic or arq queues describes the previous
> implementation and is now Frappe's responsibility — see
> [frappe-mapping.md](frappe-mapping.md). Not yet revised.

This document records decisions that materially affect security, privacy, reliability, cost, scalability, maintainability, or AI governance. Decisions are append-only: supersede a prior decision with a new ADR rather than rewriting history.

## ADR format

- **Status:** Proposed | Accepted | Superseded | Deprecated
- **Context:** Problem and constraints
- **Decision:** Chosen approach
- **Consequences:** Benefits, costs, risks, and follow-up work

---

## ADR-001: AI-assisted, human-authorized decision model

- **Status:** Accepted
- **Date:** 2026-09-22

### Context

Employment decisions are consequential. Resume parsing and matching systems can be inaccurate, biased, vulnerable to prompt injection, or unable to capture relevant context. The platform must improve recruiter throughput without allowing automated output to become an unreviewed employment decision.

### Decision

The platform will use three layers:

1. Deterministic, approved eligibility rules.
2. Schema-constrained AI extraction and evidence-backed scoring.
3. Explicit recruiter decision and approval before shortlist, rejection, or candidate communication.

Models cannot autonomously hire/reject, change job criteria, invoke arbitrary tools, or send messages. System failures and low-confidence results route to manual review.

### Consequences

- Improves explainability, safety, and auditability.
- Requires HR UI and workflow design for review, override, and decision reason capture.
- Reduces maximum automation but prevents unsafe unattended decisioning.
- Requires measurement of override rates and false-negative samples.

---

## ADR-002: Local-first processing for candidate PII

- **Status:** Accepted
- **Date:** 2026-09-22

### Context

Resumes contain sensitive personal information. Sending full document content to third-party hosted models can create privacy, residency, vendor-retention, and procurement risk.

### Decision

Raw resumes, rendered resume pages, extracted text, structured candidate profiles, embeddings, and PII-bearing model inputs/outputs are processed by self-hosted/private services and local models wherever practical. External services are used only after a documented privacy/security review and explicit approval.

### Consequences

- Reduces PII exposure to external model providers.
- Requires private GPU capacity, model lifecycle controls, and operational expertise.
- Can increase infrastructure complexity and capital/compute cost.
- Does not remove the need for encryption, access control, retention, audit, and incident response.

---

## ADR-003: Asynchronous, queue-backed processing

- **Status:** Accepted
- **Date:** 2026-09-22

### Context

Resume parsing can take tens of seconds or longer per document. A role may receive 1,000 applications, while recruiters generally have multiple days to review the pool. Synchronous parsing would create poor candidate experience and fragile API behavior.

### Decision

Application receipt is synchronous and durable; scanning, rendering, parsing, scoring, embedding, outreach, and deletion are asynchronous queue-backed workflows. Workers are idempotent and use bounded retries, dead-letter queues, and correlation IDs.

### Consequences

- Candidate submission remains fast and resilient to model/GPU outages.
- Queue backlog, event ordering, retry, and idempotency need careful implementation.
- Supports capacity scaling based on predicted drain time rather than raw queue depth.

---

## ADR-004: Versioned job criteria and deterministic rules precede LLM scoring

- **Status:** Accepted
- **Date:** 2026-09-22

### Context

Embedding all hiring requirements in a prompt makes policy hard to inspect, test, reproduce, or change safely.

### Decision

Each job has an approved, versioned blueprint containing must-haves, nice-to-haves, weights, disallowed features, and deterministic eligibility rules. Rules execute in application code or a declarative rules engine before LLM scoring. The model receives only minimized, authorized profile information and the active blueprint.

### Consequences

- Improves reproducibility, testability, auditability, and human review.
- Requires a criteria approval UI and migration/reprocessing strategy.
- Historic results remain attributable to the criteria version active at the time.

---

## ADR-005: Evidence-backed scorecards and score bands

- **Status:** Accepted
- **Date:** 2026-09-22

### Context

A scalar ranking score can imply false precision. Recruiters need to understand what source evidence supports a match and where uncertainty exists.

### Decision

The scoring service returns a strict scorecard with criterion-level status, source evidence, gaps, uncertainty, model/prompt version, and output hash. The UI emphasizes score bands—strong match, potential match, needs review, insufficient evidence, and processing exception—rather than only a leaderboard.

### Consequences

- Adds data-model and UI complexity.
- Helps recruiters challenge, correct, or override recommendations.
- Requires evaluation for evidence grounding and unsupported claims.

---

## ADR-006: Separate quarantine and processing storage

- **Status:** Accepted
- **Date:** 2026-09-22

### Context

Uploaded PDFs, DOCX files, and image documents are untrusted and can exploit parsers or contain malware.

### Decision

Files enter encrypted quarantine storage. They are validated and scanned before moving to a restricted processing domain. Document rendering runs in sandboxed containers with no outbound network egress, read-only filesystem where possible, resource limits, and low-privilege execution.

### Consequences

- Adds storage domains, state transitions, and operational monitoring.
- Prevents unscanned content from reaching parser/model services or normal recruiter download paths.
- Requires explicit handling for scanner failures and suspicious-file workflows.

---

## ADR-007: Retention deletion covers derived data

- **Status:** Accepted
- **Date:** 2026-09-22

### Context

Deleting only the original résumé does not delete PII copied into extracted text, structured profiles, embeddings, prompts, outputs, queues, search indexes, logs, or backups.

### Decision

The retention/deletion orchestrator must delete or irreversibly anonymize PII-bearing primary and derived artifacts. The standard product target is candidate PII deletion no later than 60 calendar days after job closure, subject to documented legal holds, statutory retention, disputes, security investigations, or separate candidate opt-in. A non-PII deletion ledger proves completion.

### Consequences

- Requires data inventory, deletion adapters for every store, and deletion testing.
- Requires backup-expiry policy and candid candidate notices about backup lifecycle.
- Legal and privacy review is required per supported jurisdiction; the application cannot infer that every statutory record may be deleted at the same time.

---

## ADR-008: Hybrid search is authorized server-side

- **Status:** Accepted
- **Date:** 2026-09-22

### Context

Semantic search can reveal candidate information outside a recruiter's role, tenant, or job scope if filtering occurs only in the UI or after retrieval.

### Decision

Hybrid search applies tenant/job/role authorization filters inside the search service before retrieval and reranking. Vector records include mandatory access metadata. Candidate search and result-detail views generate audit events.

### Consequences

- Search is more secure but may require vector-store capabilities for metadata filtering and careful index partitioning.
- Requires authorization tests that attempt cross-tenant and cross-job retrieval.

---

## ADR-009: Recruiter approval is required for external communications

- **Status:** Accepted
- **Date:** 2026-09-22

### Context

Incorrect or duplicated recruitment emails can harm candidates, create legal risk, and damage sender reputation.

### Decision

A local model may draft content, but a recruiter must approve the exact content before sending. The outbound service revalidates decision state, role access, consent/contact preference, suppression list, frequency cap, and idempotency immediately before dispatch.

### Consequences

- Adds a review step to outbound campaigns.
- Prevents a model or background job from sending candidate messages without human authorization.
- Requires delivery, bounce, reply, unsubscribe, and duplicate-send observability.

---

## ADR-010: Start with a modular monolith and bounded workers

- **Status:** Accepted
- **Date:** 2026-09-22

### Context

The initial product needs security boundaries and independently scalable processing, but premature microservice decomposition would add deployment and debugging complexity.

### Decision

Start with a modular FastAPI application for transactional/API concerns and distinct worker deployments for document rendering, parser inference, scoring, outreach, and deletion. Extract services only when ownership, scale, deployment cadence, or security isolation justifies it.

### Consequences

- Faster iteration and simpler local development.
- Requires clean module boundaries and a disciplined internal API/domain-event design.
- GPU parser workers remain independently scalable from web/API workloads.
