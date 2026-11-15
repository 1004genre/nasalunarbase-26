# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Cloud column from NASA POWER (decision 17 of the version 3 plan). No test touches the network."""
from __future__ import annotations

import datetime
import json
import math
import urllib.error

import pytest

from twinfinder import cloud, sun

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# The first two grid boxes and the header of a real answer of the regional climatology
# service (asked on 14 November 2026 for 63 to 65 N, 24 to 20 W, CLOUD_AMT), unchanged.
REAL_ANSWER = (
    '{"features":[{"type":"Feature","geometry":{"type":"Point","coordinates":[-23.5,63.5,0.13]},'
    '"properties":{"parameter":{"CLOUD_AMT":{"JAN":85.59,"FEB":83.07,"MAR":83.37,"APR":81.52,'
    '"MAY":77.87,"JUN":83.49,"JUL":83.62,"AUG":80.65,"SEP":82.56,"OCT":79.98,"NOV":84.11,'
    '"DEC":84.69,"ANN":82.54}}}},{"type":"Feature","geometry":{"type":"Point","coordinates":'
    '[-22.5,63.5,0.95]},"properties":{"parameter":{"CLOUD_AMT":{"JAN":85.6,"FEB":83.07,"MAR":83.38,'
    '"APR":81.5,"MAY":77.87,"JUN":83.48,"JUL":83.64,"AUG":80.64,"SEP":82.56,"OCT":79.98,"NOV":84.1,'
    '"DEC":84.69,"ANN":82.54}}}}],"header":{"title":"NASA/POWER Source Native Resolution '
    'Climatology Climatologies","api":{"version":"v2.10.1","name":"POWER Climatology API"},'
    '"sources":["SYN1DEG"],"fill_value":-999.0,"time_standard":"LST","start":"20010101",'
    '"end":"20251231"},"messages":["The requested parameters are retrieved from a pre-computed '
    'climatological period (January 2001 - December 2025)"],"parameters":{"CLOUD_AMT":{"units":"%",'
    '"longname":"Cloud Amount"}},"times":{"data":0.046,"process":0.01},"type":"FeatureCollection"}'
)

ERROR_ANSWER = (
    '{"header":"The POWER Climatology API failed to complete your request; please review the '
    'errors below and the POWER Docs (https://power.larc.nasa.gov/docs/).","messages":["Please '
    'provide a maximum of 10 degree range in latitude."]}'
)


def answer(boxes: dict, parameter: str = "CLOUD_AMT", fill=-999.0, with_fill_header: bool = True) -> str:
    """A made-up answer in the service's layout. boxes maps (lat, lon) to 12 values."""
    features = []
    for (lat, lon), values in boxes.items():
        months = dict(zip(MONTHS, values))
        months["ANN"] = 50.0
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat, 12.3]},  # GeoJSON: longitude first
            "properties": {"parameter": {parameter: months}},
        })
    header = {"api": {"version": "v2.10.1", "name": "POWER Climatology API"}, "sources": ["SYN1DEG"],
              "start": "20010101", "end": "20251231"}
    if with_fill_header:
        header["fill_value"] = fill
    return json.dumps({"features": features, "header": header, "type": "FeatureCollection"})


# ---- reading a raw answer -------------------------------------------------------------------

def test_read_answer_reads_a_real_answer_with_latitude_first_and_january_first():
    got = cloud.read_answer(REAL_ANSWER, "CLOUD_AMT")
    assert set(got) == {(63.5, -23.5), (63.5, -22.5)}
    assert got[(63.5, -23.5)] == [85.59, 83.07, 83.37, 81.52, 77.87, 83.49, 83.62, 80.65, 82.56, 79.98, 84.11, 84.69]
    assert got[(63.5, -22.5)][0] == 85.6 and got[(63.5, -22.5)][11] == 84.69
    assert all(len(values) == 12 for values in got.values())  # the yearly mean "ANN" is left out


def test_read_answer_accepts_bytes_and_parsed_json():
    assert cloud.read_answer(REAL_ANSWER.encode(), "CLOUD_AMT") == cloud.read_answer(REAL_ANSWER, "CLOUD_AMT")
    assert cloud.read_answer(json.loads(REAL_ANSWER), "CLOUD_AMT") == cloud.read_answer(REAL_ANSWER, "CLOUD_AMT")


