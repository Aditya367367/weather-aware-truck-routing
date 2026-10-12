from trucking.domain.risk import Risk
from trucking.domain.scoring import coverage_miles, explain, rank, score_route

L, M, H, S = Risk.LOW, Risk.MODERATE, Risk.HIGH, Risk.SEVERE


def test_coverage_sums_to_route_length():
    marks = [0, 25, 50, 60]
    cov = coverage_miles(marks)
    assert cov == [12.5, 25.0, 17.5, 5.0] and sum(cov) == 60


def test_score_aggregates_miles_by_level():
    s = score_route([L, S, H, M], [0, 25, 50, 60], 3600)
    assert (s.severe_miles, s.high_miles, s.moderate_miles) == (25.0, 17.5, 5.0)
    assert s.max_risk == S


def test_ranking_prefers_fewer_severe_over_speed():
    fast_but_severe = score_route([S, L], [0, 100], 3_000)
    slow_but_safe = score_route([L, L], [0, 100], 9_000)
    assert rank([fast_but_severe, slow_but_safe]) == [1, 0]
    assert "Severe" in explain(slow_but_safe, fast_but_severe)


def test_ties_fall_through_to_travel_time():
    a = score_route([L, L], [0, 100], 7_200)
    b = score_route([L, L], [0, 100], 3_600)
    assert rank([a, b]) == [1, 0] and "travel time" in explain(b, a)


def test_no_travel_beats_everything():
    blocked = score_route([Risk.NO_TRAVEL, L], [0, 100], 1_000)
    severe = score_route([S, S], [0, 100], 9_000)
    assert rank([blocked, severe]) == [1, 0]
