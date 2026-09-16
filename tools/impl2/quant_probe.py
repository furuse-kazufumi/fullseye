# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""**内部で 8 bit に落としている op** を実測で見つける。

2026-09-16、codex に書かせた第 2 実装が `cv_median` で食い違い、差が**厳密に 1/255**
だった。追うと Fullseye 側が内部で uint8 に量子化していた —— ノートには書かれていない。

これは測定の道具としては見逃せない事実である。**利用者は float64 の画像を渡すので、
渡した精度がそのまま出てくると思う。** 実際には 8 bit に落ちるので:

* 16-bit カメラの階調(1.5e-5)は 1/255 = 3.9e-3 に丸められ、**255 段階まで潰れる**
* 1/255 より小さい差しか無い 2 枚は、**同じ答えを返す**(欠陥が消える)
* 出力の値は k/255 の格子にしか乗らないので、**微分・回帰の入力にすると段差が出る**

**どう見分けるか(2 つの署名を同時に満たすこと)**:

1. 出力の値が**すべて k/255 の格子に載る**(誤差 0)
2. 出力が**その格子を 20 段以上使っている**(数個の階級ではなく 8 bit の連続量)

片方だけでは別の説明が付く。1 だけなら二値・段階出力の op(しきい値は 0 と 1 しか
返さないが、どちらも格子上である)が該当してしまう。2 だけなら普通の float の op が
該当してしまう。

**最初は 2 を「1/255 より小さく揺らしても出力が変わらない」にして失敗した。**
量子化する参照実装ですら、揺らしが丸め境界を跨げば出力は 1 段変わる —— **陽性対照が
落ちて**気づいた。鈍さは量子化の署名ではない。

**確信が持てない形は報告しない。** 二値出力の op は 1 を満たすが 2 を満たさないので
落ちる —— それが正しい答えである。

使い方::

    py -3.11 tools/impl2/quant_probe.py --ops cv_median,median
    py -3.11 tools/impl2/quant_probe.py --all-image --json docs/op_quantisation.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

EPS = 1e-9
#: 8 bit の格子。``k/255`` に載っているかを見る。
LEVELS = 255.0
#: 「8 bit の連続量」と言うのに必要な段数。二値(2 段)・数階級の op を落とすため。
MIN_LEVELS = 20


def _inputs(n: int = 24) -> list[np.ndarray]:
    """構造の違う入力を複数枚。1 枚では「たまたま格子に載った」と区別できない。"""
    rng = np.random.default_rng(20260916)
    y, x = np.mgrid[0:n, 0:n]
    return [
        rng.random((n, n)),
        np.clip((np.sin(x / 6.0) + np.cos(y / 5.0)) * 0.25 + 0.5
                + rng.normal(0, 0.05, (n, n)), 0, 1),
        np.clip(np.outer(np.linspace(0.07, 0.93, n), np.ones(n)), 0, 1),
    ]


def measure(op: str) -> dict:
    import fullseye as fs

    rec: dict = {"op": op}
    on_grid = True
    worst_grid, most_levels = 0.0, 0
    for im in _inputs():
        try:
            o = np.asarray(fs.apply(im.copy(), op, a=0.5, b=0.5), np.float64)
        except Exception as e:
            return {**rec, "status": "not_applicable",
                    "reason": f"{type(e).__name__}: {e}"[:140]}
        if o.shape != im.shape or not np.isfinite(o).all():
            return {**rec, "status": "not_applicable", "reason": "形が違う/非有限"}
        g = float(np.max(np.abs(o * LEVELS - np.round(o * LEVELS))))
        worst_grid = max(worst_grid, g)
        most_levels = max(most_levels, int(np.unique(o).size))
        if g > EPS:
            on_grid = False

    rec["status"] = "determined"
    rec["worst_off_grid"] = round(worst_grid, 12)
    rec["distinct_levels"] = most_levels
    rec["output_on_8bit_grid"] = on_grid
    rec["uses_many_levels"] = most_levels >= MIN_LEVELS
    # **両方揃ったときだけ**言う。片方だけでは別の説明が付く。
    rec["quantises_to_8bit"] = bool(on_grid and most_levels >= MIN_LEVELS)
    return rec


def _self_test() -> str:
    """**陽性対照**: 答えを知っている 2 つの参照で判定できるか。

    当てられない道具で op を測れば、出てくるのは事実ではなく思い込みになる。
    """
    rng = np.random.default_rng(1)
    im = rng.random((24, 24))

    def verdict(fn):
        a = fn(im)
        g = float(np.max(np.abs(a * LEVELS - np.round(a * LEVELS))))
        return g <= EPS and int(np.unique(a).size) >= MIN_LEVELS

    refs = {
        "8 bit に落とす": (lambda v: np.round(v * LEVELS) / LEVELS, True),
        "落とさない": (lambda v: v * 0.5 + 0.25, False),
        # **二値出力**は格子には載るが段を使わない。1 だけを署名にすると誤判定する。
        "二値化": (lambda v: (v > 0.5).astype(np.float64), False),
    }
    ng = [n for n, (fn, want) in refs.items() if verdict(fn) is not want]
    return "OK" if not ng else "NG " + ",".join(ng)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ops")
    ap.add_argument("--all-image", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args()

    names = [o.strip() for o in (a.ops or "").split(",") if o.strip()]
    if a.all_image:
        idx = json.loads((ROOT / "docs" / "OP_INDEX.json").read_text(encoding="utf-8"))
        names += [o["name"] for o in idx["ops"]
                  if o["tier"] in ("registry", "color")
                  and o["in_sort"] == "image" and o["out_sort"] == "image"]
    names = list(dict.fromkeys(names))
    if not names:
        print("op を指定してください(--ops か --all-image)"); return 2

    st = _self_test()
    print(f"陽性対照(8 bit に落とす参照と落とさない参照を撃ち分けられるか): {st}")
    if st != "OK":
        print("→ 道具が当てられないので op は測らない")
        return 3

    out = []
    for op in names:
        try:
            r = measure(op)
        except Exception as e:
            r = {"op": op, "status": "not_applicable",
                 "reason": f"{type(e).__name__}: {e}"[:140]}
        out.append(r)
        if r.get("quantises_to_8bit"):
            print(f"[8bit に落とす  ] {op}")
    det = [r for r in out if r["status"] == "determined"]
    hit = [r for r in det if r.get("quantises_to_8bit")]
    print(f"\n測れた {len(det)} / {len(out)}")
    print(f"★内部で 8 bit に落としている op: {len(hit)}")
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=2, ensure_ascii=False),
                                encoding="utf-8")
        print(f"\n{a.json} に書いた")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
