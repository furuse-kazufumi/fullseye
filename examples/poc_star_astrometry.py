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


def m_gaussfit_w(img, centers, box=11, read=READ, **_):
    """**重み付き**ガウシアン当てはめ(比較用に自前で書いた)。

    ``astrostack.psf_fit`` は残差を ``model - vals`` のまま最小化する ——
    つまり全画素の分散が等しいと仮定している。実際の分散は Poisson なので
    ``var = mu + read^2`` で重みを付けるのが最尤に近い。段 2b でこの差が
    理論下限への到達度をどれだけ変えるかを測る。
    """
    from scipy.optimize import least_squares
    out = []
    for r0, c0 in centers:
        st, r_off, c_off = _stamp(img, r0, c0, box)
        rr, cc = np.indices(st.shape)
        vals = st.ravel().astype(float)
        w = 1.0 / np.sqrt(np.maximum(vals, 1.0) + read ** 2)
        b0 = float(np.median(vals))
        pos = np.maximum(vals - b0, 0.0)
        tot = max(pos.sum(), 1e-12)
        mr = float((pos * rr.ravel()).sum() / tot)
        mc = float((pos * cc.ravel()).sum() / tot)

        def resid(p, rr=rr.ravel(), cc=cc.ravel(), vals=vals, w=w):
            amp, pr, pc, s, bkg = p
            m = bkg + amp * np.exp(-0.5 * (((rr - pr) ** 2 + (cc - pc) ** 2) / s ** 2))
            return (m - vals) * w

        p0 = [max(vals.max() - b0, 1.0), mr, mc, 1.4, b0]
        try:
            res = least_squares(resid, p0, method="lm", max_nfev=500)
            out.append((res.x[1] + r_off, res.x[2] + c_off))
        except Exception:
            out.append((np.nan, np.nan))
    return np.array(out, float)


