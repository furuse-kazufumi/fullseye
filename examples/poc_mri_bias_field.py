# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""MRI のバイアス場が組織面積を歪める量 —— 灰白質と白質は逆向きに壊れ、足すと隠れる。

脳 MRI(T1 強調)から灰白質(GM)/白質(WM)/脳脊髄液(CSF)の体積を測る、という
仕事です(萎縮の経過観察・研究コホートの標準的な数字)。MRI の受信コイルには
感度の空間分布があり、画像は**滑らかな乗算場 b(x)**(バイアス場、強度不均一)を
掛けられて出てきます。組織の見分けは輝度しかないので、場が組織のコントラストに
近づいた所から**明るい側の GM が WM に、暗い側の WM が GM に**流れます。

EXTEND: 実データに差し替えるなら :func:`make_phantom` が返す ``labels``(組織の
真値)と観測画像の対を、手動分割つきの公開データ(BrainWeb 等)に置き換えます。
**組織ごとの真値が要ります** —— この PoC の主張は「合計は保存されて組織ごとの
誤差が隠れる」なので、全脳体積の真値だけでは測れません。場の真値 ``b`` は実データ
では手に入らないので「理想補正」の行は消え、**残留不均一(b̂/b の変動係数)は
測れなくなります** —— 代わりに WM 内の輝度の変動係数を使うのが常道ですが、それは
組織の中の本当の不均一と区別できません。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(大域 3 クラス大津、fullseye ``xsk2_multiotsu``)は場なし・SNR 20 で
   CSF +0.00 % / GM +1.45 % / WM -0.55 %**。大津のしきい値は 0.381 / 0.635 で
   真の輝度の中点 0.375 / 0.635 とほぼ同じ。壊すのは場のほう: 場 30 % で雑音を
   止めると GM -11.80 % / WM +4.48 %。
2. ★★**壊れ方は組織ごとに逆符号で、足すと隠れる**。振幅 30 %(SNR 20)で
   GM +20.17 % / WM -7.65 % だが GM+WM(いわゆる脳実質)は +0.00 %。臨床で
   いちばん見られる「脳実質体積」は、両方が大きく間違っていても動かない。
   CSF は場では動かない(-0.02 %)—— GM との輝度差 0.35 が場の幅より大きい。
3. ★★**符号は雑音の有無で反転する**。場 30 %・雑音なしでは大津の GM/WM しきい値が
   中点の下(0.625)に落ちて GM が WM へ流れ(GM -11.8 %)、SNR 20 では上(0.644)
   に飛んで WM が GM へ流れる(GM +20.2 %)。同じ場、同じ分割器で、雑音を
   足すだけで誤差の向きが変わる。
4. ★**崖の予測は 30.0 %、実測は 17.5 %**。「しきい値は真の輝度の中点に固定・
   雑音なし」の幾何予測では GM の誤差が 5 % を超える振幅は 30.0 %(GM -9.5 %)。
   実測(大津・SNR 20)は 17.5 %(GM +5.6 %)—— 予想どおり手前だが、**向きは
   予測と逆**(3 の理由)。予測は雑音なしの実測とは一致する(-9.5 vs -11.8)。
5. ★★**素朴な低域推定(log I をそのまま平滑)は場のない画像を壊す**。
   2 次多項式面(``fit_poly_surface``)を log I に当てると振幅 0 % で GM +81.8 %、
   ガウス低域(σ 24 px)でも +38.6 %(いずれも雑音の床 +1.45 % を引いた値)。
   中心に WM が集まる解剖そのものが「滑らかな場」に見えるから。★分割の残差から
   場を推定する反復(Wells 型・4 回)に替えると自傷は多項式 +0.05 % / ガウス
   -0.03 % / 格子 B スプライン -0.12 % に消え、振幅 40 % でも GM は +1.76 〜
   +2.21 %(理想補正 +1.94 %)。**補正器の基底より「何を平滑するか」が桁で効く**。
   ★ただし格子 B スプラインは粗→密(128→64→32→32 px)にしないと、初回の分割が
   外れた斑を場として追いかけ 40 % で GM +44 % に発散する(反復 1 回目 +4.0 %、
   2 回目で +1.8 % に収束)。
6. ★**周波数の崖は基底で決まる**: 場の空間スケール σ_b を 64 → 4 px と細かく
   すると、GM 誤差 5 % を超えるのは 2 次多項式面 32 px、ガウス(σ 24)16 px、
   格子 B スプライン(h 32)8 px。4 px(皮質リボンと同じ太さ)では全補正器が
   +9.3 〜 +10.0 % で壊れ、**真の b で割る理想補正(+1.45 %)だけが正しい** ——
   そこでは場と組織は同じ帯域に居る。★予想は「格子を 8 px に細かくすると
   場のない画像で自傷が戻る」だったが**外れた**: h 8 px でも床から +0.5 %。
   粗い側は h 64 px で σ_b 16 px の場を取り逃して +8.2 %。
7. ★**SNR の崖は場の補正では動かず、小さい組織に現れる**: 場なしでも SNR 15 で
   GM +8.5 %(ガウス裾の予測 +6.3 %)、SNR 10 で +34 %。GM→WM と WM→GM の
   取り違えの割合は同じでも、WM の面積が GM の 2.63 倍あるので相対誤差は GM に
   出る。理想補正でも SNR 15 で GM +6.9 %。Rician の底上げで CSF が GM に流れる
   のは SNR 5 で +11.2 %。
8. **残留不均一(b̂/b の変動係数)**: 振幅 30 % で 補正なし 7.99 % → Wells 型
   多項式 0.72 % / ガウス 0.48 % / 格子 B スプライン 0.84 %。
   ★``fit_bspline_surface``(FITPACK)は自動平滑では 8 節点 = 双三次多項式に
   留まり(1.53 %)、平滑係数を 5 に下げると頭の内側で |log b̂| 2.1(真値 0.19)、
   頭の外で 2.7e3 に発散して警告を握り潰す —— 非矩形の台では格子 B スプライン
   (N4 流)が要る。``dc_homomorphic`` op は組織のコントラスト自体が低域なので
   一緒に潰し、最良の cutoff でも CSF +254 % / WM -81 %。

【グラウンドトゥルース】
頭部は**閉形式の楕円殻**(頭蓋 / CSF 殻 / 皮質リボン / WM)で、皮質と WM の
境界は角度の正弦で皺を付ける。脳室(CSF)と深部灰白質(GM)を楕円で埋める。
組織の面積はラベル画像の画素数で**幾何から決まる**。輝度は T1 強調風に
CSF 0.20 / GM 0.55 / WM 0.72(GM/WM 比 0.76)。場 b(x) は表面コイル型のガウス
(主掃引)または σ_b でぼかした乱数場(周波数掃引)で、頭の内側で平均 1・
peak-to-peak = 振幅に正規化する。雑音は Rician(実部・虚部に独立ガウス、
SNR = WM 輝度 / σ)。すべての乱数は ``np.random.default_rng(SEED)`` で固定。

