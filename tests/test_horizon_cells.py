# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
import importlib
import json
import math
import threading
import time
import urllib.error

import numpy as np

from twinfinder import earth

build = importlib.import_module("scripts.build_horizon_cells")

CELL = {"id": "66.5_-52.5", "lat": 66.55, "lon": -52.35, "why": ["named: Qaqortorsuaq"], "top_position": None}
DATELINE = {"id": "66.1_-180.0", "lat": 66.15, "lon": -179.85, "why": ["top malapert year"], "top_position": 0.5}


def test_the_tile_list_is_the_elevation_and_water_tiles_of_the_30_km_window():
    urls, refused = build.tile_urls(CELL)
    assert refused is None
    assert urls == (earth.tiles_for_window(66.55, -52.35, 30.0, "DEM")
                    + earth.tiles_for_window(66.55, -52.35, 30.0, "WBM"))
    assert len(earth.tiles_for_window(66.55, -52.35, 5.0, "DEM")) == 1
    assert len(urls) == 6   # three tiles side by side, each as elevation and as water mask: wider than the cell


def test_a_window_across_the_antimeridian_has_no_tiles_and_a_reason():
    urls, refused = build.tile_urls(DATELINE)
    assert urls == [] and "antimeridian" in refused


def test_tile_state_tells_cached_from_known_ocean_from_new(tmp_path):
    (tmp_path / "a_DEM.tif").write_bytes(b"x" * 10)
    (tmp_path / "b_DEM.tif.missing").touch()
    assert build.tile_state("https://host/x/a_DEM.tif", tmp_path) == "cached"
    assert build.tile_state("https://host/x/b_DEM.tif", tmp_path) == "ocean"
    assert build.tile_state("https://host/x/c_DEM.tif", tmp_path) == "new"


def test_a_record_holds_the_open_share_to_four_decimals_and_the_pixel_size():
    share = np.full((36, 9), 0.123456, dtype="float32")
    share[0, 0] = 1.0
    record = build.record(share, 7.4712, -0.1234, 0.98765, 60.0)
    assert record["open_share"][0][0] == 1.0 and record["open_share"][35][8] == 0.1235
    assert len(record["open_share"]) == 36 and all(len(row) == 9 for row in record["open_share"])
    assert (record["north_deg"], record["south_deg"], record["valid_share"], record["pixel_m"]) == (7.47, -0.12, 0.988, 60.0)
    json.dumps(record)   # plain numbers only


def test_a_cell_without_land_is_skipped_not_given_zero_hours():
    nothing = np.full((36, 9), np.nan, dtype="float32")
    assert build.record(nothing, math.nan, math.nan, 0.0, 60.0) == {"skipped": "no land pixels"}


def test_an_unknown_median_is_null_never_zero():
    record = build.record(np.ones((36, 9), dtype="float32"), math.nan, 1.0, 0.5, 60.0)
    assert record["north_deg"] is None and record["south_deg"] == 1.0


def test_resume_skips_cells_done_at_the_same_pixel_size_and_settled_refusals():
    done = {"open_share": [[1.0] * 9] * 36, "north_deg": 0.0, "south_deg": 0.0, "valid_share": 1.0, "pixel_m": 60.0}
    assert build.needs_horizon(None, 60.0)
    assert not build.needs_horizon(done, 60.0)
    assert build.needs_horizon(done, 90.0) and build.needs_horizon(dict(done, pixel_m=90.0), 60.0)
    assert not build.needs_horizon({"skipped": "no land pixels"}, 60.0)
    assert not build.needs_horizon({"skipped": "window at 66.15, -179.85 crosses the antimeridian"}, 60.0)


def test_resume_tries_again_what_a_download_or_the_budget_held_back():
    assert build.needs_horizon({"skipped": build.NOT_FETCHED + ": https://host/a.tif"}, 60.0)
    assert build.needs_horizon({"skipped": build.OVER_BUDGET}, 60.0)
    assert build.needs_horizon({"skipped": build.FAILED + ": RuntimeError: boom"}, 60.0)


