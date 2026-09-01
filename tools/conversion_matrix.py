# -*- coding: utf-8 -*-
"""conversion_matrix — 型どうしの変換を行列で見て、穴と不具合を洗い出す。

## なぜ行列で見るのか

この repo で最近見つかった型の嘘は、**全部が変換 op** だった
(``voxel_to_mesh`` が宣言 ``mesh`` に 3-tuple、``render_beauty`` が宣言 ``image2d``
に RGB、``project_points`` が宣言 ``image2d`` にタプル、``alpha_shape_boundary``
が宣言 ``points`` に添字)。変換は**入口の型と出口の型を両方主張する**ので、
嘘をつく面が 2 つある。だから変換だけを取り出して行列にすると、
「無い変換」と「怪しい変換」が同じ絵の上に並ぶ。

## 何を報告するか

* **行列** ― どの型からどの型へ、いくつの op で行けるか。
* **袋小路** ― 産めるのに、そこから他の型へ一切出られない型。
  進化探索でも連鎖ファザーでも一歩も進めない = 記事で言う「死んだ語彙」。
* **孤児** ― 誰も産まない型(生成器も変換元も無い)。宣言だけあって到達不能。
* **片道** ― A→B はあるが B→A が無い組。**戻せないことが正しい**場合も多いので、
  これは「バグの一覧」ではなく「**判断すべき一覧**」として出す。
* **無検査** ― 出力型に ``TYPE_CHECKS`` の述語が無い変換 op。
  **何を返しても TYPEMISS にならない**ので、嘘をついても誰も気づけない。
  上に挙げた実バグは、述語を足した瞬間に出てきたものが含まれる。
* **到達可能性** ― 生成器の型から不動点で閉じ、構造的に到達できない型を出す。

多入力の op(``["mesh","keypoints"] → table`` など)も変換として数える。
1 入力に限ると、実際に使われている経路の多くを見落とす。

    py -3.11 tools/conversion_matrix.py                 # 要約
    py -3.11 tools/conversion_matrix.py --matrix        # 行列も出す
    py -3.11 tools/conversion_matrix.py --md docs/CONVERSION_MATRIX.md
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))


def load():
    import chain_fuzz as CF
    ops = CF.catalog()
    checks = set(CF.TYPE_CHECKS)
    gens = set(CF.make_generators())
    builders = set(getattr(CF, "OP_ARG_BUILDERS", {}))
    return ops, checks, gens, builders


def analyse() -> dict:
    ops, checks, gens, builders = load()

    sorts: set[str] = set()
    # edges[(a, b)] = [op 名] ― a を入力に取り b を返す op(多入力は入力ごとに 1 本)
    edges: dict[tuple[str, str], list[str]] = defaultdict(list)
    op_in: dict[str, list[str]] = {}
    op_out: dict[str, str] = {}
    for name, _family, ins, out, _func in ops:
        op_in[name], op_out[name] = list(ins), out
        sorts.add(out)
        for i in ins:
            sorts.add(i)
            if i != out:
                edges[(i, out)].append(name)

    outdeg = defaultdict(set)
    indeg = defaultdict(set)
    for (a, b) in edges:
        outdeg[a].add(b)
        indeg[b].add(a)

    produced = {out for out in op_out.values()}
    consumed = {i for ins in op_in.values() for i in ins}

    dead_ends = sorted(s for s in sorts if not outdeg[s] and s in produced)
    orphans = sorted(s for s in sorts if s not in produced and s not in gens)
    never_consumed = sorted(s for s in sorts if s not in consumed)

    one_way = sorted((a, b) for (a, b) in edges if (b, a) not in edges)

    unchecked = sorted({name for name in op_out
                        if op_out[name] not in checks
                        and any(i != op_out[name] for i in op_in[name])})
    unchecked_sorts = sorted({op_out[n] for n in unchecked})

    # 到達可能性の不動点: 生成器の型から始め、入力が全て揃う op の出力型を足す。
    #
    # ★ここは 2 度間違えられる。ファザーの ``run_chain`` は
    #   (1) 入力型 ``any`` を「常に揃っている」として扱い(プールから任意に引く)、
    #   (2) ``OP_ARG_BUILDERS`` に登録された op は引数を自前で組み立てる。
    # この 2 つを数えないと、実際には毎回走っている op を「構造的に到達不能」と
    # 報告してしまう(実際に ``fuse_to_voxel`` / ``register_cross`` で誤報した)。
    # 到達可能性は「型だけ」では決まらない ―― 到達経路の一部はコードの側にある。
    def _satisfied(t: str, reached: set[str]) -> bool:
        return t == "any" or t in reached

    reach = set(gens)
    changed = True
    while changed:
        changed = False
        for name, ins in op_in.items():
            if op_out[name] in reach:
                continue
            if name in builders or all(_satisfied(i, reach) for i in ins):
                reach.add(op_out[name])
                changed = True
    unreachable = sorted(s for s in sorts if s not in reach)
    by_builder = sorted(n for n in op_in
                        if n in builders
                        and not all(_satisfied(i, reach - {op_out[n]}) for i in op_in[n]))

    return {
        "ops": ops, "sorts": sorted(sorts), "edges": edges,
        "outdeg": outdeg, "indeg": indeg, "generators": sorted(gens),
        "dead_ends": dead_ends, "orphans": orphans,
        "never_consumed": never_consumed, "one_way": one_way,
        "unchecked_ops": unchecked, "unchecked_sorts": unchecked_sorts,
        "unreachable": unreachable, "checks": sorted(checks),
    }


def _matrix_md(a: dict) -> str:
    sorts = [s for s in a["sorts"] if a["outdeg"][s] or a["indeg"][s]]
    head = "| from \\ to | " + " | ".join(sorts) + " |"
    sep = "|---" * (len(sorts) + 1) + "|"
    rows = [head, sep]
    for src in sorts:
        cells = []
        for dst in sorts:
            n = len(a["edges"].get((src, dst), ()))
            cells.append(str(n) if n else "")
        rows.append(f"| **{src}** | " + " | ".join(cells) + " |")
    return "\n".join(rows)


def report(a: dict, show_matrix: bool) -> str:
    lines: list[str] = []
    w = lines.append
    n_edges = sum(len(v) for v in a["edges"].values())
    w(f"型 {len(a['sorts'])} / 変換ペア {len(a['edges'])} / 変換を行う op のべ {n_edges}")
    w(f"生成器のある型 {len(a['generators'])} / 出力型に述語のある型 {len(a['checks'])}")
    w("")

    w(f"■ 袋小路 ({len(a['dead_ends'])}) ― 産めるのに、そこから他の型へ出られない")
    for s in a["dead_ends"]:
        w(f"   {s:16} ← {len(a['indeg'][s])} 型から来る")
    w("")

    w(f"■ 孤児 ({len(a['orphans'])}) ― 生成器も無く、どの op も産まない")
    for s in a["orphans"]:
        w(f"   {s}")
    w("")

    w(f"■ 構造的に到達不能 ({len(a['unreachable'])}) ― 不動点で閉じても届かない")
    for s in a["unreachable"]:
        w(f"   {s}")
    w("")

    w(f"■ 誰も食べない型 ({len(a['never_consumed'])}) ― 出力専用。終端なら正しい")
    w("   " + ", ".join(a["never_consumed"]))
    w("")

    w(f"■ 出力型に述語が無い変換 op ({len(a['unchecked_ops'])}) ― 何を返しても TYPEMISS にならない")
    w(f"   対象の型: {', '.join(a['unchecked_sorts'])}")
    by_sort: dict[str, list[str]] = defaultdict(list)
    for name in a["unchecked_ops"]:
        by_sort[dict((n, o) for n, _f, _i, o, _fn in a["ops"])[name]].append(name)
    for s in sorted(by_sort):
        names = by_sort[s]
        w(f"   {s:16} {len(names):3} op   {', '.join(sorted(names)[:6])}"
          + (" …" if len(names) > 6 else ""))
    w("")

    w(f"■ 片道の変換 ({len(a['one_way'])}) ― A→B はあるが B→A が無い(戻せないのが正しい場合も多い)")
    for (x, y) in a["one_way"]:
        w(f"   {x:16} → {y:16}  {', '.join(a['edges'][(x, y)][:3])}")
    if show_matrix:
        w("")
        w("■ 行列(セル = その変換を行う op の数)")
        w(_matrix_md(a))
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--matrix", action="store_true", help="行列も表示する")
    ap.add_argument("--md", metavar="PATH", help="Markdown として書き出す")
    args = ap.parse_args(argv)

    a = analyse()
    text = report(a, show_matrix=args.matrix or bool(args.md))
    print(text)
    if args.md:
        out = Path(args.md)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            "# 型変換の行列 ―― 穴と不具合の点検\n\n"
            "`py -3.11 tools/conversion_matrix.py --md docs/CONVERSION_MATRIX.md` の生成物。\n"
            "手で編集しない。\n\n```\n" + text + "\n```\n", encoding="utf-8")
        print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
