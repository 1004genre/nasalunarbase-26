# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
import importlib
import json
import urllib.error
from pathlib import Path

import numpy as np
import pytest

from twinfinder import terrain

build = importlib.import_module("scripts.build_terrain_cells")

NAMED = {"id": "66.5_-52.5", "lat": 66.55, "lon": -52.35, "hemisphere": "N", "why": ["named: Qaqortorsuaq"],
         "top_position": None, "bare": 0.1, "snow_status": "measured"}
BARE = {"id": "70.0_20.0", "lat": 70.05, "lon": 20.0, "hemisphere": "N", "why": ["all"], "top_position": None,
        "bare": 0.25, "snow_status": "measured"}
THIN = {"id": "70.0_40.0", "lat": 70.05, "lon": 40.5, "hemisphere": "N", "why": ["all"], "top_position": None,
        "bare": 0.2, "snow_status": "measured"}
SOUTH = {"id": "-70.0_40.0", "lat": -70.05, "lon": 40.5, "hemisphere": "S", "why": ["sample"], "top_position": None,
         "bare": 0.9, "snow_status": "unmeasured"}
DATELINE = {"id": "66.1_-180.0", "lat": 66.15, "lon": -179.99, "hemisphere": "N", "why": ["all"],
            "top_position": None, "bare": 0.9, "snow_status": "measured"}
HISTS = {"flat": terrain.slope_histogram(np.full(100, 0.5)).tolist(),
         "ten": terrain.slope_histogram(np.full(100, 10.5)).tolist()}


def tilted(deg, n=111, pixel_m=90.0):
    return np.tile(np.arange(n) * pixel_m * np.tan(np.radians(deg)), (n, 1)).astype("float32")


def test_the_agreed_settings():
    assert build.HALF_KM == 5.0 and build.MIN_SLOPE_PIXELS == 500
    assert build.DOWNLOADS_AT_ONCE == 6 and build.SAVE_EVERY == 200 and build.PROCESSES == 8
    assert build.MUST_MIN_BARE == 0.25


def test_the_old_rule_and_the_old_light_file_are_gone():
    for name in ("LIGHT", "CELLS", "BODIES", "MIN_USABLE_DAYS", "is_candidate", "load_candidates"):
        assert not hasattr(build, name), name
    source = Path(build.__file__).read_text()
    assert "light_cells" not in source and "landcover_cells" not in source


def test_the_tile_list_is_the_elevation_and_water_tiles_of_the_5_km_window_and_empty_for_a_refused_window():
    urls = build.tile_urls(NAMED)
    assert urls and all(url.startswith("https://copernicus-dem-90m.s3.amazonaws.com/") for url in urls)
    assert sum(url.endswith("_DEM.tif") for url in urls) == sum(url.endswith("_WBM.tif") for url in urls) == len(urls) / 2
    assert build.tile_urls(DATELINE) == []


def test_a_cell_is_worked_out_again_only_when_it_has_no_numbers():
    assert build.needs_terrain(None)
    assert build.needs_terrain({"skipped": "window at 66.15, -179.99 crosses the antimeridian"})
    assert build.needs_terrain({"skipped": "tile not fetched: https://host/a.tif (HTTPError: 403)"})
    assert not build.needs_terrain({"valid_share": 0.01, "slope_pixels": 12})          # too little land: settled
    assert not build.needs_terrain({"valid_share": 1.0, "slope_pixels": 9000, "overlap": {"flat": 0.5}})


def test_cells_that_must_have_terrain_are_the_ones_bare_enough_to_rank_in_either_hemisphere_and_the_named_ones():
    assert build.must_have(BARE) and build.must_have(SOUTH) and build.must_have(NAMED)
    assert not build.must_have(THIN)
    assert not build.must_have(dict(THIN, bare=None))
    assert build.must_have(dict(BARE, snow_status="doubtful"))      # any snow status: the screen is bare ground alone
    assert not build.must_have({"id": "old record", "why": ["top malapert year"]})


