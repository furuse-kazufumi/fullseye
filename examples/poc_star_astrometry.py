# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_star_astrometry — 星の位置は何分の 1 画素まで測れるのか。(執筆中)

    py -3.11 examples/poc_star_astrometry.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.special import erf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import astrostack as A          # noqa: E402
import fit_transform as FT      # noqa: E402

ARCSEC = 180.0 * 3600.0 / np.pi          # rad → 秒角
SIGMA_PER_FWHM = 1.0 / A.FWHM_PER_SIGMA

# ── 真値(私が決める。ここに書いた数以外の情報は推定側に渡さない)────────────── #
RA0_DEG, DEC0_DEG = 83.0, -5.0           # 接点(接平面投影の原点)
PLATE_ARCSEC_PX = 1.20                   # プレートスケール
PLATE_ROT_DEG = 17.0                     # 天の北 と 画像の行 のなす角
CRPIX_ROW, CRPIX_COL = 127.3, 128.7      # 接点が落ちる画素(わざと副画素)
SHAPE = (256, 256)
SKY, READ = 80.0, 5.0                    # 背景 [e-/px] と読み出し雑音 [e- rms]
FULL_WELL = 65000.0                      # 飽和レベル [e-]


# ------------------------------------------------------------------------- #
# 0) 天球 → 画素 の真値経路(接平面投影 + プレート定数)                       #
# ------------------------------------------------------------------------- #
def sky_to_standard(ra_deg, dec_deg, ra0_deg=RA0_DEG, dec0_deg=DEC0_DEG):
    """接平面(gnomonic / TAN)投影。返り値は標準座標 ``(xi, eta)`` [秒角]。

    ``xi`` は東向き、``eta`` は北向き。接点で 1 次まで平坦、視野の端で
    ``tan`` のぶんだけ伸びる —— この伸びが「線形なプレート定数で足りるか」を
    決めるので、投影を先に通してからプレート定数を当てる。
    """
    ra, dec = np.deg2rad(np.asarray(ra_deg, float)), np.deg2rad(np.asarray(dec_deg, float))
    ra0, dec0 = np.deg2rad(ra0_deg), np.deg2rad(dec0_deg)
    d = np.sin(dec) * np.sin(dec0) + np.cos(dec) * np.cos(dec0) * np.cos(ra - ra0)
    xi = np.cos(dec) * np.sin(ra - ra0) / d
    eta = (np.sin(dec) * np.cos(dec0) - np.cos(dec) * np.sin(dec0) * np.cos(ra - ra0)) / d
    return xi * ARCSEC, eta * ARCSEC


def standard_to_sky(xi_as, eta_as, ra0_deg=RA0_DEG, dec0_deg=DEC0_DEG):
    """:func:`sky_to_standard` の逆。標準座標 [秒角] → ``(ra_deg, dec_deg)``。"""
    xi, eta = np.asarray(xi_as, float) / ARCSEC, np.asarray(eta_as, float) / ARCSEC
    ra0, dec0 = np.deg2rad(ra0_deg), np.deg2rad(dec0_deg)
    den = np.cos(dec0) - eta * np.sin(dec0)
    ra = ra0 + np.arctan2(xi, den)
    dec = np.arctan2((np.sin(dec0) + eta * np.cos(dec0)) * np.cos(ra - ra0), den)
    return np.rad2deg(ra), np.rad2deg(dec)


def plate_forward(xi_as, eta_as, scale=PLATE_ARCSEC_PX, rot_deg=PLATE_ROT_DEG,
                  crpix_row=CRPIX_ROW, crpix_col=CRPIX_COL):
    """プレート定数(スケール・回転・原点)で 標準座標 → ``(row, col)`` 画素。"""
    t = np.deg2rad(rot_deg)
    xi, eta = np.asarray(xi_as, float), np.asarray(eta_as, float)
    col = crpix_col + (xi * np.cos(t) + eta * np.sin(t)) / scale
    row = crpix_row + (-xi * np.sin(t) + eta * np.cos(t)) / scale
    return row, col


