# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""つまみ ``a`` / ``b`` が**実際に何をしているか**を測る。

2-D の呼び出しモデルは「1 画像 + つまみ 2 つ(``a``, ``b`` はどちらも [0,1])」。
ノートは「``a`` が窓の一辺を ``3,5,7,9`` の 4 段階に切り替える」「``b`` は未使用」と
書くが、**どこで段が切り替わるかは書いていない**ことが多く(「X〜Y に振る」と書く
55 本のうち 45 本が線形か幾何かすら書いていない)、**「``b`` は未使用」が本当かも
誰も検査していなかった**。

測るのは 3 つ:

1. **``b`` が本当に効いていないか** —— ``b`` だけ動かして出力が変わるかを見る。
   「未使用」と書いてあるのに変わるなら、それは文書の誤り(利用者は ``b`` を無視する)。
2. **``a`` が段か連続か** —— ``a`` を細かく掃いて、出力の変化が**跳ぶ**なら段(離散)、
   なめらかなら連続。
3. **段の切り替え点** —— 跳んだ位置。「``3,5,7,9`` に振る」とだけ書かれていて、
   a=0.5 が 5 なのか 7 なのかが分からない、という穴を埋める。

**測れなかったものは「測れなかった」と返す**(推測で埋めない)。出力の形が変わる op、
乱数を含む op、例外を出す op は対象外。

使い方::

    py -3.11 tools/impl2/knob_probe.py --ops mean_box,gamma
    py -3.11 tools/impl2/knob_probe.py --all-image --json docs/op_knob.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

#: 段差を段とみなす閾値。連続な op の隣り合う出力差はこれより桁違いに小さい。
JUMP = 1e-6
#: 「効いている」とみなす最小の差。
EFFECT = 1e-9


