# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 曲がった薄板の3D非剛体位置合わせ (non-rigid registration).

問題(素朴な言葉で):
    平らなカード(点群テンプレート)を手で少し曲げると、点は全体がねじれたのではなく
    「場所ごとに違う量」ずれる。回転+並進だけの剛体位置合わせでは、この場所ごとの
    曲がりを吸収できない。曲げを打ち消すには、なめらかに伸び縮みする非剛体変形が要る。

方法(3つのopを自然に連鎖):
    1) tps_fit   : 少数の制御点対応(平らな位置 → 曲げた位置)から、既知のなめらかな
                   Thin-Plate-Spline(TPS)曲げ変形を作る。
    2) tps_warp  : その曲げをテンプレート全点に適用して「標的(target)」を合成する。
                   さらにセンサノイズを足す(=現実のスキャンを模す)。
    3) register_nonrigid : 対応が未知の前提で、テンプレートを標的へ非剛体で寄せる
                   (最近傍対応 → TPS 再当てはめの反復)。

検証(GT):
    標的は「テンプレートを既知TPSで曲げた点」なので、各点の真の対応先(ノイズ無しの
    曲げ位置 clean_bent[i])が分かっている。位置合わせ後の対応点距離
    mean_i ||warped[i] - clean_bent[i]|| を測る。
    - 成功条件: この距離が注入ノイズの床(≈ σ·1.6)まで縮む(それ以下には原理的に
      下げられない=足したノイズは消せない)。実測 ≈ 1.1×床。
    - beat-the-null: 「剛体だけ」の最良解(対応既知の Kabsch=剛体位置合わせの上限性能)
      では曲げの曲率(非アフィン成分)を吸収できず残差が大きいまま(実測 ≈ 4×床)。
      非剛体がそれを 1/4 未満まで下回ることを要求する。
      補足: 半波正弦の曲げは中央対称なので、剛体の平面傾け(x に線形)では相殺できない
      曲率がまるごと残る。ここが「剛体では原理的に無理」の根拠。
    - さらに、tps_warp が制御点上で厳密に写る(λ=0 の内挿性)ことも確認する。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from deform3d import tps_fit, tps_warp, register_nonrigid


def flat_sheet(nx=9, ny=9, size=10.0):
    """z=0 の平らな格子点群 (nx*ny, 3) を返す(テンプレート=曲げる前のカード)。"""
    xs = np.linspace(0.0, size, nx)
    ys = np.linspace(0.0, size, ny)
    gx, gy = np.meshgrid(xs, ys, indexing="ij")
    pts = np.stack([gx.ravel(), gy.ravel(), np.zeros(gx.size)], axis=1)
    return pts.astype(np.float64)


def analytic_bend(pts, size=10.0, amp=3.0):
    """x に沿って半波正弦で持ち上げるなめらかな曲げ(剛体では表せない非線形変形)。

    z' = amp * sin(pi * x / size)。両端 z=0、中央 z=amp。これは回転+並進では
    再現できない(場所ごとに持ち上げ量が違う)=真の非剛体変形。
    """
    out = pts.copy()
    out[:, 2] = amp * np.sin(np.pi * pts[:, 0] / size)
    return out


def kabsch_rigid(a, b):
    """既知対応 a[i]->b[i] の最良剛体変換(回転R+並進t)を Kabsch で解き、
    変換後の a を返す。これは「剛体位置合わせの上限性能」= beat-the-null 基準線。

    対応を与えているので ICP のような反復・初期値問題は無く、剛体で到達しうる
    最小残差そのものを与える(=非剛体がこれを下回れば、曲げの吸収は剛体には
    原理的に無理だったと言える)。
    """
    ca = a.mean(axis=0)
    cb = b.mean(axis=0)
    A = a - ca
    B = b - cb
    H = A.T @ B
    U, _, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    D = np.diag([1.0, 1.0, d])
    R = Vt.T @ D @ U.T
    t = cb - R @ ca
    return a @ R.T + t


def mean_corr_dist(x, y):
    """既知対応での平均対応点距離 mean_i ||x[i] - y[i]||。"""
    return float(np.mean(np.linalg.norm(x - y, axis=1)))


