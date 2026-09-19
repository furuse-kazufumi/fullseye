# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fullseye.golden — 基準画像との比較で欠陥を測る(検査ワークフロー層 #3)。

恒等式で固定する: 同一画像→欠陥 0・ssim 1 / 並進した良品→shift が測れ合わせれば欠陥 0 /
欠陥を足せば count 1・area ≈ 足した大きさ / mask の外は数えない / min_area で足切り /
max_shift 超えは合わせず align_ok=0 / 形違い・NaN は ValueError / inspect_batch+judge で欠陥品だけ ng。
"""
import numpy as np
import pytest

import fullseye as fs
from fullseye.golden import compare_to_golden, golden_measure, golden_spec, GOLDEN_KEYS
from fullseye.judge import judge


def _golden(seed=0):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:96, 0:96]
    im = 0.35 + 0.25 * np.sin(xx / 9.0) * np.cos(yy / 11.0) + 0.02 * rng.standard_normal((96, 96))
    im[40:56, 40:56] = 0.9                       # 部品の明部
    return np.clip(im, 0, 1)


def _shift(im, dr, dc):
    """縁を端の値で埋めた並進(np.roll の巻き込みを使わない=現実の撮像に近い)。"""
    from scipy.ndimage import shift
    return shift(im, (dr, dc), order=0, mode="nearest")


def test_identical_image_has_no_defects_and_ssim_one():
    g = _golden()
    out = compare_to_golden(g, g)
    m = out["measurements"]
    assert set(m) == set(GOLDEN_KEYS)
    assert m["defect_area"] == 0 and m["defect_count"] == 0
    assert m["ssim"] == pytest.approx(1.0) and m["shift_row"] == 0 and m["shift_col"] == 0
    assert m["align_ok"] == 1.0 and m["valid_fraction"] == 1.0
    assert out["diff"].shape == g.shape and not out["defect_mask"].any()


def test_translated_good_part_is_aligned_and_clean():
    g = _golden()
    im = _shift(g, 3, -5)
    out = compare_to_golden(im, g, threshold=0.15)
    m = out["measurements"]
    assert (m["shift_row"], m["shift_col"]) == (-3.0, 5.0)     # image を golden に戻す並進
    assert m["align_ok"] == 1.0
    assert m["defect_area"] == 0, "位置合わせ後の良品に欠陥が出ている: %s" % m
    assert m["valid_fraction"] < 1.0                           # 巻き込んだ縁は valid から外れる
    # 合わせなければ明部のずれがそのまま欠陥になる
    raw = compare_to_golden(im, g, align=False, threshold=0.15)["measurements"]
    assert raw["defect_area"] > 0 and raw["shift_row"] == 0


def test_added_blob_is_one_defect_with_its_area():
    g = _golden()
    im = g.copy()
    im[10:16, 70:78] = 0.95                                     # 6x8 = 48 px の異物
    m = compare_to_golden(im, g, threshold=0.2)["measurements"]
    assert m["defect_count"] == 1 and m["defect_area"] == 48 and m["defect_area_max"] == 48
    assert m["max_diff"] > 0.4 and m["ssim"] < 1.0


def test_mask_excludes_regions_and_min_area_drops_specks():
    g = _golden()
    im = g.copy()
    im[10:16, 70:78] = 0.95                                     # 48 px
    im[80, 5] = 0.95                                            # 1 px の点
    mask = np.ones_like(g, dtype=bool)
    mask[0:30, :] = False                                       # 上 30 行は見ない → 48 px は除外
    m = compare_to_golden(im, g, threshold=0.2, mask=mask)["measurements"]
    assert m["defect_count"] == 1 and m["defect_area"] == 1        # 残るのは 1 px の点だけ
    m2 = compare_to_golden(im, g, threshold=0.2, mask=mask, min_area=2)["measurements"]
    assert m2["defect_count"] == 0 and m2["defect_area"] == 0
    # 番号は残した成分だけで振り直される
    out = compare_to_golden(im, g, threshold=0.2, min_area=2)
    assert out["labels"].max() == 1 and out["measurements"]["defect_count"] == 1


def test_shift_beyond_max_shift_is_not_applied_and_flagged():
    g = _golden()
    im = _shift(g, 6, 0)
    m = compare_to_golden(im, g, max_shift=3, threshold=0.15)["measurements"]
    assert m["align_ok"] == 0.0 and m["shift_row"] == -6.0
    assert m["defect_area"] > 0                                  # 合わせていないので差分が残る
    assert m["valid_fraction"] == 1.0                            # 何も巻き込んでいない
    v = judge(m, golden_spec(max_shift=3))
    assert v.status == "ng" and {x["key"] for x in v.result["violations"]} >= {"align_ok", "shift_row"}


def test_blur_suppresses_one_pixel_edge_jitter():
    g = _golden()
    im = g.copy()
    im[40:56, 56] = 0.9                                          # 明部の右縁が 1 px 太った
    hard = compare_to_golden(im, g, threshold=0.3)["measurements"]
    soft = compare_to_golden(im, g, threshold=0.3, blur=1.5)["measurements"]
    assert hard["defect_area"] > 0 and soft["defect_area"] < hard["defect_area"]


@pytest.mark.parametrize("bad", [
    lambda g: (g[:, :50], g),                                    # 形違い
    lambda g: (np.where(np.arange(96)[:, None] == 3, np.nan, g), g),
    lambda g: (g[None], g),                                       # 3-D
    lambda g: (g, np.zeros((0, 0))),
])
def test_bad_inputs_fail_closed(bad):
    g = _golden()
    im, ref = bad(g)
    with pytest.raises(ValueError):
        compare_to_golden(im, ref)


def test_bad_mask_and_bad_knobs_fail_closed():
    g = _golden()
    with pytest.raises(ValueError):
        compare_to_golden(g, g, mask=np.ones((10, 10), bool))
    with pytest.raises(ValueError):
        compare_to_golden(g, g, min_area=0)
    with pytest.raises(ValueError):
        golden_measure(g, mask=np.ones((3, 3), bool))


def test_golden_spec_is_a_valid_judge_spec():
    spec = golden_spec(max_defect_area=10, max_defect_count=1, min_ssim=0.9, max_shift=2)
    assert set(spec) == {"defect_area", "defect_count", "ssim", "shift_row", "shift_col", "align_ok"}
    g = _golden()
    assert judge(compare_to_golden(g, g)["measurements"], spec).status == "ok"
    assert judge(compare_to_golden(g, g)["measurements"], golden_spec()).status == "ok"


def test_batch_with_golden_measure_flags_only_the_defective_part(tmp_path):
    g = _golden()
    lot = tmp_path / "lot"
    lot.mkdir()
    for i in range(4):
        np.save(lot / ("p%d.npy" % i), _shift(g, (i % 3) - 1, 1 - (i % 2)))   # 良品(±1 px ずれ)
    bad = g.copy()
    bad[20:28, 20:30] = 1.0                                      # 異物 80 px(背景 ≤ 0.62 なので全画素で差 > 0.2)
    np.save(lot / "p4.npy", bad)
    out = fs.inspect_batch(lot, None, measure=fs.golden_measure(g, threshold=0.2, max_shift=3),
                           spec=fs.golden_spec(max_shift=3))
    status = [r["verdict"]["status"] for r in out["rows"]]
    assert status == ["ok", "ok", "ok", "ok", "ng"], status
    assert out["rows"][4]["measurements"]["defect_area"] == 80
    assert "defect_area" in out["series"] and out["spc"]["ssim"]["n"] == 5


def test_facade_exposes_the_golden_layer():
    assert fs.compare_to_golden is compare_to_golden and fs.golden_measure is golden_measure
    assert {"compare_to_golden", "golden_measure", "golden_spec"} <= set(fs.__all__)
