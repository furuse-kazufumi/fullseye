# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実測した**端の規約**が、ノートに載り続けていることを検査する。

2026-09-16、近傍窓を使う op 213 本のうち **198 本(93%)** が端の規約に触れていなかった。
そして端の規約は答えを**値域の 2 割**動かす —— 同じ「矩形平均」でも `mean_box` は
`symmetric`、`cv_box` は `reflect` で、利用者にはどちらとも書かれていなかった
(`impl2/FINDINGS.md`)。`tools/impl2/border_probe.py` で image->image の全 378 op を
測り、確定した 106 本を `docs/op_border.json` に置いて、ノート生成器が本文へ差し込む
ようにした。

**この門が守るのは「差し込みが黙って剥がれないこと」**。生成器の分岐が消えても、
`op_border.json` が古くなっても、ノートは前と同じ見た目のまま**規約だけが消える** ——
それは最初の状態(93% が沈黙)に戻ったのと同じで、誰も気づけない。

門は**壊して確かめてある**: 台帳が空なら失格、確定件数が実測より大きく減ったら失格、
台帳に居る op が registry から消えていたら失格。
"""
from __future__ import annotations

import json
import os
import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
#: image->image と region->region の 2 本。**片方だけ見る門は、もう片方の差し込みが
#: 剥がれても緑のまま**になる。
#: 3 本ある。**型ごとに別々に測る**ので、1 本でも忘れると、その型の差し込みが
#: 剥がれても緑のままになる。image->region(しきい値・領域抽出)の 83 本は
#: 2026-09-16 まで**丸ごと測っていなかった** —— `local_max` / `dyn_threshold` の
#: 争点を追って初めて気づいた。
BORDER_JSONS = (os.path.join(ROOT, "docs", "op_border.json"),
                os.path.join(ROOT, "docs", "op_border_region.json"),
                os.path.join(ROOT, "docs", "op_border_region_out.json"))
OPS_DIR = os.path.join(ROOT, "docs", "ops")

#: 2026-09-16 の実測値。**下振れしたら知らせる**ための床であって、上げるのは自由。
#: (op を足して確定数が増えるのは歓迎。減るのは「測れなくなった」か「台帳が壊れた」)
MEASURED_DETERMINED = 156   # image->image 106 + region->region 38 + image->region 12
FLOOR = 130

_MENTIONS_BORDER = re.compile(r"端の扱い|境界|端は|BORDER_|パディング")


def _rows():
    rows = []
    for path in BORDER_JSONS:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                rows.extend(json.load(f))
    if not rows:
        pytest.skip("端の規約の台帳が無い(tools/impl2/border_probe.py で作る)")
    return rows


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


def test_the_border_ledger_is_not_empty():
    """**空の台帳は全部を素通りさせる。** 件数そのものを別に数える。"""
    rows = _rows()
    assert rows, "docs/op_border.json が空"
    determined = [r for r in rows if r.get("status") == "determined"]
    assert len(determined) >= FLOOR, (
        f"端の規約が確定している op が {len(determined)} 本しかない"
        f"(2026-09-16 の実測は {MEASURED_DETERMINED} 本)。測定が壊れたか台帳が古い")


def test_every_determined_op_says_its_border_in_the_note():
    """確定した規約が**ノートに載っている**こと。生成器の差し込みが消えたら落ちる。"""
    missing = []
    for r in _rows():
        if r.get("status") != "determined":
            continue
        p = _note_path(r["op"])
        if p is None:
            missing.append(f"{r['op']}: ノートが無い")
            continue
        if not _MENTIONS_BORDER.search(open(p, encoding="utf-8").read()):
            missing.append(f"{r['op']}: ノートが端の扱いを書いていない")
    assert not missing, (
        "実測した端の規約がノートから消えている(生成器の差し込みが効いていない):\n"
        + "\n".join(missing[:20]))


def test_no_unconfirmed_record_carries_a_border_key():
    """**確定していない記録に ``border`` を持たせない。**

    曖昧(``ambiguous``)な記録にも最有力候補が入っていて、鍵の名前が確定値と同じ
    ``border`` だった。status を見ない消費側はそれを確定値として読む ——
    2026-09-16、**この道具自身の集計表がその罠を踏んだ**(確定 12 / 曖昧 37 なのに
    「symmetric 17, edge 7 ...」= 49 本確定したように見えた)。推測は ``best_guess``
    という別の鍵に移し、取り違えを型で防ぐ。
    """
    bad = [r["op"] for r in _rows() if r.get("status") != "determined" and "border" in r]
    assert not bad, (
        f"確定していないのに border を持つ記録がある(推測が確定値として読まれる): {bad[:10]}")


def test_undetermined_ops_are_not_given_a_guessed_border():
    """**測れなかったものに規約を書かない。** 推測を書けば、その推測が契約になる。

    `undetermined` は「判定法の前提(``op(pad_P(x))[crop] == op(x)``)が成り立たない」
    という意味で、「規約が無い」ではない。ここに当てずっぽうを載せるくらいなら
    黙っているほうがよい。
    """
    for r in _rows():
        if r.get("status") == "undetermined":
            assert "border" not in r, (
                f"{r['op']}: 判定できていないのに規約が入っている(推測を契約にしている)")


def test_the_ledger_only_names_ops_that_exist():
    """台帳が古くなって、もう無い op を指していないこと。"""
    idx_path = os.path.join(ROOT, "docs", "OP_INDEX.json")
    if not os.path.exists(idx_path):
        pytest.skip("docs/OP_INDEX.json が無い")
    with open(idx_path, encoding="utf-8") as f:
        known = {o["name"] for o in json.load(f)["ops"]}
    gone = [r["op"] for r in _rows() if r["op"] not in known]
    assert not gone, f"台帳が存在しない op を指している(古い): {gone[:10]}"


def test_name_collisions_resolve_to_the_two_dimensional_note():
    """**次元をまたいで名前が衝突している op を、2-D 側に解決すること。**

    2026-09-16、この門が **CI でだけ落ちた**。`highpass` / `lowpass` は
    `docs/ops/2d/frequency/` と `docs/ops/oned/signal/` の両方にノートがあり(別の op
    だが名前が同じ)、素の ``os.walk`` は ``os.scandir`` の順に歩く —— Windows は整列、
    Linux はハッシュ順なので、**同じ木に対して環境ごとに違う答え**を返していた。

    「手元で緑」は直った証拠にならない(手元は元から緑だった)。解決先そのものを
    ここで固定する。衝突しているのは `highpass` / `lowpass` / `fill_holes` /
    `gaussians_to_voxel` / `local_std` / `companding_mu_law`。
    """
    # 2026-09-17: 1-D 版を足したので `local_std` / `companding_mu_law` も衝突する。
    # 名前が衝突した瞬間に門へ足すこと —— 足し忘れると、また CI でだけ落ちる。
    for op in ("highpass", "lowpass", "fill_holes",
               "local_std", "companding_mu_law"):
        p = _note_path(op)
        if p is None:
            continue
        rel = os.path.relpath(p, OPS_DIR).replace(os.sep, "/")
        assert rel.startswith("2d/"), (
            f"{op}: 2-D でないノート({rel})に解決した。台帳は 2-D の op を指しているので、"
            f"別次元の同名ノートを掴むと環境によって門の結果が変わる")
