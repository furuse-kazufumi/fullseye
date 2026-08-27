# -*- coding: utf-8 -*-
"""事例: 点群登録(2 つの点群を重ね合わせる剛体変換)の品質を評価する。

実問題: ICP や特徴マッチングで「source を target に合わせる 4x4 変換」を推定したとき、
その推定が良いのか悪いのかを客観的な数値で判定したい。ここでは 3 つの標準指標を使う:
  - inlier_ratio : 推定変換で残差がしきい値内に収まる対応の割合(1 に近いほど良い)。
  - rmse_inliers : その inlier 上の位置合わせ誤差(RMSE)と inlier 数。
  - registration_recall : 3DMatch 流の成否(1.0=成功 / 0.0=失敗)。
良い推定と悪い推定を用意し、recall が 1.0 -> 0.0 に切り替わること、そして対応が
1 つも無いときに RMSE が「0 の捏造」でなく NaN で返ること(honest)を検証する。

依存は numpy/scipy と fullseye の registration_eval のみ(cv2/torch/skimage 不使用)。
"""
import numpy as np

import registration_eval as re   # 主モジュール


def rot_about(axis, deg):
    """軸 axis まわり deg 度の回転行列を Rodrigues 公式で自作(scipy にも依存しない)。"""
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    th = np.deg2rad(deg)
    K = np.array([[0, -a[2], a[1]],
                  [a[2], 0, -a[0]],
                  [-a[1], a[0], 0]], float)
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * (K @ K)


# ── 真の変換(GT)と source/target を用意 ────────────────────────────────
rng = np.random.default_rng(0)
S = rng.uniform(-1.0, 1.0, size=(200, 3))          # source 点群
R_gt = rot_about([0.3, -0.7, 0.5], 37.0)           # 真の回転
t_gt = np.array([1.2, -0.4, 2.0])                  # 真の並進
gt = re.make_transform(R_gt, t_gt)                 # 真の 4x4 変換
target = re.transform_points(gt, S)                # target[i] は source[i] の真の対応

thresh = 0.05                                      # 成功と見なす残差しきい値(データ単位)

# ── 良い推定 = GT / 悪い推定 = GT を大きく並進ずらししたもの ──────────────
est_good = gt.copy()                               # 完璧に推定できた場合
est_bad = gt.copy()
est_bad[:3, 3] += np.array([2.0, 0.0, 0.0])        # 並進を 2.0 ずらした失敗推定(残差 2.0)

# inlier_ratio: 良い推定はほぼ全対応が inlier、悪い推定は残差 2.0 で全滅
ir_good = re.inlier_ratio(S, target, est_good, thresh)
ir_bad = re.inlier_ratio(S, target, est_bad, thresh)

# rmse_inliers: 良い推定は inlier 多数で RMSE~0、悪い推定は inlier 0 で (nan, 0)
rmse_good, n_good = re.rmse_inliers(S, target, est_good, thresh)
rmse_bad, n_bad = re.rmse_inliers(S, target, est_bad, thresh)

# registration_recall: GT で対応(重なり)を張り、推定変換での RMSE が thresh を切るか
recall_good = re.registration_recall(S, target, gt, est_good, thresh=thresh)
recall_bad = re.registration_recall(S, target, gt, est_bad, thresh=thresh)

# 参考: 推定と GT の回転誤差[度]・並進誤差
rre_good, rte_good = re.rotation_translation_error(gt, est_good)
rre_bad, rte_bad = re.rotation_translation_error(gt, est_bad)

# ── 数値 GT の出力 ──────────────────────────────────────────────────────
print("thresh                    =", thresh)
print("[good est = GT]  inlier_ratio =", round(ir_good, 4),
      " rmse =", None if np.isnan(rmse_good) else round(rmse_good, 8),
      " n_inliers =", n_good,
      " recall =", recall_good,
      " (RRE=%.4f deg, RTE=%.4f)" % (rre_good, rte_good))
print("[bad  est]       inlier_ratio =", round(ir_bad, 4),
      " rmse =", rmse_bad, "(NaN)" if np.isnan(rmse_bad) else "",
      " n_inliers =", n_bad,
      " recall =", recall_bad,
      " (RRE=%.4f deg, RTE=%.4f)" % (rre_bad, rte_bad))

# GT-1: 良い推定は inlier 率 1.0 / RMSE ほぼ 0 / recall 1.0
assert ir_good == 1.0, f"good est inlier_ratio should be 1.0, got {ir_good}"
assert n_good == len(S) and rmse_good < 1e-9, f"good est rmse should be ~0 over all pts, got {rmse_good}"
assert recall_good == 1.0, f"good est recall should be 1.0, got {recall_good}"

# GT-2: 悪い推定は inlier 率 0.0 / recall 0.0(recall が 1.0->0.0 に切り替わる)
assert ir_bad == 0.0, f"bad est inlier_ratio should be 0.0, got {ir_bad}"
assert recall_bad == 0.0, f"bad est recall should be 0.0, got {recall_bad}"

# GT-3: inlier が 0 個のとき RMSE は 0 の捏造でなく NaN(honest)、n=0
assert n_bad == 0, f"bad est should have zero inliers, got {n_bad}"
assert np.isnan(rmse_bad), f"zero-inlier rmse must be NaN (not fabricated 0), got {rmse_bad}"

# GT-4: 回転・並進誤差も一致(良い推定は 0、悪い推定は並進誤差 2.0)
assert rre_good < 1e-6 and rte_good < 1e-9, "good est should have zero pose error"
assert abs(rte_bad - 2.0) < 1e-9, f"bad est translation error should be 2.0, got {rte_bad}"

print("OK: recall は 1.0->0.0 に切り替わり、対応ゼロの RMSE は捏造でなく NaN")