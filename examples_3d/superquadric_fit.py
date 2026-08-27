# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: ロボットが未知の「角丸ブロック」を1個の握れる体積として当てはめる。

やりたいこと(平たく言うと):
    ビンの中に転がった角丸の直方体ブロックを、深度センサで点群として観測した。
    ロボットの把持計画は「その物体はどこに・どんな向きで・どれくらいの大きさで
    あるか」を1個の解析的な体積プリミティブで欲しい。スーパー2次曲面を1個
    当てはめれば、姿勢(R,t)・半径(a)・角の丸み(eps)がまとめて手に入り、
    内外関数 F で任意の点が物体の中か外かを判定できる(把持点や衝突判定に使う)。

方法:
    1. 既知の角丸ブロック(半径 a=(2,1,1)、丸み eps=(0.5,0.5))を既知姿勢に置く。
    2. sample_surface でその表面から点を採り、センサノイズを重畳(=観測点群)。
    3. fit_superquadric で観測点群だけから (a, eps, R, t) を復元。
    4. inside_outside で「観測に使っていない別の点」を内外分類し、真の体積と照合。

検証(GT / ground truth):
    * 復元した半径が真値の 5% 以内(軸の入れ替わりに強いよう sort して比較)。
    * フィット残差が注入ノイズの水準(Gross-Boult 残差 ~ 表面距離^2)。
    * 保留点の内外分類が真の体積と 95% 超で一致(姿勢まで含めた総合判定)。

零点(null)より良いこと:
    同じ点群に「球を1個」当てる素朴なモデルは、角丸ブロックの平たい面を球で
    近似できないため残差が数倍に膨らむ。スーパー2次曲面がそれを明確に下回る
    ことを assert する(単に「何か当たった」ではなく形を捉えたことの証拠)。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# 自己完結で走らせるためリポジトリルート(superquadric.py の場所)を import パスへ。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from superquadric import (  # noqa: E402
    fit_superquadric,
    inside_outside,
    sample_surface,
    superquadric_residual,
)


def rotation_matrix(axis, deg: float) -> np.ndarray:
    """軸まわり deg 度の回転行列(ロドリゲスの公式)。"""
    a = np.asarray(axis, dtype=np.float64)
    a = a / np.linalg.norm(a)
    th = np.radians(deg)
    K = np.array([[0.0, -a[2], a[1]], [a[2], 0.0, -a[0]], [-a[1], a[0], 0.0]])
    return np.eye(3) + np.sin(th) * K + (1.0 - np.cos(th)) * K @ K


def sphere_null_residual(points, t_center) -> tuple[float, float]:
    """零点モデル: 同じ点群に「最良の球1個」を当てたときの残差。

    球はスーパー2次曲面の特別な場合(a=(r,r,r), eps=(1,1))。半径は点群を
    内外にバランスさせる二乗平均距離(F の平均を 1 にする r)を採る素朴かつ
    公平な当て方。角丸ブロックの平たい面は球で近似できないので残差が残る。
    """
    P = np.asarray(points, dtype=np.float64).reshape(-1, 3)
    d = np.linalg.norm(P - np.asarray(t_center, dtype=np.float64).reshape(3), axis=1)
    r = float(np.sqrt(np.mean(d ** 2)))  # rms 距離 = mean(F)=1 にする球半径
    res = superquadric_residual(P, (r, r, r), (1.0, 1.0), np.eye(3), t_center)
    return res, r


