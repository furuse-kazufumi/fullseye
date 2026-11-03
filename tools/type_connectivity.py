# -*- coding: utf-8 -*-
"""type_connectivity — 型(sort)のつながりを全型で数え、役割の台帳と突き合わせる。

## なぜ要るか(2026-11-03)

``tools/conversion_matrix.py`` は連鎖ファザーのカタログ(型 95)で袋小路を数えるが、
RAG や MCP が読む正本は ``docs/OP_INDEX.json``(型 101)の方で、そちらには
**型ごとの役割**(入口として正しい / 終端として正しい / 本当に欠けている)を
書く場所が無かった。役割が書いていないと「行き止まり 7」が全部バグなのか、
報告書のように受け手が無いのが自然なのかを、毎回読み直して判断することになる。

この道具は 2 つを突き合わせる:

* ``docs/OP_INDEX.json`` —— op ごとの入力の型(**全入力**。第 1 入力だけで数えると
  ``lut`` のように第 2 入力で受けられている型を行き止まりと誤る)と出力の型。
* ``docs/TYPE_ROLES.json`` —— 手書きの台帳。型ごとに分類 a/b/c/d/ok、根拠、
  ``entry``(入口として正しい理由)/ ``terminal``(終端として正しい理由)。

## 何を数えるか

* **行き止まり** = 作られるのに誰も受けない型。``terminal`` の無いものは問題。
* **入口なし** = 受ける op はあるのに誰も作らない型。``entry`` の無いものは問題。
* **入口から届かない** = 入口の型(``entry`` を書いた型)と、引数だけで値を作る op
  (入力 0 個)から始め、**全入力がそろった op の出力を足す**不動点で閉じても
  届かない型。``any`` はどの型でも満たすとして扱う。
* **終端へ届かない** = その型を受ける op をたどって ``terminal`` の型に行けない型。
* **細い型** = 作る op か受ける op が 2 以下(参考。問題とは限らない)。
* 参考として、親が最初に数えた「第 1 入力だけ・画像から」の数え方も並べる
  (数え方が違えば数字も違う、を同じ表で見せるため)。

    py -3.11 tools/type_connectivity.py                 # 要約を表示
    py -3.11 tools/type_connectivity.py --md docs/TYPE_CONNECTIVITY.md
    py -3.11 tools/type_connectivity.py --check         # 生成物が古ければ exit 1
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OP_INDEX = ROOT / "docs" / "OP_INDEX.json"
ROLES = ROOT / "docs" / "TYPE_ROLES.json"
OUT_MD = ROOT / "docs" / "TYPE_CONNECTIVITY.md"

#: 型の分類の名前(報告と門で同じ語を使う)。
CLASSES = {
    "a": "型の付け方の揺れ",
    "b": "受け手か作り手が本当に欠けていた",
    "c": "終端として正しい",
    "d": "入口として正しい",
    "ok": "両側に十分つながっている",
}
#: どの型でも満たす型(到達の計算で常に満たされているとみなす)。
WILDCARD = "any"
#: 細い型のしきい値(作る op か受ける op がこの数以下)。
THIN = 2


def load_ops(path: Path = OP_INDEX) -> tuple[list[str], list[tuple[str, list[str], str]]]:
    """``OP_INDEX.json`` → (型の一覧, [(op 名, 全入力の型, 出力の型)])。

    入力は ``in_sorts`` があればそれ(多入力の全部)、無ければ ``in_sort`` の 1 個、
    ``in_sort`` が None なら 0 個(引数だけで値を作る op)。
    """
    d = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for o in d["ops"]:
        if "in_sorts" in o:
            ins = list(o["in_sorts"] or [])
        else:
            ins = [o["in_sort"]] if o.get("in_sort") else []
        rows.append((o["name"], ins, o["out_sort"]))
    return list(d["sorts"]), rows


def load_roles(path: Path = ROLES) -> dict:
    """``TYPE_ROLES.json`` の ``sorts`` を返す。"""
    return json.loads(path.read_text(encoding="utf-8"))["sorts"]


def analyse(sorts: list[str], ops: list[tuple[str, list[str], str]], roles: dict) -> dict:
    """つながりの数字と、台帳と食い違う箇所を全部数える。"""
    produced = Counter()
    consumed = Counter()
    sources = Counter()
    consumers = defaultdict(list)
    producers = defaultdict(list)
    for name, ins, out in ops:
        produced[out] += 1
        producers[out].append(name)
        if not ins:
            sources[out] += 1
        for s in set(ins):
            consumed[s] += 1
            consumers[s].append(name)
    all_sorts = sorted(set(sorts) | set(produced) | set(consumed))

    entry = {s for s, r in roles.items() if r.get("entry")}
    terminal = {s for s, r in roles.items() if r.get("terminal")}

    # 入口から届く型: entry の型 + 入力 0 個の op の出力から、全入力がそろう op を足す不動点
    reach = set(entry) | {out for _n, ins, out in ops if not ins}
    changed = True
    while changed:
        changed = False
        for _n, ins, out in ops:
            if out in reach:
                continue
            if all(s == WILDCARD or s in reach for s in ins):
                reach.add(out)
                changed = True
    # 終端へ届く型: terminal から逆向きに「その型を受けて届く型を出す op がある」
    to_term = set(terminal)
    changed = True
    while changed:
        changed = False
        for _n, ins, out in ops:
            if out not in to_term:
                continue
            for s in ins:
                if s != WILDCARD and s not in to_term:
                    to_term.add(s)
                    changed = True
    concrete = [s for s in all_sorts if s != WILDCARD]

    # 参考: 第 1 入力だけ・画像から・単純な有向グラフ(最初に親が数えた数え方)
    first_in = Counter()
    adj = defaultdict(set)
    for _n, ins, out in ops:
        if ins:
            first_in[ins[0]] += 1
            if ins[0] != out:
                adj[ins[0]].add(out)
    seen, stack = {"image"}, ["image"]
    while stack:
        x = stack.pop()
        for y in adj[x]:
            if y not in seen:
                seen.add(y)
                stack.append(y)
    legacy = {
        "dead_ends": sorted(s for s in all_sorts if produced[s] and not first_in[s]),
        "no_entry": sorted(s for s in all_sorts if first_in[s] and not produced[s]),
        "unreachable_from_image": sorted(s for s in all_sorts if s not in seen),
        "thin": sorted(s for s in all_sorts if first_in[s] <= THIN or produced[s] <= THIN),
    }

    dead = sorted(s for s in concrete if produced[s] and not consumed[s])
    no_entry = sorted(s for s in concrete if consumed[s] and not produced[s])
    return {
        "sorts": all_sorts,
        "produced": produced, "consumed": consumed, "sources": sources,
        "producers": producers, "consumers": consumers,
        "entry": sorted(entry), "terminal": sorted(terminal),
        "dead_ends": dead,
        "dead_ends_unexplained": [s for s in dead if s not in terminal],
        "no_entry": no_entry,
        "no_entry_unexplained": [s for s in no_entry if s not in entry],
        "unreachable": sorted(s for s in concrete if s not in reach),
        "no_terminal": sorted(s for s in concrete if s not in to_term),
        "thin": sorted(s for s in concrete if produced[s] <= THIN or consumed[s] <= THIN),
        "missing_roles": sorted(s for s in all_sorts if s not in roles),
        "stale_roles": sorted(s for s in roles if s not in set(all_sorts)),
        "class_counts": Counter(r.get("class") for r in roles.values()),
        "legacy": legacy,
    }


def _summary_lines(a: dict, roles: dict) -> list[str]:
    w = []
    cc = a["class_counts"]
    w.append(f"型 {len(a['sorts'])}(うち {WILDCARD} 1) / 入口として数える型 {len(a['entry'])}"
             f" / 終端として数える型 {len(a['terminal'])}")
    w.append("分類: " + " / ".join(f"{k} {cc.get(k, 0)}" for k in CLASSES))
    w.append("")
    w.append("全入力で数える(この表の基準):")
    w.append(f"  行き止まり {len(a['dead_ends'])}(理由なし {len(a['dead_ends_unexplained'])})"
             f" / 入口なし {len(a['no_entry'])}(理由なし {len(a['no_entry_unexplained'])})")
    w.append(f"  入口から届かない {len(a['unreachable'])} / 終端へ届かない {len(a['no_terminal'])}"
             f" / 細い型(産 or 受 <= {THIN}) {len(a['thin'])}")
    lg = a["legacy"]
    w.append("参考: 第 1 入力だけ・image から(最初の数え方):")
    w.append(f"  行き止まり {len(lg['dead_ends'])} / 入口なし {len(lg['no_entry'])}"
             f" / image から届かない {len(lg['unreachable_from_image'])} / 細い型 {len(lg['thin'])}")
    for key, label in (("dead_ends_unexplained", "行き止まり(理由なし)"),
                       ("no_entry_unexplained", "入口なし(理由なし)"),
                       ("unreachable", "入口から届かない"), ("no_terminal", "終端へ届かない"),
                       ("missing_roles", "台帳に行が無い型"), ("stale_roles", "台帳にだけある型")):
        if a[key]:
            w.append(f"  ! {label}: {', '.join(a[key])}")
    return w


def _cell(text) -> str:
    return str(text or "").replace("|", "/").replace("\n", " ")


def render_md(a: dict, roles: dict) -> str:
    """``docs/TYPE_CONNECTIVITY.md`` の本文。"""
    L = ["# 型のつながり ―― 全型の役割と処置", "",
         "`py -3.11 tools/type_connectivity.py --md docs/TYPE_CONNECTIVITY.md` の生成物。"
         "手で編集しない(直すのは `docs/TYPE_ROLES.json` と op の宣言)。"
         "門は `tests/test_type_connectivity.py`。", "",
         "数え方: 入力は **全入力**(`in_sorts`)。「入口から届く」は、入口の型(台帳に `entry` が"
         "ある型)と引数だけで値を作る op から始め、**全入力がそろった op** の出力を足していく"
         "不動点。「終端へ届く」は、受ける op をたどって `terminal` の型に行けること。", "",
         "```", *_summary_lines(a, roles), "```", "",
         "## 分類の意味", ""]
    for k, v in CLASSES.items():
        L.append(f"- **{k}** —— {v}")
    L += ["", "## 直したもの・案だけのもの", ""]
    for status, title in (("fixed", "この版で直した(b)"), ("open", "直していない(案は下の表)")):
        names = [s for s in sorted(roles) if roles[s].get("status") == status]
        L.append(f"- {title}: " + (", ".join(f"`{s}`" for s in names) if names else "なし"))
    designs = [s for s in sorted(roles) if roles[s].get("design")]
    L += ["", "### 設計の判断が要るもの(実装していない)", "",
          "型の宣言の変更・新しい型名は CONTRIBUTING で破壊的変更の扱い。1.0 の前に決める。", "",
          "| 型 | 分類 | 案 |", "|---|---|---|"]
    for s in designs:
        L.append(f"| `{s}` | {roles[s].get('class')} | {_cell(roles[s]['design'])} |")
    L += ["", "## 全型の表", "",
          "| 型 | 分類 | 産 | 受 | 入口 | 終端 | 処置 | 理由 | 根拠(検索語・確かめた関数) |",
          "|---|---|--:|--:|---|---|---|---|---|"]
    for s in a["sorts"]:
        r = roles.get(s, {})
        L.append("| `{}` | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            s, r.get("class", "**未分類**"), a["produced"][s], a["consumed"][s],
            _cell(r.get("entry")) or "", _cell(r.get("terminal")) or "",
            _cell(r.get("action") or r.get("status", "")), _cell(r.get("why")),
            _cell(r.get("evidence"))))
    L.append("")
    return "\n".join(L)


def build() -> tuple[dict, dict, str]:
    sorts, ops = load_ops()
    roles = load_roles()
    a = analyse(sorts, ops, roles)
    return a, roles, render_md(a, roles)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--md", metavar="PATH", help="Markdown として書き出す")
    ap.add_argument("--check", action="store_true", help="docs/TYPE_CONNECTIVITY.md が古ければ exit 1")
    ns = ap.parse_args(argv)
    a, roles, md = build()
    if ns.check:
        cur = OUT_MD.read_text(encoding="utf-8") if OUT_MD.exists() else ""
        if cur.replace("\r\n", "\n") != md:
            print(f"stale: {OUT_MD} (run tools/type_connectivity.py --md)", file=sys.stderr)
            return 1
        return 0
    print("\n".join(_summary_lines(a, roles)))
    if ns.md:
        out = Path(ns.md)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8", newline="\n")
        print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
