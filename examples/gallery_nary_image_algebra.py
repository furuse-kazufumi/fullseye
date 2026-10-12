# -*- coding: utf-8 -*-
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 2 枚の画像・2 つの領域を受け取る op(n-ary 層 17 本)と identity を、numpy の独立な検算と集合の恒等式で確かめる

平たく言うと:
  進化のパイプラインは値を 1 本しか流さないので、「2 枚の画像を足す」「2 つの領域の和を取る」のような
  HALCON の多入力 op は別の層(``imgops_nary``)にある。呼び方は ``fullseye.apply([x1, x2], "<op 名>", a, b)``
  —— 入力を **リスト**で渡す。ここでは 1 本ずつ、答えが外から分かる入力で呼ぶ:
  画素値は 8 bit の格子(k/255)、領域は円盤と正方形。各行に「何を期待し、何が出て、合ったか」を印字し、
  外れたら exit 1。

確かめ方(op ごとの真値):
  * add_image / sub_image / mult_image / div_image —— ゲイン 1・オフセット 0 になる a, b で、numpy の和・差・積・商と一致
    (商は I1 = q·I2 と作って q が戻る)。sub_image は b = 0.5 で同じ画像どうしが一面 0.5 の灰色になる
  * abs_diff_image —— |I1 − I2| と一致し、max_image − min_image(独立な op どうし)とも一致、引数の順に依らない
  * max_image / min_image —— np.maximum / np.minimum と一致、max + min = I1 + I2
  * bit_and / bit_or —— 8 bit 整数のビット演算と一致、(a AND b) + (a OR b) = a + b
  * convol_image —— 中心の右に重み 1 のマスクは「右隣の画素を読む」(相関)。端は半画素対称の折り返し。3×3 の箱は 9 画素平均
  * union2 / intersection / difference / symm_difference —— numpy の論理演算と一致、|A∪B| = |A| + |B| − |A∩B|、
    対称差 = 和 − 積、(A − B) ∪ (A ∩ B) = A、A − B ≠ B − A
  * reduce_domain / overpaint_region / paint_gray —— 領域の外を 0 / 領域の中を a で塗る / source の非ゼロ画素(暗い 0.1 も)を塗る
  * identity —— 入力をそのまま返す(値も dtype も同じ)

    py -3.11 examples/gallery_nary_image_algebra.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402

import fullseye  # noqa: E402

ROWS: list = []
N = 40
RNG = np.random.default_rng(20261012)
K1 = RNG.integers(0, 256, size=(N, N))
K2 = RNG.integers(0, 256, size=(N, N))
I1 = K1 / 255.0                                   # 8 bit の格子に乗った濃淡(bit 演算の量子化が誤差を生まない)
I2 = K2 / 255.0
YY, XX = np.mgrid[0:N, 0:N]
A = (((YY - 16) ** 2 + (XX - 16) ** 2) <= 10 ** 2).astype(np.float64)   # 円盤
B = ((YY >= 14) & (YY < 34) & (XX >= 20) & (XX < 36)).astype(np.float64)  # 正方形(円盤と一部重なる)


def check(op: str, what: str, expected: str, got: str, ok: bool) -> None:
    """表の 1 行を貯める(何を期待し、何が出て、合ったか)。"""
    ROWS.append((op, what, expected, got, bool(ok)))


def run(inputs, name, a=0.5, b=0.5):
    """利用者の入口(``fullseye.apply`` にリストで渡す)。失敗は握り潰さない。"""
    return np.asarray(fullseye.apply(inputs, name, a, b, on_error="raise"), dtype=np.float64)


def _err(x, y) -> float:
    return float(np.max(np.abs(np.asarray(x, np.float64) - np.asarray(y, np.float64))))


