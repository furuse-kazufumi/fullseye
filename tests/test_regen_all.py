# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""`tools/regen_all.py` の表が現実から遅れないための門(2026-09-09)。

`regen_all` は「生成物の回し忘れ」を潰すために作った。ところがその CHAIN 自体を
**人が手で選んでいた**ので、同じ失敗が一段上で再発した —— `gen_examples3d_doc`
が漏れ、`docs/EXAMPLES_3D.md` は `ops3d = 347 op` と書いたまま古びていた
(実際は 357)。`tools/` の外にある `imgevolve.py index`(`docs/OP_INDEX.json`)と
`conversion_matrix.py`(`docs/CONVERSION_MATRIX.md`)も同じ理由で外れていた。

**手で書く表は、門を付けない限り必ず遅れる。** だからここでは
「ファイルを書くスクリプト」を**ディレクトリの側から**列挙し、その 1 本 1 本が
3 つの表のどれかに載っていることを要求する:

  * ``CHAIN``           —— 回すもの(``--check`` の対象)
  * ``EXCLUDED``        —— 生成器だが門にできないもの(**理由を書く**)
  * ``NOT_A_GENERATOR`` —— そもそも生成器でないもの(ベンチ・門・公開スクリプト)

新しい生成器を足した人は、どれかに分類することを迫られる。どれでもよいが、
**黙って増やすことだけができない。**
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import regen_all as RA  # noqa: E402


def test_every_generator_is_classified():
    """CHAIN / EXCLUDED / NOT_A_GENERATOR のどれにも無い生成器があれば落ちる。"""
    rest = RA.unclassified()
    assert not rest, (
        "分類されていない生成器が %d 本: %s —— "
        "回すなら CHAIN に、回せないなら EXCLUDED に**理由つきで**、"
        "生成器でないなら NOT_A_GENERATOR に入れてください "
        "(tools/regen_all.py)" % (len(rest), ", ".join(rest)))


def test_the_discovery_actually_finds_things():
    """列挙が空になったら門は無言で通る —— 「一致の門は空を通す」の型を封じる。

    印を緩めて 0 本にすれば `test_every_generator_is_classified` は永遠に緑。
    実測の下限を置いて、それが起きたら気づけるようにする。
    """
    found = RA.discover_generators()
    assert len(found) >= 120, (
        "生成器の列挙が %d 本しか返さない(2026-10-07 の実測は 145 本)—— "
        "_WRITES の印か探す場所が壊れていないか" % len(found))
    # 探す場所ごとに 1 本ずつ、実在の生成器が釣れていること(どの層が黙って落ちても気づく)。
    for must, why in (
            ("imgevolve.py", "repo 直下の生成器"),
            ("samples.py", "repo 直下の生成器(2026-10-07 まで見えず docs/EXAMPLES.md が 67-op のまま)"),
            ("tools/impl2/knob_probe.py", "tools/ の下の階層"),
            ("tools/gen_banner.py", "画像の書き手(PIL の .save)"),
            ("assets/make_icon.py", "assets/ の生成器"),
    ):
        assert must in found, "%s(%s)が列挙から落ちている" % (must, why)
    # ライブラリ(__main__ 無し)は repo 直下にあっても生成器ではない。
    assert "imgio.py" not in found, "__main__ の無いライブラリを生成器として拾っている"


def test_excluded_entries_carry_a_reason():
    """除外は理由とセットでなければ、ただの黙殺と区別がつかない。"""
    thin = sorted(k for k, v in RA.EXCLUDED.items() if len(v.strip()) < 15)
    assert not thin, "除外の理由が短すぎる(なぜ門にできないかを書く): %s" % ", ".join(thin)


def test_chain_and_excluded_do_not_overlap():
    in_chain = {args[0] for args, _ in RA.CHAIN}
    both = sorted(in_chain & (set(RA.EXCLUDED) | set(RA.NOT_A_GENERATOR)))
    assert not both, "CHAIN と除外表の両方に載っている: %s" % ", ".join(both)