def _probe_images(n: int = 24) -> list[np.ndarray]:
    """**構造の違う入力を複数枚**。1 枚では足りない。

    2026-09-16、縞模様 1 枚だけで測って `xcv_stylization` の ``a`` が「効かない」と
    判定しかけた。同じ 24x24 でも、テクスチャ + 雑音の画像に替えると ``sigma_r`` で
    出力が 184/255 動く —— **つまみは効いており、探針がパラメータを励起できていな
    かっただけ**だった。バグを 1 件でっち上げる寸前で、原因は探針 1 枚
    ([[feedback_one_probe_input_is_not_coverage]])。

    平滑化・エッジ保存・形態学・周波数のどれかには必ず反応が出るよう、
    傾斜 / 縞 / テクスチャ+雑音 / 塊と穴 / 高周波 を混ぜる。
    """
    rng = np.random.default_rng(20260916)
    y, x = np.mgrid[0:n, 0:n]
    out = []

    stripes = np.outer(np.ones(n), np.linspace(0.05, 0.95, n)).copy()
    stripes[::5, :] = 0.9
    stripes[:, ::7] = 0.15
    stripes[n // 3:n // 2, n // 3:n // 2] = 1.0
    out.append(stripes)

    tex = np.clip((np.sin(x / 6.0) + np.cos(y / 5.0)) * 0.25 + 0.5
                  + rng.normal(0, 0.05, (n, n)), 0, 1)
    out.append(tex)                                   # ← これが無いと励起できない op がある

    blobs = np.zeros((n, n))
    blobs[3:10, 3:10] = 1.0
    blobs[5:8, 5:8] = 0.2
    blobs[14:20, 14:20] = 0.8
    blobs += rng.normal(0, 0.02, (n, n))
    out.append(np.clip(blobs, 0, 1))

    hi = ((x + y) % 2).astype(np.float64) * 0.6 + 0.2   # 最高周波
    out.append(hi)

    return out


def _run(fs, op: str, img: np.ndarray, a: float, b: float):
    out = np.asarray(fs.apply(img.copy(), op, a=a, b=b), np.float64)
    if not np.isfinite(out).all():
        return None
    return out


def measure(op: str, steps: int = 51) -> dict:
    import fullseye as fs

    imgs = _probe_images()
    rec: dict = {"op": op, "steps": steps, "n_probe_images": len(imgs)}
    img = imgs[0]

    # 再現性: 同じ引数で 2 回走らせて違えば、この測定法は使えない(乱数を含む op)
    try:
        r1 = _run(fs, op, img, 0.5, 0.5)
        r2 = _run(fs, op, img, 0.5, 0.5)
    except Exception as e:
        return {**rec, "status": "not_applicable", "reason": f"{type(e).__name__}: {e}"[:140]}
    if r1 is None or r2 is None:
        return {**rec, "status": "not_applicable", "reason": "出力に非有限が混じる"}
    if r1.shape != img.shape:
        return {**rec, "status": "not_applicable", "reason": "出力の形が入力と違う"}
    if float(np.max(np.abs(r1 - r2))) > EFFECT:
        return {**rec, "status": "not_applicable", "reason": "同じ引数で結果が変わる(乱数を含む)"}

    # --- b は効くか ------------------------------------------------------- #
    b_diff = 0.0
    for im in imgs:                      # **全部の探針で試す**。1 枚で 0 でも他で動く
        ref = _run(fs, op, im, 0.5, 0.5)
        if ref is None or ref.shape != im.shape:
            return {**rec, "status": "not_applicable", "reason": "b の基準を取れない"}
        for b in (0.0, 0.25, 0.75, 1.0):
            o = _run(fs, op, im, 0.5, b)
            if o is None or o.shape != ref.shape:
                return {**rec, "status": "not_applicable", "reason": "b を振ると形が変わる/非有限"}
            b_diff = max(b_diff, float(np.max(np.abs(o - ref))))
    rec["b_effect"] = b_diff
    rec["b_used"] = b_diff > EFFECT

    # --- a を掃く --------------------------------------------------------- #
    xs = np.linspace(0.0, 1.0, steps)
    per_image = []
    for im in imgs:                      # **全部の探針で掃く**。最も動いた 1 枚で判定
        prev, d = None, []
        for a in xs:
            o = _run(fs, op, im, float(a), 0.5)
            if o is None or o.shape != im.shape:
                return {**rec, "status": "not_applicable", "reason": "a を振ると形が変わる/非有限"}
            if prev is not None:
                d.append(float(np.max(np.abs(o - prev))))
            prev = o
        per_image.append(np.asarray(d))
    diffs = max(per_image, key=lambda d: d.sum())
    rec["a_effect_per_image"] = [round(float(d.sum()), 6) for d in per_image]
    rec["a_effect"] = float(diffs.sum())
    if diffs.max(initial=0.0) <= EFFECT:
        rec["status"] = "determined"
        rec["a_kind"] = "unused"
        rec["breakpoints"] = []
        return rec

    # 段 = 「ほぼ 0 の区間」に挟まれた跳び。連続なら全区間で同程度に動く。
    jumps = [i for i, d in enumerate(diffs) if d > JUMP]
    flat = [i for i, d in enumerate(diffs) if d <= EFFECT]
    if flat and len(jumps) <= max(6, steps // 8):
        rec["a_kind"] = "discrete"
        # 跳んだ区間の中点を切り替え点とする(掃きの分解能ぶんの幅がある)
        rec["breakpoints"] = [round(float((xs[i] + xs[i + 1]) / 2), 4) for i in jumps]
        rec["breakpoint_resolution"] = round(float(xs[1] - xs[0]), 4)
    else:
        rec["a_kind"] = "continuous"
        rec["breakpoints"] = []
    rec["status"] = "determined"
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ops")
    ap.add_argument("--all-image", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--json")
    a = ap.parse_args()

    names = [o.strip() for o in (a.ops or "").split(",") if o.strip()]
    if a.all_image:
        idx = json.loads((ROOT / "docs" / "OP_INDEX.json").read_text(encoding="utf-8"))
        names += [o["name"] for o in idx["ops"]
                  if o["tier"] in ("registry", "color")
                  and o["in_sort"] == "image" and o["out_sort"] == "image"]
    names = list(dict.fromkeys(names))
    if a.limit:
        names = names[:a.limit]
    if not names:
        print("op を指定してください(--ops か --all-image)"); return 2

    out, tally = [], {}
    for op in names:
        try:
            r = measure(op)
        except Exception as e:                       # 測定器が落ちても全体は続ける
            r = {"op": op, "status": "not_applicable", "reason": f"{type(e).__name__}: {e}"[:140]}
        out.append(r)
        key = r.get("a_kind") or r["status"]
        tally[key] = tally.get(key, 0) + 1
        line = f"[{r['status']:14s}] {op:24s}"
        if r["status"] == "determined":
            line += f" a={r['a_kind']:10s} b={'使う' if r.get('b_used') else '未使用'}"
            if r.get("breakpoints"):
                line += f" 切替点 {r['breakpoints']}"
        else:
            line += " " + str(r.get("reason", ""))[:50]
        print(line)

    print("\n--- 集計 ---")
    for k, v in sorted(tally.items(), key=lambda x: -x[1]):
        print(f"  {k:16s} {v}")
    det = [r for r in out if r["status"] == "determined"]
    print(f"  b を実際に使う op: {sum(1 for r in det if r.get('b_used'))} / {len(det)}")
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n{a.json} に書いた")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
