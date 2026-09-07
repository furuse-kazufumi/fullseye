# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""MRI のバイアス場が組織体積を歪める量 —— 灰白質と白質は逆向きに壊れ、足すと隠れる。

脳 MRI(T1 強調)から灰白質(GM)/白質(WM)/脳脊髄液(CSF)の体積を測る、という
仕事です(萎縮の経過観察・研究コホートの標準的な数字)。MRI の受信コイルには
感度の空間分布があり、画像は**滑らかな乗算場 b(x)**(バイアス場、強度不均一)を
掛けられて出てきます。組織の見分けは輝度しかないので、場が組織のコントラストに
近づいた所から**明るい側の WM が GM に、暗い側の GM が WM に**流れます。

EXTEND: 実データに差し替えるなら :func:`make_phantom` が返す ``labels``(組織の
真値)と ``obs``(観測画像)の対を、手動分割つきの公開データ(BrainWeb 等)に
置き換えます。**真値の分割が要ります** —— この PoC の主張は「合計は保存されて
組織ごとの誤差が隠れる」なので、全脳体積の真値だけでは測れません。場の真値
``b`` は実データでは手に入らないので、「理想補正」の行は消え、**残留不均一
(b̂/b の変動係数)は測れなくなります** —— 代わりに WM 内の輝度の変動係数を
使うのが常道ですが、それは組織の中の本当の不均一と区別できません。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(大域 3 クラス大津)は場なし・雑音 SNR 20 で GM +0.0 % / WM -0.0 % /
   CSF +0.0 %** —— しきい値が真の輝度の間に落ちる限り、雑音だけでは壊れない。
2. ★★**壊れ方は組織ごとに逆符号で、足すと隠れる**。場の振幅 30 % で
   GM +14.0 % / WM -6.5 % だが GM+WM(いわゆる脳実質)は -0.4 %。臨床で
   いちばん見られる「脳実質体積」は、両方が大きく間違っていても動かない。
3. ★**崖の予測はしきい値固定なら当たり、実際はもっと手前だった**。「しきい値は
   真の輝度の中点に固定・雑音なし」の幾何予測では GM の誤差が 5 % を超える
   振幅は 17.5 %、実測(大津・SNR 20)は 15.0 %。大津は場で広がった山を追って
   しきい値自体を動かすので、幾何予測より先に壊れる。
4. ★**補正は効くが、場のない画像を傷つける**。ガウス低域(σ 24 px)補正は
   振幅 40 % で GM の誤差を +18.9 → +0.8 % に戻す。同じ補正を場のない画像に
   掛けると GM +1.2 % / WM -0.7 % —— 補正器は組織の構造(中心に WM が集まる)
   を場と区別できず、**無い場を「補正」する**。σ を 6 px まで下げると
   GM +9.5 %(場と同じ桁の自傷)。
5. ★**周波数の崖**: 場の空間スケール σ_b を 64 → 4 px と細かくすると、
   2 次多項式面は σ_b 32 px で GM 誤差 5 % を超え、ガウス低域(σ 24 px)は
   16 px で超える。B スプライン反復(N4 風 4 回)は 8 px まで持つが、
   4 px(皮質リボンと同じ太さ)では全補正器が壊れ、**真の b で割る理想補正
   だけが正しい**。そこでは「場」と「組織」は同じ帯域に居る。
6. **SNR の崖**: 振幅 20 % で SNR 30 → 5 と落とすと、ゼロ点は SNR 10 で
   CSF +30 % を超える(Rician 雑音の底上げで暗い CSF が GM に流れる)。
   場の補正は雑音を直さないので、補正後も SNR 7 以下では GM が 5 % を超える。
7. **残留不均一(b̂/b の変動係数)**: 振幅 30 % で 補正なし 8.6 % →
   多項式 1.4 % / ガウス低域 1.1 % / B スプライン反復 0.9 %。★ただし
   マスクを知らない op(``hx_fit_surface2`` をそのまま)は 3.4 % で、
   頭の外の暗い背景を場と一緒に当てはめてしまう。

【グラウンドトゥルース】
頭部は**閉形式の楕円殻**(頭蓋 / CSF 殻 / 皮質リボン / WM)で、皮質と WM の
境界は角度の正弦で皺を付ける。脳室(CSF)と深部灰白質(GM)を楕円で埋める。
組織の面積はラベル画像の画素数で**幾何から決まる**。場 b(x) は表面コイル型の
ガウス(主掃引)または σ_b でぼかした乱数場(周波数掃引)で、頭の内側で平均 1・
peak-to-peak = 振幅に正規化する。雑音は Rician(実部・虚部に独立ガウス、
SNR = WM 輝度 / σ)。すべての乱数は ``np.random.default_rng(SEED)`` で固定。

