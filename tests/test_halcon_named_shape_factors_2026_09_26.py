# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""HALCON と同名の形状係数は、HALCON の式で答えること(2026-09-26)。

規準(ユーザー指示): **op 名が HALCON と同じなら HALCON に合わせる。** 名前を
借りておいて別の量を返すと、HALCON のレシピを移してきた人が同じしきい値で違う
判定を得る —— しかも例外は出ない。

一次情報(MVTec のオペレータ文書、2026-09-26 に確認):

| op | 定義 |
|---|---|
| `circularity` | ``min(1, F/(π·max²))``、max = 重心から全輪郭画素までの最大距離 |
| `compactness` | ``max(1, L²/(4π·F))``、L = 輪郭長 |
| `roundness` | ``1 - σ/μ``、μ・σ = 重心→輪郭距離の平均と標準偏差 |
| `rectangularity` | 同じ 1 次・2 次モーメントを持つ矩形との差を矩形面積で正規化 |
| `convexity` | ``F / F_convex`` |

★この門は**式を試験側で独立に書き直して**比べる。実装を呼んで実装と比べても
何も守れない。
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

skimage_measure = pytest.importorskip("skimage.measure")
ndi = pytest.importorskip("scipy.ndimage")


# --------------------------------------------------------------------------- #
# 形
# --------------------------------------------------------------------------- #
def _disc(r, n=160):
    yy, xx = np.mgrid[:n, :n]
    c = n / 2.0
    return (((yy - c) ** 2 + (xx - c) ** 2) <= r * r).astype(np.float64)


def _rect(h, w, n=160, rot=0.0):
    reg = np.zeros((n, n))
    reg[n // 2 - h // 2:n // 2 + h // 2, n // 2 - w // 2:n // 2 + w // 2] = 1.0
    if rot:
        reg = (ndi.rotate(reg, rot, reshape=False, order=1) > 0.5).astype(np.float64)
    return reg


def _ell():
    reg = np.zeros((160, 160))
    reg[50:110, 50:70] = 1.0
    reg[90:110, 50:110] = 1.0
    return reg


SHAPES = {
    "disc": _disc(24),
    "square": _rect(40, 40),
    "rect": _rect(16, 64),
    "rect_rot30": _rect(16, 64, rot=30),
    "thin": _rect(4, 80),
    "L": _ell(),
}


# --------------------------------------------------------------------------- #
# HALCON の式(試験側の独立実装)
# --------------------------------------------------------------------------- #
def _contour_distances(reg):
    b = reg > 0.5
    st = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool)
    border = b & ~ndi.binary_erosion(b, st)
    ys, xs = np.nonzero(b)
    by, bx = np.nonzero(border)
    return np.hypot(by - ys.mean(), bx - xs.mean())


def halcon_circularity(reg):
    d = _contour_distances(reg)
    return min(1.0, float((reg > 0.5).sum()) / (np.pi * float(d.max()) ** 2))


def halcon_compactness(reg):
    pr = skimage_measure.regionprops((reg > 0.5).astype(int))[0]
    return max(1.0, pr.perimeter ** 2 / (4 * np.pi * float(pr.area)))


def halcon_roundness(reg):
    d = _contour_distances(reg)
    return min(1.0, max(0.0, 1.0 - float(d.std()) / float(d.mean())))


def halcon_convexity(reg):
    pr = skimage_measure.regionprops((reg > 0.5).astype(int))[0]
    return float(pr.area) / max(pr.area_convex, 1)


FORMULA = {"circularity": halcon_circularity, "compactness": halcon_compactness,
           "roundness": halcon_roundness, "convexity": halcon_convexity}


def _feat(name, reg):
    return float(np.ravel(np.asarray(ops.RT[name](reg.copy(), 0.5, 0.5), np.float64))[0])


