# AI Governance Standard

> **Ported from the `HR-Screening` repo**, where it was written against a
> FastAPI + SQLAlchemy implementation. The requirements, threat analysis,
> security model and privacy rules still hold. Anything naming FastAPI
> routers, SQLAlchemy models, Alembic or arq queues describes the previous
> implementation and is now Frappe's responsibility — see
> [frappe-mapping.md](frappe-mapping.md). Not yet revised.

> **Scope:** Local resume parser, job-description structuring, candidate scorecard generation, embeddings/search, and optional local outreach drafting.
>
> **Principle:** AI assists authorized human decision makers; it does not independently make employment decisions.

## 1. Governance objectives

- Ensure models are used only for approved, documented purposes.
- Prevent automated output from becoming an unreviewed employment decision.
- Maintain reproducibility through model, prompt, schema, rubric, and policy versioning.
- Measure extraction accuracy, groundedness, reliability, bias risks, and operational impact before and after deployment.
- Maintain an immediate rollback path for every AI component.
- Protect candidate data and prevent unintended training/telemetry use.

## 2. Approved AI use cases

| Use case | Allowed output | Human control | Prohibited behavior |
|---|---|---|---|
| Resume parsing | Schema-validated candidate profile with confidence | Recruiter may correct; low confidence routes to review | Treating extracted fields as verified facts |
| JD structuring | Draft job blueprint | Hiring manager/recruiter must approve before activation | Self-activating criteria or hidden criteria changes |
| Eligibility support | Evidence for explicit deterministic rules | Low confidence routes to review | Implicit/prompt-only eligibility decision |
| Candidate scorecard | Criterion-level evidence, gaps, uncertainties, bounded numeric components | Recruiter reviews and makes final decision | `hire`/`reject` decision or autonomous workflow action |
| Candidate search | Authorized retrieval/reranking within scope | Recruiter chooses records to view/use | Retrieval beyond tenant/job/role permissions |
| Outreach draft | Draft based on approved template and permitted fields | Recruiter approves exact message | Unapproved external send |

## 3. Prohibited AI uses

- Autonomous hire, rejection, interview invitation, or other consequential employment action.
- Inference or scoring based on protected characteristics or unapproved proxy attributes.
- Personality, emotion, honesty, culture-fit, health, disability, age, ethnicity, or socioeconomic inference from résumé content or images.
- Model tool access that can alter criteria, access arbitrary records, export data, send communications, or change permissions.
- Training foundation models on candidate data without explicit, documented approval and appropriate legal/privacy basis.
- Using candidate data in external model services without an approved data-transfer/privacy/security assessment.

## 4. Model inventory

Maintain a version-controlled model registry. Every deployed model must have:

| Field | Requirement |
|---|---|
| Model ID and version | Immutable name/version/artifact hash |
| Purpose | Approved use case and owner |
| Source/license | Repository/source, license, commercial-use constraints |
| Deployment | Environment, endpoint, hardware, image digest |
| Data classification | Allowed input/output sensitivity |
| Prompt/schema compatibility | Supported prompt and JSON-schema versions |
| Evaluation | Dataset version, metrics, thresholds, results, known limitations |
| Security review | Dependency/model artifact scan, trust-remote-code decision, network controls |
| Privacy review | Data flow, retention, telemetry/training settings |
| Rollback target | Last approved release and rollback procedure |
| Approval | AI owner, security, privacy/HR approvals as appropriate |

## 5. Change-management gates

A change to a model, adapter, quantization, serving runtime, prompt, schema, embedding model, scoring weight, criteria generation behavior, or output handling requires:

1. Pull request with version increment and rationale.
2. Updated model registry entry and relevant documentation.
3. Automated quality, schema, security, prompt-injection, and regression tests.
4. Evaluation against the locked benchmark and review of deltas.
5. Staging deployment with telemetry and rollback verification.
6. Approval by the accountable AI engineering owner; require HR/privacy/security review for material behavior or data-flow changes.
7. Production release with monitoring and a defined rollback trigger.

No production release may silently change a prompt, rubric, model artifact, or parsing schema.

## 6. Human oversight design

The recruiter UI must show:

- Job criteria version and scorecard generation time.
- Source résumé evidence for every claimed skill/experience match.
- Missing evidence, ambiguities, parser confidence, and model limitations.
- Human correction history and model/review version lineage.
- Clear actions: shortlist, reject, hold, request review, and override.
- Mandatory reason capture for material overrides or decisions where policy requires it.

The system records whether a recruiter followed, ignored, or modified the AI recommendation. High override rates, systematic disagreement, or unexplained distribution shifts are quality signals—not user errors to suppress.

## 7. Prompt and output controls

- Store prompts as versioned source files, not ad hoc strings in application code.
- Use a fixed system instruction and delimit untrusted document/JD content as data.
- Use JSON-schema constrained output where the runtime supports it; validate again server-side.
- Reject unexpected fields, unsafe text, invalid enums, and unsupported evidence references.
- Keep prompts minimal; remove disallowed fields and unrelated candidate information.
- Store only prompt version and output hash in routine logs; retain raw PII-bearing prompts/outputs only in tightly restricted processing storage when operationally necessary.
- Disable tool use for parsing/scoring unless separately designed, allow-listed, and approved.

## 8. Quality, fairness, and monitoring

### Minimum metrics

- Parser JSON validity rate.
- Field-level extraction precision/recall or agreement against human labels.
- Scorecard evidence-groundedness rate.
- Unsupported-claim/hallucination rate.
- Human correction and override rate by model/rubric/role.
- Manual-review routing rate and reason distribution.
- Score distribution by role, criteria version, and processing condition.
- Processing latency, error rate, retry rate, and cost per application.

### Fairness review

- Review all rubric inputs for protected/proxy attributes before activation.
- Sample low-scoring and rejected candidates to identify false negatives or extraction failures.
- Use representative, lawfully obtained evaluation data.
- Where legally permitted and governed, measure adverse-impact indicators with privacy safeguards and appropriate statistical interpretation.
- Freeze or roll back a model/rubric if material quality, reliability, or fairness concerns are identified.

## 9. Incident response for AI behavior

Examples of AI incidents:

- Model returns malformed or incomplete profiles above threshold.
- Evidence citations are frequently unsupported.
- A new prompt/model changes rankings materially without an approved criteria change.
- Prompt injection causes policy-violating output.
- A scoring policy uses prohibited/proxy information.
- A model service sends PII to an unapproved destination.

Response:

1. Freeze the affected model/prompt/rubric release.
2. Disable auto-progression to scoring or route affected work to manual review.
3. Preserve restricted evidence required for investigation.
4. Assess candidate impact and whether prior outcomes need re-review.
5. Roll back to the last approved release or use deterministic/manual workflow.
6. Document root cause, corrective action, test coverage gap, and release criteria update.

## 10. Governance acceptance checklist

- [ ] Every production model is present in the registry with immutable artifact/version and approval evidence.
- [ ] Every model/prompt/rubric change has automated regression results and rollback plan.
- [ ] AI outputs are schema-validated, evidence-backed, and cannot directly make decisions or send messages.
- [ ] Recruiters can view source evidence and override results.
- [ ] Prohibited attributes and proxy features are excluded from scoring design.
- [ ] Quality, fairness, override, and reliability signals are monitored.
- [ ] Candidate PII is not used for training/telemetry without explicit approved policy.
- [ ] AI incidents have a documented disable/rollback and candidate-impact review path.
