# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Operator-docs invariants: the Markdown corpus is the source of truth and stays in
sync with the op registry (version linkage), every op has a note + a Studio help page,
and every op-family has an authored usage guide.

The drift check compares each committed per-op note to what ``tools/opdocs.py`` would
generate for the *current* registry — with no side effects. If an op's spec changes,
the note drifts and this fails, forcing a regenerate so docs and code share one version
(image-processing behaviour is sensitive; docs must never silently lag the op set).
"""
import glob
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, ROOT)
import opdocs as OD  # noqa: E402

_RECS, _IDX2D, _OP_FAM, _FAM_OPS = OD._records()
_BY_NAME = {(r["dim"], r["name"]): r for r in _RECS}
# last-writer-wins per path (matches cmd_md, which overwrites on duplicate op names)
_PATH_REC = {}
for _r in _RECS:
    _PATH_REC[OD._op_path(_r)] = _r

_EXPECTED_GUIDES = sorted(f for f, ops in _FAM_OPS.items())  # 13 gallery2d_* families


def test_every_op_has_a_note():
    missing = [f"{r['dim']}:{r['name']}" for r in _RECS if not os.path.exists(OD._op_path(r))]
    assert not missing, f"{len(missing)} ops have no Markdown note: {missing[:20]}"


def test_notes_match_generator_no_drift():
    """Committed per-op note == generator output for the current registry (version linkage)."""
    drift = []
    for path, rec in _PATH_REC.items():
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            on_disk = f.read()
        if on_disk != OD._op_md(rec, path, _BY_NAME):
            drift.append(os.path.relpath(path, ROOT))
    assert not drift, ("per-op notes are stale — run `py -3.11 tools/opdocs.py md`:\n"
                       + "\n".join(drift[:30]))


def test_notes_carry_version_author_license():
    # a representative sample must stamp the linkage fields
    sample = [r for r in _RECS if r["dim"] == "2d"][:5] + [r for r in _RECS if r["dim"] == "3d"][:3]
    for r in sample:
        with open(OD._op_path(r), encoding="utf-8") as f:
            txt = f.read()
        assert "author: Kazufumi Furuse" in txt, r["name"]
        assert "license: Apache-2.0" in txt, r["name"]
        assert "version:" in txt, r["name"]
        assert "Kazufumi Furuse" in txt.rsplit("---", 1)[-1], f"copyright footer missing in {r['name']}"


def test_every_2d_op_has_a_studio_help_page():
    """Studio reads op_help/<name>.html; every 2-D op must resolve to one (generated or authored)."""
    base = os.path.join(ROOT, "studio_assets", "op_help")
    missing = [r["name"] for r in _RECS if r["dim"] == "2d"
               and not os.path.exists(os.path.join(base, r["name"] + ".html"))]
    assert not missing, f"{len(missing)} 2-D ops lack an op_help page: {missing[:20]}"


def test_index_and_samples_generated():
    for rel in ("docs/ops/INDEX.md", "docs/ops/2d/INDEX.md", "docs/ops/3d/INDEX.md",
                "docs/ops/SAMPLES.md"):
        p = os.path.join(ROOT, rel)
        assert os.path.exists(p), f"missing generated index: {rel}"
        with open(p, encoding="utf-8") as f:
            txt = f.read()
        assert "Kazufumi Furuse" in txt, f"copyright missing in {rel}"
    # top index records the version/fingerprint linkage comment
    with open(os.path.join(ROOT, "docs/ops/INDEX.md"), encoding="utf-8") as f:
        top = f.read()
    assert "fingerprint" in top and "fullseye" in top, "version/fingerprint linkage missing in top INDEX"


def test_every_family_has_a_guide():
    gdir = os.path.join(ROOT, "docs", "ops", "2d", "guides")
    have = {os.path.splitext(f)[0] for f in os.listdir(gdir)} if os.path.isdir(gdir) else set()
    missing = [f for f in _EXPECTED_GUIDES if f not in have]
    assert not missing, f"op-families with no usage guide: {missing}"


@pytest.mark.parametrize("guide", _EXPECTED_GUIDES)
def test_guide_is_well_formed(guide):
    p = os.path.join(ROOT, "docs", "ops", "2d", "guides", guide + ".md")
    if not os.path.exists(p):
        pytest.skip(f"{guide} not authored yet")
    with open(p, encoding="utf-8") as f:
        md = f.read()
    assert md.lstrip().startswith("---"), f"{guide}: missing YAML frontmatter"
    assert "Kazufumi Furuse" in md, f"{guide}: missing author/copyright"
    assert "```mermaid" in md, f"{guide}: missing a mermaid pipeline diagram"
    assert "```python" in md, f"{guide}: missing a runnable python snippet"
    # the guide must actually name ops from its own family (grounded, not generic prose).
    # Ops may be written as `code`, **bold**, or in mermaid — accept any whole-word mention.
    fam_ops = set(_FAM_OPS.get(guide, []))   # _FAM_OPS: family -> set of op-name strings
    hit = {n for n in fam_ops if re.search(r"(?<![\w])" + re.escape(n) + r"(?![\w])", md)}
    assert len(hit) >= 3, f"{guide}: names too few of its own family ops ({len(hit)}/{len(fam_ops)})"
