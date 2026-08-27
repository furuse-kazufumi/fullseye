# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 陰影だけから物体表面の凹凸(3D形状)を復元する — フォトメトリックステレオ.

やりたいこと(平たく言うと): カメラは動かさず、物体も動かさず、照明の向きだけを
変えて何枚か撮る。人間も、懐中電灯を左右から当てて影の出方が変われば「ここが盛り
上がっている」と分かる。あれを数値でやる。各画素の「面の向き(法線)」を陰影の変化
から解き、その向きを積分して高さ(凹凸)まで戻す。外観検査(微小な打痕・うねりを法線
マップで顕在化)や、検査サンプルの合成(順方向レンダでループを閉じる)に効く。

方法:
  1. render_lambertian  — 既知の高さ場(ドーム+こぶ)の面の向きに、既知の光を複数方向
                          から当てて陰影画像を合成する(順方向 = 撮影のシミュレーション)。
  2. photometric_stereo — その陰影画像群と光源方向から、画素ごとの法線を逆算する。
  3. integrate_normals  — 復元した法線場を積分して高さ場に戻す。

検証(GT): 合成元の高さ場と面の向きが真値として手元にあるので、
  (a) 復元した法線と真の法線の平均角度誤差 (< 5度)、
  (b) 復元した高さと真の高さの相関 (> 0.98) を直接測れる。
beat-the-null: 「陰影画像1枚の輝度をそのまま高さとみなす」素朴推定を対照に置く。
輝度は高さではなく面の傾き(N·L)に比例するので、素朴推定は法線も高さも大きく外す。
実手法がこの素朴推定を明確に上回ることを assert する(上回れなければ手法の価値は無い)。

honest な前提: Lambertian + 既知光源 + 影なし(全光源で N·L>0)なら線形最小二乗が
厳密。ここでは光源を上向きの円錐内に配して全画素で影が出ないようにし、実センサを
模した微小なガウスノイズだけ乗せる。影やスペキュラが混じる実機では頑健版が要る。
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from photometric import (           # noqa: E402  (sys.path 調整後に import)
    render_lambertian,
    photometric_stereo,
    integrate_normals,
    surface_normals,
    angular_error_deg,
)


# --- 合成データ: 既知の高さ場(ドーム+こぶ)と、その解析的な面の向き(真値) ---
# 高さ場をガウス関数の和で作ると、勾配(=面の傾き)も閉形式で書けるので、
# 数値微分に頼らず「真の法線」を厳密に用意できる。境界付近で高さ~0 に減衰させて
# あるため、周期境界を仮定する Frankot-Chellappa 積分の端の歪みを小さく保てる。
_GAUSSIANS = (
    # (振幅 A, 中心 cx, 中心 cy, 幅 s)
    (0.30,  0.00,  0.00, 0.35),   # 中央の大きなドーム
    (0.15,  0.42, -0.30, 0.20),   # 右下の小さなこぶ
)


def height_and_normals(n=96):
    """ドーム+こぶの高さ場 z(HxW) と、その解析的な単位法線 (H,W,3) を返す。

    z = Σ A exp(-((x-cx)^2+(y-cy)^2)/(2 s^2)) なので
    dz/dx = Σ A exp(...) * (-(x-cx)/s^2)、dz/dy も同様。
    面の法線は n ∝ (-dz/dx, -dz/dy, 1)。
    """
    xs = np.linspace(-1.0, 1.0, n)
    x, y = np.meshgrid(xs, xs)             # (H,W)
    z = np.zeros_like(x)
    dzdx = np.zeros_like(x)
    dzdy = np.zeros_like(x)
    for A, cx, cy, s in _GAUSSIANS:
        g = A * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2.0 * s ** 2))
        z += g
        dzdx += g * (-(x - cx) / s ** 2)
        dzdy += g * (-(y - cy) / s ** 2)
    normals = np.stack([-dzdx, -dzdy, np.ones_like(z)], axis=-1)
    normals /= np.linalg.norm(normals, axis=-1, keepdims=True)
    return z, normals.astype(np.float32)


def light_directions():
    """上向きの円錐内に配した既知光源方向 (N,3)。

    方位を 90 度ずつ 4 方向 + 真上の 1 灯 = 5 灯。全て z 成分が大きい(=上寄り)ので、
    傾きが 30〜40 度程度の面でも N·L>0 が保たれ、影(線形性の破れ)を避けられる。
    真上の 1 灯を混ぜると光源行列の条件数が良くなる。
    """
    elev = np.radians(55.0)               # 地平からの仰角(真上=90度)
    dirs = []
    for az_deg in (0.0, 90.0, 180.0, 270.0):
        az = np.radians(az_deg)
        dirs.append([np.cos(elev) * np.cos(az),
                     np.cos(elev) * np.sin(az),
                     np.sin(elev)])
    dirs.append([0.0, 0.0, 1.0])          # 真上
    return np.asarray(dirs, float)


