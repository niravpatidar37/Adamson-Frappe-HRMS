# Model Evaluation Plan

> **Ported from the `HR-Screening` repo**, where it was written against a
> FastAPI + SQLAlchemy implementation. The requirements, threat analysis,
> security model and privacy rules still hold. Anything naming FastAPI
> routers, SQLAlchemy models, Alembic or arq queues describes the previous
> implementation and is now Frappe's responsibility — see
> [frappe-mapping.md](frappe-mapping.md). Not yet revised.

> **Purpose:** Define how the resume parser, scoring model, embeddings, prompts, and rubric behavior are evaluated before release and monitored after deployment.
>
> **Rule:** No model, prompt, parser schema, scoring logic, or embedding model is promoted solely because it “looks good” on a few examples.

## 1. Evaluation scope

| Component | Primary question |
|---|---|
| Resume parser | Does it accurately extract structured fields from varied real-world resume formats? |
| Schema validator | Does it reject malformed, incomplete, contradictory, or unsafe output correctly? |
| Rules engine | Does it apply approved deterministic criteria exactly and reproducibly? |
| Scorecard model | Does it identify job-relevant evidence, gaps, and uncertainty without unsupported claims? |
| Embedding/search | Does it retrieve relevant, authorized candidates while enforcing filters? |
| Outreach drafting | Does it follow approved template constraints, avoid unsupported claims, and preserve tone/privacy rules? |

## 2. Dataset governance

### Dataset types

- **Synthetic set:** Generated resumes and job descriptions for development, adversarial testing, and open-source demonstration.
- **Consented evaluation set:** Real or representative documents used only with documented authorization and controls.
- **Gold-label set:** Independently annotated examples with field values, evidence spans, eligibility outcomes, and rubric assessments.
- **Adversarial set:** Prompt injection, hidden text, malformed files, unusual layouts, multilingual content, OCR noise, contradictory dates, and fabricated credentials.
- **Regression set:** Locked examples representing prior defects, edge cases, and production incidents.

### Dataset controls

- Version datasets and labels; record source, purpose, owner, access, and retention.
- Do not use production candidate data in local development or public repositories.
- Separate training, validation, and test data. Do not tune prompts/models against the locked test set.
- Redact or irreversibly anonymize examples used in documentation.
- Record annotation guidelines and inter-annotator agreement for subjective labels.

## 3. Parser evaluation

### Metrics

| Metric | Definition | Why it matters |
|---|---|---|
| JSON validity | Valid schema outputs / total parser outputs | Measures integration reliability |
| Field precision | Correct extracted values / extracted values | Prevents incorrect data from being shown as fact |
| Field recall | Correct extracted values / gold values | Measures missed candidate information |
| Exact match | Fields exactly matching normalized gold labels | Useful for email, phone, dates, enums |
| Evidence span accuracy | Correct source evidence alignment | Supports reviewer verification |
| Manual correction rate | Recruiter corrections / parsed profiles | Measures real-world usability |
| Failure routing accuracy | Invalid/low-confidence records routed to review | Ensures safe failure behavior |
| Latency and cost | p50/p95/p99 and GPU seconds/document | Drives capacity planning |

### Initial acceptance thresholds

Set final thresholds with a representative benchmark. A conservative initial release gate could be:

| Metric | Initial target |
|---|---:|
| JSON-schema validity | >= 99.5% after bounded repair/validation policy |
| Critical contact-field precision | >= 99% or require verification before use |
| Skills/experience evidence-groundedness | >= 95% on gold dataset |
| Invalid/low-confidence safe routing | 100% of known invalid test cases |
| Parser p95 latency | Within documented capacity model |

A previously reported model JSON validity of approximately 88% is not adequate as a production contract by itself. The platform must use validation, bounded retry/fallback, and manual review; production readiness should be measured on the deployed inference configuration and representative document set.

## 4. Scorecard evaluation

### Gold-label method

For every evaluation example, qualified reviewers label:

- Active job criteria and rule version.
- Evidence snippets supporting each criterion.
- Criterion outcome: met, partially met, not found, ambiguous, or not applicable.
- Any known disallowed/proxy data that must not influence assessment.
- Expected routing: proceed, manual review, or deterministic ineligible.

### Metrics

