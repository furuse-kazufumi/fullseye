# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""門: optional 依存(cv2 / scikit-image / Pillow)が無い min 構成で、op が**別の答えを黙って返さない**。

2026-10-25 の探針(Studio をブラウザで動かす可否の測定)で、min 構成(numpy + scipy)で image / region 入力の
登録 op 488 本を走らせると **89 本が例外なく走って別の値を返した**(領域特徴 23 本が全部「面積率」0.0844、
``*_circle`` の構造要素が矩形、``skeleton`` が恒等写像、``lines_gauss`` が空の輪郭 …)。原因は
``_HAS_SK`` / ``_HAS_CV`` が偽のときの fallback 分岐がそう設計されていたから —— 例外が出ないので ULP の門が
無ければ気づけない。

この門は ``tools/check_fallback_parity.py`` で同じ入力・同じノブを **full**(何も塞がない)と **min**
(``sys.meta_path`` で cv2 / skimage / PIL の import を塞ぐ)の 2 つのサブプロセスで走らせ、89 本を**名指しで**
照合する。認める答えは 2 つだけ:

* **(A) 双子で一致**: 出力が bit 一致(浮動小数は 4 ULP かつ 1e-12 以内)—— ``numpy_twins`` の経路
* **(B) fail-closed**: min 側が :class:`backend_safe.MissingDependencyError`(何が無くて何を入れればよいかを言う)

どちらになるべきかも op ごとに名指しで持つ(``TWIN_EXACT`` / ``FAIL_CLOSED``)—— 双子が消えて fail-closed に
退行しても、fail-closed が外れて別の答えに戻っても赤になる。**範囲は自分で読まない**(件数の下限を assert)。

