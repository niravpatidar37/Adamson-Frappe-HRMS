# Adamson Frappe HRMS

Frappe HR as the system of record and recruiter UI, with a private AI
screening engine alongside it. Everything runs on Adamson's own server.

See [ADR 0001](docs/adr/0001-decoupled-hybrid-architecture.md) for why.

```
Frappe HR ──1. applicant + resume──▶ Screening Gateway (FastAPI)
    ▲                                        │
    │                                  2. queue (Redis)
    │                                        ▼
    │                                 Worker pool ──▶ vLLM (GPU, on-prem)
    └──────3. signed callback: score, recommendation, evidence link
```

Frappe never sees the parsed profile or the evidence behind a score.

## Layout

```
apps/adamson_screening_bridge/   Frappe app: dispatch and record. No ML.
services/screening_engine/
  app/                           FastAPI, Celery workers, audit ledger
  screening/                     domain core — imports no framework
deploy/                          compose, GPU stack, reverse proxy
tests/unit/                      39 tests, no database, sub-second
tests/integration/               API, worker and ledger tests
docs/                            design, governance, ADRs
```

## Run the tests

```powershell
uv run --with pydantic --with httpx --with pytest pytest tests/unit -q
```

No Frappe, no database, no containers. If that ever stops being true,
something has imported a framework into `screening/`.

## Status

The domain core is ported and green. The engine's API, workers and ledger are
scaffolded but not implemented, and the bridge raises `NotImplementedError` by
design — both are blocked on [spike questions 4 and 5](docs/phase-0-spike.md):
whether Frappe's queue survives a 180-second model call, and where quarantined
files live before anything scans them.

Nothing is enabled until callback signature verification exists. A score
influences a hiring decision, and an unauthenticated endpoint that writes one
is not acceptable.
