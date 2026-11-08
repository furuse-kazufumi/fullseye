# -*- coding: utf-8 -*-
"""記事の図の説明を 1 文に切るとき、括弧の中の「。」で切らない(2026-11-09、機材選びの PoC の 5 回目の確認)。

以前の ``_first_sentence`` は最初の「。」で切っていたので、「見本(上から … PE の破片。橙の三角 …)。」のような説明が
括弧の閉じないまま切れ、括弧の後ろの説明(表示倍率など)が記事から消えていた。同じ形の切れ方が記事の 3 か所に
あった。ここでは切り方そのものと、生成済みの記事に括弧の閉じない説明が残っていないことを確かめる。
"""
from __future__ import annotations

import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import gen_wingpoc_gallery as G  # noqa: E402


def test_does_not_cut_inside_parentheses():
    t = "同じ部位の見本(上から線傷、凹み。橙の三角 = 欠陥の位置)。表示は地で割った濃淡。"
    assert G._first_sentence(t) == "同じ部位の見本(上から線傷、凹み。橙の三角 = 欠陥の位置)。"


def test_initial_is_not_a_sentence_end_but_a_unit_is():
    assert G._first_sentence("出典: E. Arbash ら, Polymers, CC BY 4.0。改変: 束ねた。") == \
        "出典: E. Arbash ら, Polymers, CC BY 4.0。"
    assert G._first_sentence("mean -0.010 m, range -0.098 to +0.063 m. Revising the model moves it less.") == \
        "mean -0.010 m, range -0.098 to +0.063 m."


def test_long_text_without_an_end_is_cut_before_the_open_bracket():
    t = "both readings recover the radius to within half a voxel (" + "x" * 400 + ")"
    out = G._first_sentence(t)
    assert out.endswith("…") and "(" not in out


def test_generated_articles_have_no_caption_cut_inside_brackets():
    files = glob.glob(os.path.join(ROOT, "docs", "articles", "exhibits", "wingpoc.*.md"))
    assert len(files) >= 2, files
    bad = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            for ln in fh:
                if ln.startswith("*↑") and not ln.rstrip().endswith("…*"):
                    if sum(ln.count(c) for c in "(（") > sum(ln.count(c) for c in ")）"):
                        bad.append((os.path.basename(f), ln[:80]))
    assert not bad, bad