def m_gaussfit_masked(img, centers, box=15, **_):
    """飽和画素を ``nan`` にした画像を受け取り、**残りの画素だけで**当てはめる。

    段 3 の対策。モデルは対称なので、欠けた画素があっても残りから中心を
    復元できる —— 重心にはこれができない(欠けた形がそのまま偏りになる)。
    """
    from scipy.optimize import least_squares
    out = []
    for r0, c0 in centers:
        st, r_off, c_off = _stamp(img, r0, c0, box)
        rr, cc = np.indices(st.shape)
        v = st.ravel().astype(float)
        ok = np.isfinite(v)
        rr, cc, v = rr.ravel()[ok], cc.ravel()[ok], v[ok]
        b0 = float(np.median(v))
        h = box // 2

        def resid(p, rr=rr, cc=cc, v=v):
            amp, pr, pc, s, bkg = p
            return bkg + amp * np.exp(-0.5 * (((rr - pr) ** 2 + (cc - pc) ** 2)
                                              / s ** 2)) - v

        try:
            res = least_squares(resid, [max(v.max() - b0, 1.0), h, h, 1.4, b0],
                                method="lm", max_nfev=800)
            out.append((res.x[1] + r_off, res.x[2] + c_off))
        except Exception:
            out.append((np.nan, np.nan))
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
    bg300 = sn_tab[300.0]["背景引き重心"][4]
    print(f"   同じ罠は背景引き重心にも **弱く** 効いている: S/N 2.6 で感度 "
          f"{bg300:.3f} —— 真のずれの {100 * (1 - bg300):.0f} % を初期値の側へ"
          f"引き戻している(閾値クリップが雑音の山を切り落とすため)。"
          f"当てはめ系の感度は {sn_tab[300.0]['ガウシアン当てはめ'][4]:.3f} / "
          f"{sn_tab[300.0]['PSF 相関'][4]:.3f} で、この縮み方はしない")
    assert 0.4 < bg300 < 0.8
    assert all(sn_tab[300.0][lab][4] > 0.9 for lab in
               ("ガウシアン当てはめ", "PSF 相関"))
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

    # --------------------------------------------------------------- #
    # 2) 標本化不足 —— 画素位相に依存する系統誤差(偏り)                 #
    # --------------------------------------------------------------- #
    t0 = time.perf_counter()
    print("\n【2】PSF の標本化不足 —— 真の位置を副画素でずらすと、偏りが位相で振れる")
    print(f"   雑音を切った期待値画像(flux 1e5、空 {SKY:.0f} e-/px、箱 11x11)。"
          f"星 1 個を行方向に 0〜1 px ずらし、位相 16 点での誤差の"
          f"**山谷差(peak-to-peak)= 系統誤差の振れ幅**を出す。単位 px "
          f"(1 px = {PLATE_ARCSEC_PX} 秒角)")
    phases = np.linspace(0.0, 1.0, 16, endpoint=False)
    fwhms = (1.0, 1.4, 2.0, 2.5, 3.2, 4.0)

    def phase_curve(fn, fw, flux=1e5, box=11, sky=SKY, seed=None, **kw):
        e = []
        for ph in phases:
            r0, c0 = 32.0 + ph, 32.0
            img = render((64, 64), [r0], [c0], [flux], fw, sky=sky, seed=seed)
            got = fn(img, [(round(r0), round(c0))], box=box, fwhm_px=fw, **kw)
            e.append(got[0, 0] - r0)
        return np.array(e)

    print("     " + pad("手法", 20) + "".join(
        f"{'FWHM ' + format(f, '.1f'):>9s}" for f in fwhms))
    phase_tab = {}
    for lab, fn in METHODS:
        line = "     " + pad(lab, 20)
        phase_tab[lab] = {}
        for fw in fwhms:
            e = phase_curve(fn, fw)
            phase_tab[lab][fw] = (float(e.max() - e.min()), float(e.mean()))
            line += f"{e.max() - e.min():9.4f}"
        print(line)

    # 素の重心の一定値は「標本化」ではなく「空による希釈」で説明できる。
    f_box = float(render((64, 64), [32.0], [32.0], [1e5], 3.2, sky=0.0).sum())
    dilute = 121.0 * SKY / (f_box + 121.0 * SKY)
    print(f"   ★ 素の重心の山谷差は FWHM に**ほとんど依らない** "
          f"({min(v[0] for v in phase_tab['重心(ゼロ点)'].values()):.4f}〜"
          f"{max(v[0] for v in phase_tab['重心(ゼロ点)'].values()):.4f})。"
          f"これは標本化の話ではなく空の希釈: 箱の空 {121 * SKY:.0f} e- と星 "
          f"{f_box:.0f} e- の比 {dilute:.4f} が、端数 -0.5〜+0.5 をそのまま"
          f"箱の中心へ引く → 予測 山谷差 {dilute:.4f} px、実測 "
          f"{phase_tab['重心(ゼロ点)'][3.2][0]:.4f} px(FWHM 3.2)")
    assert abs(phase_tab["重心(ゼロ点)"][3.2][0] - dilute) < 0.01

    bg = phase_tab["背景引き重心"]
    print(f"   ★ 背景引き重心は **U 字**: {bg[1.0][0]:.4f}(FWHM 1.0)→ "
          f"{bg[2.0][0]:.5f}(2.0)→ {bg[2.5][0]:.5f}(2.5)→ "
          f"{bg[3.2][0]:.4f}(3.2)→ {bg[4.0][0]:.4f}(4.0)。"
          f"両端で別の系統誤差が立つ —— 左は標本化不足、右は**箱の切り落とし**")
    e4 = {b: float(np.ptp(phase_curve(m_centroid_bg, 4.0, box=b))) for b in (11, 15, 21)}
    print(f"      右側が箱のせいである証拠: FWHM 4.0 のまま箱だけ広げると "
          + " / ".join(f"箱 {b} で {v:.5f}" for b, v in e4.items())
          + f" —— 箱 21 では {e4[21]:.1e} px まで落ちて**測れなくなる**。"
          f"左側は箱を広げても消えない(標本化は箱の外の話ではない)")
    e1 = {b: float(np.ptp(phase_curve(m_centroid_bg, 1.0, box=b))) for b in (11, 21)}
    print(f"      実際 FWHM 1.0 では 箱 11 で {e1[11]:.4f} / 箱 21 で {e1[21]:.4f} "
          f"= {e1[21] / e1[11]:.2f} 倍(変わらない)")
    assert e4[21] < 0.2 * e4[11] and abs(e1[21] / e1[11] - 1.0) < 0.3

    print(f"   ★ **崖は FWHM 2 px**(Nyquist)。当てはめ系は FWHM 2.0 以上で "
          f"{phase_tab['ガウシアン当てはめ'][2.0][0]:.5f} / "
          f"{phase_tab['PSF 相関'][2.0][0]:.5f} px と実質ゼロなのに、1.4 で "
          f"{phase_tab['ガウシアン当てはめ'][1.4][0]:.4f} / "
          f"{phase_tab['PSF 相関'][1.4][0]:.4f}、1.0 で "
          f"{phase_tab['ガウシアン当てはめ'][1.0][0]:.4f} / "
          f"{phase_tab['PSF 相関'][1.0][0]:.4f} px "
          f"= {PLATE_ARCSEC_PX * phase_tab['PSF 相関'][1.0][0] * 1000:.0f} ミリ秒角。"
          f"**雑音ではないので枚数を重ねても消えない**")
    print(f"   ☆ 予想が外れた点: 「PSF 相関は既知 PSF を使うから標本化不足に強い」"
          f"と思っていたが逆だった —— FWHM 1.0〜1.4 で 4 手法中**最悪**"
          f"({phase_tab['PSF 相関'][1.4][0]:.4f} px、背景引き重心の "
          f"{phase_tab['PSF 相関'][1.4][0] / max(bg[1.4][0], 1e-9):.0f} 倍)。"
          f"「平滑後もガウシアンだから対数は放物線」が成り立つのは連続の話で、"
          f"画素は箱で積分されているうえ ``gaussian_filter`` の核も離散 —— "
          f"標本化が粗いほどその 2 つのずれが効く")
    assert phase_tab["ガウシアン当てはめ"][2.5][0] < 1e-3
    assert phase_tab["PSF 相関"][1.4][0] > 10.0 * phase_tab["PSF 相関"][2.5][0]

    # --- 2b) 当てはめが理論下限に届かない理由 = 重みを付けていないこと ----- #
    print("\n【2b】段 1 で当てはめ系だけ理論下限の 1.2 倍に張り付いた理由")
    print(f"   段 2 で見たとおり FWHM 3.2 の位相系統誤差は "
          f"{phase_tab['ガウシアン当てはめ'][3.2][0]:.5f} px しかないので、"
          f"**位相のせいではない**。``psf_fit`` の残差は ``model - vals`` "
          f"—— 全画素の分散が等しいという仮定で、Poisson には合っていない。"
          f"重みだけ ``1/sqrt(値 + read^2)`` に替えた当てはめと比べる")
    print("     " + pad("flux[e-]", 12) + pad("理論下限", 11)
          + pad("psf_fit(重みなし)", 22) + pad("重み付き(自前)", 20))
    w_gain = {}
    for flux in (3000.0, 30000.0, 100000.0):
        crlb = crlb_px(flux, 3.2)
        got = {}
        for lab, fn in (("u", m_gaussfit), ("w", m_gaussfit_w)):
            ee = []
            for rep in range(6):
                rg = np.random.default_rng(2000 + rep)
                dr = rg.uniform(-0.5, 0.5, n_grid)
                dc = rg.uniform(-0.5, 0.5, n_grid)
                tr, tc = base_r + dr, base_c + dc
                img = render(SHAPE, tr, tc, np.full(n_grid, flux), 3.2, seed=700 + rep)
                guess = np.stack([np.round(tr), np.round(tc)], axis=1)
                p = fn(img, guess, box=11, fwhm_px=3.2)
                ee.append(np.concatenate([p[:, 0] - tr, p[:, 1] - tc]))
            e = np.concatenate(ee)
            got[lab] = float(np.sqrt(np.nanmean(e ** 2)))
        w_gain[flux] = (got["u"] / crlb, got["w"] / crlb)
        print(f"     {flux:>10.0f}  {crlb:9.4f}  {got['u']:9.4f} "
              f"({got['u'] / crlb:.2f}x)      {got['w']:9.4f} "
              f"({got['w'] / crlb:.2f}x)")
    print(f"   → 重みを入れるだけで {w_gain[100000.0][0]:.2f}x → "
          f"{w_gain[100000.0][1]:.2f}x(flux 1e5)。★ **``psf_fit`` は"
          f"重み付けの引数を持たない**ので、この {100 * (1 - w_gain[100000.0][1] / w_gain[100000.0][0]):.0f} % は"
          f"利用者側では取り戻せない(道具の穴として報告する)")
    assert w_gain[100000.0][1] < w_gain[100000.0][0]
    assert abs(w_gain[100000.0][1] - 1.0) < 0.08
    timing["2 位相"] = time.perf_counter() - t0

    # --------------------------------------------------------------- #
    # 3) 飽和 —— ピークが潰れると位置はどこへ行くか                      #
    # --------------------------------------------------------------- #
    t0 = time.perf_counter()
    peak_frac = float(profile((64, 64), 32.0, 32.0, 3.2).max())
    print(f"\n【3】飽和 —— ピークが潰れた星。満杯 {FULL_WELL:.0f} e-/px、"
          f"FWHM 3.2(中心画素の取り分 {peak_frac:.4f})。"
          f"雑音は切って**飽和だけ**の効果を見る")
    print("     " + pad("飽和度", 9) + pad("flux[e-]", 11) + pad("潰れ画素", 10)
          + "".join(pad(lab, 20) for lab, _ in METHODS))
    print("     " + pad("(peak/満杯)", 9) + pad("", 11) + pad("(最大)", 10)
          + "".join(pad("山谷差   平均|e|", 20) for _ in METHODS))
    sat_tab = {}
    for ratio in (0.5, 1.2, 2.0, 4.0, 8.0, 16.0):
        flux = ratio * FULL_WELL / peak_frac
        nsat = 0
        sat_tab[ratio] = {}
        for lab, fn in METHODS:
            e = []
            for ph in phases:
                r0 = 32.0 + ph
                img = render((64, 64), [r0], [32.0], [flux], 3.2, seed=None,
                             full_well=FULL_WELL)
                nsat = max(nsat, int((img >= FULL_WELL - 1e-6).sum()))
                got = fn(img, [(round(r0), 32)], box=11, fwhm_px=3.2)
                e.append(got[0, 0] - r0)
            e = np.array(e)
            sat_tab[ratio][lab] = (float(np.ptp(e)), float(np.abs(e).mean()))
        print("     " + pad(f"{ratio:.1f}x", 9) + f"{flux:10.3e}" + f"{nsat:7d}   "
              + "".join(f"{sat_tab[ratio][lab][0]:9.4f}{sat_tab[ratio][lab][1]:11.4f}"
                        for lab, _ in METHODS))
    g = sat_tab
    print(f"   → 飽和は **偏りを作る**。背景引き重心の山谷差は "
          f"{g[0.5]['背景引き重心'][0]:.4f}(未飽和)→ "
          f"{g[1.2]['背景引き重心'][0]:.4f}(1.2x)→ "
          f"{g[4.0]['背景引き重心'][0]:.4f}(4x)→ "
          f"{g[16.0]['背景引き重心'][0]:.4f} px(16x)= "
          f"{PLATE_ARCSEC_PX * g[16.0]['背景引き重心'][0]:.3f} 秒角。"
          f"潰れた平面は**画素の格子に貼り付く**ので、返る位置が"
          f"格子の側へ引かれる(段 2 の希釈と同じ形の誤差)")
    print(f"   ガウシアン当てはめが一番悪い —— 16x で山谷差 "
          f"{g[16.0]['ガウシアン当てはめ'][0]:.4f} px、平均 |e| "
          f"{g[16.0]['ガウシアン当てはめ'][1]:.4f} px。"
          f"潰れた頂上はガウシアンではないのに、モデルは頂上を一番強く重視する")
    # 対策を 2 つ測る。「潰れた画素を捨てる」だけでは**悪化する**。
    mask_cen, mask_fit = {}, {}
    for ratio in (2.0, 8.0, 16.0):
        flux = ratio * FULL_WELL / peak_frac
        ec, ef = [], []
        for ph in phases:
            r0 = 32.0 + ph
            img = render((64, 64), [r0], [32.0], [flux], 3.2, seed=None,
                         full_well=FULL_WELL)
            msk = img.copy()
            msk[msk >= FULL_WELL - 1e-6] = np.nan      # 潰れた画素を捨てる
            st, r_off, _ = _stamp(msk, round(r0), 32, 15)
            w = np.maximum(np.where(np.isfinite(st), st - SKY, 0.0), 0.0)
            rr = np.arange(st.shape[0])[:, None]
            ec.append((w * rr).sum() / w.sum() + r_off - r0)
            ef.append(m_gaussfit_masked(msk, [(round(r0), 32)], box=15)[0, 0] - r0)
        mask_cen[ratio] = float(np.ptp(np.array(ec)))
        mask_fit[ratio] = float(np.ptp(np.array(ef)))
    print("     " + pad("対策(山谷差 px)", 26) + "".join(
        f"{r:.0f}x 飽和".rjust(12) for r in (2.0, 8.0, 16.0)))
    for name, tab in (("何もしない(背景引き重心)",
                       {r: g[r]["背景引き重心"][0] for r in (2.0, 8.0, 16.0)}),
                      ("潰れた画素を捨てて重心", mask_cen),
                      ("潰れた画素を捨てて当てはめ", mask_fit)):
        print("     " + pad(name, 26) + "".join(
            f"{tab[r]:12.5f}" for r in (2.0, 8.0, 16.0)))
    print(f"   ☆ ここも予想が外れた。**「潰れた画素を捨てる」だけでは "
          f"{mask_cen[16.0] / g[16.0]['背景引き重心'][0]:.0f} 倍悪化する** —— "
          f"捨てた穴の形が画素の格子に量子化され、位相が 0.5 を跨ぐたびに"
          f"穴が 1 画素ぶん非対称になる。残った翼の重心はその非対称を"
          f"そのまま拾う({mask_cen[16.0]:.3f} px = 半画素の桁)。"
          f"対して**同じマスクで当てはめる**と {mask_fit[16.0]:.5f} px —— "
          f"モデルが対称だから、欠けた画素があっても残りから中心が決まる。"
          f"{g[16.0]['背景引き重心'][0] / mask_fit[16.0]:.0f} 倍改善")
    print(f"   ★ fullseye には**画素マスクを受け取る測位 op が無い** —— "
          f"``psf_fit`` にも ``star_detect`` にも ``mask`` / ``saturation`` 引数が"
          f"無く、飽和した星は黙って偏った値を返す(この PoC は自前で書いた)")
    assert g[16.0]["背景引き重心"][0] > 5.0 * g[0.5]["背景引き重心"][0]
    assert mask_cen[16.0] > 5.0 * g[16.0]["背景引き重心"][0]      # 悪化する
    assert mask_fit[16.0] < 0.1 * g[16.0]["背景引き重心"][0]      # 当てはめは効く
    timing["3 飽和"] = time.perf_counter() - t0

    # --------------------------------------------------------------- #
    # 4) 二重星 —— 1 個と誤認する境界と、位置が真ん中に寄る量            #
    # --------------------------------------------------------------- #
    t0 = time.perf_counter()
    fw = 3.2
    sig = fw * SIGMA_PER_FWHM
    seps_fwhm = (0.5, 0.75, 0.85, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0)
    ang = np.deg2rad(30.0)
    print(f"\n【4】二重星 —— 分離を PSF の 0.5〜3.0 倍で振る(FWHM {fw} px、"
          f"σ = {sig:.3f} px、位置角 30 度)。総フラックス 60000 e-、"
          f"雑音あり x 8 実現。検出は ``star_detect``"
          f"(threshold 5σ, min_separation 2)")
    print(f"   理論の目安: 等光度なら 2 つのガウシアンの和が**二峰になる**のは "
          f"分離 > 2σ = {2 * sig:.2f} px = {2 * sig / fw:.2f} FWHM。"
          f"それ未満は原理的に 1 つの山であって、検出器の出来の問題ではない")
    print("     " + pad("分離", 16) + pad("等光度 1:1", 34)
          + pad("不等光度 4:1", 34))
    print("     " + pad("[FWHM]  [px]", 16)
          + pad("2 個検出  1 個時の|e|  光心まで", 34)
          + pad("2 個検出  1 個時の|e|  光心まで", 34))
    dbl = {}
    for sf in seps_fwhm:
        sep = sf * fw
        cells = []
        for f1, f2 in ((30000.0, 30000.0), (48000.0, 12000.0)):
            n2, e_prim, e_phot = 0, [], []
            dr, dc = sep * np.cos(ang) / 2, sep * np.sin(ang) / 2
            r1, c1 = 32.0 - dr, 32.0 - dc
            r2, c2 = 32.0 + dr, 32.0 + dc
            pr = (f1 * r1 + f2 * r2) / (f1 + f2)       # 光心(フラックス重心)
            pc = (f1 * c1 + f2 * c2) / (f1 + f2)
            for k in range(8):
                img = render((64, 64), [r1, r2], [c1, c2], [f1, f2], fw, seed=3000 + k)
                kp = A.star_detect(img, threshold_sigma=5.0, min_separation=2,
                                   max_stars=10)
                near = kp[(np.abs(kp[:, 0] - 32) < 8) & (np.abs(kp[:, 1] - 32) < 8)]
                if len(near) >= 2:
                    n2 += 1
                elif len(near) == 1:
                    got = m_centroid_bg(img, near, box=11)[0]
                    e_prim.append(np.hypot(got[0] - r1, got[1] - c1))
                    e_phot.append(np.hypot(got[0] - pr, got[1] - pc))
            cells.append((n2 / 8.0,
                          float(np.mean(e_prim)) if e_prim else np.nan,
                          float(np.mean(e_phot)) if e_phot else np.nan))
        dbl[sf] = cells
        print(f"     {sf:5.2f}  {sep:6.2f}    " + "  ".join(
            f"{c[0]:6.0%} {c[1]:11.3f} {c[2]:9.4f}" for c in cells)
            + "  ")
    thr_eq = next((sf for sf in seps_fwhm if dbl[sf][0][0] >= 0.5), None)
    thr_un = next((sf for sf in seps_fwhm if dbl[sf][1][0] >= 0.5), None)
    print(f"   → 2 個に割れ始める境界(半数以上で 2 検出): 等光度 "
          f"**{thr_eq:.2f} FWHM**、不等光度 4:1 は **{thr_un:.2f} FWHM** —— "
          f"暗い方が明るい方の翼に埋もれるので "
          f"{thr_un / thr_eq:.1f} 倍遠くまで離れないと割れない")
    # 理論(0.85 FWHM)と実測(1.25 FWHM)の差は「谷が在るか」と
    # 「谷が雑音より深いか」の違い。谷の深さを雑音の単位で測って確かめる。
    print(f"   ☆ 理論の二峰条件 {2 * sig / fw:.2f} FWHM と実測 {thr_eq:.2f} FWHM は "
          f"{thr_eq / (2 * sig / fw):.1f} 倍ずれる。**「谷が在る」と"
          f"「谷が雑音より深い」は別**だから ——")
    print("       " + pad("分離[FWHM]", 12) + pad("峰[e-]", 10) + pad("谷[e-]", 10)
          + pad("落差", 10) + pad("落差/雑音", 12))
    for sf in (0.85, 1.0, 1.25, 1.5):
        sep = sf * fw
        dr, dc = sep * np.cos(ang) / 2, sep * np.sin(ang) / 2
        img = render((64, 64), [32 - dr, 32 + dr], [32 - dc, 32 + dc],
                     [30000.0, 30000.0], fw, seed=None)
        u = np.linspace(-sep, sep, 201)
        prof = np.array([img[int(round(32 + x * np.cos(ang))),
                             int(round(32 + x * np.sin(ang)))] for x in u])
        pk, sd = float(prof.max()), float(prof[80:121].min())
        nz = float(np.sqrt(pk + READ ** 2))
        print("       " + pad(f"{sf:.2f}", 12) + f"{pk:9.0f} {sd:9.0f} "
              f"{pk - sd:9.0f} {(pk - sd) / nz:11.1f}")
    print(f"       分離 0.85 FWHM は理論上ちょうど二峰の境目なので、整数画素で"
          f"走査すると落差は **0 e-**(谷が画素の間に隠れる)。1.00 FWHM でも"
          f"落差は雑音の 2.0 倍しかなく、5σ の局所最大では割れない。"
          f"13.7 倍になる 1.25 FWHM で初めて 100 % 割れる —— "
          f"**「谷が在る」と「谷が雑音より深い」は 1.5 倍ぶん違う**")
    print(f"   1 個と誤認したとき、返る位置は**主星ではなく光心**: 分離 "
          f"{0.75:.2f} FWHM 等光度で 主星まで {dbl[0.75][0][1]:.3f} px に対し "
          f"光心まで {dbl[0.75][0][2]:.4f} px。不等光度 4:1・分離 1.0 FWHM でも "
          f"主星まで {dbl[1.0][1][1]:.3f} px / 光心まで {dbl[1.0][1][2]:.4f} px")
    print(f"   ★ 寄る量は幾何で決まる: 光心は主星から 分離 x f2/(f1+f2)。"
          f"1:1 なら分離の 1/2、4:1 なら 1/5 —— 分離 1.0 FWHM (= {fw:.1f} px) の"
          f"4:1 で {fw * 0.2:.2f} px = {PLATE_ARCSEC_PX * fw * 0.2:.2f} 秒角の"
          f"**偏り**。星表に「二重星」と書いていなければ、この量が"
          f"そのままプレート解の系統誤差になる")
    assert dbl[0.5][0][0] == 0.0 and dbl[3.0][0][0] == 1.0
    assert dbl[0.75][0][2] < 0.3 * dbl[0.75][0][1]     # 主星より光心に近い
    assert thr_un > thr_eq
    timing["4 二重星"] = time.perf_counter() - t0

    print("\nPASS(執筆中)")
    return True


if __name__ == "__main__":
    main()
