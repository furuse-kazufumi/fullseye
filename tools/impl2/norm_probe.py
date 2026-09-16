# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""**画像ごとの正規化**を実測で見つける。

`cv_scharr` の第 2 実装が出力スケールごと食い違ったのを追ったら、ノートが
「正規化したもの」とだけ書いて**式が無い**ことが分かった。実測すると
``|Sx| + |Sy|`` を **その画像の最大値**で割っていた(完全一致)。

これは利用者に効く落とし穴である。**画像ごとに割ると、同じエッジでも別の画像では
違う値になる** —— 値が画像間で比較できない。明るさを変えただけの同じ被写体が同じ値を
返し(スケール不変)、逆に「弱いエッジしか無い画像」では雑音が 1.0 まで持ち上がる。
物理量を測る道具としては、書かれていなければ誤用される。

**どう見分けるか(2 つの署名を同時に満たすこと)**:

1. 出力の最大が**常にちょうど 1.0**(複数の入力で)
2. 入力を定数倍しても**出力が 1 ビットも変わらない**(スケール不変)

片方だけなら別の説明が付く(1 だけ = たまたま飽和、2 だけ = 二値化など)。
両方が揃うのは「その画像の最大で割っている」形に特有。**確信が持てない形は報告しない**。

使い方::

    py -3.11 tools/impl2/norm_probe.py --all-image --json docs/op_normalisation.json
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


def _inputs(n: int = 24) -> list[np.ndarray]:
    """**構造の違う入力を複数枚**。1 枚では「たまたま最大が 1.0」と区別できない。"""
    rng = np.random.default_rng(20260916)
    y, x = np.mgrid[0:n, 0:n]
    return [
        np.clip((np.sin(x / 6.0) + np.cos(y / 5.0)) * 0.25 + 0.5
                + rng.normal(0, 0.05, (n, n)), 0, 1),
        np.clip(np.outer(np.linspace(0.1, 0.9, n), np.ones(n))
                + rng.normal(0, 0.03, (n, n)), 0, 1),
        np.clip(np.abs(rng.normal(0.4, 0.2, (n, n))), 0, 1),
    ]


def measure(op: str) -> dict:
    import fullseye as fs

    rec: dict = {"op": op}
    maxes, scale_invariant = [], True
    for im in _inputs():
        try:
            o = np.asarray(fs.apply(im.copy(), op, a=0.5, b=0.5), np.float64)
            o2 = np.asarray(fs.apply((im * 0.5).copy(), op, a=0.5, b=0.5), np.float64)
        except Exception as e:
            return {**rec, "status": "not_applicable",
                    "reason": f"{type(e).__name__}: {e}"[:140]}
        if o.shape != im.shape or not np.isfinite(o).all():
            return {**rec, "status": "not_applicable", "reason": "形が違う/非有限"}
        if o2.shape != o.shape or not np.isfinite(o2).all():
            return {**rec, "status": "not_applicable", "reason": "定数倍で形が違う/非有限"}
        maxes.append(float(o.max()))
        if float(np.max(np.abs(o2 - o))) > EPS:
            scale_invariant = False

    rec["out_max_per_input"] = [round(m, 12) for m in maxes]
    rec["scale_invariant"] = scale_invariant
    always_one = all(abs(m - 1.0) < EPS for m in maxes)
    rec["out_max_always_one"] = always_one
    # **両方揃ったときだけ**言う。片方だけでは別の説明が付く。
    rec["status"] = "determined"
    rec["per_image_normalised"] = bool(always_one and scale_invariant)
    return rec


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
        print("op を指定してください"); return 2

    out = []
    for op in names:
        try:
            r = measure(op)
        except Exception as e:
            r = {"op": op, "status": "not_applicable", "reason": f"{type(e).__name__}: {e}"[:140]}
        out.append(r)
    hits = [r for r in out if r.get("per_image_normalised")]
    det = [r for r in out if r["status"] == "determined"]
    print(f"測れた op: {len(det)} / {len(out)}")
    print(f"★画像ごとの最大で正規化している op: {len(hits)}")
    for r in hits[:25]:
        print("   ", r["op"])
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n{a.json} に書いた")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
