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


def sharpness(img, r, c, bkg=None):
    """中心画素 / 3x3 の和。1 画素スパイクは 1.0、点源は PSF で決まる値。"""
    i, j = int(round(r)), int(round(c))
    blk = img[i - 1:i + 2, j - 1:j + 2] - (np.median(img) if bkg is None else bkg)
    return float(blk[1, 1] / max(blk.sum(), 1e-9))


def build_field(seed=11, fwhm=3.2):
    """構造のある星野の**真値**。一様 + 密集星団 + 二重星 + 飽和星 + 宇宙線。

    乱数だけの星野は「どの手法でも同じくらい上手くいく」ので、失敗が
    見えない。近接・飽和・偽の点源を混ぜて初めて、測位の弱点が出る。
    座標は画素で設計してから :func:`plate_inverse` → :func:`standard_to_sky`
    で天球へ戻す(段 0 で往復が倍精度の丸めまで一致することを確かめてある
    ので、画素で設計しても天球で設計しても同じもの)。
    """
    rg = np.random.default_rng(seed)
    row, col, flux, kind = [], [], [], []

    def add(r, c, f, k):
        row.append(r), col.append(c), flux.append(f), kind.append(k)

    for _ in range(24):                                # 0 = 一様
        add(rg.uniform(18, SHAPE[0] - 18), rg.uniform(18, SHAPE[1] - 18),
            10 ** rg.uniform(np.log10(2000.0), np.log10(60000.0)), 0)
    for _ in range(10):                                # 1 = 密集星団
        add(68.0 + rg.normal(0, 5.0), 182.0 + rg.normal(0, 5.0),
            10 ** rg.uniform(np.log10(1500.0), np.log10(20000.0)), 1)
    for i, sf in enumerate((1.0, 1.8, 3.0)):           # 2 = 二重星
        r0, c0 = 190.0 + 20.0 * i, 60.0 + 15.0 * i
        d = sf * fwhm / 2.0
        add(r0 - d * 0.8, c0 - d * 0.6, 40000.0, 2)
        add(r0 + d * 0.8, c0 + d * 0.6, 10000.0, 2)
    add(45.0, 45.0, 2.0e6, 3)                          # 3 = 飽和星
    add(140.0, 210.0, 8.0e5, 3)
    cat = {"row": np.array(row), "col": np.array(col),
           "flux": np.array(flux), "kind": np.array(kind)}
    xi, eta = plate_inverse(cat["row"], cat["col"])
    cat["ra"], cat["dec"] = standard_to_sky(xi, eta)
    crs = [(int(rg.integers(14, SHAPE[0] - 14)), int(rg.integers(14, SHAPE[1] - 14)),
            float(rg.uniform(2000.0, 20000.0))) for _ in range(25)]
    return cat, crs


def plate_from_matrix(mat):
    """相似変換行列 → ``(スケール[秒角/px], 回転[度], (原点 row, 原点 col))``。"""
    s = np.hypot(mat[0, 0], mat[0, 1])
    return (1.0 / s, float(np.degrees(np.arctan2(mat[1, 0], mat[0, 0]))),
            (float(mat[0, 2]), float(mat[1, 2])))


def apply_matrix(mat, src):
    """``(N, 2)`` に 3x3 の相似変換を適用する(``fit_transform`` の規約)。"""
    src = np.asarray(src, float)
    h = np.concatenate([src, np.ones((len(src), 1))], axis=1)
    return (mat @ h.T)[:2].T


