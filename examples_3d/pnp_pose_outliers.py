"""事例: 特徴マッチに誤対応が 4 割混じっても物体に対するカメラ姿勢を当てる (pose_estimation).

ロボットの hand-eye や AR では、既知形状の物体(3D モデル上のキーポイント 200 点)と、
カメラ画像から検出した 2D 特徴点を対応づけて「カメラがどこから見ているか」を復元する。
だが特徴マッチャは万能ではなく、実運用では対応の 3〜5 割が**誤対応(gross outlier)**=
まったく別の場所を指すことがある。全点をまとめて最小二乗で解く素の DLT は、この外れ値に
引っ張られて姿勢が崩壊する。pnp_ransac は 6 点の最小サンプルで仮姿勢を立て、再投影誤差で
「多数派の対応(inlier)」だけの合意を取り、外れ値を捨てて姿勢を復元する。

方法:
  - 200 個の非共平面な 3D モデル点を用意し、既知姿勢 (R_gt=軸角 50度, t_gt) と内部行列 K で
    2D に順投影(pnp3d と同一規約 x = K(RX+t))。0.5px の検出ブレを付与。
  - 40% の 2D 点を画像内のランダムな別位置に差し替える(=誤対応)。
  - pnp_ransac で頑健に姿勢を逆算し、同じ汚染データに素の dlt_pose を掛けた結果と比べる。

検証(GT・beat-the-null):
  真の姿勢を自分で決めて投影しているので、復元姿勢との測地回転誤差が厳密に測れる。
  合格 = 回転誤差 < 2度 かつ inlier 再投影 RMS < 1.5px(=真の inlier に正しく当てはまる)。
  null = **同じ汚染データへの素の dlt_pose**。40% 外れ値で回転が二桁度に破綻するので、
  「pnp_ransac の回転誤差 << dlt_pose の回転誤差(5 倍以上の開き)」で判別的に上回る。
"""
import sys
from pathlib import Path

import numpy as np

# examples_3d/ の 1 つ上(リポジトリ直下)に pnp3d.py がある。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pnp3d  # noqa: E402


def rotation_matrix(axis, deg):
    """軸角(axis-angle)表現からの回転行列(ロドリゲスの公式)。"""
    a = np.asarray(axis, float)
    a /= np.linalg.norm(a)
    th = np.radians(deg)
    k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(th) * k + (1 - np.cos(th)) * k @ k


def rotation_error_deg(R_est, R_gt):
    """2 つの回転行列の間の測地距離(度)。相対回転の回転角 = 誤差。"""
    cos = (np.trace(np.asarray(R_est).T @ R_gt) - 1) / 2
    return float(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))))


def translation_rel_error(t_est, t_gt):
    """並進の相対誤差 = ||t_est - t_gt|| / ||t_gt||(スケール不変)。"""
    t_gt = np.asarray(t_gt, float)
    return float(np.linalg.norm(np.asarray(t_est) - t_gt) / np.linalg.norm(t_gt))


def project_points(points_3d, K, R, t):
    """順方向の透視投影: x = K(RX+t)、u=x0/x2, v=x1/x2(pnp3d と同一規約)。→ (n,2)。"""
    Xc = (R @ np.asarray(points_3d, float).T).T + np.asarray(t, float)
    x = (np.asarray(K, float) @ Xc.T).T
    return x[:, :2] / x[:, 2:3]


