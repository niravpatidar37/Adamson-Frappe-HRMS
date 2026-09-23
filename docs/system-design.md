# System Architecture & Technical Specifications
**Document:** `system-design.md`  
**Classification:** Internal Engineering Specification  
**Version:** 2.1.0 (Production Blueprint)

---

## 1. System Topology & Architecture

The Adamson Screening Platform is a high-throughput, privacy-preserving automated recruitment evaluation system designed to process 1,000+ applicants per requisition using an on-premise vision-language model (Qwen-VL).

```text
                             ADAMSON INTRANET BOUNDARY (ON-PREM HQ)
 ┌──────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                                                                              │
 │   RECRUITER WORKFLOW GATEWAY                                                                 │
 │   ┌────────────────────────────────────────────────────────┐                                 │
 │   │                   Frappe HRMS (Desk)                   │                                 │
 │   │   - Requisition lifecycle (Open -> Closed)             │                                 │
 │   │   - Recruiter identity & RBAC                          │                                 │
 │   └───────────────────────────┬────────────────────────────┘                                 │
 │                               │                                                              │
 │                      (1) Webhook: CandidateApplied                                           │
 │                      (Document URI + Blueprint ID)                                           │
 │                               ▼                                                              │
 │   INGESTION & DATA MINIMIZATION BOUNDARY                                                     │
 │   ┌────────────────────────────────────────────────────────┐                                 │
 │   │                 FastAPI Intake Gateway                 │                                 │
 │   │   - Request payload validation (Pydantic v2)           │                                 │
 │   │   - Generates tracking UUID; immediate HTTP 202        │                                 │
 │   └───────────────────────────┬────────────────────────────┘                                 │
 │                               │                                                              │
 │                      (2) Enqueue Job (Broker)                                                │
 │                               ▼                                                              │
 │   ┌────────────────────────────────────────────────────────┐     ┌────────────────────────┐  │
 │   │              Celery / Async Worker Pool                │◄───►│ Dedicated vLLM Node    │  │
 │   │   - Multi-page resume image rasterization              │HTTP │ (Qwen2-VL-7B-Instruct) │  │
 │   │   - Guided JSON token extraction                       │     │ Hardware: A100 / RTX   │  │
 │   └───────────────────────────┬────────────────────────────┘     └────────────────────────┘  │
 │                               │                                                              │
 │                      (3) Evaluate Rubric                                                     │
 │                               ▼                                                              │
 │   ┌────────────────────────────────────────────────────────┐                                 │
 │   │             Deterministic Evaluation Core              │                                 │
 │   │   - build_scoring_profile (Strips candidate PII)       │                                 │
 │   │   - rules_engine (Deterministic; no auto-rejection)    │                                 │
 │   └─────────────┬────────────────────────────┬─────────────┘                                 │
 │                 │                            │                                               │
 │        (4) Write Audit Log          (5) Webhook Callback                                     │
 │                 ▼                            ▼                                               │
 │   ┌───────────────────────────┐┌───────────────────────────┐                                 │
 │   │ PostgreSQL Audit Ledger   ││ Frappe HR Desk Bridge     │                                 │
 │   │ - Immutable evidence trail││ - Updates match_score     │                                 │
 │   │ - Hash-chained verify log ││ - Updates tier & status   │                                 │
 │   └───────────────────────────┘└───────────────────────────┘                                 │
 │                                                                                              │
 └──────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Subsystems & Interfaces

### 2.1 Ingestion Gateway (FastAPI)
- **Role:** Non-blocking API that receives incoming resume attachments from Frappe webhooks.
- **SLA:** Sub-50ms acknowledgment (`HTTP 202 Accepted`).
- **Idempotency:** Implements deduplication using SHA-256 hashes of incoming document payloads.

### 2.2 Inference Engine (vLLM Node)
- **Model:** `Qwen2-VL-7B-Instruct` served via vLLM with PagedAttention.
- **Decoding:** Enforces valid JSON emission via guided grammars matching the `CandidateProfile` schema.
- **Concurrency:** Worker concurrency bounded to $N=4$ concurrent streams per physical GPU to prevent VRAM out-of-memory faults.

### 2.3 Data Minimization Boundary (`build_scoring_profile`)
- **Isolation:** Operates entirely in volatile memory.
- **Redaction:** Identifiers (names, phone numbers, email addresses, street locations, graduation years, gender markers) are stripped before criteria evaluation.
- **Integrity Hash:** Generates a cryptographic verification token:
  $$\text{audit\_token} = \text{HMAC-SHA256}(K_{\text{tenant}}, \text{candidate\_id} \parallel \text{blueprint\_id} \parallel \text{timestamp})$$

### 2.4 Deterministic Rules Engine
- Evaluates extracted candidate attributes against the immutable `JobBlueprint`.
- **Core Invariant:** Missing evidence evaluates to `UNKNOWN` or zero-weight; it **never triggers automated candidate rejection**.

---

## 3. Database Schema (PostgreSQL Audit Ledger)

```sql
CREATE TABLE job_blueprints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    criteria JSONB NOT NULL,
    disallowed_features JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE scorecard_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_blueprint_id UUID NOT NULL REFERENCES job_blueprints(id),
    external_applicant_id VARCHAR(64) NOT NULL,
    composite_score NUMERIC(5, 2) NOT NULL,
    qualification_tier VARCHAR(32) NOT NULL,
    evidence_trail JSONB NOT NULL,
    audit_hash CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_scorecards_blueprint ON scorecard_audits(job_blueprint_id, composite_score DESC);
```
