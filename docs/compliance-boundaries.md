# AI Governance, Compliance Boundaries & Data Classification
**Documents:** `ai-governance.md` | `compliance-boundaries.md` | `data-classification.md`  
**Classification:** Enterprise AI Compliance Policy  
**Scope:** Automated Employment Decision Tools (AEDT) & High-Risk AI Systems

---

## Part 1: AI Governance Framework (`ai-governance.md`)

### 1. High-Risk System Classification
The Adamson AI Screening Engine operates as an **Automated Employment Decision Support Tool (AEDT)** under:
* **NYC Local Law 144 (AEDT Audit Requirements)**
* **EU AI Act (Annex III - High-Risk Employment AI)**
* **EEOC Uniform Guidelines on Employee Selection Procedures (UGESP)**

### 2. Prohibited AI Behaviors & Non-Negotiable Invariants
1. **No Autonomous Negative Rejections:** The system generates match scorecards and evidence trails. It is strictly prohibited from executing terminal rejection decisions without an explicit recruiter review step.
2. **Deterministic Rules Over Generative Scoring:** Large Language Models are used exclusively for document extraction (rasterized text $\rightarrow$ structured JSON). Final candidate evaluation is calculated using a deterministic rules engine.
3. **Disallowed Proxy Features:** Scoring criteria cannot evaluate or derive proxies for protected characteristics:
   - Graduating class years (age proxy).
   - Institution names or postal codes (race/socioeconomic proxy).
   - Pronouns, extracurricular associations, or gap years.

### 3. Bias Audit & Adverse Impact Monitoring
The system monitors scoring distributions using the **Four-Fifths (80%) Rule**:
$$\text{Impact Ratio} = \frac{\text{Selection Rate of Protected Group}}{\text{Selection Rate of Most Selected Group}} \ge 0.80$$
If an active job requisition violates this threshold, the system flags the requisition for immediate human auditing.

---

## Part 2: Compliance Boundaries (`compliance-boundaries.md`)

```text
 ┌────────────────────────────────────────────────────────┐
 │           CANDIDATE PII BOUNDARY (Frappe Desk)         │
 │   Contains: Full Name, Address, Contact, Raw PDF       │
 └───────────────────────────┬────────────────────────────┘
                             │
                  One-Way Minimization Boundary
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │        SCREENING ENGINE MEMORY SPACE (FastAPI)         │
 │   Transforms raw profile into anonymized schema        │
 └───────────────────────────┬────────────────────────────┘
                             │
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │         AUDIT LEDGER BOUNDARY (PostgreSQL)             │
 │   Stores: Composite Score, Evidence Quotes, Hash       │
 │   NEVER STORES: PII, Raw Resume Text, Identity         │
 └────────────────────────────────────────────────────────┘
```

### Statutory Boundary Mappings
| Statutory Standard | System Implementation |
| :--- | :--- |
| **NYC Local Law 144** | Annual independent bias audit; public posting of selection rates; 10-day candidate notification mechanism. |
| **EU AI Act (Art. 9–15)** | Continuous risk management; technical logging of all scoring executions; human-in-the-loop oversight. |
| **GDPR (Art. 22)** | Prohibition of solely automated profiling producing legal or significant effects on candidates. |

---

## Part 3: Data Classification Policy (`data-classification.md`)

| Tier | Classification | Data Elements | Retention Period | Storage Location |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1** | **Direct PII** | Candidate name, email, phone, physical address, raw resume attachment. | 180 days post-requisition close (or per candidate deletion request). | Frappe HR File System / Encrypted Object Storage. |
| **Tier 2** | **Anonymized Capability Data** | Normalized skill set, years of relevant experience, structured work history. | Transient (In-memory execution only). | None (Discarded post-evaluation). |
| **Tier 3** | **Immutable Audit Evidence** | Objective scorecard metrics, verbatim evidence citations, cryptographic integrity hash. | 3 years (Statutory compliance requirement). | PostgreSQL `scorecard_audits` (Append-only). |
