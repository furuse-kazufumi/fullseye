# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""itokawa_self_register — 未知姿勢で置かれた小惑星スキャンの位置合わせ(ICP)。

【この例が解く現実問題】
探査機が小惑星に接近するたびに、機体の姿勢は毎回違う。新しいスキャン点群を、既存の
形状モデル(基準点群)に **重ね合わせて位置姿勢を推定** できれば、相対航法・自転軸推定・
複数観測の統合ができる。ここでは基準モデルに未知回転 + センサーノイズを掛けた「スキャン」を
作り、ICP(反復最近傍点、Kabsch/SVD)で基準へ登録し直して、回転が数度以内で回復することを示す。

【重要な洞察 — 球と違い、実在の非対称小惑星は登録できる】
完全な球はどんな回転を掛けても自分自身に重なる(回転対称)。だから球のスキャンからは
「どれだけ回ったか」を原理的に復元できない。イトカワは 558×301×242 m の凸凹した非対称体で、
形状そのものが回転対称性を破っている。ゆえに最近傍対応が向きに敏感になり、ICP が一意な回転へ
収束する。本スクリプトは同じ ICP を球にも掛け、球では回転が復元できない(残差は小さいのに
回転誤差は大きい)ことを対比として assert し、"登録できる = 形状が非対称であること" を示す。

対象データ: studio_assets/sample_3d/itokawa_points.npy(実測イトカワ点群, ~3000 点)。
使う op: match3d.icp_point2point_3d、metrics3d.pose_error。
"""
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import match3d    # icp_point2point_3d(点群 → 剛体姿勢を SVD で精緻化)
import metrics3d  # pose_error(推定姿勢と GT の回転角・並進誤差)

DATA = _REPO / "studio_assets" / "sample_3d" / "itokawa_points.npy"


def register_and_error(scan, reference, R_true_inverse):
    """scan を reference へ ICP 登録し、GT 回転(R_true の逆)との誤差[度]を返す。

    icp_point2point_3d は reference ~= scan @ R.T + t を満たす R,t を返す。scan = ref @ R_gt.T
    なので、回復される R は R_gt の逆(= R_gt.T)に一致するはず。
    """
    R, t, info = match3d.icp_point2point_3d(scan, reference, iters=80)
    R = R.detach().cpu().numpy()
    t = t.detach().cpu().numpy()
    rot_deg, _ = metrics3d.pose_error(R, np.zeros(3), R_true_inverse, np.zeros(3))
    return rot_deg, float(info["rmse"])


def main():
    rng = np.random.default_rng(0)
    ref = np.load(DATA).astype(np.float64)
    ref = ref - ref.mean(axis=0)
    diag = float(np.linalg.norm(ref.max(axis=0) - ref.min(axis=0)))

    # 未知の姿勢とセンサーノイズ(外接対角の 0.4%)でスキャンを合成
    R_gt = Rotation.from_rotvec(np.array([0.2, 0.5, 0.84]) /
                                np.linalg.norm([0.2, 0.5, 0.84]) *
                                np.radians(30.0)).as_matrix()
    noise_sigma = 0.004 * diag
    scan = ref @ R_gt.T + rng.normal(0.0, noise_sigma, ref.shape)

    print("=== グラウンドトゥルース ===")
    print(f"外接対角        : {diag:.1f} m")
    print(f"与えた回転      : 30.0 度(軸まわり)")
    print(f"センサーノイズσ : {noise_sigma:.2f} m(対角の 0.4%)")

    # --- 小惑星(非対称)の登録 ---
    ast_rot_err, ast_rmse = register_and_error(scan, ref, R_gt.T)
    print("\n=== イトカワ(非対称)を ICP で登録 ===")
    print(f"最終 RMSE       : {ast_rmse:.2f} m(≈ ノイズ床 {noise_sigma:.2f} m)")
    print(f"回転誤差        : {ast_rot_err:.3f} 度")
    assert ast_rot_err < 2.0, f"小惑星の回転が回復できていない: {ast_rot_err:.3f} 度"

    # --- 対比: 完全な球(回転対称)は登録できない ---
    n = len(ref)
    u = rng.normal(size=(n, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    radius = 0.25 * diag
    sphere = u * radius
    sphere_scan = sphere @ R_gt.T + rng.normal(0.0, noise_sigma, sphere.shape)
    sph_rot_err, sph_rmse = register_and_error(sphere_scan, sphere, R_gt.T)
    print("\n=== 対比: 球(回転対称)を同じ ICP で登録 ===")
    print(f"最終 RMSE       : {sph_rmse:.2f} m(小さい = 表面には重なる)")
    print(f"回転誤差        : {sph_rot_err:.2f} 度(大きい = 回転を復元できない)")

    # 球は残差が小さくても回転を復元できない(回転対称)。小惑星は両方成功。
    assert sph_rot_err > 5.0 * ast_rot_err + 5.0, \
        f"球でも回転が復元できてしまった(対比が成立しない): 球={sph_rot_err:.2f}度"

    print("\nPASS: 実在の非対称小惑星は ICP で数度以内に登録できる"
          f"(回転誤差 {ast_rot_err:.3f} 度)。球は形状が回転対称なため同じ ICP でも"
          f"回転を復元できない(誤差 {sph_rot_err:.1f} 度)。"
          "登録可能性は形状の非対称性そのものに由来する。")


if __name__ == "__main__":
    main()
