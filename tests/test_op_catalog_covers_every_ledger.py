# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""`OP_CATALOG.md` が**台帳の全 op**を載せているか —— 配布物の側から数える門。

## なぜ要るか(2026-09-16)

`fullseye/OP_CATALOG.md` は wheel に同梱され、「用途を伝えればどの op を
どう組み合わせるか AI が提案するための**全 op の一覧**」と自分で名乗っている。
ところが実測すると、載っていたのは **台帳 1,027 op のうち 550 op だけ**だった。
`tools/gen_op_catalog.py` が `ops3d` / `ops2d` / `ops1d` / `opsmath` /
`opsoptics` の **5 節しか出していなかった**ためで、残る **28 族 436 op**
(カメラ校正・blob 解析・tomography・PIV・DEM・粗さ …)は 1 行も載っていない。

読み手から見るとこれは「無い」と同じで、実際に外部の AI 2 体が
「カメラ校正の op は確認できなかった」と報告した。**検索層の自己紹介が
探す範囲を決めてしまう**形([[feedback_retrieval_layer_must_not_describe_itself]])。

## なぜ「配布物の側から」数えるか

生成器の出力同士を突き合わせる門(`test_opdocs.test_op_catalog_matches_generator_no_drift`)
は**既に在った**。そして緑だった —— 生成器が 5 節しか出さないなら、生成物も
5 節で「一致」するからである。**一致の門は空を通す**
([[feedback_drift_gate_passes_empty_output]])。

だからここでは生成器を呼ばず、**コミット済み・同梱される markdown を読んで**、
台帳(`opassist._LEDGERS` = `fs.op_find` / `fs.ledger` が引く正本)の側から
「この op の名前がファイルに在るか」を数える。数える向きが逆なので、
生成器が族を取りこぼしても検出できる。

落ちたら `py -3.11 tools/gen_op_catalog.py` を回すこと(門を緩めるのではない)。
"""
from __future__ import annotations

import importlib
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

#: wheel に入るコピーが**正**(利用者と AI が実際に読むのはこちら)。
SHIPPED = os.path.join(ROOT, "fullseye", "OP_CATALOG.md")
DOCS_COPY = os.path.join(ROOT, "docs", "OP_CATALOG.md")

#: 台帳の行(`- \`op_name\` (\`in → out\`) — 説明`)。スタンドアロン関数 API の行は
#: 署名がバッククォートの内側に入るのでここには一致しない(意図どおり)。
_OP_LINE = re.compile(r"^- `([A-Za-z_][A-Za-z0-9_]*)`", re.M)


def _listed(path: str) -> set[str]:
    with open(path, encoding="utf-8") as fh:
        return set(_OP_LINE.findall(fh.read()))


def _ledger_tables() -> list[tuple[str, dict]]:
    """`opassist._LEDGERS` の全族 -> (モジュール名, op 表)。

    import 失敗は**握らない**。台帳は numpy/scipy だけで組める一次モジュールなので、
    読めないのは「壊れた checkout」であって「無い機能」ではない
    (`imgevolve._ledger_rows` と同じ規律)。
    """
    import opassist

    out = []
    for mod_name, table in opassist._LEDGERS:
        entries = getattr(importlib.import_module(mod_name), table)
        assert entries, "%s.%s が空" % (mod_name, table)
        out.append((mod_name, entries))
    return out


def test_the_shipped_catalog_exists():
    assert os.path.isfile(SHIPPED), (
        "fullseye/OP_CATALOG.md が無い —— `py -3.11 tools/gen_op_catalog.py`")


def test_every_ledger_family_appears_in_the_shipped_catalog():
    """★族まるごとの欠落。これが 28 族 436 op を隠していた失敗そのもの。"""
    listed = _listed(SHIPPED)
    missing = [mod for mod, entries in _ledger_tables()
               if not (set(entries) & listed)]
    assert not missing, (
        "同梱カタログに 1 op も載っていない台帳の族が %d 族: %s —— "
        "`py -3.11 tools/gen_op_catalog.py` で作り直すこと。"
        % (len(missing), ", ".join(missing)))


def test_every_ledger_op_appears_in_the_shipped_catalog():
    """族が載っていても op が欠けることはある(カテゴリ分けの取りこぼし)。"""
    listed = _listed(SHIPPED)
    missing = {}
    for mod, entries in _ledger_tables():
        lost = sorted(n for n in entries if n not in listed)
        if lost:
            missing[mod] = lost
    total = sum(len(v) for v in missing.values())
    assert not missing, (
        "同梱カタログに載っていない台帳 op が %d 本: %s —— "
        "`py -3.11 tools/gen_op_catalog.py`"
        % (total, {k: v[:5] for k, v in missing.items()}))


def test_the_catalog_is_not_trivially_small():
    """**空を通さない。** 抽出の正規表現が壊れて 0 件になれば上の 2 本は無言で緑。

    実測の下限を置く(2026-09-16 実測: 台帳 1,027 op / 33 族)。
    """
    listed = _listed(SHIPPED)
    assert len(listed) >= 900, (
        "カタログから抽出できた op 名が %d 件しかない —— 抽出の印が壊れていないか"
        % len(listed))
    tables = _ledger_tables()
    assert len(tables) >= 30, "台帳の族が %d しか見えない" % len(tables)


def test_the_docs_copy_and_the_shipped_copy_agree():
    """人が読む docs/ のコピーと wheel に入るコピーが同じであること。

    片方だけ作り直す事故を止める(生成器は両方に書くので、ずれていたら
    どちらかが手で触られたか、回し忘れている)。
    """
    with open(SHIPPED, encoding="utf-8") as fh:
        shipped = fh.read()
    with open(DOCS_COPY, encoding="utf-8") as fh:
        docs = fh.read()
    assert shipped == docs, (
        "docs/OP_CATALOG.md と fullseye/OP_CATALOG.md が食い違っている —— "
        "`py -3.11 tools/gen_op_catalog.py` で両方を作り直すこと")


@pytest.mark.parametrize("path", [SHIPPED, DOCS_COPY],
                         ids=["shipped", "docs"])
def test_the_catalog_names_its_own_scope_honestly(path):
    """自己紹介(「全 op の一覧」)と中身の量が食い違わないこと。

    この門の動機そのもの —— 台帳の 54 % しか載せないファイルが
    「全 op カタログ」を名乗っていた。
    """
    listed = _listed(path)
    ledger_ops = set()
    for _mod, entries in _ledger_tables():
        ledger_ops |= set(entries)
    covered = len(ledger_ops & listed)
    assert covered == len(ledger_ops), (
        "%s は台帳 %d op のうち %d op しか載せていない(%.0f %%)"
        % (os.path.basename(path), len(ledger_ops), covered,
           100.0 * covered / max(len(ledger_ops), 1)))