def test_read_answer_turns_the_fill_value_into_null_not_a_number():
    values = [-999.0, -999, 40.0] + [50.0] * 9
    got = cloud.read_answer(answer({(80.5, 20.5): values}), "CLOUD_AMT")[(80.5, 20.5)]
    assert got[0] is None and got[1] is None
    assert got[2] == 40.0
    assert all(v is None or 0.0 <= v <= 100.0 for v in got)


def test_read_answer_uses_the_fill_value_the_header_names():
    values = [-99.0] + [50.0] * 11
    got = cloud.read_answer(answer({(80.5, 20.5): values}, fill=-99.0), "CLOUD_AMT")[(80.5, 20.5)]
    assert got[0] is None and got[1] == 50.0


def test_read_answer_knows_the_usual_fill_value_when_the_header_is_silent():
    values = [-999.0] + [50.0] * 11
    text = answer({(80.5, 20.5): values}, with_fill_header=False)
    assert cloud.read_answer(text, "CLOUD_AMT")[(80.5, 20.5)][0] is None


def test_read_answer_keeps_a_real_zero_and_a_real_hundred():
    values = [0.0, 100.0] + [50.0] * 10
    got = cloud.read_answer(answer({(80.5, 20.5): values}), "CLOUD_AMT")[(80.5, 20.5)]
    assert got[0] == 0.0 and got[0] is not None
    assert got[1] == 100.0


def test_read_answer_a_missing_month_is_null():
    data = json.loads(answer({(80.5, 20.5): [50.0] * 12}))
    del data["features"][0]["properties"]["parameter"]["CLOUD_AMT"]["MAR"]
    data["features"][0]["properties"]["parameter"]["CLOUD_AMT"]["APR"] = None
    got = cloud.read_answer(data, "CLOUD_AMT")[(80.5, 20.5)]
    assert got[2] is None and got[3] is None and got[4] == 50.0


def test_read_answer_does_not_depend_on_the_order_of_the_months_in_the_file():
    data = json.loads(answer({(80.5, 20.5): [float(m) for m in range(12)]}))
    months = data["features"][0]["properties"]["parameter"]["CLOUD_AMT"]
    data["features"][0]["properties"]["parameter"]["CLOUD_AMT"] = dict(reversed(list(months.items())))
    assert cloud.read_answer(data, "CLOUD_AMT")[(80.5, 20.5)] == [float(m) for m in range(12)]


def test_read_answer_refuses_an_error_answer():
    with pytest.raises(ValueError):
        cloud.read_answer(ERROR_ANSWER, "CLOUD_AMT")
    with pytest.raises(ValueError):
        cloud.read_answer("<html>busy</html>", "CLOUD_AMT")


def test_read_answer_refuses_an_answer_for_another_parameter():
    with pytest.raises(ValueError):
        cloud.read_answer(REAL_ANSWER, "CLOUD_AMT_DAY")


def test_read_answer_refuses_a_percent_that_is_neither_fill_nor_between_0_and_100():
    with pytest.raises(ValueError):
        cloud.read_answer(answer({(80.5, 20.5): [120.0] + [50.0] * 11}), "CLOUD_AMT")
    with pytest.raises(ValueError):
        cloud.read_answer(answer({(80.5, 20.5): [-5.0] + [50.0] * 11}), "CLOUD_AMT")


def test_answer_header_reports_what_the_service_said():
    head = cloud.answer_header(REAL_ANSWER)
    assert head["version"] == "v2.10.1"
    assert head["sources"] == ["SYN1DEG"]
    assert head["start"] == "20010101" and head["end"] == "20251231"
    assert head["fill_value"] == -999.0


# ---- the grid box of a cell ------------------------------------------------------------------

