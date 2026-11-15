# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
import json
from pathlib import Path

import pytest
from twinfinder import reference

SITES = [
    {"name": "Near", "lat": 66.0, "lon": -52.0, "tier": "B", "body": "Moon"},
    {"name": "Far", "lat": 10.0, "lon": 10.0, "tier": "A", "body": "Mars"},
]


def body(name, lat, lon, radius, lo, hi):
    return {"name": name, "lat": lat, "lon": lon, "radius_km": radius, "an_low": lo, "an_high": hi}


def test_one_degree_of_latitude_is_about_111_km():
    assert reference.haversine_km(0.0, 0.0, 1.0, 0.0) == pytest.approx(111.2, abs=0.2)


def test_nearest_known_within_50_km():
    hit = reference.nearest_known(66.2, -52.0, SITES)
    assert hit["name"] == "Near"
    assert hit["tier"] == "B"
    assert hit["distance_km"] == pytest.approx(22.2, abs=0.3)


def test_nearest_known_is_none_beyond_the_limit():
    assert reference.nearest_known(70.0, -52.0, SITES) is None


def test_rock_score_follows_feldspar_calcium_number():
    assert reference.rock_match(66.0, -52.0, [body("A", 66.0, -52.0, 5, 83, 83)]) == (pytest.approx(0.74), "A")
    assert reference.rock_match(66.0, -52.0, [body("B", 66.0, -52.0, 5, 86, 88)]) == (pytest.approx(0.82), "B")
    assert reference.rock_match(66.0, -52.0, [body("C", 66.0, -52.0, 5, None, None)]) == (pytest.approx(0.5), "C")


def test_rock_score_is_zero_outside_every_body():
    assert reference.rock_match(60.0, 0.0, [body("A", 66.0, -52.0, 5, 83, 83)]) == (0.0, None)


def test_rock_score_takes_the_best_overlapping_body():
    bodies = [body("Poor", 66.0, -52.0, 20, 50, 50), body("Good", 66.0, -52.0, 20, 90, 90)]
    assert reference.rock_match(66.0, -52.0, bodies) == (pytest.approx(0.88), "Good")


def test_margin_extends_the_radius():
    bodies = [body("A", 66.0, -52.0, 5, 83, 83)]
    assert reference.rock_match(66.1, -52.0, bodies) == (0.0, None)          # 11 km away
    assert reference.rock_match(66.1, -52.0, bodies, margin_km=8)[1] == "A"


# The hand-compiled list itself: rock scores at named bodies, pinned so a data edit cannot move them unnoticed.
BODIES_FILE = Path(__file__).resolve().parents[1] / "data" / "reference" / "anorthosite_bodies.json"


def listed_body(fragment):
    (found,) = [b for b in json.loads(BODIES_FILE.read_text()) if fragment in b["name"]]
    return found


def score_at(fragment):
    b = listed_body(fragment)
    score, name = reference.rock_match(b["lat"], b["lon"], json.loads(BODIES_FILE.read_text()))
    assert name == b["name"]
    return score


def test_fiskenaesset_scores_by_its_drill_core_mean():
    b = listed_body("Fiskenaesset")
    assert (b["an_low"], b["an_high"]) == (86, 88)   # An87 +/- 1
    assert score_at("Fiskenaesset") == pytest.approx(0.82)


def test_lofoten_scores_by_its_published_plagioclase_range():
    b = listed_body("Lofoten")
    assert (b["an_low"], b["an_high"]) == (47, 57)
    assert 0.12 - 1e-9 <= score_at("Lofoten") <= 0.16


def test_qaqortorsuaq_score_is_unchanged():
    assert score_at("Qaqortorsuaq") == pytest.approx(0.736)


def test_changed_rock_values_carry_a_source_and_a_note():
    for fragment in ("Fiskenaesset", "Lofoten"):
        b = listed_body(fragment)
        assert b["an_source"].startswith("https://")
        assert b["rock_note"]


def test_bodies_without_a_published_value_stay_unknown():
    for fragment in ("Bergen Arcs", "Eliseev"):
        b = listed_body(fragment)
        assert b["an_low"] is None and b["an_high"] is None
        assert reference.an_score(b) == reference.UNKNOWN_AN_SCORE
