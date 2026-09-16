# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実測した**内部 8 bit 量子化**が、ノートに載り続けていることを検査する。

2026-09-16、codex に書かせた第 2 実装が `cv_median` で食い違い、差が**厳密に 1/255**
だった。追うと Fullseye が内部で uint8 に落としていた —— ノートには書かれていない。
全 image op 378 本を `tools/impl2/quant_probe.py` で測ると **29 本**が該当し、そのうち
**21 本(72%)が黙っていた**。

**なぜこれを黙ってはいけないか。** 利用者は float64 の画像を渡すので、渡した精度が
そのまま出てくると思う。実際には 255 段に潰れるので:

* 16-bit カメラの階調(約 1.5e-5)は 1/255 = 約 3.9e-3 に丸められ、**意味を失う**
* 1/255 より小さい差しか無い 2 枚は**同じ答えを返す**(微小な欠陥が消える)
* 出力は k/255 の格子にしか乗らないので、**微分・回帰に渡すと段差が出る**

Fullseye は「測る道具」を名乗っている。精度が黙って目減りするのは、値が画像間で
比較できない([[tests/test_op_normalisation_documented.py]])のと同じ種類の落とし穴で、
書かれていなければ必ず誤用される。

**この門が守るのは「差し込みが黙って剥がれないこと」**。生成器の分岐が消えても、
台帳が古くなっても、ノートは前と同じ見た目のまま**精度の断りだけが消える**。

門は壊して確かめてある: 台帳が空なら失格、該当件数が実測より大きく減ったら失格、
台帳に居る op が registry から消えていたら失格、判定の署名が片方しか無いのに
「量子化する」と書いてあったら失格。
"""
from __future__ import annotations

import json
import os
import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
QUANT_JSON = os.path.join(ROOT, "docs", "op_quantisation.json")
OPS_DIR = os.path.join(ROOT, "docs", "ops")

#: 2026-09-16 の実測値。**下振れしたら知らせる**ための床であって、上げるのは自由。
MEASURED = 29
FLOOR = 22

_MENTIONS_8BIT = re.compile(r"uint8|8 ?bit|8-bit|256 段|1/255|量子化")


def _rows():
    if not os.path.exists(QUANT_JSON):
        pytest.skip("量子化の台帳が無い(tools/impl2/quant_probe.py で作る)")
    with open(QUANT_JSON, encoding="utf-8") as f:
        return json.load(f)


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


def test_the_quantisation_ledger_is_not_empty():
    """**空の台帳は全部を素通りさせる。** 件数そのものを別に数える。"""
    hits = [r for r in _rows() if r.get("quantises_to_8bit")]
    assert len(hits) >= FLOOR, (
        f"8 bit に落とすと判定された op が {len(hits)} 本しかない"
        f"(2026-09-16 の実測は {MEASURED} 本)。測定が壊れたか台帳が古い")


def test_every_quantising_op_says_so_in_its_note():
    """実測した事実が**ノートに載っている**こと。生成器の差し込みが消えたら落ちる。"""
    missing = []
    for r in _rows():
        if not r.get("quantises_to_8bit"):
            continue
        p = _note_path(r["op"])
        if p is None:
            missing.append(f"{r['op']}: ノートが無い")
            continue
        if not _MENTIONS_8BIT.search(open(p, encoding="utf-8").read()):
            missing.append(f"{r['op']}: ノートが 8 bit 量子化に触れていない")
    assert not missing, (
        "実測した量子化がノートから消えている(生成器の差し込みが効いていない):\n"
        + "\n".join(missing[:20]))


def test_the_verdict_needs_both_halves_of_the_signature():
    """**片方の署名だけで「量子化する」と言っていないこと。**

    格子に載るだけなら二値化の op が該当し、段数が多いだけなら普通の float の op が
    該当する。両方揃ってはじめて「8 bit の連続量」と言える —— 最初の版は署名を
    「揺らしに鈍い」にして**陽性対照で落ちた**(量子化する参照実装でも、揺らしが
    丸め境界を跨げば出力は 1 段変わる)。
    """
    for r in _rows():
        if r.get("quantises_to_8bit"):
            assert r.get("output_on_8bit_grid") and r.get("uses_many_levels"), (
                f"{r['op']}: 署名が片方しか立っていないのに量子化すると書いている")


def test_the_ledger_only_names_ops_that_exist():
    """台帳が古くなって、もう無い op を指していないこと。"""
    idx_path = os.path.join(ROOT, "docs", "OP_INDEX.json")
    if not os.path.exists(idx_path):
        pytest.skip("docs/OP_INDEX.json が無い")
    with open(idx_path, encoding="utf-8") as f:
        known = {o["name"] for o in json.load(f)["ops"]}
    gone = [r["op"] for r in _rows() if r["op"] not in known]
    assert not gone, f"台帳が存在しない op を指している(古い): {gone[:10]}"
