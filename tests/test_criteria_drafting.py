from screening.services.criteria_drafting import draft_blueprint_from_description

_JOB_DESCRIPTION = """
Responsibilities

- Design and implement agentic workflows for teams including Human Resources, Marketing, Software Development, Manufacturing, and Product Development.
- Build planning and reasoning loops, including task decomposition, reflection, autonomous execution, and workflow handoffs.
- Develop secure tool and API integrations that allow agents to interact safely with files, databases, services, and internal systems.
- Create multi-agent systems that coordinate specialized agents through structured communication and orchestration.
- Establish guardrails, observability, and monitoring to improve reliability, safety, and performance in production environments.
- Collaborate with engineering and business stakeholders to identify automation opportunities and turn them into practical AI solutions.

Qualifications

- Experience with agent orchestration frameworks such as LangGraph, CrewAI, AutoGen, or LangChain.
- Familiarity with integration standards and protocols such as Model Context Protocol (MCP) and Agent-to-Agent (A2A) frameworks.
- Experience building Retrieval-Augmented Generation (RAG) pipelines and working with vector databases such as Pinecone, Weaviate, or pgvector.
- Advanced Python development skills, including asynchronous programming with asyncio.
- Experience developing APIs using FastAPI or similar frameworks.
- Understanding of observability, monitoring, safety, and governance practices for AI systems, including tools such as OpenTelemetry.
- Ability to translate business or engineering needs into scalable, maintainable AI-enabled workflows.

Requirements added by the job poster

- Authorized to work in Canada
"""


def test_draft_extracts_must_have_skills_from_qualifications() -> None:
    blueprint = draft_blueprint_from_description(
        role_id="role_agentic_ai", version=1, description=_JOB_DESCRIPTION
    )
    must_have_labels = {c.criterion for c in blueprint.must_haves}

    for expected in (
        "LangGraph",
        "CrewAI",
        "AutoGen",
        "LangChain",
        "RAG pipelines",
        "Pinecone",
        "Weaviate",
        "pgvector",
        "Python",
        "asyncio",
        "FastAPI",
        "OpenTelemetry",
    ):
        assert expected in must_have_labels


def test_draft_treats_familiarity_bullets_as_nice_to_have() -> None:
    blueprint = draft_blueprint_from_description(
        role_id="role_agentic_ai", version=1, description=_JOB_DESCRIPTION
    )
    must_have_labels = {c.criterion for c in blueprint.must_haves}

    assert "Model Context Protocol (MCP)" in blueprint.nice_to_haves
    assert "Agent-to-Agent (A2A)" in blueprint.nice_to_haves
    assert "Model Context Protocol (MCP)" not in must_have_labels


def test_draft_extracts_work_authorization_requirement() -> None:
    blueprint = draft_blueprint_from_description(
        role_id="role_agentic_ai", version=1, description=_JOB_DESCRIPTION
    )
    auth_criteria = [c for c in blueprint.must_haves if c.criterion.startswith("Authorized")]

    assert len(auth_criteria) == 1
    assert auth_criteria[0].criterion == "Authorized to work in Canada"