来歴(公開文献のみ): バイアス場補正の総説 Vovk, Pernus & Likar (2007) IEEE TMI;
N3 = Sled, Zijdenbos & Evans (1998) IEEE TMI; N4 = Tustison et al. (2010) IEEE TMI;
分割と交互に場を推定する反復 = Wells et al. (1996) IEEE TMI; Rician 雑音 =
Gudbjartsson & Patz (1995) MRM; 多値大津 = Otsu (1979) / Liao, Chen & Chung (2001)。
BrainWeb ファントム(Collins et al. 1998)の考え方(既知ラベル + 場 + 雑音)に倣う
が、ここでは 2-D の楕円殻で自前に作る。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
N_PIX = 256                 # 視野 [px](1 px = 1 mm と読む)
SEED = 7
MEAN = {"bg": 0.03, "csf": 0.22, "gm": 0.48, "wm": 0.72, "skull": 0.85}  # T1 風の輝度
LAB = {"bg": 0, "csf": 1, "gm": 2, "wm": 3, "skull": 4}
TISSUES = ("csf", "gm", "wm")                                     # 分割する 3 組織
SNR_DEFAULT = 20.0          # SNR = WM 輝度 / 雑音 σ
SIGMA_GAUSS = 24.0          # ガウス低域補正器の σ [px]
N_ITER = 4                  # B スプライン反復の回数
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
    hi = float(v.max())
    v = np.clip(v / hi, 0.0, 1.0) if hi > 0 else v
    n = v.size
    side = int(np.ceil(np.sqrt(n)))
    pad = np.concatenate([v, np.repeat(v[-1], side * side - n)]).reshape(side, side)
    q = fs.apply(pad, "xsk2_multiotsu", a=0.1)          # a<=0.5 -> 3 クラス
    return np.rint(q.ravel()[:n] * 2).astype(np.int32)


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


