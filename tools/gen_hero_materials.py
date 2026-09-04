# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""記事図: 予告していた材質 3 つ(ヘアライン / CD の虹 / 薄膜干渉)を出す(2026-09-04)。

ユーザーの問い(「鏡面とかガラスは作れないの?」「CD の面みたいな虹は?」「ヘアラインは?」)
のうち、**光線追跡を必要としない 3 つ**をここで出す。どれも色を絵の具として塗るのではなく、
回折・干渉・微小面の統計から**波長ごとに計算して CIE の等色関数で RGB に落とす**ので、
角度を変えれば色が変わり、格子ピッチや膜厚を変えれば色が動く。

図の構成:
  上段 = レンダラに載せた 3 材質(render_beauty(surface=...))
  下段 = その物理の検算(膜厚掃引・格子ピッチ別の 1 次波長・異方性ローブの伸び)

Run: py -3.11 tools/gen_hero_materials.py
出力: docs/articles/assets/hero_materials.png
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matappear as M  # noqa: E402
import render_beauty as rb  # noqa: E402

OUT = ROOT / "docs" / "articles" / "assets" / "hero_materials.png"
S = 420


def torus(R=1.0, r=0.36, nu=160, nv=64):
    """トーラス (V, F)。ヘアライン/CD の「回転体らしさ」を見せるのに使う。"""
    u = np.linspace(0, 2 * np.pi, nu, endpoint=False)
    v = np.linspace(0, 2 * np.pi, nv, endpoint=False)
    U, Vv = np.meshgrid(u, v, indexing="ij")
    X = (R + r * np.cos(Vv)) * np.cos(U)
    Y = (R + r * np.cos(Vv)) * np.sin(U)
    Z = r * np.sin(Vv)
    P = np.stack([X, Y, Z], -1).reshape(-1, 3)
    F = []
    for i in range(nu):
        for j in range(nv):
            a = i * nv + j
            b = ((i + 1) % nu) * nv + j
            c = ((i + 1) % nu) * nv + (j + 1) % nv
            d = i * nv + (j + 1) % nv
            F += [[a, b, c], [a, c, d]]
    return P, np.asarray(F, np.int64)


def sphere(n_lat=64, n_lon=128):
    lat = np.linspace(1e-4, np.pi - 1e-4, n_lat)
    lon = np.linspace(0, 2 * np.pi, n_lon, endpoint=False)
    la, lo = np.meshgrid(lat, lon, indexing="ij")
    P = np.stack([np.sin(la) * np.cos(lo), np.sin(la) * np.sin(lo), np.cos(la)], -1).reshape(-1, 3)
    F = []
    for i in range(n_lat - 1):
        for j in range(n_lon):
            a = i * n_lon + j
            b = i * n_lon + (j + 1) % n_lon
            # ★ 巻き順は外向き。逆にすると法線が内を向き、render_beauty が
            # **例外を出さずに真っ黒**を返す(最初の版がそれで、薄膜の球だけ黒かった)。
            F += [[a, a + n_lon, b], [b, a + n_lon, b + n_lon]]
    return P, np.asarray(F, np.int64)


def strip(img):
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


