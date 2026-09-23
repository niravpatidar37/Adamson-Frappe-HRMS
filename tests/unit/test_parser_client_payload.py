"""What actually goes to the model server."""

import base64

from screening.model_serving.client import ResumeParserClient
from screening.model_serving.prompts import (
    RESUME_PARSER_SYSTEM_PROMPT,
    RESUME_PARSER_USER_PROMPT,
)

CLIENT = ResumeParserClient(endpoint="http://vllm:8000/v1/chat/completions", model="resume-parser")


def test_the_payload_is_openai_chat_completions_shaped():
    """vllm/vllm-openai serves this shape. The custom {system_prompt,
    user_prompt, images} wrapper the old client posted to does not exist."""
    payload = CLIENT.build_payload([b"\x89PNG-one"])

    assert payload["model"] == "resume-parser"
    assert payload["messages"][0] == {
        "role": "system",
        "content": RESUME_PARSER_SYSTEM_PROMPT,
    }
    assert payload["messages"][1]["role"] == "user"
    assert payload["messages"][1]["content"][0] == {
        "type": "text",
        "text": RESUME_PARSER_USER_PROMPT,
    }


def test_images_are_embedded_not_linked():
    """A URL would be either unauthenticated PII or credentials handed to the
    GPU node. The bytes travel in the request instead."""
    payload = CLIENT.build_payload([b"page-one-bytes", b"page-two-bytes"])
    parts = payload["messages"][1]["content"][1:]

    assert len(parts) == 2
    for part, original in zip(parts, [b"page-one-bytes", b"page-two-bytes"], strict=True):
        assert part["type"] == "image_url"
        url = part["image_url"]["url"]
        assert url.startswith("data:image/png;base64,")
        assert base64.b64decode(url.split(",", 1)[1]) == original
        assert "http" not in url


def test_sampling_is_off():
    """The same resume must parse identically on a retry; a hiring input that
    varies run to run is not reproducible evidence."""
    assert CLIENT.build_payload([b"x"])["temperature"] == 0.0
