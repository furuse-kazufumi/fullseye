# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""**何も写っていないフレーム**を入れたとき op が何を返すかを測る。

2026-09-16、codex に書かせた第 2 実装が `auto_threshold` で **`constant_half` と
`single_pixel` の 2 つだけ**食い違った(差はきっかり 1.0 = 二値出力の全反転)。他の
11 種の構造探針では厳密に一致していたので、争点は 1 点に絞れた ——
**ヒストグラムが縮退した画像で、自動しきい値は何を返すのか**。

実測すると族の中で答えが割れていた:

* `auto_threshold` / `bin_threshold` / `dyn_threshold` は c に関係なく **全部 0**
* `cv_otsu` は c=0 だけ 0 で、**c>0 なら全部 1**

`cv_otsu` の側は不具合ではない —— cv2 は定数画像に対しクラス間分散がどこでも 0 に
なるため**しきい値 0.0** を返し、``>0`` が真になって全画素が前景になる(一次情報で
確認済み)。Fullseye は OpenCV を忠実に再現している。**問題は、それがどこにも
書かれていないこと**である。検査の現場で真っ暗なフレームが来ると `cv_otsu` は
「欠陥 100%」と報告する。知らなければ必ず踏む。

**なぜ機械的に測れるか。** 端の規約には ``op(pad_P(x))[crop] == op(x)`` という恒等式が
あり、連結性にはそれが無くて確定手段が作れなかった。ここは**もっと単純**で、
恒等式すら要らない —— 定数画像を入れて出力を見るだけ。op の意味を知らなくても
「c を上げていったとき出力が跳ぶ場所」は観測できる。**推測する余地が無い。**

測って報告するのは 3 つ:

1. **定数画像に定数を返すか**(返さないなら位置依存か乱数。判定せず記録だけ)
2. **c を上げると出力が跳ぶか**、跳ぶならどこで(空フレームの分類が反転する点)
3. **c に依らず常に同じ値か**(「真っ白でも全部背景」のような、これも書くべき事実)

固定しきい値の op が 0.5 付近で跳ぶのは**正しい動作**であって穴ではない。この道具は
跳びの有無を返すだけで、それが穴かどうかは判定しない —— 判定するとノートに推測が
載る。穴かどうかは「ノートがその跳びに触れているか」で決まる。

使い方::

    py -3.11 tools/impl2/blank_probe.py --ops auto_threshold,cv_otsu
    py -3.11 tools/impl2/blank_probe.py --all-image --json docs/op_blank_frame.json
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
N = 24
#: 掃きの刻み。跳びの位置はこの幅ぶんの不確かさを持つ(そのまま記録する)。
STEPS = 101


def _levels() -> np.ndarray:
    return np.linspace(0.0, 1.0, STEPS)


def _classify(levels: np.ndarray, values: list[float | None]) -> dict:
    """出力値の列から「跳び」と「c に依らず一定か」を読む。

    跳びの判定は**観測された値域に対する相対量**で行う。絶対値 0.5 を閾にすると、
    出力が [0,0.01] に収まる op では永久に跳ばず、[0,255] の op では滑らかな変化まで
    跳びに見える。
    """
    vs = [v for v in values if v is not None]
    if not vs:
        return {"status": "not_applicable", "reason": "定数画像で値を取れない"}
    lo, hi = min(vs), max(vs)
    span = hi - lo
    if span <= EPS:
        return {"status": "determined", "constant_in_c": True,
                "value": round(float(lo), 12), "jumps": []}
    jumps = []
    for i in range(len(values) - 1):
        a, b = values[i], values[i + 1]
        if a is None or b is None:
            continue
        if abs(b - a) > 0.5 * span:
            jumps.append({"between": [round(float(levels[i]), 4),
                                      round(float(levels[i + 1]), 4)],
                          "from": round(float(a), 12), "to": round(float(b), 12)})
    return {"status": "determined", "constant_in_c": False,
            "out_min": round(float(lo), 12), "out_max": round(float(hi), 12),
            "jumps": jumps}


