"""Batch capacity planning (system-design.md section 13).

Scale parser capacity based on forecasted completion time, not raw
queue depth. This module is planning logic only; it does not itself
start/stop workers.
"""

from dataclasses import dataclass
from enum import StrEnum


class CapacityAction(StrEnum):
    KEEP_CURRENT = "keep_current"
    ALERT_OPERATIONS = "alert_operations"
    ADD_WORKER = "add_worker"
    ESCALATE_OR_DELAY = "escalate_or_delay"


@dataclass(frozen=True, slots=True)
class CapacityForecast:
    estimated_drain_hours: float
    action: CapacityAction


def estimate_drain_hours(
    queued_resumes: int, average_parse_seconds: float, active_parser_workers: int
) -> float:
    if active_parser_workers <= 0:
        raise ValueError("active_parser_workers must be at least 1")
    return round((queued_resumes * average_parse_seconds) / (active_parser_workers * 3600), 2)


def recommend_action(estimated_drain_hours: float, standard_sla_hours: int = 72) -> CapacityAction:
    """Thresholds are fractions of the standard SLA, matching the 0-36 /
    36-60 / 60-72 / >72 hour bands at the default 72-hour SLA."""
    low = standard_sla_hours * 0.5
    mid = standard_sla_hours * (5 / 6)

    if estimated_drain_hours <= low:
        return CapacityAction.KEEP_CURRENT
    if estimated_drain_hours <= mid:
        return CapacityAction.ALERT_OPERATIONS
    if estimated_drain_hours <= standard_sla_hours:
        return CapacityAction.ADD_WORKER
    return CapacityAction.ESCALATE_OR_DELAY


def forecast_capacity(
    queued_resumes: int,
    average_parse_seconds: float,
    active_parser_workers: int,
    standard_sla_hours: int = 72,
) -> CapacityForecast:
    drain_hours = estimate_drain_hours(
        queued_resumes, average_parse_seconds, active_parser_workers
    )
    return CapacityForecast(
        estimated_drain_hours=drain_hours,
        action=recommend_action(drain_hours, standard_sla_hours),
    )