def main():
    rng = np.random.default_rng(0)

    size = 10.0
    template = flat_sheet(nx=9, ny=9, size=size)      # 平らなカード(81点)

    # --- 1) tps_fit: 既知のなめらかな曲げTPSを「制御点対応」から作る ---
    #   制御点=粗い格子。その平らな位置(src)→ 解析的に曲げた位置(dst)。
    ctrl_src = flat_sheet(nx=4, ny=4, size=size)       # 制御点 16 点(>=4 必須)
    ctrl_dst = analytic_bend(ctrl_src, size=size, amp=3.0)
    bend_model = tps_fit(ctrl_src, ctrl_dst, lam=0.0)  # λ=0 → 制御点で厳密内挿

    # 制御点上で tps_warp が厳密に写ることの確認(TPS 内挿性)。
    ctrl_check = tps_warp(bend_model, ctrl_src)
    ctrl_exact_err = float(np.max(np.linalg.norm(ctrl_check - ctrl_dst, axis=1)))

    # --- 2) tps_warp: 曲げをテンプレート全点へ適用 → clean な標的、+ノイズ ---
    clean_bent = tps_warp(bend_model, template)        # ノイズ無しの真の対応先
    scale = float(np.linalg.norm(clean_bent.max(0) - clean_bent.min(0)))  # 対角長
    noise_sigma = 0.01 * scale                         # センサノイズ = スケールの1%
    target = clean_bent + rng.normal(0.0, noise_sigma, clean_bent.shape)

    # ノイズ床(3Dガウスの距離の期待値 ≈ σ·1.596、χ分布 df=3 の平均)。
    noise_floor = noise_sigma * 1.5957691216057308

    # --- 3) register_nonrigid: 対応未知の前提で template を target へ非剛体で寄せる ---
    #   λ は小さめ(細かい曲げを回復)。返る warped は src=template と同じ並びなので
    #   clean_bent[i] が各 warped[i] の真の対応先になる(GT が測れる)。
    warped, model, info = register_nonrigid(template, target, iters=40, lam=0.02)

    # beat-the-null: 対応既知の最良剛体(Kabsch)= 剛体位置合わせの上限性能。
    rigid_null = kabsch_rigid(template, target)

    d_nonrigid = mean_corr_dist(warped, clean_bent)    # 非剛体後の対応点距離
    d_rigid = mean_corr_dist(rigid_null, clean_bent)   # 剛体だけの残差(null)
    d_before = mean_corr_dist(template, clean_bent)     # 位置合わせ前(平ら vs 曲げ)

    print(f"点数(template/target)     : {template.shape[0]} / {target.shape[0]}")
    print(f"物体スケール(対角長)       : {scale:.3f}")
    print(f"注入ノイズ σ               : {noise_sigma:.4f}  (スケールの1%)")
    print(f"ノイズ床(距離の期待値)     : {noise_floor:.4f}")
    print(f"制御点での tps_warp 誤差    : {ctrl_exact_err:.2e}  (λ=0 内挿→ほぼ0)")
    print(f"位置合わせ前の対応点距離    : {d_before:.4f}  (平ら vs 曲げ)")
    print(f"beat-the-null 剛体(Kabsch) : {d_rigid:.4f}  (剛体は曲げを吸収できない)")
    print(f"非剛体後の対応点距離        : {d_nonrigid:.4f}  (ノイズ床の水準まで縮む)")
    print(f"register_nonrigid info     : best_iter={info['best_iter']} "
          f"rms={info['rms']:.4f} rms_init={info['rms_init']:.4f} "
          f"converged={info['converged']}")

    # --- GT アサーション ---
    # (a) TPS 内挿性: 制御点上では厳密に写る。
    assert ctrl_exact_err < 1e-8, \
        f"tps_warp が制御点で厳密に写らない: {ctrl_exact_err:.2e}"
    # (b) 非剛体はノイズ床の水準まで縮む(足したノイズ以下には原理的に下げられない)。
    assert d_nonrigid < 3.0 * noise_floor, \
        f"非剛体後の距離がノイズ床まで縮んでいない: {d_nonrigid:.4f} vs 床 {noise_floor:.4f}"
    # (c) beat-the-null: 剛体だけの最良解を大きく下回る(曲げの吸収は剛体には無理)。
    assert d_nonrigid < 0.25 * d_rigid, \
        f"非剛体が剛体nullを十分下回らない: {d_nonrigid:.4f} vs 剛体 {d_rigid:.4f}"
    # (d) 剛体nullは「位置合わせ前」から大きく改善しない(曲げが残る=nullが弱い証拠)。
    assert d_rigid > 5.0 * noise_floor, \
        f"剛体nullがノイズ床近くまで下がってしまい null として機能しない: {d_rigid:.4f}"

    print(f"PASS: 非剛体後 {d_nonrigid:.4f} <= ノイズ床 {noise_floor:.4f} の3倍、"
          f"かつ剛体null {d_rigid:.4f} の1/4未満(曲げを吸収)、"
          f"制御点内挿誤差 {ctrl_exact_err:.1e}")


if __name__ == "__main__":
    main()
