"""Raw plenoptic frame -> decoded light field -> refocus and depth."""
import numpy as np
import lightfield as LF
import plenoptic as P

truth, _ = LF.lf_synthesize((0.5,), (5, 5), (32, 40), seed=17, occlusion=False)
raw = LF.lf_to_mla(truth)
calibration = {"origin_px": np.array([2., 2.]),
               "basis_px": np.array([[5., 0.], [0., 5.]]),
               "white_image": np.ones_like(raw)}
decoded = P.plenoptic_decode(raw, calibration, angular=(5, 5))
refocused = LF.lf_refocus(decoded, 0.5)
slopes, confidence = LF.lf_depth_from_focus(decoded, np.linspace(-1, 1, 17), window=5)
assert decoded.shape == (5, 5, 32, 40)
assert refocused.shape == slopes.shape == confidence.shape == (32, 40)
print("PASS: plenoptic_decode -> lf_refocus / lf_depth_from_focus")
