import numpy as np
import odometry as od

# Two clouds with NO consistent rigid transform between them, tight thresh.
rng = np.random.default_rng(1)
n = 30
A = rng.normal(size=(n, 3))
B = rng.normal(size=(n, 3))  # totally unrelated -> no rigid transform fits

thresh = 1e-3  # very tight
R, t, inl = od._ransac_kabsch(A, B, thresh=thresh, iters=200, seed=0)

# Actual residuals under the returned (R, t)
resid = np.linalg.norm(A @ R.T + t - B, axis=1)
actual_inlier_frac = float((resid <= thresh).mean())

print("returned inlier mask fraction :", float(inl.mean()))
print("actual fraction within thresh :", actual_inlier_frac)
print("median residual (m)           :", float(np.median(resid)))
print("min residual (m)              :", float(resid.min()))

# Also drive it through the public rgbd_odometry to confirm 3rd output.
# Build a synthetic RGB-D pair where flow correspondences map to inconsistent depths.
