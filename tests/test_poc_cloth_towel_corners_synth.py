"""poc_cloth_towel_corners_synth の門を小さく回す: 折りの幾何、描画の整合、検出が真値に合うこと、
壊れる条件で検出が崩れる(無理に出さない)こと、別の真値では当たらないこと。

The full PoC (20 seeds x 17 conditions, ~2 min) runs in ``test_poc_scripts_run.py``; these are the cheap pieces.
"""
import numpy as np
import pytest

from examples import poc_cloth_towel_corners_synth as P


@pytest.mark.parametrize("fold,layers,ncre,nopen", [("flat", (1, 1, 1, 1), 0, 4), ("half", (2, 2, 2, 2), 1, 2),
                                                    ("third", (1, 1, 2, 2), 1, 2), ("quarter", (4, 4, 4, 4), 2, 1)])
def test_fold_geometry(fold, layers, ncre, nopen):
    img, tr = P.render_scene(0, fold=fold, wrinkle=0.0)
    assert tuple(tr["layers"]) == layers
    assert len(tr["creases_px"]) == ncre and int(tr["open"].sum()) == nopen
    assert np.isfinite(img).all() and img.min() >= 0 and img.max() <= 1 and np.ptp(img) > 0.2
    assert 0.99 < tr["cover"].sum() / P.shoelace(tr["corners_px"]) < 1.005


def test_stack_area_is_conserved_by_folding():
    sheets, _ = P.fold_stack(P.FOLD_PLANS["quarter"])
    assert len(sheets) == 4
    assert np.isclose(sum(abs(P._area(s["V"])) for s in sheets), P.W_T * P.L_T)


@pytest.fixture(scope="module")
def easy():
    img, tr = P.render_scene(1, fold="half", contrast=1.0, wrinkle=1.0, light_az=90.0)
    return img, tr


def test_detectors_find_the_corners_in_an_easy_image(easy):
    img, tr = easy
    for det in (P.detect_proposed(img), P.detect_proposed(img, chroma_only=True), P.detect_minrect(P.segment(img)[1])):
        err, _ = P.match_corners(det["corners"], tr["corners_px"], tr["mm_per_px"])
        assert np.all(np.isfinite(err)) and err.max() < 2.5           # 実測は 1〜2 mm(1 画素 = 1 mm)。3 px ずれたら落ちる


def test_a_truth_shifted_by_20_mm_is_not_matched(easy):
    """対照: 真の隅を 20 mm 平行移動した偽の真値には当たらない(別の種の真値は隅どうしが 6 px しか離れない種があり、対照にならなかった)。"""
    img, tr = easy
    fake = tr["corners_px"] + np.array([0.0, 20.0 / tr["mm_per_px"]])
    err, _ = P.match_corners(P.detect_proposed(img)["corners"], fake, tr["mm_per_px"])
    assert not np.any(err <= P.FOUND_MM)
    err, _ = P.match_corners(P.detect_proposed(img)["corners"], tr["corners_px"], tr["mm_per_px"])
    assert np.all(err <= P.FOUND_MM)                                  # 同じ検出は本物の真値には全部当たる


def test_a_detector_shifted_by_3_px_is_caught(easy):
    img, tr = easy
    D = P.detect_proposed(img)["corners"] + 3.0
    err, _ = P.match_corners(D, tr["corners_px"], tr["mm_per_px"])
    assert np.nanmax(err) > 2.5 or not np.all(np.isfinite(err))


def test_every_gate_has_a_band():
    """門の名前と BANDS が 1 対 1(帯の無い門は KeyError、使われない帯は死んだ設定)。"""
    names = set(P.BANDS)
    assert len(names) >= 170 and all(lo is None or hi is None or lo <= hi for lo, hi in P.BANDS.values())


def test_far_baseline_picks_four_separated_extremes(easy):
    img, _ = easy
    d = P.detect_far(P.segment(img)[1])
    assert len(d["corners"]) == 4
    dd = np.linalg.norm(d["corners"][:, None] - d["corners"][None], axis=2)
    assert dd[np.triu_indices(4, 1)].min() >= 40


def test_zero_contrast_is_refused_not_invented():
    """タオルと台が同じ平均色だと、領域に頼る提案は隅を出さない(出しても当たらない)。Harris は領域を使わない。"""
    rec = [P.evaluate(s, fold="half", contrast=0.0) for s in range(3)]
    assert P.recall(rec, "propc").mean() < 0.2
    assert P.recall(rec, "harris").mean() > 0.4


def test_hem_line_ranks_the_open_corner_first():
    rec = [P.evaluate(s, fold="quarter", contrast=1.0, wrinkle=0.0) for s in range(8)]
    assert P.hit1(rec, "prop").mean() >= 0.75                     # 偶然は 0.25
    off = [P.evaluate(s, fold="quarter", contrast=1.0, wrinkle=0.0, hem=False) for s in range(8)]
    assert P.hit1(off, "prop").mean() <= P.hit1(rec, "prop").mean() - 0.3


def test_blank_image_gives_no_corners():
    d = P.detect_proposed(np.full(P.SHAPE + (3,), 0.4))
    assert not d["ok"] and len(d["corners"]) == 0


def test_stats_helpers():
    m, lo, hi = P.boot_ci([1.0] * 10)
    assert m == lo == hi == 1.0
    assert P.auc([2, 3], [0, 1]) == 1.0 and P.auc([1], [1]) == 0.5
    err, own = P.match_corners(np.array([[0.0, 0.0]]), np.array([[0.0, 20.0]]), 1.0, gate_mm=15.0)
    assert np.isnan(err[0]) and own[0] == -1
