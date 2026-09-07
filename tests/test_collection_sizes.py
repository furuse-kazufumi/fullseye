# -*- coding: utf-8 -*-
"""表・ファイル群の大きさを 1 か所の台帳で守る(床が古くなるのを止める)。

## なぜ要るか(2026-09-08)

各所の門が「昔の小さい床」を持ったまま置き去りになっていた。実測した差:

======================  ======  ======  =======
対象                      床      実測    倍率
======================  ======  ======  =======
``examples2d.EXAMPLES``     57     173     3.0x
``examples/poc_*.py``       31      98     3.2x
``ops3d.OPS3D``             80     356     4.5x
examples3d ギャラリー       20     117     5.8x
======================  ======  ======  =======

``assert len(_poc_paths()) >= 31`` は、**PoC が 98 本から 31 本に消えても緑**という
意味である。同じ日に見つけた 2 つ ——「探針の門が 17 sort 中 4 つにしか入力を作らず
到達率 76 %」「図を書けなかった記録を溜めるだけで誰も読まない」—— と同じ型で、
**記録も門も在るのに、判定に使う数が現実から取り残されている**。

## 何を守るか

1. 実測が台帳を**下回らない**(消えたら落ちる)。
2. 台帳が実測から**離れすぎない**(増えたら台帳を更新させる)。放っておくと
   また床が古くなるので、増加も摩擦にする。

台帳 = ``docs/COLLECTION_SIZES.json``。落ちたら**台帳を直す**のであって、
この門を緩めるのではない(減らしたのが意図的なら、その回の commit で説明する)。

op レジストリの本数はここに入れない —— Linux CI には torch/kornia が無く
正当に少ないため。そちらは ``tests/test_docs_index_numbers.py`` が満杯の環境で
だけ厳密一致を見る。
"""
from __future__ import annotations

import glob
import json
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
LEDGER = os.path.join(ROOT, "docs", "COLLECTION_SIZES.json")

#: 台帳がこの倍率を超えて古くなったら落とす(増えたことを記録に残させる)。
GROWTH_TOLERANCE = 1.25


def _ledger():
    with open(LEDGER, encoding="utf-8") as fh:
        return json.load(fh)


def _measure():
    """環境に依らない大きさだけを測る。"""
    import comm
    import examples2d
    import imgio
    import ops3d
    import recipes

    # ★OPS3D は {op 名: メタデータ dict} の平坦な表。`sum(len(v) for v in values())`
    #   と数えると**各 op のメタデータのキー数の総和**(2,492)になり、意味の無い
    #   数字を台帳に刻むところだった(2026-09-08、書く前に構造を見て気づいた)。
    n_o3 = len(ops3d.OPS3D)

    import examples3d
    gal = getattr(examples3d, "EXAMPLES", None) or getattr(examples3d, "META", [])

    with open(os.path.join(ROOT, "docs", "articles", "exhibits", "poc_captions.json"),
              encoding="utf-8") as fh:
        exhibits = len(json.load(fh)["exhibits"])

    return {
        "examples2d.EXAMPLES": len(examples2d.EXAMPLES),
        "examples_poc_files": len(glob.glob(os.path.join(ROOT, "examples", "poc_*.py"))),
        "ops3d.OPS3D": n_o3,
        "examples3d.gallery": len(gal),
        "recipes.RECIPES": len(recipes.RECIPES),
        "imgio.COLORMAPS": len(imgio.COLORMAPS),
        "comm.protocols": len(comm.protocols()),
        "poc_exhibits": exhibits,
    }


@pytest.fixture(scope="module")
def sizes():
    return _measure()


def test_ledger_lists_exactly_what_is_measured(sizes):
    led = _ledger()["sizes"]
    assert set(led) == set(sizes), {
        "台帳にあって測っていない": sorted(set(led) - set(sizes)),
        "測っているのに台帳に無い": sorted(set(sizes) - set(led)),
    }


@pytest.mark.parametrize("key", sorted(_ledger()["sizes"]))
def test_nothing_silently_disappeared(sizes, key):
    want = _ledger()["sizes"][key]
    got = sizes[key]
    assert got >= want, (
        f"{key} が {want} → {got} に減った。意図した削除なら "
        f"docs/COLLECTION_SIZES.json を直し、その回の commit で理由を書くこと"
        f"(門を緩めるのではない)")


@pytest.mark.parametrize("key", sorted(_ledger()["sizes"]))
def test_the_ledger_has_not_gone_stale(sizes, key):
    want = _ledger()["sizes"][key]
    got = sizes[key]
    assert got <= want * GROWTH_TOLERANCE, (
        f"{key} が {want} → {got}({got / want:.2f} 倍)に育った。"
        f"docs/COLLECTION_SIZES.json を {got} に更新すること —— "
        f"床を古いままにすると「消えても気づかない」に戻る"
        f"(2026-09-08 に PoC の床が 31 のまま実測 98 になっていた)")
