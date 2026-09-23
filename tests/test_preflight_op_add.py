# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""``tools/preflight_op_add.py`` が**どの台帳にも反応する**ことの門。

2026-09-23 の実測: ここには門が 1 本も無く、``REGISTRY_FILES`` は 8 つの名前の
**手書き列挙**だった。照合は ``startswith`` の完全一致なので ``opsspc.py`` も
``ops1d.py`` も当たらず、台帳 **40 本のうち 3 本**しか見ていなかった。opsspc に
op を 8 本足して preflight を回すと「動きうる帳簿: (無し) / 選んだ門: 0 ファイル」
と出る —— **「帳簿に触っていない」ときとまったく同じ顔**なので、0 件を見ても
異常だと気づけない。道具の沈黙は「異常なし」ではなかった。

直しは列挙をやめて repo から導出すること(``ops*.py`` と、台帳が ``_MOD`` で
名指しする実装モジュール)。この門はその導出を**台帳の側から数えて**固定する。
"""
import glob
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

preflight = pytest.importorskip("preflight_op_add",
                                reason="tools/preflight_op_add.py が読めない")


def _ledgers():
    return sorted(os.path.basename(p) for p in glob.glob(os.path.join(ROOT, "ops*.py")))


def test_every_ledger_is_recognised_as_a_registry_file():
    """``ops*.py`` は**全部**「op が増減しうる」ファイルとして扱われること。

    台帳を 1 本足した人が preflight を直し忘れても、ここで気づけるようにする
    (直し忘れの症状は例外でなく **0 件の静かな成功**なので、門が無いと出ない)。
    """
    ledgers = _ledgers()
    assert len(ledgers) >= 30, "台帳が %d 本しか見つからない — 数え方が壊れている" % len(ledgers)
    missed = [name for name in ledgers
              if preflight._touched_surfaces({name}) != set(preflight.SURFACES)]
    assert not missed, (
        "%d 本の台帳が preflight から見えていない(触っても門が 1 つも選ばれない): %s"
        % (len(missed), missed[:8]))


def test_the_modules_a_ledger_names_are_recognised_too():
    """台帳が ``_MOD`` で名指しする実装モジュールも同じ扱いになること。

    op の実体は ``spc.py`` / ``blob2d.py`` のような実装側にあり、**台帳を触らずに
    実装だけ直す回**がある(既存 op の挙動が変われば図もノートも変わる)。
    """
    seen = 0
    for led in _ledgers():
        for mod in preflight._ledger_modules(os.path.join(ROOT, led)):
            seen += 1
            assert preflight._touched_surfaces({mod + ".py"}) == set(preflight.SURFACES), (
                "台帳 %s が名指しする実装 %s.py が preflight から見えていない" % (led, mod))
    assert seen >= 30, "台帳が名指しする実装モジュールが %d 個しか拾えていない" % seen


def test_a_plain_document_does_not_select_every_gate():
    """**空を通さない**: 何を渡しても全門が選ばれるなら、この門は無意味。

    導出を「常に真」で実装してしまう事故(``ops*`` の照合を書き間違える等)を、
    レジストリでないファイルで押さえる。
    """
    for innocent in ("README.md", "CHANGELOG.md", "LICENSE", "docs/README.ja.md"):
        assert preflight._touched_surfaces({innocent}) != set(preflight.SURFACES), (
            "%r がレジストリ本体と見なされている — 導出が広すぎる" % innocent)


def test_ledger_count_is_derived_not_hand_written():
    """導出された一覧が、手書きでは追いつかない規模であることを数で残す。

    2026-09-23 時点: 台帳 40 本 + 実装 117 本 + 中枢 4 本 = 161 件。手書きの 8 件とは
    桁が違うので、「増えたら足す」運用が成り立たないことがこの数で分かる。
    """
    assert len(preflight.REGISTRY_FILES) > 3 * len(_ledgers()), (
        "導出が %d 件しかない(台帳 %d 本)— 実装モジュールを拾えていない"
        % (len(preflight.REGISTRY_FILES), len(_ledgers())))
