# -*- coding: utf-8 -*-
"""事例: 体積の時系列(4D)と動画を、動きの分かった合成で確かめる(live4d ギャラリー)

平たく言うと:
  live4d は「時間とともに変わる 3-D の体積」(volseq = (T, Z, Y, X))を扱う族。体積を断面や最大値投影で
  動画に畳む op、動きの速さを測る op、動画のコマの間を流れで埋める op がある。ここでは
  「どこに何があって、毎コマどれだけ動くか」を自分で決めた合成データを作り、その真値と照合する。
  外れたら exit 1。図は作らない、乱数は seed 固定。

確かめ方(op ごとの真値):
  * volseq_cut_video      —— position = k/(n−1) はちょうど k 枚目の断面、3 つの plane で numpy の切り出しとビット一致
  * volseq_mip_video      —— 1 点だけ光る voxel の投影は、その (y, x) にだけ値が出る / 一般に断面 ≤ MIP、全軸で S.max と一致
  * volseq_speed          —— 1 voxel/コマで x に平行移動する滑らかな塊の中心で |d| ≈ 1、止まった塊で ≈ 0、形 (T−1, Z, Y, X)
  * video_interpolate_flow —— 2 倍のコマ数で動画を作り半分に間引く → 2 倍に補間 → 抜いたコマと比べ、
                            ただの平均(二重像)より誤差がずっと小さい。元のコマはそのまま残る

    py -3.11 examples/gallery_live4d_volseq_truth.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402

import live4d as L4  # noqa: E402

ROWS: list = []


def check(op: str, what: str, expected: str, got: str, ok: bool) -> None:
    """表の 1 行を貯める(何を期待し、何が出て、合ったか)。"""
    ROWS.append((op, what, expected, got, bool(ok)))


def blob(shape, centre, sigma):
    """中心 ``centre``・幅 ``sigma`` のガウスの塊(次元は shape に合わせる)。"""
    grids = np.meshgrid(*[np.arange(n, dtype=np.float64) for n in shape], indexing="ij")
    r2 = sum((g - c) ** 2 for g, c in zip(grids, centre))
    return np.exp(-0.5 * r2 / sigma ** 2)


def demo_fold() -> None:
    rng = np.random.default_rng(0)
    S = rng.random((3, 6, 7, 8))
    ok_all = True
    for plane, axis in (("xy", 1), ("xz", 2), ("yz", 3)):
        n = S.shape[axis]
        for k in (0, 2, n - 1):
            got = L4.volseq_cut_video(S, plane=plane, position=k / (n - 1))
            ok_all &= np.array_equal(got, np.take(S, k, axis=axis))
    check("volseq_cut_video", "3 つの plane × position = k/(n−1)(k = 0, 2, 末尾)", "k 枚目の断面とビット一致",
          f"一致 {ok_all}、xy の形 {L4.volseq_cut_video(S, 'xy', 0.5).shape}", ok_all)

    P = np.zeros((4, 5, 6, 7))
    for t in range(4):
        P[t, 3, 1 + t, 2] = 1.0           # 1 点が毎コマ y に 1 進む(z = 3、x = 2)
    mz = L4.volseq_mip_video(P, axis=1)
    where = [tuple(int(v) for v in np.argwhere(mz[t])[0]) for t in range(4)]
    single = all(int((mz[t] > 0).sum()) == 1 for t in range(4))
    check("volseq_mip_video", "1 点が (z 3, y 1+t, x 2) で光る、z 軸に投影", "各コマ 1 画素だけ、(y, x) = (1+t, 2)",
          f"{where}、各コマ 1 画素 {single}", single and where == [(1 + t, 2) for t in range(4)])
    eq = all(np.array_equal(L4.volseq_mip_video(S, axis=a), S.max(axis=a)) for a in (1, 2, 3))
    below = all(np.all(L4.volseq_cut_video(S, plane=p, position=0.4) <= L4.volseq_mip_video(S, axis=a))
                for p, a in (("xy", 1), ("xz", 2), ("yz", 3)))
    check("volseq_mip_video", "乱数の体積で 3 軸", "S.max(axis) と一致、どの断面も MIP 以下", f"一致 {eq}、断面 ≤ MIP {below}",
          eq and below)


def demo_speed() -> None:
    T, shape = 4, (16, 20, 28)
    mov = np.stack([blob(shape, (8, 10, 10 + t), 2.5) for t in range(T)])
    still = np.stack([blob(shape, (8, 10, 12), 2.5) for _ in range(T)])
    v = L4.volseq_speed(mov)
    v0 = L4.volseq_speed(still)
    centre = [float(v[t, 8, 10, 10 + t]) for t in range(T - 1)]
    check("volseq_speed", "x に 1 voxel/コマ進む塊(σ 2.5)の中心", "形 (3, 16, 20, 28)、|d| = 1 ± 0.15",
          f"形 {v.shape}、中心の速さ {np.round(centre, 3).tolist()}",
          v.shape == (T - 1,) + shape and all(abs(c - 1.0) < 0.15 for c in centre))
    check("volseq_speed", "止まった塊", "|d| ≈ 0(最大 < 0.05)", f"最大 {float(v0.max()):.2e}", float(v0.max()) < 0.05)


def demo_interp() -> None:
    H, W, n = 40, 56, 9
    truth = np.stack([blob((H, W), (20 + 0.5 * t, 12 + 1.5 * t), 3.0) for t in range(n)])
    half = truth[::2]                                    # 5 コマに間引く(1 コマ 3 px 進む)
    out = L4.video_interpolate_flow(half, factor=2)
    keep = np.array_equal(out[::2], half)
    err = [float(np.abs(out[k] - truth[k]).max()) for k in range(1, n, 2)]
    naive = [float(np.abs(0.5 * (truth[k - 1] + truth[k + 1]) - truth[k]).max()) for k in range(1, n, 2)]
    check("video_interpolate_flow", "形と元のコマ", f"(5 + 4·1, 40, 56) = (9, 40, 56)、偶数番は入力のまま",
          f"{out.shape}、元のコマが残る {keep}", out.shape == (n, H, W) and keep)
    check("video_interpolate_flow", "抜いた 4 コマとの最大誤差(ピークは 1)", "どのコマもただの平均の 1/3 未満",
          f"補間 {np.round(err, 3).tolist()} / 平均 {np.round(naive, 3).tolist()}",
          all(e < a / 3 for e, a in zip(err, naive)))


def main() -> int:
    t0 = time.time()
    demo_fold()
    demo_speed()
    demo_interp()
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
