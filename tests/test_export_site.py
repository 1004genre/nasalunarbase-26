"""The export for the map page: what the page reads must say what the pipeline files say."""
import importlib
import json
from pathlib import Path

import numpy as np
import pytest

export_site = importlib.import_module("scripts.export_site")

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
REFERENCE = ROOT / "data" / "reference"
LAND = ROOT / "data" / "raw" / "naturalearth" / "ne_50m_land.geojson"
NAN = float("nan")
TARGETS = [("connecting-ridge", "Shackleton-de Gerlache connecting ridge", 2.08),
           ("malapert", "Malapert Massif", 5.55),
           ("mons-mouton", "Mons Mouton plateau", 6.11),
           ("nobile-rim-2", "Nobile Rim 2", 7.59)]
WINTER = [27, 28, 29, 30, 31, 32, 33, 34, 35, 0, 1, 2, 3, 4, 5, 6, 7, 8]
SUMMER = list(range(9, 27))
ROCK = [33, 34, 35, 0, 1, 2, 3, 4, 5]


# ---- small made-up inputs ----

def _target_values(v3: bool, north: bool, known_snow: bool, horizon: bool, clear: bool) -> dict:
    values = {
        "flat_hours": 400.0, "snow_free_hours": 200.0 if known_snow else None,
        "open_hours": 100.0 if (known_snow and horizon) else None,
        "long_flat_hours": 300.0,
        "long_snow_free_hours": 150.0 if known_snow else None,
        "long_open_hours": 80.0 if (known_snow and horizon and north) else None,
        "long_snow_free_hours_winter": 10.0 if known_snow else None,
        "long_snow_free_hours_summer": 140.0 if known_snow else None,
        "long_open_hours_winter": 5.0 if (known_snow and horizon and north) else None,
        "long_open_hours_summer": 75.0 if (known_snow and horizon and north) else None,
        "long_snow_free_hours_as_mapped": 160.0 if known_snow else None,
        "summer_rock_hours": None if north else 120.0,
        "long_summer_rock_hours": None if north else 90.0,
        "long_summer_rock_open_hours": None if north or not horizon else 40.0,
        "longest_stretch_h": 5.5, "best_stretch_bin": 20, "poleward_share": 0.6,
        "top_bins": [[20, 30.0], [21, 20.0]], "all_day_days": 3, "usable_days": 1.0 if known_snow else None,
    }
    if v3 and known_snow:
        values["long_snow_free_hours_with_rule"] = 150.0
    if clear and horizon:
        if north and known_snow:
            values.update(long_open_hours_clear=30.0, long_open_hours_clear_winter=2.0,
                          long_open_hours_clear_summer=28.0)
        if not north:
            values["long_summer_rock_open_hours_clear"] = 15.0
    return values


EXTRA = [  # more cells for the tests that need them: southern without a horizon, southern outside the screen,
    # and a northern cell whose horizon was refused
    ("-71.0_11.0", -71.05, 11.15, "S", "unmeasured", False, True),
    ("-72.0_12.0", -72.05, 12.15, "S", "unmeasured", True, False),
    ("66.0_-179.9", 66.05, -179.85, "N", "measured", "skipped", True),
]
SKIPPED = "window at 66.15, -179.85 crosses the antimeridian (longitudes 179 to -179); not supported"


def make_inputs(folder: Path, v3: bool, cloud: bool, seed: int = 3, extra: bool = False) -> Path:
    """A derived folder with seven cells: three measured (two with a horizon), doubtful, no data, southern, and a
    named one outside the screen. With extra=True three more (see EXTRA)."""
    rng = np.random.default_rng(seed)
    spec = [  # id, lat, lon, hemisphere, status, horizon, gridded
        ("70.0_20.0", 70.05, 20.15, "N", "measured", True, True),
        ("70.0_20.3", 70.05, 20.45, "N", "measured", False, True),
        ("64.0_-20.0", 64.05, -19.85, "N", "measured", True, True),
        ("74.4_19.0", 74.45, 19.25, "N", "doubtful", True, True),
        ("80.0_-40.0", 80.05, -39.5, "N", "no data", False, True),
        ("-70.0_10.0", -70.05, 10.15, "S", "unmeasured", True, True),
        ("68.0_13.2", 68.05, 13.35, "N", "measured", True, False),
    ]
    if extra:
        spec += EXTRA
    n = len(spec)
    flat = rng.uniform(0.0, 60.0, (n, 4, 36)).astype(np.float32)
    flat[:, :, 10:14] = 0.0
    for i, (_, lat, *_rest) in enumerate(spec):   # flat hours depend on latitude only
        for j, (_, other, *_r) in enumerate(spec[:i]):
            if other == lat:
                flat[i] = flat[j]
    stretch = rng.uniform(0.0, 6.0, (n, 4, 36)).astype(np.float32)
    odds = rng.uniform(0.0, 1.0, (n, 1, 36)).astype(np.float32)
    snow_free = flat * odds
    share = rng.uniform(0.2, 1.0, (n, 4, 36)).astype(np.float32)
    opened = snow_free * share
    cells = []
    for i, (cid, lat, lon, hemi, status, horizon, gridded) in enumerate(spec):
        known_snow = status in ("measured", "doubtful")
        if not known_snow:
            snow_free[i] = NAN
        if hemi == "S":
            opened[i] = flat[i] * share[i]
        if horizon is not True or (hemi == "N" and not known_snow):
            opened[i] = NAN
        snow = {"status": status, "source": "3x3" if known_snow else None,
                "land_pixels": 6 if hemi == "N" else None, "stuck_winters": 3 if status == "doubtful" else
                (0 if hemi == "N" else None)}
        if v3 and hemi == "N":
            snow["block_pixels"] = 9
            snow["odds_used"] = "as mapped" if status == "measured" else "stale-flag rule"
        cells.append({
            "id": cid, "lat": lat, "lon": lon, "hemisphere": hemi,
            "region": "Testland" if hemi == "N" else "Southland", "bare": 0.5, "land_share": 0.8,
            "cell_km2": 120.0, "bare_km2": 48.0 + i, "layers_disagree": None if hemi == "N" else False,
            "gridded": gridded, "snow": snow,
            "horizon": ({"north_deg": 1.2, "south_deg": -0.1, "valid_share": 0.9, "pixel_m": 60.0} if horizon is True
                        else {"skipped": SKIPPED} if horizon == "skipped" else None),
            "targets": {t: _target_values(v3, hemi == "N", known_snow, horizon is True, False) for t, _, _ in TARGETS},
        })
        if not gridded:
            cells[-1]["named_site"] = True
            cells[-1]["site_name"] = ("Lofoten anorthosite (Nusfjord), Norway" if hemi == "N"
                                      else "Test nunatak, Antarctica")
    meta = {"targets": [{"id": t, "name": name, "limit_deg": limit, "elev_bins": [0]} for t, name, limit in TARGETS],
            "stretch_min_h": 2.0, "bin_days": 10, "n_bins": 36, "winter_bins_north": WINTER,
            "summer_bins_north": SUMMER, "summer_bins_south": ROCK,
            "counts": {"north_cells": 5, "south_cells": 1}}
    if v3:
        meta["long_rule"] = "per-day spells"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "grazing_cells.json").write_text(json.dumps({"meta": meta, "cells": cells}))
    arrays = {"ids": np.array([c["id"] for c in cells]), "targets": np.array([t for t, _, _ in TARGETS]),
              "flat": flat, "snow_free": snow_free, "open": opened, "stretch": stretch}
    if v3:
        part = rng.uniform(0.3, 1.0, (n, 4, 36)).astype(np.float32)
        for i in range(n):
            for j in range(i):
                if spec[i][1] == spec[j][1]:
                    part[i] = part[j]
        arrays["long_flat"] = flat * part
        arrays["long_snow_free"] = snow_free * part
        arrays["long_open"] = opened * part
    np.savez(folder / "grazing_bins.npz", **arrays)
    scored = []
    for c in cells[:1] + cells[2:4] + cells[5:6] + cells[7:]:
        north = c["hemisphere"] == "N"
        record = {k: c[k] for k in ("id", "lat", "lon", "hemisphere", "region", "gridded", "bare", "bare_km2",
                                    "land_share", "snow", "horizon")}
        record.update({
            "site_name": None,
            "terrain": {"median_slope_deg": 6.4, "p90_slope_deg": 13.9, "relief_m": 234.1, "valid_share": 0.9,
                        "overlap": {t: 0.5 for t, _, _ in TARGETS}},
            "rock": {"score": 0.0, "body": None}, "known": None,
            "known_region": None if c["id"] != "64.0_-20.0" else "Iceland: named in the challenge as widely studied",
            "little_known": c["id"] != "64.0_-20.0", "ranking": "north" if north else "south",
            "ranked": (c["snow"]["status"] in ("measured", "unmeasured") and c["gridded"]
                       and "north_deg" in (c["horizon"] or {})),
            "not_ranked_because": [] if c["snow"]["status"] != "doubtful" else ["snow doubtful"],
            "targets": {},
        })
        if cloud and v3:
            record["cloud"] = {"pct_by_month": [70.0] * 12}
        for t, _, _ in TARGETS:
            known_snow = c["snow"]["status"] in ("measured", "doubtful")
            values = _target_values(v3, north, known_snow, "north_deg" in (c["horizon"] or {}), cloud and v3)
            values.update({"light": 0.4, "terrain": 0.6, "bare": 0.5, "rock": 0.0,
                           "goals": {"lighting": 0.447 if north else 0.3, "shadows": 0.2, "geology": 0.0, "full": 0.0},
                           "top_bins_summer_rock": [[35, 9.0]], "poleward_share_summer_rock": 1.0})
            record["targets"][t] = values
        scored.append(record)
    (folder / "cells_scored.json").write_text(json.dumps({
        "meta": {"full_hours": 200.0, "rank_min_bare": 0.25, "same_site_km": 50.0, "stretch_min_h": 2.0},
        "cells": scored}))
    if cloud:
        (folder / "cloud_cells.json").write_text(json.dumps({
            "meta": {"source": "NASA POWER", "parameter": "CLOUD_AMT", "period": "2001-2020", "grid_deg": 1.0,
                     "fetched": "2026-11-14", "url_pattern": "https://power.larc.nasa.gov/..."},
            "cells": {c["id"]: {"cloud_pct": ([60.0 + m for m in range(12)] if c["id"] != "80.0_-40.0" else
                                              [None] * 12), "grid": [c["lat"], c["lon"]]} for c in cells}}))
    return folder


