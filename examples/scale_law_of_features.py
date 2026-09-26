# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""scale_law_of_features — 特徴の**次元**を、真値を一つも使わずに測る。

    py -3.11 examples/scale_law_of_features.py

【この例が示すこと】
形を k 倍に拡大すると、長さは k 倍、面積は k² 倍、比は変わらない。だから
「k 倍にしたら値が何倍になったか」を測れば、**その op が返している量の次元**が
分かる —— HALCON の数値も、閉形式の真値も、一つも要らない。

    p = 0  尺度不変(比・形状指数・位相の個数・正規化した不変量)
    p = 1  長さ(周囲長・直径・厚み・楕円半径)
    p = 2  面積
    p = 4  2 次モーメント(正規化なし)

これは **metamorphic relation**(変成関係)という古典的な手口である。真値が
手に入らないプログラムを検算する方法として `Pseudo-oracles for non-testable
programs`(Weyuker 1981)、`Metamorphic Testing and Its Applications`
(Chen 2004)に名前がある。

★**この 1 枚で、2026-09-26 に直した 8 op のうち 5 本が出る。** そのとき実際に
直したのは HALCON のリファレンスを読み、閉形式と突き合わせてのことだった ——
つまり**外の一次情報が無ければ出なかった**。しかし次元を測るだけなら、
外の何も要らずに同じ 5 本が挙がる。

★そして同じ 1 枚が、**まだ開いている欠陥**も指す —— `moments_region_2nd` は
p≈0 だが、HALCON の同名演算子は正規化しない中心モーメントなので p=4 で
なければならない(`docs/KNOWN_ISSUES.md` §52)。

門 = `tests/test_scale_law_2026_09_26.py`(35 op すべてに次元を宣言させる)。

EXTEND: 自分の op を測るなら `shape()` を差し替える。非対称で穴のある形が要る
—— 対称な形では奇数次モーメントが厳密に 0 になり、比が取れない。
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fullseye as fs  # noqa: E402
import ops as _ops  # noqa: E402

#: 次元の名前(表示用)
DIM = {0.0: "無次元", 1.0: "長さ", 2.0: "面積", 4.0: "2 次モーメント",
       5.0: "3 次モーメント", 8.0: "アフィン不変量"}


def shape(n: int = 60) -> np.ndarray:
    """非対称で穴のある形。対称だと奇数次が厳密に 0 になり、比が取れない。"""
    m = np.zeros((n, n))
    m[12:34, 9:47] = 1.0        # 横長の板
    m[28:46, 18:28] = 1.0       # 足(非対称にする)
    m[18:22, 28:36] = 0.0       # 穴
    return m


def call(name: str, x: np.ndarray) -> np.ndarray:
    return np.ravel(np.asarray(fs.apply(np.array(x, np.float64), name), np.float64))


def exponents(name: str, ks: tuple[int, ...] = (2, 3)) -> tuple[np.ndarray, bool]:
    """k 倍に拡大したときの尺度指数 p(成分ごと)と、冪則かどうか。"""
    base = shape()
    v1 = call(name, base)
    out = []
    for k in ks:
        vk = call(name, np.kron(base, np.ones((k, k))))
        if vk.shape != v1.shape:
            return np.array([np.nan]), False
        p = []
        for a, b in zip(v1, vk):
            if abs(a) < 1e-12:
                p.append(0.0 if abs(b) < 1e-9 else np.nan)
            else:
                r = b / a
                p.append(np.log(abs(r)) / np.log(k) if r > 0 else np.nan)
        out.append(np.array(p, np.float64))
    same = bool(np.allclose(out[0], out[1], atol=0.12, equal_nan=True))
    return (out[0] + out[1]) / 2.0, same


def nearest_dim(p: float) -> str:
    if not np.isfinite(p):
        return "?"
    best = min(DIM, key=lambda d: abs(d - p))
    return DIM[best] if abs(best - p) < 0.15 else "★宣言のどれでもない"


def main() -> int:
    names = sorted(o.name for o in _ops._BY_NAME.values()
                   if o.in_sort == "region" and o.out_sort in ("feature", "match", "counts"))
    print("=" * 78)
    print("特徴の次元を、真値を一つも使わずに測る —— 形を k 倍にして何倍になるか")
    print("  対象 %d op / 拡大は np.kron(整数倍・補間なし)で 2 倍と 3 倍" % len(names))
    print("=" * 78)
    print("%-30s %-22s %s" % ("op", "尺度指数 p", "読み取れる次元"))
    print("-" * 78)
    by_dim: dict[str, list[str]] = {}
    for name in names:
        p, same = exponents(name)
        label = ", ".join("%.2f" % v for v in p)
        dim = nearest_dim(float(p[0])) if p.size else "?"
        flag = "" if same else "  ★冪則でない"
        print("%-30s %-22s %s%s" % (name, label, dim, flag))
        by_dim.setdefault(dim, []).append(name)

    print("\n次元ごとの内訳")
    for dim in sorted(by_dim, key=lambda d: -len(by_dim[d])):
        print("  %-18s %2d 本  %s" % (dim, len(by_dim[dim]),
                                      ", ".join(sorted(by_dim[dim])[:6])
                                      + (" ..." if len(by_dim[dim]) > 6 else "")))

    # --- 正規化すると次元が消えることを、その場で見せる ----------------------
    print("\n" + "=" * 78)
    print("★正規化すると次元が消える —— 2026-09-26 まで 8 op がこれだった")
    print("=" * 78)
    base = shape()
    for k in (1, 2, 3):
        m = np.kron(base, np.ones((k, k))) if k > 1 else base
        per = call("contlength", m)[0]
        normed = per / (2.0 * (m.shape[0] + m.shape[1]))
        print("  %dx  画素の周囲長 %8.2f   画布で割った値 %.6f" % (k, per, normed))
    p_raw = np.log(call("contlength", np.kron(base, np.ones((2, 2))))[0]
                   / call("contlength", base)[0]) / np.log(2.0)
    n1 = call("contlength", base)[0] / (2.0 * sum(base.shape))
    b2 = np.kron(base, np.ones((2, 2)))
    n2 = call("contlength", b2)[0] / (2.0 * sum(b2.shape))
    print("  -> 画素なら p=%.3f(長さ)、画布で割ると p=%.3f(無次元)"
          % (p_raw, np.log(n2 / n1) / np.log(2.0)))
    print("     つまり**同じ op でも、割った瞬間に別の量になる**。名前は変わらないので")
    print("     値域や有限性を見る門はどちらも通す —— 次元を見る門だけが区別できる。")

    # --- まだ開いている欠陥 --------------------------------------------------
    print("\n" + "=" * 78)
    print("★まだ開いている: moments 族(docs/KNOWN_ISSUES.md §52)")
    print("=" * 78)
    for name, want in (("moments_region_2nd", 4.0), ("moments_region_3rd", 5.0),
                       ("moments_region_central", 8.0)):
        p, _ = exponents(name)
        print("  %-28s 実測 p=%.3f   HALCON の次元 p=%.0f" % (name, p[0], want))
    print("  HALCON の同名演算子は**正規化しない**中心モーメントを返す。この repo は")
    print("  Hu の正規化不変量を 1 スカラーに合成しているので p が 0 になる。")
    print("  門はこれを免除でなく strict xfail で持つ —— 直った瞬間に「予期せぬ成功」で")
    print("  落ち、宣言表の更新を要求する。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