def measure(op: str) -> dict:
    import fullseye as fs

    rec: dict = {"op": op, "steps": STEPS}
    levels = _levels()
    values: list[float | None] = []
    non_constant_at: list[float] = []
    for c in levels:
        im = np.full((N, N), float(c))
        try:
            o = np.asarray(fs.apply(im.copy(), op, a=0.5, b=0.5), np.float64)
        except Exception as e:
            return {**rec, "status": "not_applicable",
                    "reason": f"{type(e).__name__}: {e}"[:140]}
        if o.shape != im.shape or not np.isfinite(o).all():
            return {**rec, "status": "not_applicable", "reason": "形が違う/非有限"}
        spread = float(o.max() - o.min())
        if spread > EPS:
            # **定数を入れたのに定数が返らない** —— 位置依存(端の扱い等)か乱数。
            # 判定はせず事実だけ残す。ここで「おかしい」と断じると推測が契約になる。
            non_constant_at.append(round(float(c), 4))
            values.append(None)
        else:
            values.append(float(o.flat[0]))
    rec["non_constant_output_at"] = non_constant_at[:12]
    rec["n_non_constant"] = len(non_constant_at)
    if len(non_constant_at) == len(levels):
        return {**rec, "status": "non_constant_output",
                "reason": "どの定数画像でも出力が一様にならない(位置依存か乱数)"}
    rec.update(_classify(levels, values))
    return rec


def _self_test() -> str:
    """**陽性対照**: 答えを知っている 3 つの参照で、跳び・一定・非一様を当てられるか。

    当てられない道具で op を測れば、出てくるのは事実ではなく思い込みになる。
    """
    levels = _levels()
    cases = []

    # (1) 0.5 で切る固定しきい値 -> 0.5 付近に跳びが 1 つ
    vs = [1.0 if c > 0.5 else 0.0 for c in levels]
    r = _classify(levels, vs)
    cases.append(("跳び 1 つ", len(r.get("jumps", [])) == 1 and not r["constant_in_c"]))

    # (2) 常に 0 を返す -> c に依らず一定、跳び無し
    r = _classify(levels, [0.0] * len(levels))
    cases.append(("c に依らず一定", r.get("constant_in_c") is True))

    # (3) 恒等 -> 一定でなく、跳びも無い(なめらか)
    r = _classify(levels, [float(c) for c in levels])
    cases.append(("なめらか", not r["constant_in_c"] and not r["jumps"]))

    ng = [n for n, ok in cases if not ok]
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
    print(f"陽性対照(答えを知っている参照で跳び/一定/なめらかを当てられるか): {st}")
    if st != "OK":
        print("→ 道具が当てられないので op は測らない(思い込みを事実として出さない)")
        return 3

    out = []
    for op in names:
        try:
            r = measure(op)
        except Exception as e:
            r = {"op": op, "status": "not_applicable",
                 "reason": f"{type(e).__name__}: {e}"[:140]}
        out.append(r)
        line = f"[{r['status']:20s}] {op:26s}"
        if r.get("constant_in_c"):
            line += f" c に依らず常に {r['value']:g}"
        elif r.get("jumps"):
            line += " 跳び " + ", ".join(f"{j['between'][0]:g}〜{j['between'][1]:g} で"
                                         f"{j['from']:g}→{j['to']:g}" for j in r["jumps"][:3])
        elif r["status"] == "determined":
            line += " なめらか(跳び無し)"
        else:
            line += " " + str(r.get("reason", ""))[:44]
        print(line)

    det = [r for r in out if r["status"] == "determined"]
    jump = [r for r in det if r.get("jumps")]
    flat = [r for r in det if r.get("constant_in_c")]
    print(f"\n測れた {len(det)} / {len(out)}")
    print(f"  空フレームの分類が跳ぶ op: {len(jump)}")
    print(f"  c に依らず常に同じ値を返す op: {len(flat)}")
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=2, ensure_ascii=False),
                                encoding="utf-8")
        print(f"\n{a.json} に書いた")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
