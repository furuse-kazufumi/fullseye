# -*- coding: utf-8 -*-
"""手で書いた「N operators / N ops / N notes」が、索引から数えた値のどれかと一致することの門。

2026-10-07 の見直しで、生成ブロックの外に手書きの数が古いまま 10 か所以上残っていた:
PyPI に出る ``pyproject.toml`` の description が「1,942 typed ops」(実際は 3,083)、
``CITATION.cff`` が 3,078 / 2,125、README が 901 / ~1200 / 265、INTEGRATION が 901 / 918、
AI 向けの SKILL.md 2 本が「~2000 notes」(実際は 3089)。生成器が書く数は drift 検査が守るが、
手書きの数はどの門にも映っていなかった。

ここでは対象ファイルの中の「3 桁以上の数 + ops / operators / notes」を全部拾い、
索引から計算した**許される値の集合**に入っているかだけを見る。入っていない数は、古いか、
新しい種類の数(ならここに足す)かのどちらか。
"""
from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]

FILES = ("pyproject.toml", "CITATION.cff", "README.md", "docs/INTEGRATION.md",
         "skills/fullseye-ops/SKILL.md", "fullseye/skill_template/SKILL.md")

_PAT = re.compile(r"(~?\d[\d,]*)\s+((?:typed |distinct |single-input |evolvable |registered )*"
                  r"(?:2-D |3-D )?(?:ops|operators|notes)\b)")

#: 索引の外で決まる数(理由つき)。
_OTHER = {
    2313: "HALCON の演算子の総数(halcon_names_data)",
    366: "SKILL.md の生成ブロック: 物理計測 15 族のノート数",
}


def _allowed() -> dict[int, str]:
    idx = json.loads((ROOT / "docs" / "OP_INDEX.json").read_text(encoding="utf-8"))
    t = idx["tiers"]
    single = t["registry"] + t["color"]
    notes = [p for p in (ROOT / "docs" / "ops").rglob("*.md")
             if not re.match(r"^INDEX(\.[a-z]{2})?\.md$", p.name) and p.name != "SAMPLES.md"
             and "guides" not in p.parts]
    import ops3d
    n3d = len(ops3d.list_ops())          # 3-D 台帳の op(1 本は別台帳と同名なので索引では 1 少ない)
    out = {idx["n_ops"]: "索引の全 op", t["ledger"]: "型つき台帳", single: "単入力の 2-D",
           single + t["nary"]: "2-D(n-ary 込み)", len(notes): "ノート", n3d: "3-D 台帳の op"}
    assert n3d > 300 and len(notes) > 3000, "数え損ねている: 3-D %d / ノート %d" % (n3d, len(notes))
    out.update(_OTHER)
    return out


def _found():
    for rel in FILES:
        for i, line in enumerate((ROOT / rel).read_text(encoding="utf-8").splitlines(), 1):
            for m in _PAT.finditer(line):
                digits = m.group(1).lstrip("~").replace(",", "")
                if len(digits) >= 3:
                    yield rel, i, m.group(1), int(digits), m.group(2)


def test_the_scan_sees_the_known_counts():
    got = list(_found())
    assert len(got) >= 10, "数を拾い損ねている: %d 件" % len(got)
    assert any(rel == "pyproject.toml" for rel, *_ in got), "PyPI の説明文を見ていない"


def test_every_hand_written_count_is_current():
    ok = _allowed()
    bad = ["%s:%d: %s %s" % (rel, i, raw, what) for rel, i, raw, n, what in _found() if n not in ok]
    assert not bad, ("手書きの数が索引と合わない(古いか、許す値の表に無い種類の数):\n  "
                     + "\n  ".join(bad) + "\n  いまの値: "
                     + ", ".join("%d=%s" % kv for kv in sorted(_allowed().items())))


def test_the_gate_catches_a_stale_count():
    """★門を壊して確かめる: 古い 1,942 は許す値に無い。"""
    assert 1942 not in _allowed() and 2000 not in _allowed()