# --------------------------------------------------------------------------- #
# 本体
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("shape", sorted(SHAPES))
@pytest.mark.parametrize("name", sorted(FORMULA))
def test_the_op_returns_the_halcon_quantity(name, shape):
    got, want = _feat(name, SHAPES[shape]), FORMULA[name](SHAPES[shape])
    assert abs(got - want) < 1e-9, (
        "%s(%s): %.6f だが HALCON の式は %.6f —— 名前を借りて別の量を返している"
        % (name, shape, got, want))


def test_circularity_is_one_for_a_circle_and_two_over_pi_for_a_square():
    """★閉形式で押さえる。円 -> 1、正方形 -> 2/π(漸近)。"""
    assert abs(_feat("circularity", _disc(48)) - 1.0) < 0.01
    big = _rect(120, 120, n=160)
    assert abs(_feat("circularity", big) - 2.0 / np.pi) < 0.02


def test_compactness_is_one_for_a_circle():
    assert abs(_feat("compactness", _disc(48)) - 1.0) < 0.12


def test_rectangularity_is_one_for_rectangles_whatever_the_angle():
    """★以前はここが壊れていた —— **同じ長方形を回すだけで 1.000 が 0.359** に。"""
    for rot in (0, 15, 30, 45, 60, 75):
        got = _feat("rectangularity", _rect(16, 64, rot=rot))
        assert got > 0.90, "%d 度で矩形度が %.3f(矩形なら 1 のはず)" % (rot, got)


def test_rectangularity_is_one_for_a_square():
    """★2 次モーメントで向きが決まらない形。HALCON は「矩形なら 1」と言う。

    向きの任意性をそのままにすると、モーメント矩形が 45 度回って当たり 0.651 に
    なる(実測)。定義は向きを決めないので、重なりが最大の向きを選んでいる。
    """
    assert _feat("rectangularity", _rect(40, 40)) > 0.95


def test_rectangularity_drops_for_a_shape_that_is_not_a_rectangle():
    """上げ底でないこと —— L 字や円では 1 にならない。"""
    assert _feat("rectangularity", _ell()) < 0.7
    assert _feat("rectangularity", _disc(24)) < 0.9


# --------------------------------------------------------------------------- #
# HALCON が 3 値を返す演算子(eccentricity)
# --------------------------------------------------------------------------- #
def halcon_eccentricity(reg):
    """``(Anisometry, Bulkiness, StructureFactor)``(Ra/Rb = 同モーメント楕円の半径)。"""
    pr = skimage_measure.regionprops((reg > 0.5).astype(int))[0]
    ra, rb = pr.axis_major_length / 2.0, max(pr.axis_minor_length / 2.0, 1e-9)
    area = float(pr.area)
    aniso = ra / rb
    bulk = np.pi * ra * rb / area
    return np.array([aniso, bulk, aniso * bulk - 1.0])


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_eccentricity_returns_the_three_halcon_values(shape):
    got = np.asarray(ops.RT["eccentricity"](SHAPES[shape].copy(), 0.5, 0.5), np.float64)
    want = halcon_eccentricity(SHAPES[shape])
    assert got.shape == (3,), "3 成分でない: %s" % (got.shape,)
    assert np.abs(got - want).max() < 1e-9, (
        "%s: %s だが HALCON は %s" % (shape, np.round(got, 4), np.round(want, 4)))


def test_eccentricity_is_one_one_zero_for_a_circle():
    """★閉形式: 円なら (1, 1, 0)。旧実装は 0.0 という 3 つのどれでもない値だった。"""
    got = np.asarray(ops.RT["eccentricity"](_disc(48), 0.5, 0.5), np.float64)
    assert abs(got[0] - 1.0) < 0.01 and abs(got[1] - 1.0) < 0.01 and abs(got[2]) < 0.02


