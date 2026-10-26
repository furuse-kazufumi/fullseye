# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""docs/anim3d/itokawa_gravity.html が幅 390 px で横にはみ出さない(全タブ × 8 言語)ことの門。

headless Chrome の窓は幅 500 px 前後より狭くならない(実測 511 px)ので、幅 390 の iframe に入れて組ませ、
document.documentElement.scrollWidth <= clientWidth を確かめる(tools/check_page_overflow.py)。
Chrome の無い環境(CI の Linux)では回らない —— その場合は skip の理由に出す。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _tool():
    spec = importlib.util.spec_from_file_location("check_page_overflow_t", ROOT / "tools" / "check_page_overflow.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_no_horizontal_overflow_at_390px_in_any_tab_or_language():
    m = _tool()
    if m.chrome_path() is None:
        pytest.skip("Chrome が無い(FULLSEYE_CHROME で指定すれば回る)")
    rows = m.check(ROOT / "docs" / "anim3d" / "itokawa_gravity.html", 390)
    assert len(rows) == 8 * 6, len(rows)
    bad = [(r["l"], r["id"], r["sw"], r["cw"], r["bad"]) for r in rows if r["sw"] > r["cw"]]
    assert not bad, bad
    assert all(r["cw"] <= 390 for r in rows)                     # 本当に 390 px 以下で組ませている