| Metric | Definition | Initial direction |
|---|---|---|
| Criterion agreement | Agreement with human labels per criterion | Maximize |
| Evidence groundedness | Claims supported by source text / all claims | Maximize |
| Unsupported claim rate | Unsupported claims / all claims | Minimize |
| Eligibility-rule accuracy | Correct deterministic outcome / all cases | 100% for deterministic inputs |
| Ranking quality | NDCG@k, pairwise agreement, or reviewer preference | Compare against recruiter baseline |
| Calibration | Relationship between confidence and actual correctness | Improve before using confidence gates |
| Manual-review recall | Ambiguous/unsafe cases sent to review / all known ambiguous/unsafe cases | Maximize |
| Disallowed-feature leakage | Outputs/input fields violating policy | 0 tolerated |
| Prompt-injection resistance | Adversarial cases without policy violation | 100% of defined critical tests |

### Scorecard release requirements

- Every criterion claim must cite candidate-provided source evidence or state “not found/ambiguous.”
- The model may not infer years of experience, certifications, work authorization, or skills absent from the evidence.
- Numerical score calculation occurs in deterministic application code using the approved rubric—not in free-form model reasoning.
- Any material regression in groundedness, rule agreement, false-negative sample performance, or safety behavior blocks release.

## 5. Fairness and proxy-risk evaluation

This platform must not infer or rank by protected characteristics. Evaluation should therefore test both intentional and accidental proxy usage.

- Create counterfactual pairs that differ only in a prohibited/proxy attribute, such as a name or graduation year, while holding job-relevant evidence constant.
- Verify the extracted job-relevant profile and scorecard are materially identical except for permitted text normalization differences.
- Test school prestige, postal codes, hobbies, photos, pronouns, age signals, employment gaps, and language style as potential proxy vectors.
- Review score and manual-review distributions across lawfully available, appropriately governed groups where such testing is permitted.
- Document limits: absence of demographic data does not prove absence of bias.

## 6. Search evaluation

Evaluate semantic search separately from screening:

- Recall@k and precision@k for role-relevant candidate retrieval.
- Filter correctness: tenant, job, consent, candidate status, and authorization restrictions must be enforced before results are returned.
- Cross-tenant/cross-job leakage rate: zero tolerated.
- Reranker groundedness and latency.
- Search audit completeness and anomaly detection.

## 7. Outreach drafting evaluation

Test that drafted messages:

- Use only permitted candidate and job fields.
- Follow the approved template and organization tone.
- Do not claim the candidate was “selected” or “rejected” unless the final human decision state authorizes that text.
- Do not include sensitive data unnecessarily.
- Preserve opt-out/contact instructions where required.
- Never send without exact recruiter approval.

## 8. Regression and monitoring

### Pre-release

Run the full locked regression suite for every change to model artifact, quantization, serving runtime, prompt, schema, scoring code, parser preprocessing, embedding model, or job-blueprint generation logic.

### Post-release

Monitor:

- JSON/schema failures and fallback/manual-review rate.
- Latency, GPU saturation, token/image usage, error/retry rate, and cost per application.
- Recruiter corrections, overrides, and disagreement by role/criteria/model version.
- Unsupported-claim samples and evidence coverage.
- Candidate decision distribution changes after a release.
- Prompt-injection/security test drift.

Define rollback triggers before release. Example triggers: critical policy violation, disallowed-field leakage, material evidence-groundedness regression, substantial unexplained ranking distribution shift, or failure to meet processing SLA.

## 9. Evaluation report template

Each release should produce a concise report:

```text
Release ID:
Component and version:
Dataset version:
Prompt/schema/rubric version:
Deployment configuration:
Evaluator/approver:

Quality metrics:
- JSON validity:
- Field precision/recall:
- Evidence groundedness:
- Unsupported claim rate:
- Criterion agreement:
- Manual-review routing:
- Search quality (if applicable):

Safety metrics:
- Prompt injection pass rate:
- Disallowed/proxy leakage:
- Authorization/isolation tests:

Operations:
- p50/p95 latency:
- Error/retry rate:
- GPU/CPU cost per application:

Decision:
- Approve / approve with limits / reject
- Known limitations:
- Rollback trigger:
- Required follow-up:
```

## 10. Acceptance checklist

- [ ] Evaluation data is versioned, access-controlled, and appropriate for the intended use.
- [ ] Parser and scorecard benchmarks include representative formats and adversarial examples.
- [ ] Strict output validation and safe routing are tested.
- [ ] Groundedness, unsupported claims, and human agreement are measured.
- [ ] Counterfactual/proxy-risk tests run before release.
- [ ] Cross-tenant search leakage tests pass.
- [ ] Every material model/prompt/rubric change has a release report and rollback trigger.
- [ ] Production monitoring is tied to defined quality and safety thresholds.
