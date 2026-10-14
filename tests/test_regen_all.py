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
    "tools/gen_capabilities_index.py", "tools/gen_hardening_index.py", "tools/gen_maturity.py",
    "tools/gen_exhibit_numbers.py", "tools/gen_wingpoc_gallery.py", "tools/gen_examples_readme.py",
    "tools/gen_oss_landscape.py", "tools/gen_view2026_pages.py", "tools/gen_trust_block.py",
    "tools/gen_docs_index_ops.py", "tools/gen_examples3d_doc.py", "tools/gen_sensor_playbook.py",
    "imgevolve.py", "catalog.py", "dispositions.py", "references.py", "samples.py",
    "tools/gen_mcp_data.py", "tools/conversion_matrix.py", "tools/gen_design_notes.py",
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
    assert any("READS に無い生成物を読んだ: docs/EXAMPLES.md" in p for p in RA.trace_problems(t))

    t = clean()
    t["catalog.py"]["w"].append("docs/STRAY.md")                                # 宣言に無い書き
    assert any("OUTPUTS に無いファイルを書いた: docs/STRAY.md" in p for p in RA.trace_problems(t))

    t = clean()
    t["tools/gen_capabilities_index.py"]["r"] = []                              # 読まなくなった宣言
    assert any("1 本も読んでいない" in p for p in RA.trace_problems(t))

    t = clean()
    t["tools/conversion_matrix.py"] = {"r": [], "w": []}                        # 何も書かない段
    assert any("tools/conversion_matrix.py: OUTPUTS の 'docs/CONVERSION_MATRIX.md' に触れもしない" in p
               for p in RA.trace_problems(t))


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
    assert any(p.endswith(".py") for p in t["r"]), "読みが 1 本も記録されていない —— hook が効いていない"
    # 表から見ると、これは「出力に触れもしない段」として拒まれる。
    probs = RA.trace_problems({**{s: {"r": [p.replace("*", "x") for p in RA.READS.get(s, [])],
                                      "w": [p.replace("*", "x") for p in RA.OUTPUTS[s]]}
                                  for s in _chain_order()},
                               "tools/conversion_matrix.py": t})
    assert any("conversion_matrix.py: OUTPUTS" in p and "触れもしない" in p for p in probs), probs
