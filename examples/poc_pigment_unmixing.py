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
    # 区画 2 はさらに 2 つに割る: 朱の面と、褪色する茜レーキの面。
    # 混ぜてしまうと朱の吸収が茜を覆い隠して「褪色しても何も起きない」になる
    # (最初の版がまさにそれで、f を 1 -> 0.15 に振っても ΔE00 が 0.20 -> 0.43 しか
    #  動かなかった。褪色の実験になっていなかった)。
    field = np.zeros((H, W), int)
    field[:, 40:80] = 1
    field[:, 80:] = 2
    lake = np.zeros((H, W), bool)
    lake[:, 100:] = True                                  # 区画 2 の右半分 = 茜レーキ

    conc = np.zeros((H, W, len(LAYER_KEYS)))
    idx = {k: i for i, k in enumerate(LAYER_KEYS)}
    #  区画 0: 群青 + 鉛白 / 区画 1: アズライト + 鉛白 / 区画 2: 朱 + 鉛白 と 茜 + 鉛白
    mix_lo = 0.30 + 0.25 * _gauss(yy, 40.0, 26.0)        # 白の混ぜ量が面内で変わる
    mix_lo = np.where(lake, 0.35 * mix_lo, mix_lo)       # レーキの面は白が少ない
    f0, f1, f2 = field == 0, field == 1, field == 2
    conc[..., idx["ultramarine"]] = np.where(f0, 1.0 - mix_lo, 0.0)
    conc[..., idx["azurite"]] = np.where(f1, 1.0 - mix_lo, 0.0)
    conc[..., idx["vermilion"]] = np.where(f2 & ~lake, 1.0 - mix_lo, 0.0)
    conc[..., idx["madder"]] = np.where(lake, 1.0 - mix_lo, 0.0)
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
    return {"ink": ink, "conc": conc, "thick": thick, "flake": flake,
            "field": field, "lake": lake}


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
    n = min(int(n), bb)
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
    """偽陽性率が fpr **以下**になる中でいちばん緩い閾値を返す(判定は ``> thr``)。

    分位点をそのまま閾値にして ``>=`` で数えると、**同値が大量にある検出器**
    (アンミキシングの存在量は負例のほとんどが厳密に 0)で偽陽性率が跳ね上がる。
    実際この PoC の最初の版では線形アンミキシングが「再現率 1.000 / 適合率 0.095」
    という、動作点が存在しないだけの数字を出した。到達できない動作点は
    「到達できなかった」と書けるようにする。
    """
    s = np.sort(np.asarray(neg, float))[::-1]
    k = int(np.floor(fpr * s.size))
    if k <= 0:
        return float(s[0])                     # 負例の最大値。これを超えた分だけ拾う
    if k >= s.size:
        return -np.inf
    return float(s[k])


def pr_at(det, pos_mask, neg_mask, thr):
    """閾値 thr での (再現率, 適合率, 実際の偽陽性率)。判定は厳密に ``> thr``。"""
    hit = det > thr
    tp = int((hit & pos_mask).sum())
    fp = int((hit & neg_mask).sum())
    npos, nneg = int(pos_mask.sum()), int(neg_mask.sum())
    rec = tp / npos if npos else float("nan")
    prec = tp / (tp + fp) if (tp + fp) else float("nan")
    return rec, prec, (fp / nneg if nneg else float("nan"))


def recall_at(det, pos_mask, neg_mask, fpr):
    """その領域だけで閾値を引き直したときの再現率(領域ごとの素の感度)。"""
    if pos_mask.sum() == 0 or neg_mask.sum() == 0:
        return float("nan")
    return pr_at(det, pos_mask, neg_mask, thresh_at_fpr(det[neg_mask], fpr))[0]


def bias_scatter(err):
    """偏り(平均誤差)と散らばり(標準偏差)を分ける。"""
    return float(np.mean(err)), float(np.std(err))


