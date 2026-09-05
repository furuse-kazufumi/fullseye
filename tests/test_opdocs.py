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
import json
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
                "docs/ops/math/INDEX.md", "docs/ops/optics/INDEX.md",
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


def test_index_fingerprint_matches_the_live_registry():
    """目次の fingerprint が **live レジストリと実際に一致**すること。

    INDEX.md のヘッダは「この fingerprint が live レジストリと一致することを
    CI の drift テストが強制する」と書いているが、2026-09-02 まで検査は
    ``"fingerprint" in top`` という**文字列の存在確認だけ**で、値を比べて
    いなかった。実測: 目次は 851 op のまま live は 861 op で、**10 op が
    目次から欠落**していた(個別の md は存在するのに索引から辿れない)。

    主張だけあって実装が無い検査は、無い検査より悪い —— 「守られている」と
    読める文言が残るぶん、誰も見に行かなくなる。
    """
    import re as _re
    fp_live = OD._registry_fingerprint(_RECS)
    m = _re.search(r"op-registry fingerprint ([0-9a-f]+)", top_index_text())
    assert m, "INDEX.md のヘッダに fingerprint が見つからない"
    assert m.group(1) == fp_live, (
        f"docs/ops/INDEX.md の fingerprint {m.group(1)} が live レジストリの "
        f"{fp_live} と違う — `py -3.11 tools/opdocs.py md` で再生成すること")


def top_index_text():
    with open(os.path.join(ROOT, "docs/ops/INDEX.md"), encoding="utf-8") as f:
        return f.read()


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


#: 意図的なバックエンド上書き: コアの ``ops._<name>`` を ``backends_auto`` の
#: fail-closed ``_safe`` ラッパが置き換える。**上書き先が勝つこと**が設計意図。
_SAFE_WRAP_OVERRIDES = ["dyn_threshold", "edges_sub_pix", "laplace", "local_max"]


def test_op_names_are_unique_in_the_registry():
    """レジストリに同名 op が 2 つ存在しない。

    2026-09-02 まで上の 4 件が**二重登録**されていた。当時の判断は「コアの
    fallback を物理的に消すと Wave0 の stable-slot 不変条件と no-backend
    fallback が壊れるので、上書きの集合を pin する」だった。

    しかし二重登録には測れる害があった: ``RT`` / ``_BY_NAME`` / ``SLOTS`` は
    後勝ちの dict なので**先に入った方は名前で二度と引けない**(``decode_by_names``
    が再現できない)一方、``_candidates`` はリストを走査するので**両方が抽選に
    入り、この 4 op だけ当たる確率が 2 倍**になっていた。

    いまは ``ops.py`` の登録時に**後勝ちで畳む**。``RT`` は元々後勝ちの dict
    だったので**名前で引ける実装は 1 ビットも変わらず**、消えるのは抽選の
    二重取りだけ。backend 不在の環境ではコア定義しか登録されないので
    no-backend fallback も保たれる。stable-slot は pin を取り直して守る。
    """
    import ops
    from collections import Counter
    dups = sorted(n for n, c in Counter(o.name for o in ops.REGISTRY).items() if c > 1)
    assert not dups, (
        f"op 名が重複している: {dups} — 名前は addressing の鍵で、先に入った方は "
        "名前で引けなくなるうえ、抽選には両方入って確率が 2 倍になる。"
        "ops.py の登録で後勝ちに畳まれるはずなので、ここに出るのは畳み損ね。")


def test_intentional_overrides_still_win_by_name():
    """意図的な上書き 4 件が、名前で引いたときに ``_safe`` ラッパを指すこと。

    重複を畳むときに**勝者を入れ替えてはいけない**。最初の実装は「先に来た方を
    残す」にしてしまい、コアの素実装が勝つようになっていた(= fail-closed の
    ラッパが外れる)。畳む向きが逆でも重複は消えるので、数だけ見ていると通る。
    """
    import ops
    for n in _SAFE_WRAP_OVERRIDES:
        assert n in ops.RT, f"{n} がレジストリから消えている"
        fn = ops.RT[n]
        # ★2026-09-03: 全 backend の _safe が backend_safe.guard に集約されたので、
        # qualname の文字列一致ではなく guard が立てる構造化マーカーで判定する
        # (guard は qualname にも "_safe(...)" を残すが、そちらは表示用)。
        assert getattr(fn, "__fullseye_guarded__", False) or "_safe" in getattr(fn, "__qualname__", ""), (
            f"{n}: 名前で引ける実装が fail-closed ラッパでない "
            f"({fn.__module__}.{getattr(fn, '__qualname__', '?')})")


def test_dropped_duplicates_are_exactly_the_known_overrides():
    """畳んだ結果として捨てた名前が、既知の上書き集合ちょうどであること。

    黙って消えると「登録したのに使えない」に気づけない。新しい衝突が増えたら
    ここが赤くなる(意図的なら一覧へ追加、事故なら改名する)。
    """
    import ops
    dropped = sorted(getattr(ops, "DROPPED_DUPLICATES", []))
    assert dropped == sorted(_SAFE_WRAP_OVERRIDES), (
        f"畳んだ重複が {dropped} に変わった — 意図的な上書きなら "
        "_SAFE_WRAP_OVERRIDES へ追加し、勝者が正しいか確認すること。事故なら改名。")


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


# --------------------------------------------------------------------------- #
# math ops (opsmath ledger): same md=source-of-truth pipeline as 2-D/3-D —
# notes under docs/ops/math/<category>/, help pages in op_help/math/<name>.html
# (namespaced like 3-D; op-jump anchors are opmath:, the guide anchor guidemath:),
# and one authored family guide (docs/ops/math/guides/math_metrology.md).
# --------------------------------------------------------------------------- #
_MATH_RECS = [r for r in _RECS if r["dim"] == "math"]
_HELPMATH = os.path.join(ROOT, "studio_assets", "op_help", "math")


