# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 構造色を**波長から**作る(回折・薄膜干渉・異方性)。

やりたいこと(素朴な言葉で): CD の虹、シャボン玉の色、ヘアラインの伸びたハイライト。
どれも「色を塗る」のではなく、面の微細構造が**波長ごとに違う反射**を返す結果である。
分光反射率を作り、CIE 1931 等色関数で積分して線形 sRGB に落とす ―― だから角度を
変えれば色が動き、格子ピッチや膜厚を変えれば色そのものが変わる。

使う op(matappear 7 つ全部): cie_xyz_from_wavelength / spectrum_to_srgb /
thin_film_reflectance / grating_wavelengths / grating_rgb / thin_film_rgb /
ward_anisotropic。

検証(GT): 閉じた式と公開値で固定する。
  * 等色関数 ȳ のピークは 555 nm 近傍(CIE 1931 の既知値)。
  * 反射率 1 の面は sRGB の基準白 (1,1,1) に落ちる(白色順応が効いている)。
  * 膜厚 0 の薄膜は**基板単体のフレネル反射に厳密一致**、λ/4 は解析値に一致。
  * 回折は格子の式 d(sinθo − sinθi) = mλ を**そのまま**満たす(CD 1.6 µm で 560 nm)。
  * Ward の異方性はハイライトの伸び比が αx/αy に従う(等方なら円)。

beat-the-null: 「色を塗る」零点との対比 —— 分光を通さずに固定 RGB を返すのは、
角度を変えても色が動かない。ここでは同じ幾何で pitch を変えると**選ばれる波長が変わり**、
可視域を外れれば暗くなることを数字で示す(BD 0.32 µm は同条件で可視域に届かない)。
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from matappear import (cie_xyz_from_wavelength, grating_rgb, grating_wavelengths,
                       spectrum_to_srgb, thin_film_reflectance, thin_film_rgb,
                       ward_anisotropic)


def hemisphere(n=96):
    y, x = np.mgrid[-1:1:n * 1j, -1:1:n * 1j]
    r2 = x * x + y * y
    m = r2 < 1.0
    z = np.sqrt(np.maximum(1.0 - r2, 0.0))
    return np.stack([x, y, z], -1) * m[..., None], m


def extent(a):
    m = a > 0.1 * a.max()
    ys, xs = np.nonzero(m)
    return int(np.ptp(xs)) + 1, int(np.ptp(ys)) + 1


def main() -> None:
    print("=" * 78)
    print("構造色: 回折・薄膜干渉・異方性を波長から作る")
    print("=" * 78)

    # --- 1) 等色関数と分光 → sRGB ------------------------------------------
    w = np.linspace(360.0, 830.0, 471)
    cmf = cie_xyz_from_wavelength(w)
    peak = float(w[int(cmf[:, 1].argmax())])
    white = spectrum_to_srgb(w, np.ones_like(w))
    half = spectrum_to_srgb(w, np.full_like(w, 0.5))
    print(f"等色関数 ȳ のピーク      : {peak:.0f} nm  (CIE 1931 の既知値 555 nm)")
    print(f"反射率 1.0 → 線形 sRGB   : {np.round(white, 6)}  (基準白 = (1,1,1))")
    print(f"反射率 0.5 → 線形 sRGB   : {np.round(half, 6)}")
    assert abs(peak - 555.0) <= 3.0
    assert np.allclose(white, 1.0, atol=1e-3) and np.allclose(half, 0.5, atol=1e-3)

    # --- 2) 薄膜干渉 --------------------------------------------------------
    n_film, n_sub = 1.33, 1.5
    r0 = float(thin_film_reflectance([550.0], 0.0, n_film, n_sub)[0])
    bare = ((1.0 - n_sub) / (1.0 + n_sub)) ** 2
    qw = float(thin_film_reflectance([550.0], 550.0 / (4 * n_film), n_film, 1.0)[0])
    qw_exact = ((n_film ** 2 - 1.0) / (n_film ** 2 + 1.0)) ** 2
    print(f"膜厚 0 の反射率           : {r0:.9f}  (基板単体のフレネル {bare:.9f})")
    print(f"λ/4 膜の反射率            : {qw:.9f}  (解析値 {qw_exact:.9f})")
    assert abs(r0 - bare) < 1e-12 and abs(qw - qw_exact) < 1e-9

    # --- 3) 回折格子(CD の虹)----------------------------------------------
    lam = grating_wavelengths(1.6, 0.0, 0.35, orders=(1, 2))
    print(f"CD 1.6 µm・Δsin 0.35 の 1 次 : {float(lam[0]):.1f} nm(2 次 {float(lam[1]):.1f} nm)")
    assert abs(float(lam[0]) - 560.0) < 1e-9

    N, mask = hemisphere()
    across = np.array([0.0, 0.55, 0.83]); across /= np.linalg.norm(across)
    cd = grating_rgb(N, light=across, view=(0, 0, 1), tangent=(1, 0, 0), pitch_um=1.6)
    bd = grating_rgb(N, light=across, view=(0, 0, 1), tangent=(1, 0, 0), pitch_um=0.32)
    e_cd = float(np.abs(cd[mask]).sum())
    e_bd = float(np.abs(bd[mask]).sum())
    print(f"回折色の総量  CD {e_cd:.1f}  対  BD {e_bd:.1f}  (BD は同条件で可視域に届かない)")
    assert e_cd > 3.0 * e_bd

    # --- 4) 薄膜の色は膜厚で動く -------------------------------------------
    a = thin_film_rgb(N, thickness_nm=250.0)
    b = thin_film_rgb(N, thickness_nm=520.0)
    print(f"膜厚 250 → 520 nm の色差   : 平均 {float(np.abs(a[mask] - b[mask]).mean()):.4f}")
    assert float(np.abs(a[mask] - b[mask]).mean()) > 0.01

    # --- 5) 異方性ハイライト ------------------------------------------------
    L = np.array([0.4, 0.5, 0.77]); L /= np.linalg.norm(L)
    wide = ward_anisotropic(N, light=L, view=(0, 0, 1), alpha_x=0.30, alpha_y=0.03)
    tall = ward_anisotropic(N, light=L, view=(0, 0, 1), alpha_x=0.03, alpha_y=0.30)
    iso = ward_anisotropic(N, light=L, view=(0, 0, 1), alpha_x=0.15, alpha_y=0.15)
    ew, et, ei = extent(wide), extent(tall), extent(iso)
    print(f"ハイライトの伸び (x, y)  : αx>αy {ew} / αx<αy {et} / 等方 {ei}")
    assert ew[0] > 3 * ew[1] and et[1] > 3 * et[0] and 0.7 < ei[0] / ei[1] < 1.4

    print(f"PASS: 等色関数のピーク {peak:.0f} nm・白 (1,1,1)・膜厚 0 が厳密にフレネル・"
          f"CD の 1 次 560 nm・異方性の伸び {ew[0]}:{ew[1]} —— すべて閉じた式と一致")


if __name__ == "__main__":
    main()