def delta_e(rgb_a, rgb_b):
    return fs.delta_e_map(np.clip(rgb_a, 0.0, 1.0), np.clip(rgb_b, 0.0, 1.0))


#: 既定の上層の厚み倍率。0.6 = 薄めに塗られた層(可視でもわずかに下絵が漏れる)。
TAU0 = 0.6
#: 既定のバンド数(400–1000 nm)。
NB0 = 16


def unmix_any(cube, endm_bands, constrained=True):
    """``fs.spec_unmix`` を呼ぶ。ただし **B=3 は op が拒否する**ので自前に落ちる。

    拒否は「(H,W,3) は色画像であって分光キューブではない」という型境界であり、
    RGB を黙って食わないための設計としては正しい。だが 3 バンドの多波長カメラ
    (可視 / レッドエッジ / 近赤外)は実在する構成で、それも同じ扱いで落ちる。
    バンド数の頭打ちを測るには 3 が要るので、ここだけ自前で解く。
    """
    if np.asarray(cube).shape[2] != 3:
        return fs.spec_unmix(cube, endm_bands, constrained=constrained)
    from scipy.optimize import nnls
    hh, ww, bb = cube.shape
    E = np.asarray(endm_bands, float)
    K = E.shape[0]
    if not constrained:
        return (cube.reshape(-1, bb) @ np.linalg.pinv(E)).reshape(hh, ww, K)
    delta = 1e3
    M = np.vstack([E.T, delta * np.ones((1, K))])
    P = cube.reshape(-1, bb)
    A = np.zeros((P.shape[0], K))
    y = np.empty(bb + 1)
    y[bb] = delta
    for i in range(P.shape[0]):
        y[:bb] = P[i]
        A[i], _ = nnls(M, y)
    return A.reshape(hh, ww, K)


def detectors(scene, spectra, rng, n_bands=NB0, sigma=None, fixed_sigma=False,
              endm_full=None, want=("rgb", "vis", "ms", "unmix", "ks", "nir", "sam")):
    """全手法の検出マップを作って dict で返す。値が大きいほど「下絵あり」。"""
    out = {}
    if "rgb" in want:
        rgb = make_rgb(spectra, rng, sigma=(sigma if sigma is not None
                                            else SIGMA0 * np.sqrt(3.0)))
        out["_rgb"] = rgb
        out["rgb"] = own_pca(rgb, 3)[0]                      # 成分選択は後段
    if "vis" in want:
        _, cv = make_cube(spectra, n_bands, rng, lo=400.0, hi=700.0,
                          sigma=sigma, fixed_sigma=fixed_sigma)
        out["vis"] = (own_pca(cv, 4)[0] if n_bands == 3
                      else fs.spec_pca(cv, 4)[0])
    centers, cube = make_cube(spectra, n_bands, rng, sigma=sigma, fixed_sigma=fixed_sigma)
    out["_cube"] = cube
    out["_centers"] = centers
    if "ms" in want:
        out["ms"] = (own_pca(cube, 4)[0] if n_bands == 3 else fs.spec_pca(cube, 4)[0])
    _, filt = band_filters(n_bands)
    Eb = (endm_full if endm_full is not None else endmember_spectra()) @ filt.T
    if "unmix" in want:
        A = unmix_any(cube, Eb)
        out["_abund"] = A
        out["unmix"] = A[..., CARBON_ROW]
    if "ks" in want:
        A2 = unmix_any(ks_transform(cube), ks_transform(Eb))
        out["_abund_ks"] = A2
        out["ks"] = A2[..., CARBON_ROW]
    if "nir" in want:
        d = nir_difference(centers, cube)
        if d is not None:
            out["nir"] = d
        nb = (centers >= NIR_LO) & (centers <= NIR_HI)
        if nb.any():
            out["nirb"] = -cube[..., nb].mean(axis=2)      # 近赤外 1 枚(暗い所を拾う)
    if "sam" in want:
        out["sam"] = -fs.spec_angle_mapper(cube, Eb[CARBON_ROW])
    return out


