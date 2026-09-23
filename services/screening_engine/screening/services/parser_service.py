"""Parser service orchestration (system-design.md section 7.5).

Coordinates calling the resume-parser model, validating JSON output
against the CandidateProfile schema, and deciding whether to route to
manual review.
"""

import json

from pydantic import ValidationError

from screening.core.exceptions import ParserOutputInvalidError
from screening.model_serving.client import ResumeParserClient
from screening.schemas.candidate_profile import CandidateProfile


class ParserService:
    def __init__(self, client: ResumeParserClient | None = None) -> None:
        self._client = client or ResumeParserClient()

    async def parse_resume(self, page_image_urls: list[str]) -> tuple[CandidateProfile | None, str]:
        """Return (profile_or_none, raw_output).

        On invalid JSON or schema-validation failure, returns
        (None, raw_output) so the caller can mark the application
        `needs_review` rather than silently rejecting the candidate.
        """
        raw_output = await self._client.parse(page_image_urls)
        try:
            data = json.loads(raw_output)
            profile = CandidateProfile.model_validate(data)
        except (json.JSONDecodeError, ValidationError):
            return None, raw_output
        return profile, raw_output


def require_profile(profile: CandidateProfile | None) -> CandidateProfile:
    if profile is None:
        raise ParserOutputInvalidError("resume parser returned invalid JSON")
    return profile