@pytest.mark.parametrize("lat, lon, box", [
    (63.88, -22.45, (63.5, -22.5)),      # Reykjanes
    (74.7, -94.97, (74.5, -94.5)),       # Resolute
    (78.2, 15.6, (78.5, 15.5)),          # Longyearbyen
    (-68.55, 78.15, (-68.5, 78.5)),      # Vestfold Hills
    (-77.6, 161.5, (-77.5, 161.5)),      # McMurdo Dry Valleys
    (59.05, -109.1, (59.5, -109.5)),
    (-87.35, -179.4, (-87.5, -179.5)),
    (0.2, 0.2, (0.5, 0.5)),
    (-0.2, -0.2, (-0.5, -0.5)),
])
def test_grid_box_is_the_centre_of_the_one_degree_box_that_holds_the_point(lat, lon, box):
    assert cloud.grid_box(lat, lon) == box


def test_grid_box_a_point_on_an_edge_goes_to_the_box_above_and_to_the_east():
    assert cloud.grid_box(75.0, 141.25) == (75.5, 141.5)   # Kotelny Island, on a latitude edge
    assert cloud.grid_box(-85.05, 3.0) == (-85.5, 3.5)
    # a cell centre that should be 3.0 but carries rounding noise lands in the same box
    assert cloud.grid_box(-85.05, 2.9999999999) == (-85.5, 3.5)
    assert cloud.grid_box(63.99999999999, 10.5) == (64.5, 10.5)


def test_grid_box_wraps_at_the_date_line_and_stops_at_the_poles():
    assert cloud.grid_box(70.2, 180.0) == (70.5, -179.5)
    assert cloud.grid_box(70.2, -180.0) == (70.5, -179.5)
    assert cloud.grid_box(70.2, 179.85) == (70.5, 179.5)
    assert cloud.grid_box(90.0, 10.2) == (89.5, 10.5)
    assert cloud.grid_box(-90.0, 10.2) == (-89.5, 10.5)


def test_grid_box_holds_the_point():
    for lat, lon in [(59.05, -109.1), (82.75, -61.3), (-60.65, -45.5), (-87.35, 179.4), (66.45, 13.95)]:
        box_lat, box_lon = cloud.grid_box(lat, lon)
        assert abs(box_lat - lat) <= 0.5 and abs(box_lon - lon) <= 0.5
        assert box_lat % 1 == 0.5 and box_lon % 1 == 0.5


# ---- ten-day bins and the clear share ---------------------------------------------------------

