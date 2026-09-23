"""Criteria drafting and authoring (system-design.md section 7.6).

Persistence-free: the functions that needed a SQLAlchemy session
(create_job_with_draft_criteria, assert_publishable) were left behind
and their job belongs to Frappe doctypes now.

Converts a job description into a proposed blueprint and enforces
recruiter/hiring-manager review before activation. Drafting is
deterministic keyword extraction, not an LLM call: "deterministic
before generative" (design principle 3), and a proposed blueprint must
still be reviewed/approved by a human before activation regardless of
how it was drafted.
"""

import re

from screening.core.exceptions import ValidationFailedError
from screening.schemas.job_blueprint import (
    DEFAULT_SCORING_WEIGHTS,
    CriterionType,
    JobBlueprint,
    MustHaveCriterion,
)

# Keyword -> normalized criterion label. Longer/more specific phrases are
# listed before the short acronyms they contain so both can still match
# independently via word-boundary search.
_SKILL_KEYWORDS: dict[str, str] = {
    "langgraph": "LangGraph",
    "crewai": "CrewAI",
    "autogen": "AutoGen",
    "langchain": "LangChain",
    "model context protocol": "Model Context Protocol (MCP)",
    "mcp": "Model Context Protocol (MCP)",
    "agent-to-agent": "Agent-to-Agent (A2A)",
    "a2a": "Agent-to-Agent (A2A)",
    "retrieval-augmented generation": "RAG pipelines",
    "rag": "RAG pipelines",
    "pinecone": "Pinecone",
    "weaviate": "Weaviate",
    "pgvector": "pgvector",
    "asyncio": "asyncio",
    "fastapi": "FastAPI",
    "opentelemetry": "OpenTelemetry",
    "python": "Python",
}

_NICE_TO_HAVE_PREFIXES = ("familiarity",)
_AUTHORIZATION_PATTERN = re.compile(r"authorized to work in ([a-z]+)", re.IGNORECASE)


def draft_blueprint_from_description(
    *, role_id: str, version: int, description: str
) -> JobBlueprint:
    """Extract must-have/nice-to-have criteria from raw JD text.

    Bullet lines starting with "Familiarity" are treated as lower-bar
    nice-to-haves; everything else matching a known skill keyword is a
    must-have. This is a starting draft only — recruiters/hiring
    managers must review before `activate_blueprint`.
    """
    must_haves: list[MustHaveCriterion] = []
    nice_to_haves: list[str] = []
    seen_must_haves: set[str] = set()

    for raw_line in description.splitlines():
        line = raw_line.strip().lstrip("-•* ").strip()
        if not line:
            continue
        lower = line.lower()
        is_nice_to_have = lower.startswith(_NICE_TO_HAVE_PREFIXES)

        for keyword, label in _SKILL_KEYWORDS.items():
            if not re.search(rf"\b{re.escape(keyword)}\b", lower):
                continue
            if is_nice_to_have:
                if label not in nice_to_haves:
                    nice_to_haves.append(label)
            elif label not in seen_must_haves:
                seen_must_haves.add(label)
                must_haves.append(MustHaveCriterion(criterion=label, type=CriterionType.SKILL))

        auth_match = _AUTHORIZATION_PATTERN.search(line)
        if auth_match:
            country = auth_match.group(1)
            criterion = f"Authorized to work in {country}"
            if criterion not in seen_must_haves:
                seen_must_haves.add(criterion)
                must_haves.append(
                    MustHaveCriterion(criterion=criterion, type=CriterionType.AUTHORIZATION)
                )

    return JobBlueprint(
        role_id=role_id,
        version=version,
        must_haves=must_haves,
        nice_to_haves=nice_to_haves,
        weights=DEFAULT_SCORING_WEIGHTS,
    )


def activate_blueprint(blueprint: JobBlueprint, approved_by: str | None) -> JobBlueprint:
    if approved_by is None:
        raise ValidationFailedError("job criteria must be approved before activation")
    return blueprint.model_copy(update={"approved_by": approved_by})


def build_blueprint_from_input(
    *,
    role_id: str,
    version: int,
    must_haves: list[MustHaveCriterion],
    nice_to_haves: list[str],
    other_requirements: list[str],
) -> JobBlueprint:
    """Build a blueprint from recruiter-authored criteria.

    The counterpart to draft_blueprint_from_description: that one proposes,
    this one records what a human decided. Disallowed-feature screening is
    enforced by JobBlueprint's own validators, so it applies identically
    however a blueprint is constructed.
    """
    return JobBlueprint(
        role_id=role_id,
        version=version,
        must_haves=must_haves,
        nice_to_haves=nice_to_haves,
        other_requirements=other_requirements,
        weights=DEFAULT_SCORING_WEIGHTS,
    )