def test_fetching_counts_new_files_ocean_tiles_and_collects_other_failures(tmp_path):
    running, most = [0], [0]
    lock = threading.Lock()

    def fake_fetch(url, dest_dir):
        with lock:
            running[0] += 1
            most[0] = max(most[0], running[0])
        time.sleep(0.01)
        with lock:
            running[0] -= 1
        name = url.rsplit("/", 1)[-1]
        if name.startswith("ocean"):
            return None
        if name.startswith("refused"):
            raise urllib.error.HTTPError(url, 403, "Forbidden", None, None)
        path = dest_dir / name
        path.write_bytes(b"x" * 100)
        return path

    (tmp_path / "old.tif").write_bytes(b"x" * 999)
    urls = [f"https://host/land{k}.tif" for k in range(20)] + ["https://host/ocean1.tif", "https://host/refused1.tif",
                                                                 "https://host/old.tif"]
    result = build.fetch_tiles(urls, tmp_path, fetch_one=fake_fetch)
    assert result["asked"] == 22                      # the cached tile is not asked for again
    assert result["fetched"] == 20 and result["bytes"] == 2000
    assert result["ocean"] == 1
    assert list(result["failures"]) == ["https://host/refused1.tif"] and "403" in result["failures"]["https://host/refused1.tif"]
    assert 1 < most[0] <= 6                           # several at once, never more than six


def test_cells_that_need_a_tile_that_was_not_fetched_are_held_back():
    tiles = {"a": ["t1", "t2"], "b": ["t2", "t3"], "c": ["t4"]}
    held = build.held_back(tiles, {"t3": "HTTPError: 403", "t9": "HTTPError: 500"})
    assert held == {"b": build.NOT_FETCHED + ": t3 (HTTPError: 403)"}


def test_within_budget_nothing_is_dropped():
    tiles = {"a": ["t1"], "b": ["t2"]}
    assert build.over_budget(["b", "a"], tiles, {"t1": 10, "t2": 10}, budget=20) == []


def test_over_budget_cells_go_in_the_order_given_until_the_new_tiles_fit():
    tiles = {"keep": ["t1"], "a": ["t1", "t2"], "b": ["t3"], "c": ["t4"], "d": ["t5"]}
    cost = {"t1": 10, "t2": 10, "t3": 10, "t4": 10, "t5": 0}     # t5 is cached already: no new bytes
    # all five need 40; dropping "c" leaves 30, dropping "b" leaves 20
    assert build.over_budget(["c", "b", "a"], tiles, cost, budget=20) == ["c", "b"]
    # a tile shared with a cell that stays is still needed, so dropping "a" saves only t2
    assert build.over_budget(["a", "c"], tiles, cost, budget=25) == ["a", "c"]
    assert build.over_budget(["a"], tiles, cost, budget=5) == ["a"]          # cannot fit: says what it dropped, no more


def test_new_bytes_are_estimated_from_the_tiles_already_in_the_cache(tmp_path):
    (tmp_path / "x_DEM.tif").write_bytes(b"x" * 300)
    (tmp_path / "y_DEM.tif").write_bytes(b"x" * 100)
    (tmp_path / "x_WBM.tif").write_bytes(b"x" * 10)
    (tmp_path / "z_DEM.tif.missing").touch()
    cost = build.expected_bytes(["h/x_DEM.tif", "h/n_DEM.tif", "h/n_WBM.tif", "h/z_DEM.tif"], tmp_path)
    assert cost == {"h/x_DEM.tif": 0, "h/n_DEM.tif": 200, "h/n_WBM.tif": 10, "h/z_DEM.tif": 0}


def test_work_order_puts_named_sites_and_samples_before_the_top_lists():
    cells = [{"id": "t", "why": ["top malapert year"], "top_position": 0.1},
             {"id": "s", "why": ["sample"], "top_position": None},
             {"id": "n", "why": ["top malapert year", "named: X"], "top_position": 0.9},
             {"id": "u", "why": ["top malapert year"], "top_position": 0.05}]
    assert [c["id"] for c in build.work_order(cells)] == ["s", "n", "u", "t"]


