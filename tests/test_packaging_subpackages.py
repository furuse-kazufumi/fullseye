# -*- coding: utf-8 -*-
"""`fullseye/` 配下のサブパッケージが **全部** `pyproject.toml` の `packages` に居ること。

★`[tool.setuptools] packages = [...]` は**明示列挙**で、setuptools は明示列挙のとき
サブパッケージを自動では含めない。2026-09-15 に `fullseye/mcp/` を足したとき、
修正前に wheel を実際に作って確かめたら **`fullseye/mcp/*` は 0 エントリ**だった ——
import は通り、テストは緑、wheel からは丸ごと消える。root モジュールが wheel から落ちた
事故(0.1.6 で 321 op、2026-09-05 で 224 op、2026-09-14 で 26 op)と同じ族で、
場所がサブパッケージに移っただけ。`tests/test_packaging_foundation.py` は root
モジュールしか数えていなかったので、こちらはサブパッケージを数える。

検査は**ディスク側から**する(`__init__.py` を持つ dir を列挙して宣言と突き合わせる)。
宣言側から数えると、宣言し忘れたものは構造的に見えない
([[feedback_registered_only_gates_miss_unregistered]])。
"""
from __future__ import annotations

import os
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _declared_packages() -> list[str]:
    with open(os.path.join(ROOT, "pyproject.toml"), "rb") as f:
        return list(tomllib.load(f)["tool"]["setuptools"]["packages"])


def _subpackages_on_disk(top: str) -> list[str]:
    out = []
    base = os.path.join(ROOT, top)
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if not d.startswith((".", "__"))]
        if "__init__.py" in filenames and dirpath != base:
            rel = os.path.relpath(dirpath, ROOT).replace(os.sep, ".")
            out.append(rel)
    return sorted(out)


def test_every_subpackage_under_fullseye_is_declared_in_packages():
    declared = set(_declared_packages())
    on_disk = _subpackages_on_disk("fullseye")
    assert on_disk, "fullseye/ 配下にサブパッケージが 1 つも無い(この門が空を通している)"
    missing = [p for p in on_disk if p not in declared]
    assert not missing, (
        "wheel から落ちるサブパッケージ: %s —— pyproject.toml の "
        "[tool.setuptools] packages に足すこと(明示列挙は自動で含めない)" % missing)


def test_declared_packages_all_exist_on_disk():
    """逆向き: 宣言だけ残って実体が消えたものも捕まえる。"""
    for p in _declared_packages():
        d = os.path.join(ROOT, *p.split("."))
        assert os.path.isfile(os.path.join(d, "__init__.py")), "宣言だけある package: %s" % p
