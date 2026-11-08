# -*- coding: utf-8 -*-
"""記事の図の説明を 1 文に切るとき、括弧の中で切らない(2026-11-09、機材選びの PoC の 5・6 回目の確認)。

以前の ``_first_sentence`` は最初の「。」で切っていたので、「見本(上から … PE の破片。橙の三角 …)。」のような説明が
括弧の閉じないまま切れ、括弧の後ろの説明(表示倍率など)が記事から消えていた。長さで切るときも括弧の中で切っていた
(「停止線: [(3.3, 'intersection'), …」)。ここでは切り方そのものと、生成済みの記事(展示館の棟と博物館の記事)の
説明の行に括弧の閉じないものが無いことを確かめる。
"""
from __future__ import annotations

import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import gen_wingpoc_gallery as G  # noqa: E402

#: 道具が括弧として数える文字(``_OPEN`` / ``_CLOSE`` と同じ)。
OPEN, CLOSE = G._OPEN, G._CLOSE
#: 検査する説明の行の下限(2026-11-09 の実測 6,402 行。範囲が黙って縮んだら落ちるように)。
MIN_CAPTION_LINES = 5000


def _balanced(t):
    return sum(t.count(c) for c in OPEN) <= sum(t.count(c) for c in CLOSE)


def test_brackets_are_the_tools_brackets():
    assert set("(（[「『") <= set(OPEN) and set(")）]」』") <= set(CLOSE)


def test_does_not_cut_inside_parentheses():
    t = "同じ部位の見本(上から線傷、凹み。橙の三角 = 欠陥の位置)。表示は地で割った濃淡。"
    assert G._first_sentence(t) == "同じ部位の見本(上から線傷、凹み。橙の三角 = 欠陥の位置)。"


def test_initials_and_abbreviations_are_not_sentence_ends_but_a_unit_is():
    assert G._first_sentence("出典: E. Arbash ら, Polymers, CC BY 4.0。改変: 束ねた。") == \
        "出典: E. Arbash ら, Polymers, CC BY 4.0。"
    assert G._first_sentence("mean -0.010 m, range -0.098 to +0.063 m. Revising the model moves it less.") == \
        "mean -0.010 m, range -0.098 to +0.063 m."
    for a in ("e.g.", "et al.", "Fig.", "vs.", "U.S."):
        t = "the blur grows, %s the second case, and stays. More text follows here." % a
        assert G._first_sentence(t) == "the blur grows, %s the second case, and stays." % a, a


def test_length_cut_never_lands_inside_brackets():
    long_list = "停止線: [" + ", ".join("(%d.1, 'intersection')" % k for k in range(40)) + "]"
    out = G._first_sentence(long_list)
    assert out.endswith("…") and _balanced(out), out
    t = "both readings recover the radius to within half a voxel (" + "x" * 400 + ")"
    out = G._first_sentence(t)
    assert out.endswith("…") and _balanced(out), out


def test_generated_articles_have_no_caption_cut_inside_brackets():
    files = (glob.glob(os.path.join(ROOT, "docs", "articles", "exhibits", "wingpoc.*.md"))
             + glob.glob(os.path.join(ROOT, "docs", "articles", "fullseye_poc_museum*_qiita_*.md")))
    assert len(files) >= 4, files
    n, bad = 0, []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            for k, ln in enumerate(fh, 1):
                if ln.startswith("*↑"):
                    n += 1
                    if not _balanced(ln):                       # 「…*」で終わる行も数える
                        bad.append((os.path.basename(f), k, ln[:80]))
    assert n >= MIN_CAPTION_LINES, n
    assert not bad, bad
