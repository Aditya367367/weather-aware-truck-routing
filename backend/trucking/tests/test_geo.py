import pytest

from trucking.domain.geo import Polyline, distance_marks, haversine_mi


def test_haversine_known_distance():
    la, ny = (34.0522, -118.2437), (40.7128, -74.0060)
    assert haversine_mi(la, ny) == pytest.approx(2445, rel=0.01)


def test_marks_include_destination_and_point_at_interpolates():
    p = Polyline([(0.0, 0.0), (0.0, 1.0)])  # ~69 mi along the equator
    marks = distance_marks(p.length_mi, 25)
    assert marks[:3] == [0, 25, 50] and marks[-1] == pytest.approx(p.length_mi)
    assert p.point_at(p.length_mi / 2)[1] == pytest.approx(0.5, abs=1e-3)
    assert p.point_at(10_000) == p.points[-1]  # clamped


def test_retraced_miles_flags_out_and_back_spurs_only():
    straight = Polyline([(40.0, -101.0), (40.0, -99.0)])
    with_spur = Polyline([(40.0, -101.0), (40.0, -100.0), (40.0, -99.7), (40.0, -100.0), (40.0, -99.0)])
    assert straight.retraced_mi() == 0
    assert with_spur.retraced_mi() > 10