def test_math_registry_is_connected():
    """Every op in the opsmath ledger flows into the docs corpus (and only those)."""
    import opsmath
    have = {r["name"] for r in _MATH_RECS}
    assert have == set(opsmath.OPSMATH), (
        f"docs corpus and opsmath ledger disagree: only-in-docs={have - set(opsmath.OPSMATH)}, "
        f"only-in-ledger={set(opsmath.OPSMATH) - have}")
    assert len(_MATH_RECS) >= 16                       # tier-1: linalg 6 + stats 5 + interp_poly 5
    assert {"linalg", "stats", "interp_poly"} <= {r["category"] for r in _MATH_RECS}


def test_every_math_op_has_a_studio_help_page():
    missing = [r["name"] for r in _MATH_RECS
               if not os.path.exists(os.path.join(_HELPMATH, r["name"] + ".html"))]
    assert not missing, f"{len(missing)} math ops lack an op_help/math page: {missing}"


def test_math_help_is_generated_from_markdown_no_drift():
    """Each math help page == md_to_html of its committed note, with op-jump anchors
    namespaced op: -> opmath: and the guide anchor guide2d: -> guidemath:."""
    drift = []
    for r in _MATH_RECS:
        html_path = os.path.join(_HELPMATH, r["name"] + ".html")
        md_path = OD._op_path(r)
        if not (os.path.exists(html_path) and os.path.exists(md_path)):
            continue
        with open(html_path, encoding="utf-8") as f:
            on_disk = f.read()
        with open(md_path, encoding="utf-8") as f:
            md = f.read()
        expected = (OD._GEN_MARK + "\n"
                    + OD.md_to_html(md)
                    .replace('href="op:', 'href="opmath:')
                    .replace('href="guide2d:', 'href="guidemath:'))
        if on_disk != expected:
            drift.append(os.path.relpath(html_path, ROOT))
    assert not drift, ("math help pages are stale — run `py -3.11 tools/opdocs.py html`:\n"
                       + "\n".join(drift[:30]))


def test_math_help_pages_carry_marker_and_are_namespaced():
    unmarked, stray = [], []
    for r in _MATH_RECS:
        p = os.path.join(_HELPMATH, r["name"] + ".html")
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as f:
            txt = f.read()
        if OD._GEN_MARK not in txt:
            unmarked.append(r["name"])
        if 'href="op:' in txt or 'href="guide2d:' in txt:
            stray.append(r["name"])
    assert not unmarked, f"math help pages missing the generated marker: {unmarked}"
    assert not stray, f"math help pages carry non-namespaced op:/guide2d: anchors: {stray}"


# --------------------------------------------------------------------------- #
# optics ops (opsoptics ledger, 2026-09-01): the second *ledger* dimension, on
# the same md=source-of-truth pipeline as math — notes under
# docs/ops/optics/<category>/, help pages in op_help/optics/<name>.html
# (anchors opoptics: / guideoptics:), and one authored family guide
# (docs/ops/optics/guides/optics_imaging.md). These tests are the math block's
# twin: when a third ledger dimension arrives, generalise both together.
# --------------------------------------------------------------------------- #
_OPT_RECS = [r for r in _RECS if r["dim"] == "optics"]
_HELPOPT = os.path.join(ROOT, "studio_assets", "op_help", "optics")


def test_optics_registry_is_connected():
    """Every op in the opsoptics ledger flows into the docs corpus (and only those)."""
    import opsoptics
    have = {r["name"] for r in _OPT_RECS}
    assert have == set(opsoptics.OPSOPTICS), (
        "docs corpus and opsoptics ledger disagree: "
        f"only-in-docs={have - set(opsoptics.OPSOPTICS)}, "
        f"only-in-ledger={set(opsoptics.OPSOPTICS) - have}")
    # optics 18 + raytrace "design" 15 + lensimage "imaging_sim" 5 + lensopt "optimization" 3
    # + illumdesign "illumination" 6 = 47。2026-09-04 に見え方の 5 族 33 op を追加:
    # matappear "appearance" 7 + glassmirror "interface" 4 / "mirror" 2 / "glassbody" 4
    # + metalfinish "finish" 5 + surfacelib "material" 6 / "surface" 5 = 33 → 計 124。
    # 2026-09-05: optscene "scene" 44 op を追加 → 計 124。
    assert len(_OPT_RECS) == 124
    assert {"geometric", "wave", "imaging", "polarization", "design", "imaging_sim",
            "optimization", "illumination", "appearance", "interface", "mirror",
            "glassbody", "finish", "material", "surface",
            "scene"} == {r["category"] for r in _OPT_RECS}
    # the design / imaging_sim notes must say where their implementation lives
    for r in _OPT_RECS:
        if r["category"] == "design":
            assert r["module"] == "raytrace", (r["name"], r["module"])
        if r["category"] == "imaging_sim":
            assert r["module"] == "lensimage", (r["name"], r["module"])
        if r["category"] == "optimization":
            assert r["module"] == "lensopt", (r["name"], r["module"])
        if r["category"] == "illumination":
            assert r["module"] == "illumdesign", (r["name"], r["module"])


def test_every_optics_op_has_a_studio_help_page():
    missing = [r["name"] for r in _OPT_RECS
               if not os.path.exists(os.path.join(_HELPOPT, r["name"] + ".html"))]
    assert not missing, f"{len(missing)} optics ops lack an op_help/optics page: {missing}"