def run(tmp_path: Path, v3: bool, cloud: bool, extra: bool = False, patch=None) -> tuple[Path, Path]:
    """Make the inputs, optionally change them (patch gets the grazing and the scored records by id), export."""
    derived = make_inputs(tmp_path / "derived", v3, cloud, extra=extra)
    if patch is not None:
        grazing = json.loads((derived / "grazing_cells.json").read_text())
        scored = json.loads((derived / "cells_scored.json").read_text())
        patch({c["id"]: c for c in grazing["cells"]}, {c["id"]: c for c in scored["cells"]})
        (derived / "grazing_cells.json").write_text(json.dumps(grazing))
        (derived / "cells_scored.json").write_text(json.dumps(scored))
    out = tmp_path / "site" / "data"
    export_site.export(derived, tmp_path / "no_reference", None, out)
    return derived, out


def yearly_of(out: Path, target: str = "malapert") -> dict:
    return export_site.read_yearly(out, load(out, "cells.json")["n"], [t for t, _, _ in TARGETS])[target]


def load(out: Path, name: str):
    return json.loads((out / name).read_text())


def read_bins(out: Path, name: str, n: int) -> np.ndarray:
    return np.frombuffer((out / name).read_bytes(), dtype=np.uint8).reshape(n, 4, 36)


# ---- encoding ----

def test_encoding_keeps_half_hours_and_never_turns_unknown_into_zero():
    hours = np.array([0.0, 0.2, 0.26, 12.4, 126.9, 127.0, 127.3, 300.0, NAN], dtype=np.float32)
    coded = export_site.encode_hours(hours)
    assert coded.dtype == np.uint8
    assert coded.tolist() == [0, 0, 1, 25, 254, 254, 254, 254, 255]
    back = export_site.decode_hours(coded)
    assert np.isnan(back[-1])
    assert np.all(np.abs(back[:5] - hours[:5]) <= 0.25 + 1e-6)


def test_a_tiny_positive_value_may_round_to_zero_but_unknown_never_does():
    coded = export_site.encode_hours(np.array([NAN, 0.01, NAN], dtype=np.float32))
    assert coded.tolist() == [255, 0, 255]


def test_bins_have_calendar_labels_and_the_month_of_the_middle_day():
    bins = export_site.bin_table()
    assert len(bins) == 36
    assert bins[0]["label"] == "1 Jan-10 Jan" and bins[0]["first_day"] == 1 and bins[0]["last_day"] == 10
    assert bins[21]["label"] == "30 Jul-8 Aug" and bins[21]["month"] == 8
    assert bins[22]["label"] == "9 Aug-18 Aug"
    assert bins[35]["label"] == "17 Dec-31 Dec" and bins[35]["last_day"] == 365 and bins[35]["month"] == 12
    assert bins[3]["month"] == 2


def test_clear_share_takes_each_bin_month():
    share = export_site.clear_share_by_bin([10.0 * m for m in range(12)])
    assert len(share) == 36
    assert share[0] == pytest.approx(1.0) and share[35] == pytest.approx(1.0 - 1.1)
    assert share[21] == pytest.approx(1.0 - 0.7)
    assert all(np.isnan(v) for v in export_site.clear_share_by_bin([None] * 12))


# ---- long-window hours per bin: version 3 arrays when present, the version 2 rule when not ----

def test_version_2_rule_counts_a_bin_whose_stretch_is_two_hours(tmp_path):
    derived, out = run(tmp_path, v3=False, cloud=False)
    z = np.load(derived / "grazing_bins.npz")
    meta = load(out, "meta.json")
    assert "ten-day" in meta["long_rule"]["used"]
    n = len(z["ids"])
    want = np.where(z["stretch"] >= 2.0, z["snow_free"], 0.0)
    got = export_site.decode_hours(read_bins(out, "snowfree.bin", n))
    known = ~np.isnan(want)
    assert np.all(np.abs(got[known] - np.minimum(want[known], 127.0)) <= 0.25 + 1e-4)
    assert np.all(np.isnan(got[np.isnan(want)]))
    unknown_cell = list(z["ids"]).index("80.0_-40.0")
    counted = z["stretch"][unknown_cell] >= 2.0
    assert np.all(read_bins(out, "snowfree.bin", n)[unknown_cell][counted & (z["flat"][unknown_cell] > 0)] == 255)


def test_version_3_arrays_are_used_when_present(tmp_path):
    derived, out = run(tmp_path, v3=True, cloud=True)
    z = np.load(derived / "grazing_bins.npz")
    meta = load(out, "meta.json")
    assert meta["long_rule"]["used"] == "per-day spells"
    n = len(z["ids"])
    for name, key in (("snowfree.bin", "long_snow_free"), ("open.bin", "long_open")):
        want = z[key]
        raw = read_bins(out, name, n)
        got = export_site.decode_hours(raw)
        known = ~np.isnan(want)
        assert np.all(np.abs(got[known] - np.minimum(want[known], 127.0)) <= 0.25 + 1e-4)
        assert np.all(raw[~known] == 255)


@pytest.mark.parametrize("v3,cloud", [(False, False), (True, True), (True, False), (False, True)])
def test_export_runs_with_and_without_the_version_3_fields(tmp_path, v3, cloud):
    derived, out = run(tmp_path, v3, cloud)
    meta = load(out, "meta.json")
    cells = load(out, "cells.json")
    n = cells["n"]
    assert n == 7 and len(cells["ids"]) == n
    for name in ("snowfree.bin", "open.bin"):
        assert (out / name).stat().st_size == n * 4 * 36
    assert (out / "snowodds.bin").stat().st_size == n * 36
    assert meta["has_cloud"] is cloud
    assert (out / "cloud.bin").exists() is cloud
    if cloud:
        raw = np.frombuffer((out / "cloud.bin").read_bytes(), dtype=np.uint8).reshape(n, 12)
        assert raw[0].tolist() == [60 + m for m in range(12)]
        assert raw[cells["ids"].index("80.0_-40.0")].tolist() == [255] * 12
    for name in ("calendar.json", "sites.json", "flat.json", "profile.json", "copy.json", "land.json"):
        assert (out / name).exists(), name
    copy = load(out, "copy.json")
    assert copy["headline"] == "Where and when Earth copies the low Sun of the Moon's south pole"
    assert copy["subline"] and copy["purpose"]
    for key in ("headline", "subline", "purpose"):               # no sentence over 25 words on the page
        for sentence in copy[key].split(". "):
            assert len(sentence.split()) <= 25, sentence
    assert [t["id"] for t in meta["targets"]] == [t for t, _, _ in TARGETS]
    assert meta["targets"][1]["shadow_m"] == pytest.approx(1 / np.tan(np.radians(5.55)), abs=0.01)


