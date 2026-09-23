"""A stand-in for vLLM that speaks the same API.

The real model needs a GPU this laptop does not have. Everything around the
model call — rendering, transport, validation, the minimization boundary, the
audit row — is testable without one, and this makes that true by answering on
the same endpoint in the same shape.

It returns a fixed CandidateProfile. It is not a model and makes no claim to
parse anything: the images are counted and discarded.
"""

import os

from fastapi import FastAPI

app = FastAPI(title="Resume parser stub", description="Not a model. Development only.")

# Deliberately a real, schema-valid CandidateProfile: the point is to prove
# the validation path accepts good output, so that the needs_review path can
# be trusted when it rejects bad output.
FIXTURE = """{
  "full_name": "Jordan Avery",
  "emails": ["jordan.avery@example.com"],
  "phones": ["+1-555-0100"],
  "skills": [{"name": "Python"}, {"name": "PostgreSQL"}, {"name": "Kubernetes"}],
  "experiences": [
    {"title": "Senior Engineer", "company": "Northwind",
     "start_date": "2021-03-01", "end_date": null},
    {"title": "Engineer", "company": "Contoso",
     "start_date": "2018-01-15", "end_date": "2021-02-28"}
  ],
  "educations": [{"institution": "University of Toronto", "degree": "BSc Computer Science"}],
  "certificates": [{"name": "AWS Solutions Architect"}]
}"""


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok", "stub": True}


@app.post("/v1/chat/completions")
async def chat_completions(body: dict) -> dict:
    images = [
        part
        for message in body.get("messages", [])
        if isinstance(message.get("content"), list)
        for part in message["content"]
        if part.get("type") == "image_url"
    ]
    return {
        "id": "stub",
        "model": body.get("model", "resume-parser"),
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": os.environ.get("STUB_OUTPUT") or FIXTURE,
                },
            }
        ],
        "usage": {"pages_received": len(images)},
    }