def main() -> int:
    t0 = time.time()
    Vt, Ft = torus()
    Vs, Fs = sphere()

    common = dict(size=S, ss=2, ao=True, ground_shadow=True, smooth_normals=True,
                  ao_samples=16, shadow_res=384, shadow_samples=4, exposure=1.1)
    # 1) ヘアライン(異方性): 研磨の筋はトーラスの周方向 → 接線を x にとる
    brushed = rb.render_beauty(Vt, Ft, material="metal", albedo=(0.82, 0.84, 0.88),
                               surface="brushed",
                               surface_params={"tangent": (1.0, 0.0, 0.0),
                                               "alpha_x": 0.35, "alpha_y": 0.025,
                                               "strength": 0.5}, **common)
    # 2) CD の虹: 溝は 1.6 µm ピッチ。分散は溝に直交する向きにしか出ないので接線を y に
    # 光源は**溝に直交して大きく寝かせる**(Δsin を稼がないと可視域に届かない)
    cd = rb.render_beauty(Vt, Ft, material="metal", albedo=(0.55, 0.56, 0.60),
                          light=(0.82, 0.0, 0.57), surface="grating",
                          surface_params={"tangent": (0.0, 1.0, 0.0), "pitch_um": 1.6,
                                          "orders": (1, 2, 3), "strength": 0.55,
                                          "width_nm": 45.0}, **common)
    # 3) 薄膜干渉: 水膜 350 nm を基板 n=1.0(シャボン)で
    film = rb.render_beauty(Vs, Fs, material="plastic", albedo=(0.22, 0.24, 0.28),
                            light=(0.35, 0.45, 0.82), surface="thinfilm",
                            surface_params={"thickness_nm": 380.0, "n_film": 1.33,
                                            "n_sub": 1.0, "strength": 1.6}, **common)
    print(f"[render] 3 materials {time.time() - t0:.0f}s", flush=True)

    # --- 下段: 物理の検算 --------------------------------------------------
    # (a) 膜厚 100–800 nm を掃引した色(シャボン玉の色順が出る)
    d_list = np.linspace(100.0, 800.0, S)
    grid = np.linspace(380.0, 720.0, 121)
    Rspec = np.stack([M.thin_film_reflectance(grid, float(d), 1.33, 1.0) for d in d_list])
    sweep = np.clip(M.spectrum_to_srgb(grid, Rspec) * 3.2, 0, 1)          # (S, 3)
    sweep_img = np.repeat(sweep[None, :, :], S, axis=0)

    # (b) 格子ピッチ別: Δsin を掃引したときの ±1/±2 次の波長を色で
    dsin = np.linspace(-0.9, 0.9, S)
    pitches = [(1.6, "CD 1.6 µm"), (0.74, "DVD 0.74 µm"), (0.32, "BD 0.32 µm")]
    rows = []
    for pitch, _lab in pitches:
        lam = M.grating_wavelengths(pitch, 0.0, dsin, orders=(1, -1, 2, -2, 3, -3))
        spd = np.zeros((S, grid.size))
        for k in range(lam.shape[-1]):
            c = lam[..., k]
            ok = np.isfinite(c) & (c > 0)
            spd += np.where(ok[:, None], np.exp(-0.5 * ((grid[None, :] - c[:, None]) / 45.0) ** 2), 0.0)
        rows.append(np.clip(M.spectrum_to_srgb(grid, spd) * 1.6, 0, 1))
    band = S // len(rows)
    grat_img = np.concatenate([np.repeat(r[None, :, :], band, axis=0) for r in rows], axis=0)
    grat_img = np.pad(grat_img, ((0, S - grat_img.shape[0]), (0, 0), (0, 0)))

    # (c) 異方性ローブ: αx/αy を変えたときの伸び(半球の法線マップ上で)
    yy, xx = np.mgrid[-1:1:S * 1j, -1:1:S * 1j]
    r2 = xx * xx + yy * yy
    msk = r2 < 1.0
    nz = np.sqrt(np.maximum(1.0 - r2, 0.0))
    nmap = np.stack([xx, yy, nz], -1) * msk[..., None]
    L = np.array([0.30, 0.32, 0.90]); L /= np.linalg.norm(L)
    lobes = [M.ward_anisotropic(nmap, light=L, view=(0, 0, 1), alpha_x=a, alpha_y=b)
             for a, b in ((0.30, 0.03), (0.12, 0.12), (0.03, 0.30))]
    ratios = []
    for lo in lobes:
        mm = lo > 0.1 * lo.max()
        ys, xs = np.nonzero(mm)
        ratios.append((int(np.ptp(xs)) + 1) / max(int(np.ptp(ys)) + 1, 1))
    lobe_img = np.stack([np.clip(lo / max(lo.max(), 1e-9), 0, 1) for lo in lobes], -1)
    print(f"[check] ward 伸び比 x/y = " + " / ".join(f"{r:.1f}" for r in ratios), flush=True)

    # 検算値(記事に載せる数字)
    w = np.linspace(360.0, 830.0, 471)
    white = M.spectrum_to_srgb(w, np.ones_like(w))
    ybar_peak = float(w[int(M.cie_xyz_from_wavelength(w)[:, 1].argmax())])
    r0 = float(M.thin_film_reflectance([550.0], 0.0, 1.33, 1.5)[0])
    qw = float(M.thin_film_reflectance([550.0], 550.0 / (4 * 1.33), 1.33, 1.0)[0])
    print(f"[check] ȳ peak {ybar_peak:.0f} nm / white {white.round(4)} / "
          f"d=0 R {r0:.6f}(bare 0.040000) / λ/4 R {qw:.6f}(解析 "
          f"{((1.33**2-1)/(1.33**2+1))**2:.6f})", flush=True)
    assert abs(ybar_peak - 555.0) <= 3.0
    assert np.allclose(white, 1.0, atol=1e-3)
    assert abs(r0 - 0.04) < 1e-12
    assert ratios[0] > 3.0 and ratios[2] < 0.34

    panels = [
        (brushed, "ヘアライン(Ward 異方性)"),
        (cd, "CD の虹(回折格子 1.6 µm)"),
        (film, "薄膜干渉(水膜 380 nm)"),
        (sweep_img, "検算: 膜厚 100→800 nm の掃引色(左→右)"),
        (grat_img, "検算: Δsin 掃引 上 CD / 中 DVD / 下 BD"),
        (lobe_img, f"検算: 異方性ローブ 伸び比 {ratios[0]:.0f} : 1 : {ratios[2]:.2f}"),
    ]
    font = ImageFont.truetype("C:/Windows/Fonts/YuGothB.ttc", 20)
    small = ImageFont.truetype("C:/Windows/Fonts/YuGothB.ttc", 17)
    T, pad, cap, head = 400, 12, 34, 70
    cv = Image.new("RGB", (pad + 3 * (T + pad), head + pad + 2 * (T + cap + pad)), (18, 20, 24))
    dr = ImageDraw.Draw(cv)
    dr.text((pad, 8), "予告していた材質 — 波長から計算する 3 つ(光線追跡を要さない)",
            font=font, fill=(240, 240, 240))
    dr.text((pad, 36), "色は塗っていない: 回折・干渉・微小面の統計 → 分光反射率 → CIE 1931 等色関数 → 線形 sRGB"
                       f"(等色関数 y の峰 {ybar_peak:.0f} nm / 白は (1,1,1) に一致)",
            font=small, fill=(198, 200, 206))
    for i, (img, c) in enumerate(panels):
        im = Image.fromarray(strip(img)).resize((T, T), Image.LANCZOS)
        x = pad + (i % 3) * (T + pad)
        y = head + pad + (i // 3) * (T + cap + pad)
        cv.paste(im, (x, y))
        dr.text((x, y + T + 5), c, font=small, fill=(235, 235, 235))
    cv.save(OUT, optimize=True)
    print(f"[fig] {OUT} {cv.size} ({time.time() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
