"""Client for the local vLLM server hosting the resume parser.

Speaks vLLM's OpenAI-compatible chat-completions API, because that is what
`vllm/vllm-openai` actually serves. An earlier version of this client posted
`{system_prompt, user_prompt, images, extra_body}` to a custom `/parse`
wrapper that does not exist in this repository; vLLM rejects that shape.

Page images travel as base64 `data:` URLs inside the request body, not as
links for the model server to fetch. A link would be either unauthenticated —
candidate PII on an open endpoint — or would need the GPU node to hold
credentials. Same reasoning that makes Frappe POST resume bytes to this
service rather than a URL, one hop further down.

Reachable only from private-network processing workloads; this client
implements no public egress.
"""

import base64

import httpx

from screening.model_serving.prompts import (
    RESUME_PARSER_SYSTEM_PROMPT,
    RESUME_PARSER_USER_PROMPT,
)


class ResumeParserClient:
    def __init__(self, *, endpoint: str, model: str, timeout: float = 180.0) -> None:
        """Endpoint and model are injected rather than read from settings.

        The domain package does not know where its configuration lives, which
        is what lets the same code run against vLLM here and a stub in tests.
        """
        self._endpoint = endpoint
        self._model = model
        self._timeout = timeout

    @staticmethod
    def _data_url(image: bytes, media_type: str) -> str:
        return f"data:{media_type};base64,{base64.b64encode(image).decode()}"

    def build_payload(self, page_images: list[bytes], *, media_type: str = "image/png") -> dict:
        """Separated from the call so a test can assert on what gets sent
        without standing up a server."""
        content: list[dict] = [{"type": "text", "text": RESUME_PARSER_USER_PROMPT}]
        content.extend(
            {"type": "image_url", "image_url": {"url": self._data_url(image, media_type)}}
            for image in page_images
        )
        return {
            "model": self._model,
            "messages": [
                {"role": "system", "content": RESUME_PARSER_SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            # A hiring input must not vary between identical runs. Sampling
            # would make the same resume parse differently on a retry.
            "temperature": 0.0,
            "chat_template_kwargs": {"enable_thinking": False},
        }

    async def parse(self, page_images: list[bytes], *, media_type: str = "image/png") -> str:
        """Call the model server and return the raw text output.

        Validation is the caller's job. The model does not always emit valid
        JSON, and invalid output must be routed to human review rather than
        repaired beyond documented strategies — or, worse, treated as a
        rejection.
        """
        if not page_images:
            raise ValueError("no page images to parse")

        payload = self.build_payload(page_images, media_type=media_type)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(self._endpoint, json=payload)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