def test_cells_columns_all_have_one_entry_per_cell_in_the_npz_order(tmp_path):
    derived, out = run(tmp_path, v3=True, cloud=True)
    z = np.load(derived / "grazing_bins.npz")
    cells = load(out, "cells.json")
    n = cells["n"]
    assert cells["ids"] == [str(i) for i in z["ids"]]
    for key in ("lat", "lon", "region", "bare", "bare_km2", "snow", "horizon_n", "horizon_s", "flat_row", "known"):
        assert len(cells[key]) == n, key
    assert len(cells["hemisphere"]) == n and len(cells["ranked"]) == n
    spec = cells["yearly"]
    assert spec["shape"] == [n, 4, len(spec["fields"])]
    assert (out / spec["file"]).stat().st_size == n * 4 * len(spec["fields"]) * 2


def test_unknown_is_minus_one_or_null_never_zero(tmp_path):
    _, out = run(tmp_path, v3=False, cloud=False)
    cells = load(out, "cells.json")
    ids = cells["ids"]
    no_data, no_horizon, south = ids.index("80.0_-40.0"), ids.index("70.0_20.3"), ids.index("-70.0_10.0")
    columns = export_site.read_yearly(out, cells["n"], [t for t, _, _ in TARGETS])["malapert"]
    assert np.isnan(columns["snow_free"][no_data]) and np.isnan(columns["snow_free"][south])
    assert np.isnan(columns["open"][no_horizon]) and np.isnan(columns["open"][no_data])
    assert np.isnan(columns["clear"][0])                  # no cloud file: unknown, not zero
    assert np.isnan(columns["lighting"][no_horizon])      # not in the scored file: unknown, not zero
    assert cells["horizon_n"][no_horizon] is None
    assert all(isinstance(v, int) and 0 <= v < len(cells["horizon_note_labels"]) for v in cells["horizon_note"].values())
    assert columns["snow_free"][0] == 150.0 and columns["snow_free_winter"][0] == 10.0
    assert columns["lighting"][0] == pytest.approx(0.447)
    raw = np.frombuffer((out / "yearly.bin").read_bytes(), dtype="<u2").reshape(cells["n"], 4, -1)
    assert raw[no_data, 1, cells["yearly"]["fields"].index("snow_free")] == 65535
    assert cells["snow_statuses"][cells["snow"][no_data]] == "no data"
    assert cells["hemisphere"][south] == "S"
    rock = cells["south"]
    assert rock["cells"] == [south]
    assert rock["targets"]["malapert"]["rock_flat"] == [900] and rock["targets"]["malapert"]["rock_open"] == [400]


def test_clear_sky_hours_come_from_the_scored_file_or_are_computed(tmp_path):
    derived, out = run(tmp_path, v3=True, cloud=True)
    cells = load(out, "cells.json")
    yearly = export_site.read_yearly(out, cells["n"], [t for t, _, _ in TARGETS])["malapert"]
    assert yearly["clear"][0] == 30.0                               # the pipeline's own figure
    z = np.load(derived / "grazing_bins.npz")
    i = cells["ids"].index("68.0_13.2")                             # not in the scored file: computed here
    share = export_site.clear_share_by_bin([60.0 + m for m in range(12)])
    want = float(np.nansum(z["long_open"][i, 1] * share))
    assert yearly["clear"][i] == pytest.approx(want, abs=0.1)


def test_calendar_sums_equal_sums_made_from_the_source_arrays(tmp_path):
    for v3, cloud in ((False, False), (True, True)):
        derived, out = run(tmp_path / f"v{int(v3)}", v3, cloud)
        z = np.load(derived / "grazing_bins.npz")
        grazing = json.loads((derived / "grazing_cells.json").read_text())["cells"]
        calendar = load(out, "calendar.json")
        if v3:
            long_flat, long_snow, long_open = z["long_flat"], z["long_snow_free"], z["long_open"]
        else:
            ok = z["stretch"] >= 2.0
            long_flat, long_snow, long_open = (np.where(ok, z[k], 0.0) for k in ("flat", "snow_free", "open"))
        rows = [i for i, c in enumerate(grazing) if c["hemisphere"] == "N" and c["gridded"]
                and c["snow"]["status"] == "measured"]
        km2 = np.array([grazing[i]["bare_km2"] for i in rows])
        north = calendar["north"]
        assert north["cells"] == len(rows) == 3
        assert north["bare_km2"] == pytest.approx(km2.sum(), abs=0.1)
        for t, (target, _, _) in enumerate(TARGETS):
            series = north["targets"][target]
            assert series["sun"] == pytest.approx((long_flat[rows, t] * km2[:, None]).sum(axis=0), rel=1e-4, abs=0.2)
            assert series["snow_free"] == pytest.approx(np.nansum(long_snow[rows, t] * km2[:, None], axis=0),
                                                        rel=1e-4, abs=0.2)
            with_horizon = [i for i in rows if grazing[i]["horizon"]]
            k = np.array([grazing[i]["bare_km2"] for i in with_horizon])
            assert north["cells_with_horizon"] == len(with_horizon) == 2
            assert series["open"] == pytest.approx(np.nansum(long_open[with_horizon, t] * k[:, None], axis=0),
                                                   rel=1e-4, abs=0.2)
            assert series["snow_free_h"] == pytest.approx(np.nansum(long_snow[with_horizon, t] * k[:, None], axis=0),
                                                          rel=1e-4, abs=0.2)
            if cloud:
                share = np.array(export_site.clear_share_by_bin([60.0 + m for m in range(12)]))
                assert series["clear"] == pytest.approx(
                    np.nansum(long_open[with_horizon, t] * k[:, None] * share[None, :], axis=0), rel=1e-4, abs=0.2)
            else:
                assert series["clear"] is None
        south = calendar["south"]
        assert south["cells"] == 1 and south["targets"]["malapert"]["snow_free"] is None


def test_sites_lists_point_at_cells_by_index(tmp_path):
    _, out = run(tmp_path, v3=True, cloud=True)
    sites = load(out, "sites.json")
    cells = load(out, "cells.json")
    top = sites["top"]["malapert"]
    assert [row["cell"] for row in top["north_lighting"]] and all(
        cells["hemisphere"][row["cell"]] == "N" for row in top["north_lighting"])
    assert all(cells["ranked"][row["cell"]] == "1" for row in top["north_lighting"])
    assert [cells["ids"][row["cell"]] for row in top["south_lighting"]] == ["-70.0_10.0"]
    named = {s["name"]: s for s in sites["named"]}
    assert cells["ids"][named["Lofoten anorthosite (Nusfjord), Norway"]["cell"]] == "68.0_13.2"


def test_flat_rows_hold_the_long_hours_of_each_latitude(tmp_path):
    derived, out = run(tmp_path, v3=True, cloud=False)
    z = np.load(derived / "grazing_bins.npz")
    flat = load(out, "flat.json")
    cells = load(out, "cells.json")
    assert len(flat["lat"]) == 6                              # two of the seven cells share a latitude
    for i in range(cells["n"]):
        row = cells["flat_row"][i]
        assert flat["lat"][row] == pytest.approx(cells["lat"][i] / 100)
        got = np.array(flat["targets"]["nobile-rim-2"]["bins"][row]) / 10
        assert got == pytest.approx(z["long_flat"][i, 3], abs=0.051)


def test_horizon_skip_reasons_become_short_labels():
    label = export_site.horizon_note_label
    assert label("window at 66.15, -179.85 crosses the antimeridian (longitudes 179 to -179); not supported") == \
        "no terrain figure: the area lies on the date line"
    assert label("tile not fetched: https://example.org/a/very/long/address.tif (downloads were off)") == \
        "no terrain figure"
    assert label("no land pixels") == "no terrain figure: no land in the terrain model"
    assert label("x" * 500) == "no terrain figure"            # an unforeseen reason is not passed on to the page