METHODS = (
    ("rgb",   "RGB の PCA(ゼロ点)", True),
    ("vis",   "可視のみ多波長 PCA", True),
    ("ms",    "可視+近赤外 PCA", True),
    ("unmix", "線形アンミキシング", False),
    ("ks",    "K/S アンミキシング", False),
    ("nir",   "近赤外の単純差分", False),
    ("nirb",  "近赤外 1 枚(反転)", False),
    ("sam",   "分光角マッパ", False),
)


def score_maps(det, pos, neg):
    """PCA 系は成分と符号を真値で選ぶ(下駄)。他はそのまま。"""
    maps = {}
    for key, _name, is_pca in METHODS:
        if key not in det:
            continue
        maps[key] = best_pc_detector(det[key], pos, neg)[0] if is_pca else det[key]
    return maps


def main():
    t_all = time.perf_counter()
    rng = np.random.default_rng(SEED)
    scene = build_scene()
    ink, flake, field = scene["ink"], scene["flake"], scene["field"]

    # 評価マスク。中間の被覆率(0.02 < alpha < 0.6)は「どちらとも言えない」ので外す。
    pos_all = ink >= 0.6
    neg_all = ink <= 0.02
    pos, neg = pos_all & ~flake, neg_all & ~flake
    field_names = ("群青の面", "アズライトの面", "朱+茜の面")

    # ---------------------------------------------------------------- 1 -----
    print("\n1. 場面 —— 何を作って、何を真値として握っているか")
    print(f"   画素 {H}x{W} / 分光 {WL[0]:.0f}–{WL[-1]:.0f} nm を {WL.size} 点")
    print("   層: 白亜の地 → 炭素黒の線で下絵 → 上層(区画ごとに顔料が違う)、一部剥落")
    rows = [
        ["下絵の線 (alpha>=0.6)", str(int(pos_all.sum())), "%.1f %%" % (100 * pos_all.mean())],
        ["中間の縁 (0.02<alpha<0.6)", str(int(((ink > 0.02) & (ink < 0.6)).sum())),
         "%.1f %%" % (100 * ((ink > 0.02) & (ink < 0.6)).mean())],
        ["下絵なし (alpha<=0.02)", str(int(neg_all.sum())), "%.1f %%" % (100 * neg_all.mean())],
        ["剥落部", str(int(flake.sum())), "%.1f %%" % (100 * flake.mean())],
        ["剥落部のうち線", str(int((pos_all & flake).sum())), "—"],
    ]
    for f in range(3):
        rows.append(["区画 %d: %s" % (f, field_names[f]), str(int((field == f).sum())),
                     "%.1f %%" % (100 * (field == f).mean())])
    _table(["真値の内訳", "画素数", "割合"], rows)

    # ---------------------------------------------------------------- 2 -----
    print("\n2. 物理の確認 —— Kubelka–Munk が両端で正しく振る舞うか")
    lim_rows = []
    for key in LAYER_KEYS:
        r_inf, s550, name = PIGMENTS[key]
        S = scat(s550)
        K = S * ks_ratio(r_inf)
        rg = np.full_like(S, 0.5)
        e_thick = float(np.abs(km_layer(K, S, 30.0, rg) - r_inf).max())
        e_thin = float(np.abs(km_layer(K, S, 1e-9, rg) - 0.5).max())
        lim_rows.append([name, "%.3f" % r_inf[WL == 550][0], "%.1f" % s550,
                         "%.1e" % e_thick, "%.1e" % e_thin])
    _table(["顔料", "R∞(550nm)", "散乱能 S550", "厚→∞ の誤差", "厚→0 の誤差"], lim_rows)

    # 下絵そのものの信号(インクを消した同じ場面との差)。手法の話の前に物理を見る。
    scene_noink = dict(scene, ink=np.zeros_like(ink))
    sig_rows = []
    for tau in (0.3, TAU0, 1.0, 2.0):
        d = render_spectra(scene, tau=tau) - render_spectra(scene_noink, tau=tau)
        row = ["%.1f" % tau]
        for f in range(3):
            fm = pos & (field == f)
            row.append("%+.4f" % d[..., WL == 450][..., 0][fm].mean())
            row.append("%+.4f" % d[..., WL == 950][..., 0][fm].mean())
        sig_rows.append(row)
    _table(["厚み倍率 tau",
            "群青 450nm", "群青 950nm",
            "アズ 450nm", "アズ 950nm",
            "朱茜 450nm", "朱茜 950nm"], sig_rows)
    print("   線のところの反射率が、下絵を消した場合と比べてどれだけ下がるか。")
    print("   アズライトは近赤外でも吸収が残るので、下絵の信号がほぼ出ない(後で効く)。")

    print(f"\n   以降の既定: 厚み倍率 tau={TAU0} / バンド数 {NB0}(400–1000 nm) /")
    print(f"   雑音は光量一定モデル sigma = {SIGMA0} * sqrt(B) = "
          f"{SIGMA0 * np.sqrt(NB0):.4f}(RGB は sqrt(3) で {SIGMA0 * np.sqrt(3):.4f})")

    # ---------------------------------------------------------------- 3 -----
    print("\n3. 下絵の検出 —— 適合率と再現率を別々に、面ごとに分けて")
    spec0 = render_spectra(scene, tau=TAU0)
    det0 = detectors(scene, spec0, np.random.default_rng(SEED + 1))
    maps0 = score_maps(det0, pos, neg)

    rows = []
    detect_summary = {}
    for key, name, _p in METHODS:
        if key not in maps0:
            continue
        d = maps0[key]
        a = auc(d[pos], d[neg])
        t1 = thresh_at_fpr(d[neg], 0.01)
        t5 = thresh_at_fpr(d[neg], 0.05)
        r1, p1, f1 = pr_at(d, pos, neg, t1)
        r5, p5, f5 = pr_at(d, pos, neg, t5)
        per = [recall_at(d, pos & (field == f), neg & (field == f), 0.01) for f in range(3)]
        rf = recall_at(d, pos_all & flake, neg_all & flake, 0.01)
        aper = [auc(d[pos & (field == f)], d[neg & (field == f)]) for f in range(3)]
        detect_summary[key] = (a, r1, p1, per, rf, aper, f1)
        rows.append([name, "%.3f" % a, "%.4f" % f1, "%.3f" % r1, "%.3f" % p1,
                     "%.3f" % r5, "%.3f" % p5])
    _table(["手法", "AUC", "実FPR", "再現率@FPR1%", "適合率@FPR1%",
            "再現率@FPR5%", "適合率@FPR5%"], rows)
    print("   閾値は「下絵なしの画素の 1 %(5 %)だけが超える」ところに全体で 1 本。")
    print("   実FPR = その閾値で実際に超えた負例の割合。同値が多い検出器は 1 % に")
    print("   届かない(存在量は負例の大半が厳密に 0 なので、動作点自体が飛び飛び)。")
    print("   PCA の 3 手法は **真値を見て**成分と符号を選んでいる(ゼロ点に下駄を履かせた)。")

    rows = []
    for key, name, _p in METHODS:
        if key not in detect_summary:
            continue
        a, r1, p1, per, rf, aper, _f = detect_summary[key]
        rows.append([name] + ["%.3f" % v for v in aper]
                    + ["%.3f" % v for v in per] + ["%.3f" % rf])
    _table(["手法(面ごとに閾値を引き直す)", "AUC群青", "AUCアズ", "AUC朱茜",
            "再現群青", "再現アズ", "再現朱茜", "再現剥落"], rows)
    print("   上の表と違い、ここは **面ごとに閾値を引き直した**。信号があるかどうかと、")
    print("   全体で 1 本の閾値が引けるかどうかは別の問いだから分ける。")

    # ---------------------------------------------------------------- 4 -----
    print("\n4. 崖 (a) —— 上層の光学的厚み。下絵はどこで見えなくなるか")
    taus = (0.15, 0.3, 0.6, 1.0, 1.6, 2.5)
    rows_a = []
    cliff_a = {}
    for tau in taus:
        sp = render_spectra(scene, tau=tau)
        dt = detectors(scene, sp, np.random.default_rng(SEED + 2),
                       want=("rgb", "ms", "unmix", "nir"))
        mp = score_maps(dt, pos, neg)
        row = ["%.2f" % tau]
        cliff_a[tau] = {}
        for key in ("rgb", "ms", "unmix", "nir"):
            d = mp[key]
            r1 = pr_at(d, pos, neg, thresh_at_fpr(d[neg], 0.01))[0]
            r1b = recall_at(d, pos & (field == 1), neg & (field == 1), 0.01)
            cliff_a[tau][key] = (r1, r1b)
            row += ["%.3f" % r1, "%.3f" % r1b]
        rows_a.append(row)
    _table(["tau", "RGB全体", "RGBアズ", "多波長全体", "多波長アズ",
            "アンミ全体", "アンミアズ", "NIR全体", "NIRアズ"], rows_a)
    print("   「全体」= 全体で 1 本の閾値 / 「アズ」= アズライトの面だけで引き直した閾値。")
    print("   平均の厚み(剥落部を除く)= tau x %.3f。" % scene["thick"][~flake].mean())

    # ---------------------------------------------------------------- 5 -----
    print("\n5. 崖 (b) —— バンド数。増やすほど良い、とは限らない")
    print("   左半分 = 光量一定(バンドを割ると 1 本あたりの雑音は sqrt(B) 倍)")
    print("   右半分 = 雑音固定(バンドを増やしても雑音が増えない、都合のよい仮定)")
    rows_b = []
    cliff_b = {}
    for nb in (3, 8, 16, 31):
        row = [str(nb)]
        cliff_b[nb] = {}
        for fixed in (False, True):
            dt = detectors(scene, spec0, np.random.default_rng(SEED + 3), n_bands=nb,
                           fixed_sigma=fixed, want=("ms", "unmix", "nir"))
            mp = score_maps(dt, pos, neg)
            for key in ("ms", "unmix", "nir"):
                d = mp[key]
                r1 = pr_at(d, pos, neg, thresh_at_fpr(d[neg], 0.01))[0]
                cliff_b[nb][(key, fixed)] = r1
                row.append("%.3f" % r1)
        rows_b.append(row)
    _table(["バンド数", "多波長PCA", "アンミックス", "NIR差分",
            "多波長PCA*", "アンミックス*", "NIR差分*"], rows_b)
    print("   * = 雑音固定。B=3 は fs.spec_unmix / fs.spec_pca が拒否するので自前で解いた。")

    # ---------------------------------------------------------------- 6 -----
    print("\n6. 崖 (c) —— 似た 2 つの青。どこまで似ると分けられなくなるか")
    print("   ここだけは **層を挟まない**。層(Kubelka–Munk)の非線形を混ぜると、")
    print("   アンミキシングの偏りが飽和して青の似方に反応しなくなる(最初の版が")
    print("   まさにそれで、相関 -0.11 でも 0.9997 でも偏りが +0.474 で一定だった)。")
    print("   線形混合モデルが成り立つ土俵でだけ「分光の似方」の崖を測る。")
    az = PIGMENTS["azurite"][0]
    ul = PIGMENTS["ultramarine"][0]
    _, filt16 = band_filters(NB0)
    # 真値: 2 つの青の配合比を空間的に構造をもって振る(乱数の面にしない)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    frac = np.clip(0.5 + 0.45 * np.sin(xx * 0.11) * np.cos(yy * 0.07)
                   + 0.15 * (yy / (H - 1) - 0.5), 0.02, 0.98)
    wfrac = 0.25 + 0.15 * np.cos(xx * 0.05)               # 鉛白の混ぜ量
    lw = PIGMENTS["lead_white"][0]
    rows_c = []
    cliff_c = []
    rng_c = np.random.default_rng(SEED + 4)
    for s in (1.0, 0.5, 0.25, 0.12, 0.06, 0.03, 0.015):
        blue2 = np.clip(az + s * (ul - az), 0.02, 0.95)
        Eb = np.vstack([az, blue2, lw]) @ filt16.T
        r = float(np.corrcoef(Eb[0], Eb[1])[0, 1])
        mix = ((1.0 - wfrac) * frac)[..., None] * Eb[0] \
            + ((1.0 - wfrac) * (1.0 - frac))[..., None] * Eb[1] \
            + wfrac[..., None] * Eb[2]
        cube = mix + rng_c.normal(0.0, SIGMA0 * np.sqrt(NB0), mix.shape)
        A = fs.spec_unmix(cube, Eb)
        est = A[..., 0] / np.maximum(A[..., 0] + A[..., 1], 1e-12)
        b, sc_ = bias_scatter(est - frac)
        worst = float(np.abs(est - frac).max())
        cliff_c.append((r, b, sc_, worst))
        rows_c.append(["%.5f" % r, "%+.4f" % b, "%.4f" % sc_, "%.3f" % worst,
                       "可" if sc_ < 0.10 else "不可"])
    _table(["2 青の相関 r", "配合比の偏り", "配合比の散らばり", "最悪誤差", "分離"],
           rows_c)
    print("   偏り = 平均誤差、散らばり = 誤差の標準偏差。1 つの RMSE に丸めない。")
    print("   「分離 可」= 散らばりが 0.10 未満(配合比を 1 割の精度で言える)。")

    # ---------------------------------------------------------------- 7 -----
    print("\n7. 崖 (d) —— 褪色。端成分を未褪色のまま使うとどれだけ外れるか")
    truth_rgb = make_rgb(render_spectra(scene, tau=TAU0, fade=1.0),
                         np.random.default_rng(SEED + 9), sigma=0.0)
    E_unfaded = endmember_spectra(fade=1.0)
    im = LAYER_KEYS.index("madder")
    f2 = (field == 2) & ~flake & neg_all
    rows_d = []
    cliff_d = {}
    for fade in (1.0, 0.7, 0.5, 0.3, 0.15):
        sp = render_spectra(scene, tau=TAU0, fade=fade)
        obs_rgb = make_rgb(sp, np.random.default_rng(SEED + 5))
        _, cube = make_cube(sp, NB0, np.random.default_rng(SEED + 5))
        de_null = float(np.median(delta_e(obs_rgb, truth_rgb)[f2]))
        row = ["%.2f" % fade, "%.2f" % de_null]
        cliff_d[fade] = {"null": de_null}
        for tag, E in (("固定", E_unfaded), ("追従", endmember_spectra(fade=fade))):
            A = unmix_any(cube, E @ filt16.T)
            lay = A[..., :len(LAYER_KEYS)]
            lay = lay / np.maximum(lay.sum(axis=2, keepdims=True), 1e-12)
            b, s = bias_scatter(lay[..., im][f2] - scene["conc"][..., im][f2])
            # 未褪色の端成分で組み直して描き直す = 退色前の色の復元
            rec = np.tensordot(A, E_unfaded, axes=([2], [0]))
            rec_rgb = make_rgb(rec, np.random.default_rng(SEED + 6), sigma=0.0)
            de = float(np.median(delta_e(rec_rgb, truth_rgb)[f2]))
            cliff_d[fade][tag] = (b, s, de)
            row += ["%+.3f" % b, "%.3f" % s, "%.2f" % de]
        rows_d.append(row)
    _table(["褪色 f", "何もしない ΔE00",
            "固定:茜の偏り", "固定:散らばり", "固定:復元 ΔE00",
            "追従:茜の偏り", "追従:散らばり", "追従:復元 ΔE00"], rows_d)
    print("   f = 茜レーキの吸収 K に掛ける倍率。1 = 未褪色。ΔE00 は朱+茜の面の中央値。")
    print("   「固定」= 端成分を未褪色のまま使う / 「追従」= 褪色後の端成分を渡す(反則)。")

    # ---------------------------------------------------------------- 8 -----
    print("\n8. 崖 (e) —— 雑音")
    rows_e = []
    cliff_e = {}
    for sg in (0.0, 0.001, 0.004, 0.01, 0.03, 0.1):
        dt = detectors(scene, spec0, np.random.default_rng(SEED + 7), sigma=sg,
                       want=("rgb", "ms", "unmix", "nir"))
        mp = score_maps(dt, pos, neg)
        row = ["%.3f" % sg]
        cliff_e[sg] = {}
        for key in ("rgb", "ms", "unmix", "nir"):
            d = mp[key]
            r1 = pr_at(d, pos, neg, thresh_at_fpr(d[neg], 0.01))[0]
            cliff_e[sg][key] = r1
            row.append("%.3f" % r1)
        rows_e.append(row)
    _table(["雑音 sigma", "RGB PCA", "多波長 PCA", "アンミックス", "NIR 差分"], rows_e)

    # ---------------------------------------------------------------- 9 -----
    print("\n9. 顔料の存在量 —— 偏りと散らばりを分ける(既定条件)")
    painted = ~flake & neg_all
    rows_f = []
    ab_summary = {}
    for tag, akey in (("反射率で線形", "_abund"), ("K/S で線形", "_abund_ks")):
        A = det0[akey]
        lay = A[..., :len(LAYER_KEYS)]
        lay = lay / np.maximum(lay.sum(axis=2, keepdims=True), 1e-12)
        for i, key in enumerate(LAYER_KEYS):
            fm = painted & (scene["conc"][..., i] > 0.02)
            if fm.sum() < 20:
                continue
            b, s = bias_scatter(lay[..., i][fm] - scene["conc"][..., i][fm])
            ab_summary[(tag, key)] = (b, s)
            rows_f.append([tag, PIGMENTS[key][2], str(int(fm.sum())),
                           "%.3f" % scene["conc"][..., i][fm].mean(),
                           "%+.3f" % b, "%.3f" % s])
    _table(["空間", "顔料", "対象画素", "真の平均濃度", "偏り", "散らばり"], rows_f)
    print("   真値は上層の顔料濃度(和 1)。推定は 7 端成分のうち上層 5 種を和 1 に正規化。")
    print("   線形混合モデルは層構造(Kubelka–Munk)を知らないので、偏りは残って当然。")
    print("   見るべきは **偏りと散らばりのどちらが大きいか** —— 偏りなら補正できる。")

    # --------------------------------------------------------------- 10 -----
    print("\n10. まとめ —— 何が効いて、何が効かなかったか")
    zero = detect_summary["rgb"][1]
    for key, name, _p in METHODS:
        if key not in detect_summary:
            continue
        a, r1, p1, per, rf, aper, f1 = detect_summary[key]
        gain = ("%.2f 倍" % (r1 / zero)) if zero > 1e-6 else "—"
        print("   %s: AUC %.3f / 再現率@FPR1%% %.3f(ゼロ点比 %s)/ 適合率 %.3f"
              % (_pad(name, 22), a, r1, gain, p1))

    dt_total = time.perf_counter() - t_all

    # --------------------------------------------------------------- 検証 ----
    # 1. ゼロ点が実在し、可視だけでは下絵がほとんど見えない
    assert detect_summary["rgb"][0] < 0.90, \
        "ゼロ点(RGB PCA)が強すぎる。実験設計が崩れた: AUC %.3f" % detect_summary["rgb"][0]
    # 2. 近赤外を含む手法がゼロ点に勝つ
    assert detect_summary["nir"][1] > 2.0 * max(detect_summary["rgb"][1], 0.01), \
        "近赤外がゼロ点に勝てていない"
    assert detect_summary["ms"][0] > detect_summary["vis"][0], \
        "可視+近赤外が可視のみに勝てていない"
    # 3. 面ごとに結果が割れる(1 つの数字にまとめられない)
    nir_per = detect_summary["nir"][3]
    assert nir_per[1] < 0.5 * max(nir_per[0], nir_per[2]), \
        "アズライトの面でも近赤外が効いてしまっている(物理の仮定が崩れた): %r" % (nir_per,)
    assert detect_summary["nir"][4] > 0.8, "剥落部ですら下絵が取れていない"
    # 4. 崖 (a): 厚みで単調に落ち、どこかで半分を割る
    nir_a = [cliff_a[t]["nir"][0] for t in taus]
    assert nir_a[0] > 0.8 and nir_a[-1] < 0.5, \
        "厚みの崖が見えない: %r" % (["%.3f" % v for v in nir_a],)
    assert all(b <= a + 1e-9 for a, b in zip(nir_a, nir_a[1:])), \
        "厚みに対して単調でない: %r" % (["%.3f" % v for v in nir_a],)
    # 5. 崖 (b): 光量一定なら 8→16→31 で頭打ち(31 が 16 を明確に上回らない)
    r8, r16, r31 = (cliff_b[n][("unmix", False)] for n in (8, 16, 31))
    assert r31 <= r16 + 0.02, \
        "光量一定でもバンドを増やし続けて改善している(頭打ちの所見が崩れた): " \
        "8=%.3f 16=%.3f 31=%.3f" % (r8, r16, r31)
    assert cliff_b[3][("unmix", False)] < r8, "3 バンドが 8 バンドに勝っている"
    # 6. 崖 (c): 相関が上がるほど散らばりが増える
    scat_c = [c[2] for c in cliff_c]
    assert scat_c[-1] > 3.0 * scat_c[0], \
        "2 つの青を似せても散らばりが増えない: %r" % (["%.3f" % v for v in scat_c],)
    # 7. 崖 (d): 端成分固定は褪色が進むほど外れる / 追従より必ず悪い
    de_fixed = [cliff_d[f]["固定"][2] for f in (1.0, 0.7, 0.5, 0.3, 0.15)]
    assert de_fixed[-1] > de_fixed[0], "褪色を進めても固定端成分の誤差が増えない"
    for f in (0.7, 0.5, 0.3, 0.15):
        assert cliff_d[f]["固定"][2] >= cliff_d[f]["追従"][2] - 1e-9, \
            "端成分を追従させたのに悪化した (f=%.2f)" % f
    # 8. 崖 (e): 雑音で単調に落ちる
    ne = [cliff_e[s]["nir"] for s in (0.0, 0.001, 0.004, 0.01, 0.03, 0.1)]
    assert ne[0] > ne[-1] and ne[-1] < 0.3, \
        "雑音で落ちない: %r" % (["%.3f" % v for v in ne],)
    # 9. 物理の両端(KM の極限)が閉形式に一致
    for key in LAYER_KEYS:
        r_inf, s550, _n = PIGMENTS[key]
        S = scat(s550)
        assert np.abs(km_layer(S * ks_ratio(r_inf), S, 1e-9,
                               np.full_like(S, 0.5)) - 0.5).max() < 1e-5
    print(f"\n総所要 {dt_total:.1f} 秒")
    print("PASS")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
