# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実測した**何も写っていないフレームでの答え**が、ノートに載り続けていることを検査する。

一様な画像は検査の現場では日常的に来る —— 照明が飛んだ、遮られた、被写体が無い。
そこで op が何を返すかは書かれていないことが多く、実測すると**族の中で割れていた**:
`auto_threshold` は「全部背景」、`cv_otsu` は「全部前景」を返す(どちらも不具合では
なく、cv2 が定数画像にしきい値 0.0 を返すのを忠実に再現している —— 一次情報で確認済み)。

2026-09-16 に `tools/impl2/blank_probe.py` で 461 本(image->image 378 +
image->region 83)を測り、一定の二値の答えを返す 168 本のうち **166 本(99%)が
黙っていた**。**全部前景になる 20 本**は「空フレーム = 欠陥 100%」と読まれるので、
書かれていないと必ず誤用される。

**この門が守るのは「差し込みが黙って剥がれないこと」**。生成器の分岐が消えても、
台帳が古くなっても、ノートは前と同じ見た目のまま**空フレームの断りだけが消える**。
"""
from __future__ import annotations

import json
import os
import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BLANK_JSON = os.path.join(ROOT, "docs", "op_blank_frame.json")
OPS_DIR = os.path.join(ROOT, "docs", "ops")

#: 2026-09-16 の実測値。**下振れしたら知らせる**ための床であって、上げるのは自由。
MEASURED = 168
FLOOR = 140
#: 空フレームが「全部前景」になる op(いちばん危ない側)。
MEASURED_FOREGROUND = 20
FOREGROUND_FLOOR = 15

_MENTIONS_BLANK = re.compile(r"一様な画像|定数画像|何も写っていない|空フレーム|全体が平坦")


def _rows():
    if not os.path.exists(BLANK_JSON):
        pytest.skip("空フレームの台帳が無い(tools/impl2/blank_probe.py で作る)")
    with open(BLANK_JSON, encoding="utf-8") as f:
        return json.load(f)


def _binary_verdicts():
    return [r for r in _rows()
            if r.get("constant_in_c") and r.get("value") in (0.0, 1.0)]


def _note_path(op: str) -> str | None:
    """op のノートを探す。**2-D を先に見て、列挙順は必ず整列する。**

    2026-09-16、この門が **CI でだけ落ちた**(手元は緑)。`highpass` / `lowpass` は
    `docs/ops/2d/frequency/` と `docs/ops/oned/signal/` の **両方に同名のノートがある**
    (別の op だが名前が衝突している)。素の ``os.walk`` は ``os.scandir`` の順で歩くので、
    Windows(整列される)では 2-D 側を、Linux(ハッシュ順)では 1-D 側を掴んでいた。
    ここで見る台帳はすべて 2-D の op なので、2-D を優先する。整列するのは、
    **同じ木に対して同じ答えを返させる**ため —— 順序に依存する門は、落ちる環境を
    選ぶぶん、落ちないほうが嘘になる。
    衝突しているのは `highpass` / `lowpass` / `fill_holes` / `gaussians_to_voxel` の 4 件。
    """
    for base in (os.path.join(OPS_DIR, "2d"), OPS_DIR):
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames.sort()
            if f"{op}.md" in sorted(filenames):
                return os.path.join(dirpath, f"{op}.md")
    return None


def test_the_blank_frame_ledger_is_not_empty():
    """**空の台帳は全部を素通りさせる。** 件数そのものを別に数える。"""
    rows = _binary_verdicts()
    assert len(rows) >= FLOOR, (
        f"空フレームの答えが確定している op が {len(rows)} 本しかない"
        f"(2026-09-16 の実測は {MEASURED} 本)。測定が壊れたか台帳が古い")


def test_the_dangerous_side_is_still_counted():
    """**「全部前景」になる側を別に数える。** ここが減るのは、測れなくなったか、
    誰かが挙動を変えたかのどちらかで、どちらも知りたい。"""
    fg = [r for r in _binary_verdicts() if r["value"] == 1.0]
    assert len(fg) >= FOREGROUND_FLOOR, (
        f"空フレームが全部前景になる op が {len(fg)} 本しかない"
        f"(2026-09-16 の実測は {MEASURED_FOREGROUND} 本)")


def test_every_measured_op_says_what_a_blank_frame_gives():
    """実測した答えが**ノートに載っている**こと。生成器の差し込みが消えたら落ちる。"""
    missing = []
    for r in _binary_verdicts():
        p = _note_path(r["op"])
        if p is None:
            missing.append(f"{r['op']}: ノートが無い")
            continue
        if not _MENTIONS_BLANK.search(open(p, encoding="utf-8").read()):
            missing.append(f"{r['op']}: ノートが空フレームの扱いを書いていない")
    assert not missing, (
        "実測した空フレームの答えがノートから消えている(差し込みが効いていない):\n"
        + "\n".join(missing[:20]))


def test_ops_that_flip_are_not_given_a_single_answer():
    """**明るさで答えが変わる op に、一つの答えを書かない。** 嘘になる。

    跳ぶ op は `constant_in_c` が立たないので台帳から拾われない —— その不変条件を
    ここで固定する。
    """
    for r in _rows():
        if r.get("jumps"):
            assert not r.get("constant_in_c"), (
                f"{r['op']}: 跳ぶのに「c に依らず一定」と記録されている(台帳が壊れている)")


def test_the_ledger_only_names_ops_that_exist():
    """台帳が古くなって、もう無い op を指していないこと。"""
    idx_path = os.path.join(ROOT, "docs", "OP_INDEX.json")
    if not os.path.exists(idx_path):
        pytest.skip("docs/OP_INDEX.json が無い")
    with open(idx_path, encoding="utf-8") as f:
        known = {o["name"] for o in json.load(f)["ops"]}
    gone = [r["op"] for r in _rows() if r["op"] not in known]
    assert not gone, f"台帳が存在しない op を指している(古い): {gone[:10]}"