# ---- each figure against its own source field (added by the data review) ----

def test_snow_odds_file_holds_the_odds_the_pipeline_used(tmp_path):
    derived, out = run(tmp_path, v3=True, cloud=False)
    z = np.load(derived / "grazing_bins.npz")
    n = len(z["ids"])
    raw = np.frombuffer((out / "snowodds.bin").read_bytes(), dtype=np.uint8).reshape(n, 36)
    flat, snow_free = z["flat"].astype(np.float64), z["snow_free"].astype(np.float64)
    for i in range(n):
        for b in range(36):
            t = int(flat[i, :, b].argmax())
            if flat[i, t, b] < 0.05 or np.isnan(snow_free[i, t, b]):
                assert raw[i, b] == 255                      # no low Sun or no snow figure: unknown, never 0
            else:
                assert raw[i, b] == pytest.approx(100.0 * snow_free[i, t, b] / flat[i, t, b], abs=0.51)
    assert (raw[:, 10:14] == 255).all()
    assert (raw[list(z["ids"]).index("80.0_-40.0")] == 255).all()


def test_calendar_series_use_the_right_cells_and_weights(tmp_path):
    derived, out = run(tmp_path, v3=True, cloud=True, extra=True)
    z = np.load(derived / "grazing_bins.npz")
    grazing = json.loads((derived / "grazing_cells.json").read_text())["cells"]
    calendar = load(out, "calendar.json")
    km2 = np.array([c["bare_km2"] for c in grazing])
    arrays = {k: z[k].astype(np.float64) for k in ("long_flat", "long_snow_free", "long_open")}
    share = np.array(export_site.clear_share_by_bin([60.0 + m for m in range(12)]))

    def has_horizon(i: int) -> bool:
        return "north_deg" in (grazing[i]["horizon"] or {})

    def total(name: str, rows: list[int], t: int, times=1.0):
        return pytest.approx(np.nansum(arrays[name][rows, t] * km2[rows, None] * times, axis=0), rel=1e-6, abs=0.06)

    north = [i for i, c in enumerate(grazing) if c["hemisphere"] == "N" and c["gridded"]
             and c["snow"]["status"] == "measured"]
    south = [i for i, c in enumerate(grazing) if c["hemisphere"] == "S" and c["gridded"]]
    north_h, south_h = [i for i in north if has_horizon(i)], [i for i in south if has_horizon(i)]
    assert (len(north), len(north_h), len(south), len(south_h)) == (4, 2, 2, 1)
    for side, rows, rows_h in (("north", north, north_h), ("south", south, south_h)):
        part = calendar[side]
        assert (part["cells"], part["cells_with_horizon"]) == (len(rows), len(rows_h))
        assert part["bare_km2"] == pytest.approx(km2[rows].sum(), abs=0.06)
        assert part["bare_km2_with_horizon"] == pytest.approx(km2[rows_h].sum(), abs=0.06)
        for t, (target, _, _) in enumerate(TARGETS):
            series = part["targets"][target]
            assert series["sun"] == total("long_flat", rows, t)
            assert series["sun_h"] == total("long_flat", rows_h, t)
            assert series["open"] == total("long_open", rows_h, t)
            assert series["clear"] == total("long_open", rows_h, t, share[None, :])
            if side == "north":
                assert series["snow_free"] == total("long_snow_free", rows, t)
                assert series["snow_free_h"] == total("long_snow_free", rows_h, t)
            else:
                assert series["snow_free"] is None           # not measured in the south: no figure, not zero


def test_cell_columns_take_the_right_fields_and_units(tmp_path):
    def patch(grazing, scored):
        scored["70.0_20.0"]["rock"] = {"score": 0.736, "body": "Test anorthosite"}

    _, out = run(tmp_path, v3=True, cloud=True, extra=True, patch=patch)
    cells = load(out, "cells.json")
    ids = cells["ids"]
    a, b, c, d, x = (ids.index(k) for k in ("70.0_20.0", "70.0_20.3", "64.0_-20.0", "74.4_19.0", "66.0_-179.9"))
    assert (cells["lat"][a], cells["lon"][a], cells["lon"][c]) == (7005, 2015, -1985)
    assert (cells["bare"][a], cells["bare_km2"][a]) == (50, 480)
    assert (cells["horizon_n"][a], cells["horizon_s"][a]) == (120, -10)
    assert cells["horizon_n"][x] is None and cells["horizon_s"][x] is None    # refused: no horizon, not zero
    assert cells["horizon_note_labels"][cells["horizon_note"][str(x)]] == \
        "no terrain figure: the area lies on the date line"
    assert (cells["slope"][a], cells["relief"][a], cells["slope"][b]) == (64, 234, -1)
    assert cells["rock"] == {str(a): [736, "Test anorthosite"]}
    assert cells["stuck_winters"] == {str(d): 3}
    assert (cells["snow_pixels"][a], cells["snow_block"][a]) == (6, 9)
    assert cells["doubtful"][str(d)]["malapert"] == [1500, 1600]              # with the rule first, then as mapped
    assert cells["known"][a] == -1 and cells["known"][b] == -2                # little known; not assessed
    assert cells["known_labels"][cells["known"][c]].startswith("Iceland")
    assert [cells["ranked"][i] for i in (a, b, c, d, x)] == ["1", "0", "1", "0", "0"]
    assert cells["why_not_labels"][cells["why_not"][d]] == "snow doubtful"
    assert cells["gridded"] == "1111110101" and cells["hemisphere"] == "NNNNNSNSSN"
    south = cells["south"]
    assert [ids[i] for i in south["cells"]] == ["-70.0_10.0", "-71.0_11.0", "-72.0_12.0"]
    column = south["targets"]["malapert"]
    assert column["rock_flat"] == [900, 900, 900]
    assert column["rock_open"] == [400, -1, 400]                              # no horizon: unknown, not zero
    assert column["rock_clear"] == [150, -1, 150]
    assert column["poleward"] == [1000, 1000, 1000]


def test_yearly_file_takes_each_figure_from_its_own_field(tmp_path):
    derived, out = run(tmp_path, v3=True, cloud=True)
    y = yearly_of(out)
    assert (y["snow_free"][0], y["snow_free_winter"][0], y["snow_free_summer"][0]) == (150.0, 10.0, 140.0)
    assert (y["open"][0], y["open_winter"][0], y["open_summer"][0]) == (80.0, 5.0, 75.0)
    assert (y["clear"][0], y["clear_winter"][0], y["clear_summer"][0]) == (30.0, 2.0, 28.0)
    assert y["terrain"][0] == pytest.approx(0.6) and y["lighting"][0] == pytest.approx(0.447) and y["full"][0] == 0.0
    # a cell the scored file does not hold: its clear-sky hours are worked out here, season by season
    z = np.load(derived / "grazing_bins.npz")
    i = load(out, "cells.json")["ids"].index("68.0_13.2")
    hours = z["long_open"][i, 1].astype(np.float64) * np.array(export_site.clear_share_by_bin([60.0 + m for m in range(12)]))
    assert y["clear"][i] == pytest.approx(hours.sum(), abs=0.051)
    assert y["clear_winter"][i] == pytest.approx(hours[WINTER].sum(), abs=0.051)
    assert y["clear_summer"][i] == pytest.approx(hours[SUMMER].sum(), abs=0.051)
    assert abs(hours[WINTER].sum() - hours.sum()) > 1.0 and abs(hours[SUMMER].sum() - hours[WINTER].sum()) > 1.0


def test_summer_half_is_the_pipelines_own_figure_not_year_minus_winter(tmp_path):
    def patch(grazing, scored):   # three rounded figures need not add up: 150.0 - 50.1 = 99.9, the summer field says 100.0
        for values in grazing["70.0_20.0"]["targets"].values():
            values.update(long_snow_free_hours_winter=50.1, long_snow_free_hours_summer=100.0,
                          long_open_hours_summer=75.1)
        for values in scored["70.0_20.0"]["targets"].values():
            values.update(long_open_hours_clear_summer=28.1)

    _, out = run(tmp_path, v3=True, cloud=True, patch=patch)
    y = yearly_of(out)
    assert (y["snow_free_summer"][0], y["open_summer"][0], y["clear_summer"][0]) == (100.0, 75.1, 28.1)
    reach = load(out, "meta.json")["headline"]["malapert"]["measured_cells_reaching"]
    assert reach["100"] == {"winter": 0, "summer": 3}
    assert reach["50"] == {"winter": 1, "summer": 3}
    assert reach["200"] == {"winter": 0, "summer": 0}