# --- added in review: the call into the horizon code and the whole run, which had no test ---

FAR = {"id": "70.0_20.0", "lat": 70.05, "lon": 20.0, "why": ["sample"], "top_position": None}


def test_the_agreed_settings():
    assert build.PIXEL_M == 60.0 and (build.HALF_KM, build.REACH_KM) == (5.0, 25.0)
    assert build.DOWNLOADS_AT_ONCE == 6 and build.PROCESSES == 8 and build.BUDGET_BYTES == 8e9
    assert build.SAVE_EVERY == 200
    assert build.NO_LAND == "no land pixels"


def test_compute_asks_for_the_cell_centre_a_5_km_cell_25_km_reach_and_60_m_pixels(monkeypatch):
    seen = []

    def fake(lat, lon, half_km=5.0, reach_km=25.0, pixel_m=90.0):
        seen.append((lat, lon, half_km, reach_km, pixel_m))
        return np.full((36, 9), 0.5, dtype="float32"), 1.234, 5.678, 0.25

    monkeypatch.setattr(build.horizon, "cell_open_share", fake)
    cid, result, seconds = build.compute(CELL)
    assert seen == [(66.55, -52.35, 5.0, 25.0, 60.0)]
    assert cid == "66.5_-52.5" and seconds >= 0.0
    assert result == {"open_share": [[0.5] * 9] * 36, "north_deg": 1.23, "south_deg": 5.68, "valid_share": 0.25,
                      "pixel_m": 60.0}


