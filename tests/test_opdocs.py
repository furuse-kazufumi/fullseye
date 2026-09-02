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
_MATH_GUIDE = os.path.join(ROOT, "docs", "ops", "math", "guides", "math_metrology.md")


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


def test_math_family_guide_is_well_formed():
    """The maths family has one authored usage guide, held to the same bar as the
    2-D gallery guides: frontmatter, author, a mermaid diagram, a runnable python
    snippet, and grounded mentions of its own ops."""
    assert os.path.exists(_MATH_GUIDE), "docs/ops/math/guides/math_metrology.md missing"
    with open(_MATH_GUIDE, encoding="utf-8") as f:
        md = f.read()
    assert md.lstrip().startswith("---"), "math guide: missing YAML frontmatter"
    assert "Kazufumi Furuse" in md, "math guide: missing author/copyright"
    assert "```mermaid" in md, "math guide: missing a mermaid pipeline diagram"
    assert "```python" in md, "math guide: missing a runnable python snippet"
    import opsmath
    hit = {n for n in opsmath.OPSMATH
           if re.search(r"(?<![\w])" + re.escape(n) + r"(?![\w])", md)}
    assert len(hit) >= 3, f"math guide names too few of its own ops ({len(hit)}/{len(opsmath.OPSMATH)})"


def test_math_notes_link_their_family_guide():
    """Every math note points at the family guide (the AI-usage entry point)."""
    unlinked = []
    for r in _MATH_RECS:
        with open(OD._op_path(r), encoding="utf-8") as f:
            if "../guides/math_metrology.md" not in f.read():
                unlinked.append(r["name"])
    assert not unlinked, f"math notes without a family-guide link: {unlinked}"


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
_OPT_GUIDE = os.path.join(ROOT, "docs", "ops", "optics", "guides",
                          "optics_imaging.md")


def test_optics_registry_is_connected():
    """Every op in the opsoptics ledger flows into the docs corpus (and only those)."""
    import opsoptics
    have = {r["name"] for r in _OPT_RECS}
    assert have == set(opsoptics.OPSOPTICS), (
        "docs corpus and opsoptics ledger disagree: "
        f"only-in-docs={have - set(opsoptics.OPSOPTICS)}, "
        f"only-in-ledger={set(opsoptics.OPSOPTICS) - have}")
    assert len(_OPT_RECS) == 30                 # optics 18 + raytrace "design" 12
    assert {"geometric", "wave", "imaging", "polarization", "design"} == {
        r["category"] for r in _OPT_RECS}
    # the design notes must say where their implementation lives (raytrace, not optics)
    for r in _OPT_RECS:
        if r["category"] == "design":
            assert r["module"] == "raytrace", (r["name"], r["module"])


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


def test_optics_family_guide_is_well_formed():
    assert os.path.exists(_OPT_GUIDE), "docs/ops/optics/guides/optics_imaging.md missing"
    with open(_OPT_GUIDE, encoding="utf-8") as f:
        md = f.read()
    assert md.lstrip().startswith("---"), "optics guide: missing YAML frontmatter"
    assert "Kazufumi Furuse" in md, "optics guide: missing author/copyright"
    assert "```mermaid" in md, "optics guide: missing a mermaid pipeline diagram"
    assert "```python" in md, "optics guide: missing a runnable python snippet"
    import opsoptics
    hit = {n for n in opsoptics.OPSOPTICS
           if re.search(r"(?<![\w])" + re.escape(n) + r"(?![\w])", md)}
    assert len(hit) >= 12, (
        f"optics guide names too few of its own ops ({len(hit)}/{len(opsoptics.OPSOPTICS)})")


def test_optics_notes_link_their_family_guide():
    unlinked = []
    for r in _OPT_RECS:
        with open(OD._op_path(r), encoding="utf-8") as f:
            if "../guides/optics_imaging.md" not in f.read():
                unlinked.append(r["name"])
    assert not unlinked, f"optics notes without a family-guide link: {unlinked}"


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