def test_summer_half_falls_back_to_year_minus_winter_when_the_field_is_missing(tmp_path):
    def patch(grazing, scored):
        for record in list(grazing.values()) + list(scored.values()):
            for values in record["targets"].values():
                for key in [k for k in values if k.endswith("_summer")]:
                    del values[key]

    _, out = run(tmp_path, v3=False, cloud=False, patch=patch)
    y = yearly_of(out)
    assert (y["snow_free_summer"][0], y["open_summer"][0]) == (140.0, 75.0)
    assert np.isnan(y["snow_free_summer"][4])      # no snow data: unknown stays unknown
    assert np.isnan(y["open_summer"][1])           # no horizon
    assert np.isnan(y["clear_summer"][0])          # no cloud file


def test_headline_figures_follow_the_calendar_and_the_ranked_cells(tmp_path):
    def patch(grazing, scored):
        for record in (grazing["64.0_-20.0"], scored["64.0_-20.0"]):
            for values in record["targets"].values():
                values.update(long_open_hours=60.0, long_snow_free_hours_winter=55.0, long_snow_free_hours_summer=95.0)

    _, out = run(tmp_path, v3=True, cloud=True, patch=patch)
    head = load(out, "meta.json")["headline"]["malapert"]
    series = load(out, "calendar.json")["north"]["targets"]["malapert"]
    summer_share = sum(series["snow_free"][b] for b in SUMMER) / sum(series["snow_free"])
    winter_share = sum(series["sun"][b] for b in WINTER) / sum(series["sun"])
    assert abs(summer_share - 0.5) > 0.01 and abs(winter_share - 0.5) > 0.01      # so that a swap would show
    assert head["summer_share_snow_free"] == pytest.approx(summer_share, abs=6e-5)
    assert head["winter_share_sun_only"] == pytest.approx(winter_share, abs=6e-5)
    assert head["measured_cells_reaching"]["50"] == {"winter": 1, "summer": 3}
    assert head["measured_cells_reaching"]["100"] == {"winter": 0, "summer": 2}
    assert head["best_open_hours"] == 80.0                                         # the best ranked cell, not the worst


def test_flat_file_carries_the_long_hours_of_the_year_and_where_the_sun_stands(tmp_path):
    _, out = run(tmp_path, v3=True, cloud=False)
    flat = load(out, "flat.json")["targets"]["malapert"]
    assert set(flat["year"]) == {3000}             # long_flat_hours (300), not every low-Sun hour (400)
    assert set(flat["poleward"]) == {600} and set(flat["longest"]) == {550}


def test_cluster_keeps_the_best_first_and_one_site_per_distance():
    lat, lon = [70.0, 70.1, 70.0, 60.0], [20.0, 20.0, 40.0, 0.0]
    key, tie = [0.5, 0.9, 0.9, None], [1.0, 2.0, 5.0, 9.0]
    kept = export_site.cluster([0, 1, 2, 3], lat, lon, lambda r: key[r], lambda r: tie[r], 10, 50.0)
    assert kept == [2, 1]      # equal scores: more hours first; row 0 is 11 km from row 1; an unknown score is left out
    assert export_site.cluster([0, 1, 2], lat, lon, lambda r: key[r], lambda r: tie[r], 1, 50.0) == [2]


def test_short_lists_are_keyed_on_their_own_figures(tmp_path):
    def patch(grazing, scored):
        for record in (grazing["64.0_-20.0"], scored["64.0_-20.0"]):
            for values in record["targets"].values():
                values.update(long_snow_free_hours=120.0, long_snow_free_hours_winter=60.0,
                              long_snow_free_hours_summer=60.0)
        for values in scored["64.0_-20.0"]["targets"].values():
            values["goals"] = {"lighting": 0.2, "shadows": 0.1, "geology": 0.3, "full": 0.3}
        for values in scored["70.0_20.0"]["targets"].values():
            values["goals"] = {"lighting": 0.447, "shadows": 0.2, "geology": 0.1, "full": 0.1}

    _, out = run(tmp_path, v3=True, cloud=True, patch=patch)
    cells = load(out, "cells.json")
    top = load(out, "sites.json")["top"]["malapert"]

    def ids_of(rows: list[dict]) -> list[str]:
        return [cells["ids"][row["cell"]] for row in rows]

    assert ids_of(top["north_lighting"]) == ["70.0_20.0", "64.0_-20.0"]
    assert [row["score"] for row in top["north_lighting"]] == [0.447, 0.2]
    assert ids_of(top["north_full"]) == ["64.0_-20.0", "70.0_20.0"] and top["north_full"][0]["score"] == 0.3
    assert ids_of(top["winter"]) == ["64.0_-20.0", "70.0_20.0"]      # 70.0_20.3 is 11 km from 70.0_20.0: one site
    assert [row["hours"] for row in top["winter"]] == [60.0, 10.0]
    assert ids_of(top["snow_free_year"]) == ["70.0_20.0", "64.0_-20.0"]
    assert ids_of(top["south_lighting"]) == ["-70.0_10.0"]


def test_latitude_profile_and_named_sites_are_passed_on_as_they_are(tmp_path):
    derived = make_inputs(tmp_path / "derived", True, True, extra=True)
    lofoten = "Lofoten anorthosite (Nusfjord), Norway"
    (derived / "latitude_profile.json").write_text(json.dumps({
        "profile": [{"lat": lat, "targets": {t: {"flat_hours": 100.0 + lat, "longest_stretch_h": 3.5,
                                                 "long_flat_hours": {"1": 50.0 + lat, "2": 20.0 + lat, "3": 5.0}}
                                             for t, _, _ in TARGETS}} for lat in (-60.0, 0.0, 60.0, 70.0)],
        "thresholds": {t: {side: {"lowest_lat_with_long_window": {"1": 50.1, "2": 60.65, "3": 63.0},
                                  "lowest_lat_with_all_day_low_sun": 66.5} for side in ("N", "S")}
                       for t, _, _ in TARGETS}}))
    (derived / "validation.json").write_text(json.dumps({"named_sites": {"sites": [
        {"name": lofoten, "lat": 68.04, "lon": 13.35, "cell": "68.0_13.2", "hemisphere": "N"},
        {"name": "Test nunatak, Antarctica", "lat": -72.0, "lon": 12.2, "cell": "-72.0_12.0", "hemisphere": "S",
         "winter_snow_evidence": "station shows snow"},
        {"name": "A place whose cell is not in the files", "lat": 1.0, "lon": 1.0, "cell": "1.0_1.0",
         "hemisphere": "N"}]}}))
    out = tmp_path / "site" / "data"
    meta = export_site.export(derived, tmp_path / "no_reference", None, out)
    got = load(out, "profile.json")
    assert got["lat"] == [-60.0, 0.0, 60.0, 70.0]
    assert got["targets"]["malapert"]["all"] == [40.0, 100.0, 160.0, 170.0]
    assert got["targets"]["malapert"]["long"] == [-40.0, 20.0, 80.0, 90.0]     # the two-hour figures
    assert got["targets"]["malapert"]["longest"] == [3.5] * 4
    assert got["thresholds"]["malapert"]["N"] == {"spells": {"1": 50.1, "2": 60.65, "3": 63.0}, "all_day": 66.5}
    assert meta["headline"]["malapert"]["first_latitude_with_spells"] == 60.65
    assert got["search_band"] == {"north": [64.05, 80.05], "south": [-71.05, -70.05]}
    cells = load(out, "cells.json")
    named = load(out, "sites.json")["named"]
    assert [(s["name"], cells["ids"][s["cell"]]) for s in named] == [(lofoten, "68.0_13.2"),
                                                                    ("Test nunatak, Antarctica", "-72.0_12.0")]
    assert named[1]["winter_snow_evidence"] == "station shows snow" and meta["counts"]["named_sites"] == 2