def plate_inverse(row, col, scale=PLATE_ARCSEC_PX, rot_deg=PLATE_ROT_DEG,
                  crpix_row=CRPIX_ROW, crpix_col=CRPIX_COL):
    """:func:`plate_forward` の逆。``(row, col)`` → 標準座標 [秒角]。"""
    t = np.deg2rad(rot_deg)
    dr, dc = np.asarray(row, float) - crpix_row, np.asarray(col, float) - crpix_col
    xi = (dc * np.cos(t) - dr * np.sin(t)) * scale
    eta = (dc * np.sin(t) + dr * np.cos(t)) * scale
    return xi, eta


# ------------------------------------------------------------------------- #
# 画像の合成(★ 穴: 指定座標に星を置く公開 op が fullseye に無い)            #
# ------------------------------------------------------------------------- #
def render(shape, rows, cols, fluxes, fwhm_px, sky=SKY, read=READ, seed=None,
           full_well=None, extra=None):
    """指定座標にガウシアン星を置いた 1 枚。単位は電子。

    画素は箱で積分する(``erf`` の差)ので、星 1 個の総和は与えたフラックスに
    厳密に一致する —— ``astrostack.synth_starfield`` と同じ描き方だが、
    あちらは座標を**乱数で決める**ので既知の天球座標を置けない。

    *seed* が ``None`` なら雑音を入れない(= 期待値画像)。*full_well* を
    与えると Poisson の**前**に飽和で切る。*extra* は ``(row, col, e-)`` の列で、
    Poisson の後に足す(宇宙線は光子ではない)。
    """
    h, w = shape
    img = np.full((h, w), float(sky))
    rr = np.arange(h)[:, None]
    cc = np.arange(w)[None, :]
    sig = float(fwhm_px) * SIGMA_PER_FWHM
    s2 = sig * np.sqrt(2.0)
    for r0, c0, f in zip(np.atleast_1d(rows), np.atleast_1d(cols), np.atleast_1d(fluxes)):
        fr = 0.5 * (erf((rr + 0.5 - r0) / s2) - erf((rr - 0.5 - r0) / s2))
        fc = 0.5 * (erf((cc + 0.5 - c0) / s2) - erf((cc - 0.5 - c0) / s2))
        img += float(f) * fr * fc
    if full_well is not None:
        img = np.minimum(img, float(full_well))
    if seed is not None:
        rng = np.random.default_rng(int(seed))
        img = rng.poisson(np.maximum(img, 0.0)).astype(float)
        img += rng.normal(0.0, READ if read is None else read, img.shape)
    if extra:
        for r0, c0, f in extra:
            img[int(r0), int(c0)] += float(f)
    if full_well is not None:
        img = np.minimum(img, float(full_well))
    return img


def profile(shape, r0, c0, fwhm_px):
    """1 星の**画素あたりの取り分**(総和 1)。CRLB の微分に使う。"""
    return render(shape, [r0], [c0], [1.0], fwhm_px, sky=0.0, read=0.0, seed=None)


# ------------------------------------------------------------------------- #
# 4 つの測位手法                                                              #
# ------------------------------------------------------------------------- #
def _stamp(img, r0, c0, box):
    h = box // 2
    r, c = int(round(r0)), int(round(c0))
    return img[r - h:r + h + 1, c - h:c + h + 1], r - h, c - h


def m_centroid(img, centers, box=11, **_):
    """**ゼロ点** —— 素の 1 次モーメント。背景も引かず、閾値も引かない。"""
    out = []
    for r0, c0 in centers:
        st, r_off, c_off = _stamp(img, r0, c0, box)
        w = np.maximum(st, 0.0)
        tot = w.sum()
        if tot <= 0:
            out.append((np.nan, np.nan))
            continue
        rr = np.arange(st.shape[0])[:, None]
        cc = np.arange(st.shape[1])[None, :]
        out.append(((w * rr).sum() / tot + r_off, (w * cc).sum() / tot + c_off))
    return np.array(out, float)


