# -*- coding: utf-8 -*-
"""事例: 動く物体のシーンフローを点群・ボクセル・画像平面の 3 表現で復元する (scene_flow).

平たく言うと: デプスカメラや LiDAR が「同じ物体の 2 時刻」を撮った。物体はフレーム間で少し
動いた(わずかに回って・ずれた)。この運動を、同じシーンの **3 つの見え方** から取り出す:

  (1) 点群として   … 各点がどこへ動いたか(密な変位=シーンフロー)を最近傍で拾い、その対応
                      から剛体運動 (R, t) を閉形式で当てる。別解として軟対応の CPD でも当て、
                      2 手法が一致することを相互チェックする。
  (2) ボクセルとして … 物体をボクセル密度場にして、既知の並進で動かし、Lucas-Kanade で
                      **密な per-voxel 運動場** を復元する(点群フローのボクセル版)。
  (3) 画像平面として … 物体の平らな面が動くと画像には homography が誘導される。復元した
                      剛体 (R, t) から平面 homography を作り、warp で実際に画素を動かして、
                      その写像が解析的な点対応と一致することを確かめる。

5 つの op を鎖でつなぐ:
    estimate_flow(frame0, frame1)         -> 最近傍シーンフロー(小運動なので対応=恒等)。
    fit_rigid(frame0, frame0 + flow)      -> フロー対応から Kabsch で (R, t) を復元。
    register_cpd_rigid(frame0, frame1)    -> 生点群から軟対応 EM で (R, t) を独立復元(相互検証)。
    scene_flow_lk(vol0, vol1)             -> ボクセル密度場の密な並進フロー場を復元。
    warp_by_plane(img, H)                 -> 復元 (R, t) が誘導する画像 homography を実現。

検証(GT): 合成データはすべて **既知の真値** を握って作る。真の剛体 (R_gt, t_gt)、真のボクセル
並進 shift、真の画素並進。各 op が真値を機械精度〜物理的に妥当な誤差で復元することを assert する:
    * estimate_flow : 対応が恒等になる小運動なので、フロー == 真の変位(丸め誤差以内)。
    * fit_rigid     : 回転誤差 < 1e-3 度・並進誤差 < 1e-6(厳密対応の Kabsch は本質的に厳密)。
    * register_cpd_rigid : 同 (R_gt, t_gt) を独立復元し、かつ fit_rigid と一致(2 手法の相互検証)。
    * scene_flow_lk : 中央領域の平均フロー ≈ 真の並進(誤差 < 0.15 voxel)、per-voxel EPE 中央値
                      も小さく、実行は決定的(2 回呼んで一致)。
    * warp_by_plane : (a) 整数並進 homography のワープが np.roll と機械精度一致、(b) 復元剛体が
                      誘導する homography のインパルス写像先が解析値 H^{-1}·landmark と一致。

beat-the-null: 各主張を「何もしない null」と対比する。
    * 剛体復元(fit_rigid / CPD)の回転誤差 ~1e-6 度 << 無運動 null(恒等との角 = 真回転 2 度)、
      並進誤差 ~1e-15 << 無運動 null(|t_gt|)。
    * scene_flow_lk の per-voxel EPE << ゼロフロー null(= |shift|)。
    * warp_by_plane はインパルスを ~30 画素動かす(無ワープ null=0 画素)、かつ整数並進ワープの
      対 np.roll 誤差 ~0 << 「ワープせず元画像のまま」の誤差(=並進で動いた画素の総量)。

限界(honest): 最近傍フロー(estimate_flow)と Kabsch(fit_rigid)は、変位が局所点間隔より十分
小さい **小運動** で対応が恒等になる前提で厳密。本例は格子間隔 1.0 に対し回転 2 度・並進 < 0.3 と
小さく設計しこの前提を満たす(NN 対応恒等率を実測 assert)。大変位では最近傍対応が崩れ fit_rigid は
悪化する — その領域は軟対応の CPD が担う(CPD は初期ずれに頑健)。scene_flow_lk は輝度一定を
仮定するため滑らかな低周波テクスチャで最良に働き、反復過多はむしろ発散する(iters=3 が最適)。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402
from scipy.ndimage import map_coordinates  # noqa: E402

from motion_seg3d import estimate_flow, fit_rigid  # noqa: E402
from deform3d import register_cpd_rigid  # noqa: E402
from match3d import scene_flow_lk  # noqa: E402
from plane_sweep import warp_by_plane, plane_homography  # noqa: E402


def rodrigues(axis, deg):
    """軸まわり deg 度の回転行列(ロドリゲス)。実装の Kabsch/SVD とは独立の真値生成器。"""
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    th = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * (K @ K)


def rot_err_deg(R_est, R_gt):
    """2 つの回転行列の間の測地角(度)= 復元誤差。"""
    c = (np.trace(np.asarray(R_est).T @ np.asarray(R_gt)) - 1.0) / 2.0
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


def box_lattice():
    """非対称な直方体格子(格子間隔 1.0、10x6x4 = 240 点)。

    3 辺長が違う(9x5x3)ので回転が一意に決まる(立方体だと回転対称で姿勢が定まらない)。
    """
    xs, ys, zs = np.arange(10.0), np.arange(6.0), np.arange(4.0)
    gx, gy, gz = np.meshgrid(xs, ys, zs, indexing="ij")
    return np.stack([gx.ravel(), gy.ravel(), gz.ravel()], axis=1)


def main():
    # ================================================================= #
    # 表現 1: 点群のシーンフロー -> 剛体復元(estimate_flow -> fit_rigid, + CPD)
    # ================================================================= #
    frame0 = box_lattice()                                  # 時刻 0 の物体点群 (240, 3)
    # 運動は格子間隔(1.0)より小さく設計 = 最近傍対応が恒等になる小運動の前提を満たす。
    R_gt = rodrigues([0.2, 1.0, 0.3], 2.0)                  # 真の回転 = 2 度
    t_gt = np.array([0.20, -0.15, 0.10])                   # 真の並進(すべて < 1 voxel)
    frame1 = frame0 @ R_gt.T + t_gt                        # 時刻 1 の物体点群 (240, 3)

    null_rot = rot_err_deg(np.eye(3), R_gt)                # 無運動 null の回転誤差 = 真回転角
    null_t = float(np.linalg.norm(t_gt))                   # 無運動 null の並進誤差 = |t_gt|

    # --- op1: 最近傍シーンフロー(各 frame0 点 -> frame1 最近傍への 3-D 変位) ---
    flow = estimate_flow(frame0, frame1)                   # (240, 3)
    true_disp = frame1 - frame0                            # 真の変位(GT)
    # 小運動なので i 番点の最近傍は自分自身の移動先 = 対応は恒等になるはず。
    _, nn_idx = cKDTree(frame1).query(frame0, k=1)
    nn_identity = float(np.mean(nn_idx == np.arange(len(frame0))))
    flow_err = float(np.max(np.linalg.norm(flow - true_disp, axis=1)))
    null_flow_epe = float(np.mean(np.linalg.norm(true_disp, axis=1)))  # ゼロフロー null

    # --- op2: フロー対応から閉形式 Kabsch で剛体 (R, t) を復元 ---
    target = frame0 + flow                                 # フローが指す対応先
    R_fit, t_fit = fit_rigid(frame0, target)
    fit_rerr = rot_err_deg(R_fit, R_gt)
    fit_terr = float(np.linalg.norm(t_fit - t_gt))

    # --- op3: CPD 剛体版で「生点群から」独立に (R, t) を復元(相互検証) ---
    R_cpd, t_cpd, cpd_info = register_cpd_rigid(frame0, frame1, iters=100, w=0.0)
    cpd_rerr = rot_err_deg(R_cpd, R_gt)
    cpd_terr = float(np.linalg.norm(t_cpd - t_gt))
    # 2 手法(Kabsch-on-NN-flow と 軟対応 CPD)の一致 = 相互チェック。
    cross_rerr = rot_err_deg(R_cpd, R_fit)
    cross_terr = float(np.linalg.norm(t_cpd - t_fit))

    print("[表現 1: 点群 -> 剛体復元]")
    print(f"  真の運動                 : 回転 2.000 度, 並進 |t|={null_t:.4f}")
    print(f"  estimate_flow NN 対応恒等率: {nn_identity:.3f}   (小運動なら 1.000)")
    print(f"  estimate_flow フロー誤差 : {flow_err:.3e}   (真変位との最大差)")
    print(f"  fit_rigid 回転/並進誤差  : {fit_rerr:.3e} 度 / {fit_terr:.3e}")
    print(f"  CPD       回転/並進誤差  : {cpd_rerr:.3e} 度 / {cpd_terr:.3e}  "
          f"(conv={cpd_info['converged']}, iters={cpd_info['iters']})")
    print(f"  相互検証 CPD vs fit_rigid: 回転差 {cross_rerr:.3e} 度 / 並進差 {cross_terr:.3e}")
    print(f"  null(無運動)             : 回転 {null_rot:.3f} 度 / 並進 {null_t:.4f}")

    # 検証 1: estimate_flow は小運動で対応恒等 -> フロー == 真の変位(丸め以内)、null を圧倒。
    assert nn_identity == 1.0, f"最近傍対応が恒等でない(小運動前提が崩れた): {nn_identity}"
    assert flow_err < 1e-9, f"最近傍フローが真の変位と一致しない: {flow_err:.3e}"
    assert flow_err < 1e-3 * null_flow_epe, "フローがゼロフロー null を圧倒していない"
    # 検証 1: fit_rigid は厳密対応の Kabsch -> 機械精度、無運動 null を桁で下回る。
    assert fit_rerr < 1e-3, f"fit_rigid 回転誤差が大きい: {fit_rerr:.3e} 度"
    assert fit_terr < 1e-6, f"fit_rigid 並進誤差が大きい: {fit_terr:.3e}"
    assert fit_rerr < 0.01 * null_rot, "fit_rigid が無運動 null を明確に下回らない"
    # 検証 1: CPD も同じ真値を独立復元し、fit_rigid と一致(2 手法の相互検証)。
    assert cpd_rerr < 1e-2, f"CPD 回転誤差が大きい: {cpd_rerr:.3e} 度"
    assert cpd_terr < 1e-5, f"CPD 並進誤差が大きい: {cpd_terr:.3e}"
    assert cpd_info["converged"], "CPD が収束しなかった"
    assert cross_rerr < 1e-2 and cross_terr < 1e-5, \
        f"2 手法が一致しない(相互検証失敗): 回転差 {cross_rerr:.3e}, 並進差 {cross_terr:.3e}"

    # ================================================================= #
    # 表現 2: ボクセル密度場の密なシーンフロー(scene_flow_lk)
    # ================================================================= #
    # 物体を滑らかな低周波テクスチャのボクセル密度場にする(輝度一定を仮定する LK が最も
    # 安定に働く帯域)。既知の並進 shift で動かして vol1 を作り、密フロー場を復元する。
    D = H = W = 40
    zz, yy, xx = np.mgrid[0:D, 0:H, 0:W].astype(float)
    vol0 = (np.sin(xx * 0.35) * np.cos(yy * 0.28)
            + 0.6 * np.sin(yy * 0.22 + zz * 0.19)
            + 0.4 * np.cos(zz * 0.25 + xx * 0.18)).astype(np.float32)
    shift = np.array([1.5, -2.0, 1.0])                     # 真の並進 (dz, dy, dx)
    # vol1(x) = vol0(x - shift) を map_coordinates で厳密に生成(規約: scene_flow_lk は
    # vol1(x) ≈ vol0(x - d) を仮定し d を返すので、復元フロー ≈ shift になるはず)。
    src = np.stack([zz - shift[0], yy - shift[1], xx - shift[2]], axis=0)
    vol1 = map_coordinates(vol0, src, order=1, mode="nearest").astype(np.float32)

    flow_lk = scene_flow_lk(vol0, vol1, device="cpu", win=3, levels=3, iters=3)
    assert flow_lk.shape == (3, D, H, W), f"LK フロー形状が不正: {flow_lk.shape}"
    core = (slice(12, 28),) * 3                            # 境界流入出を避けた中央領域
    sub = flow_lk[:, core[0], core[1], core[2]].reshape(3, -1)
    mean_flow = sub.mean(axis=1)
    mean_err = float(np.linalg.norm(mean_flow - shift))
    epe = np.linalg.norm(sub - shift[:, None], axis=0)     # per-voxel EPE
    epe_median = float(np.median(epe))
    null_lk_epe = float(np.linalg.norm(shift))             # ゼロフロー null の EPE
    # 決定性(同入力で 2 回呼んで完全一致)。
    flow_lk2 = scene_flow_lk(vol0, vol1, device="cpu", win=3, levels=3, iters=3)
    lk_determinism = float(np.max(np.abs(flow_lk - flow_lk2)))

    print("\n[表現 2: ボクセル密フロー scene_flow_lk]")
    print(f"  真の並進 shift (dz,dy,dx): {shift}")
    print(f"  復元 平均フロー(中央)   : {np.round(mean_flow, 4)}  (誤差 {mean_err:.4f} voxel)")
    print(f"  per-voxel EPE 中央値     : {epe_median:.4f}   (ゼロフロー null={null_lk_epe:.4f})")
    print(f"  決定性 max|call1-call2|  : {lk_determinism:.3e}")

    # 検証 2: 中央平均フロー ≈ 真の並進、per-voxel EPE も小、決定的、null を圧倒。
    assert mean_err < 0.15, f"LK 平均フロー誤差が大きい: {mean_err:.4f} voxel"
    assert epe_median < 0.4, f"LK per-voxel EPE 中央値が大きい: {epe_median:.4f}"
    assert epe_median < 0.25 * null_lk_epe, "LK EPE がゼロフロー null を明確に下回らない"
    assert lk_determinism == 0.0, f"scene_flow_lk が非決定的: {lk_determinism:.3e}"

    # ================================================================= #
    # 表現 3: 画像平面の運動(warp_by_plane)
    # ================================================================= #
    rng = np.random.default_rng(0)

    # --- (a) 整数並進 homography のワープが np.roll と機械精度一致 ---
    # 平面の面が画素平面内を (dx, dy) 平行移動する最も基本の場合。warp_by_plane は
    # out[y,x] = img(H·(x,y,1)) の逆写像なので、内容を (+dx,+dy) 動かすには H で source を
    # (x-dx, y-dy) に引く。整数シフト・bilinear は格子上で厳密 = np.roll と一致するはず。
    img = rng.uniform(0.0, 1.0, size=(60, 70))
    dx, dy = 5, -3
    H_shift = np.array([[1.0, 0.0, -dx], [0.0, 1.0, -dy], [0.0, 0.0, 1.0]])
    warped = warp_by_plane(img, H_shift, order=1, cval=0.0)
    rolled = np.roll(np.roll(img, dy, axis=0), dx, axis=1)   # 独立 GT(巻き込み境界を除く)
    interior = (slice(6, 54), slice(8, 64))                 # 巻き込み帯を避けた完全有効域
    roll_diff = float(np.max(np.abs(warped[interior] - rolled[interior])))
    null_warp_diff = float(np.max(np.abs(img[interior] - rolled[interior])))  # 無ワープ null

    # --- (b) 復元剛体が誘導する画像 homography のインパルス写像が解析値と一致 ---
    # 物体の平らな面(法線 [0,0,1]、深度 depth)が剛体 (R_fit, t_fit) で動くと画像には
    # H = K(R + t n^T/depth)K^{-1} が誘導される。インパルスを置いてワープし、その移動先が
    # 解析的な逆写像 H^{-1}·(x0,y0) と一致するかを確かめる(warp が homography を正しく実現)。
    focal, depth = 600.0, 5.0
    Kmat = np.array([[focal, 0.0, 60.0], [0.0, focal, 60.0], [0.0, 0.0, 1.0]])
    H_img = plane_homography(Kmat, R_fit, t_fit, depth, normal=(0.0, 0.0, 1.0))
    imp = np.zeros((120, 120))
    x0, y0 = 60, 60                                         # 中央のインパルス(landmark)
    imp[y0, x0] = 1.0
    warped_imp = warp_by_plane(imp, H_img, order=1, cval=0.0)
    Hinv = np.linalg.inv(H_img)
    exp = Hinv @ np.array([x0, y0, 1.0])
    exp_xy = exp[:2] / exp[2]                               # 解析的な出力インパルス位置 (x,y)
    ay, ax = np.unravel_index(int(np.argmax(warped_imp)), warped_imp.shape)
    argmax_err = float(max(abs(ax - exp_xy[0]), abs(ay - exp_xy[1])))
    disp_px = float(np.linalg.norm(exp_xy - np.array([x0, y0])))  # 無ワープ null=0 との対比
    finite_frac = float(np.mean(np.isfinite(warped_imp)))

    print("\n[表現 3: 画像平面ワープ warp_by_plane]")
    print(f"  (a) 整数並進 vs np.roll   : 最大差 {roll_diff:.3e}  (無ワープ null={null_warp_diff:.3f})")
    print(f"  (b) インパルス解析写像先  : ({exp_xy[0]:.2f}, {exp_xy[1]:.2f})  argmax=({ax}, {ay})")
    print(f"      argmax 誤差 / 移動量  : {argmax_err:.2f} px / {disp_px:.2f} px  (無ワープ null=0)")

    # 検証 3(a): 整数並進ワープは np.roll と機械精度一致、無ワープ null を圧倒。
    assert roll_diff < 1e-9, f"整数並進ワープが np.roll と一致しない: {roll_diff:.3e}"
    assert null_warp_diff > 0.1, "並進 null 対比が退化(画像に構造が無い)"
    # 検証 3(b): homography 逆写像の解析値と argmax が一致(1 px 以内)、無ワープ null を圧倒。
    assert finite_frac == 1.0, f"ワープ出力に非有限値: finite_frac={finite_frac}"
    assert argmax_err <= 1.0, f"インパルス写像先が解析値とずれる: {argmax_err:.2f} px"
    assert disp_px > 5.0, f"homography がインパルスをほぼ動かさない(null と区別不能): {disp_px:.2f} px"

    print(
        f"\nPASS: estimate_flow フロー誤差 {flow_err:.1e} (対応恒等), "
        f"fit_rigid 回転 {fit_rerr:.1e}度/並進 {fit_terr:.1e} == CPD {cpd_rerr:.1e}度/{cpd_terr:.1e} "
        f"(相互検証, << null {null_rot:.1f}度/{null_t:.2f}), "
        f"scene_flow_lk 平均誤差 {mean_err:.3f}/EPE中央 {epe_median:.3f} voxel (<< null {null_lk_epe:.2f}, 決定的), "
        f"warp_by_plane roll差 {roll_diff:.1e}・インパルス写像 {argmax_err:.1f}px/移動 {disp_px:.0f}px "
        f"(homography を正しく実現, beat-the-null)"
    )


if __name__ == "__main__":
    main()