def main():
    rng = np.random.default_rng(20260828)

    # --- 1) 既知の 3D モデル点(200 点)と真のカメラ姿勢・内部行列 ---
    # ランダムな立体的散布 = 非共平面(DLT が有効)。物体モデル上のキーポイントを模す。
    n = 200
    pts_3d = rng.uniform(-1.2, 1.2, size=(n, 3))       # 世界座標の 3D モデル点
    K = np.array([[800.0, 0.0, 320.0],
                  [0.0, 800.0, 240.0],
                  [0.0, 0.0, 1.0]])                    # 640x480, f=800px
    R_gt = rotation_matrix([0.2, 1.0, 0.35], 50.0)     # 真のカメラの向き(軸角 50度)
    t_gt = np.array([0.3, -0.25, 6.0])                 # 真のカメラ位置(物体は前方 z~6)

    # DLT は非共平面点を要する。ランダム立体散布なので比は大きい(> 0)。
    cop = pnp3d.coplanarity_ratio(pts_3d)
    depth = (pts_3d @ R_gt.T + t_gt)[:, 2]             # 全点カメラ前方(depth>0)を確認
    assert depth.min() > 0.1, f"カメラ後方の点がある: min depth {depth.min():.3f}"

    # --- 2) 順投影 → 検出ブレ → 40% を誤対応に差し替え(=汚れた対応点) ---
    pts_2d_clean = project_points(pts_3d, K, R_gt, t_gt)
    pts_2d = pts_2d_clean + rng.normal(0.0, 0.5, pts_2d_clean.shape)   # 0.5px 検出ブレ

    outlier_frac = 0.40
    n_outliers = int(round(outlier_frac * n))          # 40% を誤対応(gross outlier)に
    outlier_idx = rng.choice(n, n_outliers, replace=False)
    pts_2d[outlier_idx] = rng.uniform([0, 0], [640, 480], size=(n_outliers, 2))
    is_outlier = np.zeros(n, bool)
    is_outlier[outlier_idx] = True

    # --- 3) RANSAC で頑健に姿勢復元(op を連鎖: 出力を後段の入力へ) ---
    # thresh=3px: 0.5px 雑音の真 inlier は真姿勢で ~0.5px 再投影なので余裕で入り、
    # 数十〜数百px ずれる外れ値は確実に外れる。inlier 率 0.6 の 6 点全 inlier 標本は
    # 約 4.7% なので反復を 3000 と厚く取り、良い合意集合を確実に引く。
    R_est, t_est, inlier_mask, info = pnp3d.pnp_ransac(
        pts_3d, pts_2d, K, thresh=3.0, iters=3000, seed=0)

    # null: 同じ汚染データへの素の dlt_pose(全点・外れ値込み)= 素朴解の破綻を見る
    R_naive, t_naive = pnp3d.dlt_pose(pts_3d, pts_2d, K)

    # --- 4) GT 検証量 ---
    rerr = rotation_error_deg(R_est, R_gt)
    terr = translation_rel_error(t_est, t_gt)
    # reprojection_error を「真の inlier 部分集合」で(復元姿勢の当てはまり)
    true_inlier = ~is_outlier
    inlier_rms = pnp3d.reprojection_error(
        pts_3d[true_inlier], pts_2d[true_inlier], K, R_est, t_est)

    # beat-the-null: 同じ汚染データへの素 dlt_pose の回転誤差(外れ値で破綻)
    rerr_naive = rotation_error_deg(R_naive, R_gt)
    naive_inlier_rms = pnp3d.reprojection_error(
        pts_3d[true_inlier], pts_2d[true_inlier], K, R_naive, t_naive)

    # RANSAC が拾った inlier のうち、真の inlier だった割合(誤対応の除去性能)
    recovered = int(inlier_mask.sum())
    correct = int((inlier_mask & true_inlier).sum())
    precision = correct / max(recovered, 1)

    print(f"点数 / 誤対応              : {n} 点 / {n_outliers} 点 ({outlier_frac*100:.0f}%)")
    print(f"非平面度 coplanarity_ratio : {cop:.4f}  (>0 = 非共平面、DLT が有効)")
    print(f"RANSAC inlier             : {recovered}/{n}"
          f"  (真 inlier 適合率 {precision*100:.1f}%)")
    print(f"回転誤差 (度)             : {rerr:.3f}   (合格 < 2)")
    print(f"並進相対誤差              : {terr * 100:.3f}% ")
    print(f"inlier 再投影 RMS (px)    : {inlier_rms:.3f}   (合格 < 1.5)")
    print("--- beat-the-null (同じ汚染データへの素 dlt_pose) ---")
    print(f"素 dlt_pose 回転誤差 (度) : {rerr_naive:.2f}度  (40% 外れ値で破綻)")
    print(f"素 dlt_pose inlier RMS    : {naive_inlier_rms:.1f}px  (真 inlier にも合わない)")

    # --- 5) GT アサーション ---
    assert rerr < 2.0, f"回転誤差が大きすぎる: {rerr:.3f} 度"
    assert inlier_rms < 1.5, f"inlier 再投影 RMS が大きすぎる: {inlier_rms:.3f} px"
    assert precision > 0.95, f"外れ値を inlier に取り込んでいる: 適合率 {precision*100:.1f}%"
    # beat-the-null: 同じ汚染データへの素朴解は破綻し、RANSAC が判別的に上回る
    assert rerr_naive > 5.0, \
        f"素 dlt_pose が破綻していない(比較が無意味): {rerr_naive:.2f} 度"
    assert rerr_naive > 5.0 * rerr, \
        f"pnp_ransac が素 dlt_pose を明確に上回っていない: {rerr:.3f} << {rerr_naive:.3f} 度 のはず"

    print(f"PASS: pnp_ransac が 40% 誤対応・0.5px 雑音下で姿勢を復元 — "
          f"回転誤差 {rerr:.2f}度 < 2、inlier RMS {inlier_rms:.2f}px < 1.5。"
          f"同じ汚染データの素 dlt_pose は {rerr_naive:.1f}度 に破綻 "
          f"({rerr_naive / max(rerr, 1e-9):.0f}倍)、RANSAC が判別的に上回る。")


if __name__ == "__main__":
    main()
