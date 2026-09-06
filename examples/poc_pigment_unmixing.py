# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PLACEHOLDER — 実測後に差し替える。"""
from __future__ import annotations

import time
import unicodedata

import numpy as np

import fullseye as fs

# --------------------------------------------------------------------------- #
# 0. 表示の道具                                                                 #
# --------------------------------------------------------------------------- #
WL = np.arange(400.0, 1001.0, 5.0)          # 分光格子 (121,) [nm]
VIS = WL <= 700.0                            # 可視の範囲
NIR_LO, NIR_HI = 780.0, 1000.0

H, W = 80, 120
SEED = 20260906


def _dw(s):
    """全角を 2 桁と数えた表示幅(str.format は文字数で数えるので自前で持つ)。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in str(s))


def _pad(s, n, right=False):
    s = str(s)
    fill = " " * max(0, n - _dw(s))
    return (fill + s) if right else (s + fill)


def _table(header, rows, widths=None, aligns=None):
    cols = len(header)
    widths = widths or [max(_dw(header[i]), *(_dw(r[i]) for r in rows)) if rows
                        else _dw(header[i]) for i in range(cols)]
    aligns = aligns or ([False] + [True] * (cols - 1))
    line = "  ".join("-" * w for w in widths)
    print(line)
    print("  ".join(_pad(header[i], widths[i], aligns[i]) for i in range(cols)))
    print(line)
    for r in rows:
        print("  ".join(_pad(r[i], widths[i], aligns[i]) for i in range(cols)))
    print(line)


def _sig(x, x0, k):
    return 1.0 / (1.0 + np.exp(-(np.asarray(x, float) - x0) / k))


def _gauss(x, mu, s):
    return np.exp(-0.5 * ((np.asarray(x, float) - mu) / s) ** 2)


# --------------------------------------------------------------------------- #
# 1. 顔料 —— 分光反射率(masstone)と散乱能                                       #
# --------------------------------------------------------------------------- #
# ここに置く曲線は **文献の実測値ではない**。既知の定性的な振る舞い
#   * 炭素は 400–1000 nm の全域で暗い(だから近赤外で下絵が残る)
#   * 銅系の青は近赤外でも吸収が残る(だから近赤外で下が見えにくい)
#   * 群青(ラピスラズリ系)は近赤外で明るく、層が透ける
#   * 朱(硫化水銀)は 590 nm 付近で立ち上がる階段状
#   * 有機レーキは褪色すると吸収 K が落ちて淡くなる
# を模した解析曲線である。**絶対値の一致は主張しない**。実測の分光反射率
# データベースに差し替えるときは PIGMENTS の "R" を置き換えるだけでよい。


def _pigment_table():
    lw = 0.90 - 0.25 * (1.0 - _sig(WL, 425.0, 15.0))            # 鉛白
    ch = 0.87 - 0.12 * (1.0 - _sig(WL, 415.0, 12.0))            # 白亜(地塗り)
    cb = 0.045 + 0.010 * (WL - 400.0) / 600.0                   # 炭素黒(下絵)
    az = 0.045 + 0.500 * _gauss(WL, 468.0, 42.0) + 0.10 * _gauss(WL, 760.0, 90.0)
    ul = 0.050 + 0.420 * _gauss(WL, 455.0, 48.0) + 0.720 * _sig(WL, 780.0, 55.0)
    vm = 0.045 + 0.750 * _sig(WL, 592.0, 9.0)                   # 朱
    md = 0.100 + 0.700 * _sig(WL, 610.0, 22.0) - 0.050 * _gauss(WL, 520.0, 30.0)
    return {
        # 名前:            (masstone R∞, 散乱能 S550, 表示名)
        "lead_white":  (lw, 12.0, "鉛白"),
        "chalk":       (ch, 10.0, "白亜(地)"),
        "carbon":      (cb, 1.20, "炭素黒(下絵)"),
        "azurite":     (az, 4.00, "アズライト"),
        "ultramarine": (ul, 3.00, "群青"),
        "vermilion":   (vm, 6.00, "朱"),
        "madder":      (md, 0.60, "茜レーキ"),
    }


PIGMENTS = _pigment_table()
#: 上層に使う 5 種(地と下絵は層ではないので別扱い)。この順が端成分行列の行順。
LAYER_KEYS = ("lead_white", "azurite", "ultramarine", "vermilion", "madder")
#: 波長による散乱能の減衰指数。S(λ) = S550 * (550/λ)^SCAT_P。
#: 近赤外で層が透けるのは K が落ちるからだけではなく **散乱が落ちるから**でもある。
SCAT_P = 1.5


def ks_ratio(r_inf):
    """masstone R∞ から Kubelka–Munk の K/S を出す(Kubelka 1948)。"""
    r = np.clip(np.asarray(r_inf, float), 1e-4, 1.0 - 1e-6)
    return (1.0 - r) ** 2 / (2.0 * r)


def scat(s550):
    """散乱能の波長依存 S(λ)。短波長ほど強く散る(だから近赤外が透ける)。"""
    return s550 * (550.0 / WL) ** SCAT_P


def km_layer(k_mix, s_mix, thickness, r_ground):
    """厚み有限の Kubelka–Munk 層を下地の上に載せた反射率。

    a = 1 + K/S, b = sqrt(a^2 - 1), t = S * X として

        R = (1 - Rg * (a - b * coth(b t))) / (a - Rg + b * coth(b t))

    t -> 0 で Rg、t -> inf で R∞ = a - b に落ちることは main() で数値確認する。
    """
    a = 1.0 + k_mix / s_mix
    b = np.sqrt(np.maximum(a * a - 1.0, 1e-18))
    bt = np.clip(b * s_mix * thickness, 1e-9, 60.0)
    coth = 1.0 / np.tanh(bt)
    num = 1.0 - r_ground * (a - b * coth)
    den = a - r_ground + b * coth
    return np.clip(num / den, 0.0, 1.0)


# --------------------------------------------------------------------------- #
# 2. 場面 —— 下絵の線・地塗り・上層・剥落                                        #
# --------------------------------------------------------------------------- #
def _stroke(cov, p0, p1, width):
    """線分を被覆率 alpha として焼き込む(端をなだらかにして中間の alpha を作る)。"""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    (y0, x0), (y1, x1) = p0, p1
    dy, dx = y1 - y0, x1 - x0
    ll = dy * dy + dx * dx
    t = np.clip(((yy - y0) * dy + (xx - x0) * dx) / max(ll, 1e-9), 0.0, 1.0)
    d = np.hypot(yy - (y0 + t * dy), xx - (x0 + t * dx))
    np.maximum(cov, np.clip(1.0 - (d - width * 0.5) / 0.9, 0.0, 1.0), out=cov)


def _arc(cov, cy, cx, rad, width, a0, a1):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    ang = np.arctan2(yy - cy, xx - cx)
    inside = (ang >= a0) & (ang <= a1)
    d = np.abs(np.hypot(yy - cy, xx - cx) - rad)
    v = np.where(inside, np.clip(1.0 - (d - width * 0.5) / 0.9, 0.0, 1.0), 0.0)
    np.maximum(cov, v, out=cov)


def build_scene():
    """真値一式を作る。乱数は雑音にしか使わない(構造は決定的)。

    戻り値の dict:
      ``ink``      (H,W) 下絵の被覆率 alpha。0 = 線なし。
      ``conc``     (H,W,5) 上層の顔料濃度(画素ごとに和 1)。
      ``thick``    (H,W) 上層の厚み X(剥落部は 0)。
      ``flake``    (H,W) bool 剥落。
      ``field``    (H,W) int 0=群青の面 / 1=アズライトの面 / 2=朱+茜の面。
    """
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)

    # --- 下絵(線で描く)。太さと濃さを変えて中間の alpha を必ず作る -------------
    ink = np.zeros((H, W))
    _stroke(ink, (8, 14), (72, 30), 1.6)        # 長い斜線
    _stroke(ink, (10, 46), (70, 46), 1.2)       # 縦線(細い)
    _stroke(ink, (16, 34), (16, 108), 1.0)      # 上の横線(いちばん細い)
    _stroke(ink, (64, 20), (64, 112), 1.4)      # 下の横線
    _stroke(ink, (20, 100), (66, 74), 1.8)      # 太い斜線
    _stroke(ink, (24, 62), (52, 90), 1.1)
    _arc(ink, 40.0, 60.0, 22.0, 1.5, -2.4, 0.9)  # 弧
    _arc(ink, 30.0, 92.0, 12.0, 1.2, -3.2, 3.2)  # 小円
    ink *= 0.55 + 0.45 * _sig(xx, 40.0, 26.0)   # 左ほど薄い(筆圧のむら)
    ink = np.clip(ink, 0.0, 1.0)

    # --- 上層の面(3 つの区画)。境界は縦の帯で、面の中は筆致で厚みが揺れる -------
    field = np.zeros((H, W), int)
    field[:, 40:80] = 1
    field[:, 80:] = 2

    conc = np.zeros((H, W, len(LAYER_KEYS)))
    idx = {k: i for i, k in enumerate(LAYER_KEYS)}
    #  区画 0: 群青 + 鉛白 / 区画 1: アズライト + 鉛白 / 区画 2: 朱 + 茜 + 鉛白
    mix_lo = 0.30 + 0.25 * _gauss(yy, 40.0, 26.0)        # 白の混ぜ量が面内で変わる
    f0, f1, f2 = field == 0, field == 1, field == 2
    conc[..., idx["ultramarine"]] = np.where(f0, 1.0 - mix_lo, 0.0)
    conc[..., idx["azurite"]] = np.where(f1, 1.0 - mix_lo, 0.0)
    conc[..., idx["vermilion"]] = np.where(f2, 0.62 * (1.0 - mix_lo), 0.0)
    conc[..., idx["madder"]] = np.where(f2, 0.38 * (1.0 - mix_lo), 0.0)
    conc[..., idx["lead_white"]] = mix_lo
    conc /= conc.sum(axis=2, keepdims=True)

    # --- 厚み。筆致(斜めの縞)+ 端に向かって薄くなる -------------------------
    thick = (1.0
             + 0.35 * np.sin((xx * 0.9 + yy * 0.5) * 0.25)
             + 0.22 * np.cos(yy * 0.18))
    thick *= 0.55 + 0.45 * _sig(np.minimum(np.minimum(xx, W - 1 - xx),
                                           np.minimum(yy, H - 1 - yy)), 5.0, 3.0)
    thick = np.clip(thick, 0.10, None)

    # --- 剥落(上層が失われて地と下絵が露出する) ------------------------------
    flake = np.zeros((H, W), bool)
    for (cy, cx, ry, rx) in ((22, 22, 6, 9), (58, 55, 7, 6),
                             (34, 96, 5, 11), (68, 100, 4, 5)):
        flake |= (((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2) <= 1.0
    thick = np.where(flake, 0.0, thick)
    return {"ink": ink, "conc": conc, "thick": thick, "flake": flake, "field": field}


def render_spectra(scene, tau=1.0, fade=1.0, swap=None, extra_conc=None):
    """場面 -> 画素ごとの分光反射率 (H,W,121)。

    tau    上層の厚みの全体倍率(不透明度のノブ)。
    fade   茜レーキの吸収 K に掛ける倍率。1 = 未褪色、0 に近いほど褪せる。
    swap   ("azurite", R∞配列) の形で 1 種の masstone を差し替える(似た 2 つの青の実験)。
    """
    ks = {}
    ss = {}
    for k, (r_inf, s550, _n) in PIGMENTS.items():
        r = r_inf if (swap is None or swap[0] != k) else swap[1]
        ss[k] = scat(s550)
        ks[k] = ss[k] * ks_ratio(r)
    ks["madder"] = ks["madder"] * float(fade)

    # 下地 = 白亜 + 炭素の線(面積被覆の線形混合)
    ink = scene["ink"][..., None]
    r_ground = (1.0 - ink) * PIGMENTS["chalk"][0] + ink * PIGMENTS["carbon"][0]

    conc = scene["conc"] if extra_conc is None else extra_conc
    k_mix = np.zeros((H, W, WL.size))
    s_mix = np.zeros((H, W, WL.size))
    for i, key in enumerate(LAYER_KEYS):
        c = conc[..., i:i + 1]
        k_mix += c * ks[key][None, None, :]
        s_mix += c * ss[key][None, None, :]
    s_mix = np.maximum(s_mix, 1e-6)

    thick = (scene["thick"] * float(tau))[..., None]
    out = km_layer(k_mix, s_mix, thick, r_ground)
    # 剥落部は層が無いので下地そのもの(km_layer は t->0 でそうなるが明示する)
    out = np.where(scene["flake"][..., None], r_ground, out)
    return out


def endmember_spectra(fade=1.0, swap=None):
    """上層 5 種 + 地 + 下絵の masstone を並べた (7, 121)。線形アンミキシングの端成分。

    ここでは **観測できる面の反射率** に相当する量として masstone R∞ を使う。
    fade を効かせた茜レーキは K を落として R∞ を計算し直す。
    """
    rows = []
    for key in LAYER_KEYS + ("chalk", "carbon"):
        r_inf = PIGMENTS[key][0] if (swap is None or swap[0] != key) else swap[1]
        if key == "madder" and fade != 1.0:
            ksr = ks_ratio(r_inf) * float(fade)
            r_inf = 1.0 + ksr - np.sqrt(ksr * ksr + 2.0 * ksr)
        rows.append(r_inf)
    return np.asarray(rows, float)


ENDMEMBER_NAMES = tuple(PIGMENTS[k][2] for k in LAYER_KEYS) + ("白亜(地)", "炭素黒(下絵)")
CARBON_ROW = len(LAYER_KEYS) + 1


# --------------------------------------------------------------------------- #
# 3. カメラ —— バンド化と雑音                                                    #
# --------------------------------------------------------------------------- #
def band_filters(n_bands, lo=400.0, hi=1000.0):
    """ガウス帯域のフィルタ行列 (n_bands, 121)。各行の和は 1。"""
    edge = (hi - lo) / (2.0 * n_bands)
    centers = np.linspace(lo + edge, hi - edge, n_bands)
    sigma = max((hi - lo) / n_bands, 1.0) / 2.355
    f = np.exp(-0.5 * ((WL[None, :] - centers[:, None]) / sigma) ** 2)
    f /= f.sum(axis=1, keepdims=True)
    return centers, f


#: 光量一定モデルの基準。B バンドに割ると 1 バンドあたりの光子は 1/B なので
#: 反射率換算の雑音は sqrt(B) で増える。SIGMA0 * sqrt(B) が既定。
SIGMA0 = 0.0010


def make_cube(spectra, n_bands, rng, lo=400.0, hi=1000.0, sigma=None, fixed_sigma=False):
    """分光 -> (H,W,B) のキューブ。sigma=None なら光量一定モデル。"""
    centers, f = band_filters(n_bands, lo, hi)
    cube = spectra @ f.T
    if sigma is None:
        sigma = SIGMA0 if fixed_sigma else SIGMA0 * np.sqrt(n_bands)
    if sigma > 0:
        cube = cube + rng.normal(0.0, sigma, cube.shape)
    return centers, cube


def make_rgb(spectra, rng, sigma=None):
    """分光 -> sRGB 画像 (H,W,3)。可視 400–700 nm だけを使う。"""
    lin = fs.spectrum_to_srgb(WL[VIS], spectra[..., VIS])
    if sigma is None:
        sigma = SIGMA0 * np.sqrt(3.0)
    if sigma > 0:
        lin = lin + rng.normal(0.0, sigma, lin.shape)
    return fs.linear_to_srgb(np.clip(lin, 0.0, 1.0))


# --------------------------------------------------------------------------- #
# 4. 検出器 —— 4 手法 + 追加 2 手法                                              #
# --------------------------------------------------------------------------- #
def own_pca(x, n=3):
    """自前の主成分分析。**fullseye の spec_pca は B=3 を拒否する**(色画像と
    分光キューブの型境界。設計として妥当で、既報)。しかしゼロ点はまさに
    「RGB の主成分分析」なので、ここだけは自前で持たざるを得ない。
    """
    a = np.asarray(x, float)
    hh, ww, bb = a.shape
    flat = a.reshape(-1, bb)
    mean = flat.mean(axis=0)
    xc = flat - mean
    cov = (xc.T @ xc) / max(flat.shape[0] - 1, 1)
    ev, evec = np.linalg.eigh(cov)
    order = np.argsort(ev)[::-1]
    comps = evec[:, order[:n]].T
    return (xc @ comps.T).reshape(hh, ww, n), comps, ev[order[:n]] / max(ev.sum(), 1e-30)


def best_pc_detector(scores, pos, neg, first=1):
    """PC1 以外の各成分を +/- 両符号で試し、**真値を見て AUC 最大**を返す。

    これは検出器に下駄を履かせている(実運用では符号も成分も選べない)。
    ゼロ点である RGB PCA を不当に弱く見せないため、全 PCA 系に同じ下駄を履かせる。
    """
    best, best_auc = None, -1.0
    for j in range(first, scores.shape[2]):
        for sgn in (1.0, -1.0):
            d = sgn * scores[..., j]
            a = auc(d[pos], d[neg])
            if a > best_auc:
                best, best_auc = d, a
    return best, best_auc


def nir_difference(centers, cube):
    """近赤外の単純差分。可視の赤帯 - 近赤外帯。炭素は近赤外でも暗いので正に振れる。"""
    vis = (centers >= 600.0) & (centers <= 700.0)
    nir = (centers >= NIR_LO) & (centers <= NIR_HI)
    if not vis.any() or not nir.any():
        return None
    return cube[..., vis].mean(axis=2) - cube[..., nir].mean(axis=2)


def unmix_carbon(cube, endm_bands, constrained=True):
    """線形アンミキシングの炭素黒の存在量マップ。"""
    return fs.spec_unmix(cube, endm_bands, constrained=constrained)


def ks_transform(cube):
    """反射率 -> K/S。単一定数 Kubelka–Munk では **K/S が線形に混ざる**ので、
    反射率のまま混ぜる線形アンミキシングより素直になるはず、という仮説の検証用。
    """
    r = np.clip(cube, 1e-3, 1.0)
    return (1.0 - r) ** 2 / (2.0 * r)


# --------------------------------------------------------------------------- #
# 5. 評価 —— ROC / 適合率・再現率 / 偏りと散らばり                                #
# --------------------------------------------------------------------------- #
def auc(pos, neg):
    """Mann–Whitney U による AUC(同値は 0.5 として扱う)。"""
    from scipy.stats import rankdata
    if pos.size == 0 or neg.size == 0:
        return float("nan")
    allv = np.concatenate([pos, neg])
    r = rankdata(allv)
    return float((r[:pos.size].sum() - pos.size * (pos.size + 1) / 2.0)
                 / (pos.size * neg.size))


def thresh_at_fpr(neg, fpr):
    """負例の上側 fpr 分位を閾値にする。"""
    return float(np.quantile(neg, 1.0 - fpr))


def pr_at(det, pos_mask, neg_mask, thr):
    """閾値 thr での再現率と適合率(適合率は pos/neg の 2 群だけで数える)。"""
    tp = int(((det >= thr) & pos_mask).sum())
    fp = int(((det >= thr) & neg_mask).sum())
    npos = int(pos_mask.sum())
    rec = tp / npos if npos else float("nan")
    prec = tp / (tp + fp) if (tp + fp) else float("nan")
    return rec, prec


def bias_scatter(err):
    """偏り(平均誤差)と散らばり(標準偏差)を分ける。"""
    return float(np.mean(err)), float(np.std(err))


def delta_e(rgb_a, rgb_b):
    return fs.delta_e_map(np.clip(rgb_a, 0.0, 1.0), np.clip(rgb_b, 0.0, 1.0))


def main():
    t_all = time.perf_counter()
    print("PLACEHOLDER")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
