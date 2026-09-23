"""HTTP client for the internal `sukhrobnurali/qwen3vl-resume-parser`
model-serving endpoint (system-design.md section 7.5/7.9).

The endpoint is only reachable from private-network processing
workloads; this client does not implement any public network egress.
"""

import httpx

from screening.model_serving.prompts import (
    RESUME_PARSER_SYSTEM_PROMPT,
    RESUME_PARSER_USER_PROMPT,
)


class ResumeParserClient:
    def __init__(self, endpoint: str, timeout: float = 180.0) -> None:
        """The endpoint is injected rather than read from global settings.

        Under Frappe this comes from site config; the client should not know
        where its configuration lives.
        """
        self._endpoint = endpoint
        self._timeout = timeout

    async def parse(self, page_image_urls: list[str]) -> str:
        """Call the model server and return the raw text output.

        Callers are responsible for JSON validation; the model has ~88%
        JSON validity on held-out eval and truncated/invalid output must
        be routed to manual review, not auto-repaired beyond documented
        strategies.
        """
        payload = {
            "system_prompt": RESUME_PARSER_SYSTEM_PROMPT,
            "user_prompt": RESUME_PARSER_USER_PROMPT,
            "images": page_image_urls,
            "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(self._endpoint, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["output"]
