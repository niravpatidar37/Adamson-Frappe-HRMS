"""Fixed prompt templates for local model calls.

Per system-design.md 7.5/11.7: use the short, fixed training prompt for
the resume parser; never concatenate arbitrary instructions from
untrusted resume/JD content into the system prompt.
"""

RESUME_PARSER_SYSTEM_PROMPT = (
    "You are a resume parser. Extract information from resume images "
    "into structured JSON."
)
RESUME_PARSER_USER_PROMPT = "Parse this resume and return the structured JSON."
RESUME_PARSER_PROMPT_VERSION = "resume-parser-v1"
