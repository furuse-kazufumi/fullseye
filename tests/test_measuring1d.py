"""measuring1d (HALCON-style 1-D measuring): sub-pixel edge positions in image
coordinates, gray-difference amplitudes, unit sample spacing, edges at the ends.

Regressions for the 2026-09-02 findings:
  * ``amplitude`` was the smoothed-gradient peak (~0.32x the gray step, sigma
    dependent) and ``threshold`` was applied to it — HALCON-style thresholds
    silently rejected real edges.  Now amplitude = gray difference across the edge.
  * ``pos`` was a profile index with non-unit spacing for fractional length1 / arcs,
    no (row, col) was returned, and edges within ~1.5 px of the ends were dropped.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import measuring1d as m1  # noqa: E402


def _area_step(W, e, lo=0.0, hi=1.0, rising=True):
    """pixel k covers [k-0.5, k+0.5]; edge at e (pixel-centre convention)."""
    k = np.arange(W)
    frac = np.clip(k + 0.5 - e, 0, 1)
    v = lo + (hi - lo) * frac
    return v if rising else (hi + lo - v)


def _img(row, H=41):
    return np.tile(row[None, :], (H, 1))


@pytest.mark.parametrize("sigma", [0.5, 1.0, 2.0, 3.0])
def test_unit_step_amplitude_is_the_gray_difference(sigma):
    im = _img(_area_step(41, 10.37))
    ms = m1.gen_measure_rectangle2(20, 15, 0.0, 10, 3, im.shape)
    ed = m1.measure_pos(im, ms, sigma=sigma, threshold=0.05)
    assert len(ed) == 1
    assert abs(ed[0]["amplitude"] - 1.0) < 0.02
    assert ed[0]["polarity"] == "positive"
    assert abs(ed[0]["col"] - 10.37) < 0.1 and abs(ed[0]["row"] - 20) < 1e-9


def test_threshold_is_in_gray_units():
    im = _img(_area_step(41, 10.37, 0.2, 0.8))                # 0.6 step
    ms = m1.gen_measure_rectangle2(20, 15, 0.0, 10, 3, im.shape)
    assert len(m1.measure_pos(im, ms, sigma=1.0, threshold=0.5)) == 1
    assert len(m1.measure_pos(im, ms, sigma=1.0, threshold=0.7)) == 0
    e = m1.measure_pos(im, ms, sigma=1.0, threshold=0.5)[0]
    assert abs(e["amplitude"] - 0.6) < 0.02
    # gray units follow the image: a uint8 100->200 step has amplitude ~100
    im8 = (_img(_area_step(41, 10.37, 100, 200))).astype(np.uint8)
    e8 = m1.measure_pos(im8, ms, sigma=1.0, threshold=50)
    assert len(e8) == 1 and abs(e8[0]["amplitude"] - 100) < 3


def test_falling_edge_sign_and_transition_filter():
    im = _img(_area_step(41, 10.37, rising=False))
    ms = m1.gen_measure_rectangle2(20, 15, 0.0, 10, 3, im.shape)
    ed = m1.measure_pos(im, ms, sigma=1.0, threshold=0.05)
    assert len(ed) == 1 and ed[0]["polarity"] == "negative" and ed[0]["amplitude"] < -0.98
    assert m1.measure_pos(im, ms, sigma=1.0, threshold=0.05, transition="positive") == []


@pytest.mark.parametrize("e", np.arange(10.0, 11.01, 0.1).tolist())
def test_subpixel_position_sweep(e):
    im = _img(_area_step(41, e))
    ms = m1.gen_measure_rectangle2(20, 15, 0.0, 10, 3, im.shape)
    ed = m1.measure_pos(im, ms, sigma=1.0, threshold=0.05)
    assert len(ed) == 1
    assert abs(ed[0]["col"] - e) < 0.06
    assert abs(ed[0]["pos"] - (e - ms["cols"][0])) < 0.06          # pos in px from start


def test_fractional_length1_has_unit_spacing_and_correct_col():
    ms = m1.gen_measure_rectangle2(20, 15, 0.0, 10.3, 3, (41, 41))
    assert ms["spacing"] == 1.0
    assert np.allclose(np.diff(ms["cols"]), 1.0)
    im = _img(_area_step(41, 10.37))
    ed = m1.measure_pos(im, ms, sigma=1.0, threshold=0.05)
    assert len(ed) == 1 and abs(ed[0]["col"] - 10.37) < 0.06
    assert abs(ed[0]["dist"] - ed[0]["pos"]) < 1e-12


@pytest.mark.parametrize("e", [5.3, 5.8, 6.3, 23.7, 24.2, 24.7])
def test_edges_near_the_rectangle_ends_are_found(e):
    """rect covers cols 5..25; edges within 1.5 px of either end used to be dropped."""
    im = _img(_area_step(41, e))
    ms = m1.gen_measure_rectangle2(20, 15, 0.0, 10, 3, im.shape)
    ed = m1.measure_pos(im, ms, sigma=1.0, threshold=0.05)
    assert len(ed) == 1 and abs(ed[0]["col"] - e) < 0.1


def test_edge_outside_the_rectangle_is_not_reported():
    im = _img(_area_step(41, 27.0))
    ms = m1.gen_measure_rectangle2(20, 15, 0.0, 10, 3, im.shape)      # cols 5..25
    assert m1.measure_pos(im, ms, sigma=1.0, threshold=0.05) == []


def test_vertical_measure_returns_row_col():
    imv = _img(_area_step(41, 10.37)).T                                # edge across rows
    ms = m1.gen_measure_rectangle2(15, 20, np.pi / 2, 10, 3, imv.shape)
    ed = m1.measure_pos(imv, ms, sigma=1.0, threshold=0.05)
    assert len(ed) == 1
    assert abs(ed[0]["row"] - 10.37) < 0.06 and abs(ed[0]["col"] - 20) < 1e-9


def test_tilted_measure_with_band_averaging():
    H = W = 61
    yy, xx = np.mgrid[0:H, 0:W]
    phi = 0.3
    s = (xx - 30) * np.cos(phi) + (yy - 30) * np.sin(phi)
    im = np.clip(s - 3.37 + 0.5, 0, 1)                                 # edge at s = 3.37
    ms = m1.gen_measure_rectangle2(30, 30, phi, 10, 5, im.shape)
    ed = m1.measure_pos(im, ms, sigma=1.0, threshold=0.05)
    assert len(ed) == 1
    e = ed[0]
    s_hat = (e["col"] - 30) * np.cos(phi) + (e["row"] - 30) * np.sin(phi)
    assert abs(s_hat - 3.37) < 0.1


def test_arc_measure_unit_spacing_and_position():
    H = W = 101
    yy, xx = np.mgrid[0:H, 0:W]
    ang = np.arctan2(yy - 50.0, xx - 50.0)
    theta0 = 0.7
    im = (ang < theta0).astype(float)                                  # angular step
    ms = m1.gen_measure_arc(50, 50, 20, 0.0, np.pi / 2, 3, im.shape)
    assert abs(ms["spacing"] - 1.0) < 0.05
    ed = m1.measure_pos(im, ms, sigma=1.0, threshold=0.3)
    assert len(ed) == 1
    e = ed[0]
    assert abs(e["dist"] - theta0 * 20) < 0.6
    assert abs(np.hypot(e["row"] - 50, e["col"] - 50) - 20) < 0.3
    assert abs(np.arctan2(e["row"] - 50, e["col"] - 50) - theta0) < 0.03


def test_measure_pairs_width_and_points():
    bar = np.clip(_area_step(41, 10.37) - _area_step(41, 17.82), 0, 1)
    im = _img(bar)
    ms = m1.gen_measure_rectangle2(20, 15, 0.0, 10, 3, im.shape)
    pr = m1.measure_pairs(im, ms, sigma=1.0, threshold=0.05)
    assert len(pr) == 1
    p = pr[0]
    assert abs(p["width"] - 7.45) < 0.1
    assert abs(p["first_point"][1] - 10.37) < 0.06 and abs(p["second_point"][1] - 17.82) < 0.06
    # fuzzy pairing ranks the pair closest to pair_size first
    bar2 = bar + np.clip(_area_step(41, 28.1) - _area_step(41, 32.6), 0, 1)
    ms2 = m1.gen_measure_rectangle2(20, 20, 0.0, 19, 3, im.shape)
    fz = m1.fuzzy_measure_pairing(_img(bar2), ms2, 1.0, 0.05, pair_size=4.5)
    assert len(fz) == 2 and abs(fz[0]["width"] - 4.5) < 0.15 and abs(fz[1]["width"] - 7.45) < 0.1


def test_translate_measure_moves_everything():
    im = _img(_area_step(41, 12.37))
    ms = m1.translate_measure(m1.gen_measure_rectangle2(20, 15, 0.0, 10, 3, im.shape), 0, 2)
    ed = m1.measure_pos(im, ms, sigma=1.0, threshold=0.05)
    assert len(ed) == 1 and abs(ed[0]["col"] - 12.37) < 0.06
    assert ms["origin"] == (20.0, 17.0)


def test_non_2d_image_raises():
    ms = m1.gen_measure_rectangle2(20, 15, 0.0, 10, 3, (41, 41))
    with pytest.raises(ValueError):
        m1.measure_pos(np.zeros((41, 41, 3)), ms)


# --------------------------------------------------------------------------- #
# 画素 → mm(2026-09-15)。構造データ: 既知寸法の円板を描いて、校正 → 換算で往復する。
# --------------------------------------------------------------------------- #
def _disk(size, cy, cx, r, ss=8):
    """被覆率で描いた暗い円板(真値 r [px])。"""
    n = size * ss
    yy = (np.arange(n) + 0.5) / ss - 0.5
    inside = ((yy[:, None] - cy) ** 2 + (yy[None, :] - cx) ** 2) <= r * r
    cov = inside.reshape(size, ss, size, ss).mean(axis=(1, 3))
    return 0.8 - 0.6 * cov


def test_pixel_to_world_round_trips_a_known_disk_through_calibration():
    """基準の的(直径 10.00 mm を 200 px に写す)で mm/px を出し、被測定の円板の
    直径が mm で真値に戻ること。校正と測定を同じ op 族で取る(公称倍率は使わない)。"""
    import metrology as mt

    mm_per_px_true = 0.05
    ref_r_px, dut_r_px = 100.0, 61.3                      # 的 10.00 mm、被測定 6.13 mm
    for r_px, name in ((ref_r_px, "ref"), (dut_r_px, "dut")):
        img = _disk(int(2 * r_px + 40), r_px + 20.37, r_px + 20.11, r_px)
        model = mt.create_metrology_model()
        mt.add_metrology_object_circle_measure(model, r_px + 20.37, r_px + 20.11, r_px + 1.0, n=72)
        res = mt.apply_metrology_model(model, img, measure_length=6.0, sigma=1.0, threshold=0.1)[0]
        assert res["params"] is not None
        if name == "ref":
            k = m1.mm_per_px_from_reference(2.0 * res["params"]["radius"], 10.0)
            assert abs(k - mm_per_px_true) < 1e-4 * mm_per_px_true * 10   # 0.1 %
        else:
            d_mm = m1.pixel_to_world(2.0 * res["params"]["radius"], k)
            assert abs(d_mm - 2 * dut_r_px * mm_per_px_true) < 0.01       # 10 µm
            rows = m1.table_px_to_mm([res], k)
            assert abs(rows[0]["params"]["radius_mm"] - dut_r_px * mm_per_px_true) < 0.005
            assert "rms_mm" in rows[0] and "radius" in rows[0]["params"]   # px 列は残る
            assert "params" in res and "radius_mm" not in res["params"]    # 入力は変えない


def test_table_px_to_mm_converts_measure_pairs_rows_and_skips_positions():
    bar = np.clip(_area_step(41, 10.37) - _area_step(41, 17.82), 0, 1)
    im = _img(bar)
    ms = m1.gen_measure_rectangle2(20, 15, 0.0, 10, 3, im.shape)
    pr = m1.table_px_to_mm(m1.measure_pairs(im, ms, sigma=1.0, threshold=0.05), 0.02)
    assert len(pr) == 1
    assert abs(pr[0]["width_mm"] - 7.45 * 0.02) < 0.1 * 0.02
    assert "first_mm" not in pr[0] and "first_point_mm" not in pr[0]       # 位置は換算しない
    single = m1.table_px_to_mm({"width": 5.0, "note": "x"}, 2.0)
    assert single["width_mm"] == 10.0 and "note_mm" not in single


@pytest.mark.parametrize("fn,args", [
    (m1.mm_per_px_from_reference, (0.0, 10.0)),
    (m1.mm_per_px_from_reference, (100.0, -1.0)),
    (m1.mm_per_px_from_reference, (float("inf"), 1.0)),
    (m1.pixel_to_world, (1.0, 0.0)),
    (m1.pixel_to_world, (float("nan"), 1.0)),
    (m1.pixel_to_world, ("12", 1.0)),
    (m1.table_px_to_mm, ([{"width": 1.0}], 0.0)),
    (m1.table_px_to_mm, ("not a table", 1.0)),
    (m1.table_px_to_mm, ([1.0, 2.0], 1.0)),
])
def test_scale_ops_fail_closed(fn, args):
    with pytest.raises(ValueError):
        fn(*args)


def test_scale_ops_are_in_the_ledger_and_reach_the_public_tiers():
    """登録面: 台帳(scale カテゴリ)と fs.ledger の両方から届くこと。"""
    import fullseye as fs
    import opsmeasure1d as M

    assert M.list_ops("scale") == ["mm_per_px_from_reference", "pixel_to_world", "table_px_to_mm"]
    assert M.info("pixel_to_world")["in"] == ["measurement"]
    assert M.info("table_px_to_mm")["out"] == "table"
    assert fs.ledger.pixel_to_world(200.0, 0.05) == 10.0
    assert any(h["op"] == "mm_per_px_from_reference" for h in fs.op_find("mm per px"))
