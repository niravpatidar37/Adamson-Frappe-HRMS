"""Engine configuration.

Everything the engine needs to know, read from the environment. The domain
package under `screening/` reads none of this — values are passed in.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SCREENING_", extra="ignore")

    environment: str = "development"

    # Audit ledger. Holds scorecards and evidence; never candidate PII beyond
    # what a scorecard needs to be explainable.
    database_url: str = "postgresql+psycopg://screening:screening@localhost:5432/screening"

    redis_url: str = "redis://localhost:6379/0"

    # Local vLLM serving qwen3-vl. Private network only.
    vlm_endpoint: str = "http://localhost:8001/parse"
    vlm_timeout_seconds: float = 180.0

    max_upload_bytes: int = 20 * 1024 * 1024
    max_resume_pages: int = 15

    # Frappe callback target, and the shared secret both sides sign with.
    frappe_base_url: str = "http://frappe-internal:8000"
    frappe_callback_path: str = "/api/method/adamson_screening_bridge.api.record_scorecard"
    # No default: an unset secret must fail loudly rather than silently
    # accepting unsigned callbacks.
    callback_secret: str = Field(min_length=32)


@lru_cache
def get_settings() -> Settings:
    return Settings()
