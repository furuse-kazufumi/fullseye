# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 加工された金属表面と、金属以外の素材(粗い拡散・上塗り・布・木・濡れ・腐食)。

やりたいこと: 「材質 × 仕上げ」で見え方が決まることを op で組む。材質は複素屈折率、
仕上げは**微小面の向きと粗さの場**。金属以外の素材も (1) 粗い拡散 (2) 透明な上塗り
(3) 微細構造 (4) むら の 4 つで説明できる。

使う op(metalfinish 5 + surfacelib 11): finish_catalog / tangent_field /
micro_normals / blast_normals / finish_shade / material_catalog / oren_nayar /
clearcoat_shade / metallic_flake_normals / sheen_shade / weave_normals /
wood_grain / wetness / corrosion_mask / subsurface_approx / rough_transmission。

検証(GT): 退化ケースと保存則で固定する。
  * Oren–Nayar は σ=0 で **Lambert に厳密一致**(粗さ 0 なら同じ式になるべき)。
  * 上塗りは**エネルギーを作らない**: 強くするほど下地の寄与が単調に減る。
  * 布の縁光沢は鏡面と**逆**に、正面で 0・縁で最大(Phong では出せない)。
  * 濡れは拡散を暗くする。腐食マスクの面積率は指定値に一致する。
  * すりガラスの直進 + 拡散 = 透明板の透過率(エネルギー保存)。
  * 接線場は仕上げごとに幾何が違う(同心円は半径に直交、放射は半径に平行)。

beat-the-null: 「粗さを無視して Lambert で描く」零点との対比 —— 端(terminator)の
明るさが 1.2 倍以上変わる。満月が球ではなく円盤に見えるのがこの差である。
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from glassmirror import slab_transmittance
from metalfinish import (FINISHES, blast_normals, finish_catalog, finish_shade,
                         micro_normals, tangent_field)
from surfacelib import (MATERIALS, clearcoat_shade, corrosion_mask, material_catalog,
                        metallic_flake_normals, oren_nayar, rough_transmission,
                        sheen_shade, subsurface_approx, weave_normals, wetness,
                        wood_grain)


def hemisphere(n=96):
    y, x = np.mgrid[-1:1:n * 1j, -1:1:n * 1j]
    r2 = x * x + y * y
    m = r2 < 1.0
    z = np.sqrt(np.maximum(1.0 - r2, 0.0))
    return np.stack([x, y, z], -1) * m[..., None], m