def test_classified_entries_still_exist():
    """消えたファイルの名前が表に残り続けると、表は嘘の台帳になる。"""
    missing = sorted(name for name in
                     (set(RA.EXCLUDED) | set(RA.NOT_A_GENERATOR)
                      | {args[0] for args, _ in RA.CHAIN})
                     if not os.path.isfile(os.path.join(ROOT, name)))
    assert not missing, "表に載っているのに実在しないファイル: %s" % ", ".join(missing)


# ---- 段の順序(2026-10-15)---------------------------------------------------------
#
# `gen_capabilities_index`(4 番目)が、16 番目でやっと作り直される `docs/OP_INDEX.json` を
# 先に読んでいた —— op を足すマージで索引に本線側を取ると止まる。洗い出すと同じ型の逆順が
# `gen_trust_block` ← 索引、`gen_docs_index_ops` ← 後ろの 7 段 にもあった。
# 順序は `READS` / `OUTPUTS` の表から静的に検査し、表そのものは regen_all を回すたびに
# audit hook の実測と突き合わせる(`trace_problems`)。

#: 2026-10-15 に直す前の並び(回帰の探針)。
_OLD_ORDER = [
    "gen_auto_specs_data.py", "tools/opdocs.py", "tools/gen_op_catalog.py",
    "tools/gen_capabilities_index.py", "tools/gen_hardening_index.py", "tools/audit_fallbacks.py",
    "tools/gen_maturity.py",
    "tools/gen_exhibit_numbers.py", "tools/gen_exhibit_glossary.py",
    "tools/gen_wingpoc_gallery.py", "tools/gen_examples_readme.py",
    "tools/gen_oss_landscape.py", "tools/gen_view2026_pages.py", "tools/gen_trust_block.py",
    "tools/gen_literature_counts.py", "tools/gen_docs_index_ops.py", "tools/gen_examples3d_doc.py",
    "tools/gen_sensor_playbook.py", "imgevolve.py", "tools/audit_file_formats.py", "tools/halcon_compat_profile.py", "catalog.py", "dispositions.py", "references.py", "samples.py",
    "tools/gen_mcp_data.py", "tools/gen_recipe_index.py", "tools/gen_recipe_retrieval_report.py", "tools/gen_rag_benchmark_report.py", "tools/conversion_matrix.py", "tools/gen_design_notes.py",
    "tools/gen_op_facets.py", "tools/measure_mcp_context.py",
    "tools/gen_doc_counts.py",
]


def _chain_order():
    return [args[0] for args, _ in RA.CHAIN]


def test_dependency_tables_are_sound():
    """表のキーが鎖と一致し、READS は他の段の出力を指し、OUTPUTS は実在のファイルに当たる。"""
    probs = RA.table_problems()
    assert not probs, "依存表が壊れている:\n  " + "\n  ".join(probs)


def test_no_stage_reads_what_a_later_stage_writes():
    """読む生成物を書く段が、読む段より**後ろ**にあってはならない(ORDER_EXEMPT を除く)。"""
    bad = RA.order_violations()
    assert not bad, "鎖の逆順:\n  " + "\n  ".join(
        "%s が %s を読むが、後ろの %s が書く" % (r, rp, w) for r, rp, w, _ in bad)


def test_the_order_gate_catches_the_old_order():
    """門は壊して確かめる: 直す前の並びを渡すと、見つけた逆順が**全部**出ること。"""
    assert sorted(_OLD_ORDER) == sorted(_chain_order()), "鎖の段が変わった —— _OLD_ORDER の探針を見直す"
    got = {(r, w) for r, _rp, w, _wp in RA.order_violations(_OLD_ORDER)}
    expect = {
        ("tools/gen_capabilities_index.py", "imgevolve.py"),
        ("tools/gen_trust_block.py", "imgevolve.py"),
        # 2026-10-22: 互換プロファイルは HALCON_PARITY.md を書き、旧順序では docs 索引がそれを先に読む。
        ("tools/gen_docs_index_ops.py", "tools/halcon_compat_profile.py"),
        # FILE_FORMATS.md は audit_file_formats が書き、docs 索引が文書地図へ載せる。
        ("tools/gen_docs_index_ops.py", "tools/audit_file_formats.py"),
            ("tools/gen_rag_benchmark_report.py", "tools/gen_op_facets.py"),
    } | {("tools/gen_docs_index_ops.py", w) for w in (
        "tools/gen_examples3d_doc.py", "tools/gen_sensor_playbook.py", "catalog.py",
        "references.py", "samples.py", "tools/conversion_matrix.py", "tools/gen_design_notes.py")}
    assert got == expect, "逆順の検出が食い違う: 余分 %s / 見落とし %s" % (
        sorted(got - expect), sorted(expect - got))


