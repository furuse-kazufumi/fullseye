# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 実物の画像の誤差から薄膜の模型の係数を合わせる —— ただし、データが決めない係数には数を出さない(sim-to-real 較正)。

【問い】「実物の画像を与えられたら、誤差をフィードバックして計算に使う係数を自動的に調整したい」。Si 上の SiO₂ の膜を、
転送行列(``filmoptics``)× 光源の色温度(``spectralrad`` の黒体)× カメラ(利得・ガンマ・周辺減光)の順方向の模型で
描き、実物の顕微分光と顕微鏡写真に合わせる。合わせる前に**多変量解析で、どのつまみが効き、どれが交絡し、データが
何次元しか持たないか**を見て、決まるつまみだけを較正する(``simcal`` 10 op・``multivar`` の計画と感度解析を再利用)。

  1. **計画と多変量**: つまみ 7 本(膜厚 d・Cauchy の A と B・色温度 T・照明の強さ・利得・ガンマ)を L18 の直交表で
     振り、出力 6 個(裸の Si と膜の RGB)の主成分の数を数える。Morris のふるい(``simcal_screen``)で効く/効かない/
     組み合わせを分け、共線性指数(``mv_confounding``、Brun ら 2001)で交絡を物理と照合する —— 照明 × 利得は積しか
     決まらず、1 波長の膜は A^1·d^≈1(光路長 n·d)しか決まらない。
  2. **合成の真値で回収**: 実測と同じ雑音・同じ波長の模型で、作った真値を 3σ_CRLB の内に戻す(G1 型)。膜厚 500 nm を
     4 つの入射角で撮った合成では、分散を無視した貧しい模型の残差を ``simcal_discrepancy``(残差 PCA)が見つける。
  3. **実測の顕微分光で較正(主役)**: 被覆率 100 % の反射スペクトルに d・A・B・NA・利得の 5 本を合わせる。局所の
     共線性(γ > 10)で点推定は出さず、プロファイル尤度(Raue ら 2009)の 95 % 区間で膜厚を出し、論文の基準値と比べる。
     過適合の門(``simcal_validate``、取り置いた波長で)と絶対の χ² の門。
  4. **貧しい模型**: 「直入射・材料表の n」と「分散を無視した一定の n」は、絶対の χ² の門で拒否される(狭い区間が
     基準から外れていても、門が止める)。
  5. **実物の顕微鏡写真(カメラ不明・JPEG)**: 色温度と周辺減光は決まり、膜厚・屈折率・利得・ガンマは組み合わせしか
     決まらない。材料表の n を固定すれば膜厚は狭い区間で出るが、絶対の χ² と残差 PCA が「カメラの分光感度が模型に
     無い」食い違いを見つけて拒否する。
  6. **壊して確かめる探針**(どれも乱数を引かない): 基準値をずらす・雑音を白色の分だけと見誤る・照明を固定する・
     真値を貧しい模型で作る、で各門が逆向きに鳴るか。

【実データ】(どちらも Creative Commons Attribution 4.0 International、CC BY 4.0、
https://creativecommons.org/licenses/by/4.0/ 。``data/thin_film_real/`` の同梱物は既存の薄膜 PoC と共用、出典と改変は
同じ場所の README.md)
  * J. Schwarz, M. Niebauer, L. J. Roemling, A. Pham, M. M. Kolesnik-Gray, P. Evanschitzky, N. Vogel, V. Krstić,
    M. Rommel, A. Hutzler, "Spectro-Spatial Unmixing in Optical Microspectroscopy for Thickness Determination of
    Layered Materials", Adv. Opt. Mater. (2024), doi:10.1002/adom.202402502。データ Zenodo 10.5281/zenodo.13753754。
    改変: 反射率の表は列名を付け直し 6 桁に丸めた(README)。写真は 1920×1080 → 640×360 に縮小し JPEG で保存し直した。
    この PoC では、写真を 40 px 角の 104 区画の平均に、スペクトルを 2 点おきの交互の組に分けて使う。
  * 基準の膜厚 98.5 nm は論文の図 S4a のモデル値 98.8 nm と図 4 の比 1.003046 からの逆算(Fullseye 側)。基準の測り方と
    その不確かさは論文本文を読めておらず未確認(本文は出版社のページで読めなかった。データの記録の要旨は分光エリプソ
    メトリと比べたと書く)。顕微鏡の対物の NA も未確認 —— だから NA は合わせるつまみにした。

【外部真値】論文の基準の膜厚(上)、材料表の SiO₂(Malitson 1965)と Si(Green 2008)、合成の章の作った真値。
雑音の大きさは**別の測定**(同じ論文の被覆率 0 % = 裸の Si のスペクトルを材料表の Si に利得だけで合わせた残差)から
取る —— 合わせる 100 % のスペクトルからは取らない(同じデータで雑音と係数を決めると門が自分を採点する)。
【学習】0。【較正】この PoC そのもの(係数の推定)。収蔵番号 2026.247(2026-10-18 の統合で発行)。