def test_work_order_puts_the_must_haves_first_and_keeps_the_order_of_the_file_inside_each_group():
    assert [c["id"] for c in build.work_order([THIN, SOUTH, DATELINE, NAMED, dict(THIN, id="t2"), BARE])] == \
        [SOUTH["id"], DATELINE["id"], NAMED["id"], BARE["id"], THIN["id"], "t2"]


def test_summarise_gives_slope_numbers_and_the_overlap_with_every_target(monkeypatch):
    seen = []

    def window(lat, lon, half_km=5.0, pixel_m=90.0, mask_water=True, sea_as_zero=False):
        seen.append((lat, lon, half_km, pixel_m, mask_water, sea_as_zero))
        return tilted(10.5)

    monkeypatch.setattr(build.earth, "elevation_window", window)
    monkeypatch.setattr(build, "_TARGET_HISTS", HISTS)
    cid, result, took = build.summarise(BARE)
    assert cid == BARE["id"] and took >= 0.0
    assert seen == [(70.05, 20.0, 5.0, 90.0, True, False)]
    assert result["valid_share"] == 1.0 and result["slope_pixels"] > 500
    assert result["median_slope_deg"] == pytest.approx(10.5, abs=0.01)
    assert result["p90_slope_deg"] == pytest.approx(10.5, abs=0.01)
    assert result["relief_m"] == pytest.approx(float(np.percentile(tilted(10.5), 95) - np.percentile(tilted(10.5), 5)), abs=0.1)
    assert result["overlap"] == {"flat": 0.0, "ten": 1.0}
    assert set(result) == {"valid_share", "slope_pixels", "median_slope_deg", "p90_slope_deg", "relief_m", "overlap"}


def test_a_cell_with_too_little_land_keeps_its_pixel_count_and_gets_no_numbers(monkeypatch):
    z = np.full((111, 111), np.nan, dtype="float32")
    z[:12, :12] = tilted(3.0)[:12, :12]
    monkeypatch.setattr(build.earth, "elevation_window", lambda lat, lon, half_km: z)
    monkeypatch.setattr(build, "_TARGET_HISTS", HISTS)
    _, result, _ = build.summarise(BARE)
    assert set(result) == {"valid_share", "slope_pixels"} and 0 < result["slope_pixels"] < 500
    assert result["valid_share"] == round(144 / 111 ** 2, 3)


def test_a_refused_window_is_skipped_with_its_reason_and_any_other_error_is_kept_to_try_again(monkeypatch):
    def refuse(lat, lon, half_km):
        raise ValueError("window at 66.15, -179.99 crosses the antimeridian")

    def crash(lat, lon, half_km):
        raise RuntimeError("bad tile")

    monkeypatch.setattr(build.earth, "elevation_window", refuse)
    assert build.summarise(DATELINE)[1] == {"skipped": "window at 66.15, -179.99 crosses the antimeridian"}
    monkeypatch.setattr(build.earth, "elevation_window", crash)
    result = build.summarise(BARE)[1]
    assert result == {"skipped": "failed: RuntimeError: bad tile"} and build.needs_terrain(result)


def test_the_file_is_written_beside_the_old_one_and_renamed_into_place(tmp_path, monkeypatch):
    out = tmp_path / "terrain_cells.json"
    out.write_text('{"old": 1}')
    seen = []
    real_replace = build.os.replace

    def watch(source, target):
        seen.append((Path(source).name, json.loads(Path(target).read_text()), json.loads(Path(source).read_text())))
        real_replace(source, target)

    monkeypatch.setattr(build.os, "replace", watch)
    build.write_json(out, {"new": 2})
    assert seen == [("terrain_cells.json.part", {"old": 1}, {"new": 2})]     # the old file is whole until the swap
    assert json.loads(out.read_text()) == {"new": 2} and [p.name for p in tmp_path.iterdir()] == ["terrain_cells.json"]


class PoolInThisProcess:
    """Stands in for the process pool: the initializer and the work run in the test's own process."""
    made = []

    def __init__(self, max_workers=None, initializer=None, initargs=()):
        PoolInThisProcess.made.append({"workers": max_workers, "initargs": initargs})
        if initializer is not None:
            initializer(*initargs)

    def __enter__(self):
        return self

    def __exit__(self, *error):
        return False

    def map(self, function, items, chunksize=1):
        return map(function, items)