# --------------------------------------------------------------------------- #
# バイアス場の補正器 —— 対数領域の低周波推定 4 種 + 理想                          #
# --------------------------------------------------------------------------- #
def _center(logb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    return logb - logb[mask].mean()


def est_poly2(obs: np.ndarray, mask: np.ndarray, sc: dict) -> np.ndarray:
    """log I をマスク内で 2 次多項式面に最小二乗(``fit_poly_surface``)。"""
    x = (sc["xx"] / (N_PIX - 1)) * 2 - 1
    y = (sc["yy"] / (N_PIX - 1)) * 2 - 1
    z = np.log(obs[mask])
    model = _LED.fit_poly_surface(x[mask], y[mask], z, degree=2)
    fit = np.asarray(_LED.eval_poly_surface(model, x, y), np.float64)
    return np.exp(_center(fit, mask))


def est_poly2_op(obs: np.ndarray, mask: np.ndarray, sc: dict) -> np.ndarray:
    """``hx_fit_surface2`` op をそのまま(マスクを知らない)。

    op は画像全体に当てはめ、出力を [0,1] に正規化して尺度を捨てるので、
    (1) 頭の外は log I の頭内平均で埋め、(2) 出力を log I に回帰して尺度を戻す。
    """
    logi = np.log(obs)
    filled = np.where(mask, logi, logi[mask].mean())
    lo, hi = float(filled.min()), float(filled.max())
    surf = fs.apply((filled - lo) / (hi - lo), "hx_fit_surface2")
    A = np.stack([surf[mask], np.ones(int(mask.sum()))], 1)
    coef, *_ = np.linalg.lstsq(A, logi[mask], rcond=None)
    return np.exp(_center(coef[0] * surf, mask))


def est_gauss(obs: np.ndarray, mask: np.ndarray, sc: dict,
              sigma: float = SIGMA_GAUSS) -> np.ndarray:
    """log I のマスク付きガウス低域(正規化畳み込み)。★公開経路に無い処理。"""
    logi = np.where(mask, np.log(obs), 0.0)
    num = ndimage.gaussian_filter(logi, sigma)
    den = ndimage.gaussian_filter(mask.astype(np.float64), sigma)
    fit = num / np.maximum(den, 1e-6)
    return np.exp(_center(fit, mask))


def est_iter_bspline(obs: np.ndarray, mask: np.ndarray, sc: dict,
                     n_iter: int = N_ITER, step: int = 6, history: list | None = None) -> np.ndarray:
    """分割と交互に場を推定する反復(Wells 型の E-M を N4 風に B スプラインで)。

    各反復: 現在の補正画像を 3 クラスに分割 -> クラス平均の区分定数モデル ->
    log 残差 = log(補正画像) - log(モデル) -> ``fit_bspline_surface`` で平滑 ->
    log b̂ に足す。平滑係数は残差の隣接差から雑音 σ を推定して ``m·σ²``。
    """
    logb = np.zeros(obs.shape)
    sub = np.zeros(obs.shape, bool)
    sub[::step, ::step] = True
    sub &= mask
    ys, xs = np.nonzero(sub)
    for _ in range(n_iter):
        corr = obs / np.exp(logb)
        seg = segment(corr, mask)
        model = np.ones(obs.shape)
        for k in (1, 2, 3):
            sel = seg == k
            if sel.any():
                model[sel] = corr[sel].mean()
        resid = np.where(mask, np.log(np.maximum(corr, 1e-6)) - np.log(model), 0.0)
        d = np.diff(resid[mask])
        sig = 1.4826 * float(np.median(np.abs(d - np.median(d)))) / np.sqrt(2.0)
        z = resid[ys, xs]
        tck = _LED.fit_bspline_surface(xs.astype(np.float64), ys.astype(np.float64), z,
                                       smooth=len(z) * sig * sig)
        delta = np.asarray(_LED.eval_bspline_surface(
            tck, np.arange(N_PIX, dtype=np.float64), np.arange(N_PIX, dtype=np.float64),
            grid=True), np.float64).T          # grid=True は (len(x), len(y)) で返る
        logb = _center(logb + delta, mask)
        if history is not None:
            history.append(np.exp(logb))
    return np.exp(logb)


def est_ideal(obs: np.ndarray, mask: np.ndarray, sc: dict) -> np.ndarray:
    return sc["field"] / sc["field"][mask].mean()


def corrected_homomorphic(obs: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """``dc_homomorphic`` op(周波数領域で log I の低域を減衰)。b̂ は出ない。"""
    v = np.where(mask, obs, 0.0)
    v = v / float(v.max())
    return fs.apply(v, "dc_homomorphic", a=0.1, b=0.0)


ESTIMATORS = {
    "poly2": est_poly2, "poly2_op": est_poly2_op, "gauss": est_gauss,
    "iter": est_iter_bspline, "ideal": est_ideal,
}
NAMES = {"zero": "ゼロ点(補正なし)", "poly2": "2 次多項式面", "poly2_op": "hx_fit_surface2 そのまま",
         "gauss": "ガウス低域 σ%.0f px" % SIGMA_GAUSS, "homo": "同型フィルタ op",
         "iter": "B スプライン反復 %d 回" % N_ITER, "ideal": "理想補正(真の b)"}


def evaluate(method: str, obs: np.ndarray, sc: dict, **kw) -> dict:
    """1 手法を掛けて {誤差, 残留 CV, 補正画像, b̂} を返す。"""
    mask = sc["mask"]
    b_true = sc["field"] / sc["field"][mask].mean()
    if method == "zero":
        corr, bhat = obs, np.ones_like(obs)
    elif method == "homo":
        corr, bhat = corrected_homomorphic(obs, mask), None
    else:
        bhat = ESTIMATORS[method](obs, mask, sc, **kw)
        corr = obs / bhat
    seg = segment(corr, mask)
    out = {"err": area_errors(seg, sc["truth"]), "seg": seg, "corr": corr, "bhat": bhat}
    if bhat is not None:
        ratio = (bhat / b_true)[mask]
        out["cv"] = 100.0 * float(ratio.std() / ratio.mean())
    else:
        out["cv"] = float("nan")
    return out


def scene_with(ph: dict, amplitude: float, snr: float = SNR_DEFAULT, **field_kw) -> tuple[dict, np.ndarray]:
    sc = dict(ph)
    sc["field"] = make_field(ph["mask"], amplitude, **field_kw)
    obs = observe(ph["clean"], sc["field"], snr)
    return sc, obs


def predict_zero_errors(ph: dict, field: np.ndarray) -> dict:
    """幾何予測: しきい値を真の輝度の中点に固定・雑音なしで、場だけが動かす面積。"""
    t_cg = 0.5 * (MEAN["csf"] + MEAN["gm"])
    t_gw = 0.5 * (MEAN["gm"] + MEAN["wm"])
    v = ph["clean"] * field
    seg = np.zeros(v.shape, np.int32)
    m = ph["mask"]
    seg[m] = 1 + (v[m] > t_cg) + (v[m] > t_gw)
    return area_errors(seg, ph["truth"])


def first_cliff(xs, errs, thr=CLIFF):
    """|誤差| が thr を初めて超える x(超えなければ None)。"""
    for x, e in zip(xs, errs):
        if abs(e) > thr:
            return x
    return None


def _label_rgb(img: np.ndarray, seg: np.ndarray) -> np.ndarray:
    base = np.clip(img / max(float(img.max()), 1e-6), 0, 1)
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
    rows = []
    out = {}
    for label, amp, snr in (("場なし・雑音なし", 0.0, 0.0), ("場なし・SNR 20", 0.0, SNR_DEFAULT),
                            ("場 30 %・雑音なし", 0.30, 0.0), ("場 30 %・SNR 20", 0.30, SNR_DEFAULT)):
        sc, obs = scene_with(ph, amp, snr)
        r = evaluate("zero", obs, sc)
        e = r["err"]
        rows.append([label] + ["%+.2f" % e[k] for k in ("csf", "gm", "wm", "gm+wm")])
        out[label] = (sc, obs, r)
        print("   %-18s  CSF %+6.2f %%  GM %+6.2f %%  WM %+6.2f %%  | GM+WM %+6.2f %%" % (
            label, e["csf"], e["gm"], e["wm"], e["gm+wm"]))
    figs.save_table("controls", ["条件", "CSF [%]", "GM [%]", "WM [%]", "GM+WM [%]"], rows,
                    title="対照群: 場と雑音を別々に止める(ゼロ点の面積誤差)",
                    caption="雑音だけでは壊れず、場だけで GM と WM が逆向きに動く。")

    sc, obs, r = out["場 30 %・SNR 20"]
    ideal = evaluate("ideal", obs, sc)
    figs.save_grid("scene",
                   [_label_rgb(ph["clean"], ph["labels"] * (ph["labels"] <= 3)), sc["field"],
                    obs, _label_rgb(obs, r["seg"]), _label_rgb(obs, ideal["seg"]),
                    (r["seg"] - ph["labels"]) * (ph["mask"] & (r["seg"] != ph["labels"]))],
                   ["真値ラベル(CSF/GM/WM、1 px = 1 mm)", "バイアス場 b(x)(振幅 30 %)",
                    "観測(Rician、SNR 20)", "ゼロ点の分割(GM %+.1f %% / WM %+.1f %%)" % (
                        r["err"]["gm"], r["err"]["wm"]),
                    "理想補正の分割(GM %+.1f %% / WM %+.1f %%)" % (
                        ideal["err"]["gm"], ideal["err"]["wm"]),
                    "誤り(+: 明るい組織へ / -: 暗い組織へ)"],
                   title="脳スライス風ファントムにバイアス場を掛ける", ncols=3,
                   signed=[False, False, False, False, False, True])
    return {"noise_only": out["場なし・SNR 20"][2]["err"], "field30": r["err"]}


# --------------------------------------------------------------------------- #
# 2-3. 振幅を振る —— 逆符号・合計保存・崖の予測                                  #
# --------------------------------------------------------------------------- #
def section_amplitude_sweep(ph: dict) -> dict:
    print("\n" + "=" * 78)
    print("2-3) 場の振幅 0 -> 40 % —— 組織ごとに逆符号、GM+WM は動かない、崖の予測")
    print("=" * 78)
    amps = np.arange(0.0, 0.401, 0.05)
    methods = ("zero", "poly2", "gauss", "homo", "iter", "ideal")
    res = {m: {k: [] for k in ("csf", "gm", "wm", "gm+wm", "cv")} for m in methods}
    pred = {k: [] for k in ("gm", "wm")}
    print("   振幅   | ゼロ点 CSF     GM      WM   GM+WM | 予測 GM     WM | 補正後 GM: poly2  gauss   homo   iter  ideal")
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
        print("   %4.0f %% | %+6.2f %+7.2f %+7.2f %+6.2f | %+6.2f %+6.2f | %+6.2f %+6.2f %+6.2f %+6.2f %+6.2f" % (
            100 * a, z["csf"][-1], z["gm"][-1], z["wm"][-1], z["gm+wm"][-1],
            p["gm"], p["wm"], *line[1:]))

    pct = [100 * a for a in amps]
    cliffs = {}
    for m in methods:
        cg = first_cliff(pct, res[m]["gm"])
        cw = first_cliff(pct, res[m]["wm"])
        cliffs[m] = (cg, cw)
    cliff_pred = (first_cliff(pct, pred["gm"]), first_cliff(pct, pred["wm"]))
    # 幾何予測の崖を 2.5 % 刻みで細かく(掃引は 5 % 刻み)
    fine = np.arange(0.0, 0.401, 0.025)
    pg = [predict_zero_errors(ph, make_field(ph["mask"], a))["gm"] for a in fine]
    cliff_pred_fine = first_cliff([100 * a for a in fine], pg)
    fine_meas = []
    for a in fine:
        sc, obs = scene_with(ph, a)
        fine_meas.append(evaluate("zero", obs, sc)["err"]["gm"])
    cliff_meas_fine = first_cliff([100 * a for a in fine], fine_meas)

    i30 = int(np.argmin(np.abs(amps - 0.30)))
    z = res["zero"]
    print("\n  ★振幅 30 %: GM %+.1f %% / WM %+.1f %% だが GM+WM は %+.1f %% —— 足すと隠れる。" % (
        z["gm"][i30], z["wm"][i30], z["gm+wm"][i30]))
    print("  ★崖(GM 誤差が ±%.0f %% を超える振幅、2.5 %% 刻み): 幾何予測(しきい値固定・雑音なし) %s %% / "
          "実測(大津・SNR %.0f) %s %%" % (CLIFF, cliff_pred_fine, SNR_DEFAULT, cliff_meas_fine))
    print("     予測は「しきい値は動かない」前提。大津は場で広がった山を追ってしきい値を動かすので、"
          "実測のほうが手前で壊れる。")
    print("  補正後の崖(GM / WM、5 %% 刻み): " + "  ".join(
        "%s %s/%s" % (m, cliffs[m][0], cliffs[m][1]) for m in methods))
    print("  振幅 40 %% の GM 誤差: ゼロ点 %+.1f %% -> ガウス低域 %+.1f %% / B スプライン反復 %+.1f %% / 理想 %+.1f %%" % (
        z["gm"][-1], res["gauss"]["gm"][-1], res["iter"]["gm"][-1], res["ideal"]["gm"][-1]))
    print("  ★場なし(振幅 0)に補正を掛けた自傷: poly2 GM %+.2f %% / gauss GM %+.2f %% WM %+.2f %% / iter GM %+.2f %%" % (
        res["poly2"]["gm"][0], res["gauss"]["gm"][0], res["gauss"]["wm"][0], res["iter"]["gm"][0]))

    figs.save_plot("amplitude_sweep_zero",
                   [("GM", pct, z["gm"]), ("WM", pct, z["wm"]), ("CSF", pct, z["csf"]),
                    ("GM+WM(脳実質)", pct, z["gm+wm"]), ("幾何予測 GM", pct, pred["gm"])],
                   xlabel="バイアス場の振幅(peak-to-peak)[%]", ylabel="面積誤差 [%]",
                   title="ゼロ点: GM と WM は逆向きに壊れ、GM+WM は動かない",
                   caption="幾何予測(しきい値固定)より実測(大津)のほうが先に壊れる。")
    figs.save_plot("amplitude_sweep_methods",
                   [(NAMES[m], pct, res[m]["gm"]) for m in ("zero", "poly2", "gauss", "iter", "ideal")],
                   xlabel="バイアス場の振幅 [%]", ylabel="GM の面積誤差 [%]",
                   title="補正後の GM 誤差(場は表面コイル型、SNR %.0f)" % SNR_DEFAULT)
    figs.save_plot("amplitude_residual_cv",
                   [(NAMES[m], pct, res[m]["cv"]) for m in ("zero", "poly2", "gauss", "iter")],
                   xlabel="バイアス場の振幅 [%]", ylabel="残留不均一 CV(b̂/b)[%]",
                   title="補正後に残る場(理想補正は 0)")
    return {"amps": pct, "res": res, "cliffs": cliffs, "cliff_pred": cliff_pred,
            "cliff_pred_fine": cliff_pred_fine, "cliff_meas_fine": cliff_meas_fine, "i30": i30}


# --------------------------------------------------------------------------- #
# 4. 振幅 30 % の表 —— 全手法・全組織・残留不均一                                #
# --------------------------------------------------------------------------- #
def section_table30(ph: dict) -> dict:
    print("\n" + "=" * 78)
    print("4) 振幅 30 %、SNR 20 —— 手法 × 組織の表(残留不均一つき)")
    print("=" * 78)
    sc, obs = scene_with(ph, 0.30)
    rows, out = [], {}
    hist: list = []
    print("   %-26s  CSF      GM      WM    GM+WM   | CV(b̂/b)" % "手法")
    for m in ("zero", "poly2", "poly2_op", "gauss", "homo", "iter", "ideal"):
        r = evaluate(m, obs, sc, **({"history": hist} if m == "iter" else {}))
        e = r["err"]
        out[m] = r
        cv = "%.2f" % r["cv"] if np.isfinite(r["cv"]) else "-"
        rows.append([NAMES[m], "%+.2f" % e["csf"], "%+.2f" % e["gm"], "%+.2f" % e["wm"],
                     "%+.2f" % e["gm+wm"], cv])
        print("   %-26s %+6.2f  %+6.2f  %+6.2f  %+6.2f   | %s" % (
            NAMES[m], e["csf"], e["gm"], e["wm"], e["gm+wm"], cv))
    # 反復の途中経過
    for k, bh in enumerate(hist, 1):
        seg = segment(obs / bh, sc["mask"])
        e = area_errors(seg, sc["truth"])
        ratio = (bh / (sc["field"] / sc["field"][sc["mask"]].mean()))[sc["mask"]]
        print("     反復 %d 回目: GM %+.2f %% / WM %+.2f %% / CV %.2f %%" % (
            k, e["gm"], e["wm"], 100 * ratio.std() / ratio.mean()))
    figs.save_table("methods_table", ["手法", "CSF [%]", "GM [%]", "WM [%]", "GM+WM [%]", "CV b̂/b [%]"],
                    rows, title="振幅 30 %・SNR 20: 補正法ごとの面積誤差と残留不均一",
                    caption="hx_fit_surface2 op はマスクを知らず頭の外を場と一緒に当てはめる。")
    b_true = sc["field"] / sc["field"][sc["mask"]].mean()
    figs.save_grid("bias_map",
                   [b_true, out["poly2"]["bhat"], out["iter"]["bhat"],
                    np.where(sc["mask"], out["poly2"]["bhat"] / b_true - 1, 0),
                    np.where(sc["mask"], out["iter"]["bhat"] / b_true - 1, 0),
                    np.where(sc["mask"], out["poly2_op"]["bhat"] / b_true - 1, 0)],
                   ["真の b(x)", "b̂ 2 次多項式面", "b̂ B スプライン反復",
                    "b̂/b - 1(多項式、CV %.1f %%)" % out["poly2"]["cv"],
                    "b̂/b - 1(反復、CV %.1f %%)" % out["iter"]["cv"],
                    "b̂/b - 1(hx_fit_surface2、CV %.1f %%)" % out["poly2_op"]["cv"]],
                   title="推定した場と残留(振幅 30 %)", ncols=3,
                   signed=[False, False, False, True, True, True])
    figs.save_grid("correction_frames",
                   [_label_rgb(obs, out["zero"]["seg"]), _label_rgb(obs, out["poly2"]["seg"]),
                    _label_rgb(obs, out["gauss"]["seg"]), _label_rgb(obs, out["iter"]["seg"])],
                   ["%s(GM %+.1f %%)" % (NAMES[m], out[m]["err"]["gm"])
                    for m in ("zero", "poly2", "gauss", "iter")],
                   title="補正法ごとの分割(振幅 30 %)", ncols=2)
    return {"table": out}


# --------------------------------------------------------------------------- #
# 5. 場の空間周波数を上げる —— 補正器が組織と区別できなくなる点                    #
# --------------------------------------------------------------------------- #
def section_frequency_sweep(ph: dict) -> dict:
    print("\n" + "=" * 78)
    print("5) 場の空間スケール σ_b 64 -> 4 px(振幅 30 %)—— 補正器の周波数の崖")
    print("=" * 78)
    sigmas = (64.0, 32.0, 16.0, 8.0, 4.0)
    methods = ("zero", "poly2", "gauss", "iter", "ideal")
    res = {m: {"gm": [], "wm": [], "cv": []} for m in methods}
    print("   σ_b  | GM 誤差: " + "  ".join("%-7s" % m for m in methods) + " | CV: poly2 gauss iter")
    for s in sigmas:
        sc, obs = scene_with(ph, 0.30, kind="noise", sigma_b=s)
        for m in methods:
            r = evaluate(m, obs, sc)
            res[m]["gm"].append(r["err"]["gm"])
            res[m]["wm"].append(r["err"]["wm"])
            res[m]["cv"].append(r["cv"])
        print("   %4.0f | " % s + "  ".join("%+7.2f" % res[m]["gm"][-1] for m in methods)
              + " | %5.1f %5.1f %5.1f" % (res["poly2"]["cv"][-1], res["gauss"]["cv"][-1], res["iter"]["cv"][-1]))
    cliffs = {m: first_cliff(sigmas, res[m]["gm"]) for m in methods}
    print("  崖(σ_b を細かくして GM 誤差が ±%.0f %% を超える最初のスケール): " % CLIFF
          + "  ".join("%s %s px" % (m, cliffs[m]) for m in methods))
    print("  ★σ_b 4 px(皮質リボンの太さ)では理想補正以外すべて壊れる: 場と組織は同じ帯域に居る。")

    # 補正器のスケール σ_s を振る —— 場なし(自傷)と場あり
    print("\n  ガウス低域の σ_s を振る(場なし = 補正器の自傷 / 場 30 %・σ_b 32 px):")
    scales = (6.0, 12.0, 24.0, 48.0, 96.0)
    self_gm, self_wm, with_gm = [], [], []
    sc0, obs0 = scene_with(ph, 0.0)
    sc1, obs1 = scene_with(ph, 0.30, kind="noise", sigma_b=32.0)
    print("   σ_s  | 場なし GM     WM  | 場あり GM")
    for s in scales:
        r0 = evaluate("gauss", obs0, sc0, sigma=s)
        r1 = evaluate("gauss", obs1, sc1, sigma=s)
        self_gm.append(r0["err"]["gm"])
        self_wm.append(r0["err"]["wm"])
        with_gm.append(r1["err"]["gm"])
        print("   %4.0f | %+6.2f %+6.2f | %+6.2f" % (s, self_gm[-1], self_wm[-1], with_gm[-1]))
    print("  ★σ_s 6 px の自傷 GM %+.1f %% —— 場のない画像を『補正』して場と同じ桁で壊す。" % self_gm[0])

    figs.save_plot("frequency_sweep",
                   [(NAMES[m], list(sigmas), res[m]["gm"]) for m in methods],
                   xlabel="場の空間スケール σ_b [px](左ほど細かい)", ylabel="GM の面積誤差 [%]",
                   title="場を細かくすると補正器が順に壊れる(振幅 30 %)",
                   caption="σ_b 4 px は皮質リボンの太さ。そこで場と組織は区別できない。")
    figs.save_plot("estimator_scale",
                   [("場なし GM(自傷)", list(scales), self_gm), ("場なし WM(自傷)", list(scales), self_wm),
                    ("場 30 %・σ_b 32 px の GM", list(scales), with_gm)],
                   xlabel="補正器のガウス σ_s [px]", ylabel="面積誤差 [%]",
                   title="補正器のスケール: 細かいと組織を場と誤認し、粗いと場を取り逃す")
    return {"sigmas": sigmas, "res": res, "cliffs": cliffs, "self_gm": self_gm,
            "self_wm": self_wm, "with_gm": with_gm, "scales": scales}


# --------------------------------------------------------------------------- #
# 6. SNR を落とす —— Rician の底上げは補正では直らない                            #
# --------------------------------------------------------------------------- #
def section_snr_sweep(ph: dict) -> dict:
    print("\n" + "=" * 78)
    print("6) SNR 30 -> 5(振幅 20 %)—— 雑音の崖は場の補正では動かない")
    print("=" * 78)
    snrs = (30.0, 20.0, 15.0, 10.0, 7.0, 5.0)
    methods = ("zero", "gauss", "iter", "ideal")
    res = {m: {"csf": [], "gm": [], "wm": []} for m in methods}
    noise_only = {"csf": [], "gm": [], "wm": []}
    print("   SNR | 場なし CSF    GM | ゼロ点 CSF    GM     WM | gauss GM | iter GM | ideal GM")
    for snr in snrs:
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
        print("   %3.0f | %+6.2f %+6.2f | %+6.2f %+6.2f %+6.2f | %+6.2f | %+6.2f | %+6.2f" % (
            snr, e0["csf"], e0["gm"], z["csf"][-1], z["gm"][-1], z["wm"][-1],
            res["gauss"]["gm"][-1], res["iter"]["gm"][-1], res["ideal"]["gm"][-1]))
    cliff_csf = first_cliff(snrs, noise_only["csf"])
    cliff_gm_ideal = first_cliff(snrs, res["ideal"]["gm"])
    print("  崖: 場なしでも CSF が ±%.0f %% を超える SNR %s / 理想補正でも GM が超える SNR %s" % (
        CLIFF, cliff_csf, cliff_gm_ideal))
    print("  Rician 雑音は暗い CSF を底上げして GM に流す —— 場の補正は雑音を直さない。")
    figs.save_plot("snr_sweep",
                   [("場なし CSF(雑音だけ)", list(snrs), noise_only["csf"]),
                    ("ゼロ点 GM(場 20 %)", list(snrs), res["zero"]["gm"]),
                    ("ガウス低域 GM", list(snrs), res["gauss"]["gm"]),
                    ("B スプライン反復 GM", list(snrs), res["iter"]["gm"]),
                    ("理想補正 GM", list(snrs), res["ideal"]["gm"])],
                   xlabel="SNR(WM 輝度 / σ)", ylabel="面積誤差 [%]",
                   title="SNR を落とす: 雑音の崖は補正で動かない(振幅 20 %)")
    return {"snrs": snrs, "res": res, "noise_only": noise_only,
            "cliff_csf": cliff_csf, "cliff_gm_ideal": cliff_gm_ideal}


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("MRI バイアス場と組織面積 —— fullseye %s、%d px 角、seed %d" % (
        getattr(fs, "__version__", "?"), N_PIX, SEED))
    ph = make_phantom()
    s1 = section_zero_point(ph)
    s2 = section_amplitude_sweep(ph)
    s4 = section_table30(ph)
    s5 = section_frequency_sweep(ph)
    s6 = section_snr_sweep(ph)

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    z = s2["res"]["zero"]
    i30 = s2["i30"]
    print("  ゼロ点 30 %%: GM %+.1f %% / WM %+.1f %% / GM+WM %+.1f %%(合計は保存されて誤差が隠れる)" % (
        z["gm"][i30], z["wm"][i30], z["gm+wm"][i30]))
    print("  崖(GM ±%.0f %%): 幾何予測 %s %% vs 実測 %s %%" % (
        CLIFF, s2["cliff_pred_fine"], s2["cliff_meas_fine"]))
    print("  周波数の崖: " + "  ".join("%s %s px" % (m, s5["cliffs"][m]) for m in s5["cliffs"]))
    print("  所要 %.1f 秒" % (time.perf_counter() - t0))

    # --- 所見を固定する(壊れたら鳴る) --------------------------------------- #
    e0 = s1["noise_only"]
    assert all(abs(e0[k]) < 1.0 for k in TISSUES), e0            # 雑音だけでは壊れない
    assert z["gm"][i30] > CLIFF and z["wm"][i30] < -CLIFF, (z["gm"][i30], z["wm"][i30])   # 逆符号
    assert abs(z["gm+wm"][i30]) < 1.0, z["gm+wm"][i30]            # 足すと隠れる
    assert s2["cliff_meas_fine"] is not None and s2["cliff_pred_fine"] is not None
    assert s2["cliff_meas_fine"] <= s2["cliff_pred_fine"]        # 大津は予測より手前で壊れる
    assert abs(s2["res"]["gauss"]["gm"][-1]) < CLIFF               # 40 % でも補正は 5 % 以内
    assert abs(s2["res"]["ideal"]["gm"][-1]) < 2.0
    assert abs(s5["res"]["ideal"]["gm"][-1]) < 2.0                # 理想補正は周波数に依らない
    assert all(abs(s5["res"][m]["gm"][-1]) > CLIFF for m in ("poly2", "gauss", "iter"))  # 4 px で全滅
    assert s5["self_gm"][0] > CLIFF                                # 細かい補正器の自傷
    tb = s4["table"]
    assert tb["poly2_op"]["cv"] > tb["poly2"]["cv"]                # マスクを知らない op は残留が大きい
    assert tb["iter"]["cv"] < tb["zero"]["cv"] * 0.3
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
