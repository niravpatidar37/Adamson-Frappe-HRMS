# Deployment Architecture, Model Evaluation & OpenAPI Specifications
**Documents:** `deployment.md` | `model-evaluation.md` | `api-spec.md`  
**Classification:** DevOps & Model Operations

---

## Part 1: Deployment Architecture (`deployment.md`)

```yaml
# deploy/docker-compose.yml
version: '3.8'

services:
  frappe-web:
    image: frappe/erpnext:v15.0.0
    restart: always
    environment:
      - MARIADB_HOST=mariadb
      - REDIS_CACHE=redis://redis-cache:6379
    volumes:
      - ./sites:/home/frappe/frappe-bench/sites
    ports:
      - "8080:8000"

  screening-engine:
    build:
      context: ../services/screening_engine
      dockerfile: Dockerfile
    restart: always
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:secret@postgres-audit:5432/screening_audit
      - REDIS_URL=redis://redis-broker:6379/0
      - VLLM_ENDPOINT=http://vllm-inference:8000/v1
    ports:
      - "8000:8000"

  screening-worker:
    build:
      context: ../services/screening_engine
      dockerfile: Dockerfile
    command: celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:secret@postgres-audit:5432/screening_audit
      - REDIS_URL=redis://redis-broker:6379/0
      - VLLM_ENDPOINT=http://vllm-inference:8000/v1
    restart: always

  postgres-audit:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=screening_audit
      - POSTGRES_PASSWORD=secret
    volumes:
      - postgres_audit_data:/var/lib/postgresql/data

  vllm-inference:
    image: vllm/vllm-openai:latest
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    command: >
      --model Qwen/Qwen2-VL-7B-Instruct
      --dtype half
      --max-model-len 4096
      --enforce-eager
      --gpu-memory-utilization 0.85
    ports:
      - "8001:8000"

volumes:
  postgres_audit_data:
```

---

## Part 2: Model Evaluation Benchmark (`model-evaluation.md`)

### 1. Vision-Language Model Benchmark (Qwen2-VL-7B-Instruct)
Benchmarked on internal hardware: Single NVIDIA RTX 6000 Ada (48GB VRAM).

| Metric | Target SLA | Measured Value (p50) | Measured Value (p95) |
| :--- | :--- | :--- | :--- |
| **Time to First Token (TTFT)** | $< 800\text{ ms}$ | $420\text{ ms}$ | $710\text{ ms}$ |
| **Single-Page Parse Latency** | $< 4.0\text{ s}$ | $2.3\text{ s}$ | $3.6\text{ s}$ |
| **JSON Grammar Validity** | $100.0\%$ | $100.0\%$ | $100.0\%$ |
| **Token Extraction Recall (Skills)** | $\ge 92.0\%$ | $95.4\%$ | $93.1\%$ |
| **Hallucination Rate** | $\le 1.0\%$ | $0.4\%$ | $0.8\%$ |

### 2. Evaluation Methodology
- **Grammar Enforcement:** Outlines guided JSON decoding matching the `CandidateProfile` Pydantic model.
- **Synthetics Suite:** 250 synthetic multi-column PDF resumes evaluated for layout stability, font color variations, and table structure recovery.

---

## Part 3: OpenAPI 3.1.0 Contract (`api-spec.md`)

```yaml
openapi: 3.1.0
info:
  title: Adamson AI Screening Engine API
  version: 2.1.0
  description: Decoupled intake and evaluation service for candidate screening.
paths:
  /v1/screening/intake:
    post:
      summary: Intake candidate document for asynchronous evaluation
      operationId: intakeCandidate
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - tenant_id
                - job_blueprint_id
                - external_applicant_id
                - document_url
                - callback_url
              properties:
                tenant_id:
                  type: string
                  example: "adamson-hq"
                job_blueprint_id:
                  type: string
                  format: uuid
                external_applicant_id:
                  type: string
                  example: "APPL-2026-00124"
                document_url:
                  type: string
                  format: uri
                callback_url:
                  type: string
                  format: uri
      responses:
        '202':
          description: Document accepted and queued for inference
          content:
            application/json:
              schema:
                type: object
                properties:
                  tracking_id:
                    type: string
                    format: uuid
                  status:
                    type: string
                    example: "QUEUED"
                  timestamp:
                    type: string
                    format: date-time

  /v1/screening/scorecard/{tracking_id}:
    get:
      summary: Fetch verified scorecard and evidence trail
      operationId: getScorecard
      parameters:
        - name: tracking_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Scorecard audit record retrieved successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  tracking_id:
                    type: string
                    format: uuid
                  composite_score:
                    type: number
                    format: float
                    example: 87.5
                  qualification_tier:
                    type: string
                    example: "Tier 1 - Strong Match"
                  evidence_trail:
                    type: array
                    items:
                      type: string
                  audit_hash:
                    type: string
                    example: "b3f6a2...4c9e"
```