def test_optics_help_is_generated_from_markdown_no_drift():
    """Each optics help page == md_to_html of its committed note, with op-jump
    anchors namespaced op: -> opoptics: and guide2d: -> guideoptics:."""
    drift = []
    for r in _OPT_RECS:
        html_path = os.path.join(_HELPOPT, r["name"] + ".html")
        md_path = OD._op_path(r)
        if not (os.path.exists(html_path) and os.path.exists(md_path)):
            continue
        with open(html_path, encoding="utf-8") as f:
            on_disk = f.read()
        with open(md_path, encoding="utf-8") as f:
            md = f.read()
        expected = (OD._GEN_MARK + "\n"
                    + OD.md_to_html(md)
                    .replace('href="op:', 'href="opoptics:')
                    .replace('href="guide2d:', 'href="guideoptics:'))
        if on_disk != expected:
            drift.append(os.path.relpath(html_path, ROOT))
    assert not drift, ("optics help pages are stale — run `py -3.11 tools/opdocs.py html`:\n"
                       + "\n".join(drift[:30]))


def test_optics_help_pages_carry_marker_and_are_namespaced():
    unmarked, stray = [], []
    for r in _OPT_RECS:
        p = os.path.join(_HELPOPT, r["name"] + ".html")
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as f:
            txt = f.read()
        if OD._GEN_MARK not in txt:
            unmarked.append(r["name"])
        if 'href="op:' in txt or 'href="guide2d:' in txt:
            stray.append(r["name"])
    assert not unmarked, f"optics help pages missing the generated marker: {unmarked}"
    assert not stray, f"optics help pages carry non-namespaced anchors: {stray}"


def test_optics_notes_state_the_fail_closed_contract():
    """Each ledger dimension states its family-wide input contract once per note;
    the optics one names the units rule and the two documented infinities."""
    for r in _OPT_RECS:
        with open(OD._op_path(r), encoding="utf-8") as f:
            txt = f.read()
        assert "ファミリ共通の入力契約(fail-closed)" in txt, r["name"]
        assert "_mm" in txt and "far_is_infinite" in txt, r["name"]


def test_every_optics_op_has_a_worked_example():
    """The optics ledger keeps the same 100%-example invariant the 2-D/3-D
    registries are held to (tests/test_op_example_coverage.py)."""
    uncovered = sorted(r["name"] for r in _OPT_RECS if not r["examples"])
    assert not uncovered, f"optics ops with no worked example: {uncovered}"


def test_no_dangling_relative_links_in_corpus():
    """Every relative Markdown link under docs/ops resolves. This guards against an op
    docstring accidentally forming a link — e.g. a range 's∈[-1,1](凸球+1・...)' parses as
    [-1,1](凸球+1・...), a bogus target that becomes a broken anchor once converted to HTML.
    External http(s)/mailto and pure #anchor links are skipped."""
    import re as _re
    docs = os.path.join(ROOT, "docs", "ops")
    link = _re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    dangling = []
    for dp, _dirs, fs in os.walk(docs):
        for fn in fs:
            if not fn.endswith(".md"):
                continue
            p = os.path.join(dp, fn)
            with open(p, encoding="utf-8") as f:
                txt = f.read()
            for m in link.finditer(txt):
                tgt = m.group(1).strip().split("#", 1)[0]
                if not tgt or tgt.startswith(("http://", "https://", "mailto:")):
                    continue
                if not os.path.exists(os.path.normpath(os.path.join(dp, tgt))):
                    dangling.append(os.path.relpath(p, ROOT) + " -> " + tgt)
    assert not dangling, ("dangling relative links in the op-docs corpus "
                          "(often a docstring with an accidental [x](y) — add a space, e.g. "
                          "'[-1,1] (...)'):\n" + "\n".join(dangling[:30]))


