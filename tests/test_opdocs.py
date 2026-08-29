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


def test_intentional_op_name_overrides_are_pinned():
    """The only duplicate 2-D op names are the 4 deliberate backend safe-wrap overrides.

    These names are registered twice on purpose: a core ``ops._<name>`` fallback plus a
    ``backends_auto`` fail-closed ``_safe`` wrapper that wins (RT/last). Physically removing
    the core entry would break the Wave0 stable-slot invariant (tests/test_wave0.py) and the
    no-backend fallback, so instead we PIN the override set — a new *accidental* collision
    (a backend shadowing a core op unintentionally) makes this fail.
    """
    import ops
    from collections import Counter
    dups = sorted(n for n, c in Counter(o.name for o in ops.REGISTRY).items() if c > 1)
    assert dups == ["dyn_threshold", "edges_sub_pix", "laplace", "local_max"], (
        f"op-name duplicate set changed to {dups} — if this is a new intentional backend "
        "override, add it here (and confirm it wins in ops.RT); if accidental, rename it.")
    for n in dups:
        assert "_safe" in getattr(ops.RT[n], "__qualname__", ""), (
            f"{n}: the winning impl is no longer the backends_auto _safe wrapper "
            f"({ops.RT[n].__module__}.{getattr(ops.RT[n], '__qualname__', '?')})")
        # a core fallback of the same op still exists behind the override
        assert sum(1 for o in ops.REGISTRY if o.name == n) == 2, f"{n}: expected core+override"


# --------------------------------------------------------------------------- #
# 3-D help pages: same md=source-of-truth pipeline as 2-D, bulk-converted into
# op_help/3d/<name>.html (supersedes the retired tools/gen_op_help_3d.py).
# --------------------------------------------------------------------------- #
_3D_RECS = [r for r in _RECS if r["dim"] == "3d"]
_HELP3D = os.path.join(ROOT, "studio_assets", "op_help", "3d")


def test_every_3d_op_has_a_studio_help_page():
    """3-D help is generated into op_help/3d/<name>.html (namespaced so 2-D/3-D name
    collisions like fill_holes don't clobber each other)."""
    missing = [r["name"] for r in _3D_RECS
               if not os.path.exists(os.path.join(_HELP3D, r["name"] + ".html"))]
    assert not missing, f"{len(missing)} 3-D ops lack an op_help/3d page: {missing[:20]}"


def test_3d_help_is_generated_from_markdown_no_drift():
    """Each 3-D help page == md_to_html of its committed note (md is the single source of
    truth), with 3-D op-jump links namespaced op: -> op3d:. If a 3-D op's spec changes, the
    note drifts and so does this page, forcing `py -3.11 tools/opdocs.py html`."""
    drift = []
    for r in _3D_RECS:
        html_path = os.path.join(_HELP3D, r["name"] + ".html")
        md_path = OD._op_path(r)
        if not (os.path.exists(html_path) and os.path.exists(md_path)):
            continue
        with open(html_path, encoding="utf-8") as f:
            on_disk = f.read()
        with open(md_path, encoding="utf-8") as f:
            md = f.read()
        expected = OD._GEN_MARK + "\n" + OD.md_to_html(md).replace('href="op:', 'href="op3d:')
        if on_disk != expected:
            drift.append(os.path.relpath(html_path, ROOT))
    assert not drift, ("3-D help pages are stale — run `py -3.11 tools/opdocs.py html`:\n"
                       + "\n".join(drift[:30]))


def test_3d_help_pages_carry_marker_and_have_no_stray_2d_anchors():
    """Every 3-D page is machine-generated (carries the marker) and only links to 3-D ops
    (all op-jump anchors are op3d:, never a bare 2-D op:)."""
    unmarked, stray = [], []
    for r in _3D_RECS:
        p = os.path.join(_HELP3D, r["name"] + ".html")
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as f:
            txt = f.read()
        if OD._GEN_MARK not in txt:
            unmarked.append(r["name"])
        if 'href="op:' in txt:
            stray.append(r["name"])
    assert not unmarked, f"3-D help pages missing the generated marker: {unmarked[:20]}"
    assert not stray, f"3-D help pages carry bare 2-D op: anchors (should be op3d:): {stray[:20]}"