def test_the_order_gate_catches_a_single_swap():
    """1 段だけ戻しても赤になる(索引を能力索引の後ろへ)。"""
    order = _chain_order()
    order.remove("imgevolve.py")
    order.insert(order.index("tools/gen_capabilities_index.py") + 1, "imgevolve.py")
    bad = RA.order_violations(order)
    assert ("tools/gen_capabilities_index.py", "docs/OP_INDEX.json", "imgevolve.py",
            "docs/OP_INDEX.json") in bad


def test_the_literature_counts_stage_must_follow_the_notes_it_counts():
    """件数の打ち直しは docs/ops を数えるので、op ノートを書く opdocs より後ろでなければならない(壊して確かめる)。"""
    order = _chain_order()
    assert "tools/gen_literature_counts.py" in order
    assert not RA.order_violations(order)
    order.remove("tools/gen_literature_counts.py")
    order.insert(order.index("tools/opdocs.py"), "tools/gen_literature_counts.py")
    bad = RA.order_violations(order)
    assert bad
    assert any(r == "tools/gen_literature_counts.py" and w == "tools/opdocs.py" for r, _rp, w, _wp in bad), bad


def test_exemptions_are_not_a_blanket():
    """例外は名指しの (段, パターン) だけ。外すと、その組が違反として出ること。"""
    for (reader, rp) in list(RA.ORDER_EXEMPT):
        saved = RA.ORDER_EXEMPT.pop((reader, rp))
        try:
            assert any(r == reader and p == rp for r, p, _w, _wp in RA.order_violations()), (
                "例外 (%s, %r) は外しても違反にならない —— 要らない例外" % (reader, rp))
        finally:
            RA.ORDER_EXEMPT[(reader, rp)] = saved


def test_trace_problems_rejects_drift_between_table_and_code():
    """実測と表の突き合わせ(合成の実測で): 宣言に無い読み / 書き、読まなくなった宣言、
    出力に触れもしない段(conversion_matrix が `--md` 無しで 6 週間そうだった)。"""
    def clean():
        t = {}
        for s in _chain_order():
            outs = RA.OUTPUTS[s]
            touched = [p.replace("*", "x") for p in outs]
            reads = [p.replace("*", "x") for p in RA.READS.get(s, [])]
            t[s] = {"r": reads, "w": touched}
        return t

    assert RA.trace_problems(clean()) == []

    t = clean()
    t["tools/gen_capabilities_index.py"]["r"].append("docs/EXAMPLES.md")      # 宣言に無い読み
    probs = RA.trace_problems(t)
    assert probs, "宣言に無い読みを足したのに問題が 1 件も出ない"
    assert any("READS に無い生成物を読んだ: docs/EXAMPLES.md" in p for p in probs), probs

    t = clean()
    t["catalog.py"]["w"].append("docs/STRAY.md")                                # 宣言に無い書き
    probs = RA.trace_problems(t)
    assert probs, "宣言に無い書きを足したのに問題が 1 件も出ない"
    assert any("OUTPUTS に無いファイルを書いた: docs/STRAY.md" in p for p in probs), probs

    t = clean()
    t["tools/gen_capabilities_index.py"]["r"] = []                              # 読まなくなった宣言
    probs = RA.trace_problems(t)
    assert probs, "読みを消したのに問題が 1 件も出ない"
    assert any("1 本も読んでいない" in p for p in probs), probs

    t = clean()
    t["tools/conversion_matrix.py"] = {"r": [], "w": []}                        # 何も書かない段
    probs = RA.trace_problems(t)
    assert probs, "何も書かない段なのに問題が 1 件も出ない"
    assert any("tools/conversion_matrix.py: OUTPUTS の 'docs/CONVERSION_MATRIX.md' に触れもしない" in p
               for p in probs), probs


