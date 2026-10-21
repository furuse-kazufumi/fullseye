# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""設計ノートの行番号をエディタと同じ物理行に固定する。"""
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import gen_design_notes as G  # noqa: E402


def test_physical_lines_split_only_at_lf_boundaries():
    text = "# ★first\x0c\x1c\x85\u2028\u2029still first\nvalue = 1\n# ★second\n"

    assert G._physical_lines(text) == text.split("\n")
    assert [b["line"] for b in G._blocks_from_text(text, "synthetic.py")] == [1, 3]


def test_committed_poc_section_matches_fresh_generation():
    fresh = G.render(G.collect(), "ja")
    committed = (ROOT / "docs" / "DESIGN_NOTES.md").read_text(encoding="utf-8")

    heading = "## `examples/poc_cad_scan_deviation.py`"
    next_heading = "\n## `examples/poc_calipers_under_illusion.py`"
    start = committed.index(heading)
    fresh_start = fresh.index(heading)
    assert committed[start:committed.index(next_heading, start)] == \
        fresh[fresh_start:fresh.index(next_heading, fresh_start)]
