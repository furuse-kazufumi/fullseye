# 事例: N 視点バンドル調整による精緻化
# ----------------------------------------------------------------------------
# 実問題: 同じ物体を複数のカメラ位置から撮った画像がある。各カメラの姿勢(向きと位置)と
#   3D 点の座標には、初期推定にありがちな「ずれ(摂動)」が乗っている。この状態から、
#   すべての観測(どのカメラがどの点をどの画素に写したか)をいちばんよく説明するように
#   カメラ姿勢と点を同時に微調整し、画素の再投影ずれ(RMSE)をほぼ 0 まで、姿勢を真値へ
#   戻せることを確かめる。SfM / Visual Odometry の仕上げ段(bundle adjustment)。
import numpy as np
import bundle3d as B


def rot_angle_deg(Ra, Rb):
    """2 つの回転のあいだの角度(度)。"""
    R = Ra.T @ Rb
    c = np.clip((np.trace(R) - 1) / 2, -1, 1)
    return float(np.rad2deg(np.arccos(c)))


# --- 合成シーンを作る: 4 カメラ + 40 個の 3D 点 ------------------------------
rng = np.random.default_rng(1)
K = np.array([[600.0, 0, 320], [0, 600.0, 240], [0, 0, 1.0]])  # 全カメラ共有の内部行列

n_cam, n_pt = 4, 40
# 3D 点はカメラの前方(z≈6)にばらまく
pts_true = rng.uniform(-1.5, 1.5, size=(n_pt, 3)) + np.array([0, 0, 6.0])

# カメラ姿勢 [rvec(3) | t(3)]。先頭カメラは基準 [I|0]。
cams_true = [np.zeros(6)]
for _ in range(1, n_cam):
    rvec = rng.uniform(-0.25, 0.25, 3)
    t = np.array([rng.uniform(-1, 1), rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5)])
    cams_true.append(np.concatenate([rvec, t]))
cams_true = np.array(cams_true)

# 真値から観測(画素座標)を生成: 各カメラが全 40 点を見る
obs_cam, obs_pt, obs_uv = [], [], []
for c in range(n_cam):
    proj = B.project(pts_true, cams_true[c, :3], cams_true[c, 3:], K)
    for j in range(n_pt):
        obs_cam.append(c)
        obs_pt.append(j)
        obs_uv.append(proj[j])
obs_cam = np.array(obs_cam)
obs_pt = np.array(obs_pt)
obs_uv = np.array(obs_uv)

# 真値では再投影誤差は厳密に 0(観測を真値で作ったので当然)
rmse_truth = B.mean_reprojection_error(cams_true, pts_true, obs_cam, obs_pt, obs_uv, K)
print(f"真値での再投影 RMSE: {rmse_truth:.2e} px (~0 のはず)")

# --- 摂動を加える: 初期推定が少しずれている状況を再現 -----------------------
pert = np.random.default_rng(9)
cams0 = cams_true.copy()
cams0[1:, :3] += pert.normal(0, 0.02, cams0[1:, :3].shape)  # 回転にずれ
cams0[1:, 3:] += pert.normal(0, 0.05, cams0[1:, 3:].shape)  # 並進にずれ
pts0 = pts_true + pert.normal(0, 0.05, pts_true.shape)      # 3D 点にもずれ

rmse_init = B.mean_reprojection_error(cams0, pts_true, obs_cam, obs_pt, obs_uv, K)
print(f"摂動後(BA 前)の再投影 RMSE: {rmse_init:.3f} px")

# --- バンドル調整で精緻化 ---------------------------------------------------
# 先頭カメラを固定して座標系の不定性(gauge)を除き、姿勢+点を同時最適化。
out = B.bundle_adjust(cams0, pts0, obs_cam, obs_pt, obs_uv, K, fix_first=True)
rmse_ba = out["rmse"]
print(f"BA 後の再投影 RMSE: {rmse_ba:.2e} px")

# 各カメラの回転が真値へどれだけ戻ったか
ang_errs = [rot_angle_deg(B.rvec_to_R(out["cameras"][c, :3]),
                          B.rvec_to_R(cams_true[c, :3])) for c in range(1, n_cam)]
print("各カメラの回転誤差 (度):", [f"{a:.4f}" for a in ang_errs])
print("最大回転誤差:", f"{max(ang_errs):.4f} deg")

# --- 検証: 再投影 RMSE が ~0 へ収束・回転誤差 < 0.5° ------------------------
assert rmse_truth < 1e-9, rmse_truth              # 真値では誤差ゼロ
assert rmse_ba < 1e-3, (rmse_ba, rmse_init)       # BA 後は ~0 に回復
assert rmse_ba < rmse_init                        # 摂動時より確実に改善
for c, ang in zip(range(1, n_cam), ang_errs):
    assert ang < 0.5, (c, ang)                    # 全カメラ回転 < 0.5°
# 先頭カメラは固定されたまま(gauge 基準)
assert np.allclose(out["cameras"][0], cams_true[0])

print("\nALL ASSERTIONS PASSED")