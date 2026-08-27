"""低線量スパースビューCT再構成の例(radon 前方投影 → SART / FBP 逆投影)。

実世界の問題:
    被曝量を抑えるため「少ない角度数」でしか投影を撮らない低線量CT(sparse-view CT)を
    想定し、指の断面を前方投影(サイノグラム化)してから断面像へ再構成する。撮影角度を
    間引くほど被曝は減るが、再構成は難しくなる — その質を正直に評価するのが狙い。

原理:
    - 前方投影 (Radon 変換): 断面像を各角度から平行レイで積分し、サイノグラム
      (行=角度, 列=検出器) を作る。fullseye の backends_tomo.tm_radon_forward(v, a, b) は
      a=取得角度数のノブ (n≈round(H*a), 8..360 にクランプ), b=角度スパンのノブ
      (span=180*(0.5+0.5*b) deg)。ここでは a=b=0.5 → 角度数 ~round(H*0.5)、
      スパン 135deg の「疎な・限定角度」取得を模す。
    - 逆再構成:
        tm_sart_reconstruct(sino, a, b) … 代数的反復再構成(SART/SIRT)。疎ビュー向き。
        tm_fbp_reconstruct(sino, a, b)  … フィルタ補正逆投影(古典的解析法)。

正直な評価 (BE HONEST):
    この断面は 24x31 と非常に低解像度で、しかも疎ビュー・限定角度なので、再構成は
    「そこそこ」にしかならない。完全再構成を主張してはいけない。実測で GT との相関は
    SART/FBP とも ~0.65 程度。したがって assert は控えめな実閾値 correlation > 0.4
    のみを課す(低線量スパースビューの現実的な下限)。
"""
from __future__ import annotations

import os
import sys
import warnings

import numpy as np

# skimage の radon が出す "image must be zero outside the reconstruction circle" は
# 正方形入力に対する既知の良性警告なので、出力を汚さないよう抑制する。
warnings.filterwarnings("ignore", message=".*reconstruction circle.*")

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import backends_tomo as tomo  # fullseye: tm_radon_forward / tm_sart_reconstruct / tm_fbp_reconstruct


def load_volume() -> np.ndarray:
    path = os.path.join(_REPO_ROOT, "studio_assets", "sample_3d", "skeleton_ct.npy")
    return np.load(path).astype(np.float64)


def _normalize(a: np.ndarray) -> np.ndarray:
    """[0,1] 正規化(スケール不変な比較のため)。"""
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / (hi - lo + 1e-9)


def correlation(a: np.ndarray, b: np.ndarray) -> float:
    """ピアソン相関係数(構造の一致度)。"""
    a = a.ravel() - a.mean()
    b = b.ravel() - b.mean()
    denom = np.sqrt((a * a).sum() * (b * b).sum()) + 1e-12
    return float((a * b).sum() / denom)


def psnr(gt: np.ndarray, rec: np.ndarray) -> float:
    """正規化後の PSNR (dB)。"""
    g, r = _normalize(gt), _normalize(rec)
    mse = float(np.mean((g - r) ** 2))
    return 10.0 * np.log10(1.0 / (mse + 1e-12))


def main() -> int:
    vol = load_volume()

    # 指を通る断面を選ぶ: 骨ボクセルが最も多い y 位置の断面 vol[:, j, :] (z, x)。
    bone = vol > (vol.mean() + vol.std())
    j = int(np.argmax(bone.sum(axis=(0, 2))))
    sl = vol[:, j, :]  # (z=24, x=31) の指断面(GT)
    print(f"[GT] finger cross-section at y={j}, slice shape = {sl.shape}, "
          f"bone voxels in slice = {int(bone[:, j, :].sum())}")

    # 前方投影: a=b=0.5 = 疎ビュー・限定角度取得。
    a, b = 0.5, 0.5
    sino = tomo.tm_radon_forward(sl, a, b)
    print(f"[GT] sinogram shape = {sino.shape} (a={a} 角度数ノブ, b={b} スパンノブ)")

    # 逆再構成 2 種。
    rec_sart = tomo.tm_sart_reconstruct(sino, a, b)
    rec_fbp = tomo.tm_fbp_reconstruct(sino, a, b)

    c_sart, p_sart = correlation(sl, rec_sart), psnr(sl, rec_sart)
    c_fbp, p_fbp = correlation(sl, rec_fbp), psnr(sl, rec_fbp)
    print(f"[GT] SART reconstruction: correlation = {c_sart:.3f}, PSNR = {p_sart:.2f} dB")
    print(f"[GT] FBP  reconstruction: correlation = {c_fbp:.3f}, PSNR = {p_fbp:.2f} dB")
    print("[GT] 注: 低解像度・疎ビュー・限定角度なので相関 ~0.65 が現実。完全再構成ではない。")

    # --- 自己検証(控えめな実閾値のみ) ---
    assert rec_sart.shape == sl.shape, "SART 再構成の形状が GT と不一致"
    assert rec_fbp.shape == sl.shape, "FBP 再構成の形状が GT と不一致"
    # 低線量スパースビューの現実的な下限: 相関 > 0.4(完全再構成は主張しない)。
    assert c_sart > 0.4, f"SART 相関が下限 0.4 を下回る: {c_sart:.3f}"
    assert c_fbp > 0.4, f"FBP 相関が下限 0.4 を下回る: {c_fbp:.3f}"
    assert np.all(np.isfinite(rec_sart)) and np.all(np.isfinite(rec_fbp)), "再構成に不正値"

    print(f"PASS: 疎ビュー前方投影から SART(corr={c_sart:.3f}) / "
          f"FBP(corr={c_fbp:.3f}) で断面を再構成(低線量相当の控えめな一致)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