full 側に skimage / cv2 が無い環境では比較そのものが成立しないので、理由を明示して skip する
(CI の pytest ジョブは extras つきで走る。core-minimal ジョブはこのファイルを走らせない)。
"""
from __future__ import annotations

import importlib.util
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import check_fallback_parity as cfp  # noqa: E402

#: (A) scikit-image が無くても numpy の双子(numpy_twins)で bit 一致する op。
#: 末尾の 4 本(fractal_dimension / hx_estimate_tilt_zc / persistence_map / r2_sort_region)は skimage を使わず、
#: Pyodide(wasm)でだけ丸めや argsort の順で違った —— CPython では元から一致する(探針の「対象外」組だが、
#: 一致を保つことは門で言える)。
TWIN_EXACT = (
    # 構造要素(skimage.morphology.disk の双子)
    "erosion_circle", "dilation_circle", "opening_circle", "closing_circle",
    "erosion_golay", "dilation_golay", "opening_golay", "closing_golay", "remove_noise_region",
    "gray_erosion_shape", "gray_dilation_shape", "gray_opening_shape", "gray_closing_shape",
    # しきい値(threshold_otsu / apply_hysteresis_threshold の双子)
    "auto_threshold", "bin_threshold", "binary_threshold", "hysteresis_threshold",
    # 骨格化・細線化(skeletonize = Zhang–Suen 表、thin = Guo–Hall 表の双子)
    "skeleton", "morph_skeleton", "thinning", "thinning_golay", "thinning_seq", "pruning", "junctions_skeleton",
    "f2_gray_skeleton", "r2_split_skeleton_lines", "fill_up_shape",
    # 領域特徴(regionprops の双子 RegionTwin + perimeter / euler_number / moments の双子)
    "area_holes", "circularity", "compactness", "contlength", "diameter_region", "eccentricity", "elliptic_axis",
    "euler_number", "get_region_thickness", "height_width_ratio", "orientation_region", "rectangularity",
    "roundness", "moments_region_2nd", "moments_region_2nd_invar", "moments_region_2nd_rel_invar",
    "moments_region_3rd", "moments_region_3rd_invar", "moments_region_central", "moments_region_central_invar",
    # コーナー・テクスチャ(structure_tensor / graycomatrix の双子)
    "points_harris_binomial", "points_foerstner", "cooc_feature_matrix",
    # skimage を使わないのに skimage の import 失敗で全零に落ちていた(scipy.linalg の import を分けた)
    "sg_normalized_cut_2",
    # CPython では元から一致(探針では wasm の丸め / argsort 順で違った)
    "fractal_dimension", "hx_estimate_tilt_zc", "persistence_map", "r2_sort_region",
)

#: (B) bit 一致の numpy 双子が無い(Cython / cv2 の固定小数点)ので fail-closed にした op。
FAIL_CLOSED = (
    # cv2 の幾何変換・フィルタ
    "polar_trans_image", "polar_trans_image_ext", "polar_trans_image_inv", "polar_trans_region_inv",
    "projective_trans_image", "projective_trans_image_size", "projective_trans_region",
    "bilateral_filter", "guided_filter", "segment_image_mser",
    # skimage の Cython(find_contours / watershed / canny / frangi / convex_hull / rank.entropy / hough / sauvola)
    "gen_contour_region_xld", "threshold_sub_pix", "zero_crossing_sub_pix", "lines_gauss", "lines_facet",
    "watersheds", "watersheds_threshold", "pouring", "sg_watershed_gradient", "sg_felzenszwalb", "sg_slic_superpixels",
    "edges_image", "entropy_image", "var_threshold", "hough_line_trans", "hough_circle_trans",
    "convexity", "get_region_convex", "shape_trans", "f2_gray_inside",
    # 断層(radon / iradon / iradon_sart。numpy の近似は backends_tomo._radon_np 等の名前でだけ呼べる)
    "tm_radon_forward", "tm_fbp_reconstruct", "tm_sart_reconstruct", "tm_backproject_unfiltered",
)

ALL_OPS = TWIN_EXACT + FAIL_CLOSED
KNOBS = ((0.5, 0.5), (0.2, 0.8))
GOOD = {"bit_identical", "within_ulp"}


def test_the_scope_is_the_89_named_ops_and_nothing_is_counted_twice():
    assert len(set(ALL_OPS)) == len(ALL_OPS) == 89, len(ALL_OPS)
    assert len(TWIN_EXACT) == 55 and len(FAIL_CLOSED) == 34
    assert not set(TWIN_EXACT) & set(FAIL_CLOSED)


def _full_side_ready():
    missing = [m for m in ("skimage", "cv2", "PIL") if importlib.util.find_spec(m) is None]
    return missing


@pytest.fixture(scope="module")
def parity():
    missing = _full_side_ready()
    if missing:
        pytest.skip("比較できない: full 側(このプロセス)に %s が無いので min 構成との照合が成立しない "
                    "(extras つきの環境で走らせること)" % ", ".join(missing))
    per = cfp.run(list(ALL_OPS), block=cfp.DEFAULT_BLOCK, knobs=KNOBS, synthetic=True)
    n_inputs = len({k.split("|")[1] for k in per})
    assert n_inputs == 2, "coins と合成画像の 2 枚が要る: %d" % n_inputs
    assert len(per) == 89 * len(KNOBS) * n_inputs, len(per)
    return per


def _verdicts(per, op):
    rows = {k: v for k, v in per.items() if k.split("|")[0] == op}
    assert len(rows) == len(KNOBS) * 2, (op, sorted(rows))
    return rows


@pytest.mark.parametrize("op", TWIN_EXACT)
def test_twin_gives_the_same_answer_without_skimage_or_cv2(parity, op):
    rows = _verdicts(parity, op)
    bad = {k: v for k, v in rows.items() if v["verdict"] not in GOOD}
    assert not bad, "min 構成で別の答え(か例外): %s" % bad


@pytest.mark.parametrize("op", FAIL_CLOSED)
def test_op_without_a_twin_refuses_with_a_clear_dependency_error(parity, op):
    rows = _verdicts(parity, op)
    assert len(rows) == len(KNOBS) * 2, sorted(rows)      # 空の列への表明にしない(件数を数える)
    bad = {k: v for k, v in rows.items() if v["verdict"] != "missing_dependency"}
    assert not bad, "min 構成で MissingDependencyError 以外(= 別の答えを返している): %s" % bad
    for v in rows.values():
        msg = v["error"]
        assert "pip install" in msg and "not installed" in msg and op in msg, msg


def test_missing_dependency_is_not_swallowed_by_any_policy(monkeypatch):
    """``guard`` も ``api.apply`` の fallback / warn も、この例外だけは落とさず通す。"""
    import numpy as np
    import api
    import backend_safe as bs

    def boom(v, a, b):
        raise bs.missing_dependency("skimage", "unit test", op="unit_test_op")

    v = np.zeros((4, 4))
    w = bs.guard(boom, "image")                       # 内側のガード(backends の _safe)
    with pytest.raises(bs.MissingDependencyError):
        w(v, 0.5, 0.5)
    bs.clear_fallbacks()
    for policy in ("fallback", "warn", "raise"):      # 外側の境界(api._apply_impl と同じ _run_guarded)
        with pytest.raises(bs.MissingDependencyError, match="pip install"):
            api._run_guarded("unit_test_op", lambda: w(v, 0.5, 0.5), policy, "image", v)
    assert "unit_test_op" not in bs.fallback_counts(), "fail-closed の例外が fallback として台帳に載っている"