def test_trace_counts_cached_imports_as_the_module():
    """import は .py ではなく __pycache__ の .pyc を開く —— 生成された .py(auto_specs_data)を
    import で読む段を取りこぼさないよう、.pyc は元の .py として数える。"""
    pyc = os.path.join(ROOT, "__pycache__", "auto_specs_data.cpython-311.pyc")
    assert RA._rel_in_root(pyc) == "auto_specs_data.py"
    sub = os.path.join(ROOT, "tools", "__pycache__", "opdocs.cpython-312.pyc")
    assert RA._rel_in_root(sub) == "tools/opdocs.py"
    assert RA._rel_in_root(os.path.join(ROOT, "docs", "OP_INDEX.json")) == "docs/OP_INDEX.json"
    assert RA._rel_in_root(os.path.dirname(ROOT)) is None


def test_every_chain_stage_is_traced_for_real(tmp_path):
    """`--_trace` の入口が本当に open を拾うこと。木を書き換えないよう、`--md` を付けない
    conversion_matrix(要約を標準出力に出すだけ = 2026-10-15 まで鎖が回していた形)で走らせ、
    読みは記録され・書きは 0 で・表からは「出力に触れもしない段」として拒まれることを見る。"""
    import json
    import subprocess
    out = tmp_path / "t.json"
    env = dict(os.environ, PYTHONPATH=ROOT)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "regen_all.py"), "--_trace",
                        str(out), "tools/conversion_matrix.py"], cwd=ROOT, env=env,
                       capture_output=True, text=True, errors="replace")
    assert r.returncode == 0, r.stderr[-2000:]
    t = json.loads(out.read_text(encoding="utf-8"))
    assert t["w"] == [], "--md 無しの conversion_matrix は何も書かない(はず)"
    reads = t["r"]
    assert reads, "読みが 1 本も記録されていない —— hook が効いていない"
    assert any(p.endswith(".py") for p in reads), "読みに .py が無い —— import の記録が効いていない"
    # 表から見ると、これは「出力に触れもしない段」として拒まれる。
    probs = RA.trace_problems({**{s: {"r": [p.replace("*", "x") for p in RA.READS.get(s, [])],
                                      "w": [p.replace("*", "x") for p in RA.OUTPUTS[s]]}
                                  for s in _chain_order()},
                               "tools/conversion_matrix.py": t})
    assert probs, "出力に触れない段なのに問題が 1 件も出ない"
    assert any("conversion_matrix.py: OUTPUTS" in p and "触れもしない" in p for p in probs), probs


# ---- 書くかもしれない出力(2026-10-18)----------------------------------------------------
_THUMB = "docs/articles/assets/poc/poc_new_exhibit/01_scene_720.jpg"
_GALLERY = "tools/gen_wingpoc_gallery.py"


def _clean_traces():
    return {s: {"r": [p.replace("*", "x") for p in RA.READS.get(s, [])],
                "w": [p.replace("*", "x") for p in RA.OUTPUTS[s]]} for s in _chain_order()}


def test_conditional_thumbnail_passes_on_the_first_and_the_second_run():
    """図を初めて載せた回(サムネを書く)も、次の回(書かない)も、表と食い違わない。
    統合で 2 回踏んだ症状: 1 回目は「OUTPUTS に無いファイルを書いた」、OUTPUTS に足すと 2 回目に
    「触れもしない」で止まった。"""
    first = _clean_traces()
    first[_GALLERY]["w"].append(_THUMB)
    assert RA.trace_problems(first) == []
    assert RA.trace_problems(_clean_traces()) == []          # 2 回目: 書かない


def test_without_the_conditional_entry_the_first_run_is_rejected():
    """探針: MAY_OUTPUTS を外すと、1 回目(サムネを書く回)が止まる —— 直す前の症状が戻る。"""
    saved = RA.MAY_OUTPUTS.pop(_GALLERY)
    try:
        first = _clean_traces()
        first[_GALLERY]["w"].append(_THUMB)
        probs = RA.trace_problems(first)
        assert probs, "サムネを書いたのに問題が 1 件も出ない"
        assert any("OUTPUTS に無いファイルを書いた: " + _THUMB in p for p in probs), probs
    finally:
        RA.MAY_OUTPUTS[_GALLERY] = saved


