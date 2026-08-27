# -*- coding: utf-8 -*-
"""事例: ループ閉じ込みのポーズグラフSLAMバックエンド。

実問題: 移動ロボットが部屋を一周する。車輪オドメトリ(相対移動量の推定)には毎歩わずかな
誤差があり、それを積み上げると出発点に戻ってきたはずなのに地図上では出発点とズレる
(累積ドリフト)。ロボットが「ここは最初に居た場所だ」と気づく=ループ閉じ込みを検出
できたとき、その1本の制約で経路全体のズレをまとめて補正するのが pose_graph の役目。
ここでは合成した真の周回軌跡に対し、ノイズ入りオドメトリ積分(=生の推定)と、
ループ閉じ辺を足したポーズグラフ最適化の姿勢誤差を比較し、最適化後がドリフトを
下回ることを数値で確かめる。
"""
import numpy as np
import pose_graph as pg


def make_loop_truth(n=12, radius=3.0):
    """円周上に n 個の真姿勢を並べる(各ノードは進行方向を向く)。pose = [rvec(3)|t(3)]。"""
    poses = []
    for i in range(n):
        ang = 2 * np.pi * i / n
        pos = np.array([radius * np.cos(ang), radius * np.sin(ang), 0.0])
        yaw = ang + np.pi / 2                       # 円の接線方向(進行方向)を向く
        rvec = np.array([0.0, 0.0, yaw])            # z 軸まわりの回転のみ
        poses.append(np.concatenate([rvec, pos]))
    return np.array(poses)


def integrate_odometry(pose0, odo_edges, n):
    """node0 の真姿勢から、ノイズ入り相対姿勢(オドメトリ)を順に合成して軌跡を積分。
    これが「ループ閉じを使わない生の推定」= ドリフトが積み上がる。"""
    init = np.zeros((n, 6))
    init[0] = pose0
    for (i, j, rv, t, _wr, _wt) in odo_edges:       # 連続辺 i->i+1 を前提に順次積分
        Ri = pg.rvec_to_R(init[i][:3]); ti = init[i][3:]
        Rr = pg.rvec_to_R(rv);          tr = t
        Rj = Ri @ Rr                                 # 姿勢合成: world<-body_j
        tj = Ri @ tr + ti
        init[j] = np.concatenate([pg.R_to_rvec(Rj), tj])
    return init


def mean_position_error(poses, truth):
    """全ノードの並進誤差(真姿勢との距離)の平均 [m]。"""
    return float(np.mean([np.linalg.norm(poses[i, 3:] - truth[i, 3:]) for i in range(len(truth))]))


def main():
    rng = np.random.default_rng(7)
    n = 12
    truth = make_loop_truth(n=n, radius=3.0)

    # --- ノイズ入りオドメトリ辺(連続する node 間の相対姿勢に観測ノイズを加える) ---
    sigma_rot, sigma_trans = 0.015, 0.04
    odo = []
    for i in range(n - 1):
        rv, t = pg.relative_pose(truth[i], truth[i + 1])
        odo.append((i, i + 1,
                    rv + rng.normal(0, sigma_rot, 3),
                    t + rng.normal(0, sigma_trans, 3), 1.0, 1.0))

    # --- ループ閉じ辺: 最後のノード n-1 から node0 へ戻る相対姿勢(1本のノイズ観測) ---
    rvc, tc = pg.relative_pose(truth[n - 1], truth[0])
    closure = (n - 1, 0,
               rvc + rng.normal(0, sigma_rot, 3),
               tc + rng.normal(0, sigma_trans, 3), 1.0, 1.0)

    # --- 生の推定: node0 の真姿勢からノイズ入りオドメトリを積分(ドリフトが積算) ---
    init = integrate_odometry(truth[0], odo, n)
    raw_err = mean_position_error(init, truth)
    loop_gap_raw = np.linalg.norm(init[n - 1, 3:] - truth[n - 1, 3:])

    # --- ポーズグラフ最適化: オドメトリ辺 + ループ閉じ辺、node0 を固定して gauge を除く ---
    out = pg.optimize_pose_graph(init, odo + [closure], fix_first=True)
    opt_err = mean_position_error(out["poses"], truth)

    # node0 は固定制約通り真姿勢に一致しているか(gauge 固定の健全性確認)
    node0_fixed = np.allclose(out["poses"][0], truth[0])

    print(f"[生オドメトリ] 平均姿勢誤差 = {raw_err:.4f} m  (最終ノードのドリフト {loop_gap_raw:.4f} m)")
    print(f"[最適化後]     平均姿勢誤差 = {opt_err:.4f} m")
    print(f"[改善率]       {(1 - opt_err / raw_err) * 100:.1f}% ドリフト低減")
    print(f"[グラフ整合]   最適化後の辺残差 RMSE = {out['rmse']:.5f}")
    print(f"[gauge]        node0 は真姿勢に固定: {node0_fixed}")

    # === GT 検証 ===
    # 1) ループ閉じ最適化はドリフトを減らす(最適化後 < 生オドメトリ)
    assert opt_err < raw_err, (opt_err, raw_err)
    # 2) 実質的な低減(半分以下)であること
    assert opt_err < 0.5 * raw_err, (opt_err, raw_err)
    # 3) node0 は固定制約通り真姿勢
    assert node0_fixed
    # 4) 最適化がグラフをよく満たす(辺残差が小さく収束)
    assert out["rmse"] < 0.1, out["rmse"]
    print("OK: ループ閉じ込みのポーズグラフ最適化がオドメトリのドリフトを低減した")


if __name__ == "__main__":
    main()