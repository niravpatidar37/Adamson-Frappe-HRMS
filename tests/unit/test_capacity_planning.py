from screening.services.capacity_planning import (
    CapacityAction,
    estimate_drain_hours,
    forecast_capacity,
)


def test_estimate_drain_hours_matches_planning_example() -> None:
    assert estimate_drain_hours(1000, 90, 1) == 25.0


def test_forecast_keeps_current_worker_within_low_band() -> None:
    forecast = forecast_capacity(1000, 90, 1, standard_sla_hours=72)
    assert forecast.estimated_drain_hours == 25.0
    assert forecast.action == CapacityAction.KEEP_CURRENT


def test_forecast_alerts_operations_in_mid_band() -> None:
    forecast = forecast_capacity(2000, 90, 1, standard_sla_hours=72)
    assert forecast.estimated_drain_hours == 50.0
    assert forecast.action == CapacityAction.ALERT_OPERATIONS


def test_forecast_recommends_second_worker_near_sla() -> None:
    forecast = forecast_capacity(2600, 90, 1, standard_sla_hours=72)
    assert forecast.action == CapacityAction.ADD_WORKER


def test_forecast_escalates_beyond_sla() -> None:
    forecast = forecast_capacity(4000, 90, 1, standard_sla_hours=72)
    assert forecast.action == CapacityAction.ESCALATE_OR_DELAY