def rms_of(src, dst, mat=None):
    """当てはめ後の残差 RMS [px]。*mat* を省くとその場で当てはめる。"""
    if mat is None:
        mat = FT.vector_to_similarity(src, dst)
    d = apply_matrix(mat, src) - np.asarray(dst, float)
    return float(np.sqrt((d ** 2).sum(axis=1).mean()))


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

    # --------------------------------------------------------------- #
    # 5) 宇宙線 —— 1 画素の鋭いスパイクを星と誤認する率                  #
    # --------------------------------------------------------------- #
    t0 = time.perf_counter()
    print("\n【5】宇宙線 —— 1 画素の鋭いスパイクを星と誤認する率")
    cr_bins = ((20.0, 60.0), (60.0, 150.0), (300.0, 1000.0),
               (3000.0, 10000.0), (10000.0, 30000.0))
    print(f"   星 30 個(flux 800〜80000 e-)の視野に、1 画素スパイクを "
          f"{len(cr_bins)} 段の強さ x 20 発ずつ置く。5 実現。"
          f"``star_detect`` の出力を、真の星 / 宇宙線 / どちらでもない、に分ける")
    print("     " + pad("宇宙線 [e-]", 16) + pad("置いた数", 10)
          + pad("星と誤認", 10) + pad("誤認率", 10) + pad("鋭さで除去後", 14)
          + pad("巻き添えの星", 14))
    cr_res = {}
    for lo, hi in cr_bins:
        n_put = n_fp = n_fp2 = n_lost = n_star = 0
        survivor_d = []
        for k in range(5):
            rg = np.random.default_rng(4000 + k)
            sr = rg.uniform(16, SHAPE[0] - 16, 30)
            sc = rg.uniform(16, SHAPE[1] - 16, 30)
            sf = 10 ** rg.uniform(np.log10(800.0), np.log10(80000.0), 30)
            crr = rg.integers(16, SHAPE[0] - 16, 20)
            crc = rg.integers(16, SHAPE[1] - 16, 20)
            cra = rg.uniform(lo, hi, 20)
            # 星の近く(3 px 以内)に落ちた宇宙線は「誤認」の勘定から外す
            keep = np.array([np.hypot(sr - r, sc - c).min() > 3.0
                             for r, c in zip(crr, crc)])
            extra = [(r, c, a) for r, c, a, k2 in zip(crr, crc, cra, keep) if k2]
            img = render(SHAPE, sr, sc, sf, 3.2, seed=5000 + k, extra=extra)
            kp = A.star_detect(img, threshold_sigma=5.0, min_separation=3,
                               max_stars=300)
            n_put += len(extra)
            is_cr, is_star = [], []
            for r, c in kp:
                d_star = np.hypot(sr - r, sc - c).min()
                d_cr = (min(np.hypot(e[0] - r, e[1] - c) for e in extra)
                        if extra else np.inf)
                is_star.append(d_star < 2.0)
                is_cr.append(d_cr < 2.0 and d_star >= 2.0)
            is_cr, is_star = np.array(is_cr), np.array(is_star)
            n_fp += int(is_cr.sum())
            n_star += int(is_star.sum())
            # 鋭さ = 中心画素 / 3x3 の和。点源より鋭ければ宇宙線と判定する。
            if len(kp):
                sharp = []
                for r, c in kp:
                    i, j = int(round(r)), int(round(c))
                    blk = img[i - 1:i + 2, j - 1:j + 2] - np.median(img)
                    sharp.append(blk[1, 1] / max(blk.sum(), 1e-9))
                sharp = np.array(sharp)
                star_sharp = float(profile((7, 7), 3.0, 3.0, 3.2)[2:5, 2:5].sum())
                star_sharp = float(profile((7, 7), 3.0, 3.0, 3.2)[3, 3]) / star_sharp
                cut = sharp > 0.5 * (star_sharp + 1.0)   # 点源と 1.0 の中間で切る
                n_fp2 += int((is_cr & ~cut).sum())
                n_lost += int((is_star & cut).sum())
                for (r, c), bad in zip(kp, is_cr & ~cut):
                    if bad:
                        d2 = sorted(np.hypot(e[0] - r, e[1] - c) for e in extra)
                        survivor_d.append((float(np.hypot(sr - r, sc - c).min()),
                                           float(d2[1]) if len(d2) > 1 else np.inf))
        cr_res[(lo, hi)] = (n_put, n_fp, n_fp / max(n_put, 1), n_fp2, n_lost,
                            n_star, survivor_d)
        print("     " + pad(f"{lo:.0f}〜{hi:.0f}", 16) + f"{n_put:8d}  "
              f"{n_fp:8d}  {n_fp / max(n_put, 1):8.1%}  {n_fp2:10d}    "
              f"{n_lost:10d}")
    worst = cr_res[(10000.0, 30000.0)]
    print(f"   → 誤認率は宇宙線の強さで決まる: 検出しきい値 5σ は "
          f"σ ≈ {np.sqrt(SKY + READ ** 2):.1f} e- なので "
          f"{5 * np.sqrt(SKY + READ ** 2):.0f} e-。それを跨ぐ 20〜60 e- で "
          f"{cr_res[(20.0, 60.0)][2]:.0%}、60〜150 e- で "
          f"{cr_res[(60.0, 150.0)][2]:.0%}、それ以上は "
          f"{cr_res[(300.0, 1000.0)][2]:.0%}〜{worst[2]:.0%} で飽和する。"
          f"★ **弱い宇宙線ほど安全なのではない** —— しきい値を超えたら"
          f"そこから先はほぼ全部が星として出てくる")
    print(f"   鋭さ(中心画素 / 3x3 の和)で切ると、誤認は "
          f"{worst[1]} → {worst[3]} 件({1 - worst[3] / max(worst[1], 1):.0%} 除去)、"
          f"巻き添えで落ちた本物の星は {worst[4]} 個 / 検出した星 {worst[5]} 個 "
          f"({worst[4] / max(worst[5], 1):.1%})。"
          f"1 画素スパイクの鋭さは 1.0、FWHM 3.2 の点源は "
          f"{float(profile((7, 7), 3.0, 3.0, 3.2)[3, 3]) / float(profile((7, 7), 3.0, 3.0, 3.2)[2:5, 2:5].sum()):.3f} "
          f"—— 分布が重ならないので**本物の星は 1 個も落ちない**")
    surv = worst[6]
    if surv:
        pair = sum(1 for _, d2 in surv if d2 < 2.5)
        print(f"   残った {worst[3]} 件の内訳を数えた: **{pair} 件は"
              f"宇宙線が 2 発 {min(d2 for _, d2 in surv):.1f}〜"
              f"{max(d2 for _, d2 in surv if d2 < 2.5):.1f} px 隣に落ちた組**で、"
              f"``star_detect`` が返す 7x7 窓の**重心**が 2 発の中間に来る。"
              f"そこの中心画素は空なので鋭さが {0.0:.1f} に落ちる。"
              f"残り {worst[3] - pair} 件は星まで "
              f"{min(d1 for d1, d2 in surv if d2 >= 2.5):.1f} px の宇宙線で、"
              f"星の翼が窓に入って重心がずれた。"
              f"★ どちらも原因は同じ —— **鋭さを測る場所が、検出器が返した"
              f"重心であって峰ではない**。峰の画素を一緒に返す op なら起きない")
    print(f"   ★ ``star_detect`` は鋭さも真円度も返さない(返るのは "
          f"``(N, 2)`` の座標だけ)ので、この選別は利用者が書くしかない。"
          f"``cosmic_ray_reject`` は**画像を直す** op であって"
          f"「この検出は宇宙線か」を答える op ではない")
    assert worst[2] > 0.8                              # 強い宇宙線はほぼ全部拾う
    assert worst[3] < 0.1 * worst[1] and worst[4] == 0   # 9 割方切れる/星は無傷
    timing["5 宇宙線"] = time.perf_counter() - t0

    # --------------------------------------------------------------- #
    # 6) 構造のある星野 —— 検出 → 測位 → プレートソルブ                  #
    # --------------------------------------------------------------- #
    t0 = time.perf_counter()
    cat, crs = build_field(11)
    img = render(SHAPE, cat["row"], cat["col"], cat["flux"], 3.2, seed=9001,
                 full_well=FULL_WELL, extra=crs)
    print(f"\n【6】構造のある星野 —— 一様 {int((cat['kind'] == 0).sum())} / "
          f"星団 {int((cat['kind'] == 1).sum())} / "
          f"二重星 {int((cat['kind'] == 2).sum())} 個(3 組)/ "
          f"飽和 {int((cat['kind'] == 3).sum())} 個、宇宙線 {len(crs)} 発。"
          f"乱数の一様分布だけでは出ない失敗を入れるための配置")
    print(f"   星表は**天球座標で渡す**(画素座標は渡さない)。推定側が知って"
          f"いいのは画像と ``(RA, Dec)`` だけで、スケールも回転も原点も知らない")

    kp = A.star_detect(img, threshold_sigma=5.0, min_separation=3, max_stars=300)
    sharp = np.array([sharpness(img, r, c) for r, c in kp])
    star_sharp = float(profile((7, 7), 3.0, 3.0, 3.2)[3, 3]
                       / profile((7, 7), 3.0, 3.0, 3.2)[2:5, 2:5].sum())
    kp = kp[sharp < 0.5 * (star_sharp + 1.0)]          # 段 5 の鋭さ切り
    meas = m_centroid_bg(img, kp, box=11)
    print(f"   ``star_detect`` {len(sharp)} 検出 → 鋭さ切りで {len(kp)} —— "
          f"真の星 {len(cat['row'])} 個に対して "
          f"{len(kp) - len(cat['row']):+d}(二重星の未分離と、"
          f"星団の混み合いで数が合わない)")

    # 真値との対応は**採点にだけ**使う(推定には渡さない)
    d = np.hypot(meas[:, None, 0] - cat["row"][None, :],
                 meas[:, None, 1] - cat["col"][None, :])
    j = np.argmin(d, axis=1)
    dmin = d[np.arange(len(meas)), j]
    ok = dmin < 2.0
    print(f"   採点用の突き合わせ(2 px 以内): {int(ok.sum())} / {len(meas)} 一致")

    # --- 6a) 対応が既知のとき、何個の星でプレート定数が決まるか ---------- #
    clean = ok & (cat["kind"][j] == 0)                 # 一様配置の孤立星だけ
    ci = j[clean]
    xi_c, eta_c = sky_to_standard(cat["ra"][ci], cat["dec"][ci])
    src_all = np.stack([eta_c, xi_c], axis=1)
    dst_all = meas[clean]
    n_clean = len(ci)
    print(f"\n   6a) **対応が既知**のとき、星を何個使えばプレート定数が決まるか"
          f"(孤立星 {n_clean} 個から k 個を無作為に選ぶ x 200 回)")
    print("       " + pad("k", 5) + pad("スケール誤差[ppm]", 22)
          + pad("回転誤差[秒角]", 20) + pad("原点誤差[px]", 18)
          + pad("残りの星での予測[秒角]", 24))
    print("       " + pad("", 5) + pad("中央     95 %", 22)
          + pad("中央     95 %", 20) + pad("中央     95 %", 18)
          + pad("中央     95 %", 24))
    solve_tab = {}
    for k in (2, 3, 4, 6, 10, 20, n_clean):
        if k > n_clean:
            continue
        es, er, eo, ep = [], [], [], []
        rg = np.random.default_rng(6000 + k)
        for _ in range(200 if k < n_clean else 1):
            sel = rg.choice(n_clean, size=k, replace=False) if k < n_clean \
                else np.arange(n_clean)
            M = FT.vector_to_similarity(src_all[sel], dst_all[sel])
            s_est, rot_est, org = plate_from_matrix(M)
            es.append(abs(s_est - PLATE_ARCSEC_PX) / PLATE_ARCSEC_PX * 1e6)
            er.append(abs(rot_est - PLATE_ROT_DEG) * 3600.0)
            eo.append(np.hypot(org[0] - CRPIX_ROW, org[1] - CRPIX_COL))
            rest = np.setdiff1d(np.arange(n_clean), sel)
            if len(rest):
                pr = apply_matrix(M, src_all[rest])
                ep.append(np.median(np.hypot(*(pr - dst_all[rest]).T))
                          * PLATE_ARCSEC_PX)
        solve_tab[k] = (np.median(es), np.percentile(es, 95),
                        np.median(er), np.percentile(er, 95),
                        np.median(eo), np.percentile(eo, 95),
                        np.median(ep) if ep else np.nan,
                        np.percentile(ep, 95) if ep else np.nan)
        v = solve_tab[k]
        print("       " + pad(f"{k}", 5)
              + f"{v[0]:9.1f}{v[1]:11.1f}   " + f"{v[2]:8.2f}{v[3]:10.2f}  "
              + f"{v[4]:8.3f}{v[5]:9.3f}   " + f"{v[6]:9.4f}{v[7]:11.4f}")
    print(f"       → k=2 でも**解は必ず出る**(相似変換は 4 自由度、"
          f"2 対応 = 4 式でちょうど決まる)。しかし予測誤差の 95 % 点は "
          f"{solve_tab[2][7]:.3f} 秒角 = {solve_tab[2][7] / PLATE_ARCSEC_PX:.2f} px。"
          f"k を増やすと {solve_tab[4][7]:.4f}(k=4)→ {solve_tab[10][7]:.4f}"
          f"(k=10)秒角 と落ちる。**解が出ることと解が正しいことは別**")
    lever = float(np.sqrt(((dst_all - dst_all.mean(axis=0)) ** 2).sum(axis=1).mean()))
    print(f"       ★ 単位に騙されないこと: 全 {n_clean} 個を使った解でも回転誤差は "
          f"{solve_tab[n_clean][2]:.0f} 秒角ある。桁が大きく見えるが、"
          f"腕の長さ(星の重心からの RMS 距離){lever:.1f} px を掛けると "
          f"{np.deg2rad(solve_tab[n_clean][2] / 3600.0) * lever:.4f} px —— "
          f"段 1 で測った 1 星の測位精度と同じ桁。"
          f"**角度の誤差は腕の長さを掛けて初めて意味を持つ**")
    assert solve_tab[2][7] > 3.0 * solve_tab[10][7]
    assert np.deg2rad(solve_tab[n_clean][2] / 3600.0) * lever < 0.1
    timing["6 プレート解"] = time.perf_counter() - t0

    # --- 6b) 対応が未知のとき、間違った対応が「もっともらしく」出る確率 --- #
    t0 = time.perf_counter()
    M_all = FT.vector_to_similarity(src_all, dst_all)
    resid_true = np.hypot(*(apply_matrix(M_all, src_all) - dst_all).T)
    n_hit_true = int((np.hypot(*(apply_matrix(M_all, src_all)[:, None, :]
                                 - dst_all[None, :, :]).T).min(axis=0) < 1.0).sum())
    print(f"\n   6b) **対応が未知**のとき。k 個の像に**でたらめな**星表を"
          f"割り当てて相似変換を当て、残差 RMS を見る(各 k で 4000 回)")
    print(f"       正しい対応(孤立星 {n_clean} 個)での残差は 1 星あたり "
          f"中央 {np.median(resid_true):.4f} px / 95 % 点 "
          f"{np.percentile(resid_true, 95):.4f} px / 最大 "
          f"{resid_true.max():.4f} px。**採否のしきい値はこの上に置く**")
    print("       " + pad("k", 4) + pad("自由度", 8)
          + pad("でたらめな対応の残差 RMS [px]", 34)
          + pad("しきい値別 偽採択率", 30))
    print("       " + pad("", 4) + pad("2k-4", 8)
          + pad("最小       1 % 点      中央", 34)
          + pad("< 0.5     < 1.0     < 3.0", 30))
    false_p = {}
    for k in (2, 3, 4, 5, 6):
        rg = np.random.default_rng(7000 + k)
        r = []
        for _ in range(4000):
            a = rg.choice(n_clean, size=k, replace=False)
            b = rg.choice(n_clean, size=k, replace=False)
            if np.array_equal(a, b):
                continue
            r.append(rms_of(src_all[b], dst_all[a]))
        r = np.array(r)
        false_p[k] = (float(r.min()), float(np.percentile(r, 1)),
                      float(np.median(r)), float((r < 0.5).mean()),
                      float((r < 1.0).mean()), float((r < 3.0).mean()))
        v = false_p[k]
        print("       " + pad(f"{k}", 4) + pad(f"{2 * k - 4}", 8)
              + f"{v[0]:9.2e}{v[1]:11.3f}{v[2]:11.2f}     "
              + f"{v[3]:8.2%}{v[4]:10.2%}{v[5]:10.2%}")
    print(f"       → k=2 は **でたらめでも残差が厳密に 0**"
          f"({false_p[2][0]:.1e}、{false_p[2][3]:.0%} が採択される)—— "
          f"自由度 0 なので何を当てても合う。「残差が小さいから正しい」は "
          f"k=2 では**情報が 1 ビットも無い**。"
          f"**プレート解が一意に決まるのは 3 個から**")
    print(f"       k=3 でいきなり効く: 4000 回の最小残差が "
          f"{false_p[3][0]:.2f} px、0.5 px を下回ったのは "
          f"{false_p[3][3]:.2%}。3 px まで緩めても {false_p[3][5]:.2%} —— "
          f"相似変換は 4 自由度しかないので、でたらめな 3 点が偶然そろう"
          f"余地が小さい")
    # ★ 「1 回あたり小さい」と「総当たりで小さい」は別の主張。
    n_hyp = n_clean * (n_clean - 1) * (n_clean - 2)
    rg = np.random.default_rng(9100)
    trials, hit05, hit10 = 40000, 0, 0
    for _ in range(trials):
        a = rg.choice(n_clean, size=3, replace=False)
        b = rg.choice(n_clean, size=3, replace=False)
        if np.array_equal(a, b):
            continue
        v = rms_of(src_all[b], dst_all[a])
        hit05 += v < 0.5
        hit10 += v < 1.0
    p05, p10 = hit05 / trials, hit10 / trials
    print(f"       ★ ただし **1 回の確率と総当たりの期待値を混同しない**。"
          f"k=3 の対応は {n_hyp} 通り(順列)あるので、期待偽解数 = "
          f"通り数 x 1 回の確率。{trials} 回で測ると < 0.5 px が {hit05} 件"
          f"(p = {p05:.1e})、< 1.0 px が {hit10} 件(p = {p10:.1e})→ "
          f"期待偽解数 {n_hyp * p05:.2f} 件 / {n_hyp * p10:.2f} 件。"
          f"しきい値を 0.5 から 1.0 px に緩めるだけで"
          f"**総当たりでは偽解が出る側に回る**")
    # 検算 —— 通った候補を、使わなかった星で検証する
    rg = np.random.default_rng(8080)
    n_pass, n_survive, best_hit = 0, 0, 0
    for _ in range(40000):
        a = rg.choice(n_clean, size=3, replace=False)
        b = rg.choice(n_clean, size=3, replace=False)
        if np.array_equal(a, b):
            continue
        M = FT.vector_to_similarity(src_all[b], dst_all[a])
        if rms_of(src_all[b], dst_all[a], M) >= 1.0:
            continue
        n_pass += 1
        pr = apply_matrix(M, src_all)
        hit = int((np.hypot(*(pr[:, None, :] - dst_all[None, :, :]).T)
                   .min(axis=0) < 1.0).sum())
        best_hit = max(best_hit, hit)
        n_survive += hit >= 6
    print(f"       検算 —— しきい値 1.0 px を通った偽の候補 {n_pass} 件を、"
          f"**使わなかった星も含めた全 {n_clean} 個**へ投影して数え直した: "
          f"1 px 以内に当たった星は最大 {best_hit} 個で、6 個以上"
          f"当てたのは {n_survive} 件。正しい解は {n_hit_true} 個当てる。"
          f"★ **少数で当てて多数で検証する** —— 3 個で作った解を "
          f"{n_clean} 個で数え直すだけで、偽解は 1 件も残らない")
    assert false_p[2][0] < 1e-9 and false_p[2][3] == 1.0
    assert false_p[3][3] == 0.0 and n_survive == 0 and n_hit_true == n_clean
    timing["6b 偽解"] = time.perf_counter() - t0

    # --------------------------------------------------------------- #
    # 7) 天球座標に直したときの誤差 —— 1 つの数字にまとめない            #
    # --------------------------------------------------------------- #
    t0 = time.perf_counter()
    Minv = np.linalg.inv(M_all)
    got_src = apply_matrix(Minv, meas)                 # (eta, xi) [秒角]
    ra_e, dec_e = standard_to_sky(got_src[:, 1], got_src[:, 0])
    xi_t, eta_t = sky_to_standard(cat["ra"][j], cat["dec"][j])
    d_xi, d_eta = got_src[:, 1] - xi_t, got_src[:, 0] - eta_t
    # 検算: 標準座標での差と、天球上の角距離が一致すること
    dsky = np.hypot((ra_e - cat["ra"][j]) * np.cos(np.deg2rad(dec_e)),
                    dec_e - cat["dec"][j]) * 3600.0
    print(f"\n【7】天球座標に直した誤差。プレート解は 6a の孤立星 {n_clean} 個から。"
          f"検算: 標準座標での差 と 天球上の角距離 の食い違いは最大 "
          f"{np.abs(dsky - np.hypot(d_xi, d_eta)).max():.2e} 秒角")
    assert np.abs(dsky - np.hypot(d_xi, d_eta)).max() < 1e-3
    print(f"   **平均だけを見ない**。偏り(誤差ベクトルの平均の大きさ)と"
          f"散らばり(平均まわりの RMS)を分け、中央値・95 % 点・最悪も出す。"
          f"単位は秒角(1 px = {PLATE_ARCSEC_PX} 秒角)")

    def stat(mask, name):
        n = int(mask.sum())
        if n == 0:
            return None
        bx, by = d_xi[mask].mean(), d_eta[mask].mean()
        bias = float(np.hypot(bx, by))
        sc = float(np.sqrt(((d_xi[mask] - bx) ** 2 + (d_eta[mask] - by) ** 2).mean()))
        r = np.hypot(d_xi[mask], d_eta[mask])
        return (name, n, bias, sc, float(np.median(r)),
                float(np.percentile(r, 95)), float(r.max()))

    print("       " + pad("集団", 22) + pad("N", 4) + pad("偏り", 9)
          + pad("散らばり", 11) + pad("中央", 9) + pad("95 %", 9) + pad("最悪", 9))
    kindj = cat["kind"][j]
    rad = np.hypot(meas[:, 0] - 127.5, meas[:, 1] - 127.5)
    fl = cat["flux"][j]
    uni = ok & (kindj == 0)
    q1, q2 = np.percentile(fl[uni], [33, 67])
    rq1, rq2 = np.percentile(rad[uni], [33, 67])
    rows7 = [stat(uni, "一様・孤立(全体)"),
             stat(uni & (fl <= q1), "  うち暗い 1/3"),
             stat(uni & (fl > q1) & (fl <= q2), "  うち中位 1/3"),
             stat(uni & (fl > q2), "  うち明るい 1/3"),
             stat(uni & (rad <= rq1), "  うち視野中心 1/3"),
             stat(uni & (rad > rq1) & (rad <= rq2), "  うち中間 1/3"),
             stat(uni & (rad > rq2), "  うち視野外側 1/3"),
             stat(ok & (kindj == 1), "密集星団"),
             stat(ok & (kindj == 2), "二重星"),
             stat(ok & (kindj == 3), "飽和星"),
             stat(ok, "全部まぜて 1 つの数字に")]
    for r in rows7:
        if r is None:
            continue
        print("       " + pad(r[0], 22) + f"{r[1]:3d} " + f"{r[2]:8.4f}"
              f"{r[3]:10.4f}{r[4]:10.4f}{r[5]:9.4f}{r[6]:9.4f}")
    d_uni = dict((r[0], r) for r in rows7 if r)
    all_row = d_uni["全部まぜて 1 つの数字に"]
    uni_row = d_uni["一様・孤立(全体)"]
    # ★ 「一様・孤立」の偏りが 0.0000 なのは当たり前 —— プレート解を
    #   その 24 個で当てたので、最小二乗が残差の平均を 0 にしている。
    #   使わなかった星での誤差を見るには 1 個ずつ抜いて解き直す。
    loo = []
    for i in range(n_clean):
        keep = np.setdiff1d(np.arange(n_clean), [i])
        Mi = FT.vector_to_similarity(src_all[keep], dst_all[keep])
        p = apply_matrix(np.linalg.inv(Mi), dst_all[i:i + 1])[0]
        loo.append((p[1] - src_all[i, 1], p[0] - src_all[i, 0]))
    loo = np.array(loo)
    lb = np.hypot(*loo.mean(axis=0))
    ls = float(np.sqrt(((loo - loo.mean(axis=0)) ** 2).sum(axis=1).mean()))
    lr = np.hypot(*loo.T)
    print("       " + pad("一様・孤立(1 個抜き)", 22) + f"{n_clean:3d} "
          + f"{lb:8.4f}{ls:10.4f}{np.median(lr):10.4f}"
            f"{np.percentile(lr, 95):9.4f}{lr.max():9.4f}")
    print(f"       ↑ 上の「一様・孤立(全体)」の偏り {uni_row[2]:.4f} は"
          f"**当たり前に 0**(その 24 個でプレート解を当てたので、"
          f"最小二乗が残差の平均を 0 にする)。1 個ずつ抜いて解き直すと "
          f"偏り {lb:.4f} / 中央 {np.median(lr):.4f} 秒角 —— "
          f"自分を当てはめに使った数字を「精度」と呼んではいけない")
    all_row = d_uni["全部まぜて 1 つの数字に"]
    uni_row = d_uni["一様・孤立(全体)"]
    print(f"   → **1 つの数字にまとめると嘘になる**。全部混ぜた中央値 "
          f"{all_row[4]:.4f} 秒角は、孤立星の "
          f"{uni_row[4]:.4f} 秒角と 二重星の {d_uni['二重星'][4]:.4f} 秒角の"
          f"あいだのどこでもない値。最悪は {all_row[6]:.3f} 秒角 = "
          f"中央値の {all_row[6] / all_row[4]:.0f} 倍で、"
          f"その正体は二重星と星団の混み合い")
    print(f"   明るさで割ると: 暗い 1/3 の中央 {d_uni['  うち暗い 1/3'][4]:.4f} vs "
          f"明るい 1/3 の {d_uni['  うち明るい 1/3'][4]:.4f} 秒角 —— "
          f"{d_uni['  うち暗い 1/3'][4] / max(d_uni['  うち明るい 1/3'][4], 1e-9):.1f} 倍。"
          f"段 1 の S/N 掃引がそのまま出ている")
    print(f"   位置で割ると: 中心 1/3 {d_uni['  うち視野中心 1/3'][4]:.4f} / "
          f"中間 {d_uni['  うち中間 1/3'][4]:.4f} / "
          f"外側 {d_uni['  うち視野外側 1/3'][4]:.4f} 秒角。"
          f"外側が悪ければプレートモデルの不足(高次項)を疑う場面だが、"
          f"ここでは {SHAPE[0] * PLATE_ARCSEC_PX / 60:.1f} 分角の視野なので"
          f"接平面投影の非線形は "
          f"{ARCSEC * (1 / np.cos(np.deg2rad(SHAPE[0] * PLATE_ARCSEC_PX / 3600 / 2)) - 1) * 1e3:.2f} "
          f"ミリ秒角しかなく、差は出ない")
    print(f"   偏りと散らばりを分ける意味: 二重星の集団は 偏り "
          f"{d_uni['二重星'][2]:.4f} / 散らばり {d_uni['二重星'][3]:.4f} 秒角 —— "
          f"{'偏りが主' if d_uni['二重星'][2] > d_uni['二重星'][3] else '散らばりが主'}。"
          f"孤立星は 偏り {uni_row[2]:.4f} / 散らばり {uni_row[3]:.4f} で"
          f"{'偏りが主' if uni_row[2] > uni_row[3] else '散らばりが主'}。"
          f"★ **散らばりは枚数で減るが偏りは減らない**ので、"
          f"この 2 つを足して 1 つの誤差にすると「もっと撮れば良くなる」を誤る")
    assert d_uni["  うち暗い 1/3"][4] > d_uni["  うち明るい 1/3"][4]
    assert d_uni["二重星"][4] > 5.0 * uni_row[4]
    assert all_row[6] > 10.0 * uni_row[4]
    timing["7 天球誤差"] = time.perf_counter() - t0

    # --------------------------------------------------------------- #
    # 8) 速さ(assert しない)                                          #
    # --------------------------------------------------------------- #
    print("\n【8】速さ(参考値・assert しない): " + "  ".join(
        f"{k} {v:.2f}s" for k, v in timing.items())
        + f"  合計 {sum(timing.values()):.2f}s")

    print(f"\nPASS: 測位は理論下限を上回れない(最良 "
          f"{min(bright.values()):.2f}x、重み付き当てはめで "
          f"{w_gain[100000.0][1]:.2f}x)。崖は 3 つ —— "
          f"FWHM 2 px を切る標本化不足(位相系統誤差 "
          f"{phase_tab['PSF 相関'][1.0][0]:.4f} px)、飽和 "
          f"({g[16.0]['背景引き重心'][0]:.4f} px、マスクして"
          f"**当てはめ**れば {mask_fit[16.0]:.5f} px だが"
          f"マスクして**重心**を取ると {mask_cen[16.0]:.3f} px に悪化)、"
          f"二重星({thr_eq:.2f} FWHM 未満は 1 個に見え、位置は光心へ寄る)。"
          f"宇宙線はしきい値を超えたら {worst[2]:.0%} が星として出るが、"
          f"鋭さで {1 - worst[3] / worst[1]:.0%} 落とせる。"
          f"プレート解は 2 個では**でたらめでも残差 0**、3 個から一意 —— "
          f"ただし総当たり {n_hyp} 通りでは 1 px 許容で期待偽解 "
          f"{n_hyp * p10:.1f} 件。天球誤差は集団で "
          f"{uni_row[4]:.4f}(孤立星)〜{d_uni['二重星'][4]:.3f}(二重星)秒角と "
          f"{d_uni['二重星'][4] / uni_row[4]:.0f} 倍違い、"
          f"1 つの数字にまとめてはいけない")
    return True


if __name__ == "__main__":
    main()