def test_counts_and_season_words_in_meta(tmp_path):
    _, out = run(tmp_path, v3=True, cloud=True, extra=True)
    meta = load(out, "meta.json")
    counts = meta["counts"]
    assert (counts["records"], counts["north_cells"], counts["south_cells"]) == (10, 6, 2)
    assert counts["north_by_snow_status"] == {"measured": 4, "doubtful": 1, "no data": 1, "unmeasured": 0}
    assert (counts["with_horizon_north"], counts["with_horizon_south"]) == (3, 1)
    assert (counts["ranked_north"], counts["ranked_south"], counts["outside_the_screen"]) == (2, 1, 2)
    seasons = meta["seasons"]
    assert seasons["winter_text"] == "28 September to 31 March"
    assert seasons["summer_text"] == "1 April to 27 September"
    assert seasons["rock_season_text"] == "27 November to 1 March"
    assert meta["snow"]["measured_cells_use"] == "the snow maps as they read"


def test_long_rule_words_follow_the_pipelines_spell_length(tmp_path):
    def text_for(folder: Path, hours: float) -> str:
        derived = make_inputs(folder / "derived", True, False)
        grazing = json.loads((derived / "grazing_cells.json").read_text())
        grazing["meta"]["stretch_min_h"] = hours
        (derived / "grazing_cells.json").write_text(json.dumps(grazing))
        return export_site.export(derived, folder / "no_reference", None, folder / "out")["long_rule"]["text"]

    assert "at least two hours" in text_for(tmp_path / "a", 2.0)
    three = text_for(tmp_path / "b", 3.0)
    assert "at least three hours" in three and "two hours" not in three
    assert "at least 1.5 hours" in text_for(tmp_path / "c", 1.5)


def test_meta_names_the_snow_rule_of_measured_areas_by_its_key(tmp_path):
    # the key is the one the station check uses for its two sets of figures (snow_validation_many.json)
    _, out = run(tmp_path / "v3", v3=True, cloud=False)
    assert load(out, "meta.json")["snow"]["measured_cells_rule"] == "as_mapped"
    _, out = run(tmp_path / "v2", v3=False, cloud=False)
    assert load(out, "meta.json")["snow"]["measured_cells_rule"] == "with_stale_flag_rule"


def test_meta_keeps_each_file_time_under_its_own_name(tmp_path):
    derived = make_inputs(tmp_path / "derived", True, True)
    grazing = json.loads((derived / "grazing_cells.json").read_text())
    grazing["meta"]["snow_archive_written"] = "2026-11-14T13:28:39"          # the snow archive, not this file
    (derived / "grazing_cells.json").write_text(json.dumps(grazing))
    meta = export_site.export(derived, tmp_path / "no_reference", None, tmp_path / "out")
    assert meta["pipeline_written"] == {"grazing_cells": None, "snow_archive": "2026-11-14T13:28:39",
                                        "cells_scored": None}


def test_odds_used_says_which_snow_odds_stand_behind_a_cell(tmp_path):
    def used(out: Path) -> list:
        cells = load(out, "cells.json")
        return [cells["odds_labels"][k] if k >= 0 else None for k in cells["odds_used"]]

    _, out = run(tmp_path / "v2", v3=False, cloud=False)       # before version 3 every figure used the rule
    assert used(out) == ["stale-flag rule"] * 4 + [None, None, "stale-flag rule"]
    assert load(out, "meta.json")["snow"]["measured_cells_use"] == "the cautious stale-flag rule"
    _, out = run(tmp_path / "v3", v3=True, cloud=False)
    assert used(out) == ["as mapped"] * 3 + ["stale-flag rule", "stale-flag rule", None, "as mapped"]


def test_meta_says_how_fast_the_sun_moves_sideways_and_how_coarse_the_cloud_grid_is(tmp_path):
    _, out = run(tmp_path / "cloud", v3=True, cloud=True)
    meta = load(out, "meta.json")
    motion = meta["sun_motion"]
    assert motion["moon_deg_per_hour"] == 0.508                                    # once round the horizon in a synodic month
    assert motion["earth_deg_per_hour"] == {"60": 13.0, "70": 14.1, "80": 14.8}    # 15 x sin(latitude)
    assert motion["times_faster_on_earth"] == {"60": 25.6, "70": 27.7, "80": 29.1}
    assert motion["swing_in_one_spell_deg"] == {"spell_h": 2.0, "earth": [26, 30], "moon": 1.0}
    assert meta["cloud_grid_km"] == 111                                            # one degree of latitude
    _, out = run(tmp_path / "no_cloud", v3=True, cloud=False)
    assert load(out, "meta.json")["cloud_grid_km"] is None


# ---- round 2 of the page: plain words, official names, one set of areas, one colour scale ----

BUILDING_SITE_WORDS = ("fetch", "download", " yet", "tile", "cell", "screen")


def test_no_building_site_wording_reaches_the_page_files(tmp_path):
    def patch(grazing, scored):
        grazing["70.0_20.3"]["horizon"] = {"skipped": "tile not fetched: https://example.org/a.tif (downloads were "
                                                      "off in this run; 8 of the cell's 8 tiles are new)"}
        grazing["70.0_20.0"]["horizon"] = None                    # these two have no terrain figure
        grazing["64.0_-20.0"]["horizon"] = {"skipped": SKIPPED}
        scored["70.0_20.0"]["ranked"] = False
        scored["70.0_20.0"]["not_ranked_because"] = ["no horizon: tile not fetched", "bare under 0.25"]
        scored["64.0_-20.0"]["ranked"] = False
        scored["64.0_-20.0"]["not_ranked_because"] = ["window across the antimeridian",
                                                      "named-site cell outside the screen"]

    _, out = run(tmp_path, v3=True, cloud=True, extra=True, patch=patch)
    cells = load(out, "cells.json")
    ids = cells["ids"]
    labels = cells["horizon_note_labels"] + cells["why_not_labels"]
    assert labels
    for label in labels:
        assert not any(word in label.lower() for word in BUILDING_SITE_WORDS), label
    why = {k: cells["why_not_labels"][cells["why_not"][ids.index(k)]] for k in ("70.0_20.0", "64.0_-20.0", "70.0_20.3")}
    assert why["70.0_20.0"] == "no terrain figure; less than 25% bare ground"
    assert why["64.0_-20.0"] == "no terrain figure (on the date line); a named place outside the search"
    assert why["70.0_20.3"] == "no terrain figure"                 # not in the scored file at all
    assert cells["horizon_note_labels"][cells["horizon_note"][str(ids.index("70.0_20.3"))]] == "no terrain figure"


def test_an_area_with_a_terrain_figure_is_never_told_it_has_none(tmp_path):
    """The scores file can be older than the terrain figures. Its reason "no horizon" is then out of date,
    and the page must not print "no terrain figure" beside a terrain figure."""
    def patch(grazing, scored):
        assert "north_deg" in grazing["70.0_20.0"]["horizon"] and "north_deg" in grazing["64.0_-20.0"]["horizon"]
        scored["70.0_20.0"]["ranked"] = False
        scored["70.0_20.0"]["not_ranked_because"] = ["no horizon: tile not fetched", "bare under 0.25"]
        scored["64.0_-20.0"]["ranked"] = False
        scored["64.0_-20.0"]["not_ranked_because"] = ["no horizon: tile not fetched"]

    _, out = run(tmp_path, v3=True, cloud=True, patch=patch)
    cells = load(out, "cells.json")
    ids = cells["ids"]
    i, j, k = ids.index("70.0_20.0"), ids.index("64.0_-20.0"), ids.index("70.0_20.3")
    assert cells["horizon_n"][i] is not None and cells["horizon_n"][j] is not None
    assert cells["why_not_labels"][cells["why_not"][i]] == "less than 25% bare ground"   # the reason that still holds
    assert cells["why_not"][j] == -1 and cells["ranked"][j] == "0"   # no reason is better than a false one
    assert all("no terrain figure" not in cells["why_not_labels"][cells["why_not"][x]]
               for x in range(cells["n"]) if cells["horizon_n"][x] is not None and cells["why_not"][x] >= 0)
    # an area that really has no terrain figure keeps the reason
    assert cells["horizon_n"][k] is None and cells["why_not_labels"][cells["why_not"][k]] == "no terrain figure"


