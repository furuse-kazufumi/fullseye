# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""**画像ごとの正規化**がノートに書かれ続けていることを検査する。

2026-09-16、`cv_scharr` の第 2 実装が出力スケールごと食い違ったのを追ったら、
``|Sx| + |Sy|`` を**その画像の最大値**で割っていた。同じ署名(出力の最大が常に 1.0
かつ入力の定数倍に不変)を持つ op を測ると **89 本**あり、**そのうち 1 本も
そう書いていなかった**(沈黙 100%)。

これは測る道具にとって致命的になりうる。**画像ごとに割ると値が画像間で比較できない**
—— 同じ強さの特徴でも、その画像で最も強い特徴が何かによって値が変わり、弱い特徴しか
無い画像では雑音が 1.0 まで持ち上がる。書かれていなければ誤用される。

この門は「その注意書きが黙って消えないこと」を守る。
"""
from __future__ import annotations

import json
import os
import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NORM_JSON = os.path.join(ROOT, "docs", "op_normalisation.json")
OPS_DIR = os.path.join(ROOT, "docs", "ops")

#: 2026-09-16 の実測。下振れしたら知らせる床。
MEASURED = 89
FLOOR = 70

_SAYS = re.compile(r"画像ごと|各画像|最大値で割|max で割|画像内の最大|比較可能性")


def _rows():
    if not os.path.exists(NORM_JSON):
        pytest.skip("docs/op_normalisation.json が無い(tools/impl2/norm_probe.py で作る)")
    with open(NORM_JSON, encoding="utf-8") as f:
        return json.load(f)


def _note(op):
    """**2-D を先に見て、列挙順は整列する。** `highpass` / `lowpass` / `fill_holes` /
    `gaussians_to_voxel` は次元をまたいで名前が衝突しており、素の ``os.walk`` は
    Windows(整列)と Linux(ハッシュ順)で違うほうを掴む —— 実際 2026-09-16 に
    この探し方の門が **CI でだけ落ちた**(手元は緑)。台帳はすべて 2-D の op。
    """
    for base in (os.path.join(OPS_DIR, "2d"), OPS_DIR):
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames.sort()
            if f"{op}.md" in sorted(filenames):
                with open(os.path.join(dirpath, f"{op}.md"), encoding="utf-8") as f:
                    return f.read()
    return None


def test_the_normalisation_ledger_is_not_empty():
    """**空の台帳は全部を素通りさせる。** 件数そのものを数える。"""
    hits = [r for r in _rows() if r.get("per_image_normalised")]
    assert len(hits) >= FLOOR, (
        f"画像ごとの正規化が {len(hits)} 本しか見つかっていない(実測 {MEASURED} 本)。"
        "測定が壊れたか台帳が古い")


def test_per_image_normalised_ops_say_so():
    """値が画像間で比較できないことが、ノートに書かれていること。"""
    missing = []
    for r in _rows():
        if not r.get("per_image_normalised"):
            continue
        t = _note(r["op"])
        if t is None:
            missing.append(f"{r['op']}: ノートが無い")
        elif not _SAYS.search(t):
            missing.append(f"{r['op']}: 画像ごとの正規化に触れていない")
    assert not missing, (
        "画像ごとの正規化の注意書きがノートから消えている:\n" + "\n".join(missing[:20]))


def test_the_signature_needs_both_halves():
    """**片方の署名だけで「画像ごと」と言っていないこと。**

    出力の最大が 1.0 なだけなら飽和で説明が付くし、スケール不変なだけなら二値化でも
    起きる。両方が揃って初めて「その画像の最大で割っている」形になる。
    """
    for r in _rows():
        if r.get("per_image_normalised"):
            assert r.get("out_max_always_one") and r.get("scale_invariant"), \
                f"{r['op']}: 署名が片方しか揃っていないのに画像ごとと判定している"
