# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""返り値の自己診断(TRIZ #25 セルフサービス)と、昇格先の対比図。

「この出力は意味があるか」は画像処理の問いで、LLM に画素を見せて判断させる必然は無い。
fullseye 自身が数値で答える —— 走査の規律は Studio 右パネルのもの
([[feedback_ran_is_not_meaningful_output]]): **標準偏差 0 / 値域 0.1 未満 / 空 / 非有限**。

★判定(``verdict``)は**必ず生の数値と併記**する。言葉だけ返すと、判定器が中身を見て
いなくても「健全」と言えてしまう(今夜 2 度踏んだ形)。受け手が検算できる形にする。

免除は今夜作った 2 つの台帳を正本として引く: ``ops.NONFINITE_IS_MEANINGFUL``(inf が
答えの op)と ``ops.UNIT_RANGE_IS_NOT_THE_CONTRACT``(image を名乗るが物理量を運ぶ op)。
判定器が「距離画像は値域が広いから異常」と嘘をつかないため。
"""
from __future__ import annotations

import numpy as np

THUMB_H = 96          # 昇格先の小図の高さ(px)。~100 トークン相当を狙う
LOW_RANGE = 0.1       # 値域がこれ未満なら「ほぼ平ら」
SATURATED = 0.98      # 0 と 1 に張り付いた画素の割合がこれ以上なら「飽和」


def stats_of(x) -> dict:
    """どんな返り値も数値で要約する。空・非有限・飽和を別々に数える。"""
    if isinstance(x, (bool, int, float, np.generic)):
        v = float(x)
        return {"kind": "scalar", "value": v, "finite": bool(np.isfinite(v))}
    if isinstance(x, dict) and "cs" in x:
        cs = x.get("cs") or []
        return {"kind": "contour", "n_contours": len(cs),
                "n_points": int(sum(len(c) for c in cs)), "shape": list(x.get("shape") or [])}
    if not isinstance(x, np.ndarray):
        return {"kind": type(x).__name__, "repr": repr(x)[:120]}
    a = x
    out = {"kind": "array", "shape": list(a.shape), "dtype": str(a.dtype), "size": int(a.size)}
    if a.size == 0:
        return out
    if a.dtype.kind not in "fiub":
        out["repr"] = repr(a.ravel()[:4])[:120]
        return out
    f = a.astype(np.float64, copy=False)
    fin = np.isfinite(f)
    nf = int(a.size - int(fin.sum()))
    out["nonfinite"] = nf
    out["nonfinite_pct"] = round(100.0 * nf / a.size, 3)
    if fin.any():
        g = f[fin]
        mn, mx = float(g.min()), float(g.max())
        out.update({"min": mn, "max": mx, "mean": float(g.mean()), "std": float(g.std()),
                    "range": mx - mn,
                    "zero_pct": round(100.0 * float(np.mean(g <= 0.0)), 3),
                    "one_pct": round(100.0 * float(np.mean(g >= 1.0)), 3)})
        # 値の種類(大きい配列は標本で)
        sample = g if g.size <= 200_000 else g[:: max(1, g.size // 200_000)]
        out["unique_sampled"] = int(np.unique(sample).size)
    return out


def verdict_of(st: dict, *, op_name: str | None, out_sort: str | None) -> dict:
    """数値から判定を作る。``escalate`` が真なら対比図を出す価値がある。"""
    import ops

    reasons: list[str] = []
    k = st.get("kind")
    if k == "scalar":
        if not st.get("finite", True):
            return {"verdict": "nonfinite", "reasons": ["値が非有限"], "escalate": False}
        return {"verdict": "ok", "reasons": ["スカラ %g" % st["value"]], "escalate": False}
    if k == "contour":
        if st["n_contours"] == 0:
            return {"verdict": "empty", "reasons": ["輪郭が 0 本"], "escalate": True}
        return {"verdict": "ok", "reasons": ["輪郭 %d 本 / %d 点" % (st["n_contours"], st["n_points"])],
                "escalate": False}
    if k != "array":
        return {"verdict": "unknown", "reasons": ["数値で要約できない返り値 %s" % k], "escalate": False}
    if st["size"] == 0:
        return {"verdict": "empty", "reasons": ["返り値が空(size=0)"], "escalate": True}
    if "min" not in st:
        return {"verdict": "unknown", "reasons": ["数値配列でない(%s)" % st.get("dtype")], "escalate": False}

    nf_ok = op_name in ops.NONFINITE_IS_MEANINGFUL
    range_ok = op_name in ops.UNIT_RANGE_IS_NOT_THE_CONTRACT
    if st["nonfinite"] > 0 and not nf_ok:
        reasons.append("非有限が %d 画素(%.3g%%)" % (st["nonfinite"], st["nonfinite_pct"]))
    if st["nonfinite"] > 0 and nf_ok:
        reasons.append("非有限 %d 画素はこの op の答え(%s)" % (st["nonfinite"], ops.NONFINITE_IS_MEANINGFUL[op_name][:40]))
    if st["std"] == 0.0:
        reasons.append("定数(std=0, 値=%g)" % st["min"])
        return {"verdict": "constant", "reasons": reasons, "escalate": True}
    if st["zero_pct"] + st["one_pct"] >= 100.0 * SATURATED and out_sort in ("image", "color") and not range_ok:
        reasons.append("飽和(0 が %.1f%%、1 が %.1f%%)" % (st["zero_pct"], st["one_pct"]))
        return {"verdict": "saturated", "reasons": reasons, "escalate": True}
    if st["range"] < LOW_RANGE and out_sort in ("image", "color") and not range_ok:
        reasons.append("値域が狭い(range=%.3g < %.1f)" % (st["range"], LOW_RANGE))
        return {"verdict": "flat", "reasons": reasons, "escalate": True}
    if st["nonfinite"] > 0 and not nf_ok:
        return {"verdict": "nonfinite", "reasons": reasons, "escalate": True}
    outside = st["min"] < -1e-9 or st["max"] > 1 + 1e-9
    if outside and range_ok:
        reasons.append("[0,1] の外だがこの op は物理量を運ぶ(%s)" % ops.UNIT_RANGE_IS_NOT_THE_CONTRACT[op_name][:40])
    elif outside and out_sort in ("image", "region", "color"):
        # `test_every_image_op_stays_in_the_unit_range` と同じ契約を、実行時にも当てる。
        # 台帳に無い op が [0,1] を出たら、それは下流で黙って意味を失う値。
        reasons.append("image を名乗るのに [0,1] の外(min=%.4g max=%.4g)で、台帳に免除が無い"
                       % (st["min"], st["max"]))
        return {"verdict": "out_of_range", "reasons": reasons, "escalate": True}
    reasons.append("std=%.3g range=%.3g" % (st["std"], st["range"]))
    return {"verdict": "ok", "reasons": reasons, "escalate": False}


# --------------------------------------------------------------------------- #
# 昇格先の対比図                                                                 #
# --------------------------------------------------------------------------- #
def _panel(v, *, pseudocolor: bool) -> np.ndarray | None:
    """(H,W) はグレーのまま、[0,1] を超えるときだけ伸ばす(`gen_op_figures._panel` の
    作法)。物理量は疑似カラー(viridis)。(H,W,3) はそのまま。絵にならなければ None。"""
    import imgio
    a = np.asarray(v)
    if a.ndim == 3 and a.shape[-1] == 3:
        return np.clip(a.astype(np.float64), 0, 1)
    if a.ndim != 2 or a.size == 0:
        return None
    f = a.astype(np.float64)
    fin = np.isfinite(f)
    if not fin.any():
        return np.zeros(f.shape + (3,))
    if pseudocolor:
        return imgio.apply_cmap(np.where(fin, f, np.nan), name="viridis")
    lo, hi = float(f[fin].min()), float(f[fin].max())
    if lo < 0.0 or hi > 1.0:
        f = (f - lo) / (hi - lo) if hi > lo else np.zeros_like(f)
    g = np.clip(np.where(fin, f, 0.0), 0, 1)
    return np.repeat(g[..., None], 3, axis=-1)


def _resize_h(rgb: np.ndarray, h: int) -> np.ndarray:
    """最近傍で高さ h に。縮小の作法は問わない(見て判断する小図で、計測には使わない)。"""
    H, W = rgb.shape[:2]
    if H == h:
        return rgb
    w = max(1, int(round(W * h / H)))
    ys = np.clip((np.arange(h) * H / h).astype(int), 0, H - 1)
    xs = np.clip((np.arange(w) * W / w).astype(int), 0, W - 1)
    return rgb[ys][:, xs]


def side_by_side(inp, out, *, out_is_quantity: bool, h: int = THUMB_H) -> np.ndarray | None:
    """左が入力、右が出力(知識層の図と同じ並び)。1 px の白い仕切り。"""
    a = _panel(inp, pseudocolor=False)
    b = _panel(out, pseudocolor=out_is_quantity)
    if a is None and b is None:
        return None
    parts = []
    for p in (a, b):
        if p is not None:
            parts.append(_resize_h(p, h))
            parts.append(np.ones((h, 1, 3)))
    return np.concatenate(parts[:-1], axis=1)
