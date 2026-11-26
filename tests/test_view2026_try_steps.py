# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ViEW2026 の「試してみる」の手順が、そのまま打って通る順序であること(2026-11-26)。

新しい venv で以前の手順(`pip install fullseye` → clone → 実行)を打つと、PyPI の版と clone した
master のコードが混ざり、焦点合成の PoC が OpenCV の op(`xcv2_lap_var`)を呼んだ所で exit 1 になった。
clone した木を `[opencv]` 付きで入れる手順に直すと PASS(23 秒、図 7 枚)。ここではその形を固定する:
clone が install より先、install は clone した木(`-e .`)、PoC が要る extra を含む。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import gen_view2026_pages as G  # noqa: E402

POC = ROOT / "examples" / "poc_focus_stacking.py"


def _lines():
    body = G.TRY_CMD.strip().strip("`").strip()
    return [ln.strip() for ln in body.splitlines() if ln.strip()]


def test_clone_comes_before_install_and_install_uses_the_clone():
    lines = _lines()
    clone = next(i for i, ln in enumerate(lines) if ln.startswith("git clone"))
    install = next(i for i, ln in enumerate(lines) if ln.startswith("pip install"))
    run = next(i for i, ln in enumerate(lines) if ln.startswith("python examples/"))
    assert clone < install < run, lines
    assert re.match(r'pip install -e "?\.\[', lines[install]), (
        "PyPI の版でなく clone した木を入れること(版が混ざると PoC が落ちる): %r" % lines[install])


def test_install_carries_every_backend_the_try_poc_calls():
    """PoC が呼ぶ x<backend>_ op の backend を extra が含む(今は xcv2_ = opencv)。"""
    src = POC.read_text(encoding="utf-8")
    needed = set()
    if re.search(r"\bxcv2_\w+", src):
        needed.add("opencv")
    if re.search(r"\bxsk_\w+", src):
        needed.add("skimage")
    assert needed, "PoC が x*_ op を呼ばなくなった —— この門の前提を見直す"
    install = next(ln for ln in _lines() if ln.startswith("pip install"))
    extras = set(re.search(r"\[([^\]]*)\]", install).group(1).split(","))
    assert needed <= extras | {"all"}, (needed, install)


def test_every_published_page_shows_the_same_steps():
    pages = [ROOT / "docs/view2026/index.md"] + sorted((ROOT / "docs/view2026").glob("*/index.md"))
    assert len(pages) >= 8, pages
    for p in pages:
        assert G.TRY_CMD in p.read_text(encoding="utf-8"), "%s が古い手順のまま(生成器を回す)" % p
