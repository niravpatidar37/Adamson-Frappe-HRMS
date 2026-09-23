# Phase 0 Spike: Evaluation, Risks & Go/No-Go Criteria

---

## 1. Objectives

The Phase 0 Spike evaluates whether **Frappe HR** can serve as an effective administrative shell and recruiter desk for the Adamson AI Screening Engine without introducing compute bottlenecks, PII leaks, or administrative overhead.

---

## 2. Abort Conditions (Go / No-Go Gates)

The spike defines four strict criteria that determine whether to proceed with the decoupled hybrid approach:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            PHASE 0 ABORT CONDITIONS                          │
├────┬─────────────────────────────┬──────────────────────────┬────────────────┤
│ #  │ Test Dimension              │ Failure Condition        │ Threshold      │
├────┼─────────────────────────────┼──────────────────────────┼────────────────┤
│ 1  │ Worker Latency & Starvation │ Queue starvation         │ > 15s backlog  │
│ 2  │ PII Leakage in Audit Trail  │ Raw PII in tabVersion    │ > 0 occurrences│
│ 3  │ Model Node Saturation       │ vLLM VRAM OOM crash      │ > 0 crashes    │
│ 4  │ Data Integrity Mismatch     │ Schema validation bypass │ > 0 bypasses   │
└────┴─────────────────────────────┴──────────────────────────┴────────────────┘
```

### Abort Condition 1: Worker Queue Starvation
* **Hazard:** If webhook dispatches from Frappe HR block standard transactional workers, standard HRMS tasks (e.g., payroll processing, leave requests) will experience latency spikes.
* **Pass Criteria:** Webhook dispatch tasks must execute in under 150ms. Frappe web workers must maintain a p99 response time below 350ms under continuous intake load.
* **Action on Failure:** Migrate webhook dispatching to a dedicated Redis queue or an external ingestion gateway.

### Abort Condition 2: PII Leakage into Version History
* **Hazard:** Frappe tracks changes across documents by serializing diffs into the `tabVersion` table. If candidate profiles are stored as standard DocTypes, raw resume text, addresses, and demographic attributes will be recorded in system audit logs, bypassing `build_scoring_profile`.
* **Pass Criteria:** The `tabVersion` table must contain zero instances of unredacted candidate PII. Only cryptographic verification hashes and calculated scorecards may persist in Frappe.
* **Action on Failure:** Abort native Frappe storage for screening records; isolate candidate records in PostgreSQL.

### Abort Condition 3: GPU Node Saturation & Timeout
* **Hazard:** Processing 1,000 resumes (averaging 2–3 pages each) requires ~2,500 image frames. Running batch inference without bounded queue concurrency will trigger GPU out-of-memory (OOM) errors or HTTP timeouts.
* **Pass Criteria:** The local vLLM instance must process 100 concurrent pages using continuous batching and guided JSON decoding without exceeding 85% GPU VRAM or returning HTTP 5xx errors.
* **Action on Failure:** Enforce client-side rate limiting and worker concurrency caps ($N \le 4$).

### Abort Condition 4: Schema Validation Impedance
* **Hazard:** Frappe DocTypes are dynamically typed at runtime. If recruiters modify job blueprints via Desk UI, malformed criteria may bypass the strict Pydantic models defined in `JobBlueprint`.
* **Pass Criteria:** Every candidate evaluation must validate against Pydantic schemas before running the rules engine. Any schema violation must trigger an explicit exception and alert the recruiter.
* **Action on Failure:** Require strict JSON Schema validation within Frappe DocType validation hooks (`validate()`).

---

## 3. Test Matrix & Verification Protocols

```text
       Simulated Batch Intake (100–500 Synthetic Resumes)
                               │
                               ▼
     ┌───────────────────────────────────────────────────┐
     │ Test Step 1: Ingestion & Non-Blocking Dispatch    │
     │ Measure: Desk API p99 latency & queue time        │
     └─────────────────────────┬─────────────────────────┘
                               │
                               ▼
     ┌───────────────────────────────────────────────────┐
     │ Test Step 2: vLLM Batch Inference Stability       │
     │ Measure: GPU VRAM utilization & token throughput  │
     └─────────────────────────┬─────────────────────────┘
                               │
                               ▼
     ┌───────────────────────────────────────────────────┐
     │ Test Step 3: PII Minimization Audit               │
     │ Measure: SQL inspection of MariaDB tabVersion     │
     └─────────────────────────┬─────────────────────────┘
                               │
                               ▼
     ┌───────────────────────────────────────────────────┐
     │ Test Step 4: Deterministic Rules & Scorecard Sync │
     │ Measure: Score consistency across duplicate runs  │
     └───────────────────────────────────────────────────┘
```

### Verification Scripts

#### Protocol 1: PII Audit Verification
Run the following SQL check on the Frappe MariaDB instance after processing 50 synthetic test candidates:
```sql
-- Ensure no extracted resume text or candidate address data exists in Frappe audit tables
SELECT count(*) AS pii_leak_count
FROM tabVersion
WHERE docname LIKE 'APPL-%'
  AND (
      data LIKE '%street%' 
      OR data LIKE '%phone%' 
      OR data LIKE '%gender%' 
      OR data LIKE '%university%'
  );
-- PASS REQUIREMENT: pii_leak_count == 0
```

#### Protocol 2: Worker Concurrency & VRAM Stress Test
Execute the test runner against the local GPU endpoint using Locust or pytest-benchmark:
```bash
# Verify vLLM throughput and concurrency limits under multi-page resume load
pytest tests/integration/test_vllm_client.py \
    --benchmark-autosave \
    --concurrency=4 \
    --num-resumes=100
```
