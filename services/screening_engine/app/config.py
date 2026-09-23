"""Engine configuration.

Everything the engine needs to know, read from the environment. The domain
package under `screening/` reads none of this — values are passed in.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SCREENING_", extra="ignore")

    environment: str = "development"

    # Audit ledger. Holds scorecards and evidence; never candidate PII beyond
    # what a scorecard needs to be explainable.
    database_url: str = "postgresql+psycopg://screening:screening@localhost:5432/screening"

    redis_url: str = "redis://localhost:6379/0"

    # vLLM's OpenAI-compatible chat-completions endpoint. Private network
    # only. vllm/vllm-openai serves this shape; the older custom /parse
    # wrapper this once pointed at does not exist.
    vlm_endpoint: str = "http://localhost:8001/v1/chat/completions"
    vlm_model: str = "resume-parser"
    vlm_timeout_seconds: float = 180.0

    # 5 MB and 4 pages. The page cap is the binding constraint on a GPU, not
    # the model weights: every page becomes thousands of vision tokens. A
    # document over the cap goes to human review rather than being truncated,
    # because screening half a resume is worse than screening none of it.
    max_upload_bytes: int = 5 * 1024 * 1024
    max_resume_pages: int = 4

    # Off in tests, which have no broker. Also the switch that keeps the
    # pipeline from running before a deployment is ready for it.
    enqueue_screening: bool = True

    # Uploaded bytes live here until something has looked at them. Not
    # served over HTTP by anything; the worker reads it from disk.
    quarantine_root: Path = Path("/var/lib/screening/quarantine")

    # Frappe callback target, and the shared secret both sides sign with.
    frappe_base_url: str = "http://frappe-internal:8000"
    frappe_callback_path: str = "/api/method/adamson_screening_bridge.api.record_scorecard"
    # No default: an unset secret must fail loudly rather than silently
    # accepting unsigned callbacks.
    callback_secret: str = Field(min_length=32)
    # Names the secret in use. A request may carry x-screening-key-id; during
    # a rotation both sides run with the new key while the old one still
    # verifies, so neither has to restart at the same instant.
    callback_key_id: str = "v1"
    previous_callback_key_id: str | None = None
    previous_callback_secret: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
