"""寸法を持つ特徴 op の**単位**と、それを説明する文書の一致(2026-10-15)。

2026-09-26(ecdaf14637)に ``area_center`` ほか 7 op は「画像サイズで割った 0〜1 の値」から
**画素**を返すように変わった(``docs/hardening/dimensional-features-were-normalised.md``)。
挙動の門(``tests/test_pixel_units_2026_09_26.py``)は在ったが、**説明文は正規化のまま
3 週間残った** —— op ノート・Studio のヘルプ・6 言語の要約・族ガイドが全部「正規化した値を
返す」と言い、それを読んで書いた worked example が座標を (H-1) 倍して壊れた
(``examples/example_inner_diameter_mm.py``、2026-10-15)。

ここでは 2 つを固定する:

1. **戻り値の単位**(回帰): 縦横の違う画像・中心から外した領域で、面積は画素数、
   重心は行・列の画素、長さは画素。正規化に戻れば値が桁で変わるので落ちる。
2. **説明の単位**: 7 op の要約(原文と英訳)と族ガイドの行が画素を言い、
   「正規化して返す」と言わないこと。挙動を変えたら説明も変える —— その片方だけの
   変更をここで止める([[feedback_a_fix_leaves_the_twin_surface_open]] の型)。
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (ROOT, os.path.join(ROOT, "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ops  # noqa: E402

#: 9/26 に画素へ変わった 7 op(``elliptic_axis`` は 9/26 の時点で説明も直っていた)。
OPS = ("area_center", "area_center_xld", "contlength", "get_region_thickness",
       "diameter_region", "diameter_xld", "elliptic_axis_xld")

H, W = 120, 300                       # 縦横を違えて行と列の取り違えも見る
R0, R1, C0, C1 = 20, 50, 200, 270     # 30 x 70 の矩形を中心から外して置く


def _rect():
    m = np.zeros((H, W))
    m[R0:R1, C0:C1] = 1.0
    return m


def _v(name, x):
    return np.ravel(np.asarray(ops.RT[name](x, 0.5, 0.5), np.float64))


def _contour():
    return ops.RT["gen_contour_region_xld"](_rect(), 0.5, 0.5)


# --------------------------------------------------------------------------- #
# 1. 戻り値の単位
# --------------------------------------------------------------------------- #
def test_area_center_returns_pixel_count_and_pixel_centroid():
    got = _v("area_center", _rect())
    assert got.shape == (3,)
    assert got[0] == pytest.approx(30 * 70), "面積は画素数(正規化なら 0.058)"
    assert got[1] == pytest.approx((R0 + R1 - 1) / 2.0), "重心の行は画素(正規化なら 0.29)"
    assert got[2] == pytest.approx((C0 + C1 - 1) / 2.0), "重心の列は画素(正規化なら 0.78)"


def test_area_center_of_an_empty_region_is_the_image_centre_in_pixels():
    assert np.allclose(_v("area_center", np.zeros((H, W))), [0.0, (H - 1) / 2.0, (W - 1) / 2.0])


def test_area_center_xld_returns_pixel_area_and_centroid():
    pytest.importorskip("cv2")
    got = _v("area_center_xld", _contour())
    assert got.shape == (3,)
    # 輪郭は画素中心を通るので、囲む面積は (30-1) x (70-1) 付近
    assert 29 * 69 * 0.98 < got[0] < 30 * 70, got
    assert got[1] == pytest.approx((R0 + R1 - 1) / 2.0, abs=0.6)
    assert got[2] == pytest.approx((C0 + C1 - 1) / 2.0, abs=0.6)


def test_lengths_are_pixels():
    reg = _rect()
    assert _v("contlength", reg)[0] == pytest.approx(196.0, abs=1e-6)
    assert _v("get_region_thickness", reg)[0] == pytest.approx(30.0, abs=1e-6)
    assert _v("diameter_region", reg)[0] == pytest.approx(np.hypot(29, 69), abs=0.05)


def test_contour_lengths_and_ellipse_are_pixels():
    pytest.importorskip("cv2")
    con = _contour()
    d = _v("diameter_xld", con)[0]
    assert 70.0 < d < 80.0, "最大弦は画素(正規化なら 0.25)"
    ra, rb, phi = _v("elliptic_axis_xld", con)
    assert ra > rb > 10.0, (ra, rb)
    assert -np.pi / 2 < phi <= np.pi / 2


# --------------------------------------------------------------------------- #
# 2. 説明の単位
# --------------------------------------------------------------------------- #
_JA_BAD = re.compile(r"で正規化|を正規化|正規化済み|正規化した値|正規化重心|面積比 =")
_EN_BAD = re.compile(r"normali[sz]ed (3-component|centroid|value)|normali[sz]e[sd]? (it )?by|area ratio =", re.I)


@pytest.fixture(scope="module")
def summaries():
    import opdocs as OD
    recs = {r["name"]: r for r in OD._records()[0] if r["dim"] == "2d"}
    with io.open(os.path.join(ROOT, "docs", "i18n", "op_summary.json"), encoding="utf-8") as f:
        tr = json.load(f)["summaries"]
    out = {}
    for op in OPS:
        if op not in recs:
            pytest.skip("%s がこの環境のレジストリに無い(optional backend)" % op)
        out[op] = (OD.summary_and_rest(recs[op].get("doc"))[0], (tr.get("2d/" + op) or {}).get("en", ""))
    return out


@pytest.mark.parametrize("op", OPS)
def test_the_summary_says_pixels_not_normalised(summaries, op):
    ja, en = summaries[op]
    assert ("px" in ja or "画素" in ja), "%s の要約に単位(画素)が無い: %s" % (op, ja)
    assert not _JA_BAD.search(ja), "%s の要約が正規化の値と言っている: %s" % (op, ja)
    assert en, "%s の英訳が無い" % op
    assert ("px" in en or "pixel" in en), "%s の英訳に単位が無い: %s" % (op, en)
    assert not _EN_BAD.search(en), "%s の英訳が正規化の値と言っている: %s" % (op, en)


@pytest.mark.parametrize("op", OPS)
def test_the_generated_note_says_pixels(op):
    import glob
    hits = glob.glob(os.path.join(ROOT, "docs", "ops", "2d", "*", op + ".md"))
    hits = [h for h in hits if os.sep + "guides" + os.sep not in h]
    assert len(hits) == 1, (op, hits)
    with io.open(hits[0], encoding="utf-8") as f:
        text = f.read()
    use = text.split("## 使い方", 1)[1].split("\n## ", 1)[0]
    first = use.strip().split("\n\n", 1)[0]
    assert not _JA_BAD.search(first), "%s のノートの使い方が正規化の値と言っている(regen 忘れ?)" % op


def test_the_family_guide_lines_say_pixels():
    with io.open(os.path.join(ROOT, "docs", "ops", "2d", "guides", "gallery2d_features.md"),
                 encoding="utf-8") as f:
        lines = f.read().splitlines()
    seen = set()
    for line in lines:
        for op in OPS:
            if line.startswith("- `%s` —" % op):
                seen.add(op)
                now = line.split("★", 1)[0]          # ★ 以降は来歴(過去形)
                assert not _JA_BAD.search(now) and "正規化(" not in now, (op, line)
                assert ("px" in line or "画素" in line), "%s の行に単位が無い: %s" % (op, line)
    assert seen == set(OPS), "ガイドに行が無い op: %s" % sorted(set(OPS) - seen)