# --------------------------------------------------------------------------- #
# generated ledgers (OP_CATALOG.md / SENSOR_PLAYBOOK.md) must not drift          #
# --------------------------------------------------------------------------- #
def _diff_summary(expected: str, on_disk: str, limit: int = 12) -> str:
    import difflib
    d = difflib.unified_diff(on_disk.splitlines(), expected.splitlines(),
                             "committed", "generator", lineterm="", n=0)
    lines = [l for l in d if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
    return "\n".join(lines[:limit]) + ("\n..." if len(lines) > limit else "")


def _assert_no_drift(md: str, rel_paths, regen_cmd: str):
    """Committed copy == in-memory generator output (no file side effects, like
    test_notes_match_generator_no_drift). Both the docs/ copy and the shipped fullseye/
    copy (the one that goes into the wheel) are checked."""
    drift = []
    for rel in rel_paths:
        p = os.path.join(ROOT, rel)
        assert os.path.exists(p), f"{rel} missing — run `{regen_cmd}`"
        with open(p, encoding="utf-8") as f:
            on_disk = f.read()
        if on_disk != md:
            drift.append(f"{rel}:\n{_diff_summary(md, on_disk)}")
    assert not drift, (f"generated ledger is stale — run `{regen_cmd}`:\n" + "\n".join(drift))


def test_op_catalog_matches_generator_no_drift():
    """docs/OP_CATALOG.md drifted from tools/gen_op_catalog.py (2026-09-02 audit: 4 op names
    listed twice, tb_* out-types stale, a removed op still listed). This pins it."""
    import gen_op_catalog as GC
    _assert_no_drift(GC.build_catalog(), ("docs/OP_CATALOG.md", "fullseye/OP_CATALOG.md"),
                     "py -3.11 tools/gen_op_catalog.py")


def test_sensor_playbook_matches_generator_no_drift():
    """docs/SENSOR_PLAYBOOK.md == tools/gen_sensor_playbook.py output, and every op the
    curated sensor->pipeline map names resolves in the ops3d registry (no '(未登録)')."""
    import gen_sensor_playbook as SP
    md, unresolved = SP.build()
    assert not unresolved, f"SENSOR_PLAYBOOK names ops that are not registered: {unresolved}"
    assert "(未登録" not in md
    _assert_no_drift(md, ("docs/SENSOR_PLAYBOOK.md", "fullseye/SENSOR_PLAYBOOK.md"),
                     "py -3.11 tools/gen_sensor_playbook.py")


# --------------------------------------------------------------------------- #
# ガイドの二種(2026-09-05)
#
# **族ガイド** —— ファイル名が族名と一致し、その族の全 op ノートから自動リンク
# される(2-D は ``gallery2d_*``、ledger 次元は :data:`opdocs.LEDGER_DIMS` の
# ``family``)。ここまで math と optics にだけ双子のテストがあり、コード側の
# コメントが「3 つ目の ledger 次元が来たら一般化せよ」と書いていた。ledger 次元は
# 21 に増えたので、ここで**全次元へ一般化**して双子を畳んだ。
#
# **背景知識ガイド** —— 族に属さない横断的な教材(測色、深度センサ、計測の
# 不確かさ、データセット規約 …)。frontmatter の ``applies_to`` に書いた
# ``<dim>`` / ``<dim>/<category>`` の op ノートからリンクされる。この配線が
# 無かったあいだ、知識ガイドは INDEX にしか出ず **op から辿る経路が一本も無かった**。
# --------------------------------------------------------------------------- #
_LEDGER_GUIDES = [(dim, meta["family"],
                   os.path.join(ROOT, "docs", "ops", dim, "guides", meta["family"] + ".md"))
                  for dim, meta in OD.LEDGER_DIMS.items()]
_AUTHORED_LEDGER_GUIDES = [t for t in _LEDGER_GUIDES if os.path.exists(t[2])]
_LEDGER_IDS = [d for d, _, _ in _AUTHORED_LEDGER_GUIDES]


@pytest.mark.parametrize("dim,fam,path", _AUTHORED_LEDGER_GUIDES, ids=_LEDGER_IDS)
def test_ledger_family_guide_is_well_formed(dim, fam, path):
    """すべての ledger 族ガイドを 2-D ギャラリーガイドと同じ水準で見る。

    要求: frontmatter / 著者 / mermaid のパイプライン図 / 実行できる python /
    自分の族の op を実際に名指ししていること(一般論で埋めていないこと)。
    op を名指しする本数の下限は、族の大きさで 2 段(小さい族 3、30 op 以上は 12)
    —— これは畳む前の math(3)と optics(12)の水準をそのまま残したもの。
    """
    with open(path, encoding="utf-8") as f:
        md = f.read()
    assert md.lstrip().startswith("---"), f"{fam}: missing YAML frontmatter"
    assert "Kazufumi Furuse" in md, f"{fam}: missing author/copyright"
    assert "```mermaid" in md, f"{fam}: missing a mermaid pipeline diagram"
    assert "```python" in md, f"{fam}: missing a runnable python snippet"
    meta = OD.LEDGER_DIMS[dim]
    table = getattr(__import__(meta["registry"]), meta["table"])
    hit = {n for n in table if re.search(r"(?<![\w])" + re.escape(n) + r"(?![\w])", md)}
    need = 3 if len(table) < 30 else 12
    assert len(hit) >= need, (
        f"{fam} names too few of its own ops ({len(hit)}/{len(table)}, need {need})")


@pytest.mark.parametrize("dim,fam,path", _AUTHORED_LEDGER_GUIDES, ids=_LEDGER_IDS)
def test_ledger_notes_link_their_family_guide(dim, fam, path):
    """族ガイドがある次元では、その次元の全 op ノートから辿れること。"""
    unlinked = []
    for r in (x for x in _RECS if x["dim"] == dim):
        with open(OD._op_path(r), encoding="utf-8") as f:
            if f"../guides/{fam}.md" not in f.read():
                unlinked.append(r["name"])
    assert not unlinked, f"{dim} notes without a family-guide link: {unlinked[:20]}"


#: 一次情報の URL も「症状→原因」の診断表もまだ持たない知識ガイド。**書いた時期が
#: 技術移転の水準を決める前**で、記憶から書かれている可能性がある(この repo は
#: 手入力で 4 件の誤記を出した前科がある)。下げた基準で通すのではなく、
#: **隠さず並べて**埋まった順に外す。
_KNOWLEDGE_GUIDES_PENDING_SOURCES = {
    "mv_cables", "mv_cameras", "mv_frame_grabbers", "mv_image_sensors",
    "mv_standards", "virtual_machine_vision",
}
_KNOWLEDGE_STEMS = [g["stem"] for g in OD.knowledge_guides()]


def test_knowledge_guides_are_wired_or_explicitly_opted_out():
    """``applies_to`` の書き忘れが無いこと(``none`` は意図的な非配線の宣言)。"""
    unwired = OD.guides_not_wired()
    assert not unwired, (
        "背景知識ガイドに applies_to が無く、どの op ノートからも辿れない: "
        + ", ".join(unwired) + "  (繋ぐ先が無いなら `applies_to: none` と明記する)")


def test_knowledge_guide_targets_all_exist():
    """``applies_to`` の綴り違いを黙って無視しないこと。"""
    bad = OD.guides_with_unknown_targets()
    assert not bad, f"applies_to が実在しない dim/category を指している: {bad}"


def test_wired_knowledge_guides_reach_at_least_one_op():
    """配線した知識ガイドは、実際に 1 枚以上の op ノートから辿れること。"""
    orphan = []
    for g in OD.knowledge_guides():
        if not g["applies_to"]:
            continue
        if not any(g in OD.guides_for(r["dim"], r["category"]) for r in _RECS):
            orphan.append(g["stem"])
    assert not orphan, f"applies_to を持つのに届く op が 0 枚: {orphan}"


@pytest.mark.parametrize("stem", _KNOWLEDGE_STEMS)
def test_knowledge_guide_is_well_formed(stem):
    """背景知識ガイドの水準 —— 族ガイドとは**別の**基準で見る。

    族ガイドが「op の使い方」を教えるのに対し、知識ガイドは **op の手前にある
    物理と規約**を教える。したがって mermaid や python ではなく、
    **一次情報の出典**と**症状→原因の診断表**を持つことを要求する
    (「誰でも同じ仕事がこなせる」ための最小要件)。
    """
    g = next(x for x in OD.knowledge_guides() if x["stem"] == stem)
    with open(g["path"], encoding="utf-8") as f:
        md = f.read()
    assert md.lstrip().startswith("---"), f"{stem}: missing YAML frontmatter"
    assert "Kazufumi Furuse" in md, f"{stem}: missing author"
    assert "applies_to:" in md.split("---")[1], f"{stem}: frontmatter has no applies_to"
    if g["spec"] == "none" or stem in _KNOWLEDGE_GUIDES_PENDING_SOURCES:
        return
    assert "| 症状" in md, f"{stem}: 診断表(症状→原因)が無い"
    assert "http" in md, f"{stem}: 一次情報の URL が 1 本も無い"


def test_every_guide_has_a_studio_help_page():
    """ガイドは種類を問わず Studio ヘルプに出ること。

    ``cmd_html`` の dim ループから ``3d`` が抜けており、``docs/ops/3d/guides/`` の
    ガイドは Studio ヘルプに 1 枚も出ていなかった(2026-09-05 に depth_sensors を
    書いて発覚)。同じ抜けを二度作らないための検査。
    """
    missing = []
    for p in sorted(glob.glob(os.path.join(ROOT, "docs", "ops", "*", "guides", "*.md"))):
        stem = os.path.splitext(os.path.basename(p))[0]
        page = os.path.join(ROOT, "studio_assets", "op_help", "guide_" + stem + ".html")
        if not os.path.exists(page):
            missing.append(stem)
    assert not missing, f"guides with no Studio help page: {missing}"


def test_guide_stems_are_unique_across_dims():
    """ヘルプページは ``guide_<stem>.html`` の平坦な名前空間を共有するので、
    次元をまたいで stem が衝突すると**片方が黙って上書きされる**。"""
    seen = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "docs", "ops", "*", "guides", "*.md"))):
        stem = os.path.splitext(os.path.basename(p))[0]
        seen.setdefault(stem, []).append(os.path.relpath(p, ROOT))
    dupes = {k: v for k, v in seen.items() if len(v) > 1}
    assert not dupes, f"guide stem collisions (flat guide_ namespace): {dupes}"