来歴(公開文献のみ): バイアス場補正の総説 Vovk, Pernus & Likar (2007) IEEE TMI;
N3 = Sled, Zijdenbos & Evans (1998) IEEE TMI; N4 = Tustison et al. (2010) IEEE TMI
(格子 B スプラインで場を表す); 分割と交互に場を推定する反復 = Wells et al. (1996)
IEEE TMI; Rician 雑音 = Gudbjartsson & Patz (1995) MRM; 多値大津 = Otsu (1979) /
Liao, Chen & Chung (2001)。BrainWeb ファントム(Collins et al. 1998)の考え方
(既知ラベル + 場 + 雑音)に倣うが、ここでは 2-D の楕円殻で自前に作る。
"""
from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
N_PIX = 256                 # 視野 [px](1 px = 1 mm と読む)
SEED = 7
MEAN = {"bg": 0.03, "csf": 0.20, "gm": 0.55, "wm": 0.72, "skull": 0.85}  # T1 風の輝度
LAB = {"bg": 0, "csf": 1, "gm": 2, "wm": 3, "skull": 4}
TISSUES = ("csf", "gm", "wm")                                     # 分割する 3 組織
SNR_DEFAULT = 20.0          # SNR = WM 輝度 / 雑音 σ
SIGMA_GAUSS = 24.0          # ガウス低域補正器の σ [px]
H_BSPLINE = 32.0            # 格子 B スプラインの制御点間隔 [px]
N_ITER = 4                  # Wells 型反復の回数
CLIFF = 5.0                 # 崖の定義: 面積誤差 ±5 %

_LED = fs.ledger


# --------------------------------------------------------------------------- #
# 場面を作る —— 真値は「ラベル画像の画素数」                                     #
# --------------------------------------------------------------------------- #
def make_phantom() -> dict:
    """楕円殻の脳スライス風ファントム。``labels`` が真値、``mask`` が頭蓋の内側。"""
    yy, xx = np.mgrid[0:N_PIX, 0:N_PIX].astype(np.float64)
    cy, cx = N_PIX / 2, N_PIX / 2
    ry, rx = 110.0, 92.0
    u, v = (yy - cy) / ry, (xx - cx) / rx
    rho = np.sqrt(u * u + v * v)
    theta = np.arctan2(u, v)
    # 皮質 / WM 境界は角度の正弦で皺を付ける(閉形式)
    r_gw = 0.76 + 0.035 * np.sin(9 * theta) + 0.025 * np.sin(14 * theta + 1.3)

    lab = np.zeros((N_PIX, N_PIX), np.int32)
    lab[rho < 1.0] = LAB["skull"]
    lab[rho < 0.92] = LAB["csf"]
    lab[rho < 0.86] = LAB["gm"]
    lab[rho < r_gw] = LAB["wm"]
    # 脳室(CSF)と深部灰白質(GM)
    for (oy, ox, ay, ax, name) in ((0, -22, 30, 9, "csf"), (0, 22, 30, 9, "csf"),
                                   (14, -40, 13, 11, "gm"), (14, 40, 13, 11, "gm")):
        e = ((yy - cy - oy) / ay) ** 2 + ((xx - cx - ox) / ax) ** 2 <= 1.0
        lab[e] = LAB[name]

    mask = rho < 0.92                                   # 頭蓋の内側 = 分割の対象
    clean = np.full((N_PIX, N_PIX), MEAN["bg"])
    for name, k in LAB.items():
        clean[lab == k] = MEAN[name]
    truth = {t: int(np.count_nonzero(lab == LAB[t])) for t in TISSUES}
    return {"labels": lab, "clean": clean, "mask": mask, "truth": truth,
            "yy": yy, "xx": xx}


def make_field(mask: np.ndarray, amplitude: float, kind: str = "coil",
               sigma_b: float = 64.0, seed: int = SEED) -> np.ndarray:
    """乗算場 b(x)。頭の内側で平均 1、peak-to-peak = ``amplitude``(0.3 = 30 %)。

    ``kind="coil"`` は表面コイル型(頭の右上に置いたガウス感度)、``"noise"`` は
    σ_b でぼかした乱数場(空間周波数を振る用)。
    """
    yy, xx = np.mgrid[0:N_PIX, 0:N_PIX].astype(np.float64)
    if kind == "coil":
        g = np.exp(-((yy - 40.0) ** 2 + (xx - 200.0) ** 2) / (2 * 90.0 ** 2))
    elif kind == "noise":
        rng = np.random.default_rng(seed + 1000)
        g = ndimage.gaussian_filter(rng.standard_normal((N_PIX, N_PIX)), sigma_b)
    else:
        raise ValueError(kind)
    g = g - g[mask].mean()
    pp = float(g[mask].max() - g[mask].min())
    g = g / pp if pp > 0 else g
    return 1.0 + amplitude * g


def observe(clean: np.ndarray, field: np.ndarray, snr: float, seed: int = SEED) -> np.ndarray:
    """Rician 雑音: 実部・虚部に独立ガウス。SNR = WM 輝度 / σ。"""
    rng = np.random.default_rng(seed)
    sigma = MEAN["wm"] / snr if snr > 0 else 0.0
    s = clean * field
    n1 = rng.standard_normal(s.shape) * sigma
    n2 = rng.standard_normal(s.shape) * sigma
    return np.sqrt((s + n1) ** 2 + n2 ** 2)


def scene_with(ph: dict, amplitude: float, snr: float = SNR_DEFAULT, **field_kw) -> tuple[dict, np.ndarray]:
    sc = dict(ph)
    sc["field"] = make_field(ph["mask"], amplitude, **field_kw)
    obs = observe(ph["clean"], sc["field"], snr)
    return sc, obs


# --------------------------------------------------------------------------- #
# 分割 —— 大域 3 クラス大津(fullseye ``xsk2_multiotsu``)                        #
# --------------------------------------------------------------------------- #
def multiotsu3(values: np.ndarray) -> np.ndarray:
    """頭の内側の画素だけに 3 クラス大津を掛け、0/1/2(暗い順)を返す。

    ``xsk2_multiotsu`` はヒストグラムだけで決まる op なので、画素の並びは
    関係ない —— マスク内の画素を 1 列に並べて正方形に詰め直してから呼ぶ
    (マスクの外の暗い背景を 4 つ目のクラスとして混ぜないため)。
    """
    v = np.asarray(values, np.float64)
    hi = float(np.percentile(v, 99.9))
    v = np.clip(v / hi, 0.0, 1.0) if hi > 0 else v
    n = v.size
    side = int(np.ceil(np.sqrt(n)))
    pad = np.concatenate([v, np.repeat(v[-1], side * side - n)]).reshape(side, side)
    q = fs.apply(pad, "xsk2_multiotsu", a=0.1)          # a<=0.5 -> 3 クラス
    return np.rint(q.ravel()[:n] * 2).astype(np.int32)


def otsu_thresholds(values: np.ndarray) -> tuple[float, float]:
    """3 クラス大津が実際に置いた 2 本のしきい値(クラス境界の中点、元の輝度単位)。"""
    v = np.asarray(values, np.float64)
    c = multiotsu3(v)
    t1 = 0.5 * (v[c == 0].max() + v[c == 1].min()) if (c == 0).any() and (c == 1).any() else float("nan")
    t2 = 0.5 * (v[c == 1].max() + v[c == 2].min()) if (c == 1).any() and (c == 2).any() else float("nan")
    return float(t1), float(t2)


def segment(img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """観測(または補正後)画像 -> ラベル画像(CSF/GM/WM、外は 0)。"""
    cls = multiotsu3(img[mask])
    out = np.zeros(img.shape, np.int32)
    out[mask] = cls + 1                                  # 1=CSF 2=GM 3=WM
    return out


def area_errors(seg: np.ndarray, truth: dict) -> dict:
    """組織ごとの面積誤差 [%]。GM+WM(脳実質)も別に返す。"""
    est = {t: int(np.count_nonzero(seg == LAB[t])) for t in TISSUES}
    err = {t: 100.0 * (est[t] - truth[t]) / truth[t] for t in TISSUES}
    tot_t = truth["gm"] + truth["wm"]
    err["gm+wm"] = 100.0 * (est["gm"] + est["wm"] - tot_t) / tot_t
    return err


def predict_zero_errors(ph: dict, field: np.ndarray) -> dict:
    """幾何予測: しきい値を真の輝度の中点に固定・雑音なしで、場だけが動かす面積。"""
    t_cg = 0.5 * (MEAN["csf"] + MEAN["gm"])
    t_gw = 0.5 * (MEAN["gm"] + MEAN["wm"])
    v = ph["clean"] * field
    seg = np.zeros(v.shape, np.int32)
    m = ph["mask"]
    seg[m] = 1 + (v[m] > t_cg).astype(np.int32) + (v[m] > t_gw).astype(np.int32)
    return area_errors(seg, ph["truth"])


def first_cliff(xs, errs, thr=CLIFF):
    """|誤差| が thr を初めて超える x(超えなければ None)。"""
    for x, e in zip(xs, errs):
        if abs(e) > thr:
            return x
    return None


# --------------------------------------------------------------------------- #
# 平滑器 —— 「マスク内の値 z(x) を滑らかな面で表す」3 つの基底                   #
# --------------------------------------------------------------------------- #
def smooth_poly2(z: np.ndarray, mask: np.ndarray, sc: dict, **_) -> np.ndarray:
    """2 次多項式面(``fit_poly_surface`` / ``eval_poly_surface``、公開経路)。"""
    x = (sc["xx"] / (N_PIX - 1)) * 2 - 1
    y = (sc["yy"] / (N_PIX - 1)) * 2 - 1
    model = _LED.fit_poly_surface(x[mask], y[mask], z[mask], degree=2)
    return np.asarray(_LED.eval_poly_surface(model, x, y), np.float64)


def smooth_gauss(z: np.ndarray, mask: np.ndarray, sc: dict, sigma: float = SIGMA_GAUSS, **_) -> np.ndarray:
    """マスク付きガウス低域(正規化畳み込み)。★公開経路に無い(``gaussian`` op は σ≦3)。"""
    num = ndimage.gaussian_filter(np.where(mask, z, 0.0), sigma)
    den = ndimage.gaussian_filter(mask.astype(np.float64), sigma)
    return num / np.maximum(den, 1e-6)


def _bspline_basis(n: int, h: float) -> np.ndarray:
    """1 次元の三次 B スプライン基底行列 (n, n_ctrl)。制御点は間隔 h、両端を 1 個ずつ余分に。"""
    n_ctrl = int(np.ceil(n / h)) + 3
    centers = (np.arange(n_ctrl) - 1) * h
    t = np.abs((np.arange(n)[:, None] - centers[None, :]) / h)
    b = np.where(t < 1, 2.0 / 3 - t * t + t ** 3 / 2,
                 np.where(t < 2, (2 - t) ** 3 / 6, 0.0))
    return b


def smooth_bspline(z: np.ndarray, mask: np.ndarray, sc: dict, h: float = H_BSPLINE,
                   step: int = 2, ridge: float = 10.0, **_) -> np.ndarray:
    """格子 B スプライン(N4 流: 等間隔の制御点に最小二乗)。★公開経路に無い。

    ``fit_bspline_surface``(FITPACK)は節点を自動配置するが、非矩形の台
    (頭の内側だけ)では平滑係数を小さくすると台の外で発散する(本文 7 参照)。
    ここは制御点を等間隔に固定し、リッジで台の外・台の縁の制御点を 0(log b = 0)
    に寄せる。★間引き 4 px・リッジ 1e-3 では縁の制御点が雑音を拾って場なしでも
    CV 4 % 残った(実測)。2 px・リッジ 10 で 0.9 %(ガウス σ24 は 0.5 %)。
    """
    by = _bspline_basis(N_PIX, h)
    bx = _bspline_basis(N_PIX, h)
    sub = np.zeros(mask.shape, bool)
    sub[::step, ::step] = True
    sub &= mask
    ys, xs = np.nonzero(sub)
    design = (by[ys][:, :, None] * bx[xs][:, None, :]).reshape(len(ys), -1)
    n_c = design.shape[1]
    ata = design.T @ design + ridge * np.eye(n_c)
    coef = np.linalg.solve(ata, design.T @ z[ys, xs])
    return by @ coef.reshape(by.shape[1], bx.shape[1]) @ bx.T


def smooth_fitpack(z: np.ndarray, mask: np.ndarray, sc: dict, step: int = 6,
                   smooth: float | None = None, **_) -> np.ndarray:
    """``fit_bspline_surface`` / ``eval_bspline_surface``(FITPACK、公開経路)そのまま。"""
    sub = np.zeros(mask.shape, bool)
    sub[::step, ::step] = True
    sub &= mask
    ys, xs = np.nonzero(sub)
    tck = _LED.fit_bspline_surface(xs.astype(np.float64), ys.astype(np.float64),
                                   z[ys, xs], smooth=smooth)
    ax = np.arange(N_PIX, dtype=np.float64)
    # grid=True は (len(x), len(y)) = (列, 行) で返るので転置して (行, 列) に
    return np.asarray(_LED.eval_bspline_surface(tck, ax, ax, grid=True), np.float64).T


SMOOTHERS = {"poly2": smooth_poly2, "gauss": smooth_gauss, "bspline": smooth_bspline,
             "fitpack": smooth_fitpack}


# --------------------------------------------------------------------------- #
# 場の推定器 —— 素朴(log I を平滑)と Wells 型(分割残差を平滑して反復)            #
# --------------------------------------------------------------------------- #
def _center(logb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    return logb - logb[mask].mean()


def est_naive(obs: np.ndarray, mask: np.ndarray, sc: dict, smoother: str, **kw) -> np.ndarray:
    """log I をそのまま平滑して場とみなす(いちばん素朴な低域推定)。"""
    fit = SMOOTHERS[smoother](np.where(mask, np.log(obs), 0.0), mask, sc, **kw)
    return np.exp(np.clip(_center(fit, mask), -3, 3))


def est_wells(obs: np.ndarray, mask: np.ndarray, sc: dict, smoother: str,
              n_iter: int = N_ITER, history: list | None = None, **kw) -> np.ndarray:
    """分割と交互に場を推定する反復(Wells 1996 型、N4 と同じ「残差を平滑」)。

    各反復: 現在の補正画像を 3 クラスに分割 -> クラス平均の区分定数モデル ->
    log 残差 = log(補正画像) - log(モデル) -> 平滑 -> log b̂ に足す。
    格子 B スプラインは N4 と同じく粗い格子から始めて細かくする(4h, 2h, h, h)。
    ★粗→密にしないと、振幅 40 % で初回の分割が大きく外れた斑を細かい格子が
    「場」として追いかけ、GM +44 % に発散した(2026-09-07 実測)。
    """
    logb = np.zeros(obs.shape)
    h0 = float(kw.pop("h", H_BSPLINE))
    for k in range(n_iter):
        if smoother == "bspline":            # N4 流の粗→密: 4h, 2h, h, h, ...
            kw["h"] = h0 * 2 ** max(0, n_iter - 2 - k)
        corr = obs / np.exp(logb)
        seg = segment(corr, mask)
        model = np.ones(obs.shape)
        for k in (1, 2, 3):
            sel = seg == k
            if sel.any():
                model[sel] = corr[sel].mean()
        resid = np.where(mask, np.log(np.maximum(corr, 1e-6)) - np.log(model), 0.0)
        delta = SMOOTHERS[smoother](resid, mask, sc, **kw)
        logb = np.clip(_center(logb + delta, mask), -3, 3)
        if history is not None:
            history.append(np.exp(logb))
    return np.exp(logb)


def corrected_homomorphic(obs: np.ndarray, mask: np.ndarray, a: float) -> np.ndarray:
    """``dc_homomorphic`` op(周波数領域で log I の低域を減衰)。b̂ は出ない。"""
    v = np.where(mask, obs, 0.0)
    v = v / float(v.max())
    return fs.apply(v, "dc_homomorphic", a=a, b=0.0)


METHODS = {
    "zero": None,
    "naive_poly2": ("naive", "poly2"), "naive_gauss": ("naive", "gauss"),
    "wells_poly2": ("wells", "poly2"), "wells_gauss": ("wells", "gauss"),
    "wells_bspline": ("wells", "bspline"), "wells_fitpack": ("wells", "fitpack"),
    "homo": None, "ideal": None,
}
NAMES = {"zero": "ゼロ点(補正なし)",
         "naive_poly2": "素朴: log I に 2 次多項式面", "naive_gauss": "素朴: log I にガウス σ%.0f" % SIGMA_GAUSS,
         "wells_poly2": "Wells 型: 2 次多項式面", "wells_gauss": "Wells 型: ガウス σ%.0f" % SIGMA_GAUSS,
         "wells_bspline": "Wells 型: 格子 B スプライン h%.0f" % H_BSPLINE,
         "wells_fitpack": "Wells 型: fit_bspline_surface(自動)",
         "homo": "dc_homomorphic op(最良 cutoff)", "ideal": "理想補正(真の b)"}


def evaluate(method: str, obs: np.ndarray, sc: dict, **kw) -> dict:
    """1 手法を掛けて {誤差, 残留 CV, 補正画像, b̂, 分割} を返す。"""
    mask = sc["mask"]
    b_true = sc["field"] / sc["field"][mask].mean()
    if method == "zero":
        corr, bhat = obs, np.ones_like(obs)
    elif method == "ideal":
        bhat = b_true
        corr = obs / bhat
    elif method == "homo":
        best = None
        for a in (0.0, 0.25, 0.5, 1.0):
            c = corrected_homomorphic(obs, mask, a)
            e = area_errors(segment(c, mask), sc["truth"])
            worst = max(abs(e[t]) for t in TISSUES)
            if best is None or worst < max(abs(best[1][t]) for t in TISSUES):
                best = (c, e, a)
        corr, bhat = best[0], None
        kw = {"best_a": best[2]}
    else:
        kind, smoother = METHODS[method]
        fn = est_naive if kind == "naive" else est_wells
        bhat = fn(obs, mask, sc, smoother, **kw)
        corr = obs / bhat
    seg = segment(corr, mask)
    out = {"err": area_errors(seg, sc["truth"]), "seg": seg, "corr": corr, "bhat": bhat,
           "best_a": kw.get("best_a")}
    if bhat is not None:
        ratio = (bhat / b_true)[mask]
        out["cv"] = 100.0 * float(ratio.std() / ratio.mean())
    else:
        out["cv"] = float("nan")
    return out


def _label_rgb(img: np.ndarray, seg: np.ndarray) -> np.ndarray:
    base = np.clip(img / max(float(np.percentile(img, 99.9)), 1e-6), 0, 1)
    return np.asarray(fs.overlay_labels(base, seg, alpha=0.75), np.float64)


# --------------------------------------------------------------------------- #
# 1. ゼロ点と対照群                                                             #
# --------------------------------------------------------------------------- #
def section_zero_point(ph: dict) -> dict:
    print("\n" + "=" * 78)
    print("1) ゼロ点(大域 3 クラス大津)と対照群 —— 真値は幾何から")
    print("=" * 78)
    tr = ph["truth"]
    print("  真値の面積 [px]: CSF %d / GM %d / WM %d / 頭蓋内 %d" % (
        tr["csf"], tr["gm"], tr["wm"], int(ph["mask"].sum())))
    rows, out = [], {}
    for label, amp, snr in (("場なし・雑音なし", 0.0, 0.0), ("場なし・SNR 20", 0.0, SNR_DEFAULT),
                            ("場 30 %・雑音なし", 0.30, 0.0), ("場 30 %・SNR 20", 0.30, SNR_DEFAULT)):
        sc, obs = scene_with(ph, amp, snr)
        r = evaluate("zero", obs, sc)
        e = r["err"]
        t1, t2 = otsu_thresholds(obs[ph["mask"]])
        rows.append([label] + ["%+.2f" % e[k] for k in ("csf", "gm", "wm", "gm+wm")] + ["%.3f / %.3f" % (t1, t2)])
        out[label] = (sc, obs, r)
        print("   %-16s CSF %+6.2f %%  GM %+6.2f %%  WM %+6.2f %%  | GM+WM %+6.2f %%  | 大津のしきい値 %.3f / %.3f" % (
            label, e["csf"], e["gm"], e["wm"], e["gm+wm"], t1, t2))
    print("   (真の輝度の中点 = %.3f / %.3f。場 30 %% では雑音の有無で GM/WM のしきい値が中点の"
          "反対側に飛び、誤差の符号が反転する)" % (0.5 * (MEAN["csf"] + MEAN["gm"]), 0.5 * (MEAN["gm"] + MEAN["wm"])))
    figs.save_table("controls", ["条件", "CSF [%]", "GM [%]", "WM [%]", "GM+WM [%]", "大津しきい値 CSF|GM / GM|WM"], rows,
                    title="対照群: 場と雑音を別々に止める(ゼロ点の面積誤差)",
                    caption="雑音だけでは壊れず、場だけで GM と WM が逆向きに動く。")

    sc, obs, r = out["場 30 %・SNR 20"]
    ideal = evaluate("ideal", obs, sc)
    wrong = (r["seg"] - ph["labels"]).astype(np.float64) * (ph["mask"] & (r["seg"] != ph["labels"]))
    figs.save_grid("scene",
                   [_label_rgb(ph["clean"], ph["labels"] * (ph["labels"] <= 3)), sc["field"],
                    obs, _label_rgb(obs, r["seg"]), _label_rgb(obs, ideal["seg"]), wrong],
                   ["真値ラベル(CSF/GM/WM、1 px = 1 mm)", "バイアス場 b(x)(振幅 30 %)",
                    "観測(Rician、SNR 20)", "ゼロ点の分割(GM %+.1f %% / WM %+.1f %%)" % (
                        r["err"]["gm"], r["err"]["wm"]),
                    "理想補正の分割(GM %+.1f %% / WM %+.1f %%)" % (
                        ideal["err"]["gm"], ideal["err"]["wm"]),
                    "誤り(+: 明るい組織へ / -: 暗い組織へ)"],
                   title="脳スライス風ファントムにバイアス場を掛ける", ncols=3,
                   signed=[False, False, False, False, False, True])
    return {"noise_only": out["場なし・SNR 20"][2]["err"], "field_only": out["場 30 %・雑音なし"][2]["err"],
            "field30": r["err"]}


# --------------------------------------------------------------------------- #
# 2-4. 振幅を振る —— 逆符号・合計保存・崖の予測・補正の自傷                       #
# --------------------------------------------------------------------------- #
def section_amplitude_sweep(ph: dict) -> dict:
    print("\n" + "=" * 78)
    print("2-4) 場の振幅 0 -> 40 % —— 組織ごとに逆符号、GM+WM は動かない、崖の予測、補正")
    print("=" * 78)
    amps = np.arange(0.0, 0.401, 0.05)
    methods = ("zero", "naive_poly2", "naive_gauss", "wells_poly2", "wells_gauss", "wells_bspline", "ideal")
    res = {m: {k: [] for k in ("csf", "gm", "wm", "gm+wm", "cv")} for m in methods}
    pred = {k: [] for k in ("gm", "wm")}
    print("   振幅 | ゼロ点  CSF     GM      WM   GM+WM | 予測  GM     WM | GM 誤差: 素朴poly2 素朴gauss W-poly2 W-gauss W-bspl  理想")
    for a in amps:
        sc, obs = scene_with(ph, a)
        p = predict_zero_errors(ph, sc["field"])
        for k in pred:
            pred[k].append(p[k])
        line = []
        for m in methods:
            r = evaluate(m, obs, sc)
            for k in ("csf", "gm", "wm", "gm+wm"):
                res[m][k].append(r["err"][k])
            res[m]["cv"].append(r["cv"])
            line.append(r["err"]["gm"])
        z = res["zero"]
        print("   %3.0f %% | %+6.2f %+7.2f %+7.2f %+6.2f | %+6.2f %+6.2f | %+8.2f %+8.2f %+7.2f %+7.2f %+7.2f %+6.2f" % (
            100 * a, z["csf"][-1], z["gm"][-1], z["wm"][-1], z["gm+wm"][-1],
            p["gm"], p["wm"], *line[1:]))

    pct = [100 * a for a in amps]
    # 崖を 2.5 % 刻みで細かく(掃引は 5 % 刻み): 幾何予測 vs 実測(大津)
    fine = np.arange(0.0, 0.401, 0.025)
    pg, mg = [], []
    for a in fine:
        sc, obs = scene_with(ph, a)
        pg.append(predict_zero_errors(ph, sc["field"])["gm"])
        mg.append(evaluate("zero", obs, sc)["err"]["gm"])
    fpct = [100 * a for a in fine]
    cliff_pred = first_cliff(fpct, pg)
    cliff_meas = first_cliff(fpct, mg)

    i30 = int(np.argmin(np.abs(amps - 0.30)))
    z = res["zero"]
    print("\n  ★振幅 30 %%: GM %+.2f %% / WM %+.2f %% だが GM+WM は %+.2f %% —— 足すと隠れる。CSF %+.2f %%。" % (
        z["gm"][i30], z["wm"][i30], z["gm+wm"][i30], z["csf"][i30]))
    ip = fpct.index(cliff_pred) if cliff_pred is not None else -1
    im = fpct.index(cliff_meas) if cliff_meas is not None else -1
    print("  ★崖(GM 誤差が ±%.0f %% を超える振幅、2.5 %% 刻み): 幾何予測(しきい値固定・雑音なし) %.1f %%(GM %+.1f %%) / "
          "実測(大津・SNR %.0f) %.1f %%(GM %+.1f %%)" % (CLIFF, cliff_pred, pg[ip], SNR_DEFAULT, cliff_meas, mg[im]))
    print("     予想は「大津はしきい値を動かすので予測より手前で壊れる」。実測: %s。" % (
        "予想どおり手前" if (cliff_meas is not None and cliff_pred is not None and cliff_meas < cliff_pred)
        else "外れた —— 同じ場所(大津の中点は場で広がっても動かない)"))
    print("  ★場なし(振幅 0)に補正を掛けた自傷 GM(雑音の床 = 理想補正 %+.2f %% を引く): 素朴 poly2 %+.1f %% / "
          "素朴 gauss %+.1f %% | Wells poly2 %+.2f %% / gauss %+.2f %% / bspline %+.2f %%" % (
              res["ideal"]["gm"][0], *(res[m]["gm"][0] - res["ideal"]["gm"][0] for m in
                                       ("naive_poly2", "naive_gauss", "wells_poly2", "wells_gauss", "wells_bspline"))))
    print("  振幅 40 %% の GM: ゼロ点 %+.1f %% -> Wells poly2 %+.2f %% / gauss %+.2f %% / bspline %+.2f %% / 理想 %+.2f %%" % (
        z["gm"][-1], res["wells_poly2"]["gm"][-1], res["wells_gauss"]["gm"][-1],
        res["wells_bspline"]["gm"][-1], res["ideal"]["gm"][-1]))

    figs.save_plot("amplitude_sweep_zero",
                   [("GM", pct, z["gm"]), ("WM", pct, z["wm"]), ("CSF", pct, z["csf"]),
                    ("GM+WM(脳実質)", pct, z["gm+wm"]), ("幾何予測 GM(しきい値固定)", pct, pred["gm"])],
                   xlabel="バイアス場の振幅(peak-to-peak)[%]", ylabel="面積誤差 [%]",
                   title="ゼロ点: GM と WM は逆向きに壊れ、GM+WM は動かない",
                   caption="幾何予測(しきい値固定・雑音なし)と大津の実測は同じ振幅で崖を越える。")
    figs.save_plot("amplitude_sweep_methods",
                   [(NAMES[m], pct, res[m]["gm"]) for m in
                    ("zero", "naive_gauss", "wells_poly2", "wells_gauss", "wells_bspline", "ideal")],
                   xlabel="バイアス場の振幅 [%]", ylabel="GM の面積誤差 [%]",
                   title="補正後の GM 誤差(場は表面コイル型、SNR %.0f)" % SNR_DEFAULT,
                   caption="素朴な log I の平滑は場が無くても壊す。分割残差の反復は 40 % まで持つ。")
    figs.save_plot("amplitude_residual_cv",
                   [(NAMES[m], pct, res[m]["cv"]) for m in ("zero", "wells_poly2", "wells_gauss", "wells_bspline")],
                   xlabel="バイアス場の振幅 [%]", ylabel="残留不均一 CV(b̂/b)[%]",
                   title="補正後に残る場(理想補正は 0)")
    return {"amps": pct, "res": res, "cliff_pred": cliff_pred, "cliff_meas": cliff_meas, "i30": i30}


# --------------------------------------------------------------------------- #
# 5. 振幅 30 % の表 —— 全手法・全組織・残留不均一                                #
# --------------------------------------------------------------------------- #
def section_table30(ph: dict) -> dict:
    print("\n" + "=" * 78)
    print("5) 振幅 30 %、SNR 20 —— 手法 × 組織の表(残留不均一つき)")
    print("=" * 78)
    sc, obs = scene_with(ph, 0.30)
    rows, out = [], {}
    hist: list = []
    print("   %-36s  CSF      GM      WM    GM+WM   | CV(b̂/b)" % "手法")
    for m in METHODS:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")            # FITPACK 系の握り潰し警告は本文で扱う
            r = evaluate(m, obs, sc, **({"history": hist} if m == "wells_bspline" else {}))
        e = r["err"]
        out[m] = r
        cv = "%.2f" % r["cv"] if np.isfinite(r["cv"]) else "-"
        name = NAMES[m] + (" a=%.2f" % r["best_a"] if r["best_a"] is not None else "")
        rows.append([name, "%+.2f" % e["csf"], "%+.2f" % e["gm"], "%+.2f" % e["wm"],
                     "%+.2f" % e["gm+wm"], cv])
        print("   %-36s %+7.2f %+7.2f %+7.2f %+7.2f   | %s" % (
            name, e["csf"], e["gm"], e["wm"], e["gm+wm"], cv))
    for k, bh in enumerate(hist, 1):
        seg = segment(obs / bh, sc["mask"])
        e = area_errors(seg, sc["truth"])
        ratio = (bh / (sc["field"] / sc["field"][sc["mask"]].mean()))[sc["mask"]]
        print("     格子 B スプライン 反復 %d 回目: GM %+.2f %% / WM %+.2f %% / CV %.2f %%" % (
            k, e["gm"], e["wm"], 100 * ratio.std() / ratio.mean()))

    # FITPACK の平滑係数を小さくすると台の外で発散する(公開経路の穴の実測)
    mask = sc["mask"]
    model = np.ones(obs.shape)
    for k in (1, 2, 3):
        model[ph["labels"] == k] = obs[ph["labels"] == k].mean()
    resid = np.where(mask, np.log(obs) - np.log(model), 0.0)
    fp_rows = []
    for s in (None, 20.0, 5.0):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            d = smooth_fitpack(resid, mask, sc, smooth=s)
        b_log = np.log(sc["field"] / sc["field"][mask].mean())
        rms = float(np.sqrt(np.mean(((d - d[mask].mean()) - b_log)[mask] ** 2)))
        fp_rows.append((s, float(np.abs(d[mask]).max()), float(np.abs(d).max()), rms))
        print("     fit_bspline_surface smooth=%-5s  |log b̂| 最大: 頭の内側 %.2g / 全体 %.2g  真の log b との RMS %.3f" % (
            s, fp_rows[-1][1], fp_rows[-1][2], rms))

    figs.save_table("methods_table", ["手法", "CSF [%]", "GM [%]", "WM [%]", "GM+WM [%]", "CV b̂/b [%]"],
                    rows, title="振幅 30 %・SNR 20: 補正法ごとの面積誤差と残留不均一",
                    caption="素朴な低域推定は解剖を場と誤認する。dc_homomorphic は組織コントラストごと潰す。")
    b_true = sc["field"] / sc["field"][mask].mean()
    figs.save_grid("bias_map",
                   [b_true, out["naive_poly2"]["bhat"], out["wells_bspline"]["bhat"],
                    np.where(mask, out["naive_poly2"]["bhat"] / b_true - 1, 0),
                    np.where(mask, out["wells_poly2"]["bhat"] / b_true - 1, 0),
                    np.where(mask, out["wells_bspline"]["bhat"] / b_true - 1, 0)],
                   ["真の b(x)", "b̂ 素朴: log I に 2 次多項式面", "b̂ Wells 型: 格子 B スプライン",
                    "b̂/b - 1(素朴 多項式、CV %.1f %%)" % out["naive_poly2"]["cv"],
                    "b̂/b - 1(Wells 多項式、CV %.1f %%)" % out["wells_poly2"]["cv"],
                    "b̂/b - 1(Wells B スプライン、CV %.1f %%)" % out["wells_bspline"]["cv"]],
                   title="推定した場と残留(振幅 30 %)", ncols=3,
                   signed=[False, False, False, True, True, True])
    figs.save_grid("correction_frames",
                   [_label_rgb(obs, out[m]["seg"]) for m in ("zero", "naive_poly2", "wells_gauss", "wells_bspline")],
                   ["%s(GM %+.1f %%)" % (NAMES[m], out[m]["err"]["gm"])
                    for m in ("zero", "naive_poly2", "wells_gauss", "wells_bspline")],
                   title="補正法ごとの分割(振幅 30 %)", ncols=2)
    return {"table": out, "fitpack": fp_rows}


# --------------------------------------------------------------------------- #
# 6. 場の空間周波数を上げる —— 補正器が組織と区別できなくなる点                    #
# --------------------------------------------------------------------------- #
def section_frequency_sweep(ph: dict) -> dict:
    print("\n" + "=" * 78)
    print("6) 場の空間スケール σ_b 64 -> 4 px(振幅 30 %)—— 補正器の周波数の崖")
    print("=" * 78)
    sigmas = (64.0, 32.0, 16.0, 8.0, 4.0)
    methods = ("zero", "wells_poly2", "wells_gauss", "wells_bspline", "ideal")
    res = {m: {"gm": [], "wm": [], "cv": []} for m in methods}
    print("   σ_b | GM 誤差: ゼロ点  W-poly2  W-gauss  W-bspl   理想 | CV: poly2 gauss bspl")
    for s in sigmas:
        sc, obs = scene_with(ph, 0.30, kind="noise", sigma_b=s)
        for m in methods:
            r = evaluate(m, obs, sc)
            res[m]["gm"].append(r["err"]["gm"])
            res[m]["wm"].append(r["err"]["wm"])
            res[m]["cv"].append(r["cv"])
        print("   %3.0f | " % s + "  ".join("%+7.2f" % res[m]["gm"][-1] for m in methods)
              + " | %5.1f %5.1f %5.1f" % (res["wells_poly2"]["cv"][-1], res["wells_gauss"]["cv"][-1],
                                          res["wells_bspline"]["cv"][-1]))
    cliffs = {m: first_cliff(sigmas, res[m]["gm"]) for m in methods}
    print("  崖(σ_b を細かくして GM 誤差が ±%.0f %% を超える最初のスケール): " % CLIFF
          + "  ".join("%s %s px" % (m, cliffs[m]) for m in methods))
    print("  ★σ_b 4 px(皮質リボンの太さ)では理想補正以外すべて壊れる: 場と組織は同じ帯域に居る。")

    # 補正器のスケールを振る —— 場なし(自傷)と場あり σ_b 16 px
    print("\n  格子 B スプラインの制御点間隔 h を振る(場なし = 自傷 / 場 30 %・σ_b 16 px):")
    hs = (64.0, 32.0, 16.0, 8.0)
    self_gm, self_wm, with_gm = [], [], []
    sc0, obs0 = scene_with(ph, 0.0)
    sc1, obs1 = scene_with(ph, 0.30, kind="noise", sigma_b=16.0)
    print("     h  | 場なし GM     WM  | 場あり GM")
    for h in hs:
        r0 = evaluate("wells_bspline", obs0, sc0, h=h)
        r1 = evaluate("wells_bspline", obs1, sc1, h=h)
        self_gm.append(r0["err"]["gm"])
        self_wm.append(r0["err"]["wm"])
        with_gm.append(r1["err"]["gm"])
        print("   %4.0f | %+6.2f %+6.2f | %+6.2f" % (h, self_gm[-1], self_wm[-1], with_gm[-1]))
    floor = evaluate("ideal", obs0, sc0)["err"]["gm"]
    print("  ★予想は「細かい格子は場のない画像の組織を場と誤認して自傷する」。実測: h %.0f px でも"
          " 自傷は床(理想補正 %+.2f %%)から %+.2f %% —— Wells 型は分割の残差を平滑するので解剖は残差に"
          "ほとんど出ない。**外れた**。粗い側は h %.0f px で場 σ_b 16 px を取り逃して GM %+.1f %%。" % (
              hs[-1], floor, self_gm[-1] - floor, hs[0], with_gm[0]))

    figs.save_plot("frequency_sweep",
                   [(NAMES[m], list(sigmas), res[m]["gm"]) for m in methods],
                   xlabel="場の空間スケール σ_b [px](左ほど細かい)", ylabel="GM の面積誤差 [%]",
                   title="場を細かくすると補正器が基底の順に壊れる(振幅 30 %)",
                   caption="σ_b 4 px は皮質リボンの太さ。そこで場と組織は区別できない。")
    figs.save_plot("estimator_scale",
                   [("場なし GM(自傷)", list(hs), self_gm), ("場なし WM(自傷)", list(hs), self_wm),
                    ("場 30 %・σ_b 16 px の GM", list(hs), with_gm)],
                   xlabel="格子 B スプラインの制御点間隔 h [px]", ylabel="面積誤差 [%]",
                   title="補正器のスケール: 粗いと場を取り逃す。細かくしても Wells 型の自傷は小さい",
                   caption="場なしの線は雑音の床(理想補正でも同じ値)。予想した『細かい格子の自傷』は出なかった。")
    return {"sigmas": sigmas, "res": res, "cliffs": cliffs, "self_gm": self_gm,
            "self_wm": self_wm, "with_gm": with_gm, "hs": hs, "floor": floor}


# --------------------------------------------------------------------------- #
# 7. SNR を落とす —— Rician の底上げは補正では直らない                            #
# --------------------------------------------------------------------------- #
def section_snr_sweep(ph: dict) -> dict:
    print("\n" + "=" * 78)
    print("7) SNR 30 -> 5(振幅 20 %)—— 雑音の崖は場の補正では動かない")
    print("=" * 78)
    snrs = (30.0, 20.0, 15.0, 10.0, 7.0, 5.0)
    methods = ("zero", "wells_gauss", "wells_bspline", "ideal")
    res = {m: {"csf": [], "gm": [], "wm": []} for m in methods}
    noise_only = {"csf": [], "gm": [], "wm": []}
    from math import erf, sqrt
    tr = ph["truth"]
    d_gw = MEAN["wm"] - MEAN["gm"]
    pred_gm = []                      # ガウス裾の予測: 中点固定、両側とも Φ(-d/2σ) が越える
    print("   SNR | 場なし CSF     GM  予測GM | ゼロ点 CSF     GM      WM | W-gauss GM | W-bspl GM | 理想 GM")
    for snr in snrs:
        sigma = MEAN["wm"] / snr
        phi = 0.5 * (1 + erf(-d_gw / (2 * sigma) / sqrt(2)))
        pred_gm.append(100.0 * phi * (tr["wm"] - tr["gm"]) / tr["gm"])
        sc0, obs0 = scene_with(ph, 0.0, snr)
        e0 = evaluate("zero", obs0, sc0)["err"]
        for k in noise_only:
            noise_only[k].append(e0[k])
        sc, obs = scene_with(ph, 0.20, snr)
        for m in methods:
            e = evaluate(m, obs, sc)["err"]
            for k in ("csf", "gm", "wm"):
                res[m][k].append(e[k])
        z = res["zero"]
        print("   %3.0f | %+6.2f %+6.2f %+6.2f | %+6.2f %+6.2f %+6.2f | %+6.2f     | %+6.2f    | %+6.2f" % (
            snr, e0["csf"], e0["gm"], pred_gm[-1], z["csf"][-1], z["gm"][-1], z["wm"][-1],
            res["wells_gauss"]["gm"][-1], res["wells_bspline"]["gm"][-1], res["ideal"]["gm"][-1]))
    cliff_csf = first_cliff(snrs, noise_only["csf"])
    cliff_gm_ideal = first_cliff(snrs, res["ideal"]["gm"])
    print("  崖: 場なしでも CSF が ±%.0f %% を超える SNR %s / 理想補正でも GM が超える SNR %s" % (
        CLIFF, cliff_csf, cliff_gm_ideal))
    print("  ★場なしでも SNR %.0f で GM %+.1f %%: 取り違えの割合は GM->WM と WM->GM で同じでも、WM の面積が"
          " GM の %.2f 倍あるので**小さい組織の相対誤差に現れる**(ガウス裾の予測 %+.1f %%)。" % (
              snrs[2], noise_only["gm"][2], tr["wm"] / tr["gm"], pred_gm[2]))
    print("  Rician 雑音は暗い CSF を底上げして GM に流す(SNR 5 で CSF %+.1f %%)—— 場の補正は雑音を直さない。" % (
        noise_only["csf"][-1]))
    figs.save_plot("snr_sweep",
                   [("場なし GM(雑音だけ)", list(snrs), noise_only["gm"]),
                    ("ガウス裾の予測 GM", list(snrs), pred_gm),
                    ("ゼロ点 GM(場 20 %)", list(snrs), res["zero"]["gm"]),
                    ("Wells ガウス GM", list(snrs), res["wells_gauss"]["gm"]),
                    ("Wells B スプライン GM", list(snrs), res["wells_bspline"]["gm"]),
                    ("理想補正 GM", list(snrs), res["ideal"]["gm"])],
                   xlabel="SNR(WM 輝度 / σ)", ylabel="面積誤差 [%]",
                   title="SNR を落とす: 雑音の崖は補正で動かない(振幅 20 %)")
    return {"snrs": snrs, "res": res, "noise_only": noise_only, "pred_gm": pred_gm,
            "cliff_csf": cliff_csf, "cliff_gm_ideal": cliff_gm_ideal}


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("MRI バイアス場と組織面積 —— fullseye %s、%d px 角、seed %d" % (
        getattr(fs, "__version__", "?"), N_PIX, SEED))
    ph = make_phantom()
    s1 = section_zero_point(ph)
    s2 = section_amplitude_sweep(ph)
    s5 = section_table30(ph)
    s6 = section_frequency_sweep(ph)
    s7 = section_snr_sweep(ph)

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    z = s2["res"]["zero"]
    i30 = s2["i30"]
    print("  ゼロ点 30 %%: GM %+.2f %% / WM %+.2f %% / GM+WM %+.2f %%(合計は保存されて誤差が隠れる)" % (
        z["gm"][i30], z["wm"][i30], z["gm+wm"][i30]))
    print("  崖(GM ±%.0f %%): 幾何予測 %.1f %% vs 実測 %.1f %%" % (CLIFF, s2["cliff_pred"], s2["cliff_meas"]))
    print("  周波数の崖: " + "  ".join("%s %s px" % (m, s6["cliffs"][m]) for m in s6["cliffs"]))
    print("  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("  図のエラー: %s" % figs.errors())

    # --- 所見を固定する(壊れたら鳴る) --------------------------------------- #
    e0 = s1["noise_only"]
    assert all(abs(e0[k]) < 2.0 for k in TISSUES), e0            # SNR 20 の雑音だけなら 2 % 以内
    assert abs(s1["field_only"]["gm"]) > CLIFF                     # 場だけで壊れる
    assert z["gm"][i30] > CLIFF and z["wm"][i30] < -1.0, (z["gm"][i30], z["wm"][i30])   # 逆符号
    assert abs(z["gm+wm"][i30]) < 1.0, z["gm+wm"][i30]            # 足すと隠れる
    assert abs(z["csf"][i30]) < 1.0, z["csf"][i30]                # CSF は場で動かない
    assert s2["cliff_meas"] is not None and s2["cliff_pred"] is not None
    assert s2["cliff_meas"] < s2["cliff_pred"]                     # 大津は幾何予測より手前で壊れる
    assert s1["field_only"]["gm"] < 0 < s1["field30"]["gm"]        # 雑音の有無で符号が反転
    r = s2["res"]
    assert r["naive_poly2"]["gm"][0] > 50.0                        # 素朴な多項式は解剖を場と誤認
    assert r["naive_gauss"]["gm"][0] > CLIFF                       # 素朴なガウスも自傷
    floor = r["ideal"]["gm"][0]
    assert all(abs(r[m]["gm"][0] - floor) < 1.0 for m in ("wells_poly2", "wells_gauss", "wells_bspline"))
    assert all(abs(r[m]["gm"][-1]) < 3.0 for m in ("wells_poly2", "wells_gauss", "wells_bspline", "ideal"))
    assert abs(s6["res"]["ideal"]["gm"][-1]) < 3.0                # 理想補正は周波数に依らない
    assert all(abs(s6["res"][m]["gm"][-1]) > CLIFF for m in ("wells_poly2", "wells_gauss", "wells_bspline"))
    assert s6["cliffs"]["wells_bspline"] < s6["cliffs"]["wells_gauss"] < s6["cliffs"]["wells_poly2"]
    assert abs(s6["self_gm"][-1] - s6["floor"]) < 1.0             # 細かい格子でも Wells 型は自傷しない
    assert s6["with_gm"][0] > CLIFF                                # 粗い格子は細かい場を取り逃す
    tb = s5["table"]
    assert tb["wells_bspline"]["cv"] < tb["zero"]["cv"] * 0.3
    assert max(abs(tb["homo"]["err"][t]) for t in TISSUES) > 50.0  # 同型フィルタ op は組織ごと潰す
    assert s5["fitpack"][-1][2] > 1e3                              # FITPACK は台の外で発散
    assert s7["noise_only"]["csf"][-1] > CLIFF                     # Rician の底上げ
    assert s7["noise_only"]["gm"][2] > CLIFF and s7["pred_gm"][2] > 3.0   # 面積の非対称で小さい組織が先に壊れる
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