def test_putting_the_thumbnail_in_outputs_fails_the_second_run():
    """探針: 必ず書く OUTPUTS に入れると、書かない回が「触れもしない」で止まる(MAY_OUTPUTS が要る理由)。"""
    pat = next(iter(RA.MAY_OUTPUTS[_GALLERY]))
    RA.OUTPUTS[_GALLERY].append(pat)
    try:
        second = _clean_traces()
        second[_GALLERY]["w"] = [w for w in second[_GALLERY]["w"] if not w.endswith("_720.jpg")]
        probs = RA.trace_problems(second)
        assert probs, "書かない回なのに問題が 1 件も出ない"
        assert any("触れもしない" in p and "_720.jpg" in p for p in probs), probs
    finally:
        RA.OUTPUTS[_GALLERY].remove(pat)


def test_conditional_outputs_are_not_a_blanket():
    """書くかもしれない出力は、その段のそのパターンだけ。別の段が書けば拒む / 同じ段でも別の
    ファイルは拒む / 表の側も、理由の無い・鎖に無い段・ファイル名が * だけ・OUTPUTS と重なる宣言を拒む。"""
    t = _clean_traces()
    t["catalog.py"]["w"].append(_THUMB)
    probs = RA.trace_problems(t)
    assert probs, "別の段がサムネを書いたのに問題が 1 件も出ない"
    assert any("catalog.py: OUTPUTS に無いファイルを書いた: " + _THUMB in p for p in probs), probs
    t = _clean_traces()
    t[_GALLERY]["w"].append("docs/articles/assets/poc/poc_new_exhibit/01_scene.png")
    probs = RA.trace_problems(t)
    assert probs, "宣言に無い PNG を書いたのに問題が 1 件も出ない"
    assert any("01_scene.png" in p for p in probs), probs
    for bad, needle in (({"tools/no_such.py": {"docs/x_720.jpg": "理由は十分に長い説明の文です"}}, "鎖に無い段"),
                        ({_GALLERY: {"docs/x_720.jpg": "短い"}}, "理由が短すぎる"),
                        ({_GALLERY: {"docs/articles/*": "理由は十分に長い説明の文です"}}, "* だけ"),
                        ({_GALLERY: {"docs/articles/exhibits/wingpoc.ja.md": "理由は十分に長い説明の文です"}},
                         "OUTPUTS と重なる")):
        saved = dict(RA.MAY_OUTPUTS)
        RA.MAY_OUTPUTS.clear()
        RA.MAY_OUTPUTS.update(bad)
        try:
            probs = RA.table_problems()
            assert probs, needle
            assert any(needle in p for p in probs), (needle, probs)
        finally:
            RA.MAY_OUTPUTS.clear()
            RA.MAY_OUTPUTS.update(saved)


def test_conditional_outputs_take_part_in_the_order_check():
    """書くかもしれない出力も、それを読む段より前で書かれなければならない(順序の門に入る)。"""
    RA.READS.setdefault("tools/gen_examples_readme.py", [])
    RA.READS["tools/gen_examples_readme.py"].append("docs/articles/assets/poc/*_720.jpg")
    try:
        order = _chain_order()
        order.remove(_GALLERY)
        order.append(_GALLERY)                      # サムネを書く段を読む段の後ろへ
        bad = RA.order_violations(order)
        assert bad, "サムネを読む段の後ろで書いても逆順にならない"
        assert any(r == "tools/gen_examples_readme.py" and w == _GALLERY for r, _rp, w, _wp in bad), bad
    finally:
        RA.READS["tools/gen_examples_readme.py"].remove("docs/articles/assets/poc/*_720.jpg")
        if not RA.READS["tools/gen_examples_readme.py"]:
            del RA.READS["tools/gen_examples_readme.py"]