def test_every_generated_help_page_is_reachable_from_studio():
    """生成した op ヘルプは**すべて Studio から開ける**こと。

    2026-09-05: `opdocs.py html` は ledger 21 族ぶんの 494 枚を
    ``op_help/<dim>/`` に書いていたが、Studio のヘルプ画面は 2-D と 3-D しか
    捌いておらず、**生成して同梱しているのに 1 枚も開けなかった**。
    「仕組みはあるが経路が通っていない」型なので、経路そのものを検査で固定する。
    """
    import studio
    root = os.path.join(ROOT, "studio_assets", "op_help")
    unreachable = []
    for dim in sorted(os.listdir(root)):
        d = os.path.join(root, dim)
        if not os.path.isdir(d):
            continue
        pages = [f for f in sorted(os.listdir(d)) if f.endswith(".html") and f.count(".") == 1]
        if not pages:
            continue
        # 各次元の先頭・中間・末尾を代表として引く(全数だと I/O が重い)
        for f in {pages[0], pages[len(pages) // 2], pages[-1]}:
            op = f[:-5]
            html = studio.op_help_html(op, "en", None, dim)
            if not html or len(html) < 400:
                unreachable.append("%s/%s" % (dim, op))
    assert not unreachable, ("生成済みヘルプが Studio から開けない: " + ", ".join(unreachable))


def test_help_lookup_honours_the_selected_language():
    """``<op>.<lang>.html`` があればそれを、無ければ既定の頁を返すこと。

    2026-09-05 まで 3-D と ledger の経路には ``lang`` 引数が無く、**ユーザーが選んだ
    言語が黙って無視されていた**。翻訳を入れる前に、選択が届くことを固定しておく。
    """
    import studio
    root = os.path.join(ROOT, "studio_assets", "op_help")
    probe = os.path.join(root, "3d", "_i18n_probe.html")
    probe_en = os.path.join(root, "3d", "_i18n_probe.en.html")
    try:
        with open(probe, "w", encoding="utf-8") as f:
            f.write("<p>BASE</p>")
        with open(probe_en, "w", encoding="utf-8") as f:
            f.write("<p>ENGLISH</p>")
        assert "ENGLISH" in studio.op_help_html("_i18n_probe", "en", None, "3d")
        assert "BASE" in studio.op_help_html("_i18n_probe", "ja", None, "3d")   # ja 版は無い
        # ledger 次元でも同じ規則が効く
        led = os.path.join(root, "math", "_i18n_probe.zh.html")
        with open(os.path.join(root, "math", "_i18n_probe.html"), "w", encoding="utf-8") as f:
            f.write("<p>BASE</p>")
        with open(led, "w", encoding="utf-8") as f:
            f.write("<p>CHINESE</p>")
        assert "CHINESE" in studio.op_help_html("_i18n_probe", "zh", None, "math")
    finally:
        for q in (probe, probe_en, os.path.join(root, "math", "_i18n_probe.html"),
                  os.path.join(root, "math", "_i18n_probe.zh.html")):
            if os.path.exists(q):
                os.remove(q)


# ------------------------------------------------------------------ #
# i18n — ヘルプの「枠」の対訳(ja / en / zh / tw / ko / de)
# ------------------------------------------------------------------ #
_TARGET_LANGS = [c for c in OD.LANGS if c != "ja"]


def test_chrome_translation_table_has_no_holes():
    """生成器が実際に引く固定文言が、全ターゲット言語で訳されていること。

    表に**引かれない古い行**があっても構わないが、**引かれるのに訳が無い行**は
    「訳したつもりで日本語が出る」なので許さない。OD.SEEN_STRINGS は生成を 1 周
    走らせた実測なので、この 2 つを取り違えない。
    """
    by = {(r["dim"], r["name"]): r for r in _RECS}
    for rec in _RECS:                                   # 1 周まわして原文を集める
        for lang in _TARGET_LANGS:
            OD._op_md(rec, OD._op_path(rec), by, lang=lang)
    OD.T("このガイドは日本語のみです(人が書いた散文なので機械的な差し替えをしていません)。", "en")
    missing = OD.untranslated_strings()
    assert not missing, ("枠の対訳に穴がある: "
                         + "; ".join("%s=%d 件" % (k, len(v)) for k, v in missing.items()))


def test_chrome_translation_keys_are_real_source_strings():
    """対訳表のキーは**生成器のソースにある原文そのもの**であること。

    キーが 1 文字でもずれると、その行は永久に引かれない(=黙って日本語のまま出る)。
    表が肥大しても気づけないので、キー側を実ソースと突き合わせる。
    """
    import ast
    src = open(os.path.join(ROOT, "tools", "opdocs.py"), encoding="utf-8").read()
    lits = {n.value for n in ast.walk(ast.parse(src))
            if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    with open(os.path.join(ROOT, "docs", "i18n", "opdocs.json"), encoding="utf-8") as f:
        tbl = json.load(f)["strings"]
    orphan = sorted(k for k in tbl if k not in lits)
    assert not orphan, ("対訳表のキーが生成器の原文と一致しない(この行は永久に使われない): "
                        + ", ".join(repr(k[:60]) for k in orphan))


#: 言語版を**あえて作らない** op —— 手書きの上書きページがあるもの。これらは英語で
#: 書かれていて `sample:` で実行可能なパイプラインまで載せており、生成訳を横に置くと
#: 言語を選んだ瞬間に中身の薄いほうへ差し替わる(2026-09-05 実測)。
_HAND_AUTHORED_HELP = {"gaussian", "otsu", "sobel_mag"}


def test_hand_authored_help_is_not_shadowed_by_a_translation():
    """手書きヘルプの横に生成訳を置かないこと(訳が本家より貧しくなるなら出さない)。"""
    root = os.path.join(ROOT, "studio_assets", "op_help")
    import studio
    for op in sorted(_HAND_AUTHORED_HELP):
        base = os.path.join(root, op + ".html")
        assert os.path.exists(base), op
        assert OD._GEN_MARK not in open(base, encoding="utf-8").read(200), (
            "%s が生成物で上書きされた(手書きの上書きページが消えている)" % op)
        for lang in _TARGET_LANGS:
            sib = os.path.join(root, "%s.%s.html" % (op, lang))
            assert not os.path.exists(sib), ("%s が手書きページを覆い隠している" % sib)
        # 言語を選んでも中身の濃い手書き頁が出続けること(実行できるサンプルつき)
        for lang in ("en", "ko"):
            assert "sample:" in studio.op_help_html(op, lang,
                                                    {"in_sort": "image", "out_sort": "image"})
        assert studio.help_lang_bar(op, "2d", "en") == ""   # 選べない導線は出さない


def test_every_op_help_page_ships_in_every_language():
    """全 op に全言語のヘルプ頁があること(片言語だけ欠ける、を作らない)。"""
    root = os.path.join(ROOT, "studio_assets", "op_help")
    missing = []
    for rec in _RECS:
        if rec["dim"] == "2d" and rec["name"] in _HAND_AUTHORED_HELP:
            continue
        d = root if rec["dim"] == "2d" else os.path.join(root, rec["dim"])
        for lang in _TARGET_LANGS:
            if not os.path.exists(os.path.join(d, "%s.%s.html" % (rec["name"], lang))):
                missing.append("%s/%s.%s" % (rec["dim"], rec["name"], lang))
    assert not missing, ("翻訳ヘルプが欠けている(%d 件) 例: %s "
                         "— `py -3.11 tools/opdocs.py html` を実行"
                         % (len(missing), ", ".join(missing[:8])))


@pytest.mark.parametrize("lang", _TARGET_LANGS)
def test_translated_help_is_generated_from_the_generator_no_drift(lang):
    """同梱の翻訳頁が、いまの生成器の出力と一致すること(次元ごとに標本抽出)。

    全 8610 枚を毎回作り直すと重いので、次元ごとに 1 枚ずつ引く。ズレたら
    `tools/opdocs.py html` を回し忘れている。
    """
    by = {(r["dim"], r["name"]): r for r in _RECS}
    seen, bad = set(), []
    for rec in sorted(_RECS, key=lambda r: (r["dim"], r["name"])):
        if rec["dim"] in seen:
            continue
        seen.add(rec["dim"])
        p = OD._op_path(rec)
        d = (os.path.join(ROOT, "studio_assets", "op_help")
             if rec["dim"] == "2d"
             else os.path.join(ROOT, "studio_assets", "op_help", rec["dim"]))
        f = os.path.join(d, "%s.%s.html" % (rec["name"], lang))
        want = OD._anchor_rewrite(OD.md_to_html(OD._op_md(rec, p, by, lang=lang)), rec["dim"])
        with open(f, encoding="utf-8") as fh:
            got = fh.read()
        if got != OD._GEN_MARK + "\n" + want:
            bad.append("%s/%s" % (rec["dim"], rec["name"]))
    assert not bad, ("翻訳ヘルプが生成器とずれている(%s): %s" % (lang, ", ".join(bad)))


def rec_is_japanese_body(rec):
    """詳細説明の本文が日本語か(= どの読み手にとっても原文のままになる op)。"""
    return OD.has_japanese(OD.summary_and_rest(rec.get("doc"))[1])


def test_notice_when_nothing_is_translated():
    """要約の訳が**無い**op には「まだ訳がありません」が出ること。

    いまは 935/935 が訳済みなので実データでは起きない。起きたときに黙って
    日本語が出ないことを、生成器を直接呼んで固定する(将来 op を足した瞬間に
    通る道なので、実データが無いからと検査ごと消さない)。
    """
    by = {(r["dim"], r["name"]): r for r in _RECS}
    rec = dict(next(r for r in _RECS if OD.summary_and_rest(r.get("doc"))[0]))
    rec["name"] = "_untranslated_probe_"          # 対訳表に載っていない名前
    md = OD._op_md(rec, OD._op_path(rec), by, lang="en", verbatim_doc=False)
    with open(os.path.join(ROOT, "docs", "i18n", "opdocs.json"), encoding="utf-8") as f:
        tbl = json.load(f)["strings"]
    head = tbl["> この op の説明はまだ訳がありません。原文をそのまま載せます。"]["en"]
    assert head.lstrip("> ")[:30] in md


def test_translated_pages_say_plainly_what_is_not_translated():
    """訳の無い散文を**訳したふりで**出さないこと。

    枠だけ訳して本文が日本語のとき、その旨の 1 行が必ず入る。これが無いと読者は
    「英語版のはずなのに日本語」を不具合と受け取る(あるいは訳だと誤解する)。
    """
    with open(os.path.join(ROOT, "docs", "i18n", "opdocs.json"), encoding="utf-8") as f:
        tbl = json.load(f)["strings"]
    # 要約は全 935 本が 6 言語そろったが、**詳細説明の本文は原文のまま**。
    # 「要約と見出しは訳した、以下は原文」と頁が自分で言うことを固定する
    # (要約すら無い場合の断り書きは下の test_notice_when_nothing_is_translated)。
    notice = tbl["> 以下の詳細説明は原文のままです —— 要約と見出しは訳出済み。"]
    root = os.path.join(ROOT, "studio_assets", "op_help")
    rec = next(r for r in _RECS
               if OD.summary_and_rest(r.get("doc"))[1]          # 本文がある
               and OD.op_summary(r, "en")[1]                    # 要約は訳済み
               and rec_is_japanese_body(r))
    d = root if rec["dim"] == "2d" else os.path.join(root, rec["dim"])
    for lang in _TARGET_LANGS:
        with open(os.path.join(d, "%s.%s.html" % (rec["name"], lang)), encoding="utf-8") as f:
            html = f.read()
        import html as _h
        head = _h.escape(notice[lang].lstrip("> ")[:24])   # 頁側は escape 済み
        assert head in html, ("%s の %s 版に『未訳』の断り書きが無い" % (rec["name"], lang))


def test_no_stale_summary_translation_is_shipped():
    """原文が変わった要約訳を**出さない**こと(指紋で検出し、日本語へ戻す)。

    古い訳が黙って残るのが翻訳で一番たちが悪い。ここが赤いときは訳を更新するか
    該当行を消す —— 指紋だけ合わせる更新は禁止(それは訳の更新ではない)。
    """
    stale = OD.op_summary_stale()
    assert not stale, ("原文と指紋が合わない要約訳(古い訳): " + ", ".join(stale[:12]))


def test_help_language_bar_only_offers_languages_that_exist():
    """言語の導線は**実在する頁だけ**を出し、現在地を現在地として示すこと。"""
    import studio
    rec = _RECS[0]
    langs = studio.help_langs_available(rec["name"], rec["dim"])
    assert langs[0] == "ja" and set(_TARGET_LANGS) <= set(langs)
    bar = studio.help_lang_bar(rec["name"], rec["dim"], "ko")
    assert 'href="lang:en"' in bar and 'href="lang:ko"' not in bar   # 現在地はリンクにしない
    assert "<b" in bar and "한국어" in bar
    # 存在しない op には導線を出さない(押せないリンクを作らない)
    assert studio.help_lang_bar("_no_such_op_", "2d") == ""


def test_studio_ui_language_menu_and_help_agree():
    """UI の言語メニューとヘルプの言語が同じ集合であること。

    i18n.json に足せば増える、という約束をコード側が破っていた(``apply_language``
    に固定の許可リストがあり、メニューに出るのに選ぶと英語へ戻る言語があった)。
    """
    import studio
    assert set(studio.LANGUAGES) == set(OD.LANGS), (
        "Studio の languages と opdocs.LANGS が食い違う: %s vs %s"
        % (sorted(studio.LANGUAGES), sorted(OD.LANGS)))
    src = open(os.path.join(ROOT, "studio.py"), encoding="utf-8").read()
    assert 'lang in ("en", "ja", "zh")' not in src, (
        "apply_language に固定の言語許可リストが戻っている")


#: UI 表は**英語がキー**(ベース言語)なので en 行は存在しない —— 訳を数えるのは残り。
_UI_TARGET_LANGS = [c for c in OD.LANGS if c not in ("en",)]


@pytest.mark.parametrize("lang", _UI_TARGET_LANGS)
def test_studio_ui_strings_are_translated(lang):
    """Studio の UI 文字列・ツールチップが全言語ぶんそろっていること。

    2026-09-05 実測: `strings` は ja しか持っておらず、中文を選んでも 43 個の
    メニュー項目が英語のままだった(表があるのに埋まっていない、の型)。
    """
    with open(os.path.join(ROOT, "studio_assets", "i18n.json"), encoding="utf-8") as f:
        d = json.load(f)
    for key in ("strings", "tooltips"):
        miss = sorted(k for k, v in d[key].items() if not (v or {}).get(lang))
        assert not miss, ("%s に %s の訳が無い(%d 件) 例: %s"
                          % (key, lang, len(miss), ", ".join(repr(m[:40]) for m in miss[:5])))
    assert d["guide"].get(lang), "クイックガイドに %s 版が無い" % lang


def test_ledger_help_pages_ship_in_the_wheel():
    """台帳族と翻訳頁が package-data の glob に載っていること。

    2026-09-05 実測: `op_help/3d/*.html` しか挙げていなかったので、生成して
    コミット済みの台帳ヘルプ 494 枚は **wheel に 1 枚も入っていなかった**。
    """
    with open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8") as f:
        toml = f.read()
    assert '"op_help/*/*.html"' in toml, (
        "package-data が op_help のサブディレクトリを網羅していない"
        "(台帳族 21 個と翻訳頁が wheel から落ちる)")


def test_locale_tags_map_to_the_shipped_language_codes():
    """OS/ブラウザの標準タグ(BCP 47)が同梱の言語コードへ落ちること。

    台湾向け繁体字はファイル名を 2 文字にそろえて ``tw`` にしてあるが、``tw`` は
    本来 ISO 639-1 で Twi 語の記号なので、外から来るタグは必ず対応表を通す。
    """
    assert OD.normalize_lang("zh-TW") == "tw"
    assert OD.normalize_lang("zh-Hant") == "tw"
    assert OD.normalize_lang("zh-CN") == "zh"
    assert OD.normalize_lang("de-LU") == "de"          # 未知の地域は主部分へ
    assert OD.normalize_lang("fr") == "en"             # 未対応は英語へ
    for code in OD.LANGS:
        assert OD.normalize_lang(code) == code


def test_japanese_is_a_translation_target_too():
    """原文が英語の op に**日本語のヘルプ**があること。

    2026-09-05 実測: 要約 935 本のうち **349 本は原文が英語**で、日本語のヘルプを
    開いても英語のままだった。``ja`` を「原文だから常に OK」と数えていたのが誤りで、
    内訳は ja 586 / en 373 / 他 各 50 だった。``ja`` も翻訳先の 1 つとして数える。
    """
    root = os.path.join(ROOT, "studio_assets", "op_help")
    missing, extra = [], []
    for rec in _RECS:
        src = OD.summary_and_rest(rec.get("doc"))[0]
        if not src or rec["name"] in _HAND_AUTHORED_HELP:
            continue
        d = root if rec["dim"] == "2d" else os.path.join(root, rec["dim"])
        p = os.path.join(d, "%s.ja.html" % rec["name"])
        if OD.has_japanese(src):
            # 原文が日本語 —— ノートと同じ中身の兄弟を並べても情報は増えない
            if os.path.exists(p):
                extra.append("%s/%s" % (rec["dim"], rec["name"]))
        elif not os.path.exists(p):
            missing.append("%s/%s" % (rec["dim"], rec["name"]))
    assert not missing, ("原文が英語なのに日本語ヘルプが無い(%d 件) 例: %s"
                         % (len(missing), ", ".join(missing[:8])))
    assert not extra, ("原文が日本語なのに冗長な ja 兄弟がある(%d 件) 例: %s"
                       % (len(extra), ", ".join(extra[:8])))


def test_every_summary_is_readable_in_japanese():
    """全 op の要約が**日本語で読める**こと(原文が日本語か、訳があるか)。

    ここが赤いときは `docs/i18n/op_summary.json` に ``ja`` を足す。数字ではなく
    op を名指しで出すので、どれが残っているかがそのまま作業リストになる。
    """
    unreadable = [("%s/%s" % (r["dim"], r["name"]))
                  for r in _RECS
                  if OD.summary_and_rest(r.get("doc"))[0] and not OD.op_summary(r, "ja")[1]]
    assert not unreadable, ("要約が日本語で読めない op が %d 件: %s"
                            % (len(unreadable), ", ".join(unreadable[:12])))


def test_summary_translations_stay_the_readers_language():
    """要約の訳が、その言語で書かれていること(原文をそのまま貼っていないか)。

    「訳した」と表に書いてあるのに中身が原文のままだと、指紋も一致するので
    永久に気づけない。日本語訳に日本語が 1 文字も無い、といった取り違えを弾く。
    """
    bad = []
    for r in _RECS:
        src = OD.summary_and_rest(r.get("doc"))[0]
        if not src or OD.has_japanese(src):
            continue
        tr, ok = OD.op_summary(r, "ja")
        if ok and not OD.has_japanese(tr):
            bad.append("%s/%s" % (r["dim"], r["name"]))
    assert not bad, ("日本語訳のはずが日本語を含まない: " + ", ".join(bad[:12]))
