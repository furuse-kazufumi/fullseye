# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""差分を **(a) 仕様の穴 / (b) 第 2 実装の欠陥 / (c) 測り方の問題** に振り分ける。

**なぜ機械化するか。** 先行研究(RustAssure、Beyond Translation Accuracy)が実測して
いるとおり、LLM に書かせた第 2 実装は 3 割前後しか等価にならず、**差分の大半は第 2
実装側の欠陥**である。つまり生成より **triage が律速**になる。1 件ずつ手で追うと
数百件で止まるので、**手でやっていた判定規則をそのまま規則として書く**。

判定の第一問は「どちらが正しいか」ではなく **「契約が決めているか」**
([[feedback_second_implementation_finds_what_tests_cannot]] の How to apply #1)。
決めていなければ直すのは実装ではなく仕様のほう。

規則は **どの探針で分かれたか** から引く。これが効くのは探針を構造つきにしてあるから:

* 端でだけ分かれる(`impulse_corner` / `frame` / `blob_at_corner` / `all_ones`)
  かつ内部(`constant_half` / `zeros`)で一致 -> **端の規約の穴**
* 連結性の探針でだけ分かれる(`checkerboard8` / `corner_touch2` /
  `corner_touch_blocks` / `ring_with_hole`)-> **連結性の穴**
* **定数や空の入力でも分かれる** -> 端でも連結性でも説明できない。第 2 実装が
  意味を取り違えた疑いが濃い
* 出力が値域を大きく超える -> **正規化の定義の穴**
* 非有限 / 形が違う / 落ちる -> 第 2 実装の欠陥

**確信が持てないものは `needs_human` に落とす。** 自動で「仕様の穴」と断じて契約を
書き換えるのが一番危ない —— 推測が契約になる。この道具は**振り分けまで**で、
書き戻しは実測(`border_probe` / `knob_probe`)か人の確認を経る。

使い方::

    py -3.11 tools/impl2/triage.py --engine qwen2.5-coder-32b
    py -3.11 tools/impl2/triage.py --engine codex --json impl2/triage.json
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMPL2 = ROOT / "impl2"

#: 端の規約だけが効く探針。
BORDER_PROBES = {"impulse_corner", "frame", "blob_at_corner", "all_ones", "single_pixel"}
#: 連結性・離散判定が効く探針。
CONNECT_PROBES = {"checkerboard8", "corner_touch2", "corner_touch_blocks",
                  "ring_with_hole", "two_blobs", "diagonal"}
#: 端でも連結性でも説明できない「どこでも効く」入力。ここで分かれたら意味の取り違え。
INTERIOR_PROBES = {"constant_half", "zeros", "all_zeros", "ramp_x", "ramp_y",
                   "single_pixel_on", "horizontal_line", "vertical_line"}


def classify(rec: dict) -> dict:
    op = rec["op"]
    st = rec.get("status")
    if st in ("agrees",):
        # 一致は成果ではなく警告でもある。探針が弱い可能性を明記して残す。
        return {"op": op, "verdict": "agrees",
                "note": "一致。探針が弱いだけかもしれないので、後で探針を足して再確認する"}
    if st in ("compile_error", "model_error"):
        return {"op": op, "verdict": "impl2_defect",
                "note": f"第 2 実装が {st}(Fullseye 側の情報は得られていない)"}
    if st in ("no_note", "not_applicable"):
        return {"op": op, "verdict": "not_applicable", "note": rec.get("reason", "")}
    if st != "diverges":
        return {"op": op, "verdict": "needs_human", "note": f"未知の status: {st}"}

    diff_by_probe: dict[str, float] = {}
    crashed = shape = nonfinite = False
    max_out = 0.0
    for r in rec.get("probes", []):
        p = r.get("probe", "?")
        if r.get("status") == "impl2_crashed":
            crashed = True; diff_by_probe[p] = float("inf"); continue
        if r.get("status") == "shape_differs":
            shape = True; diff_by_probe[p] = float("inf"); continue
        if r.get("status") != "compared":
            continue
        v = r.get("max_abs_diff")
        if v is None or r.get("non_finite"):
            nonfinite = True; v = float("inf")
        diff_by_probe[p] = max(diff_by_probe.get(p, 0.0), float(v))
        if v != float("inf"):
            max_out = max(max_out, float(v))

    if crashed or shape:
        return {"op": op, "verdict": "impl2_defect",
                "note": "第 2 実装が落ちた / 出力の形が違う"}
    if nonfinite:
        return {"op": op, "verdict": "impl2_defect",
                "note": "どちらかの出力に非有限が出た(fail-closed で inf 扱い)"}

    bad = {p for p, v in diff_by_probe.items() if v > 0}
    good = {p for p, v in diff_by_probe.items() if v == 0}
    if not bad:
        return {"op": op, "verdict": "needs_human", "note": "diverges なのに差が見つからない"}

    interior_bad = bad & INTERIOR_PROBES
    border_only = bad and bad <= BORDER_PROBES
    connect_only = bad and bad <= CONNECT_PROBES

    if max_out > 2.0:
        return {"op": op, "verdict": "spec_gap_normalisation",
                "note": f"出力が値域を大きく超える(最大 {max_out:.3g})。正規化の定義が書かれていない疑い",
                "probes_bad": sorted(bad)}
    if border_only and good:
        return {"op": op, "verdict": "spec_gap_border",
                "note": "端に触れる探針でだけ分かれ、内部では一致。端の規約が未記載",
                "probes_bad": sorted(bad)}
    if connect_only and good:
        return {"op": op, "verdict": "spec_gap_connectivity",
                "note": "連結性の探針でだけ分かれる。4/8 連結の別が未記載",
                "probes_bad": sorted(bad)}
    if interior_bad and len(bad) >= max(3, len(diff_by_probe) * 0.6):
        return {"op": op, "verdict": "impl2_semantics",
                "note": "定数・空・傾斜でも分かれる = 端でも連結性でも説明できない。意味の取り違えの疑い",
                "probes_bad": sorted(bad)[:8]}
    return {"op": op, "verdict": "needs_human",
            "note": "規則で振り分けられない。人が見る",
            "probes_bad": sorted(bad)[:8]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--engine", default="qwen2.5-coder-32b")
    ap.add_argument("--json")
    a = ap.parse_args()

    d = IMPL2 / "meta" / a.engine
    if not d.exists():
        print(f"{d} が無い"); return 2
    out = []
    for p in sorted(d.glob("*.json")):
        out.append(classify(json.loads(p.read_text(encoding="utf-8"))))

    tally = collections.Counter(r["verdict"] for r in out)
    print(f"=== {a.engine}: {len(out)} op を振り分けた ===")
    for k, v in tally.most_common():
        print(f"  {k:26s} {v}")

    for kind in ("spec_gap_border", "spec_gap_connectivity", "spec_gap_normalisation",
                 "needs_human"):
        rows = [r for r in out if r["verdict"] == kind]
        if not rows:
            continue
        print(f"\n--- {kind} ({len(rows)}) ---")
        for r in rows[:12]:
            pb = ",".join(r.get("probes_bad", [])[:4])
            print(f"  {r['op']:26s} {pb}")
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n{a.json} に書いた")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