def main() -> int:
    rng = np.random.default_rng(0)

    # --- 1) 既知の角丸ブロック(真値)を既知姿勢に置く ------------------------
    a_gt = np.array([2.0, 1.0, 1.0])       # 半径(真値): 長辺2, 短辺1x2 の平たいブロック
    eps_gt = np.array([0.5, 0.5])          # 丸み(真値): eps<1 = 角丸の箱
    R_gt = rotation_matrix([0.3, 1.0, 0.2], 40.0)  # 未知の置かれ向き(真値)
    t_gt = np.array([1.5, -0.8, 0.6])      # 未知の置かれ位置(真値)

    # --- 2) 表面から点を採り、センサノイズを重畳(=観測点群) ---------------
    surf = sample_surface(a_gt, eps_gt, n_u=48, n_v=48, R=R_gt, t=t_gt)
    diag = float(np.linalg.norm(surf.max(0) - surf.min(0)))   # 物体の対角長
    noise = 0.01 * diag                                       # ノイズ = スケールの1%
    scan = surf + rng.normal(0.0, noise, surf.shape)          # 観測点群

    # --- 3) 観測点群だけから (a, eps, R, t) を復元 -------------------------
    fit = fit_superquadric(scan)
    a_est, eps_est = fit["a"], fit["eps"]
    t_est, res_fit = fit["t"], fit["residual"]

    # --- 4) 内外分類の検証: 保留点を真の体積 vs 復元体積で照合 --------------
    # 真値中心のまわりに query 点をばらまき、真の F と 復元 F で内外ラベルを比較。
    span = 1.6 * a_gt.max()
    q_local = rng.uniform(-span, span, size=(4000, 3))
    query = q_local @ R_gt.T + t_gt                          # 真値姿勢の近傍に配置
    inside_gt = inside_outside(query, a_gt, eps_gt, R_gt, t_gt) < 1.0
    inside_est = inside_outside(query, a_est, eps_est, fit["R"], t_est) < 1.0
    agree = float(np.mean(inside_gt == inside_est))

    # --- GT 照合(表現の入れ替わり対称性に強い量で比較) --------------------
    # a=(2,1,1) は2軸が等しく、軸の並べ替え/長軸まわり回転の不定性がある。
    # 半径は sort して比較し、姿勢込みの正しさは内外一致で判定する。
    a_gt_sorted = np.sort(a_gt)[::-1]
    a_est_sorted = np.sort(a_est)[::-1]
    a_rel_err = float(np.max(np.abs(a_est_sorted - a_gt_sorted) / a_gt_sorted))
    rms_fit = float(np.sqrt(res_fit))       # 残差 ~ 表面距離^2 なので sqrt で距離次元へ

    # --- 零点(球1個)より明確に良いか --------------------------------------
    res_sphere, r_sphere = sphere_null_residual(scan, t_est)
    beat_ratio = res_sphere / max(res_fit, 1e-30)

    print(f"物体スケール(対角長)       : {diag:.3f}")
    print(f"注入ノイズ(標準偏差)       : {noise:.4f}  (スケールの1%)")
    print(f"真の半径   a_gt (sort)      : {a_gt_sorted}")
    print(f"復元半径   a_est(sort)      : {a_est_sorted}")
    print(f"半径の相対誤差(最大)       : {a_rel_err * 100:.2f}%")
    print(f"復元した丸み eps_est        : {np.round(eps_est, 3)}  (真値 {eps_gt})")
    print(f"フィット残差 sqrt(res)      : {rms_fit:.4f}  (注入ノイズ {noise:.4f} と同水準なら良)")
    print(f"内外分類の一致率            : {agree * 100:.2f}%")
    print(f"零点(球1個)残差 / SQ残差   : {res_sphere:.4e} / {res_fit:.4e}  = {beat_ratio:.2f}x")

    # --- assert: 主張を検証で固定 ------------------------------------------
    assert a_rel_err < 0.05, f"半径の復元が 5% を超えた: {a_rel_err * 100:.2f}%"
    assert rms_fit < 3.0 * noise, \
        f"残差がノイズ水準に収束していない: sqrt(res)={rms_fit:.4f} vs noise={noise:.4f}"
    assert agree > 0.95, f"内外分類の一致率が 95% 未満: {agree * 100:.2f}%"
    assert beat_ratio > 2.0, \
        f"零点(球)を明確に上回れていない: 球残差はSQ残差の {beat_ratio:.2f}x のみ"

    print(
        f"PASS: 角丸ブロックを点群から復元 — 半径誤差 {a_rel_err * 100:.2f}% (<5%), "
        f"内外一致 {agree * 100:.1f}% (>95%), 残差 {rms_fit:.4f} ~ ノイズ {noise:.4f}, "
        f"球零点の {beat_ratio:.1f}x 良い"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