def m_centroid_bg(img, centers, box=11, bkg=None, floor_sigma=1.0, noise=None, **_):
    """背景を引き、``floor_sigma`` σ 以下を 0 に落としてから重み付き重心。

    ``star_detect`` が中でやっているのと同じ考え方(背景減算 + 窓)。
    """
    b = float(np.median(img)) if bkg is None else float(bkg)
    n = A.noise_sigma(img) if noise is None else float(noise)
    out = []
    for r0, c0 in centers:
        st, r_off, c_off = _stamp(img, r0, c0, box)
        w = np.maximum(st - b - floor_sigma * n, 0.0)
        tot = w.sum()
        if tot <= 0:
            out.append((np.nan, np.nan))
            continue
        rr = np.arange(st.shape[0])[:, None]
        cc = np.arange(st.shape[1])[None, :]
        out.append(((w * rr).sum() / tot + r_off, (w * cc).sum() / tot + c_off))
    return np.array(out, float)


def m_gaussfit(img, centers, box=11, **_):
    """``astrostack.psf_fit`` の楕円ガウシアン当てはめ(fullseye の op)。"""
    res = A.psf_fit(img, np.asarray(centers, float), model="gaussian", box=box)
    return np.array([[d["row"], d["col"]] for d in res], float)


def m_psfcorr(img, centers, box=11, fwhm_px=3.2, bkg=None, **_):
    """既知 PSF の整合フィルタ + **対数**放物線補間。

    ガウシアンで平滑したガウシアンはガウシアンなので、対数は厳密に放物線に
    なる —— 3 点の対数に放物線を当てれば、雑音と画素積分が無ければ頂点は
    真の位置に一致する。線形値の放物線ではこうならない(段 2 で差が出る)。
    """
    b = float(np.median(img)) if bkg is None else float(bkg)
    sm = gaussian_filter(img - b, float(fwhm_px) * SIGMA_PER_FWHM, mode="nearest")
    out = []
    for r0, c0 in centers:
        st, r_off, c_off = _stamp(sm, r0, c0, box)
        i, j = np.unravel_index(int(np.argmax(st)), st.shape)
        i = min(max(i, 1), st.shape[0] - 2)
        j = min(max(j, 1), st.shape[1] - 2)
        pos = []
        for tri in (st[i - 1:i + 2, j], st[i, j - 1:j + 2]):
            y = np.asarray(tri, float)
            y = np.log(y) if y.min() > 0 else y          # 正でなければ線形に退避
            den = y[0] - 2.0 * y[1] + y[2]
            pos.append(0.0 if den == 0 else 0.5 * (y[0] - y[2]) / den)
        out.append((i + pos[0] + r_off, j + pos[1] + c_off))
    return np.array(out, float)


METHODS = (("重心(ゼロ点)", m_centroid),
           ("背景引き重心", m_centroid_bg),
           ("ガウシアン当てはめ", m_gaussfit),
           ("PSF 相関", m_psfcorr))


def crlb_px(flux, fwhm_px, sky=SKY, read=READ, box=21):
    """この雑音モデルでの位置の下限 ``sigma`` [px](1 軸)。

    Fisher 情報 ``I = sum_i (dmu_i/dx)^2 / var_i`` を、実際に描くのと同じ
    画素積分プロファイルの数値微分から出す。``var_i = mu_i + read^2``。
    """
    shp = (box, box)
    c = (box - 1) / 2.0
    h = 1e-3
    p0 = profile(shp, c, c, fwhm_px)
    dp = (profile(shp, c + h, c, fwhm_px) - profile(shp, c - h, c, fwhm_px)) / (2 * h)
    var = flux * p0 + sky + read ** 2
    return float(1.0 / np.sqrt(((flux * dp) ** 2 / var).sum()))


def pad(text, width, right=False):
    """全角を 2 桁と数えて表の桁を揃える(固定幅の表を日本語で書くため)。"""
    import unicodedata
    w = sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)
    fill = " " * max(0, width - w)
    return fill + text if right else text + fill