def main() -> None:
    print("=" * 78)
    print("加工された金属表面と素材: 材質 × 仕上げ")
    print("=" * 78)
    N, mask = hemisphere()
    L = np.array([0.3, 0.4, 0.87]); L /= np.linalg.norm(L)

    # --- 1) 仕上げの接線場(幾何が違う)------------------------------------
    h = w = 64
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    r = np.stack([xx - (w - 1) / 2.0, yy - (h - 1) / 2.0], -1)
    r = r / np.maximum(np.linalg.norm(r, axis=-1, keepdims=True), 1e-9)
    inner = np.s_[8:-8, 8:-8]
    circ = tangent_field((h, w), "circular")[..., :2]
    rad = tangent_field((h, w), "radial")[..., :2]
    print(f"仕上げ {len(FINISHES)} 種の接線場 : 同心円が半径と直交 "
          f"{float(np.abs((circ * r).sum(-1))[inner].max()):.2e} / "
          f"放射が半径と平行 {float(np.abs(np.abs((rad * r).sum(-1)) - 1)[inner].max()):.2e}")
    assert np.abs((circ * r).sum(-1))[inner].max() < 1e-9
    cat = finish_catalog()
    assert cat["linear"]["alpha_y"] < cat["random"]["alpha_y"]     # 粗さの順序

    # --- 2) 加工痕と材質 ----------------------------------------------------
    turned = micro_normals(N, "circular", pitch_px=8.0, depth=0.07)
    blasted = blast_normals(N, grain=0.05, cell_px=2.5, seed=1)
    lin = finish_shade(N, "linear", "al", light=L)
    rnd = finish_shade(blasted, "random", "ag", light=L)
    au = finish_shade(turned, "circular", "au", light=L)
    peak = au.reshape(-1, 3)[au.sum(-1).argmax()]
    print(f"旋盤目の金 ピーク色       : {np.round(peak, 3)}  (R>G>B = 材質の色が残る)")
    print(f"ハイライトのピーク 筋あり {float(lin.max()):.3f} 対 梨地 {float(rnd.max()):.3f}")
    assert peak[0] > peak[1] > peak[2] and float(lin.max()) > 2.0 * float(rnd.max())

    # --- 3) 粗い拡散(零点 = Lambert)--------------------------------------
    lam = oren_nayar(N, L, roughness_deg=0.0)
    rough = oren_nayar(N, L, roughness_deg=30.0)
    edge = mask & (lam > 0.01) & (lam < 0.15)
    ratio = float(np.median((rough / np.maximum(lam, 1e-9))[edge]))
    print(f"端の明るさ σ=30° / σ=0    : {ratio:.3f} 倍  (Lambert は σ=0 と厳密一致)")
    unit = N / np.maximum(np.linalg.norm(N, axis=-1, keepdims=True), 1e-12)
    ref = np.clip(np.einsum("ijk,k->ij", unit, L), 0.0, None) * mask
    assert np.abs(lam - ref).max() < 1e-12 and ratio > 1.2

    # --- 4) 上塗り(エネルギーを作らない)----------------------------------
    base = np.array([0.6, 0.2, 0.2])
    contrib = []
    for coat in (0.0, 0.5, 1.0):
        img = clearcoat_shade(base, N, L, coat=coat, coat_roughness=0.6)
        spec = clearcoat_shade(np.zeros(3), N, L, coat=coat, coat_roughness=0.6)
        contrib.append(float((img - spec)[mask].sum()))
    print(f"下地の寄与 coat 0/0.5/1.0 : {np.round(contrib, 1)}  (単調に減る)")
    assert contrib[0] > contrib[1] > contrib[2]
    flake = metallic_flake_normals((64, 64), density=0.12, seed=1)
    assert np.allclose(np.linalg.norm(flake, axis=-1), 1.0, atol=1e-12)

    # --- 5) 布・木・状態 ----------------------------------------------------
    sh = sheen_shade(N, L)
    ndv = np.abs(N[..., 2])
    centre, rim = float(sh[mask & (ndv > 0.95)].mean()), float(sh[mask & (ndv < 0.35)].mean())
    weave = weave_normals((64, 64), warp_px=8.0, weft_px=16.0, depth=0.3)
    mod, fibre = wood_grain((64, 64), ring_px=12.0, angle_deg=20.0)
    dry = np.array([0.5, 0.4, 0.3])
    wet = wetness(dry, 1.0)
    rust = corrosion_mask((160, 160), coverage=0.3, seed=2)
    sss = subsurface_approx(N, L, thickness=0.8)
    print(f"布の縁光沢 正面 {centre:.2e} 対 縁 {rim:.4f}  (鏡面と逆)")
    print(f"濡れ: 乾き {dry} → 濡れ {np.round(wet, 4)}  (暗くなる)")
    print(f"腐食の面積率 指定 0.30 → 実測 {float((rust > 0.5).mean()):.4f}")
    assert rim > 100.0 * max(centre, 1e-9) and np.all(wet < dry)
    assert abs(float((rust > 0.5).mean()) - 0.3) < 0.02
    assert float(mod.std()) > 0.1 and np.allclose(np.linalg.norm(fibre, axis=-1), 1.0, atol=1e-12)
    assert np.allclose(np.linalg.norm(weave, axis=-1), 1.0, atol=1e-12)
    assert float(sss[mask].mean()) > 0.0
    mats = material_catalog()
    assert set(mats) == set(MATERIALS) and mats["paper"]["coat"] < mats["car_paint"]["coat"]

    # --- 6) すりガラス(エネルギー保存)------------------------------------
    clear = float(slab_transmittance(1.0, 1.0, 1.5, 0.0, 0.0))
    for rough_r in (0.0, 0.3, 0.8):
        spec_t, diff_t = rough_transmission(1.0, rough_r)
        total = float(spec_t) + float(diff_t)
        print(f"すりガラス 粗さ {rough_r:.1f}      : 直進 {float(spec_t):.4f} + 拡散 "
              f"{float(diff_t):.4f} = {total:.9f}  (透明板 {clear:.9f})")
        assert abs(total - clear) < 1e-12

    print(f"PASS: Oren–Nayar が σ=0 で Lambert と厳密一致・端は {ratio:.2f} 倍・"
          f"上塗りは下地を単調に減らす・縁光沢は鏡面と逆・腐食面積 0.30 一致・"
          "すりガラスは直進+拡散=平板の透過率")


if __name__ == "__main__":
    main()