def test_bin_rule_is_the_projects_bin_rule():
    for day in range(1, 367):
        assert cloud.bin_index(day) == min((day - 1) // 10, 35)
        assert cloud.bin_index(day) == sun.bin_index(day)


def test_each_bin_takes_the_month_of_its_middle_day():
    assert len(cloud.BIN_MONTH) == 36
    for b in range(36):
        days = [d for d in range(1, 366) if cloud.bin_index(d) == b]
        middle = (days[0] + days[-1]) / 2          # 10 b + 5.5 for a ten-day bin; 358 for the last bin
        below = (datetime.date(2025, 1, 1) + datetime.timedelta(days=math.floor(middle) - 1)).month
        above = (datetime.date(2025, 1, 1) + datetime.timedelta(days=math.ceil(middle) - 1)).month
        assert below == above, "no bin has its middle on a month boundary"
        assert cloud.BIN_MONTH[b] == below - 1


def test_each_bin_keeps_its_month_in_a_leap_year_but_for_two_ties():
    """In a leap year the middle of bin 30 falls between 31 October and 1 November, and the
    middle of bin 33 between 30 November and 1 December: two ties. Each bin keeps the later
    month, the one it has in a 365-day year."""
    ties = []
    for b in range(36):
        days = [d for d in range(1, 367) if cloud.bin_index(d) == b]
        middle = (days[0] + days[-1]) / 2
        months = {(datetime.date(2024, 1, 1) + datetime.timedelta(days=day - 1)).month - 1
                  for day in (math.floor(middle), math.ceil(middle))}
        assert cloud.BIN_MONTH[b] in months
        if len(months) > 1:
            ties.append(b)
    assert ties == [30, 33]
    assert cloud.BIN_MONTH[30] == 10 and cloud.BIN_MONTH[33] == 11


def test_every_month_gets_three_bins():
    assert list(cloud.BIN_MONTH) == [b // 3 for b in range(36)]


def test_clear_share_by_bin_is_one_minus_cloud_over_100_for_the_month_of_the_bin():
    pct = [5.0 * m for m in range(12)]          # January 0 %, February 5 %, ... December 55 %
    share = cloud.clear_share_by_bin(pct)
    assert len(share) == 36
    assert share[0] == share[1] == share[2] == 1.0
    assert share[3] == pytest.approx(0.95)
    assert share[20] == pytest.approx(0.70)      # bin 20 = 20 to 29 July
    assert share[21] == pytest.approx(0.65)      # bin 21 = 30 July to 8 August: middle day in August
    assert share[35] == pytest.approx(0.45)
    for b in range(36):
        assert share[b] == pytest.approx(1.0 - pct[cloud.BIN_MONTH[b]] / 100.0)


def test_clear_share_of_a_real_month():
    share = cloud.clear_share_by_bin([85.59, 83.07, 83.37, 81.52, 77.87, 83.49, 83.62, 80.65, 82.56, 79.98, 84.11, 84.69])
    assert share[0] == pytest.approx(0.1441)
    assert share[22] == pytest.approx(0.1935)


def test_clear_share_full_overcast_is_zero_not_null_and_a_clear_sky_is_one():
    share = cloud.clear_share_by_bin([100.0] * 6 + [0.0] * 6)
    assert share[0] == 0.0 and share[0] is not None
    assert share[35] == 1.0


def test_clear_share_null_in_null_out():
    assert cloud.clear_share_by_bin(None) == [None] * 36
    pct = [50.0] * 12
    pct[6] = None                                  # July unknown
    pct[11] = float("nan")                         # December unknown, as an array would say it
    share = cloud.clear_share_by_bin(pct)
    assert share[18] is None and share[19] is None and share[20] is None
    assert share[33] is None and share[34] is None and share[35] is None
    assert [b for b, v in enumerate(share) if v is None] == [18, 19, 20, 33, 34, 35]
    assert share[17] == 0.5 and share[21] == 0.5
    assert cloud.clear_share_by_bin([None] * 12) == [None] * 36


def test_clear_share_never_turns_null_into_zero():
    share = cloud.clear_share_by_bin([None] * 12)
    assert 0 not in share and 0.0 not in share


def test_clear_share_takes_a_numpy_array():
    import numpy as np
    pct = np.full(12, 40.0)
    pct[0] = np.nan
    share = cloud.clear_share_by_bin(pct)
    assert share[0] is None and share[3] == pytest.approx(0.6)
    assert all(v is None or type(v) is float for v in share)


def test_clear_share_refuses_a_list_that_is_not_twelve_months_or_not_a_percent():
    with pytest.raises(ValueError):
        cloud.clear_share_by_bin([50.0] * 11)
    with pytest.raises(ValueError):
        cloud.clear_share_by_bin([50.0] * 11 + [120.0])
    with pytest.raises(ValueError):
        cloud.clear_share_by_bin([-999.0] + [50.0] * 11)   # a fill value must never get this far


# ---- what to ask the service for ---------------------------------------------------------------

@pytest.mark.parametrize("box, tile", [
    ((63.5, -22.5), (60, 70, -30, -20)),
    ((-77.5, 161.5), (-80, -70, 160, 170)),
    ((59.5, 179.5), (50, 60, 170, 180)),
    ((-87.5, -179.5), (-90, -80, -180, -170)),
    ((82.5, -0.5), (80, 90, -10, 0)),
    ((60.5, 0.5), (60, 70, 0, 10)),
])
def test_tile_of_is_the_ten_degree_block_that_holds_the_box(box, tile):
    assert cloud.tile_of(box) == tile


def test_tiles_respect_the_limits_of_a_regional_request():
    boxes = [(lat + 0.5, lon + 0.5) for lat in (-88, -61, 59, 60, 69, 70, 83) for lon in range(-180, 180, 7)]
    tiles = cloud.tiles_for(boxes)
    assert tiles == sorted(set(tiles))
    for lat_min, lat_max, lon_min, lon_max in tiles:
        assert 2 <= lat_max - lat_min <= 10 and 2 <= lon_max - lon_min <= 10
        assert -90 <= lat_min < lat_max <= 90 and -180 <= lon_min < lon_max <= 180
    for box in boxes:
        holders = [t for t in tiles if t[0] < box[0] < t[1] and t[2] < box[1] < t[3]]
        assert holders == [cloud.tile_of(box)]


def test_regional_url_asks_for_one_parameter_and_sends_no_personal_detail():
    url = cloud.regional_url("CLOUD_AMT", (60, 70, -30, -20))
    assert url == ("https://power.larc.nasa.gov/api/temporal/climatology/regional"
                   "?latitude-min=60&latitude-max=70&longitude-min=-30&longitude-max=-20"
                   "&parameters=CLOUD_AMT&community=RE&format=JSON")
    assert "user" not in url and "@" not in url and "," not in url
    assert url == cloud.URL_PATTERN.format(lat_min=60, lat_max=70, lon_min=-30, lon_max=-20, parameter="CLOUD_AMT")


def test_raw_name_is_one_file_per_parameter_and_tile():
    names = {cloud.raw_name(p, t) for p in cloud.PARAMETERS for t in [(60, 70, -30, -20), (60, 70, 20, 30), (-70, -60, -30, -20)]}
    assert len(names) == 9
    assert all(name.endswith(".json") and "/" not in name and " " not in name for name in names)
    assert cloud.raw_name("CLOUD_AMT", (60, 70, -30, -20)) == "CLOUD_AMT_N60_N70_W030_W020.json"
    assert cloud.raw_name("CLOUD_AMT_DAY", (-70, -60, 0, 10)) == "CLOUD_AMT_DAY_S70_S60_E000_E010.json"


def test_the_three_cloud_parameters():
    assert cloud.PARAMETERS == ("CLOUD_AMT", "CLOUD_AMT_DAY", "CLOUD_AMT_NIGHT")
    assert cloud.USER_AGENT == "twinfinder/0.1"


# ---- fetching, with a stand-in for the network --------------------------------------------------

class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeNet:
    """Answers in turn with the given items: bytes are a good answer, an int is that HTTP error."""

    def __init__(self, items, retry_after=None):
        self.items = list(items)
        self.requests = []
        self.retry_after = retry_after

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        item = self.items.pop(0)
        if isinstance(item, int):
            headers = {"Retry-After": str(self.retry_after)} if self.retry_after is not None else {}
            raise urllib.error.HTTPError(request.full_url, item, "error", headers, None)
        return FakeResponse(item)


TILE = (60, 70, -30, -20)
GOOD = answer({(63.5, -22.5): [80.0] * 12}).encode()


def test_fetch_tile_saves_the_raw_answer_unchanged_and_names_itself(tmp_path):
    net, naps = FakeNet([GOOD]), []
    path, asked = cloud.fetch_tile("CLOUD_AMT", TILE, tmp_path, opener=net, sleep=naps.append)
    assert asked is True
    assert path == tmp_path / "CLOUD_AMT_N60_N70_W030_W020.json"
    assert path.read_bytes() == GOOD
    assert [p.name for p in tmp_path.iterdir()] == ["CLOUD_AMT_N60_N70_W030_W020.json"]   # no part file left
    (request,) = net.requests
    assert request.full_url == cloud.regional_url("CLOUD_AMT", TILE)
    assert request.get_header("User-agent") == "twinfinder/0.1"
    assert set(k.lower() for k in request.headers) == {"user-agent"}


def test_fetch_tile_makes_no_request_when_the_answer_is_already_on_disk(tmp_path):
    net = FakeNet([GOOD])
    cloud.fetch_tile("CLOUD_AMT", TILE, tmp_path, opener=net, sleep=lambda s: None)
    again = FakeNet([])
    path, asked = cloud.fetch_tile("CLOUD_AMT", TILE, tmp_path, opener=again, sleep=lambda s: None)
    assert asked is False and again.requests == []
    assert path.read_bytes() == GOOD


def test_fetch_tile_waits_and_tries_again_when_told_too_many_requests(tmp_path):
    net, naps = FakeNet([429, 429, GOOD]), []
    path, asked = cloud.fetch_tile("CLOUD_AMT", TILE, tmp_path, opener=net, sleep=naps.append)
    assert asked is True and path.read_bytes() == GOOD
    assert len(net.requests) == 3
    assert len(naps) == 2 and all(nap >= 5 for nap in naps) and naps[1] >= naps[0]


def test_fetch_tile_waits_as_long_as_the_service_asks(tmp_path):
    net, naps = FakeNet([429, GOOD], retry_after=42), []
    cloud.fetch_tile("CLOUD_AMT", TILE, tmp_path, opener=net, sleep=naps.append)
    assert naps == [42.0]


def test_fetch_tile_gives_up_after_a_few_refusals_and_leaves_nothing_behind(tmp_path):
    net = FakeNet([429] * 20)
    with pytest.raises(urllib.error.HTTPError):
        cloud.fetch_tile("CLOUD_AMT", TILE, tmp_path, opener=net, sleep=lambda s: None, attempts=4)
    assert len(net.requests) == 4
    assert list(tmp_path.iterdir()) == []


def test_fetch_tile_does_not_retry_a_request_the_service_calls_wrong(tmp_path):
    net = FakeNet([422, GOOD])
    with pytest.raises(urllib.error.HTTPError):
        cloud.fetch_tile("CLOUD_AMT", TILE, tmp_path, opener=net, sleep=lambda s: None)
    assert len(net.requests) == 1
    assert list(tmp_path.iterdir()) == []


def test_fetch_tile_does_not_keep_an_answer_it_cannot_read(tmp_path):
    net = FakeNet([ERROR_ANSWER.encode()])
    with pytest.raises(ValueError):
        cloud.fetch_tile("CLOUD_AMT", TILE, tmp_path, opener=net, sleep=lambda s: None)
    assert list(tmp_path.iterdir()) == []


def test_fetch_tile_stops_and_reports_when_asked_to_log_in(tmp_path):
    for code in (401, 403):
        net = FakeNet([code, GOOD])
        with pytest.raises(urllib.error.HTTPError):
            cloud.fetch_tile("CLOUD_AMT", TILE, tmp_path, opener=net, sleep=lambda s: None)
        assert len(net.requests) == 1


# ---- from raw answers to the table of cells ---------------------------------------------------

def write_raw(raw_dir, parameter, tile, boxes):
    (raw_dir / cloud.raw_name(parameter, tile)).write_text(answer(boxes, parameter))


CELLS = [
    {"id": "63.8_-22.6", "lat": 63.85, "lon": -22.5},
    {"id": "63.9_-22.6", "lat": 63.95, "lon": -22.5},      # same grid box as the cell above
    {"id": "64.0_-21.4", "lat": 64.05, "lon": -21.3},
    {"id": "-77.6_161.4", "lat": -77.55, "lon": 161.65},
]


def test_boxes_of_cells_lists_each_grid_box_once():
    assert cloud.boxes_of(CELLS) == [(-77.5, 161.5), (63.5, -22.5), (64.5, -21.5)]


def test_read_raw_reads_every_tile_of_a_parameter_and_fails_on_a_missing_file(tmp_path):
    write_raw(tmp_path, "CLOUD_AMT", (60, 70, -30, -20), {(63.5, -22.5): [80.0] * 12, (64.5, -21.5): [70.0] * 12})
    with pytest.raises(FileNotFoundError):
        cloud.read_raw(tmp_path, "CLOUD_AMT", cloud.tiles_for(cloud.boxes_of(CELLS)))
    write_raw(tmp_path, "CLOUD_AMT", (-80, -70, 160, 170), {(-77.5, 161.5): [-999.0] * 12})
    by_box = cloud.read_raw(tmp_path, "CLOUD_AMT", cloud.tiles_for(cloud.boxes_of(CELLS)))
    assert by_box[(63.5, -22.5)] == [80.0] * 12
    assert by_box[(-77.5, 161.5)] == [None] * 12


def test_cells_table_has_the_layout_of_decision_17():
    by_box = {(63.5, -22.5): [80.0] * 12, (64.5, -21.5): [70.0] * 11 + [None], (-77.5, 161.5): [None] * 12}
    table = cloud.cells_table(CELLS, by_box)
    assert list(table) == [c["id"] for c in CELLS]
    assert table["63.8_-22.6"] == {"cloud_pct": [80.0] * 12, "grid": [63.5, -22.5]}
    assert table["63.9_-22.6"] == table["63.8_-22.6"]
    assert table["64.0_-21.4"] == {"cloud_pct": [70.0] * 11 + [None], "grid": [64.5, -21.5]}
    # a box without any value is null as a whole, never twelve zeros
    assert table["-77.6_161.4"] == {"cloud_pct": None, "grid": [-77.5, 161.5]}
    json.dumps(table, allow_nan=False)   # plain JSON, no NaN


def test_cells_table_a_box_the_service_did_not_return_is_null():
    table = cloud.cells_table(CELLS[:1], {})
    assert table["63.8_-22.6"] == {"cloud_pct": None, "grid": [63.5, -22.5]}


def test_cells_table_can_carry_the_day_and_night_versions_beside_the_main_one():
    by_box = {(63.5, -22.5): [80.0] * 12}
    day = {(63.5, -22.5): [None] + [75.0] * 11}
    night = {(63.5, -22.5): [85.0] * 5 + [None] * 2 + [85.0] * 5}
    table = cloud.cells_table(CELLS[:1], by_box, extra={"cloud_pct_day": day, "cloud_pct_night": night})
    assert table["63.8_-22.6"] == {
        "cloud_pct": [80.0] * 12, "grid": [63.5, -22.5],
        "cloud_pct_day": [None] + [75.0] * 11,
        "cloud_pct_night": [85.0] * 5 + [None] * 2 + [85.0] * 5,
    }


# ---- the meta block ---------------------------------------------------------------------------

def test_meta_is_filled_from_the_answers_that_were_used():
    head = cloud.answer_header(REAL_ANSWER)
    meta = cloud.meta_from([head, head], fetched="2026-11-14T23:10:00Z")
    for key in ("source", "parameter", "period", "grid_deg", "fetched", "url_pattern"):   # decision 17
        assert key in meta
    assert meta["parameter"] == "CLOUD_AMT"
    assert meta["period"] == "2001-01-01 to 2025-12-31"
    assert meta["grid_deg"] == 1.0
    assert meta["fetched"] == "2026-11-14T23:10:00Z"
    assert meta["url_pattern"] == cloud.URL_PATTERN
    assert "POWER" in meta["source"] and "v2.10.1" in meta["source"] and "SYN1DEG" in meta["source"]
    assert meta["fill_value"] == -999.0
    assert "all hours" in meta["what_it_is"]
    assert "low" in meta["what_it_is_not"] and "not" in meta["what_it_is_not"].lower()
    json.dumps(meta, allow_nan=False)


def test_meta_refuses_answers_that_disagree_about_period_or_source():
    head = cloud.answer_header(REAL_ANSWER)
    with pytest.raises(ValueError):
        cloud.meta_from([head, dict(head, end="20241231")], fetched="x")
    with pytest.raises(ValueError):
        cloud.meta_from([head, dict(head, sources=["MERRA2"])], fetched="x")
    with pytest.raises(ValueError):
        cloud.meta_from([], fetched="x")


def test_meta_of_the_daylight_version_names_its_own_parameter_and_sources():
    """The service names the sources of the daylight and night versions as SYN1DEG and POWER."""
    head = dict(cloud.answer_header(REAL_ANSWER), sources=["SYN1DEG", "POWER"])
    meta = cloud.meta_from([head], fetched="x", parameter="CLOUD_AMT_DAY")
    assert meta["parameter"] == "CLOUD_AMT_DAY"
    assert "SYN1DEG, POWER" in meta["source"]
    assert cloud.meta_from([head], fetched="x")["parameter"] == "CLOUD_AMT"


# ---- added by the count check of version 3 (a breakage that no test caught)

def test_fetch_tile_tries_again_after_a_server_fault(tmp_path):
    net, naps = FakeNet([503, GOOD]), []
    path, asked = cloud.fetch_tile("CLOUD_AMT", TILE, tmp_path, opener=net, sleep=naps.append)
    assert asked is True and path.read_bytes() == GOOD
    assert len(net.requests) == 2 and len(naps) == 1