def test_reasons_for_not_ranking_are_put_in_plain_words():
    plain = export_site.plain_reason
    assert plain("no horizon: tile not fetched") == "no terrain figure"
    assert plain("bare under 0.25") == "less than 25% bare ground"
    assert plain("bare under 0.125") == "less than 12.5% bare ground"
    assert plain("snow doubtful") == "snow doubtful" and plain("no snow data") == "no snow data"
    assert plain("named-site cell outside the screen") == "a named place outside the search"
    assert plain("window across the antimeridian") == "no terrain figure (on the date line)"


CARDS = {"meta": {}, "cards": [
    {"id": "connecting-ridge", "official_name": "Connecting Ridge", "shadow_of_1m_object_at_ceiling_m": 27.58,
     "nasa_list": {"on_2022_list_of_13": True, "name_2022": "Connecting Ridge", "on_2024_list_of_9": False,
                   "name_2024": None, "summary": "On the 2022 list.", "links": ["https://example.org/list"]},
     "name_note": "a note", "why_check": {"confirmed": False}},
    {"id": "mons-mouton", "official_name": "Mons Mouton",
     "nasa_list": {"on_2022_list_of_13": True, "name_2022": "Leibnitz Beta Plateau", "on_2024_list_of_9": True,
                   "name_2024": "Mons Mouton", "name_2024_certainty": "inferred", "summary": "s", "links": []},
     "why_check": {"confirmed": None}},
    {"id": "malapert", "official_name": "Malapert Massif",
     "nasa_list": {"on_2022_list_of_13": True, "name_2022": "Malapert Massif", "on_2024_list_of_9": True,
                   "name_2024": "Malapert Massif", "summary": "s", "links": []}, "why_check": {"confirmed": True}},
]}


def test_official_lunar_names_come_from_the_moon_cards(tmp_path):
    derived = make_inputs(tmp_path / "derived", True, True)
    (derived / "moon_targets.json").write_text(json.dumps(
        [{"id": t, "why": "stored reason " + t, "centre_lat": -89.0} for t, _, _ in TARGETS]))
    plain = export_site.export(derived, tmp_path / "no_reference", None, tmp_path / "plain")
    rows = {t["id"]: t for t in plain["targets"]}
    assert rows["connecting-ridge"]["name"] == "Shackleton-de Gerlache connecting ridge"   # the pipeline's own name
    assert rows["connecting-ridge"]["official"] is False and rows["connecting-ridge"]["list_line"] is None
    assert rows["connecting-ridge"]["why"] == "stored reason connecting-ridge"
    (derived / "moon_cards.json").write_text(json.dumps(CARDS))
    meta = export_site.export(derived, tmp_path / "no_reference", None, tmp_path / "cards")
    rows = {t["id"]: t for t in meta["targets"]}
    ridge, mouton, malapert, nobile = (rows[k] for k in ("connecting-ridge", "mons-mouton", "malapert", "nobile-rim-2"))
    assert (ridge["name"], ridge["short"], ridge["official"]) == ("Connecting Ridge", "Connecting Ridge", True)
    assert (mouton["name"], mouton["short"]) == ("Mons Mouton", "Mons Mouton")              # not "plateau"
    assert ridge["list_line"] == "On NASA's 2022 list of 13 candidate regions; not among the nine kept in 2024."
    assert mouton["list_line"] == ("On NASA's 2022 list of 13 candidate regions as Leibnitz Beta Plateau; "
                                   "most likely among the nine kept in 2024.")
    assert malapert["list_line"] == "On NASA's 2022 list of 13 candidate regions; among the nine kept in 2024."
    assert ridge["why"] is None                    # the stored reason could not be confirmed: not passed on
    assert malapert["why"] == "stored reason malapert" and mouton["why"] is None
    assert ridge["list_links"] == ["https://example.org/list"]
    assert ridge["limit_deg"] == 2.08                                    # the limit the Earth search used stays
    assert (nobile["name"], nobile["official"]) == ("Nobile Rim 2", False)    # no card: the pipeline's name


def test_calendar_says_when_all_four_steps_share_one_set_of_areas(tmp_path):
    _, out = run(tmp_path / "some", v3=True, cloud=True)          # 2 of the 3 measured areas have a horizon
    north = load(out, "calendar.json")["north"]
    assert (north["cells"], north["cells_with_horizon"]) == (3, 2)
    assert north["one_set"] is False and north["one_set_from_share"] == 0.97
    assert north["horizon_share"] == pytest.approx(2 / 3, abs=1e-4)

    def patch(grazing, scored):
        grazing["70.0_20.3"]["horizon"] = {"north_deg": 0.4, "south_deg": 0.2}

    _, out = run(tmp_path / "all", v3=True, cloud=True, patch=patch)
    calendar = load(out, "calendar.json")
    assert calendar["north"]["one_set"] is True and calendar["north"]["horizon_share"] == 1.0
    assert calendar["south"]["one_set"] is True
    assert export_site.one_set(97, 100) is True and export_site.one_set(969, 1000) is False
    assert export_site.one_set(0, 0) is False


def test_headline_names_the_area_with_the_most_hours(tmp_path):
    def patch(grazing, scored):
        for record in (grazing["64.0_-20.0"], scored["64.0_-20.0"]):
            for values in record["targets"].values():
                values.update(long_open_hours=91.5)

    _, out = run(tmp_path, v3=True, cloud=True, patch=patch)
    head = load(out, "meta.json")["headline"]["malapert"]
    cells = load(out, "cells.json")
    assert head["best_open_hours"] == 91.5
    assert cells["ids"][head["best_open_cell"]] == "64.0_-20.0" and cells["ranked"][head["best_open_cell"]] == "1"


def test_nice_ceiling_rounds_up_to_a_round_figure():
    nice = export_site.nice_ceiling
    assert [nice(v) for v in (0.2, 5, 7, 43, 96, 100, 101, 240, 251, 1700)] == [5, 5, 10, 50, 100, 100, 150, 250, 300, 2000]


def test_one_colour_scale_for_all_sites_steps_and_poles(tmp_path):
    def patch(grazing, scored):
        grazing["70.0_20.0"]["targets"]["nobile-rim-2"]["long_snow_free_hours"] = 731.0     # the richest site
        grazing["-70.0_10.0"]["targets"]["connecting-ridge"]["long_summer_rock_hours"] = 12.0
        grazing["74.4_19.0"]["targets"]["nobile-rim-2"]["long_snow_free_hours"] = 5000.0     # doubtful: not counted

    derived, out = run(tmp_path, v3=True, cloud=True, patch=patch)
    scale = load(out, "meta.json")["scale"]
    # yearly: the measured northern areas in the search (150 h each, one raised to 731) and the southern rock season
    values = [150.0] * 11 + [731.0] + [12.0] + [90.0] * 3
    expected = export_site.nice_ceiling(float(np.percentile(values, 99)))
    assert scale["year_h"] == expected and scale["year_h"] > 150
    z = np.load(derived / "grazing_bins.npz")
    cells = load(out, "cells.json")
    rows = [i for i, cid in enumerate(cells["ids"]) if cid in ("70.0_20.0", "70.0_20.3", "64.0_-20.0")]
    south = cells["ids"].index("-70.0_10.0")
    per = np.concatenate([z["long_snow_free"][rows].ravel(), z["long_flat"][south][:, ROCK].ravel()])
    per = per[per > 0]
    assert scale["period_h"] == export_site.nice_ceiling(float(np.percentile(per, 99)))
    assert scale["quantile"] == 0.99 and "all four" in scale["how"]


def test_cloud_is_described_in_plain_words(tmp_path):
    _, out = run(tmp_path / "cloud", v3=True, cloud=True)
    meta = load(out, "meta.json")
    assert meta["cloud_years"] == "2001 to 2020"
    months = meta["cloud_by_month_north"]              # mean over the measured northern areas in the search
    assert months == [60.0 + m for m in range(12)]
    _, out = run(tmp_path / "none", v3=True, cloud=False)
    meta = load(out, "meta.json")
    assert meta["cloud_years"] is None and meta["cloud_by_month_north"] is None


