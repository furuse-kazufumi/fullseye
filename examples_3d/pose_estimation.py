"""事例: 既知の箱を見て、カメラの姿勢(向き・位置)を当てる (pose estimation / PnP).

工場のカメラや AR、ロボットの hand-eye で日常的に起きる問題:
形が分かっている物体(ここでは寸法既知の箱)を撮ると、画像上に角や特徴点が写る。
「その箱に対してカメラはどこから、どの向きで見ているのか?」を、
3D 点(箱の頂点座標)とその 2D 投影(画像上のピクセル)の対応だけから復元したい。

現実の対応点には二種類の汚れが乗る:
  (1) 検出のブレ = 数ピクセルのガウス雑音(ここでは 0.5px)
  (2) 誤対応 = 全く別の場所を指す外れ値(ここでは 30%)
外れ値が混ざると、全点をまとめて解く素の DLT は最小二乗が引っ張られて破綻する。
そこで pnp_ransac が「多数派の対応だけで合意」を取り、外れ値を捨てて姿勢を復元する。

方法:
  - 真のカメラ姿勢 (R_gt, t_gt) と内部行列 K で箱の 3D 点を 2D に投影(順方向)。
  - 0.5px の雑音を足し、30% の点を外れ値に差し替える。
  - pnp_ransac で姿勢を逆問題として復元し、dlt_pose(全点・素)と比べる。
  - reprojection_error で inlier の当てはまりを、coplanarity_ratio で入力の非平面度を測る。

検証(GT・beat-the-null):
  真の姿勢を自分で決めて投影しているので、復元姿勢との誤差が厳密に測れる。
  合格条件 = 回転誤差 < 2度 かつ 並進相対誤差 < 2% かつ inlier 再投影 RMS < 1.5px。
  null(恒等姿勢 = 向きを当てずに置いただけ)の再投影誤差は > 50px、
  外れ値込みの素の dlt_pose は姿勢が大きく崩れる — RANSAC がこれらを明確に上回る。
"""
import sys
from pathlib import Path

import numpy as np

# examples_3d/ の 1 つ上(リポジトリ直下)に pnp3d.py がある。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pnp3d  # noqa: E402


def rotation_matrix(axis, deg):
    """軸まわり deg 度の回転行列 (ロドリゲスの公式)。"""
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


def known_box(dims=(1.5, 1.0, 0.8)):
    """寸法既知の非対称な箱: 8 頂点 + 12 稜線中点 + 6 面中心 = 26 点(非共平面)。

    3 辺すべて異なる非対称な箱にすることで姿勢が一意に定まる(立方体や球は
    対称性で姿勢が縮退しうる)。稜線中点・面中心を足して点数を増やし、
    RANSAC が外れ値を捨てても十分な inlier が残るようにする。原点中心。
    """
    d = np.asarray(dims, float)
    hx, hy, hz = d / 2.0
    signs = [-1.0, 1.0]
    corners = np.array([[sx * hx, sy * hy, sz * hz]
                        for sx in signs for sy in signs for sz in signs])
    # 稜線中点: 2 座標が角、1 座標が 0
    edges = []
    for a in range(3):
        for i in signs:
            for j in signs:
                p = [0.0, 0.0, 0.0]
                p[a] = 0.0
                p[(a + 1) % 3] = i * (d[(a + 1) % 3] / 2.0)
                p[(a + 2) % 3] = j * (d[(a + 2) % 3] / 2.0)
                edges.append(p)
    faces = []
    for a in range(3):
        for s in signs:
            p = [0.0, 0.0, 0.0]
            p[a] = s * (d[a] / 2.0)
            faces.append(p)
    return np.vstack([corners, np.array(edges), np.array(faces)])