def pearson(a, b):
    """2 配列の Pearson 相関(平均・スケールに不変)。高さは定数分の自由度があるので相関で測る。"""
    a = np.asarray(a, float).ravel()
    b = np.asarray(b, float).ravel()
    a = a - a.mean()
    b = b - b.mean()
    denom = np.linalg.norm(a) * np.linalg.norm(b) + 1e-12
    return float(a @ b / denom)


def main():
    rng = np.random.default_rng(0)

    # --- 1) 既知の真値を用意し、順方向レンダで陰影画像群を合成 ---
    z_gt, n_gt = height_and_normals(n=96)
    albedo = 1.0                                   # 一様な反射率(単純化)
    lights = light_directions()

    images = np.stack(
        [render_lambertian(n_gt, albedo, lights[i]) for i in range(lights.shape[0])],
        axis=0,
    )                                              # (N,H,W)  各光源での陰影
    # 実センサを模した微小ノイズ(最大輝度の約1%)。影は出していないので線形性は保たれる。
    noise_sigma = 0.01 * float(images.max())
    images = images + rng.normal(0.0, noise_sigma, images.shape)

    # 影が本当に出ていない(全画素・全光源で N·L>0)ことを確認 = honest な前提の担保。
    ndotl_min = min(float((n_gt @ (lights[i] / np.linalg.norm(lights[i]))).min())
                    for i in range(lights.shape[0]))

    # --- 2) 逆問題: 陰影画像群 + 既知光源方向 から法線を復元 ---
    n_rec, _albedo_rec = photometric_stereo(images, lights)

    # --- 3) 復元した法線を積分して高さ場に戻す ---
    z_rec = integrate_normals(n_rec)

    # --- GT 検証 (a) 法線の平均角度誤差、(b) 高さの相関 ---
    ang_err = angular_error_deg(n_rec, n_gt)
    mean_ang_err = float(ang_err.mean())
    height_corr = pearson(z_rec, z_gt)

    # --- beat-the-null: 「1枚の輝度をそのまま高さとみなす」素朴推定 ---
    # 素朴推定に最も有利な 1 枚を選ぶ(=全画像で試して一番当たる結果を null とする)。
    # 輝度の符号反転もあり得るので相関は絶対値で評価。それでも実手法が勝つことを示す。
    null_height_corr = max(abs(pearson(images[i], z_gt)) for i in range(images.shape[0]))
    null_ang_err = min(float(angular_error_deg(surface_normals(images[i]), n_gt).mean())
                       for i in range(images.shape[0]))

    print(f"光源数                       : {lights.shape[0]} 灯")
    print(f"注入ノイズ(標準偏差)         : {noise_sigma:.4f}  (最大輝度の約1%)")
    print(f"最小 N·L (>0 なら影なし)      : {ndotl_min:.3f}")
    print("--- 実手法 (photometric_stereo -> integrate_normals) ---")
    print(f"法線の平均角度誤差 (度)       : {mean_ang_err:.3f}   (目標 < 5)")
    print(f"高さの相関                    : {height_corr:.4f}  (目標 > 0.98)")
    print("--- 素朴推定 (1枚の輝度=高さ) [beat-the-null 対照] ---")
    print(f"法線の平均角度誤差 (度)       : {null_ang_err:.3f}")
    print(f"高さの相関 (絶対値の最良)     : {null_height_corr:.4f}")

    # GT 目標: 復元法線の平均角度誤差 < 5 度、復元高さの相関 > 0.98。
    assert ndotl_min > 0.0, f"影が出ている (min N·L={ndotl_min:.3f}) = 線形性の前提が破れている"
    assert mean_ang_err < 5.0, f"法線の角度誤差が大きすぎる: {mean_ang_err:.3f} 度"
    assert height_corr > 0.98, f"高さの相関が低すぎる: {height_corr:.4f}"
    # beat-the-null: 実手法が素朴推定を明確に上回る(法線誤差は桁違いに小さく、相関は高い)。
    assert mean_ang_err < null_ang_err / 3.0, \
        f"法線誤差が素朴推定を明確に下回らない: 実 {mean_ang_err:.3f} vs null {null_ang_err:.3f}"
    assert height_corr > null_height_corr, \
        f"高さ相関が素朴推定を上回らない: 実 {height_corr:.4f} vs null {null_height_corr:.4f}"

    print(f"PASS: 法線誤差 {mean_ang_err:.2f}度(<5, 素朴推定 {null_ang_err:.1f}度の1/3未満)、"
          f"高さ相関 {height_corr:.3f}(>0.98, 素朴推定 {null_height_corr:.3f} 超)")


if __name__ == "__main__":
    main()
