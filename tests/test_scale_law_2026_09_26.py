# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""特徴の**尺度法則** —— 「k 倍に拡大したら値は k^p 倍」の p を宣言して固定する。

★これは metamorphic relation(変成関係)である。真値が 1 つも要らない ——
「入力をこう変えたら出力はこう変わるはず」だけで採点する。真値の無いプログラムを
検算する古典的な手口で、`Pseudo-oracles for non-testable programs`(Weyuker 1981)、
`Metamorphic Testing and Its Applications`(Chen 2004)に名前がある
(手元の調査コーパス `test_oracle_corpus_v2`)。

★**一律の変成関係は使えない**ことを先に測った。「平行移動で変わらない」を全 op に
当てると 35 本中 30 本が違反し、そのほとんどは**違反して当然**だった(重心は動くのが
正しく、個数は尺度不変が正しい)。免除が 30 本になる門は門ではない。効くのは
「その量が**何の次元を持つか**」の宣言で、それは尺度指数 1 つで書ける:

    p = 0  尺度不変(比・位相の個数・正規化した不変量)
    p = 1  長さ(周囲長・直径・厚み・楕円半径)
    p = 2  面積
    p = 4  2 次モーメント(正規化なし)
    p = 5  3 次モーメント(正規化なし)
    p = 8  アフィンモーメント不変量 I1(= μ20μ02 - μ11^2)

★この 1 枚が拾うもの: 2026-09-26 に直した 8 op のうち **5 本**は、`p` が宣言と
食い違うことで**HALCON の数値を一つも使わずに**出ていた ——
`area_center`(面積を画布で割っていたので p=0、あるべきは 2)、
`contlength` / `get_region_thickness` / `diameter_region`(p=0、あるべきは 1)、
`elliptic_axis`(Anisometry/10 を返していたので p=0、あるべきは 1)。

拡大は ``np.kron``(整数倍・補間なし)で行う。二値マスクを任意角で回すと周囲長が
3.8 倍荒れるが、整数倍の拡大は**補間を伴わない**ので期待値を厳密に書ける。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import ops  # noqa: E402

# --------------------------------------------------------------------------- #
# 宣言表 —— 成分ごとの尺度指数。★新しい op を足したらここにも書く(完全性を門で見る)
# --------------------------------------------------------------------------- #
#: 周囲長を経由する量は、ラスタ化の偏りで p が厳密に出ない(docs/KNOWN_ISSUES.md §50)。
#: そこだけ許容差を広げ、理由を名前で残す。
_PERIMETER_BASED = {"circularity", "classify_shape", "compactness", "convexity",
                    "roundness", "rectangularity"}

SCALE_LAW: dict[str, tuple[float, ...]] = {
    # --- 位置と大きさ(画素) -----------------------------------------------
    "area_center":              (2.0, 1.0, 1.0),   # 面積[画素], 重心行, 重心列
    "contlength":               (1.0,),            # 輪郭長
    "diameter_region":          (1.0,),            # 最大弦
    "get_region_thickness":     (1.0,),            # 最大内接円 x 2
    "elliptic_axis":            (1.0, 1.0, 0.0),   # Ra, Rb, Phi(角は不変)
    "r2_runlength_features":    (1.0,),            # ランの長さ
    # --- 無次元(比・形状指数)----------------------------------------------
    "area_frac":                (0.0,),
    "circularity":              (0.0,),
    "classify_shape":           (0.0,),
    "compactness":              (0.0,),
    "convexity":                (0.0,),
    "eccentricity":             (0.0, 0.0, 0.0),   # Anisometry, Bulkiness, StructureFactor
    "height_width_ratio":       (0.0,),
    "rectangularity":           (0.0,),
    "roundness":                (0.0,),
    "orientation_region":       (0.0,),            # 角
    "hx_distance_pr":           (0.0,),
    "hx_test_region_point":     (0.0,),
    "hx_test_region_points":    (0.0,),
    "r3_region_features":       (0.0,),
    "r3_runlength_distribution": (0.0,),
    # --- 位相の個数(尺度不変)----------------------------------------------
    "area_holes":               (0.0,),
    "blob_count":               (0.0,),
    "connect_and_holes":        (0.0,),
    "count_obj":                (0.0,),
    "cv_cc_count":              (0.0,),
    "euler_number":             (0.0,),
    "sk_euler":                 (0.0,),
    # --- モーメント族 ---------------------------------------------------------
    # ★HALCON の同名演算子は**正規化しない**中心モーメントを返すので、本来は
    #   p=4 / 5 / 8 になる。この repo は 1 スカラーへ合成する際に Hu の正規化
    #   不変量を使っており p=0 である(docs/KNOWN_ISSUES.md §52、巡 13 で直す)。
    #   ここは **あるべき値**を書き、直るまで strict xfail で開いたままにする ——
    #   免除台帳に「例外」として畳み込むと、直ったことに誰も気づけない。
    "moments_region_2nd":       (4.0,),
    "moments_region_3rd":       (5.0,),
    "moments_region_central":   (8.0,),
    # 正規化つきは尺度不変が正しい
    "moments_region_2nd_invar": (0.0,),
    "moments_region_2nd_rel_invar": (0.0,),
    "moments_region_3rd_invar": (0.0,),
    "moments_region_central_invar": (0.0,),
}

#: ★§52 が直るまで落ちる 3 本。`strict=True` なので、**直った瞬間に「予期せぬ成功」で
#: 落ちて**この表を直せと言ってくる(黙って通り続ける免除にしない)。
_OPEN_DEFECT_52 = {"moments_region_2nd", "moments_region_3rd", "moments_region_central"}


