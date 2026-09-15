# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""op が画像の端をどう埋めているかを **実測で確定する**。

**なぜ要るか。** 近傍窓を使う op 213 本のうち 198 本(93%)のノートが端の規約に触れて
いない。そして端の規約は答えを値域の 2 割動かす(`impl2/FINDINGS.md`)。穴を埋めるとき
**規約を推測で書いてはいけない** —— 書いた瞬間にそれが契約になり、間違っていれば
利用者と第 2 実装の両方を誤らせる。

**どう測るか(カーネル非依存)。** op が内部で規約 P で埋めているなら、**あらかじめ P で
埋めた画像に op をかけて内側を切り出したもの**は、埋めずにかけたものと一致する::

    op(pad_P(img))[crop] == op(img)     <=> op の内部規約が P

カーネルの形も窓の大きさも知らずに判定できる。候補を全部試して、差が消えるものが
その op の規約。**どれも消えなければ「判定不能」と正直に返す**(勝手に一番近いものを
選ばない —— 大域正規化を含む op などは、そもそもこの前提が成り立たない)。

**角の衝撃では足りない。** 最初に使った「角に衝撃を置いて 4/9 か 1/4 か」という探針は、
`reflect` と `edge`(複製)を**区別できない**(k=3 の角ではどちらも 4/9)。実際、
ローカル LLM は「範囲内だけ数える」、Codex は「端画素を複製」と別の選択をしたのに、
角の値だけは一致した。**一致したときは探針を疑う**という規律がそのまま当てはまる。

使い方::

    py -3.11 tools/impl2/border_probe.py --ops mean_box,cv_box,cv_erode
    py -3.11 tools/impl2/border_probe.py --category smoothing --limit 20 --json out.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

#: numpy の ``pad`` mode と、ノートに書くときの日本語。
#: ``reflect`` = 端画素を重複させない (d c b | a b c d) = OpenCV の ``BORDER_REFLECT_101``。
#: ``symmetric`` = 端画素を重複させる (d c b a | a b c d) = OpenCV の ``BORDER_REFLECT``。
MODES = {
    "constant0": ("外側は 0 とみなす", dict(mode="constant", constant_values=0)),
    "edge":      ("端の画素を複製する(最近傍)", dict(mode="edge")),
    "reflect":   ("端画素を重複させずに折り返す (d c b | a b c d)", dict(mode="reflect")),
    "symmetric": ("端画素を重複させて折り返す (d c b a | a b c d)", dict(mode="symmetric")),
    "wrap":      ("反対側へ巻き付ける(周期)", dict(mode="wrap")),
}

#: 端が効く入力。**定数や対称な画像では規約が分かれない**ので、端の近くに構造を置く。
def _inputs(n: int = 24) -> list[tuple[str, np.ndarray]]:
    rng = np.random.default_rng(20260916)
    ramp = np.tile(np.linspace(0.05, 0.95, n), (n, 1))
    return [
        ("ramp_x", ramp),
        ("ramp_xy", (ramp + ramp.T) / 2.0),
        ("random", rng.random((n, n))),
    ]


def detect(op: str, pad: int = 12, tol: float = 1e-9) -> dict:
    import fullseye as fs

    rec: dict = {"op": op, "pad": pad, "tol": tol}
    scores: dict[str, float] = {}
    for name, (_ja, kw) in MODES.items():
        worst = 0.0
        for _iname, img in _inputs():
            try:
                base = np.asarray(fs.apply(img.copy(), op, a=0.5, b=0.5), np.float64)
                big = np.pad(img, pad, **kw)
                got = np.asarray(fs.apply(big.copy(), op, a=0.5, b=0.5), np.float64)
            except Exception as e:                       # op が拒む/形が変わる
                rec["status"] = "not_applicable"
                rec["reason"] = f"{type(e).__name__}: {e}"[:160]
                return rec
            if got.shape != (img.shape[0] + 2 * pad, img.shape[1] + 2 * pad):
                rec["status"] = "not_applicable"
                rec["reason"] = "出力の形が入力と同じでない(この判定法の前提が成り立たない)"
                return rec
            crop = got[pad:-pad, pad:-pad]
            if base.shape != crop.shape:
                rec["status"] = "not_applicable"
                rec["reason"] = "切り出しの形が合わない"
                return rec
            if not (np.isfinite(base).all() and np.isfinite(crop).all()):
                worst = float("inf")
                break
            worst = max(worst, float(np.max(np.abs(base - crop))))
        scores[name] = worst

    rec["scores"] = {k: (None if v == float("inf") else v) for k, v in scores.items()}
    best = min(scores, key=lambda k: scores[k])
    if scores[best] < tol:
        # 2 位と十分離れているか。離れていなければ「この探針では分けられない」と言う。
        rest = sorted(v for k, v in scores.items() if k != best)
        rec["status"] = "determined"
        rec["border"] = best
        rec["border_ja"] = MODES[best][0]
        rec["second_best_diff"] = None if not rest or rest[0] == float("inf") else rest[0]
        if rest and rest[0] < tol:
            # 複数が一致 = この入力では規約が分かれない(例: 大域正規化で差が消える)
            rec["status"] = "ambiguous"
            rec["candidates"] = [k for k, v in scores.items() if v < tol]
    else:
        rec["status"] = "undetermined"
        rec["closest"] = best
        rec["closest_diff"] = None if scores[best] == float("inf") else scores[best]
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ops", help="カンマ区切りの op 名")
    ap.add_argument("--category", help="この category の op をまとめて測る")
    ap.add_argument("--all", action="store_true",
                    help="registry/color の image->image op を全部測る")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--json", help="結果をこのファイルに書く")
    a = ap.parse_args()

    names: list[str] = []
    if a.ops:
        names += [o.strip() for o in a.ops.split(",") if o.strip()]
    if a.category:
        idx = json.loads((ROOT / "docs" / "OP_INDEX.json").read_text(encoding="utf-8"))
        names += [o["name"] for o in idx["ops"]
                  if o.get("category") == a.category and o["tier"] in ("registry", "color")
                  and o["in_sort"] == "image" and o["out_sort"] == "image"]
    if a.all:
        idx = json.loads((ROOT / "docs" / "OP_INDEX.json").read_text(encoding="utf-8"))
        names += [o["name"] for o in idx["ops"]
                  if o["tier"] in ("registry", "color")
                  and o["in_sort"] == "image" and o["out_sort"] == "image"]
    names = list(dict.fromkeys(names))
    if a.limit:
        names = names[:a.limit]
    if not names:
        print("op を指定してください(--ops か --category)"); return 2

    out, tally = [], {}
    for op in names:
        r = detect(op)
        out.append(r)
        key = r.get("border") or r["status"]
        tally[key] = tally.get(key, 0) + 1
        line = f"[{r['status']:14s}] {op:24s}"
        if r["status"] == "determined":
            sb = r.get("second_best_diff")
            line += f" {r['border']:10s} (2 位との差 {sb:.3e})" if sb else f" {r['border']}"
        elif r["status"] == "ambiguous":
            line += " 候補: " + ",".join(r["candidates"])
        elif r["status"] == "undetermined":
            d = r.get("closest_diff")
            line += f" 最も近い {r['closest']} でも差 {d:.3e}" if d else ""
        else:
            line += " " + r.get("reason", "")[:60]
        print(line)

    print("\n--- 集計 ---")
    for k, v in sorted(tally.items(), key=lambda x: -x[1]):
        print(f"  {k:16s} {v}")
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n{a.json} に書いた")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