★正直な所見(門に書いた): (a) 98 nm の膜は帯域 440〜950 nm で縞が 1 本未満なので、分散の B は上限しか言えず、
「A を自由にした一定の n」は豊かな模型と同じだけ合う —— 分散を無視した模型を実測で拒否できるのは、n を材料表の値に
固定したときだけ。(b) 実測のスペクトルは偶数番目と奇数番目の画素で残差の大きさが違う(白色の分の 0.27 対 0.33)ので、
取り置きを 1 点おきにすると過適合の門が誤って鳴る。2 点ずつの交互に分けた。(c) 写真のカメラ較正は区間が ±0.15 nm と
狭いのに基準から −12 % 外れる —— 絶対の χ² と残差 PCA が止めるので、区間の狭さを信じてはいけない例として残す。
"""
from __future__ import annotations

import csv
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import filmoptics as FO  # noqa: E402
import fullseye as fs  # noqa: E402  公開経路(fs.ledger.<名前>)から呼ぶ
import materials as MT  # noqa: E402
import matappear as MA  # noqa: E402
from metriccontract import MetricContractError  # noqa: E402

L = fs.ledger
REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"

REAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "thin_film_real")
#: Schwarz ら 2024 の基準の膜厚(図 S4a のモデル値 98.8 nm と図 4 の比 1.003046 から逆算、data/thin_film_real/README.md)。
REF_NM = 98.8 / 1.003046
SOURCE = ("Schwarz et al., Adv. Opt. Mater. (2024) doi:10.1002/adom.202402502; data Zenodo 10.5281/zenodo.13753754 "
          "(CC BY 4.0). Modified: re-labelled and rounded table / micrograph downsized to 640x360, block means.")
CAM_LAM = np.arange(380.0, 781.0, 5.0)        # カメラの模型の波長格子 [nm] —— CIE の等色関数の主な範囲
CAM_WHITE_K = 6504.0                          # カメラの白は 6504 K の黒体に合わせてあると置く(仮定、写真の撮影条件は不明)

FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict = {}


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def _r(v, nd=6):
    """比較・同点判定は丸めた値で(丸めの屑で順や合否を決めない)。"""
    return round(float(v), nd)


#: 取り置き / 学習 の比の門の有意水準。simcal_validate の絶対の χ² の門(fit_consistent_with_noise)の既定と同じ 1e-3。
RATIO_ALPHA = 1e-3


def validate_ratio_f(res, holdout, alpha=RATIO_ALPHA):
    """simcal_validate を、取り置き / 学習 の比の限界を **F 分布から**決めて回す(既定の bootstrap の限界は使わない)。

    ★2026-10-18(統合 wave 7): 既定の限界 1 + τ は学習の残差の 2 乗を画素で再標本化した平均の 95 % 点で、
    実測の比 1.21 に対して 1.25 —— 模型が正しくても偶然で落ち得る、数字をずらせば通る門だった。
    雑音の模型(ガウス、σ 既知)が正しく模型が過適合していなければ、学習の χ² ~ χ²(ν_tr)(ν_tr = n_tr − k)、
    取り置きの χ² ~ χ²(n_ho)(取り置きには当てはめていない)で、両者は独立。simcal_validate の比は
    (χ²_ho / (n_ho − k)) / (χ²_tr / ν_tr) = F · n_ho / (n_ho − k)、F ~ F(n_ho, ν_tr)。
    だから限界 = F の上側 α 分位 × n_ho / (n_ho − k)、p = F の上側確率。σ の定数倍の見誤りは比で消える
    (分子と分母に同じ倍率が掛かる)ので、この門は雑音の床の推定に依らない。仮定は残差の独立: 隣り合う
    波長の相関や偶数・奇数の画素の差があると F は細く出過ぎる(取り置きを 2 点ずつ交互にしているのはそのため)。
    1 回目(既定の bootstrap)で ν と旧来の限界を読み、2 回目で F の限界を渡す。出力次元 dims は 1 回目の値を再利用。
    """
    from scipy.stats import f as _f
    pre = L.simcal_validate(res, holdout)
    g = pre["validation"]["gates"]["fit_consistent_with_noise"]
    nu_tr, n_ho = int(g["train"]["nu"]), int(g["holdout"]["nu"])
    k = int(pre["validation"]["n_free"])
    scale = n_ho / max(1, n_ho - k)
    limit = float(_f.ppf(1.0 - alpha, n_ho, nu_tr)) * scale
    val = L.simcal_validate(res, holdout, tau=limit - 1.0, dims=pre["validation"]["output_dims"])
    ratio = float(val["validation"]["gates"]["holdout_over_train"]["value"])
    val["validation"]["ratio_test"] = {
        "ratio": ratio, "limit": limit, "alpha": float(alpha), "p": float(_f.sf(ratio / scale, n_ho, nu_tr)),
        "nu_holdout": n_ho, "nu_train": nu_tr, "k": k, "scale": scale,
        "bootstrap_limit": 1.0 + float(pre["validation"]["tau"])}
    return val


# --------------------------------------------------------------------------- #
# 順方向の模型                                                                 #
# --------------------------------------------------------------------------- #
def cauchy_of_table(lam):
    """材料表の SiO₂(Malitson 1965)を、使う帯域で Cauchy の n = A + B/λ² に最小二乗で写す → (A, B [nm²], 最大のずれ)。"""
    n = MT._nk(MT._record("SIO2", "poc"), np.asarray(lam, float) / 1000.0, "poc")[0]
    X = np.column_stack([np.ones_like(lam), 1.0 / np.asarray(lam, float) ** 2])
    (A, B), *_ = np.linalg.lstsq(X, n, rcond=None)
    return float(A), float(B), float(np.max(np.abs(X @ [A, B] - n)))


def spectrum_line(d=98.0, A=1.46, B=3500.0, na=0.0, gain=1.0, coverage=1.0, angle=0.0, lam=None):
    """顕微分光の 1 本: 測定点の割合 coverage が膜(SiO₂、Cauchy の n)、残りが裸の Si。集光の NA で角度平均、利得を掛ける。

    返り値は (1, K) —— simcal の模型は 2-D の配列で終わる(1 行の「画像」)。
    """
    lam = np.asarray(lam, float)
    n = A + B / lam ** 2
    kw = {"wavelengths_nm": lam}
    if na > 0.0:
        kw["na"] = na
    elif angle > 0.0:
        kw["angle_deg"] = angle
    rf = FO.multilayer_reflectance([(n, float(d))], "SI", **kw)[:, 1]
    if coverage >= 1.0:
        return (gain * rf)[None, :]
    rs = FO.multilayer_reflectance([], "SI", **kw)[:, 1]
    return (gain * (coverage * rf + (1.0 - coverage) * rs))[None, :]


def _blackbody_rel(T):
    """色温度 T の黒体(spectralrad.blackbody_spectrum、560 nm で 1)を、カメラの白の黒体で割った相対の分光分布。"""
    sp = L.blackbody_spectrum(float(T), float(CAM_LAM[0]), float(CAM_LAM[-1]), len(CAM_LAM), normalize_nm=560.0)
    wh = L.blackbody_spectrum(CAM_WHITE_K, float(CAM_LAM[0]), float(CAM_LAM[-1]), len(CAM_LAM), normalize_nm=560.0)
    return np.asarray(sp)[:, 1] / np.asarray(wh)[:, 1]


def camera_blocks(d=98.0, A=1.46, B=3500.0, T=6504.0, illum=1.0, gain=1.0, gamma=2.2, vig=0.0,
                  region=None, r2=None, wavelength=None):
    """顕微鏡のカメラの模型: 区画ごとの RGB の平均 [DN] → (区画数, 3)。

    分光反射率(膜 or 裸の Si)× 光源(色温度 T の黒体 / カメラの白)→ CIE 1931 → 線形 sRGB(``matappear.spectrum_to_srgb``)
    → 周辺減光 1 + vig·r² → 利得 × 照明の強さ → ガンマ 1/γ → 255 倍。``wavelength`` を与えると単色(1 波長のモノクロ
    カメラ、3 列とも同じ値)。region は区画ごとに 0 = 裸の Si / 1 = 膜、r2 は視野の中心からの距離の 2 乗(半幅で正規化)。
    """
    region = np.asarray(region, int)
    r2 = np.asarray(r2, float)
    if wavelength is not None:
        lam = np.array([float(wavelength)])
        n = A + B / lam ** 2
        rf = FO.multilayer_reflectance([(n, float(d))], "SI", wavelengths_nm=lam)[0, 1]
        rs = FO.multilayer_reflectance([], "SI", wavelengths_nm=lam)[0, 1]
        lin = np.array([[rs] * 3, [rf] * 3])
    else:
        n = A + B / CAM_LAM ** 2
        rf = FO.multilayer_reflectance([(n, float(d))], "SI", wavelengths_nm=CAM_LAM)[:, 1]
        rs = FO.multilayer_reflectance([], "SI", wavelengths_nm=CAM_LAM)[:, 1]
        rel = _blackbody_rel(T)
        lin = MA.spectrum_to_srgb(CAM_LAM, np.stack([rs * rel, rf * rel]))
    sig = lin[region] * (1.0 + vig * r2)[:, None] * (gain * illum)
    return 255.0 * np.power(np.clip(sig, 1e-9, None), 1.0 / gamma)


# --------------------------------------------------------------------------- #
# 実データ                                                                     #
# --------------------------------------------------------------------------- #
def load_spectra():
    with open(os.path.join(REAL, "schwarz2024_sio2_si_reflectance.csv"), encoding="utf-8") as f:
        rows = list(csv.reader(f))
    cov = [float(h.replace("R_cov", "")) / 100.0 for h in rows[0][1:]]
    a = np.array([[float(v) for v in r] for r in rows[1:]])
    return a[:, 0], a[:, 1:], cov


def load_blocks():
    """顕微鏡写真 → 40 px 角の区画の RGB 平均(左 7 列が裸の Si、右 6 列が SiO₂、上下 8 段 = 104 区画)。"""
    from PIL import Image
    im = np.asarray(Image.open(os.path.join(REAL, "schwarz2024_micrograph_sio2_edge_640.jpg")).convert("RGB"), float)
    h, w = im.shape[:2]
    bs = 40
    vals, region, r2, rc = [], [], [], []
    for i, r0 in enumerate(range(20, 340, bs)):
        for j, c0 in enumerate(list(range(20, 300, bs)) + list(range(380, 620, bs))):
            vals.append(im[r0:r0 + bs, c0:c0 + bs].reshape(-1, 3).mean(0))
            region.append(1 if c0 > w // 2 else 0)
            yc, xc = r0 + bs / 2.0, c0 + bs / 2.0
            r2.append(((xc - w / 2.0) ** 2 + (yc - h / 2.0) ** 2) / (w / 2.0) ** 2)
            rc.append((i, j))
    return im, np.array(vals), np.array(region), np.array(r2), rc


# --------------------------------------------------------------------------- #
# 1. 計画と多変量                                                               #
# --------------------------------------------------------------------------- #
CAM_KNOBS = [
    {"name": "d", "arg": "d", "lo": 40.0, "hi": 250.0, "unit": "nm", "scale": "log"},
    {"name": "A", "arg": "A", "lo": 1.38, "hi": 1.56, "scale": "log"},
    {"name": "B", "arg": "B", "lo": 0.0, "hi": 9000.0, "unit": "nm^2"},
    {"name": "T", "arg": "T", "lo": 2500.0, "hi": 9000.0, "unit": "K", "scale": "log"},
    {"name": "illum", "arg": "illum", "lo": 0.5, "hi": 2.0, "scale": "log"},
    {"name": "gain", "arg": "gain", "lo": 0.3, "hi": 3.0, "scale": "log", "role": "gain"},
    {"name": "gamma", "arg": "gamma", "lo": 1.4, "hi": 3.2},
]


def _log_jacobian(fn, theta, names, log_names, h=1e-4):
    """出力の(雑音で割らない)感度行列。log のつまみは ln θ あたり、線形のつまみは範囲あたり(無次元)。"""
    base = fn(**theta).ravel()
    cols = []
    for nm in names:
        th = dict(theta)
        if nm in log_names:
            th[nm] = theta[nm] * math.exp(h)
            cols.append((fn(**th).ravel() - base) / h)
        else:
            k = next(k for k in CAM_KNOBS if k["name"] == nm)
            step = h * (k["hi"] - k["lo"])
            th[nm] = theta[nm] + step
            cols.append((fn(**th).ravel() - base) / h)
    return np.column_stack(cols)


def chapter_plan(blocks):
    print("\n1. 計画と多変量: どのつまみが効くか・交絡・決まる次元の数(合成、実物の写真と同じ区画の配置)")
    _im, _vals, region, r2, _rc = blocks
    ref = {"d": REF_NM, "A": 1.4585, "B": 3500.0, "T": 5000.0, "illum": 1.0, "gain": 1.0, "gamma": 2.2}
    two = np.array([0, 1])
    zero = np.zeros(2)

    def feats(**th):
        return camera_blocks(region=two, r2=zero, **th)            # 裸の Si と膜の RGB = 出力 6 個

    # (a) L18 の直交表(公表の表の写し、7 列の 3 水準)で 7 本を振り、出力 6 個の主成分の数を数える
    oa = L.doe_orthogonal_array("L18", [(k["name"], k["lo"], k["hi"], k.get("unit", ""), k.get("scale", "linear"))
                                        for k in CAM_KNOBS], columns=[2, 3, 4, 5, 6, 7, 8])
    nat = L.doe_decode(oa)
    names = [k["name"] for k in CAM_KNOBS]
    Y = np.array([feats(**dict(zip(names, row))).ravel() for row in nat])
    pca = L.mv_pca(Y, seed=0)
    NUMBERS["plan_runs"] = int(len(nat))
    NUMBERS["plan_pca_parallel"] = int(pca["n_components"]["parallel"]) if isinstance(pca.get("n_components"), dict) \
        else int(pca.get("n_parallel", 0))
    nc = pca["n_components"] if isinstance(pca.get("n_components"), dict) else {}
    print("      L18(18 回、7 本を 3 水準)→ 出力 6 個(裸の Si と膜の RGB)。主成分の数: %s"
          % ", ".join("%s %s" % (k, v) for k, v in nc.items()))
    # (b) Morris のふるい(simcal_screen、雑音 0.55 DN で白色化)と、決まる次元の数
    m = L.simcal_model(chain=[{"op": camera_blocks, "args": {"region": region, "r2": r2}}],
                       knobs=[dict(k, step=0, init=ref[k["name"]]) for k in CAM_KNOBS],
                       noise={"kind": "gaussian", "sigma": 0.55}, label="camera on SiO2/Si blocks")
    scr = L.simcal_screen(m, size=8 if REDUCED else 16, seed=0)
    NUMBERS["screen_class"] = scr["class"]
    NUMBERS["screen_dims"] = scr["output_dims"]
    print("      Morris のふるい(%d 回): %s / 雑音を越える出力の方向 %s 本、つまみ %d 本"
          % (scr["n_runs"], ", ".join("%s=%s" % kv for kv in scr["class"].items()), scr["output_dims"], scr["n_free"]))
    # (c) 交絡を物理と照合: (i) 照明 × 利得、(ii) 1 波長(550 nm)の膜の A と d
    logn = {"d", "A", "T", "illum", "gain"}
    S = _log_jacobian(lambda **t: camera_blocks(region=region, r2=r2, **t), ref, names, logn)
    conf = L.mv_confounding(S, names=names, log_params=True)
    groups = [sorted(g["parameters"]) for g in conf["confounded_groups"]]
    ig = S[:, names.index("illum")] / S[:, names.index("gain")]
    NUMBERS["illum_gain_ratio"] = float(np.median(ig))
    # 1 波長のモノクロ: 膜の画素 1 個は 1 つの数しか持たないので、決まるのは A と d の組み合わせ 1 つ(階数 1)。
    #   組み合わせ A^1·d^(s_d/s_A) の指数は、縞の傾きが最も急な波長(450〜650 nm を 2 nm 刻み、同点は短い側)で見る。
    #   位相 4π n d / λ だけなら s_d = s_A(光路長 n·d)。界面の反射率も n で変わるので、その分だけ 1 からずれる。
    def single(dd):
        best = None
        for lam1 in np.arange(450.0, 651.0, 2.0):
            Sx = _log_jacobian(lambda **t: camera_blocks(region=two, r2=zero, wavelength=float(lam1), **t),
                               {"d": dd, "A": 1.4585, "B": 3500.0}, ["A", "d"], {"A", "d"})[3]
            if best is None or _r(abs(Sx[1]), 6) > _r(abs(best[1][1]), 6):
                best = (float(lam1), Sx)
        lam1, Sx = best
        cx = L.mv_confounding(np.vstack([Sx, Sx]), names=["A", "d"], log_params=True)
        return lam1, float(Sx[1] / Sx[0]), cx
    lam_t, nd_ratio, c1 = single(500.0)
    lam_n, nd_thin, _c = single(REF_NM)
    NUMBERS.update({"nd_exponent": nd_ratio, "nd_lambda": lam_t, "nd_exponent_thin": nd_thin, "nd_lambda_thin": lam_n})
    nd_conf = any(set(g["parameters"]) == {"A", "d"} for g in c1["confounded_groups"])
    print("      交絡の組(γ > 10): %s / 照明と利得の感度の比 %.4f(積しか決まらない)"
          % (groups, NUMBERS["illum_gain_ratio"]))
    print("      1 波長のモノクロ、膜 500 nm(縞の傾きが最も急な %.0f nm): 決まるのは A^1·d^%.3f だけ(A と d は交絡 = %s)"
          % (lam_t, nd_ratio, nd_conf))
    print("      ★同じことを 98.5 nm の膜でやると A^1·d^%.2f(%.0f nm)—— λ/4 に近い薄い膜では、位相より界面の反射率の n 依存が"
          "効き、n·d からずれる" % (nd_thin, lam_n))
    gate("交絡の検出は既知の物理と一致: 照明 × 利得は同じ組(感度の比 %.4f = 1)、1 波長の 500 nm の膜は A と d が交絡し、"
         "決まる組み合わせの指数の比 %.3f(光路長 n·d なら 1、0.85〜1.15)" % (NUMBERS["illum_gain_ratio"], nd_ratio),
         any({"illum", "gain"} <= set(g) for g in groups) and abs(_r(NUMBERS["illum_gain_ratio"], 4) - 1.0) < 1e-3
         and 0.85 <= nd_ratio <= 1.15 and nd_conf)
    gate("ふるいはつまみ %d 本 > 決まる方向 %s 本と言い、照明と利得を「組み合わせ」に分ける"
         % (scr["n_free"], scr["output_dims"]),
         scr["output_dims"] is not None and scr["output_dims"] < scr["n_free"]
         and scr["class"]["illum"] == "combination" and scr["class"]["gain"] == "combination")
    return {"oa": oa, "Y": Y, "pca": pca, "screen": scr, "conf": conf, "S": S, "names": names}


# --------------------------------------------------------------------------- #
# 共通: 実測の分け方と雑音                                                       #
# --------------------------------------------------------------------------- #
def split_indices(n):
    """2 点ずつ交互に学習 / 取り置き(偶数・奇数の画素で残差の大きさが違うので 1 点おきにしない)。CI では 1/2 に間引く。"""
    i = np.arange(n)
    pair = i // 2
    if REDUCED:
        return i[pair % 4 == 0], i[pair % 4 == 2]
    return i[pair % 2 == 0], i[pair % 2 == 1]


def noise_floor(lam, Y):
    """雑音の大きさ = 被覆率 0 %(裸の Si)の実測を、材料表の Si に利得だけで合わせた残差の RMS(別の測定から取る)。"""
    rs = FO.multilayer_reflectance([], "SI", wavelengths_nm=lam)[:, 1]
    bare = Y[:, -1]
    g = float(np.sum(bare * rs) / np.sum(rs * rs))
    res = bare - g * rs
    d2 = Y[2:, 0] - 2 * Y[1:-1, 0] + Y[:-2, 0]
    white = float(1.4826 * np.median(np.abs(d2 - np.median(d2))) / math.sqrt(6.0))
    return float(np.sqrt(np.mean(res ** 2))), g, white


SPEC_KNOBS = {
    "d": {"name": "d", "arg": "d", "lo": 60.0, "hi": 140.0, "unit": "nm", "scale": "log"},
    "A": {"name": "A", "arg": "A", "lo": 1.38, "hi": 1.56, "scale": "log"},
    "B": {"name": "B", "arg": "B", "lo": 0.0, "hi": 9000.0, "unit": "nm^2"},
    "na": {"name": "na", "arg": "na", "lo": 0.0, "hi": 0.9},
    "gain": {"name": "gain", "arg": "gain", "lo": 0.9, "hi": 1.1},
}


def spec_model(names, fixed, lam, sigma, label, conditions=None):
    return L.simcal_model(chain=[{"op": spectrum_line, "args": dict({"lam": np.asarray(lam, float)}, **fixed)}],
                          knobs=[dict(SPEC_KNOBS[n], step=0) for n in names], conditions=conditions,
                          noise={"kind": "gaussian", "sigma": float(sigma)}, label=label)


# --------------------------------------------------------------------------- #
# 2. 合成の真値で回収                                                           #
# --------------------------------------------------------------------------- #
def chapter_synthetic(lam_all, sigma, AB):
    print("\n2. 合成の真値で回収(実測と同じ波長・同じ雑音 σ = %.5f)" % sigma)
    A0, B0 = AB
    tr, _ho = split_indices(len(lam_all))
    lam = lam_all[tr]
    # (a) G1 型: 決まる模型(d と利得、n は材料表、直入射)を固定の種 0..N−1 の雑音で 40 回 → 3σ_CRLB の内に戻るか
    m = spec_model(["d", "gain"], {"A": A0, "B": B0}, lam, sigma, "synthetic: d, gain")
    truth = {"d": REF_NM, "gain": 1.0}
    mu = L.simcal_simulate(m, truth)[0]
    n_seed = 20 if REDUCED else 40
    z = []
    for s in range(n_seed):
        obs = mu + sigma * np.random.default_rng(s).standard_normal(mu.shape)
        r = L.simcal_fit(L.simcal_observe(m, [obs]))
        crlb = L.simcal_identifiability(r, at=truth, profile=False)["identifiability"]["crlb"]
        z.append([(r["theta_hat"][k] - truth[k]) / crlb[k] for k in ("d", "gain")])
    Z = np.array(z)
    inside = int((np.abs(Z) < 3).all(axis=1).sum())
    NUMBERS.update({"g1_inside": inside, "g1_n": n_seed, "g1_zstd": float(Z.std())})
    print("      膜厚と利得: %d 種中 %d 種で両方とも 3σ_CRLB の内、z の標準偏差 %.2f(1 なら下界どおり)"
          % (n_seed, inside, Z.std()))
    gate("合成の真値の回収: %d 種中 %d 種(≥ 95 %%)が |推定 − 真値| < 3σ_CRLB" % (n_seed, inside), inside >= 0.95 * n_seed)
    # (b) 豊かな模型(5 本)の真値 = 実測に合わせた値の近く。プロファイルの 95 % 区間が真値を含むか(固定の種)
    rich_truth = {"d": 97.8, "A": 1.4696, "B": 500.0, "na": 0.69, "gain": 1.018}
    mr = spec_model(list(SPEC_KNOBS), {}, lam, sigma, "synthetic: rich")
    mur = L.simcal_simulate(mr, rich_truth)[0]
    cover = []
    for s in ((101,) if REDUCED else (101, 102, 103)):
        obs = mur + sigma * np.random.default_rng(s).standard_normal(mur.shape)
        r = L.simcal_fit(L.simcal_observe(mr, [obs]), method="multistart", allow_undetermined=True)
        p = L.simcal_identifiability(r)["identifiability"]["profile"]["d"]
        lo, hi = p["lower"], p["upper"]
        cover.append((s, lo, hi, lo is not None and hi is not None and lo <= rich_truth["d"] <= hi))
        print("      豊かな模型(d, A, B, NA, 利得)種 %d: 膜厚のプロファイル 95 %% 区間 [%s, %s] nm、真値 %.1f nm %s"
              % (s, "-" if lo is None else "%.2f" % lo, "-" if hi is None else "%.2f" % hi, rich_truth["d"],
                 "を含む" if cover[-1][3] else "を含まない"))
    NUMBERS["rich_cover"] = sum(c[3] for c in cover)
    gate("合成の豊かな模型: プロファイルの 95 %% 区間が真値の膜厚を含む(%d / %d 種)" % (NUMBERS["rich_cover"], len(cover)),
         NUMBERS["rich_cover"] == len(cover))
    # (c) 族の外: 500 nm の膜を 4 つの入射角で撮る(真値は材料表の分散)。分散を無視した模型(B = 0、A は自由)
    lam_c = np.linspace(450.0, 900.0, 61 if REDUCED else 121)
    conds = [{0: {"angle": a}} for a in (0.0, 25.0, 45.0, 60.0)]
    truth_c = {"d": 500.0, "A": A0, "B": B0, "gain": 1.0}
    def thick(names, fixed):
        kn = [dict(SPEC_KNOBS[n], step=0) for n in names]
        for k in kn:
            if k["name"] == "d":
                k.update(lo=300.0, hi=700.0)
        return L.simcal_model(chain=[{"op": spectrum_line, "args": dict({"lam": lam_c}, **fixed)}], knobs=kn,
                              conditions=conds, noise={"kind": "gaussian", "sigma": float(sigma)})
    rich_c = thick(["d", "A", "B", "gain"], {})
    poor_c = thick(["d", "A", "gain"], {"B": 0.0})
    imgs = [y + sigma * np.random.default_rng(200 + i).standard_normal(y.shape)
            for i, y in enumerate(L.simcal_simulate(rich_c, truth_c))]
    out = {}
    for tag, mm in (("rich", rich_c), ("poor", poor_c)):
        r = L.simcal_fit(L.simcal_observe(mm, imgs), method="multistart", allow_undetermined=True)
        dd = L.simcal_discrepancy(r)
        out[tag] = (r, dd)
        th = r["diagnostics"]["endpoint_not_an_estimate"]
        print("      500 nm・4 入射角、%s: d = %.2f nm、χ²/自由度 %.2f、残差 PCA の構造 %d 成分(%s)"
              % ("分散あり(A, B)" if tag == "rich" else "分散を無視(B = 0)", th["d"], r["fit"]["chi2_red"],
                 dd["discrepancy"]["n_structural"], dd["discrepancy"]["verdict"]))
    rr, rd = out["rich"]
    pr_, pdsc = out["poor"]
    NUMBERS.update({"syn_rich_d": rr["diagnostics"]["endpoint_not_an_estimate"]["d"],
                    "syn_poor_d": pr_["diagnostics"]["endpoint_not_an_estimate"]["d"],
                    "syn_poor_struct": pdsc["discrepancy"]["n_structural"],
                    "syn_rich_struct": rd["discrepancy"]["n_structural"]})
    crl = L.simcal_identifiability(rr, at={k: truth_c[k] for k in ("d", "A", "B", "gain")},
                                   profile=False)["identifiability"]["crlb"]
    zc = {k: (rr["theta_hat"].get(k, float("nan")) - truth_c[k]) / crl[k] for k in ("d", "A", "B", "gain")}
    NUMBERS["syn_rich_z"] = zc
    gate("合成 500 nm・4 入射角: 分散ありの模型は 4 本とも 3σ_CRLB の内に戻る(z = %s)"
         % ", ".join("%s %+.2f" % kv for kv in zc.items()),
         rr["status"] == "accepted" and all(abs(v) < 3 for v in zc.values()))
    gate("合成: 分散を無視した模型の残差を残差 PCA が見つけ(%d 成分)、分散ありの模型には見つけない(%d 成分)"
         % (NUMBERS["syn_poor_struct"], NUMBERS["syn_rich_struct"]),
         pdsc["discrepancy"]["verdict"] == "structure" and rd["discrepancy"]["n_structural"] == 0)
    return {"Z": Z, "cover": cover, "thick": out, "lam_c": lam_c, "imgs_c": imgs, "truth_c": truth_c}


# --------------------------------------------------------------------------- #
# 3. 実測の顕微分光で較正                                                       #
# --------------------------------------------------------------------------- #
def chapter_real_spectrum(lam_all, Y, sigma, AB):
    print("\n3. ★実測の顕微分光で較正(Schwarz ら 2024、CC BY 4.0、被覆率 100 %% の 1 本。基準 %.1f nm)" % REF_NM)
    tr, ho = split_indices(len(lam_all))
    y = Y[:, 0]
    rich = spec_model(list(SPEC_KNOBS), {}, lam_all[tr], sigma, "SiO2 on Si, rich (d, A, B, NA, gain)")
    rich_h = spec_model(list(SPEC_KNOBS), {}, lam_all[ho], sigma, "holdout")
    mo = L.simcal_observe(rich, [y[tr][None, :]])
    mh = L.simcal_observe(rich_h, [y[ho][None, :]], split="holdout")
    scr = L.simcal_screen(mo, size=8 if REDUCED else 12, seed=0)
    try:
        L.simcal_fit(mo, method="multistart")
        refused = None
    except MetricContractError as e:
        refused = str(e).splitlines()[0]
    r = L.simcal_fit(mo, method="multistart", allow_undetermined=True)
    idf = L.simcal_identifiability(r)
    val = validate_ratio_f(idf, mh)
    rep = L.simcal_report(val)
    try:
        L.simcal_uncertainty(idf)
        unc_refused = None
    except MetricContractError as e:
        unc_refused = str(e)
    prof = idf["identifiability"]["profile"]
    end = r["diagnostics"]["endpoint_not_an_estimate"]
    pd_ = prof["d"]
    NUMBERS.update({"real_end": {k: float(v) for k, v in end.items()}, "real_chi2": r["fit"]["chi2_red"],
                    "real_d_lo": pd_["lower"], "real_d_hi": pd_["upper"], "real_gamma": r["fit"].get("gamma_full"),
                    "real_screen": scr["class"], "real_dims": scr["output_dims"],
                    "real_prof": {k: (v["class"], v["lower"], v["upper"]) for k, v in prof.items()}})
    print("      ふるい: %s / 決まる方向 %s 本" % (", ".join("%s=%s" % kv for kv in scr["class"].items()), scr["output_dims"]))
    print("      当てはめ(allow なし)→ %s" % (refused or "受理"))
    print("      終点(推定ではない): %s、χ²/自由度 %.3f" % (", ".join("%s %.4g" % kv for kv in end.items()),
                                                    r["fit"]["chi2_red"]))
    for c in r["determined_combos"][:3]:
        print("      決まる組み合わせ: %s" % c["combination"])
    for k, v in prof.items():
        print("      プロファイル %-4s %-12s [%s, %s]" % (k, v["class"], "-" if v["lower"] is None else "%.4g" % v["lower"],
                                                  "-" if v["upper"] is None else "%.4g" % v["upper"]))
    gv = val["validation"]["gates"]
    print("      過適合の門(取り置いた波長 %d 点): %s" % (len(ho), ", ".join(
        "%s %s(%.3g / %.3g)" % (k, "通過" if g["passed"] else "不合格", g["value"], g["limit"]) for k, g in gv.items())))
    print("      不確かさ(simcal_uncertainty): %s" % ("拒否 —— " + unc_refused[:80] + "…" if unc_refused else "出た"))
    lo, hi = pd_["lower"], pd_["upper"]
    width = (hi - lo) if lo is not None and hi is not None else float("nan")
    NUMBERS["real_d_width"] = width
    gate("局所の共線性で点推定を出さない: 当てはめは allow なしで拒否し、d・A・NA・利得は組み合わせ(γ > 10)",
         refused is not None and not r["theta_hat"].get("d"))
    gate("★較正した膜厚のプロファイル 95 %% 区間 [%.2f, %.2f] nm(幅 %.2f nm)が基準 %.2f nm を含む"
         % (lo or float("nan"), hi or float("nan"), width, REF_NM),
         lo is not None and hi is not None and _r(lo, 4) <= _r(REF_NM, 4) <= _r(hi, 4))
    gate("分散 B は上限しか言えない(98 nm の膜は帯域内で縞が 1 本未満): B の区間は %s、上限 %s nm²"
         % (prof["B"]["class"], "-" if prof["B"]["upper"] is None else "%.0f" % prof["B"]["upper"]),
         prof["B"]["class"] in ("upper_only", "undetermined"))
    gate("豊かな模型は過適合の門 6 本をすべて通る(絶対の χ²: 学習 χ²/ν %.3f・取り置き %.3f)"
         % (gv["fit_consistent_with_noise"]["train"]["chi2_per_nu"], gv["fit_consistent_with_noise"]["holdout"]["chi2_per_nu"]),
         val["validation"]["passed"])
    rt = val["validation"]["ratio_test"]
    from scipy.stats import f as _f
    rng = np.random.default_rng(20261018)               # 探針専用の種(共有の乱数列は引かない)
    m_mc = 200000
    sim = ((rng.chisquare(rt["nu_holdout"], m_mc) / (rt["nu_holdout"] - rt["k"]))
           / (rng.chisquare(rt["nu_train"], m_mc) / rt["nu_train"]))
    q_mc = float(np.quantile(sim, 1.0 - rt["alpha"]))
    p_mc = float(np.mean(sim >= rt["ratio"]))
    p_inf = float(_f.sf(2.25 * rt["ratio"] / rt["scale"], rt["nu_holdout"], rt["nu_train"]))
    NUMBERS["real_ratio_test"] = dict(rt, limit_mc=q_mc, p_mc=p_mc, p_inflated=p_inf)
    print("      取り置き / 学習 の比 %.3f: F(%d, %d) の上側 p = %.3g、限界 %.3f(α = %.0e の分位。モンテカルロ %d 本で %.3f、"
          "p %.3g)/ 旧来の bootstrap の限界は %.3f"
          % (rt["ratio"], rt["nu_holdout"], rt["nu_train"], rt["p"], rt["limit"], rt["alpha"], m_mc, q_mc, p_mc,
             rt["bootstrap_limit"]))
    print("      ★探針: 取り置きの残差を 1.5 倍(比 × 2.25 = %.3f)にすると p = %.2g → 拒否" % (2.25 * rt["ratio"], p_inf))
    gate("取り置き / 学習 の比の門は統計から決める: 比 %.3f は F(%d, %d) の上側 p = %.3g ≥ α %.0e(限界 %.3f は解析の分位で"
         "モンテカルロ %.3f と 3 %% 以内)、取り置きの残差を 1.5 倍にすると p = %.1e で拒否"
         % (rt["ratio"], rt["nu_holdout"], rt["nu_train"], rt["p"], rt["alpha"], rt["limit"], q_mc, p_inf),
         rt["p"] >= rt["alpha"] and rt["ratio"] <= rt["limit"] and abs(q_mc / rt["limit"] - 1.0) < 0.03
         and abs(p_mc - rt["p"]) < 0.01 and p_inf < rt["alpha"])
    return {"tr": tr, "ho": ho, "fit": r, "ident": idf, "val": val, "report": rep, "screen": scr,
            "model": rich, "end": end}


# --------------------------------------------------------------------------- #
# 4. 貧しい模型                                                                 #
# --------------------------------------------------------------------------- #
def chapter_poor(lam_all, Y, sigma, AB, white):
    print("\n4. 貧しい模型を実測に合わせる —— 絶対の χ² の門が拒否するか")
    A0, B0 = AB
    tr, ho = split_indices(len(lam_all))
    y = Y[:, 0]
    n589 = float(A0 + B0 / 589.3 ** 2)
    cases = [("normal", "直入射・材料表の n(既存の PoC と同じ模型)", ["d", "gain"], {"A": A0, "B": B0}),
             ("nodisp", "分散を無視: n = %.4f 一定(材料表の 589 nm)、NA は自由" % n589, ["d", "na", "gain"],
              {"A": n589, "B": 0.0}),
             ("freeA", "分散を無視: n 一定だが A と NA は自由", ["d", "A", "na", "gain"], {"B": 0.0})]
    out = {}
    for tag, label, names, fixed in cases:
        m = spec_model(names, fixed, lam_all[tr], sigma, label)
        mh = spec_model(names, fixed, lam_all[ho], sigma, "holdout")
        r = L.simcal_fit(L.simcal_observe(m, [y[tr][None, :]]), method="multistart", allow_undetermined=True)
        idf = L.simcal_identifiability(r)
        v = validate_ratio_f(idf, L.simcal_observe(mh, [y[ho][None, :]], split="holdout"))
        pd_ = idf["identifiability"]["profile"]["d"]
        g6 = v["validation"]["gates"]["fit_consistent_with_noise"]
        out[tag] = {"fit": r, "val": v, "d": pd_, "label": label, "names": names, "fixed": fixed}
        print("      %s: χ²/ν 学習 %.2f(p = %.2g)、膜厚 [%s, %s] nm → %s(失敗した門: %s)"
              % (label, g6["train"]["chi2_per_nu"], g6["train"]["p"],
                 "-" if pd_["lower"] is None else "%.2f" % pd_["lower"], "-" if pd_["upper"] is None else "%.2f" % pd_["upper"],
                 v["status"], v["validation"]["failed"] or "なし"))
    nrm = out["normal"]
    NUMBERS.update({"poor_normal_chi2": nrm["val"]["validation"]["gates"]["fit_consistent_with_noise"]["train"]["chi2_per_nu"],
                    "poor_nodisp_chi2": out["nodisp"]["val"]["validation"]["gates"]["fit_consistent_with_noise"]["train"]["chi2_per_nu"],
                    "poor_freeA_chi2": out["freeA"]["val"]["validation"]["gates"]["fit_consistent_with_noise"]["train"]["chi2_per_nu"],
                    "poor_normal_d": (nrm["d"]["lower"], nrm["d"]["upper"])})
    lo, hi = nrm["d"]["lower"], nrm["d"]["upper"]
    gate("貧しい模型の拒否: 直入射・材料表の n は絶対の χ² の門で不合格(χ²/ν %.2f)—— 膜厚の区間 [%.2f, %.2f] nm は狭いのに"
         "基準 %.1f nm を含まない" % (NUMBERS["poor_normal_chi2"], lo, hi, REF_NM),
         "fit_consistent_with_noise" in nrm["val"]["validation"]["failed"] and not (lo <= REF_NM <= hi))
    gate("貧しい模型の拒否: 分散を無視した一定の n(材料表の値)も絶対の χ² の門で不合格(χ²/ν %.2f)"
         % NUMBERS["poor_nodisp_chi2"], "fit_consistent_with_noise" in out["nodisp"]["val"]["validation"]["failed"])
    gate("★正直な限界: A を自由にした一定の n は門を通る(χ²/ν %.3f)—— 98 nm の膜では分散は見えず、この実測では"
         "「分散を無視」を拒否できない" % NUMBERS["poor_freeA_chi2"],
         "fit_consistent_with_noise" not in out["freeA"]["val"]["validation"]["failed"])
    return out


# --------------------------------------------------------------------------- #
# 5. 実物の顕微鏡写真                                                           #
# --------------------------------------------------------------------------- #
def chapter_micrograph(blocks, AB):
    print("\n5. 実物の顕微鏡写真(Schwarz ら 2024、カメラ不明・JPEG)—— 決まる係数と決まらない組み合わせ")
    A0, B0 = AB
    im, vals, region, r2, rc = blocks
    checker = np.array([(i + j) % 2 == 0 for i, j in rc])
    # 雑音 = 学習の区画で、領域・色ごとに r² の 2 次式を引いた残りの標準偏差(区画の平均に残る JPEG・汚れ・むら)
    res = []
    for rg in (0, 1):
        mk = checker & (region == rg)
        X = np.column_stack([np.ones(mk.sum()), r2[mk], r2[mk] ** 2])
        for ch in range(3):
            res.append(vals[mk, ch] - X @ np.linalg.lstsq(X, vals[mk, ch], rcond=None)[0])
    sig = float(np.std(np.concatenate(res)))
    knobs = [dict(k, step=0) for k in CAM_KNOBS if k["name"] != "illum"] + \
        [{"name": "vig", "arg": "vig", "lo": -0.3, "hi": 0.1, "step": 0}]

    def model(mask, names_fixed=None):
        kn = [k for k in knobs if not names_fixed or k["name"] not in names_fixed]
        return L.simcal_model(chain=[{"op": camera_blocks, "args": dict({"region": region[mask], "r2": r2[mask]},
                                                                         **(names_fixed or {}))}],
                              knobs=kn, noise={"kind": "gaussian", "sigma": sig}, label="micrograph blocks")
    full = model(checker)
    mo = L.simcal_observe(full, [vals[checker]])
    scr = L.simcal_screen(mo, size=8 if REDUCED else 12, seed=0)
    r = L.simcal_fit(mo, method="multistart", allow_undetermined=True)
    det = sorted(r["theta_hat"])
    print("      雑音(区画の平均の揺れ)%.2f DN。ふるい: %s / 決まる方向 %s 本"
          % (sig, ", ".join("%s=%s" % kv for kv in scr["class"].items()), scr["output_dims"]))
    print("      つまみ 7 本の当てはめ: 決まった %s、決まらない %s、χ²/自由度 %.1f"
          % ({k: round(v, 4) for k, v in r["theta_hat"].items()}, sorted(r["undetermined"]), r["fit"]["chi2_red"]))
    NUMBERS.update({"cam_sigma": sig, "cam_determined": det, "cam_undetermined": sorted(r["undetermined"]),
                    "cam_rich_chi2": r["fit"]["chi2_red"]})
    gate("実物の写真で、決まる係数と決まらない組み合わせが分かれる: 決まる %s / 組み合わせ %s"
         % (det, sorted(r["undetermined"])),
         "d" in r["undetermined"] and len(det) >= 1 and "vig" in det)
    # 決まる模型: A, B は材料表に固定。d・T・利得・ガンマ・周辺減光
    fixed = {"A": A0, "B": B0}
    m2 = model(checker, fixed)
    h2 = model(~checker, fixed)
    r2_ = L.simcal_fit(L.simcal_observe(m2, [vals[checker]]), method="multistart")
    idf = L.simcal_identifiability(r2_)
    unc = L.simcal_uncertainty(idf)
    val = validate_ratio_f(unc, L.simcal_observe(h2, [vals[~checker]], split="holdout"))
    dsc = L.simcal_discrepancy(val)
    pd_ = idf["identifiability"]["profile"]["d"]
    g6 = val["validation"]["gates"]["fit_consistent_with_noise"]
    NUMBERS.update({"cam_d": r2_["theta_hat"]["d"], "cam_d_lo": pd_["lower"], "cam_d_hi": pd_["upper"],
                    "cam_T": r2_["theta_hat"].get("T"), "cam_gamma": r2_["theta_hat"].get("gamma"),
                    "cam_chi2": g6["train"]["chi2_per_nu"], "cam_struct": dsc["discrepancy"]["n_structural"]})
    print("      A, B を材料表に固定: d = %.2f nm(プロファイル [%.2f, %.2f])、T = %.0f K、γ = %.2f、χ²/ν %.1f → %s"
          "(失敗した門: %s)、残差 PCA %d 成分"
          % (r2_["theta_hat"]["d"], pd_["lower"], pd_["upper"], r2_["theta_hat"]["T"], r2_["theta_hat"]["gamma"],
             g6["train"]["chi2_per_nu"], val["status"], val["validation"]["failed"], dsc["discrepancy"]["n_structural"]))
    gate("★写真のカメラ較正: 区間 [%.2f, %.2f] nm は狭いが基準 %.1f nm から %+.0f %% —— 絶対の χ² の門(χ²/ν %.1f)と"
         "残差 PCA(%d 成分)が食い違いを見つけて拒否する" % (pd_["lower"], pd_["upper"], REF_NM,
                                                     100 * (r2_["theta_hat"]["d"] / REF_NM - 1), g6["train"]["chi2_per_nu"],
                                                     dsc["discrepancy"]["n_structural"]),
         "fit_consistent_with_noise" in val["validation"]["failed"] and dsc["discrepancy"]["verdict"] == "structure"
         and not (pd_["lower"] <= REF_NM <= pd_["upper"]))
    return {"im": im, "vals": vals, "region": region, "r2": r2, "checker": checker, "rich": r, "fit": r2_,
            "val": val, "disc": dsc, "m2": m2, "sigma": sig, "screen": scr}


# --------------------------------------------------------------------------- #
# 6. 探針                                                                       #
# --------------------------------------------------------------------------- #
def chapter_probes(lam_all, Y, sigma, white, real, plan, syn, blocks):
    print("\n6. 壊して確かめる探針(乱数を引かない)")
    # (1) 基準値を区間の幅の 2 倍ずらすと、一致の門は赤
    lo, hi = NUMBERS["real_d_lo"], NUMBERS["real_d_hi"]
    shifted = REF_NM + 2.0 * (hi - lo)
    p1 = not (lo <= shifted <= hi)
    print("      (1) 基準を %.1f → %.1f nm にずらす: 区間 [%.2f, %.2f] に入らない = %s" % (REF_NM, shifted, lo, hi, p1))
    # (2) 雑音を「白色の分」(隣り合う波長の 2 階差分)だけと見誤ると、豊かな模型も絶対の門で落ちる
    tr, ho = split_indices(len(lam_all))
    end = real["end"]
    mw = spec_model(list(SPEC_KNOBS), {}, lam_all[ho], white, "holdout, white-only noise")
    mo = L.simcal_observe(spec_model(list(SPEC_KNOBS), {}, lam_all[tr], white, "white-only noise"),
                          [Y[tr, 0][None, :]])
    rw = L.simcal_fit(mo, method="multistart", allow_undetermined=True)
    vw = validate_ratio_f(rw, L.simcal_observe(mw, [Y[ho, 0][None, :]], split="holdout"))
    p2 = "fit_consistent_with_noise" in vw["validation"]["failed"]
    print("      (2) 雑音を白色の分 σ = %.5f(床 %.5f の %.0f %%)と見誤る: χ²/ν %.2f → 絶対の門で不合格 = %s"
          % (white, sigma, 100 * white / sigma,
             vw["validation"]["gates"]["fit_consistent_with_noise"]["train"]["chi2_per_nu"], p2))
    del end
    # (3) 照明と利得だけを合わせる写真(ほかは真値に固定)。両方自由なら当てはめは拒否して積だけ返し、
    #     照明を固定すると利得は 1 つに決まる(組み合わせから「決まる」へ)
    _im, _vals, region, r2, _rc = blocks
    ref = {"d": REF_NM, "A": 1.4585, "B": 3500.0, "T": 5000.0, "illum": 1.5, "gain": 0.8, "gamma": 2.2}
    def ig_model(fix_illum):
        kn = [dict(k, step=0) for k in CAM_KNOBS if k["name"] in ("illum", "gain")]
        if fix_illum:
            kn[0]["fixed"] = ref["illum"]
        return L.simcal_model(chain=[{"op": camera_blocks, "args": {"region": region, "r2": r2, "d": REF_NM, "A": 1.4585,
                                                                     "B": 3500.0, "T": 5000.0, "gamma": 2.2}}],
                              knobs=kn, noise={"kind": "gaussian", "sigma": 0.55})
    m_ig = ig_model(False)
    mu = L.simcal_simulate(m_ig, {"illum": ref["illum"], "gain": ref["gain"]})[0]
    obs = mu                                                        # 探針は乱数を引かない(雑音なし)
    try:
        L.simcal_fit(L.simcal_observe(m_ig, [obs]))
        ref_ig = False
    except MetricContractError:
        ref_ig = True
    r_ig = L.simcal_fit(L.simcal_observe(m_ig, [obs]), allow_undetermined=True)
    prod = r_ig["determined_combos"][0]["value"]["product"] if r_ig["determined_combos"] else float("nan")
    r_g = L.simcal_fit(L.simcal_observe(ig_model(True), [obs]))
    g_hat = r_g["theta_hat"].get("gain", float("nan"))
    p3 = ref_ig and abs(prod / (ref["illum"] * ref["gain"]) - 1) < 0.01 and abs(g_hat / ref["gain"] - 1) < 0.01
    print("      (3) 照明と利得: 両方自由なら拒否 = %s、積 %.4f(真値 %.2f)/ 照明を固定すると利得 %.4f(真値 %.2f)= %s"
          % (ref_ig, prod, ref["illum"] * ref["gain"], g_hat, ref["gain"], p3))
    # (4) 真値を貧しい模型(B = 0)で作ると、貧しい模型の残差 PCA は構造を見つけない(門は逆向きに静か)
    lam_c, truth_c = syn["lam_c"], dict(syn["truth_c"])
    conds = [{0: {"angle": a}} for a in (0.0, 25.0, 45.0, 60.0)]
    kn = [dict(SPEC_KNOBS[n], step=0) for n in ("d", "A", "gain")]
    for k in kn:
        if k["name"] == "d":
            k.update(lo=300.0, hi=700.0)
    poor = L.simcal_model(chain=[{"op": spectrum_line, "args": {"lam": lam_c, "B": 0.0}}], knobs=kn, conditions=conds,
                          noise={"kind": "gaussian", "sigma": float(sigma)})
    tp = {"d": truth_c["d"], "A": 1.4585, "gain": 1.0}
    imgs = list(L.simcal_simulate(poor, tp))                         # 探針は乱数を引かない(雑音なし)
    dp = L.simcal_discrepancy(L.simcal_fit(L.simcal_observe(poor, imgs), method="multistart", allow_undetermined=True))
    p4 = dp["discrepancy"]["n_structural"] == 0
    print("      (4) 真値も B = 0 で作る: 貧しい模型の残差 PCA は %d 成分 = 静か %s" % (dp["discrepancy"]["n_structural"], p4))
    NUMBERS["probes"] = [p1, p2, p3, p4]
    gate("探針 4 本がすべて逆向きに鳴る(基準のずれ・白色の雑音・照明の固定・族の中の真値)", all([p1, p2, p3, p4]),
         "%s" % [p1, p2, p3, p4])


# --------------------------------------------------------------------------- #
# 図                                                                           #
# --------------------------------------------------------------------------- #
def make_figures(lam_all, Y, sigma, AB, plan, syn, real, poor, cam):
    A0, B0 = AB
    tr = real["tr"]
    end = real["end"]
    lam = lam_all
    fit_rich = spectrum_line(lam=lam, **end)[0]
    pn = poor["normal"]["fit"]["diagnostics"]["endpoint_not_an_estimate"]
    fit_poor = spectrum_line(lam=lam, A=A0, B=B0, **pn)[0]
    figs.save_plot(
        "real_spectrum_fits",
        [("実測(被覆率 100 %)", lam[::3], Y[::3, 0]), ("豊かな模型(d, A, B, NA, 利得)", lam, fit_rich),
         ("直入射・材料表の n", lam, fit_poor)],
        kinds=["scatter", "line", "line"], styles=[None, None, "dashed"], colors=["neutral", "right", "wrong"],
        xlabel="波長 [nm]", ylabel="反射率", title="実測の顕微分光に 2 つの模型を合わせる",
        caption="Si 上の SiO₂(基準 %.1f nm)の実測の反射率に、5 本のつまみの模型(実線)と直入射・材料表の n の模型(破線)を"
                "合わせた。どちらも見た目はよく重なる —— 違いは残差を雑音の床 σ = %.5f(裸の Si の別の測定から)で割ると見える"
                "(次の図)。" % (REF_NM, sigma), source=SOURCE)
    rr = (Y[:, 0] - fit_rich) / sigma
    rp = (Y[:, 0] - fit_poor) / sigma
    lim_r = float(math.ceil(1.1 * max(np.abs(rr).max(), np.abs(rp).max())))
    figs.save_plot(
        "real_residuals",
        [("豊かな模型", lam, rr), ("直入射・材料表の n", lam, rp), ("±1 σ", [lam[0], lam[-1]], [1, 1]),
         ("", [lam[0], lam[-1]], [-1, -1])],
        kinds=["line"] * 4, styles=[None, None, "dashed", "dashed"], colors=["right", "wrong", "reference", "reference"],
        xlabel="波長 [nm]", ylabel="(実測 − 模型) / σ", ylim=(-lim_r, lim_r),
        title="残差を雑音の床で割る —— 貧しい模型は全帯域でうねる",
        caption="豊かな模型の χ²/ν は %.2f、直入射・材料表の n は %.2f(絶対の χ² の門で p < 1e-3 → 拒否)。"
                % (NUMBERS["real_chi2"], NUMBERS["poor_normal_chi2"]), source=SOURCE)
    # プロファイル
    p = real["ident"]["identifiability"]["profile"]["d"]
    t = np.array(p["trace"])
    t = t[(t[:, 1] <= 12.0)]
    tn = np.array(poor["normal"]["d"]["trace"]) if poor["normal"]["d"].get("trace") else None
    series = [("豊かな模型(他のつまみは合わせ直す)", t[:, 0], t[:, 1])]
    kinds, styles, colors = ["line"], [None], ["right"]
    if tn is not None:
        tn = tn[tn[:, 1] <= 12.0]
        series.append(("直入射・材料表の n(拒否)", tn[:, 0], tn[:, 1]))
        kinds.append("line")
        styles.append(None)
        colors.append("wrong")
    series += [("χ²₁(95 %) = 3.84", [88, 104], [3.84, 3.84]), ("基準 %.1f nm" % REF_NM, [REF_NM, REF_NM], [0, 12])]
    kinds += ["line", "line"]
    styles += ["dashed", "dotted"]
    colors += ["reference", "emphasis"]
    figs.save_plot(
        "real_profile_thickness", series, kinds=kinds, styles=styles, colors=colors, xlim=(88, 104), ylim=(0, 12),
        xlabel="膜厚 d [nm]", ylabel="Δχ²",
        title="実測の膜厚: 区間 [%.1f, %.1f] nm に基準 %.1f nm が入る" % (NUMBERS["real_d_lo"], NUMBERS["real_d_hi"], REF_NM),
        caption="膜厚を固定して A・B・NA・利得を合わせ直したときの χ² の増え方(プロファイル尤度)。3.84 を越えない範囲が 95 %% 区間"
                "(幅 %.1f nm)。局所の共線性 γ > 10 なので点推定は出さない —— NA が分からないと膜厚と屈折率と NA が互いに"
                "肩代わりする。左の端で χ² が急に立つのは NA = 0 の壁(NA は負になれず、薄い側へはそれ以上逃げられない)。直入射・材料表の n の模型は区間が狭く(%.2f〜%.2f nm)基準を外すが、絶対の χ² の門が拒否する。"
                % (NUMBERS["real_d_width"], NUMBERS["poor_normal_d"][0], NUMBERS["poor_normal_d"][1]), source=SOURCE)
    # 計画: ふるいの表
    scr = plan["screen"]
    rows = []
    for nm in plan["names"]:
        rows.append([nm, scr["class"][nm], "%.1f" % scr["mu_star_whitened"][nm]])
    figs.save_table("plan_screen", ["つまみ", "分類", "μ*(雑音の σ で数えた動き)"], rows,
                    title="Morris のふるい: 7 本のつまみ、決まる方向 %s 本" % scr["output_dims"],
                    caption="写真と同じ区画の配置で、雑音 0.55 DN に白色化した出力の主成分ごとに Morris の μ* を回して合成した。"
                            "照明と利得は積しか効かないので「組み合わせ」。L18 の直交表 18 回の出力 6 個の主成分は %s。"
                            % plan["pca"].get("n_components"))
    # 合成の z
    Z = syn["Z"]
    xs = np.arange(len(Z))
    figs.save_plot("synthetic_recovery_z",
                   [("膜厚 d", xs, np.clip(Z[:, 0], -5, 5)), ("利得", xs + 0.2, np.clip(Z[:, 1], -5, 5)),
                    ("±3 σ_CRLB", [-1, len(Z)], [3, 3]), ("", [-1, len(Z)], [-3, -3])],
                   kinds=["scatter", "scatter", "line", "line"], styles=[None, None, "dashed", "dashed"],
                   colors=["emphasis", "right", "reference", "reference"], xlim=(-1, len(Z)), ylim=(-5, 5),
                   xlabel="雑音の種(固定 0..%d)" % (len(Z) - 1), ylabel="(推定 − 真値) / σ_CRLB",
                   title="合成の真値の回収: %d 種中 %d 種が ±3σ_CRLB の内" % (NUMBERS["g1_n"], NUMBERS["g1_inside"]),
                   caption="実測と同じ波長・同じ雑音 σ で、膜厚 %.1f nm・利得 1 を作って合わせた。z の標準偏差 %.2f(1 なら"
                           "Cramér-Rao 下界どおり)。" % (REF_NM, NUMBERS["g1_zstd"]))
    # 合成: 分散を無視した模型の残差 PCA の第 1 成分
    lam_c = syn["lam_c"]
    _rr, rd = syn["thick"]["rich"]
    _pr, pd_ = syn["thick"]["poor"]
    lp = np.asarray(pd_["discrepancy"]["loading_maps"][0]).ravel() if pd_["discrepancy"].get("loading_maps") else None
    rmaps = [np.asarray(m_).ravel() for m_ in pd_["residual_maps"]]
    rmaps_r = [np.asarray(m_).ravel() for m_ in _rr["residual_maps"]]
    lim_c = float(math.ceil(1.1 * max(np.abs(np.concatenate(rmaps + rmaps_r)).max(), 1.0)))
    ser = [("分散を無視、入射角 %d°" % a, lam_c, rm) for a, rm in zip((0, 25, 45, 60), rmaps)]
    ser += [("分散あり、0°", lam_c, rmaps_r[0])]
    figs.save_plot("synthetic_discrepancy", ser, kinds=["line"] * 5, styles=[None, None, None, None, "dashed"],
                   colors=["wrong", "wrong", "wrong", "wrong", "right"], ylim=(-lim_c, lim_c),
                   xlabel="波長 [nm]", ylabel="残差 / σ",
                   title="分散を無視した模型の残差は、4 つの入射角で系統的にうねる",
                   caption="合成の 500 nm の膜(真値は材料表の分散)を 0・25・45・60° で撮った。分散を無視(B = 0)すると残差が"
                           "波長に沿って系統的にうねり、残差 PCA は %d 成分の構造を見つける。分散ありの模型は %d 成分(白色)。"
                           % (NUMBERS["syn_poor_struct"], NUMBERS["syn_rich_struct"]))
    del lp
    # 写真: 元画像・区画の模型・残差
    im = cam["im"] / 255.0
    region, r2, checker = cam["region"], cam["r2"], cam["checker"]
    th = cam["fit"]["theta_hat"]
    pred = camera_blocks(region=region, r2=r2, A=A0, B=B0, **th)
    h, w = im.shape[:2]
    pim = np.zeros_like(im)
    rim = np.zeros(im.shape[:2])
    k = 0
    for r0 in range(20, 340, 40):
        for c0 in list(range(20, 300, 40)) + list(range(380, 620, 40)):
            pim[r0:r0 + 40, c0:c0 + 40] = pred[k] / 255.0
            rim[r0:r0 + 40, c0:c0 + 40] = float(np.sqrt(np.mean((cam["vals"][k] - pred[k]) ** 2))) / cam["sigma"]
            k += 1
    figs.save_grid("real_micrograph_calibration", [im, pim, rim],
                   captions=["実物の写真(左 Si・右 SiO₂)", "較正した模型(区画ごと、縁の帯は使わない)",
                             "残差の RMS / 雑音(区画ごと、RGB)"],
                   signed=[False, False, False], ncols=3,
                   title="写真のカメラ較正: よく似て見えるが、残差は雑音の数倍(中央値 %.1f・最大 %.1f)"
                         % (float(np.median(rim[rim > 0])), float(rim.max())),
                   caption="材料表の n を固定し、膜厚・色温度・利得・ガンマ・周辺減光を区画(40 px 角)の平均に合わせた: d = %.1f nm"
                           "(基準 %.1f nm と %+.0f %%)、T = %.0f K、γ = %.2f。区間は ±%.2f nm と狭いが χ²/ν %.1f で、残差 PCA は %d 成分"
                           "の構造を見つける —— カメラの分光感度(模型は CIE 1931)が足りない。出典: %s"
                           % (th["d"], REF_NM, 100 * (th["d"] / REF_NM - 1), th["T"], th["gamma"],
                              0.5 * (NUMBERS["cam_d_hi"] - NUMBERS["cam_d_lo"]), NUMBERS["cam_chi2"],
                              NUMBERS["cam_struct"], SOURCE))
    del h, w, tr
    landscape_figure(cam, AB)


def save_landscape(name, panels, title, caption):
    """χ² の地形(疑似カラー)を軸つきで並べる: 枠・物理単位の目盛り・軸名・パネルごとのカラーバー・終点の印。

    z の行 0 が縦軸の最大(上が大きい値)、列 0 が横軸の最小。格子は等間隔(log 軸は等比)なので、
    描画域の端をセルの端(格子の値から半刻み外)に合わせる —— セルの中心 = 格子の値。
    拡大は最近傍(値を作らない)。色は viridis、範囲はパネルごとに 0〜最大(カラーバーに数値)。
    """
    if figs.target_dir() is None:
        return None
    import annotate as AN
    lut = np.clip(np.asarray(fs.colorize_depth(np.linspace(0.0, 1.0, 256)[None, :]), np.float64)[0, :, :3], 0.0, 1.0)
    tiles = []
    for z, xs, ys, xlab, ylab, xscale, ptitle, mark in panels:
        z = np.asarray(z, np.float64)
        xs, ys = np.asarray(xs, np.float64), np.asarray(ys, np.float64)
        n_y, n_x = z.shape
        assert n_x == len(xs) and n_y == len(ys) and np.all(np.isfinite(z)), (z.shape, len(xs), len(ys))
        up = max(2, int(round(300.0 / max(n_x, n_y))))
        zmax = float(z.max())
        assert zmax > 0.0, "地形が平ら(χ² が動かない)"
        rgb = np.asarray(fs.colorize_depth(z, vmin=0.0, vmax=zmax), np.float64)[..., :3]
        rgb = np.repeat(np.repeat(np.clip(rgb, 0.0, 1.0), up, axis=0), up, axis=1)
        ph, pw = rgb.shape[:2]
        ml, mt, mr, mb = 92, 70, 132, 70
        H, W = mt + ph + mb, ml + pw + mr
        f = np.ones((H, W, 3))
        f[mt:mt + ph, ml:ml + pw] = rgb
        if xscale == "log":
            rr = math.sqrt(xs[1] / xs[0])
            xlim = (xs[0] / rr, xs[-1] * rr)
        else:
            dx = 0.5 * (xs[1] - xs[0])
            xlim = (xs[0] - dx, xs[-1] + dx)
        dy = 0.5 * (ys[1] - ys[0])
        ylim = (ys[0] - dy, ys[-1] + dy)
        ax = AN.axes_transform((ml, mt, pw, ph), xlim, ylim, xscale=xscale)
        if xscale == "log":                       # 十進の 1/2/5 だけでは 2 本しか立たないので、仮数を細かく
            e0, e1 = int(math.floor(math.log10(xs[0]))), int(math.ceil(math.log10(xs[-1])))
            xt = sorted(round(mm * 10.0 ** e, 6) for e in range(e0, e1 + 1) for mm in (1.0, 1.5, 2.0, 3.0, 5.0, 7.0))
        else:
            xt = AN.nice_ticks(xs[0], xs[-1], n=6)
        xt = [float(t) for t in xt if xlim[0] <= t <= xlim[1]]
        yt = [float(t) for t in AN.nice_ticks(ys[0], ys[-1], n=8) if ylim[0] <= t <= ylim[1]]
        assert 3 <= len(xt) <= 9 and 3 <= len(yt) <= 9, (xt, yt)
        f = AN.axes_frame(f, ax)
        f = AN.ticks(f, ax, xticks=xt, yticks=[], label_fmt="{:g}", font_size=12)
        f = AN.ticks(f, ax, xticks=[], yticks=yt, label_fmt="{:g}", font_size=12)
        f = AN.plot_series(f, ax, [float(mark[0])], [float(mark[1])], kind="scatter", color=(1.0, 1.0, 1.0),
                           marker_size=4)
        f = AN.text_box(f, ptitle, (6, 6), anchor="lt", font_size=13, box_alpha=0.0)
        f = AN.text_box(f, "↑ " + ylab, (ml - 4, mt - 8), anchor="lb", font_size=12, box_alpha=0.0)
        f = AN.text_box(f, xlab + " →", (ml + pw / 2.0, mt + ph + 26), anchor="ct", font_size=12, box_alpha=0.0)
        f = AN.text_box(f, "白い点 = 当てはめの終点", (ml + pw, mt - 8), anchor="rb", font_size=11, box_alpha=0.0)
        f = AN.color_bar(f, lut, (ml + pw + 22, mt, 16, ph), vmin=0.0, vmax=zmax, label_fmt="{:.1f}", font_size=11)
        f = AN.text_box(f, "log10(Δχ²+1)", (ml + pw + 14, mt - 8), anchor="lb", font_size=11, box_alpha=0.0)
        tiles.append(np.clip(np.asarray(f, np.float64), 0.0, 1.0))
    hmax = max(t.shape[0] for t in tiles)
    tiles = [np.vstack([t, np.ones((hmax - t.shape[0], t.shape[1], 3))]) if t.shape[0] < hmax else t for t in tiles]
    body = np.concatenate(tiles, axis=1)
    band = np.ones((60, body.shape[1], 3))
    band = np.asarray(fs.text_box(band, title, (body.shape[1] / 2.0, 8), anchor="ct", font_size=17, box_alpha=0.0),
                      np.float64)
    return figs.save(name, np.clip(np.vstack([band, body]), 0.0, 1.0), caption)


def landscape_figure(cam, AB):
    """★記事の主図 2 枚: 実物の写真で、決まる係数と決まらない組み合わせを地形で見せる。

    (1) χ² の 2 次元の切り口(ほかのつまみは 7 本の当てはめの終点に固定): 色温度 × 周辺減光は 1 点に締まり、
        利得 × ガンマは長い溝になる。色は log10(χ² − 最小 + 1)、暗いほど合う。
    (2) 終点から 1 本ずつ動かしたときと、Fisher 情報の最小固有ベクトル(決まらない組み合わせの向き)に沿って
        動かしたときの Δχ²。横軸はつまみの範囲を 0..1 にした単位(log のつまみは log 軸)での距離。
    """
    r = cam["rich"]
    end = dict(r["diagnostics"]["endpoint_not_an_estimate"])
    region, r2 = cam["region"][cam["checker"]], cam["r2"][cam["checker"]]
    obs = cam["vals"][cam["checker"]]
    sig = cam["sigma"]
    kn = {k["name"]: k for k in CAM_KNOBS if k["name"] != "illum"}
    kn["vig"] = {"name": "vig", "lo": -0.3, "hi": 0.1, "scale": "linear"}
    names = ["d", "A", "B", "T", "gain", "gamma", "vig"]
    crlb = L.simcal_identifiability(r, profile=False)["identifiability"]["crlb"]
    n = 41 if REDUCED else 81

    def chi(th):
        return float(np.sum((obs - camera_blocks(region=region, r2=r2, **th)) ** 2) / sig ** 2)

    def grid(xn, xs, yn, ys):
        out = np.empty((len(ys), len(xs)))
        for i, yv in enumerate(ys):
            for j, xv in enumerate(xs):
                out[i, j] = chi(dict(end, **{xn: float(xv), yn: float(yv)}))
        return np.log10(out - out.min() + 1.0)[::-1]
    Ts = np.linspace(end["T"] - 8 * crlb["T"], end["T"] + 8 * crlb["T"], n)
    vs = np.linspace(end["vig"] - 8 * crlb["vig"], end["vig"] + 8 * crlb["vig"], n)
    gs = np.geomspace(end["gain"] / 2.0, end["gain"] * 2.0, n)
    gms = np.linspace(1.4, 3.2, n)
    det = ", ".join("%s = %s" % (k, ("%.0f K" % v) if k == "T" else "%.3f" % v) for k, v in sorted(r["theta_hat"].items()))
    save_landscape("real_determined_vs_combinations",
                   [(grid("T", Ts, "vig", vs), Ts, vs, "色温度 T [K]", "周辺減光の係数 vig", "linear",
                     "(a) 色温度 × 周辺減光: 1 点に締まる = 決まる", (end["T"], end["vig"])),
                    (grid("gain", gs, "gamma", gms), gs, gms, "利得(log 軸)", "ガンマ γ", "log",
                     "(b) 利得 × ガンマ: 長い溝 = 組み合わせしか決まらない", (end["gain"], end["gamma"]))],
                   title="実物の写真の χ² の地形 —— 決まる係数は点、決まらない組み合わせは溝",
                   caption="Schwarz ら 2024 の顕微鏡写真(Si 上の SiO₂ の縁)を 40 px 角の 52 区画の RGB 平均にし、転送行列 × 黒体の"
                           "光源 × CIE 1931 → sRGB × 利得 × ガンマ × 周辺減光の 7 本のつまみに合わせた終点を通る切り口(ほかのつまみは"
                           "終点に固定、色は log10(χ² − 最小 + 1)、暗いほど合う、上が大きい値)。左は各軸 ±8 σ_CRLB(T %.0f〜%.0f K、"
                           "周辺減光 %.3f〜%.3f)でも谷が 1 点に閉じる。右は利得 ×1/2〜×2・ガンマ 1.4〜3.2 の全域に谷が溝として伸び、"
                           "明るさを上げても γ を上げれば同じ画素値に戻る。simcal_fit が値を出したのは %s だけで、膜厚・屈折率・分散・"
                           "利得・ガンマは共線性指数 γ > 10 で「組み合わせ」として数を出さない。出典: %s"
                           % (Ts[0], Ts[-1], vs[0], vs[-1], det, SOURCE))
    # (2) 1 本ずつ vs 決まらない向き
    def to_u(k, v):
        return math.log(v / k["lo"]) / math.log(k["hi"] / k["lo"]) if k.get("scale") == "log" else \
            (v - k["lo"]) / (k["hi"] - k["lo"])

    def from_u(k, u):
        return k["lo"] * (k["hi"] / k["lo"]) ** u if k.get("scale") == "log" else k["lo"] + u * (k["hi"] - k["lo"])
    u0 = np.array([to_u(kn[nm], max(end[nm], 1e-9) if kn[nm].get("scale") == "log" else end[nm]) for nm in names])
    base = camera_blocks(region=region, r2=r2, **end).ravel()
    h = 1e-4
    J = []
    for j, nm in enumerate(names):
        u = u0.copy()
        u[j] += h
        th = dict(end, **{nm: from_u(kn[nm], u[j])})
        J.append((camera_blocks(region=region, r2=r2, **th).ravel() - base) / (h * sig))
    J = np.column_stack(J)
    w, V = np.linalg.eigh(J.T @ J)
    vmin = V[:, 0] / np.linalg.norm(V[:, 0])
    vmin = vmin * np.sign(vmin[names.index("d")] if abs(vmin[names.index("d")]) > 1e-12 else 1.0)
    steps = np.linspace(-0.08, 0.08, 33)
    chi0 = chi(end)

    def along(vec):
        out = []
        for t in steps:
            u = u0 + t * vec
            th = dict(end, **{nm: from_u(kn[nm], u[j]) for j, nm in enumerate(names)})
            out.append(chi(th) - chi0)
        return np.array(out)
    ser = []
    for nm, col in (("T", "right"), ("vig", "right"), ("d", "neutral"), ("gamma", "neutral")):
        e = np.zeros(len(names))
        e[names.index(nm)] = 1.0
        ser.append(("%s だけ" % nm, steps, np.log10(along(e) + 1.0)))
    alv = along(vmin)
    single = {nm: float(np.max(along(np.eye(len(names))[names.index(nm)]))) for nm in ("d", "gamma")}
    NUMBERS.update({"cam_dir_max": float(alv.max()), "cam_dir_min": float(alv.min()), "cam_single_max": single})
    ser.append(("決まらない組み合わせの向き", steps, np.log10(np.maximum(alv, 0.0) + 1.0)))
    comp = ", ".join("%s %+.2f" % (nm, vmin[j]) for j, nm in enumerate(names) if abs(vmin[j]) >= 0.1)
    NUMBERS["cam_undetermined_direction"] = comp
    NUMBERS["cam_fisher_cond"] = float(w[-1] / max(w[0], 1e-300))
    figs.save_plot("real_undetermined_direction", ser, kinds=["line"] * 5,
                   styles=[None, None, "dashed", "dashed", None],
                   colors=["right", "emphasis", "neutral", "reference", "wrong"],
                   xlabel="終点からの距離(つまみの範囲 = 1 の単位)", ylabel="log10(Δχ² + 1)",
                   title="1 本ずつ動かすと χ² は上がる —— 組み合わせの向きに一緒に動かすと上がらない",
                   caption="実物の写真の 7 本の当てはめの終点から、1 本ずつ(色温度・周辺減光・膜厚・ガンマ)と、Fisher 情報の"
                           "最小固有ベクトル(%s)の向きに動かした。膜厚もガンマも 1 本だけ動かせば画像は大きく変わるのに、"
                           "決まらない組み合わせの向きでは ±0.08 動かしても Δχ² は最大 %.1f(膜厚だけなら %.0f、ガンマだけなら %.0f。"
                           "Fisher 情報の条件数 %.1e)。これが「値を出さない」理由。負の側で Δχ² がわずかに負(最小 %.2f、図では 0 で"
                           "切った)なのは、終点の A が範囲の端 1.38 に張り付き、範囲の外へ逃げたがっているから —— 模型か範囲が違う印で、"
                           "simcal はこの端の値も推定として出さない。出典: %s"
                           % (comp, NUMBERS["cam_dir_max"], single["d"], single["gamma"], NUMBERS["cam_fisher_cond"],
                              NUMBERS["cam_dir_min"], SOURCE))


def main():
    t0 = time.process_time()
    print("PoC 実物の画像の誤差から薄膜の模型の係数を合わせる(予算 %s)" % ("reduced" if REDUCED else "full"))
    lam_all, Y, _cov = load_spectra()
    sigma, g_bare, white = noise_floor(lam_all, Y)
    A0, B0, dn = cauchy_of_table(lam_all)
    NUMBERS.update({"sigma": sigma, "white": white, "g_bare": g_bare, "cauchy": (A0, B0, dn)})
    print("   雑音の床(裸の Si の実測 vs 材料表の Si、利得 %.4f)σ = %.5f、白色の分(2 階差分)%.5f"
          % (g_bare, sigma, white))
    print("   材料表の SiO₂ を Cauchy に: A = %.5f、B = %.0f nm²(440〜950 nm で最大 %.1e)" % (A0, B0, dn))
    blocks = load_blocks()
    plan = chapter_plan(blocks)
    syn = chapter_synthetic(lam_all, sigma, (A0, B0))
    real = chapter_real_spectrum(lam_all, Y, sigma, (A0, B0))
    poor = chapter_poor(lam_all, Y, sigma, (A0, B0), white)
    cam = chapter_micrograph(blocks, (A0, B0))
    chapter_probes(lam_all, Y, sigma, white, real, plan, syn, blocks)
    if figs.target_dir() is not None:
        make_figures(lam_all, Y, sigma, (A0, B0), plan, syn, real, poor, cam)
    el = time.process_time() - t0
    print("\n所要(この PoC の CPU 時間)%.1f s、門 %d 件中 NG %d 件" % (el, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS  poc_simcal_thin_film")


if __name__ == "__main__":
    main()