def test_words_the_exporter_writes_call_the_squares_areas(tmp_path):
    _, out = run(tmp_path, v3=True, cloud=True, extra=True)
    meta = load(out, "meta.json")
    assert meta["scoring"]["area_word"] == "area"
    for source in meta["sources"]:
        assert "cell" not in source["used_for"], source
        # the page prints "name: used for." as one sentence, and no sentence on the page has more than 25 words
        assert len((source["name"] + ": " + source["used_for"]).split()) <= 25, source
    assert "cell" not in load(out, "calendar.json")["north"]["who"]


# ---- land outline ----

def test_ring_is_cut_at_the_fiftieth_parallel():
    ring = [[0.0, 40.0], [0.0, 60.0], [10.0, 60.0], [10.0, 40.0], [0.0, 40.0]]
    cut = export_site.clip_ring(ring, 50.0, north=True)
    assert min(lat for _, lat in cut) == pytest.approx(50.0)
    assert max(lat for _, lat in cut) == pytest.approx(60.0)
    assert export_site.clip_ring([[0.0, 10.0], [5.0, 20.0], [9.0, 10.0], [0.0, 10.0]], 50.0, north=True) == []
    south = export_site.clip_ring([[0.0, -40.0], [0.0, -60.0], [10.0, -60.0], [10.0, -40.0], [0.0, -40.0]], 50.0,
                                  north=False)
    assert max(lat for _, lat in south) == pytest.approx(-50.0)


@pytest.mark.skipif(not LAND.exists(), reason="the Natural Earth file is not on disk")
def test_land_outline_is_polar_only_and_small():
    land = export_site.land_outline(LAND)
    text = json.dumps(land, separators=(",", ":"))
    assert len(text) < 500_000
    for side, sign in (("north", 1), ("south", -1)):
        rings = land[side]
        assert len(rings) > 5
        for ring in rings:
            lats = np.array(ring[1::2]) / land["scale"] * sign
            assert lats.min() >= 50.0 - 1e-6
            assert len(ring) >= 8 and len(ring) % 2 == 0
    assert "Natural Earth" in land["source"]


# ---- the real files ----

REAL = (DERIVED / "grazing_cells.json").exists() and (DERIVED / "grazing_bins.npz").exists()


@pytest.fixture(scope="module")
def real(tmp_path_factory):
    out = tmp_path_factory.mktemp("site_data")
    export_site.export(DERIVED, REFERENCE, LAND if LAND.exists() else None, out)
    return out


@pytest.mark.skipif(not REAL, reason="the derived files are not on disk")
def test_real_export_decodes_back_to_the_source_hours(real):
    z = np.load(DERIVED / "grazing_bins.npz")
    cells = load(real, "cells.json")
    n = cells["n"]
    ids = [str(i) for i in z["ids"]]
    if cells["ids"] != ids:
        pytest.skip("the pipeline files changed while the test ran")
    if "long_snow_free" in z.files:
        source = {"snowfree.bin": z["long_snow_free"], "open.bin": z["long_open"]}
    else:
        ok = z["stretch"] >= 2.0
        source = {"snowfree.bin": np.where(ok, z["snow_free"], 0.0), "open.bin": np.where(ok, z["open"], 0.0)}
    spread = np.unique(np.concatenate([np.arange(0, n, 37), [0, n - 1]]))
    for name, want in source.items():
        raw = read_bins(real, name, n)
        assert raw.shape == (n, 4, 36)
        got = export_site.decode_hours(raw[spread])
        want = want[spread]
        known = ~np.isnan(want)
        assert np.all(np.abs(got[known] - np.minimum(want[known], 127.0)) <= 0.25 + 1e-4)
        assert np.all(raw[spread][~known] == 255)
        assert not np.any((raw == 0) & np.isnan(source[name]))


@pytest.mark.skipif(not REAL, reason="the derived files are not on disk")
def test_real_export_agrees_on_count_and_order_and_is_small(real):
    cells = load(real, "cells.json")
    meta = load(real, "meta.json")
    n = cells["n"]
    assert n == meta["counts"]["records"] == len(cells["ids"]) == len(set(cells["ids"]))
    assert (real / "snowfree.bin").stat().st_size == n * 144 == (real / "open.bin").stat().st_size
    assert (real / "snowodds.bin").stat().st_size == n * 36
    assert (real / "yearly.bin").stat().st_size == n * 4 * len(cells["yearly"]["fields"]) * 2
    if (real / "cloud.bin").exists():
        assert (real / "cloud.bin").stat().st_size == n * 12
    total = sum(p.stat().st_size for p in real.iterdir() if p.is_file())
    assert total < 10_000_000
    if LAND.exists():
        assert (real / "land.json").stat().st_size < 500_000
    statuses = [cells["snow_statuses"][s] for s in cells["snow"]]
    assert statuses.count("unmeasured") == sum(1 for h in cells["hemisphere"] if h == "S")


@pytest.mark.skipif(not REAL, reason="the derived files are not on disk")
def test_real_calendar_equals_direct_sums(real):
    z = np.load(DERIVED / "grazing_bins.npz")
    grazing = json.loads((DERIVED / "grazing_cells.json").read_text())["cells"]
    cells = load(real, "cells.json")
    if cells["ids"] != [c["id"] for c in grazing] or cells["ids"] != [str(i) for i in z["ids"]]:
        pytest.skip("the pipeline files changed while the test ran")
    calendar = load(real, "calendar.json")
    if "long_snow_free" in z.files:
        long_flat, long_snow = z["long_flat"], z["long_snow_free"]
    else:
        ok = z["stretch"] >= 2.0
        long_flat, long_snow = np.where(ok, z["flat"], 0.0), np.where(ok, z["snow_free"], 0.0)
    rows = [i for i, c in enumerate(grazing) if c["hemisphere"] == "N" and c.get("gridded", True)
            and c["snow"]["status"] == "measured"]
    km2 = np.array([grazing[i]["bare_km2"] for i in rows], dtype=np.float64)
    assert calendar["north"]["cells"] == len(rows)
    for t, target in enumerate(str(x) for x in z["targets"]):
        series = calendar["north"]["targets"][target]
        assert series["sun"] == pytest.approx((long_flat[rows, t].astype(np.float64) * km2[:, None]).sum(axis=0),
                                              rel=1e-5, abs=1.0)
        assert series["snow_free"] == pytest.approx(
            np.nansum(long_snow[rows, t].astype(np.float64) * km2[:, None], axis=0), rel=1e-5, abs=1.0)


@pytest.mark.skipif(not REAL, reason="the derived files are not on disk")
def test_real_yearly_figures_and_summer_counts_equal_the_pipelines_fields(real):
    grazing = json.loads((DERIVED / "grazing_cells.json").read_text())
    cells = load(real, "cells.json")
    if cells["ids"] != [c["id"] for c in grazing["cells"]]:
        pytest.skip("the pipeline files changed while the test ran")
    meta = load(real, "meta.json")
    targets = [t["id"] for t in grazing["meta"]["targets"]]
    yearly = export_site.read_yearly(real, cells["n"], targets)
    north = [i for i, c in enumerate(grazing["cells"]) if c["hemisphere"] == "N"]
    measured = [c for c in grazing["cells"] if c["hemisphere"] == "N" and c.get("gridded", True)
                and c["snow"]["status"] == "measured"]
    pairs = {"snow_free": "long_snow_free_hours", "snow_free_winter": "long_snow_free_hours_winter",
             "snow_free_summer": "long_snow_free_hours_summer", "open": "long_open_hours",
             "open_winter": "long_open_hours_winter", "open_summer": "long_open_hours_summer"}
    for target in targets:
        for field, key in pairs.items():
            if key not in grazing["cells"][north[0]]["targets"][target]:
                continue
            want = np.array([np.nan if grazing["cells"][i]["targets"][target][key] is None
                             else grazing["cells"][i]["targets"][target][key] for i in north], dtype=np.float64)
            got = yearly[target][field][north]
            assert np.array_equal(np.isnan(want), np.isnan(got)), (target, field)      # unknown stays unknown
            assert np.nanmax(np.abs(want - got)) <= 0.051, (target, field)
        for level, halves in meta["headline"][target]["measured_cells_reaching"].items():
            for half, count in halves.items():
                key = f"long_snow_free_hours_{half}"
                assert count == sum(1 for c in measured if c["targets"][target].get(key) is not None
                                    and c["targets"][target][key] >= float(level)), (target, level, half)
