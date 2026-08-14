import numpy as np
import odometry as od

# Instrument: replicate the RANSAC loop to confirm best_cnt < 3 (fallback hit).
rng_data = np.random.default_rng(1)
n = 30
A = rng_data.normal(size=(n, 3))
B = rng_data.normal(size=(n, 3))
thresh = 1e-3

# mirror _ransac_kabsch's loop
rng = np.random.default_rng(0)
best_cnt = -1
for _ in range(200):
    i = rng.choice(n, 3, replace=False)
    R, t = od._kabsch(A[i], B[i])
    err = np.linalg.norm((A @ R.T + t) - B, axis=1)
    cnt = int((err <= thresh).sum())
    if cnt > best_cnt:
        best_cnt = cnt
print("best_cnt across 200 samples:", best_cnt, "-> fallback (best_cnt<3) taken?", best_cnt < 3)

# Now drive the PUBLIC rgbd_odometry with a synthetic RGB-D pair whose flow
# correspondences are geometrically inconsistent, forcing a garbage fit.
H, W = 40, 40
K = np.array([[50.0, 0, 20.0], [0, 50.0, 20.0], [0, 0, 1.0]])
rng2 = np.random.default_rng(7)
depth0 = rng2.uniform(0.5, 3.0, size=(H, W))
depth1 = rng2.uniform(0.5, 3.0, size=(H, W))   # unrelated depth
# random flow that scrambles correspondences
u = rng2.uniform(-3, 3, size=(H, W))
v = rng2.uniform(-3, 3, size=(H, W))
Rr, tr, inl_frac = od.rgbd_odometry(depth0, depth1, u, v, K, thresh=1e-4,
                                    iters=200, stride=2, seed=0)
print("public rgbd_odometry inlier_fraction:", inl_frac)