class Run:
    """The whole script on made-up candidates, with a made-up tile server and made-up elevation."""

    def __init__(self, tmp_path, monkeypatch, cells, stored=None):
        self.cache, self.out = tmp_path / "glo90", tmp_path / "terrain_cells.json"
        self.cache.mkdir()
        (tmp_path / "candidates.json").write_text(json.dumps(cells))
        (tmp_path / "moon_targets.json").write_text(json.dumps(
            [{"id": tid, "terrain": {"90m": {"slope_hist": hist}}} for tid, hist in HISTS.items()]))
        if stored is not None:
            self.out.write_text(json.dumps(stored))
        self.refused, self.ocean = set(), set()
        self.asked, self.computed, self.saved_before, self.tiles_were_here = [], [], [], []
        self.downloads_switched_off = []
        real_fetch_tiles = build.tiles.fetch_tiles
        monkeypatch.setattr(build, "CANDIDATES", tmp_path / "candidates.json")
        monkeypatch.setattr(build, "TARGETS", tmp_path / "moon_targets.json")
        monkeypatch.setattr(build, "OUT", self.out)
        monkeypatch.setattr(build, "_TARGET_HISTS", {})
        monkeypatch.setattr(build.earth, "GLO90_DIR", self.cache)
        monkeypatch.setattr(build.tiles, "fetch_tiles",
                            lambda urls, cache_dir, workers=None: (self.fetch_workers.append(workers),
                                                                   real_fetch_tiles(urls, cache_dir, fetch_one=self.fetch,
                                                                                    workers=workers))[1])
        self.fetch_workers = []
        monkeypatch.setattr(build.tiles, "no_downloads", lambda: self.downloads_switched_off.append(True))
        monkeypatch.setattr(build, "ProcessPoolExecutor", PoolInThisProcess)
        monkeypatch.setattr(build.earth, "elevation_window", self.window)
        PoolInThisProcess.made.clear()

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

    def window(self, lat, lon, half_km):
        build.earth.window_bounds(lat, lon, half_km)       # the real refusal of a window across the antimeridian
        self.tiles_were_here.append(all(build.tiles.tile_state(url, self.cache) != "new"
                                        for url in build.tile_urls({"lat": lat, "lon": lon})))
        stored = json.loads(self.out.read_text()) if self.out.exists() else {}
        self.saved_before.append(sum("overlap" in record for record in stored.values()))
        self.computed.append((lat, lon))
        return tilted(10.5 if lat > 0 else 0.5)

    def result(self):
        return json.loads(self.out.read_text())


def run_main(**options):
    try:
        build.main(**options)
        return 0
    except SystemExit as stop:
        return stop.code


def test_a_whole_run_fetches_first_six_at_a_time_stores_every_cell_and_a_second_run_does_only_what_is_left(tmp_path, monkeypatch, capsys):
    cells = [THIN, NAMED, DATELINE, BARE, SOUTH]
    run = Run(tmp_path, monkeypatch, cells)
    run.refused.add("N70_00_E040_00_DEM")                  # THIN's elevation tile
    assert run_main() == 1                                 # a failed download is not a clean run
    stored = run.result()
    assert set(stored) == {c["id"] for c in cells}         # nobody is silently missing
    assert stored[BARE["id"]]["overlap"] == {"flat": 0.0, "ten": 1.0}
    assert stored[SOUTH["id"]]["overlap"] == {"flat": 1.0, "ten": 0.0}
    assert "antimeridian" in stored[DATELINE["id"]]["skipped"]
    held = stored[THIN["id"]]["skipped"]
    assert held.startswith("tile not fetched: https://") and "N70_00_E040_00_DEM.tif" in held and "403" in held
    assert run.computed == [(66.55, -52.35), (70.05, 20.0), (-70.05, 40.5)]    # must-haves in file order; not the held cell
    assert all(run.tiles_were_here)                        # every tile was here before the first cell was worked out
    assert run.fetch_workers == [6]
    assert PoolInThisProcess.made == [{"workers": 8, "initargs": (HISTS, False)}] and run.downloads_switched_off == []
    said = capsys.readouterr().out
    assert "failed: 1" in said and "FAILED DOWNLOADS" in said

    asked_before = len(run.asked)
    run.refused.clear()
    assert run_main() == 0                                 # the server answers now
    again = run.result()
    assert run.computed[3:] == [(70.05, 40.5)]             # only the held cell (the refused window costs no elevation)
    assert run.asked[asked_before:] == ["Copernicus_DSM_COG_30_N70_00_E040_00_DEM.tif"]
    assert "overlap" in again[THIN["id"]]
    assert {cid: again[cid] for cid in stored if cid != THIN["id"]} == {cid: stored[cid] for cid in stored if cid != THIN["id"]}
    assert run_main() == 0 and len(run.computed) == 4 and run.result() == again      # nothing left


