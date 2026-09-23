"""The screening pipeline.

    receipt -> page images -> VLM parse -> validate -> scoring profile
            -> rules -> score -> audit row -> callback to Frappe

Order matters. Rules run before scoring: an eligibility result of UNKNOWN
routes to human review without a model ever seeing the candidate, and a FAIL
is only ever emitted for an explicit, high-confidence disqualifier.
"""

from app.workers.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def screen_resume(self, receipt_id: str) -> None:
    """Parse, evaluate and score one resume.

    TODO: blocked on the spike. Needs, in order:
      1. where quarantined bytes live before scanning (spike question 5)
      2. PDF/DOCX to page images
      3. ResumeParserClient against local vLLM, endpoint from settings
      4. CandidateProfile.model_validate; invalid output goes to review,
         never to rejection
      5. build_scoring_profile — the only thing the scoring model may see
      6. evaluate_eligibility, then score only if not FAIL
      7. write ScorecardAudit
      8. signed callback to Frappe with score, recommendation, evidence URL

    Every step already exists in `screening/` except 1, 2 and 8.
    """
    raise NotImplementedError("pipeline is blocked on spike questions 4 and 5")