def demo_arithmetic() -> None:
    out = run([I1, I2], "add_image", 0.5, 0.5)                    # ゲイン 0.5 + a = 1、オフセット b − 0.5 = 0
    want = np.clip(I1 + I2, 0, 1)
    check("add_image", "a = 0.5, b = 0.5(ゲイン 1・オフセット 0)", "clip(I1 + I2, 0, 1)", f"最大差 {_err(out, want):.1e}",
          _err(out, want) < 1e-12)
    out = run([I1, I2], "add_image", 0.25, 0.7)
    want = np.clip((I1 + I2) * 0.75 + 0.2, 0, 1)
    check("add_image", "a = 0.25, b = 0.7", "clip((I1 + I2)·0.75 + 0.2, 0, 1)(docstring の式)", f"最大差 {_err(out, want):.1e}",
          _err(out, want) < 1e-12)

    out = run([I1, I2], "sub_image", 0.5, 0.0)
    want = np.clip(I1 - I2, 0, 1)
    check("sub_image", "a = 0.5, b = 0(ゲイン 1・オフセット 0)", "clip(I1 − I2, 0, 1)", f"最大差 {_err(out, want):.1e}",
          _err(out, want) < 1e-12)
    out = run([I1, I1], "sub_image", 0.5, 0.5)
    check("sub_image", "同じ画像どうし、b = 0.5", "一面 0.5(差 0 が中間の灰色)", f"{out.min():.6f} .. {out.max():.6f}",
          _err(out, 0.5) < 1e-12)

    out = run([I1, I2], "mult_image", 1.0 / 3.0, 0.5)              # 0.5 + 1.5a = 1、b − 0.5 = 0
    want = I1 * I2
    check("mult_image", "a = 1/3, b = 0.5(ゲイン 1・オフセット 0)", "I1 · I2", f"最大差 {_err(out, want):.1e}", _err(out, want) < 1e-12)

    den = 0.2 + 0.8 * I2                                           # 分母を下限 1e-3 から遠ざける
    q = I1
    out = run([q * den, den], "div_image", 1.0, 0.5)               # 0.1 + 0.9a = 1
    check("div_image", "I1 = q·I2 と作って割る(a = 1)", "q が戻る", f"最大差 {_err(out, q):.1e}", _err(out, q) < 1e-12)
    out = run([np.full((4, 4), 0.5), np.zeros((4, 4))], "div_image", 1.0, 0.5)
    check("div_image", "0 で割る(分母の下限 1e-3)", "0.5/1e-3 = 500 → 1 で飽和", f"{out.min():.3f} .. {out.max():.3f}",
          _err(out, 1.0) == 0.0)

    ad = run([I1, I2], "abs_diff_image", 1.0 / 3.0)                # 0.5 + 1.5a = 1
    ad_rev = run([I2, I1], "abs_diff_image", 1.0 / 3.0)
    mx = run([I1, I2], "max_image")
    mn = run([I1, I2], "min_image")
    check("abs_diff_image", "a = 1/3(ゲイン 1)", "|I1 − I2|", f"最大差 {_err(ad, np.abs(I1 - I2)):.1e}", _err(ad, np.abs(I1 - I2)) < 1e-12)
    check("abs_diff_image", "max_image − min_image と照合 / 引数を入れ替える", "どちらも一致",
          f"{_err(ad, mx - mn):.1e} / {_err(ad, ad_rev):.1e}", _err(ad, mx - mn) < 1e-12 and _err(ad, ad_rev) == 0.0)
    check("max_image", "画素ごとの最大", "np.maximum(I1, I2)", f"最大差 {_err(mx, np.maximum(I1, I2)):.1e}",
          _err(mx, np.maximum(I1, I2)) == 0.0)
    check("min_image", "画素ごとの最小 / max + min", "np.minimum(I1, I2) / I1 + I2",
          f"{_err(mn, np.minimum(I1, I2)):.1e} / {_err(mx + mn, I1 + I2):.1e}",
          _err(mn, np.minimum(I1, I2)) == 0.0 and _err(mx + mn, I1 + I2) < 1e-15)

    band = run([I1, I2], "bit_and")
    bor = run([I1, I2], "bit_or")
    check("bit_and", "8 bit の格子の画素", "np.bitwise_and(k1, k2) / 255", f"最大差 {_err(band, (K1 & K2) / 255.0):.1e}",
          _err(band, (K1 & K2) / 255.0) == 0.0)
    check("bit_or", "同上 / (a AND b) + (a OR b)", "np.bitwise_or(k1, k2) / 255 / = a + b",
          f"{_err(bor, (K1 | K2) / 255.0):.1e} / {_err((band + bor) * 255.0, K1 + K2):.1e}",
          _err(bor, (K1 | K2) / 255.0) == 0.0 and _err((band + bor) * 255.0, K1 + K2) < 1e-9)


def demo_convolution() -> None:
    # ★公開の入口 ``fullseye.apply`` は n-ary の 2 入力に「同じ形」を要求する(3×3 のマスクは形の不一致で拒まれる)。
    #   画像と同じ大きさのゼロ配列の中央(scipy の原点 = N // 2)に置けば、同じマスクとして働く。
    c = N // 2
    mask = np.zeros((N, N))
    mask[c, c + 1] = 1.0                                           # 中心の右に重み 1
    out = run([I1, mask], "convol_image")
    pad = np.pad(I1, 1, mode="symmetric")                         # scipy の reflect = 半画素対称
    # 許容 2e-8: 実装はマスクを「絶対値の和 + 1e-8」で割る(ゼロ割よけ)ので、出力は相対 1e-8 だけ小さい。
    want = pad[1:-1, 2:]                                          # out[r, c] = I1[r, c + 1](相関なので反転しない)
    check("convol_image", "中心の右に重み 1 のマスク", "右隣の画素を読む(相関・端は折り返し)", f"最大差 {_err(out, want):.1e}",
          _err(out, want) < 2e-8)
    flipped = pad[1:-1, :-2]
    check("convol_image", "畳み込み(マスクを反転)なら左隣になる", "左隣とは一致しない", f"左隣との最大差 {_err(out, flipped):.2f}",
          _err(out, flipped) > 0.1)
    box = np.zeros((N, N))
    box[c - 1:c + 2, c - 1:c + 2] = 2.0                            # 絶対値の和で割られるので 1/9 の箱
    out = run([I1, box], "convol_image")
    want = sum(pad[dy:dy + N, dx:dx + N] for dy in range(3) for dx in range(3)) / 9.0
    check("convol_image", "3×3 の箱(重み 2 は正規化で消える)", "9 画素の平均", f"最大差 {_err(out, want):.1e}", _err(out, want) < 2e-8)