def test_dirty_ignores_touched_but_identical_files(tmp_path, monkeypatch):
    """改行コードだけ・mtime だけの「変更」は食い違いに数えず、本当の変更は数える。"""
    import subprocess

    def git(*a):
        return subprocess.run(["git", *a], cwd=tmp_path, capture_output=True,
                              text=True, check=True)

    git("init", "-q")
    git("config", "user.email", "t@example.invalid")
    git("config", "user.name", "t")
    git("config", "core.autocrlf", "false")
    same = tmp_path / "same.txt"
    real = tmp_path / "real.txt"
    same.write_bytes(b"a\nb\n")
    real.write_bytes(b"x\n")
    git("add", ".")
    git("commit", "-q", "-m", "init")
    # 中身は同じまま書き直し(mtime が変わり、stat キャッシュは古くなる)。
    st = same.stat()
    same.write_bytes(b"a\nb\n")
    os.utime(same, (st.st_atime + 5, st.st_mtime + 5))
    real.write_bytes(b"y\n")
    (tmp_path / "new.txt").write_bytes(b"n\n")
    monkeypatch.setattr(RA, "_ROOT", str(tmp_path))
    lines = RA._dirty()
    assert len([ln for ln in lines if ln.endswith("same.txt")]) == 0, lines
    assert len([ln for ln in lines if ln.endswith("real.txt")]) == 1, lines
    assert len([ln for ln in lines if ln.startswith("??") and ln.endswith("new.txt")]) == 1, lines
    assert len(lines) == 2, lines


# ----------------------------------------------------------------------------- 2026-10-25
#: 印ごとに「その印が無いと釣れない実在の生成器」。2026-10-25 まで write_viewer( の生成器
#: (ViEW のビューア、題材の枝の tools/build_*_anim3d.py)がどの表にも載っていなかった。
_MARK_WITNESSES = (
    ("tools/build_view2026_viewers.py", r"\bwrite_viewer\(", "pv.write_viewer( で HTML を書く"),
    ("tools/fops_article/gen_ai_inputs.py", r'open\([^)]*,\s*(?:mode\s*=\s*)?["\'](?:w|wb|w\+|wb\+|a|ab|x|xb)["\']',
     'io.open(.., "wb") で PNG を書く'),
    ("tools/update_fullseye.py", r"\bshutil\.(?:copy|copy2|copyfile|copytree|move)\(", "shutil.copytree"),
)


def test_each_write_mark_catches_its_own_real_generator():
    """印を 1 つ消すと、その印でしか釣れない実在の生成器が列挙から落ちる —— だから印は消せない。"""
    import re

    found = RA.discover_generators()
    assert len(_MARK_WITNESSES) == 3
    for path, mark, why in _MARK_WITNESSES:
        assert path in found, "%s(%s)が列挙から落ちている —— _WRITES の印 %s が消えていないか" % (path, why, mark)
        assert mark in RA._WRITES.pattern, "_WRITES に印 %s が無い" % mark
        # その印を外した _WRITES では釣れない(= この印が要る)ことも確かめる。
        rest = RA._WRITES.pattern.replace("|" + mark, "").replace(mark + "|", "")
        assert rest != RA._WRITES.pattern
        src = open(os.path.join(ROOT, path), encoding="utf-8").read()
        assert re.search(mark, src) and not re.search(rest, src), (path, mark)


def test_write_viewer_generators_are_found_and_must_be_classified(tmp_path, monkeypatch):
    """pv.write_viewer( / fs.write_viewer( だけで HTML を書く tools/build_*_anim3d.py 型の生成器は
    列挙に載り、表に無ければ unclassified() に出る(= test_every_generator_is_classified が落ちる)。"""
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "build_demo_anim3d.py").write_text(
        "import pocviewer as pv\n\ndef main():\n    pv.write_viewer({}, 'docs/anim3d/demo.html', ['ja'])\n\n"
        "if __name__ == '__main__':\n    main()\n", encoding="utf-8")
    (tools / "build_demo2_viewer.py").write_text(
        "import fullseye as fs\nfs.write_viewer({}, 'x.html')\n", encoding="utf-8")
    (tools / "reads_only.py").write_text("print(open('x').read(), open('w'), open('y', 'r'))\n", encoding="utf-8")
    monkeypatch.setattr(RA, "_ROOT", str(tmp_path))
    found = RA.discover_generators()
    assert found == ["tools/build_demo2_viewer.py", "tools/build_demo_anim3d.py"], found
    assert RA.unclassified() == found