def test_progress_is_saved_while_the_cells_are_worked_out_and_other_records_are_kept(tmp_path, monkeypatch):
    cells = [dict(BARE, id=f"70.0_{lon}.0", lon=lon + 0.5) for lon in (20, 30, 40, 50, 60)]
    kept = {"valid_share": 1.0, "slope_pixels": 9000, "overlap": {"flat": 0.5}}
    run = Run(tmp_path, monkeypatch, cells, stored={"1.0_1.0": kept, cells[0]["id"]: kept})
    monkeypatch.setattr(build, "SAVE_EVERY", 2)
    assert run_main() == 0
    assert run.saved_before == [2, 2, 4, 4]                # results in the file when each cell started
    stored = run.result()
    assert stored["1.0_1.0"] == kept and stored[cells[0]["id"]] == kept and len(stored) == 6
    assert all("overlap" in record for record in stored.values())


def test_a_cached_only_run_asks_the_server_for_nothing_and_holds_back_cells_that_need_a_new_tile(tmp_path, monkeypatch, capsys):
    run = Run(tmp_path, monkeypatch, [BARE, SOUTH])
    for url in build.tile_urls(BARE):
        (run.cache / url.rsplit("/", 1)[-1]).write_bytes(b"x" * 1000)
    files_before = sorted(p.name for p in run.cache.iterdir())
    assert run_main(cached_only=True) == 0
    stored = run.result()
    assert run.asked == [] and run.fetch_workers == []     # not one request
    assert sorted(p.name for p in run.cache.iterdir()) == files_before
    assert "overlap" in stored[BARE["id"]] and run.computed == [(70.05, 20.0)]
    assert stored[SOUTH["id"]]["skipped"].startswith("tile not fetched: https://")
    assert "downloads were off" in stored[SOUTH["id"]]["skipped"] and build.needs_terrain(stored[SOUTH["id"]])
    assert PoolInThisProcess.made == [{"workers": 8, "initargs": (HISTS, True)}]
    assert run.downloads_switched_off == [True]            # the workers cannot download either
    assert "DOWNLOADS ARE OFF" in capsys.readouterr().out
    assert run_main() == 0 and "overlap" in run.result()[SOUTH["id"]]


def test_a_must_only_run_leaves_the_other_cells_alone_and_the_number_of_processes_can_be_chosen(tmp_path, monkeypatch, capsys):
    run = Run(tmp_path, monkeypatch, [THIN, BARE, NAMED])
    assert run_main(must_only=True, processes=3) == 0
    assert set(run.result()) == {BARE["id"], NAMED["id"]} and run.computed == [(70.05, 20.0), (66.55, -52.35)]
    assert not any("E040" in name for name in run.asked)
    assert PoolInThisProcess.made[0]["workers"] == 3
    assert "not in the file: 1" in capsys.readouterr().out


def test_the_command_line_is_read_strictly():
    assert build.options([]) == {"cached_only": False, "must_only": False, "processes": 8}
    assert build.options(["--cached-only", "--must-only", "--processes", "3"]) == \
        {"cached_only": True, "must_only": True, "processes": 3}
    with pytest.raises(SystemExit):
        build.options(["--everything"])
    with pytest.raises(SystemExit):
        build.options(["--processes", "0"])