def demo_regions() -> None:
    a, b = A > 0.5, B > 0.5
    un = run([A, B], "union2")
    it = run([A, B], "intersection")
    df = run([A, B], "difference")
    df_rev = run([B, A], "difference")
    sd = run([A, B], "symm_difference")
    check("union2", f"円盤 {int(a.sum())} 画素 ∪ 正方形 {int(b.sum())} 画素", "A | B", f"{int(un.sum())} 画素",
          np.array_equal(un, (a | b).astype(float)))
    check("intersection", "A ∩ B / 包除: |A∪B| = |A| + |B| − |A∩B|", f"A & B / {int(a.sum() + b.sum() - (a & b).sum())}",
          f"{int(it.sum())} 画素 / {int(un.sum())}", np.array_equal(it, (a & b).astype(float)) and un.sum() == a.sum() + b.sum() - it.sum())
    back = run([df, it], "union2")
    check("difference", "A − B / (A − B) ∪ (A ∩ B)", "A & ~B / = A", f"{int(df.sum())} 画素 / 差 {_err(back, A):.0f}",
          np.array_equal(df, (a & ~b).astype(float)) and _err(back, A) == 0.0)
    check("difference", "順序を入れ替える(B − A)", "B & ~A(A − B とは別物)", f"{int(df_rev.sum())} 画素",
          np.array_equal(df_rev, (b & ~a).astype(float)) and not np.array_equal(df, df_rev))
    check("symm_difference", "A △ B / 和 − 積 / (A − B) + (B − A)", "A ^ B / 一致 / 一致",
          f"{int(sd.sum())} 画素 / {_err(sd, un - it):.0f} / {_err(sd, df + df_rev):.0f}",
          np.array_equal(sd, (a ^ b).astype(float)) and _err(sd, un - it) == 0.0 and _err(sd, df + df_rev) == 0.0)

    rd = run([I1, A], "reduce_domain")
    check("reduce_domain", "円盤で定義域を絞る", "中は I1 のまま・外は 0", f"中の最大差 {_err(rd[a], I1[a]):.1e}、外の最大 {rd[~a].max():.1e}",
          _err(rd[a], I1[a]) == 0.0 and rd[~a].max() == 0.0)
    op = run([I1, A], "overpaint_region", 0.25)
    check("overpaint_region", "円盤の中を a = 0.25 で塗る", "中は 0.25・外は I1 のまま",
          f"中 {op[a].min():.4f} .. {op[a].max():.4f}、外の最大差 {_err(op[~a], I1[~a]):.1e}",
          _err(op[a], 0.25) == 0.0 and _err(op[~a], I1[~a]) == 0.0)
    src = A * 0.1                                                 # 暗い source(0.1)—— 2026-09-03 までは消えていた
    pg = run([I1, src], "paint_gray")
    check("paint_gray", "暗い source(円盤の中が 0.1、外は 0)を塗り込む", "中は 0.1・外は I1 のまま",
          f"中 {pg[a].min():.4f} .. {pg[a].max():.4f}、外の最大差 {_err(pg[~a], I1[~a]):.1e}",
          _err(pg[a], 0.1) == 0.0 and _err(pg[~a], I1[~a]) == 0.0)


def demo_identity() -> None:
    arr = np.asarray(fullseye.apply(I1, "identity", on_error="raise"))
    check("identity", "濃淡画像をそのまま返す", "値・形・dtype が入力と同じ", f"最大差 {_err(arr, I1):.1e}、{arr.shape}、{arr.dtype}",
          arr.shape == I1.shape and arr.dtype == I1.dtype and _err(arr, I1) == 0.0)
    out = np.asarray(fullseye.apply(A, "identity", on_error="raise"))
    check("identity", "領域(0/1)もそのまま返す(sort = any)", "0/1 のまま一致", f"不一致 {int((out != A).sum())} 画素", np.array_equal(out, A))


def main() -> int:
    t0 = time.time()
    demo_arithmetic()
    demo_convolution()
    demo_regions()
    demo_identity()
    w_op = max(len(r[0]) for r in ROWS)
    print(f"{'op':<{w_op}} | 確かめたこと | 期待 | 出た値 | 判定")
    for op, what, exp, got, ok in ROWS:
        print(f"{op:<{w_op}} | {what} | {exp} | {got} | {'合格' if ok else '★不合格'}")
    bad = [r for r in ROWS if not r[4]]
    if bad:
        print(f"FAIL: {len(bad)}/{len(ROWS)} 行が外れた({', '.join(sorted({r[0] for r in bad}))})")
        return 1
    print(f"PASS: {len({r[0] for r in ROWS})} op を {len(ROWS)} 行の真値で確認({time.time() - t0:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