def _shape():
    """非対称で穴のある形。対称だと奇数次モーメントが厳密に 0 になり、比が取れない。"""
    m = np.zeros((60, 60))
    m[12:34, 9:47] = 1.0
    m[28:46, 18:28] = 1.0
    m[18:22, 28:36] = 0.0
    return m


def _call(name, x):
    return np.ravel(np.asarray(ops.RT[name](np.array(x, np.float64), 0.5, 0.5), np.float64))


def _exponents(name, ks=(2, 3)):
    """k 倍に拡大したときの実測指数 p(成分ごと)。ks で一致しなければ冪則でない。"""
    base = _shape()
    v1 = _call(name, base)
    out = []
    for k in ks:
        vk = _call(name, np.kron(base, np.ones((k, k))))
        assert vk.shape == v1.shape, "%s: 拡大で成分数が変わった" % name
        p = []
        for a, b in zip(v1, vk):
            if abs(a) < 1e-12:
                p.append(0.0 if abs(b) < 1e-9 else np.nan)
            else:
                r = b / a
                p.append(np.log(abs(r)) / np.log(k) if r > 0 else np.nan)
        out.append(np.array(p, np.float64))
    return out


REGION_FEATURE_OPS = sorted(
    o.name for o in ops._BY_NAME.values()
    if o.in_sort == "region" and o.out_sort in ("feature", "match", "counts"))


# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", [n for n in SCALE_LAW if n not in _OPEN_DEFECT_52])
def test_the_feature_follows_its_declared_scale_law(name):
    """k 倍に拡大したら k^p 倍になる(p は宣言表のもの)。"""
    want = np.array(SCALE_LAW[name], np.float64)
    got2, got3 = _exponents(name)
    tol = 0.08 if name in _PERIMETER_BASED else 0.05
    assert got2.shape == want.shape, "%s: 成分数 %d(宣言 %d)" % (name, got2.size, want.size)
    for label, got in (("2 倍", got2), ("3 倍", got3)):
        bad = ~np.isclose(got, want, atol=tol, equal_nan=True)
        assert not bad.any(), (
            "%s を %s に拡大: 尺度指数 %s(宣言 %s)—— 次元が宣言と違う"
            % (name, label, np.round(got, 3), want))


@pytest.mark.parametrize("name", sorted(_OPEN_DEFECT_52))
@pytest.mark.xfail(strict=True, reason="docs/KNOWN_ISSUES.md §52: HALCON の同名演算子は"
                                       "正規化しない中心モーメントを返すが、この repo は"
                                       "Hu の正規化不変量を 1 スカラーに合成している")
def test_the_moment_ops_carry_halcons_dimension(name):
    """★開いたままの欠陥を、免除でなく **strict xfail** で持つ。

    直った瞬間に「予期せぬ成功」で落ち、`SCALE_LAW` の更新を要求する。
    免除台帳に畳み込むと、**直ったことに誰も気づけない**。
    """
    want = np.array(SCALE_LAW[name], np.float64)
    got2, _ = _exponents(name)
    assert np.allclose(got2, want, atol=0.05, equal_nan=True), \
        "%s: 実測 %s / HALCON の次元 %s" % (name, np.round(got2, 3), want)


def test_every_region_feature_op_declares_a_scale_law():
    """★完全性 —— 新しい op を足したら、その量の**次元を宣言させる**。

    型 A(探針が 1 枚)への構造的な手当て: 一つずつ試験を書く運用だと、
    足した人が書かなければ何も見ない。表に載っているかを門で見れば、
    「宣言していない op」が存在できなくなる。
    """
    missing = [n for n in REGION_FEATURE_OPS if n not in SCALE_LAW]
    assert not missing, (
        "領域を受けて数を返す op が尺度法則を宣言していない: %s\n"
        "  その量は長さか、面積か、無次元か。tests/%s の SCALE_LAW に足すこと。"
        % (missing, os.path.basename(__file__)))
    extra = [n for n in SCALE_LAW if n not in ops.RT]
    assert not extra, "宣言表に実在しない op がある(消えた op の行が残っている): %s" % extra


def test_the_law_would_catch_a_normalised_feature():
    """★門を壊して確かめる —— 画布で割った偽の量を作り、指数が 1 でなくなることを見る。

    2026-09-26 まで `contlength` は「輪郭長 / (2*(H+W))」を返しており、それは p=0
    だった。ここで確かめたいのは「正規化すると指数が宣言から外れる」ことなので、
    **被検 op を経由せず**に周囲長を自前で数える —— op 自身が壊れていると
    二重に正規化してしまい、探針が弱いのか対象が壊れているのか読めなくなる。
    """
    skm = pytest.importorskip("skimage.measure")
    base = _shape()
    raw, normed = [], []
    for k in (1, 2, 3):
        m = np.kron(base, np.ones((k, k))) if k > 1 else base
        per = float(skm.regionprops((m > 0.5).astype(int))[0].perimeter)
        raw.append(per)
        normed.append(per / (2.0 * (m.shape[0] + m.shape[1])))      # 昔の正規化
    p_raw = np.log(raw[1] / raw[0]) / np.log(2.0)
    p_norm = np.log(normed[1] / normed[0]) / np.log(2.0)
    assert abs(p_raw - 1.0) < 0.05, "画素の周囲長は長さ(p=1)のはず: %.3f" % p_raw
    assert abs(p_norm - 1.0) > 0.5, (
        "正規化しても指数が 1 のまま = この門は正規化を見分けられない(%.3f)" % p_norm)
    assert abs(p_norm) < 0.05, "正規化した値は尺度不変のはず: %.3f" % p_norm