def test_eccentricity_keeps_three_components_when_the_region_is_empty():
    """★成分の数が入力で変わらないこと(受け取る側の形が壊れる)。"""
    got = np.asarray(ops.RT["eccentricity"](np.zeros((32, 32)), 0.5, 0.5), np.float64)
    assert got.shape == (3,) and got[0] == 1.0


def test_the_old_scalar_eccentricity_is_what_the_gate_catches():
    """★旧式(skimage の離心率)は HALCON の 3 値のどれでもない。"""
    reg = SHAPES["thin"]
    pr = skimage_measure.regionprops((reg > 0.5).astype(int))[0]
    old = float(pr.eccentricity)
    want = halcon_eccentricity(reg)
    assert np.abs(want - old).min() > 0.01, \
        "旧式が 3 値のどれかに近い = 探針が弱い(細長い形で差が出るはず)"


def test_the_contour_eccentricity_uses_moments_not_a_point_fit():
    """★輪郭版は**囲まれた面積のモーメント**から Ra/Rb を出すこと。

    `cv2.fitEllipse` は輪郭「点」への最小二乗当てはめで、細長い形では大きく外れる
    (4x80 の棒で Anisometry 39.1 対 20.65)。HALCON の定義は前者。
    """
    if "eccentricity_xld" not in ops.RT or "gen_contour_region_xld" not in ops.RT:
        pytest.skip("輪郭側がこの版に無い")
    reg = SHAPES["thin"]
    con = ops.RT["gen_contour_region_xld"](reg.copy(), 0.5, 0.5)
    got = np.asarray(ops.RT["eccentricity_xld"](con, 0.5, 0.5), np.float64)
    want = halcon_eccentricity(reg)
    assert got.shape == (3,)
    rel = abs(got[0] - want[0]) / want[0]
    assert rel < 0.10, "Anisometry が領域版と %.1f%% 違う(点への当てはめに戻っている?)" % (100 * rel)


# --------------------------------------------------------------------------- #
# 壊して確かめる
# --------------------------------------------------------------------------- #
def test_the_old_isoperimetric_formula_is_what_the_gate_catches():
    """★直す前の等周比に戻すと、上の門が落ちること。"""
    reg = SHAPES["square"]
    pr = skimage_measure.regionprops((reg > 0.5).astype(int))[0]
    old = min(1.0, 4 * np.pi * pr.area / (pr.perimeter ** 2))
    assert abs(old - halcon_circularity(reg)) > 0.1, \
        "旧式と HALCON の式が近すぎる = 探針が弱い(正方形で差が出るはず)"


def test_the_old_axis_aligned_extent_is_what_the_gate_catches():
    reg = _rect(16, 64, rot=30)
    pr = skimage_measure.regionprops((reg > 0.5).astype(int))[0]
    assert pr.extent < 0.5, "回転した矩形で extent が落ちない = 探針が弱い"
    assert _feat("rectangularity", reg) > 0.9


# --------------------------------------------------------------------------- #
# 輪郭版(_xld)は領域版と同じ量を答えること
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("pair", [("circularity", "circularity_xld"),
                                  ("compactness", "compactness_xld"),
                                  ("rectangularity", "rectangularity_xld")])
def test_the_contour_twin_answers_the_same_question(pair):
    """★直した op の双子を見落とすと穴が半分残る。

    輪郭版は折れ線で測るので値は完全一致しないが、**同じ量**でなければならない。
    """
    reg_name, xld_name = pair
    if xld_name not in ops.RT or "gen_contour_region_xld" not in ops.RT:
        pytest.skip("輪郭側がこの版に無い")
    for key in ("disc", "rect", "thin", "L"):
        reg = SHAPES[key]
        con = ops.RT["gen_contour_region_xld"](reg.copy(), 0.5, 0.5)
        a = _feat(reg_name, reg)
        b = float(np.ravel(np.asarray(ops.RT[xld_name](con, 0.5, 0.5), np.float64))[0])
        rel = abs(a - b) / max(abs(a), 1e-9)
        assert rel < 0.15, "%s と %s が %s で %.4f 対 %.4f" % (reg_name, xld_name, key, a, b)


