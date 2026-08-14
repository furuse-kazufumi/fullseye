import numpy as np
import odometry as od

# Ground-truth metric trajectory (camera centers), e.g. a robot walking a curve.
t = np.linspace(0, 1, 12)
gt = np.stack([t, 0.5 * np.sin(3 * t), 0.2 * t], axis=1)  # (N,3)

# Estimate that is IDENTICAL in shape but 2x scale (100% scale drift).
est = 2.0 * gt

res = od.trajectory_error(est, gt, align=True)
print("2x-scale estimate:")
print("  ATE rmse :", res["rmse"])
print("  ATE mean :", res["mean"])
print("  ATE max  :", res["max"])

# For contrast: true metric error without alignment is large.
raw = np.linalg.norm(est - gt, axis=1)
print("  raw (no-align) rmse:", float(np.sqrt(np.mean(raw**2))))

# Confirm there is NO parameter to request rigid (scale-free) alignment.
import inspect
sig = inspect.signature(od.trajectory_error)
print("trajectory_error params:", list(sig.parameters))
sig2 = inspect.signature(od.umeyama_align)
print("umeyama_align default with_scale:", sig2.parameters["with_scale"].default)

# Show that rigid alignment WOULD expose the scale error.
s, R, tt = od.umeyama_align(est, gt, with_scale=False)
E = (s * (est @ R.T)) + tt
rigid_rmse = float(np.sqrt(np.mean(np.linalg.norm(E - gt, axis=1) ** 2)))
print("  rigid-align rmse (what should be reported):", rigid_rmse, " (s=%.4f)" % s)