def bias_scatter(err):
    """``(bias, scatter)``。偏りと散らばりは別の量なので必ず分けて返す。"""
    e = np.asarray(err, float)
    e = e[np.isfinite(e)]
    return float(e.mean()), float(e.std(ddof=1))


def main():
    timing = {}
    print("=" * 78)
    print("poc_star_astrometry — 星の位置は何分の 1 画素まで測れるのか")
    print("=" * 78)

    # --------------------------------------------------------------- #
    # 0) 真値の経路を往復で検算する                                     #
    # --------------------------------------------------------------- #
    t0 = time.perf_counter()
    rng = np.random.default_rng(7)
    ra_t = RA0_DEG + rng.uniform(-0.05, 0.05, 500) / np.cos(np.deg2rad(DEC0_DEG))
    dec_t = DEC0_DEG + rng.uniform(-0.05, 0.05, 500)
    xi, eta = sky_to_standard(ra_t, dec_t)
    ra_b, dec_b = standard_to_sky(xi, eta)
    d_sky = np.hypot((ra_b - ra_t) * np.cos(np.deg2rad(DEC0_DEG)), dec_b - dec_t) * 3600.0
    rr, cc = plate_forward(xi, eta)
    xi_b, eta_b = plate_inverse(rr, cc)
    d_plate = np.hypot(xi_b - xi, eta_b - eta)
    print("\n【0】真値の経路 —— 天球 → 接平面投影 → プレート定数 → 画素")
    print(f"   接点 (RA, Dec) = ({RA0_DEG}, {DEC0_DEG}) deg   スケール "
          f"{PLATE_ARCSEC_PX} 秒角/px   回転 {PLATE_ROT_DEG} deg   "
          f"原点 (row, col) = ({CRPIX_ROW}, {CRPIX_COL})")
    print(f"   往復検算 500 点: 投影の往復 最大 {d_sky.max():.3e} 秒角 / "
          f"プレートの往復 最大 {d_plate.max():.3e} 秒角(倍精度の丸めの桁)")
    assert d_sky.max() < 1e-8 and d_plate.max() < 1e-9
    print(f"   視野 {SHAPE[0]}x{SHAPE[1]} px = "
          f"{SHAPE[0] * PLATE_ARCSEC_PX / 60:.2f} 分角四方。"
          f"1 px = {PLATE_ARCSEC_PX} 秒角 なので "
          f"0.01 px = {0.01 * PLATE_ARCSEC_PX * 1000:.0f} ミリ秒角")
    timing["0 真値"] = time.perf_counter() - t0

    # --------------------------------------------------------------- #
    # 1) S/N を振る —— 4 手法はどこで床に当たるか。理論限界と比べる      #
    # --------------------------------------------------------------- #
    t0 = time.perf_counter()
    grid = np.arange(16, SHAPE[0] - 12, 32.0)
    gr, gc = np.meshgrid(grid, grid)
    base_r, base_c = gr.ravel(), gc.ravel()
    n_grid, n_rep = base_r.size, 6
    fluxes = (300.0, 1000.0, 3000.0, 10000.0, 30000.0, 100000.0)
    print(f"\n【1】S/N を振る —— 孤立星 {n_grid} 個 x {n_rep} 実現 = "
          f"{n_grid * n_rep} 標本 x 2 軸 / 明るさ。FWHM 3.2 px、"
          f"位相は毎回一様乱数(画素位相を平均化する)。初期値は全手法で同じ"
          f"(真値の四捨五入)なので、検出のずれは混ざらない")
    print(f"   理論下限は Fisher 情報から: I = Σ(∂μ/∂x)^2 / (μ + read^2)、"
          f"μ は描くのと同じ画素積分。**この雑音モデルそのものの下限**であって"
          f"経験式ではない")
    sn_tab, raw = {}, {}
    for flux in fluxes:
        errs = {lab: [] for lab, _ in METHODS}
        frac = []
        for rep in range(n_rep):
            rg = np.random.default_rng(1000 + rep)
            dr = rg.uniform(-0.5, 0.5, n_grid)
            dc = rg.uniform(-0.5, 0.5, n_grid)
            tr, tc = base_r + dr, base_c + dc
            img = render(SHAPE, tr, tc, np.full(n_grid, flux), 3.2, seed=500 + rep)
            guess = np.stack([np.round(tr), np.round(tc)], axis=1)
            frac.append(np.concatenate([tr - guess[:, 0], tc - guess[:, 1]]))
            for lab, fn in METHODS:
                got = fn(img, guess, box=11, fwhm_px=3.2)
                errs[lab].append(np.concatenate([got[:, 0] - tr, got[:, 1] - tc]))
        frac = np.concatenate(frac)
        raw[flux] = (frac, {lab: np.concatenate(v) for lab, v in errs.items()})
        sn_tab[flux] = {}
        for lab, _ in METHODS:
            e = np.concatenate(errs[lab])
            b, s = bias_scatter(e)
            # 感度 = (返り値 - 初期値) を (真値 - 初期値) に回帰した傾き。
            # 1 なら星を追えている、0 なら**初期値をそのまま返している**。
            slope = float(np.polyfit(frac, frac + e, 1)[0])
            sn_tab[flux][lab] = (b, s, float(np.sqrt(np.nanmean(e ** 2))),
                                 crlb_px(flux, 3.2), slope)
    print("     " + pad("手法", 20) + "flux[e-]   S/N      偏り   散らばり"
          "       RMS  理論下限  RMS/下限    感度")
    for lab, _ in METHODS:
        for flux in fluxes:
            b, s, r, c, sl = sn_tab[flux][lab]
            snr = flux / np.sqrt(flux + 121.0 * (SKY + READ ** 2))
            print("     " + pad(lab, 20) + f"{flux:8.0f}{snr:6.1f} {b:+9.4f}"
                  f"{s:10.4f}{r:10.4f}{c:9.4f}{r / c:10.2f}{sl:8.3f}")
        print()
    zero = sn_tab[300.0]["重心(ゼロ点)"]
    print(f"   ★ 素の重心は暗い端で **散らばり {zero[1]:.4f} px が理論下限 "
          f"{zero[3]:.4f} px を下回る** —— 一見「限界を破った」ように見えるが、"
          f"感度 {zero[4]:.3f} が正体を明かす: 11x11 の箱に入る空 "
          f"{121 * SKY:.0f} e- が星 300 e- を圧倒し、返っているのは"
          f"**初期値(真値の四捨五入)そのもの**。誤差は端数の一様分布で、"
          f"その標準偏差 1/√12 = {1 / np.sqrt(12):.4f} px と一致する"
          f"(実測 {zero[1]:.4f})。**散らばりだけを見ると不動の推定器が勝つ**")
    assert zero[4] < 0.2 and abs(zero[1] - 1 / np.sqrt(12)) < 0.02
    assert all(sn_tab[300.0][lab][4] > 0.7 for lab in
               ("背景引き重心", "ガウシアン当てはめ", "PSF 相関"))
    bright = {lab: sn_tab[100000.0][lab][2] / sn_tab[100000.0][lab][3]
              for lab, _ in METHODS}
    print(f"   明るい端(flux 1e5、S/N 298)で理論下限に対する RMS 比: " + " / ".join(
        f"{lab} {bright[lab]:.2f}x" for lab, _ in METHODS))
    print(f"   → **理論限界は上回れない**。最良でも背景引き重心の "
          f"{min(bright.values()):.2f}x で、下回った例は 1 つも無い"
          f"(下回って見えるのは上の「動かない推定器」だけ)")
    assert min(bright.values()) > 0.95
    assert bright["ガウシアン当てはめ"] < 2.0 and bright["PSF 相関"] < 2.0
    timing["1 S/N"] = time.perf_counter() - t0

    print("\nPASS(執筆中)")
    return True


if __name__ == "__main__":
    main()