def main():
    rng = np.random.default_rng(7)

    # --- 1) 既知の 3D 点と真のカメラ姿勢・内部行列 ---
    pts_3d = known_box(dims=(2.0, 1.4, 1.0))          # 寸法既知の箱(世界座標)
    n = len(pts_3d)
    K = np.array([[800.0, 0.0, 320.0],
                  [0.0, 800.0, 240.0],
                  [0.0, 0.0, 1.0]])                    # 640x480, f=800px
    R_gt = rotation_matrix([0.3, 1.0, 0.2], 55.0)      # 真のカメラの向き(55度回転)
    t_gt = np.array([0.4, -0.3, 6.0])                  # 真のカメラ位置(箱は前方 z~6)

    # coplanarity_ratio: DLT は非共平面点を要する。箱は明確に立体なので比が大きい。
    cop = pnp3d.coplanarity_ratio(pts_3d)

    # --- 2) 順投影 → 雑音 → 外れ値差し替え(=現実の汚れた対応点) ---
    pts_2d_clean = project_points(pts_3d, K, R_gt, t_gt)
    pts_2d = pts_2d_clean + rng.normal(0.0, 0.5, pts_2d_clean.shape)   # 0.5px 検出ブレ

    n_outliers = int(round(0.30 * n))                  # 30% を誤対応に
    outlier_idx = rng.choice(n, n_outliers, replace=False)
    # 外れ値 = 画像内のランダムな別位置(元の投影とは無関係)
    pts_2d[outlier_idx] = rng.uniform([0, 0], [640, 480], size=(n_outliers, 2))
    is_outlier = np.zeros(n, bool)
    is_outlier[outlier_idx] = True

    # --- 3) RANSAC で頑健に姿勢復元(op を連鎖: 出力を後段の入力へ) ---
    R_est, t_est, inlier_mask, info = pnp3d.pnp_ransac(
        pts_3d, pts_2d, K, thresh=2.0, iters=500, seed=0)

    # 素の dlt_pose(全点・外れ値込み)= null-ish な素朴解: 破綻を見る
    R_naive, t_naive = pnp3d.dlt_pose(pts_3d, pts_2d, K)

    # --- 4) GT 検証量 ---
    rerr = rotation_error_deg(R_est, R_gt)
    terr = translation_rel_error(t_est, t_gt)
    # reprojection_error を inlier 部分集合で(復元姿勢の当てはまり)
    inlier_rms = pnp3d.reprojection_error(
        pts_3d[inlier_mask], pts_2d[inlier_mask], K, R_est, t_est)

    # beat-the-null 1: 恒等姿勢(向きを当てず箱の位置にだけ置く)
    null_reproj = pnp3d.reprojection_error(pts_3d, pts_2d_clean, K, np.eye(3), t_gt)
    # beat-the-null 2: 外れ値込みの素の dlt_pose は回転が大きく崩れる
    rerr_naive = rotation_error_deg(R_naive, R_gt)

    print(f"点数 / 外れ値              : {n} 点 / {n_outliers} 点 (30%)")
    print(f"非平面度 coplanarity_ratio : {cop:.4f}  (>0 = 非共平面、DLT が有効)")
    print(f"RANSAC inlier             : {info['n_inliers']}/{n}"
          f"  (ratio {info['inlier_ratio']:.2f})")
    print(f"回転誤差 (度)             : {rerr:.3f}   (合格 < 2)")
    print(f"並進相対誤差              : {terr * 100:.3f}% (合格 < 2%)")
    print(f"inlier 再投影 RMS (px)    : {inlier_rms:.3f}   (合格 < 1.5)")
    print("--- beat-the-null ---")
    print(f"恒等姿勢の再投影誤差 (px) : {null_reproj:.1f}   (null は > 50 で破綻)")
    print(f"素 dlt_pose(外れ値込)回転 : {rerr_naive:.2f}度  (外れ値で破綻)")

    # --- 5) GT アサーション ---
    assert rerr < 2.0, f"回転誤差が大きすぎる: {rerr:.3f} 度"
    assert terr < 0.02, f"並進相対誤差が大きすぎる: {terr * 100:.3f}%"
    assert inlier_rms < 1.5, f"inlier 再投影 RMS が大きすぎる: {inlier_rms:.3f} px"
    # beat-the-null: 素朴解より判別的に良いこと
    assert null_reproj > 50.0, f"null が破綻していない: {null_reproj:.1f} px"
    assert rerr_naive > 5.0, \
        f"外れ値込みの素 dlt_pose が破綻していない(比較が無意味): {rerr_naive:.2f} 度"
    assert rerr_naive > 3.0 * rerr, \
        f"RANSAC が素朴解を明確に上回っていない: {rerr:.3f} vs {rerr_naive:.3f} 度"

    print(f"PASS: pnp_ransac が 30% 外れ値・0.5px 雑音下で姿勢を復元 — "
          f"回転誤差 {rerr:.2f}度 < 2、並進 {terr * 100:.2f}% < 2%、"
          f"inlier RMS {inlier_rms:.2f}px < 1.5。"
          f"null(恒等姿勢 {null_reproj:.0f}px)と素 dlt_pose({rerr_naive:.1f}度)を明確に上回る。")


if __name__ == "__main__":
    main()