def test_the_contour_compactness_no_longer_saturates():
    """★領域版と同じ ``/10`` + 頭打ちが輪郭版にも在った。"""
    if "compactness_xld" not in ops.RT:
        pytest.skip("compactness_xld がこの版に無い")
    vals = []
    for length in (40, 80, 140):
        con = ops.RT["gen_contour_region_xld"](_rect(2, length, 200), 0.5, 0.5)
        vals.append(float(np.ravel(np.asarray(
            ops.RT["compactness_xld"](con, 0.5, 0.5), np.float64))[0]))
    assert vals[0] < vals[1] < vals[2] and vals[-1] > 10.0, \
        "輪郭版が頭打ちしている: %s" % vals


# --------------------------------------------------------------------------- #
# まだ合わせていないもの(理由つきで名指しし、腐らせない)
# --------------------------------------------------------------------------- #
#: ★同名なのに HALCON と別の量を返すもの。**直す予定のものだけ**をここに書き、
#: 「本当にまだ違う」ことを下の試験が確かめる(直ったら台帳から外させる)。
_NOT_YET_HALCON: dict = {
    # ★2026-09-26: `elliptic_axis` と `diameter_region` はここから外れた —— ユーザー
    # 判断で「寸法を持つ特徴も HALCON と同じ**画素値**で返す」と決まり、量もスケールも
    # 合わせたため(docs/KNOWN_ISSUES.md §51 は解決)。台帳を空にしても門は残す:
    # 次に「まだ合わせていないもの」が出たとき、ここに名指しで載せる場所が要る。
}


def test_the_not_yet_ledger_names_ops_that_really_still_differ():
    """★免除台帳が腐らないこと —— 直ったら外させる。

    2026-09-26 に `elliptic_axis` / `diameter_region` が外れて空になった。空の
    台帳はこの試験を素通りするので、**空であること自体**も確かめる(「うっかり
    全部消した」と「本当に全部直した」を区別するため)。
    """
    assert isinstance(_NOT_YET_HALCON, dict)
    if not _NOT_YET_HALCON:
        same = {o.name for o in ops._BY_NAME.values() if o.halcon == o.name}
        assert "elliptic_axis" in same and "diameter_region" in same, \
            "台帳が空なのに、対象の op が消えている"
        return
    for name in _NOT_YET_HALCON:
        assert name in ops.RT, "免除しているのに op が無い: %r" % name

def test_every_same_named_shape_factor_is_either_checked_or_named():
    """★**配布物の側から数える。** 同名の形状係数が増えたら、この門か台帳に載る。"""
    family = {"circularity", "compactness", "roundness", "rectangularity", "convexity",
              "circularity_xld", "compactness_xld", "rectangularity_xld",
              "convexity_xld", "eccentricity", "eccentricity_xld",
              "elliptic_axis", "diameter_region"}
    same_named = {o.name for o in ops._BY_NAME.values()
                  if o.halcon == o.name and o.name in family}
    # rectangularity は閉形式の参照式ではなく、性質(どの角度でも矩形なら 1 /
    # 矩形でない形では落ちる)で専用に押さえている。
    checked = set(FORMULA) | {"rectangularity", "circularity_xld", "compactness_xld",
                              "rectangularity_xld", "convexity_xld",
                              "eccentricity", "eccentricity_xld",
                              # 2026-09-26: 画素値化で HALCON の量に揃えた
                              # (tests/test_pixel_units_2026_09_26.py が採点する)
                              "elliptic_axis", "diameter_region"}
    unknown = same_named - checked - set(_NOT_YET_HALCON)
    assert not unknown, (
        "同名なのに照合も免除もされていない形状係数: %s —— 門に足すか、理由つきで "
        "_NOT_YET_HALCON に名指しすること" % sorted(unknown))