def test_a_refused_window_is_settled_and_any_other_error_is_tried_again(monkeypatch):
    def refuse(*args, **kwargs):
        raise ValueError("window at 66.15, -179.85 crosses the antimeridian; not supported")

    def crash(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(build.horizon, "cell_open_share", refuse)
    _, refused, _ = build.compute(DATELINE)
    assert refused == {"skipped": "window at 66.15, -179.85 crosses the antimeridian; not supported"}
    assert not build.needs_horizon(refused, 60.0)
    monkeypatch.setattr(build.horizon, "cell_open_share", crash)
    _, crashed, _ = build.compute(CELL)
    assert crashed == {"skipped": "failed: RuntimeError: boom"} and build.needs_horizon(crashed, 60.0)


def test_compute_stores_a_cell_without_land_as_skipped(monkeypatch):
    monkeypatch.setattr(build.horizon, "cell_open_share",
                        lambda *a, **k: (np.full((36, 9), np.nan, dtype="float32"), math.nan, math.nan, 0.0))
    assert build.compute(CELL)[1] == {"skipped": "no land pixels"}


def test_the_file_is_written_beside_the_old_one_and_renamed_into_place(tmp_path, monkeypatch):
    out = tmp_path / "horizon_cells.json"
    out.write_text('{"old": 1}')
    moves = []
    real_replace = build.os.replace

    def watch(source, target):
        moves.append((str(source) != str(out), json.loads(open(source).read()), json.loads(out.read_text())))
        real_replace(source, target)

    monkeypatch.setattr(build.os, "replace", watch)
    build.write_json(out, {"new": 2})
    assert moves == [(True, {"new": 2}, {"old": 1})]    # complete beside the old file, which stays whole until the rename
    assert json.loads(out.read_text()) == {"new": 2} and [p.name for p in tmp_path.iterdir()] == ["horizon_cells.json"]


class PoolInThisProcess:
    """Stands in for the process pool, so the made-up horizon function below is the one that runs."""
    workers = []
    initializers = []

    def __init__(self, max_workers=None, initializer=None, initargs=()):
        PoolInThisProcess.workers.append(max_workers)
        PoolInThisProcess.initializers.append(initializer)     # noted, not called: it would change this process

    def __enter__(self):
        return self

    def __exit__(self, *error):
        return False

    def map(self, function, items, chunksize=1):
        return map(function, items)


class Run:
    """The whole script on made-up candidates, with a made-up tile server and a made-up horizon function."""

    def __init__(self, tmp_path, monkeypatch, cells, stored=None):
        self.cache, self.out = tmp_path / "glo90", tmp_path / "horizon_cells.json"
        self.cache.mkdir()
        (tmp_path / "candidates.json").write_text(json.dumps(cells))
        if stored is not None:
            self.out.write_text(json.dumps(stored))
        self.refused, self.ocean = set(), set()          # parts of tile names the server refuses (403) or lacks (404)
        self.asked, self.computed, self.tiles_were_here, self.saved_before, self.ids_before = [], [], [], [], []
        real_fetch_tiles = build.fetch_tiles
        monkeypatch.setattr(build, "CANDIDATES", tmp_path / "candidates.json")
        monkeypatch.setattr(build, "OUT", self.out)
        monkeypatch.setattr(build.earth, "GLO90_DIR", self.cache)
        monkeypatch.setattr(build, "fetch_tiles",
                            lambda urls, cache_dir: real_fetch_tiles(urls, cache_dir, fetch_one=self.fetch))
        monkeypatch.setattr(build, "ProcessPoolExecutor", PoolInThisProcess)
        monkeypatch.setattr(build.horizon, "cell_open_share", self.open_share)

    def fetch(self, url, dest_dir):
        name = url.rsplit("/", 1)[-1]
        self.asked.append(name)
        if any(part in name for part in self.refused):
            raise urllib.error.HTTPError(url, 403, "Forbidden", None, None)
        if any(part in name for part in self.ocean):
            (dest_dir / (name + ".missing")).touch()
            return None
        (dest_dir / name).write_bytes(b"x" * 1000)
        return dest_dir / name

    def open_share(self, lat, lon, half_km=5.0, reach_km=25.0, pixel_m=90.0):
        urls, _ = build.tile_urls({"lat": lat, "lon": lon})
        self.tiles_were_here.append(all(build.tile_state(url, self.cache) != "new" for url in urls))
        stored = json.loads(self.out.read_text()) if self.out.exists() else {}
        self.saved_before.append(sum("open_share" in record for record in stored.values()))
        self.ids_before.append(set(stored))
        self.computed.append((lat, lon))
        if lat == 61.05:                                  # the made-up cell without land
            return np.full((36, 9), np.nan, dtype="float32"), math.nan, math.nan, 0.0
        return np.full((36, 9), 0.5, dtype="float32"), lat / 8.0, lon / 8.0, 1.0

    def result(self):
        return json.loads(self.out.read_text())


def test_a_whole_run_stores_every_candidate_and_a_second_run_does_only_what_is_left(tmp_path, monkeypatch, capsys):
    no_land = {"id": "61.0_10.0", "lat": 61.05, "lon": 10.1, "why": ["sample"], "top_position": None}
    needs_bad_tile = {"id": "75.0_60.0", "lat": 75.05, "lon": 60.5, "why": ["top malapert year"], "top_position": 0.4}
    cells = [CELL, DATELINE, FAR, no_land, needs_bad_tile]
    run = Run(tmp_path, monkeypatch, cells)
    run.refused.add("N75_00_E060_00_DEM")
    run.ocean.add("N70_00_E019_00")
    PoolInThisProcess.workers.clear()
    try:
        build.main()
        code = 0
    except SystemExit as stop:
        code = stop.code
    assert code == 1                                      # a failed download is not a clean run
    stored = run.result()
    assert set(stored) == {c["id"] for c in cells}        # nobody is silently missing
    assert stored[CELL["id"]] == {"open_share": [[0.5] * 9] * 36, "north_deg": 8.32, "south_deg": -6.54,
                                  "valid_share": 1.0, "pixel_m": 60.0}
    assert stored[FAR["id"]]["north_deg"] == 8.76 and stored[FAR["id"]]["south_deg"] == 2.5   # each under its own id
    assert "antimeridian" in stored[DATELINE["id"]]["skipped"]
    assert stored[no_land["id"]] == {"skipped": "no land pixels"}
    assert stored[needs_bad_tile["id"]]["skipped"].startswith("tile not fetched: https://")
    assert "N75_00_E060_00_DEM.tif" in stored[needs_bad_tile["id"]]["skipped"] and "403" in stored[needs_bad_tile["id"]]["skipped"]
    assert sorted(run.computed) == [(61.05, 10.1), (66.55, -52.35), (70.05, 20.0)]    # not the cell with a missing tile
    assert all(run.tiles_were_here)                       # every tile was fetched before the first cell was worked out
    assert run.ids_before[0] == {DATELINE["id"], needs_bad_tile["id"]}    # the skips are saved before the long part starts
    assert (run.cache / "Copernicus_DSM_COG_30_N70_00_E019_00_DEM.tif.missing").exists()
    assert PoolInThisProcess.workers == [8]
    assert "failed: 1" in capsys.readouterr().out

    asked_before, computed_before = len(run.asked), len(run.computed)
    run.refused.clear()
    build.main()                                          # the server answers now
    again = run.result()
    assert run.computed[computed_before:] == [(75.05, 60.5)]
    assert run.asked[asked_before:] == ["Copernicus_DSM_COG_30_N75_00_E060_00_DEM.tif"]
    assert again[needs_bad_tile["id"]]["north_deg"] == 9.38
    assert {cid: again[cid] for cid in stored if cid != needs_bad_tile["id"]} == \
           {cid: stored[cid] for cid in stored if cid != needs_bad_tile["id"]}

    build.main()                                          # nothing left: no download, no cell
    assert len(run.computed) == computed_before + 1 and len(run.asked) == asked_before + 1
    assert run.result() == again


def test_a_run_keeps_results_of_other_cells_and_redoes_a_cell_stored_at_another_pixel_size(tmp_path, monkeypatch):
    old = {"open_share": [[1.0] * 9] * 36, "north_deg": 0.0, "south_deg": 0.0, "valid_share": 1.0, "pixel_m": 90.0}
    gone = dict(old, pixel_m=60.0)
    run = Run(tmp_path, monkeypatch, [CELL, FAR], stored={CELL["id"]: old, FAR["id"]: gone, "1.0_1.0": gone})
    build.main()
    stored = run.result()
    assert run.computed == [(66.55, -52.35)]
    assert stored[CELL["id"]]["pixel_m"] == 60.0 and stored[CELL["id"]]["north_deg"] == 8.32
    assert stored[FAR["id"]] == gone and stored["1.0_1.0"] == gone


def test_progress_is_saved_while_the_cells_are_worked_out(tmp_path, monkeypatch):
    cells = [{"id": f"70.0_{lon}.0", "lat": 70.05, "lon": lon + 0.5, "why": ["sample"], "top_position": None}
             for lon in (20, 30, 40, 50, 60)]
    run = Run(tmp_path, monkeypatch, cells)
    monkeypatch.setattr(build, "SAVE_EVERY", 2)
    build.main()
    assert run.saved_before == [0, 0, 2, 2, 4]            # results in the file when each cell started
    assert len(run.result()) == 5 and all("open_share" in record for record in run.result().values())


def test_over_the_budget_the_weakest_top_cell_is_left_out_stored_as_such_and_its_tiles_are_not_fetched(tmp_path, monkeypatch, capsys):
    named = dict(CELL)
    strong = {"id": "70.0_20.0", "lat": 70.05, "lon": 20.0, "why": ["top malapert year"], "top_position": 0.1}
    weak = {"id": "75.0_60.0", "lat": 75.05, "lon": 60.5, "why": ["top malapert year"], "top_position": 0.9}
    run = Run(tmp_path, monkeypatch, [weak, named, strong])
    urls = {c["id"]: build.tile_urls(c)[0] for c in (weak, named, strong)}
    cost = build.expected_bytes([u for group in urls.values() for u in group], run.cache)
    total = sum(cost.values())
    monkeypatch.setattr(build, "BUDGET_BYTES", total - 1.0)     # one cell has to go
    build.main()
    stored = run.result()
    assert stored[weak["id"]] == {"skipped": build.OVER_BUDGET} and build.needs_horizon(stored[weak["id"]], 60.0)
    assert "open_share" in stored[named["id"]] and "open_share" in stored[strong["id"]]
    assert sorted(run.computed) == [(66.55, -52.35), (70.05, 20.0)]
    assert not any("N75_00_E06" in name or "N74_00_E06" in name for name in run.asked)
    assert sorted(run.asked) == sorted(u.rsplit("/", 1)[-1] for cid in (named["id"], strong["id"]) for u in urls[cid])
    said = capsys.readouterr().out
    assert "OVER THE DOWNLOAD BUDGET" in said and weak["id"] in said



def test_when_nothing_fits_the_budget_named_sites_and_samples_are_still_worked_out(tmp_path, monkeypatch):
    strong = {"id": "70.0_20.0", "lat": 70.05, "lon": 20.0, "why": ["top malapert year"], "top_position": 0.1}
    weak = {"id": "75.0_60.0", "lat": 75.05, "lon": 60.5, "why": ["south top malapert flat"], "top_position": 0.9}
    sampled = {"id": "70.0_40.0", "lat": 70.05, "lon": 40.5, "why": ["top malapert year", "sample"], "top_position": 1.0}
    run = Run(tmp_path, monkeypatch, [weak, CELL, strong, sampled])
    monkeypatch.setattr(build, "BUDGET_BYTES", 1.0)
    build.main()
    stored = run.result()
    assert "open_share" in stored[CELL["id"]] and "open_share" in stored[sampled["id"]]
    assert stored[weak["id"]] == stored[strong["id"]] == {"skipped": build.OVER_BUDGET}
    assert sorted(run.computed) == [(66.55, -52.35), (70.05, 40.5)]


# --- version 3, decision 15: every cell gets a horizon ---

def census_cell(cid, lat, lon, bare, status):
    return {"id": cid, "lat": lat, "lon": lon, "hemisphere": "N" if lat >= 0 else "S", "why": ["all"],
            "top_position": None, "bare": bare, "snow_status": status}


def test_work_order_takes_census_cells_last_rankable_north_then_other_north_then_the_south():
    cells = [census_cell("s", -70.05, 20.0, 0.9, "unmeasured"), census_cell("thin", 70.05, 20.0, 0.2, "measured"),
             census_cell("doubt", 70.05, 21.0, 0.9, "doubtful"), census_cell("rank2", 70.05, 23.0, 0.25, "measured"),
             census_cell("rank1", 70.05, 22.0, 0.9, "measured"),
             {"id": "top", "why": ["top malapert year"], "top_position": 0.1},
             {"id": "sampled", "why": ["sample"], "top_position": None}]
    order = [c["id"] for c in build.work_order(cells)]
    assert order[:2] == ["sampled", "top"]
    assert set(order[2:4]) == {"rank1", "rank2"} and set(order[4:6]) == {"thin", "doubt"} and order[6] == "s"
    assert order == [c["id"] for c in build.work_order(cells[::-1])]      # the same whatever order the file has


def test_cached_or_ocean_gives_the_tile_on_disk_none_for_known_ocean_and_refuses_a_tile_never_asked_for(tmp_path):
    (tmp_path / "here_DEM.tif").write_bytes(b"x")
    (tmp_path / "sea_DEM.tif.missing").touch()
    assert build.cached_or_ocean("https://host/a/here_DEM.tif", tmp_path) == tmp_path / "here_DEM.tif"
    assert build.cached_or_ocean("https://host/a/sea_DEM.tif", tmp_path) is None
    try:
        build.cached_or_ocean("https://host/a/new_DEM.tif", tmp_path)
        raised = None
    except RuntimeError as error:
        raised = str(error)
    assert raised is not None and raised.startswith(build.NOT_FETCHED) and "new_DEM.tif" in raised
    assert sorted(p.name for p in tmp_path.iterdir()) == ["here_DEM.tif", "sea_DEM.tif.missing"]   # nothing was written


def test_no_downloads_replaces_the_fetch_the_elevation_code_uses(monkeypatch):
    monkeypatch.setattr(build.earth, "fetch_optional", build.earth.fetch_optional)   # put back after the test
    build.no_downloads()
    assert build.earth.fetch_optional is build.cached_or_ocean


def test_a_cached_only_run_asks_the_server_for_nothing_and_holds_back_cells_that_need_a_new_tile(tmp_path, monkeypatch, capsys):
    run = Run(tmp_path, monkeypatch, [CELL, FAR, DATELINE])
    for url in build.tile_urls(CELL)[0]:
        name = url.rsplit("/", 1)[-1]
        if "W053" in name:
            (run.cache / (name + ".missing")).touch()      # the server said before that this one is sea
        else:
            (run.cache / name).write_bytes(b"x" * 1000)
    files_before = sorted(p.name for p in run.cache.iterdir())
    PoolInThisProcess.initializers.clear()
    build.main(cached_only=True)
    stored = run.result()
    assert run.asked == []                                 # not one request
    assert sorted(p.name for p in run.cache.iterdir()) == files_before
    assert "open_share" in stored[CELL["id"]] and run.computed == [(66.55, -52.35)]
    held = stored[FAR["id"]]["skipped"]
    assert held.startswith("tile not fetched: https://") and "downloads were off" in held
    assert build.needs_horizon(stored[FAR["id"]], 60.0)    # a later run with downloads takes it up again
    assert "antimeridian" in stored[DATELINE["id"]]["skipped"]
    assert PoolInThisProcess.initializers == [build.no_downloads]    # the workers cannot download either
    said = capsys.readouterr().out
    assert "DOWNLOADS ARE OFF" in said and "held back: 1" in said

    PoolInThisProcess.initializers.clear()
    build.main()                                           # downloads allowed again
    again = run.result()
    assert "open_share" in again[FAR["id"]] and run.computed[1:] == [(70.05, 20.0)]
    assert sorted(run.asked) == sorted(u.rsplit("/", 1)[-1] for u in build.tile_urls(FAR)[0])
    assert again[CELL["id"]] == stored[CELL["id"]]
    assert PoolInThisProcess.initializers == [None]


def test_over_the_budget_cells_in_for_the_census_alone_are_left_out_before_any_top_cell(tmp_path, monkeypatch):
    top = {"id": "70.0_20.0", "lat": 70.05, "lon": 20.0, "hemisphere": "N", "why": ["top malapert year"],
           "top_position": 1.0, "bare": 0.5, "snow_status": "measured"}
    north = census_cell("75.0_60.0", 75.05, 60.5, 0.9, "measured")
    south = census_cell("-70.0_40.0", -70.05, 40.5, 0.9, "unmeasured")
    run = Run(tmp_path, monkeypatch, [top, north, south])
    urls = {c["id"]: build.tile_urls(c)[0] for c in (top, north, south)}
    cost = build.expected_bytes([u for group in urls.values() for u in group], run.cache)
    monkeypatch.setattr(build, "BUDGET_BYTES", sum(cost[u] for u in urls[top["id"]] + urls[north["id"]]))
    build.main()
    stored = run.result()
    assert stored[south["id"]] == {"skipped": build.OVER_BUDGET}         # the south goes first
    assert "open_share" in stored[top["id"]] and "open_share" in stored[north["id"]]
    assert not any("S70" in name or "S71" in name for name in run.asked)


def test_when_nothing_fits_the_budget_census_cells_and_top_cells_are_all_left_out(tmp_path, monkeypatch):
    top = {"id": "70.0_20.0", "lat": 70.05, "lon": 20.0, "hemisphere": "N", "why": ["top malapert year"],
           "top_position": 1.0, "bare": 0.5, "snow_status": "measured"}
    cells = [top, census_cell("75.0_60.0", 75.05, 60.5, 0.9, "measured"),
             census_cell("-70.0_40.0", -70.05, 40.5, 0.9, "unmeasured")]
    run = Run(tmp_path, monkeypatch, cells)
    monkeypatch.setattr(build, "BUDGET_BYTES", 1.0)
    build.main()
    assert run.result() == {c["id"]: {"skipped": build.OVER_BUDGET} for c in cells}
    assert run.asked == [] and run.computed == []
