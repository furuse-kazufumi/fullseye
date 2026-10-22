# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: テレセンの実画像から撮像模型の係数を合わせる —— 倍率は論文と合い、入射瞳までの距離は「1 m より遠い」までしか言えない。

    py -3.11 examples/poc_simcal_telecentric.py

【問い】``poc_telecentric_metrology`` の実画像の章は、29.5° 傾いたアライメント板(円の間隔 1 mm)のリングの中心線を
放射状の測定線で拾い、同心の相似な楕円の族を当てて 252.13 px/mm を出した。ここでは同じ点に**撮像の模型**(板の傾き・
向き・倍率 [px/mm]・半径方向の歪曲 k1・入射瞳までの距離の逆数 1/L = テレセン度)を sim-to-real 較正(``simcal``)で
当て、(1) どの係数が決まり、(2) その不確かさは正直か、を問う。観測は「穴の中心から角度 a の測定線の上で、リング k の
中心線までの距離 d」(測定線 1 本 = 1 つの値)。模型は板の上の円 ρ_k = k + ρ0 [mm] を、傾き → 向き → 倍率 →
透視(光軸 = 画像の中心のまわりに L/(L − z))→ 歪曲(画像の中心のまわりに 1 + k1 r²)と写し、測定線との交点をニュートン法で解く。

  1. **合成: 模型の係数を回収する**: 実画像と同じ配置(リング 8 本、外側ほど影で弧が短い)の点を、模型とは別の離散化
     (円を 2 万点の折れ線で写し、測定線との交差を線形補間)で作り、測定線ごとに独立な雑音 1.2 px を足す。門: 8 つの係数の
     Fisher 距離が χ²(8) に従う、``simcal_validate`` の 6 つの門を全部通る。★入射瞳の真値を 2 章の通常のレンズ
     (f = 100 mm、入射瞳 302 mm、``telecentric.chief_ray_angle`` の閉形式)にすると、1/L = 3.31 /m を下界の 4 倍以内で回収する。
  2. **合成: 決まらない係数**: 傾けない板(円が円に写る)では、楕円の向きは画像を変えない —— Morris のふるい
     (``simcal_screen``)が向きを「効かない」と言い、``simcal_fit`` は向きの値を返さない(閉形式: 円に向きは無い)。
  3. **合成: 食い違いのある板**: リングごとに滑らかな歪み(実の板の印刷や縁の読みの癖を模した、0〜6 次の高調波の和 ——
     0 次 = リングの半径の癖、1 次 = リングの中心のずれ —— RMS 0.7 px)を足し、その分を白い分散とみなして(雑音の σ を
     学習の残差から取って)合わせる。係数は数を返し 6 つの門も通るのに、Laplace(Fisher の逆)の不確かさは楽観的
     (全係数の Fisher 距離の p = 1e-5、1/L のジャックナイフ / Laplace = 2.4)。★リングを 1 本ずつ抜いて解き直すジャックナイフ
     (リングごとの食い違いは独立)なら真値を覆う。食い違いが無ければ、ジャックナイフと Laplace は同じ大きさ(門は両向き)。
  0. **実画像(主役)**: Stark ほか(Sci. Rep. 2025、CC BY 4.0)のアライメント板の生画像(取得とキャッシュは
     ``poc_telecentric_metrology`` と共有、ネットの無い CI では記録値を印字して飛ばす)。点の拾い方は同じ
     (``plate_ring_points``)。雑音は模型と独立に、測定線 4° おきの点の局所 2 次式のあてはめの残差(純粋誤差)から取る。
     門: ★この雑音(1.12 px)で合わせると絶対の門(χ² の上側確率、p = 7e-9)が落ち、simcal_validate は数を取り下げる ——
     残差(1.35 px)は純粋誤差より大きく、リングごと・30° ごとの平均に雑音では説明できない形がある(板と縁の読みの
     食い違い)。その分を白い分散として足すと 6 つの門を通り、この板では Laplace の不確かさがリングのジャックナイフと
     同じ大きさになる(合成の 3 章と違い、食い違いが係数の形を真似るほど低次ではない —— 確かめたので言える)。
     倍率は 252.14 ± 0.18 px/mm(論文の K1 = 252.0、K2 = 251.8 / 253.0 の範囲)、1/L = 0.50 ± 0.18 /m で入射瞳は 1.16 m
     より遠い(2σ)。2 章の通常の f = 100 mm(302 mm)と f = 25 mm(78 mm)はこれで否定できる。★1/L が 0 から 2.7σ 離れて
     いるのは未解決(下の「正直に」)。

【外部真値】合成の注入値(模型と別の離散化)、2 章のレンズの入射瞳の閉形式、円に向きが無いこと、論文の K1・K2。
【学習】0。【較正】板の傾き・向き・中心・倍率・リングの半径の基準・k1・1/L(simcal)。

【来歴(実画像)】A. W. Stark, A. Osadare, M. Guo, G. J. Gentsch, D. Boettger, G. Brehm, C. Franke, "Telecentric stereo
3D imaging with isotropic micrometer resolution bridges macro- and microscale in small Lepidopterans", Scientific Reports
15, 28690 (2025), doi:10.1038/s41598-025-13795-6(CC BY 4.0)。画像は figshare collection doi:10.6084/m9.figshare.c.7652423
の item 28322132(CC BY 4.0)。改変: グレースケール化・縮小・計測の線の描き込み。repo には画像を入れない。

【来歴(方法)】Kennedy and O'Hagan, J. R. Stat. Soc. B 63(3):425 (2001)(モデルの食い違い)/ Brynjarsdóttir and O'Hagan,
Inverse Problems 30:114007 (2014)(較正した係数が食い違いを吸い込む)/ Raue et al., Bioinformatics 25(15):1923 (2009)
(同定性)/ Morris, Technometrics 33(2):161 (1991)(ふるい)/ Efron, Ann. Stat. 7(1):1 (1979)、Quenouille 1949・Tukey 1958
(ジャックナイフ)/ Brown, Photogramm. Eng. 32(3):444 (1966)(半径方向の歪曲)。

★正直に書いておくこと:
  * 透視は光軸を画像の中心に置いた。実機の光軸が画像の中心からずれていれば、その分は板の中心のずれと 1/L に混ざる。
  * 純粋誤差は「4° おきの 7 点(24°)の局所 2 次式で説明できない分」。24° より細かい食い違いは雑音に数えられる。
  * 隣の測定線(1° おき)の残差は相関する(ずれ 1° で 0.47、粒と線の太さ)ので、学習とホールドアウトは 4° おきの 2 組に分けた
    (0°, 4°, … と 2°, 6°, …)。2 つの組は同じリングの同じ食い違いを見るので、ホールドアウトは食い違いには盲目 ——
    食い違いを見るのはジャックナイフの側。残差 PCA(リング × 測定線の行列)はこの食い違いを「白」と言った(リングごとに
    形がばらばらで低ランクでない)—— 残差 PCA は食い違いの検出器として完全ではない。
  * 実画像の 1/L = 0.50 ± 0.18 /m は 0 から 2.7σ(入射瞳 2 m 相当)。実画像の章の β の解析(``poc_telecentric_metrology``、
    リングの中心のずれだけを見る)は入射瞳は 10.5 m より遠いと言う。ここの 1/L は倍率の傾きも見るので、光軸の位置(画像の
    中心と仮定)や板のリングの癖と混ざりうる。3σ に届かない差なので、どちらとも決めない(未解決)。

EXTEND: p1・p2(接線方向の歪曲)と k2 を足す、光軸の位置をつまみにする(板を 2 姿勢以上で撮らないと 1/L と交絡するはず ——
ふるいで確かめてから)。リングごとの食い違いを、リングごとの低次の高調波の局外つまみとして模型に入れる(Kennedy–O'Hagan の
食い違いの項)。
"""
from __future__ import annotations

import importlib.util
import inspect
import math
import os
import sys
import time

import numpy as np
from scipy.stats import chi2 as _chi2

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402  公開経路(fs.ledger.<名前>)から呼ぶ
import telecentric as TC  # noqa: E402

L = fs.ledger
REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"

FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}
ALPHA = 1e-3

#: 画像の大きさ(実画像 2848 × 2848)と、透視・歪曲の中心(光軸 = 画像の中心とみなす)。
IMG = 2848
C0 = np.array([(IMG - 1) / 2.0, (IMG - 1) / 2.0])
#: つまみ(名前・範囲・単位・初期値)。k1 は r を 1000 px で割った r² の係数、inv_L は 1/L [1/m]。
KNOBS = [{"name": "px_per_mm", "lo": 240.0, "hi": 265.0, "unit": "px/mm", "init": 251.0},
         {"name": "tilt_deg", "lo": -45.0, "hi": 45.0, "unit": "deg", "init": 25.0},
         {"name": "phi_deg", "lo": -130.0, "hi": -40.0, "unit": "deg", "init": -85.0},
         {"name": "oy", "lo": -30.0, "hi": 30.0, "unit": "px", "init": 0.0},
         {"name": "ox", "lo": -30.0, "hi": 30.0, "unit": "px", "init": 0.0},
         {"name": "rho0", "lo": 0.2, "hi": 0.8, "unit": "mm", "init": 0.5},
         {"name": "k1", "lo": -3e-3, "hi": 3e-3, "unit": "1/(1000 px)^2", "init": 0.0},
         {"name": "inv_L", "lo": -15.0, "hi": 15.0, "unit": "1/m", "init": 0.0}]
NAMES = [k["name"] for k in KNOBS]
#: 実画像に似せた合成の配置: リング 1〜8 の見える弧の半分の幅 [度] —— 外側ほど影で短い —— と、その中心の向き。
ARC_HALF = (180, 180, 180, 88, 74, 58, 39, 17)
ARC_CENTRE_DEG = 150.0
#: 合成の真値(実画像の当てはめに近い値)。
TRUTH = {"px_per_mm": 252.1, "tilt_deg": 29.5, "phi_deg": -84.15, "oy": -8.5, "ox": 7.4, "rho0": 0.496, "k1": 4e-4,
         "inv_L": 0.0}
SIGMA_SYN = 1.2


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


# --------------------------------------------------------------------------- #
# 撮像の模型                                                                    #
# --------------------------------------------------------------------------- #
def project(th, rho, t, h):
    """板の上の点(半径 rho [mm]、角度 t)→ 画像の (行, 列)。h = 穴の中心(板の中心の当たり)。

    傾き τ は板の x 軸まわり: (x, y, z) = (ρ cos t, ρ sin t cos τ, ρ sin t sin τ)。向き φ で画像へ回し、倍率 s を掛け、
    板の中心 h + (oy, ox) に置く。透視は光軸(画像の中心 C0)のまわりに 1/(1 − z/L)、歪曲は C0 のまわりに 1 + k1 (r/1000)²。
    """
    s, tau, phi = th["px_per_mm"], math.radians(th["tilt_deg"]), math.radians(th["phi_deg"])
    x = rho * np.cos(t)
    y = rho * np.sin(t)
    z = y * math.sin(tau) / 1000.0                                   # [m]
    u, v = x * s, y * math.cos(tau) * s
    dx = u * math.cos(phi) - v * math.sin(phi)
    dy = u * math.sin(phi) + v * math.cos(phi)
    wy = h[0] + th["oy"] - C0[0] + dy
    wx = h[1] + th["ox"] - C0[1] + dx
    g = 1.0 / (1.0 - z * th["inv_L"])
    wy, wx = wy * g, wx * g
    r2 = (wy * wy + wx * wx) / 1e6
    f = 1.0 + th["k1"] * r2
    return C0[0] + wy * f, C0[1] + wx * f


def ray_distance(th, h, a, rings, t0, iters=12):
    """測定線(穴の中心 h から角度 a)とリングの写像の交点までの距離 d(ニュートン法で板の角度 t を解く)。

    a・rings・t0 は同じ形の配列(リング × 測定線の格子)。
    """
    t = t0.copy()
    rho = rings + th["rho0"]
    ey, ex = np.sin(a), np.cos(a)
    for _ in range(iters):
        py_, px_ = project(th, rho, t, h)
        f = (py_ - h[0]) * ex - (px_ - h[1]) * ey
        py2, px2 = project(th, rho, t + 1e-6, h)
        f2 = (py2 - h[0]) * ex - (px2 - h[1]) * ey
        t = t - f / ((f2 - f) / 1e-6)
    py_, px_ = project(th, rho, t, h)
    return (py_ - h[0]) * ey + (px_ - h[1]) * ex


def t_start(a, h, phi_deg, q):
    """ニュートン法の出発点: 測定線の向きを、族の楕円の向き・縦横比で板の角度へ戻した値(答えはこれに依らない)。"""
    phi = math.radians(phi_deg)
    dy, dx = np.sin(a), np.cos(a)
    u = dx * math.cos(phi) + dy * math.sin(phi)
    v = -dx * math.sin(phi) + dy * math.cos(phi)
    return np.arctan2(v / q, u)


def grid(h, degs, phi_deg, q):
    """リング 1〜8 × 測定線(*degs* [度])の格子。"""
    a1 = np.radians(np.asarray(degs, float))
    rings = np.repeat(np.arange(1.0, 9.0)[:, None], a1.size, 1)
    a = np.repeat(a1[None, :], 8, 0)
    return {"h": np.asarray(h, float), "degs": np.asarray(degs), "a": a, "rings": rings, "t0": t_start(a, h, phi_deg, q)}


def make_model(g, sigma, label, fixed=None):
    """simmodel: 出力 = 格子の各測定線の距離 d(リング × 測定線の「画像」)、雑音はガウス σ [px]。"""
    fixed = dict(fixed or {})

    def plate_op(**kw):
        return ray_distance({n: kw[n] for n in NAMES}, g["h"], g["a"], g["rings"], g["t0"])
    # simcal はつまみの名前を op の引数から確かめるので、**kw の op に引数の一覧を名乗らせる
    plate_op.__signature__ = inspect.Signature(
        [inspect.Parameter(n, inspect.Parameter.KEYWORD_ONLY, default=k["init"]) for n, k in zip(NAMES, KNOBS)])
    knobs = []
    for k in KNOBS:
        d = dict(k, step=0, arg=k["name"])
        if k["name"] in g.get("init", {}):
            d["init"] = g["init"][k["name"]]
        if k["name"] in fixed:
            d["fixed"] = fixed[k["name"]]
        knobs.append(d)
    return L.simcal_model(chain=[{"op": plate_op}], knobs=knobs, noise={"kind": "gaussian", "sigma": float(sigma)},
                          label=label)


def observe(model, D, mask, split="train"):
    """観測の格子 *D*(測っていない所は何でもよい)と、測った所の印 *mask* を付ける。"""
    return L.simcal_observe(model, [np.where(mask, D, 0.0)], roi=mask, split=split)


def tau_f(n_hold, n_train, n_free):
    """ホールドアウト / 学習の χ²/自由度 の比の上限: 正しい模型なら F(ν_ho, ν_tr) に従うので、上側 α の点 − 1。"""
    from scipy.stats import f as _f
    return float(_f.ppf(1.0 - ALPHA, n_hold, n_train - n_free) - 1.0)


def validate(r, g, D, mask_ho, sigma, label):
    m = make_model(g, sigma, label)
    n_tr = int(r["model"]["observed"]["mask"][0].sum())
    return L.simcal_validate(r, observe(m, D, mask_ho, split="holdout"),
                             tau=tau_f(int(mask_ho.sum()), n_tr, len(r["theta_hat"]) or len(NAMES)))


def fit(g, D, mask, sigma, label, fixed=None):
    return L.simcal_fit(observe(make_model(g, sigma, label, fixed), D, mask), allow_undetermined=True)


def residual(r, g, D):
    return D - ray_distance(r["theta_hat"], g["h"], g["a"], g["rings"], g["t0"])


# --------------------------------------------------------------------------- #
# 合成の点(模型と別の離散化)                                                  #
# --------------------------------------------------------------------------- #
def synth_grid(truth, seed, sigma=SIGMA_SYN, discrepancy=0.0):
    """真値の係数でリング 1〜8 を 2 万点の折れ線に写し、穴の中心から 1° おきの測定線との交差を線形補間で求め、雑音を足す。

    返り値 (D, mask): 8 × 360 の距離と、測れた所の印(外側のリングほど影で弧が短い、実画像に似せた配置)。
    *discrepancy* > 0 なら、リングごとに板の上の角度 t の滑らかな関数(0〜6 次の高調波 —— 0 次 = リングの半径の癖、1 次 =
    リングの中心のずれ —— 乱数の振幅と位相)を半径の向きに足す(RMS がこの値 [px])。実の板のリングの印刷や縁の読みの癖の
    模型。乱数は呼び出しごとの専用の生成器。
    """
    rng = np.random.default_rng(seed)
    h = np.array([1231.1, 1966.1])
    tt = np.linspace(-np.pi, np.pi, 20001)
    D = np.zeros((8, 360))
    M = np.zeros((8, 360), bool)
    for ring, half in zip(range(1, 9), ARC_HALF):
        rho = ring + truth["rho0"]
        py_, px_ = project(truth, rho, tt, h)
        if discrepancy > 0:
            bump = np.full_like(tt, rng.normal(0.0, 1.0))
            for n in range(1, 7):
                bump += rng.normal(0, 1.0) * np.cos(n * tt + rng.uniform(0, 2 * np.pi)) / n
            bump *= discrepancy / np.sqrt(np.mean(bump ** 2))
            ry, rx = py_ - h[0], px_ - h[1]
            rr = np.hypot(ry, rx)
            py_, px_ = py_ + bump * ry / rr, px_ + bump * rx / rr
        for deg in range(360):
            if abs((deg - ARC_CENTRE_DEG + 180.0) % 360.0 - 180.0) > half:
                continue
            a = math.radians(deg)
            cr = (py_ - h[0]) * math.cos(a) - (px_ - h[1]) * math.sin(a)
            fw = (py_ - h[0]) * math.sin(a) + (px_ - h[1]) * math.cos(a)
            idx = np.flatnonzero((np.sign(cr[:-1]) != np.sign(cr[1:])) & (fw[:-1] > 0))
            if idx.size != 1:
                continue
            i = int(idx[0])
            w = cr[i] / (cr[i] - cr[i + 1])
            D[ring - 1, deg] = (1 - w) * fw[i] + w * fw[i + 1] + sigma * rng.standard_normal()
            M[ring - 1, deg] = True
    return h, D, M


def split_cols(D, M):
    """学習 = 0°, 4°, 8° … の測定線、ホールドアウト = 2°, 6°, …(隣の 1° は残差が相関するので間を空ける)。"""
    cols_tr, cols_ho = np.arange(0, 360, 4), np.arange(2, 360, 4)
    return (cols_tr, D[:, cols_tr], M[:, cols_tr]), (cols_ho, D[:, cols_ho], M[:, cols_ho])


def fisher_distance(result, truth):
    idf = L.simcal_identifiability(result, at=truth, profile=False)["identifiability"]
    names = [n for n in idf["knobs"] if n in result["theta_hat"]]
    ix = [idf["knobs"].index(n) for n in names]
    F = np.asarray(idf["fisher"], float)[np.ix_(ix, ix)]
    d = np.array([result["theta_hat"][n] - truth[n] for n in names])
    return float(d @ F @ d), len(names), idf


def laplace_sd(result):
    return L.simcal_identifiability(result, profile=False)["identifiability"]["crlb"]


def ring_jackknife(g, D, mask, sigma, label):
    """リングを 1 本ずつ抜いて(その行の印を消して)解き直す。リングごとの食い違いは独立とみなした各係数の標準誤差。"""
    rows = [i for i in range(8) if mask[i].any()]
    ests = []
    for i in rows:
        mk = mask.copy()
        mk[i] = False
        r = fit(g, D, mk, sigma, label + " -ring %d" % (i + 1))
        ests.append([r["theta_hat"].get(n, np.nan) for n in NAMES])
    E = np.array(ests)
    n = len(rows)
    se = np.sqrt((n - 1) / n * np.nansum((E - np.nanmean(E, 0)) ** 2, 0))
    return dict(zip(NAMES, se)), n


def optimism_p(se_jack, se_lap, n):
    """「Laplace の不確かさは正直」の帰無仮説の下で (n − 1) (SE_jack / SE_lap)² ~ χ²(n − 1) とみなした上側確率。"""
    r = se_jack / se_lap
    return float(_chi2.sf((n - 1) * r * r, n - 1)), r


def calibrate(g_tr, D_tr, M_tr, g_ho, D_ho, M_ho, label, sigma=None):
    """学習の列で合わせ、σ が無ければ残差から取って合わせ直し、ホールドアウトの列で 6 つの門にかける。"""
    if sigma is None:
        r0 = fit(g_tr, D_tr, M_tr, 1.5, label + " provisional")
        res = residual(r0, g_tr, D_tr)[M_tr]
        sigma = float(np.sqrt(np.sum(res ** 2) / (res.size - len(NAMES))))
    r = fit(g_tr, D_tr, M_tr, sigma, label)
    v = validate(r, g_ho, D_ho, M_ho, sigma, label)
    return r, v, sigma


# --------------------------------------------------------------------------- #
# 1〜3. 合成                                                                    #
# --------------------------------------------------------------------------- #
def chapter_synthetic(lenses):
    print("\n1. 合成: 実画像と同じ配置の点から、模型の 8 つの係数を回収する")
    out = {}
    L_ento = TC.chief_ray_angle(lenses["ento"], 4.0)["pupil_distance_mm"]
    q0 = math.cos(math.radians(TRUTH["tilt_deg"])) + 0.01

    def grids(h, cols_tr, cols_ho, phi, q):
        return grid(h, cols_tr, phi, q), grid(h, cols_ho, phi, q)

    for case, inv_l, seed in (("telecentric", 0.0, 11), ("entocentric", 1000.0 / L_ento, 12)):
        truth = dict(TRUTH, inv_L=inv_l)
        h, D, M = synth_grid(truth, seed)
        (ct, Dt, Mt), (ch, Dh, Mh) = split_cols(D, M)
        gt, gh = grids(h, ct, ch, TRUTH["phi_deg"] + 2.0, q0)
        r, v, _s = calibrate(gt, Dt, Mt, gh, Dh, Mh, case, sigma=SIGMA_SYN)
        d2, k, idf = fisher_distance(r, truth)
        p = float(_chi2.sf(d2, k))
        th, sd = r["theta_hat"], idf["crlb"]
        print("   %s(1/L 真値 %.3f /m): 点 %d(学習 %d・ホールドアウト %d)。px/mm %.3f ± %.3f、傾き %.3f°、k1 %.2e ± %.1e、"
              "1/L %.3f ± %.3f /m。Fisher 距離 %.1f(χ²(%d) の p = %.3f)、6 つの門 %s"
              % (case, inv_l, int(M.sum()), int(Mt.sum()), int(Mh.sum()), th["px_per_mm"], sd["px_per_mm"],
                 th["tilt_deg"], th["k1"], sd["k1"], th["inv_L"], sd["inv_L"], d2, k, p,
                 "全部通過" if v["validation"]["passed"] else "落ちた %s" % v["validation"]["failed"]))
        out[case] = {"r": r, "v": v, "p": p, "truth": truth, "sd": sd}
        NUMBERS["syn_%s_p" % case] = p
    t = out["telecentric"]
    gate("合成(テレセン): 8 つの係数は下界どおりに散り(Fisher 距離の χ²(8) の p = %.3f ≥ %g)、simcal_validate の 6 つの門を"
         "全部通る" % (t["p"], ALPHA), t["p"] >= ALPHA and t["v"]["validation"]["passed"])
    e = out["entocentric"]
    ei, es = e["r"]["theta_hat"]["inv_L"], e["sd"]["inv_L"]
    gate("合成(2 章の通常の f = 100 mm、入射瞳 %.0f mm): 1/L = %.3f ± %.3f /m は閉形式 %.3f /m と %.1fσ(< 4σ)、0 から %.0fσ"
         % (L_ento, ei, es, 1000.0 / L_ento, abs(ei - 1000.0 / L_ento) / es, ei / es),
         abs(ei - 1000.0 / L_ento) < 4.0 * es and ei / es > 10.0 and e["p"] >= ALPHA)
    out["L_ento"] = L_ento
    out["L_fa25"] = TC.chief_ray_angle(lenses["fa25"], 4.0)["pupil_distance_mm"]

    print("\n2. 合成: 傾けない板では、楕円の向きは決まらない(円に向きは無い)")
    flat = dict(TRUTH, tilt_deg=0.0)
    h, D, M = synth_grid(flat, 21)
    (ct, Dt, Mt), _ho = split_cols(D, M)
    gt = grid(h, ct, TRUTH["phi_deg"], 1.0)
    gt["init"] = {"tilt_deg": 0.0}
    m = observe(make_model(gt, SIGMA_SYN, "untilted", fixed={"inv_L": 0.0}), Dt, Mt)
    scr = L.simcal_screen(m, size=6)
    r = L.simcal_fit(m, allow_undetermined=True)
    print("   ふるい: %s" % ", ".join("%s %s" % (n, scr["class"][n]) for n in NAMES if n in scr["class"]))
    print("   当てはめ: 値を返した %s、返さなかった %s" % (sorted(r["theta_hat"]),
                                                {n: v.split(":")[0] for n, v in r["undetermined"].items()}))
    gate("★傾けない板では楕円の向き φ を、ふるいが「効かない」と言い(%s)、simcal_fit は値を返さない(%s)。倍率は決まる"
         % (scr["class"].get("phi_deg"), r["undetermined"].get("phi_deg", "値あり").split(":")[0]),
         scr["class"].get("phi_deg") == "no_influence" and "phi_deg" not in r["theta_hat"]
         and "px_per_mm" in r["theta_hat"])
    out["untilted"] = {"screen": scr, "r": r}

    print("\n3. 合成: リングごとに滑らかな食い違いがある板 —— 係数は合うのに、Laplace の不確かさは楽観的になる")
    rows = {}
    for case, disc, seed in (("clean", 0.0, 31), ("discrepant", 0.7, 32)):
        h, D, M = synth_grid(TRUTH, seed, discrepancy=disc)
        (ct, Dt, Mt), (ch, Dh, Mh) = split_cols(D, M)
        gt, gh = grids(h, ct, ch, TRUTH["phi_deg"] + 2.0, q0)
        r, v, s_tot = calibrate(gt, Dt, Mt, gh, Dh, Mh, case)          # σ は学習の残差から(実画像の章と同じ手順)
        lap = laplace_sd(r)
        jk, nr = ring_jackknife(gt, Dt, Mt, s_tot, case)
        pj, ratio = optimism_p(jk["inv_L"], lap["inv_L"], nr)
        z_lap = abs(r["theta_hat"]["inv_L"] - TRUTH["inv_L"]) / lap["inv_L"]
        z_jk = abs(r["theta_hat"]["inv_L"] - TRUTH["inv_L"]) / jk["inv_L"]
        d2, k, _idf = fisher_distance(r, TRUTH)
        pf = float(_chi2.sf(d2, k))
        rows[case] = {"r": r, "v": v, "lap": lap, "jk": jk, "pj": pj, "ratio": ratio, "z_lap": z_lap, "z_jk": z_jk,
                      "pf": pf, "s_tot": s_tot}
        print("   %-10s σ(残差から)%.2f px、6 つの門 %s。1/L = %.3f /m:Laplace ± %.3f(真値から %.1fσ)、リングの"
              "ジャックナイフ ± %.3f(%.1fσ)、比 %.1f(p = %.2g)。全係数の Fisher 距離の p = %.2g"
              % (case, s_tot, "全部通過" if v["validation"]["passed"] else "落ちた %s" % v["validation"]["failed"],
                 r["theta_hat"]["inv_L"], lap["inv_L"], z_lap, jk["inv_L"], z_jk, ratio, pj, pf))
    c, d = rows["clean"], rows["discrepant"]
    NUMBERS.update({"syn_disc_ratio": d["ratio"], "syn_clean_ratio": c["ratio"]})
    gate("★合成(食い違いあり): 6 つの門は通る(%s)のに Laplace の不確かさは楽観的 —— 全係数の Fisher 距離の p = %.1e < %g、"
         "ジャックナイフ / Laplace = %.1f(帰無仮説「Laplace は正直」の p = %.1e < %g)。ジャックナイフなら 1/L の真値は %.1fσ"
         % ("全部通過" if d["v"]["validation"]["passed"] else "落ちた", d["pf"], ALPHA, d["ratio"], d["pj"], ALPHA, d["z_jk"]),
         d["v"]["validation"]["passed"] and d["pf"] < ALPHA and d["pj"] < ALPHA and d["z_jk"] < 4.0)
    gate("探針(食い違いなし): 同じ手順で Laplace とジャックナイフは同じ大きさ(比 %.1f、p = %.2f ≥ %g)、Fisher 距離の p = %.2f"
         % (c["ratio"], c["pj"], ALPHA, c["pf"]), c["pj"] >= ALPHA and c["pf"] >= ALPHA)
    out["disc"] = rows
    return out


# --------------------------------------------------------------------------- #
# 0. 実画像                                                                     #
# --------------------------------------------------------------------------- #
#: 2026-10-18 の実測(ネットの無い CI ではこれを印字して章を飛ばす。門には使わない)。
REAL_RECORDED = {"px_per_mm": 252.14, "se": 0.18, "inv_L": 0.50, "inv_L_se": 0.18, "pupil_min_m": 1.16}


def _load_sibling(name):
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), name + ".py")
    spec = importlib.util.spec_from_file_location("_sib_" + name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pure_error(R, M, degs, win=7, order=2):
    """純粋誤差: リングごとに測れた測定線を角度順に並べ、連続した *win* 点(間が 8° を超えたら切る)に *order* 次式を
    当てた残差の分散。模型と独立な雑音の見積もり(24° より細かい揺らぎ)。返り値 (σ, 自由度)。"""
    rss, dof = 0.0, 0
    for i in range(R.shape[0]):
        x = np.asarray(degs, float)[M[i]]
        y = R[i][M[i]]
        cut = np.flatnonzero(np.diff(x) > 8) + 1
        for sx, sy in zip(np.split(x, cut), np.split(y, cut)):
            for i0 in range(0, len(sx) - win + 1, win):
                xx, yy = sx[i0:i0 + win], sy[i0:i0 + win]
                A = np.vander(xx - xx.mean(), order + 1)
                c, *_ = np.linalg.lstsq(A, yy, rcond=None)
                rss += float(((yy - A @ c) ** 2).sum())
                dof += win - order - 1
    return math.sqrt(rss / dof), dof


def chapter_real(tm, syn):
    print("\n0. 実画像 —— Stark ほか(Sci. Rep. 2025)のアライメント板の生画像に、撮像の模型を合わせる(%s)" % tm.REAL_SOURCE_SHORT)
    paths, why = tm.real_fetch()
    if paths is None:
        r = REAL_RECORDED
        print("   [skip] %s。2026-10-18 の実測: 純粋誤差で合わせると絶対の門が落ちる(板と縁の読みの食い違い)。食い違いを"
              "白い分散として足すと 6 つの門を通り、倍率 %.2f ± %.2f px/mm(論文の K1 = 252.0)、1/L = %.2f ± %.2f /m"
              "(入射瞳は %.2f m より遠い、2σ)" % (why, r["px_per_mm"], r["se"], r["inv_L"], r["inv_L_se"],
                                               r["pupil_min_m"]))
        return None
    g = np.asarray(tm.fs_read(paths["plate"]), float)
    g = g / g.max()
    rp = tm.plate_ring_points(g)
    h = np.array([rp["cy"], rp["cx"]])
    P, ks = rp["P"], rp["ks"][rp["idx"]]
    a = np.arctan2(P[:, 0] - h[0], P[:, 1] - h[1])
    deg = np.round(np.degrees(a)).astype(int) % 360
    D = np.zeros((8, 360))
    M = np.zeros((8, 360), bool)
    for kk, dg, dd in zip(ks, deg, np.hypot(P[:, 0] - h[0], P[:, 1] - h[1])):
        if 1 <= kk <= 8 and not M[kk - 1, dg]:
            D[kk - 1, dg], M[kk - 1, dg] = dd, True
    phi0, q0 = -85.0, float(rp["q"])
    init = {"px_per_mm": float(rp["s"]), "tilt_deg": math.degrees(math.acos(rp["q"])), "phi_deg": phi0,
            "rho0": float(rp["ph"] / rp["s"])}
    # 外れ点(十字線の交点など): 全点で 1 回合わせ、残差が MAD の 4 倍を超える点を落とす(実画像の章と同じ規則)
    gall = grid(h, np.arange(360), phi0, q0)
    gall["init"] = init
    r_all = fit(gall, D, M, 1.5, "real all")
    R = residual(r_all, gall, D)
    med = np.median(R[M])
    mad = 1.4826 * np.median(np.abs(R[M] - med))
    out = M & (np.abs(R - med) > 4 * mad)
    M = M & ~out
    (ct, Dt, Mt), (ch, Dh, Mh) = split_cols(D, M)
    gt, gh = grid(h, ct, phi0, q0), grid(h, ch, phi0, q0)
    gt["init"] = gh["init"] = init
    print("   点 %d(外れ点 %d を落とした)、リング %s。学習 %d 点(0°, 4°, …)・ホールドアウト %d 点(2°, 6°, …)"
          % (int(M.sum()), int(out.sum()), "・".join(str(i + 1) for i in range(8) if M[i].any()), int(Mt.sum()),
             int(Mh.sum())))
    # (a) 模型と独立な雑音(純粋誤差)で合わせる
    r1 = fit(gt, Dt, Mt, 1.5, "real provisional")
    Rt = residual(r1, gt, Dt)
    s_pe, dof_pe = pure_error(Rt, Mt, ct)
    rA = fit(gt, Dt, Mt, s_pe, "real pure-error")
    vA = L.simcal_discrepancy(validate(rA, gh, Dh, Mh, s_pe, "real pure-error"))
    g6 = vA["validation"]["gates"]["fit_consistent_with_noise"]
    rms = float(np.sqrt(np.mean(Rt[Mt] ** 2)))
    print("   (a) 純粋誤差 σ = %.2f px(自由度 %d)で合わせる: 残差 RMS %.2f px、χ²/自由度 学習 %.2f(p %.1e)・ホールドアウト "
          "%.2f(p %.1e)、残差 PCA(リング × 測定線)%s → %s"
          % (s_pe, dof_pe, rms, g6["train"]["chi2_per_nu"], g6["train"]["p"], g6["holdout"]["chi2_per_nu"],
             g6["holdout"]["p"], vA["discrepancy"]["verdict"],
             "6 つの門を通る" if vA["validation"]["passed"] else "落ちた %s(数を取り下げる)" % vA["validation"]["failed"]))
    bins = []
    for i in range(8):
        for b0 in range(0, 360, 30):
            mm = Mt[i] & (ct >= b0) & (ct < b0 + 30)
            if mm.sum() >= 4:
                bins.append((i + 1, b0, float(Rt[i][mm].mean()), int(mm.sum())))
    bz = np.array([bm / (s_pe / math.sqrt(n)) for _k, _b, bm, n in bins])
    pb = float(_chi2.sf(float((bz ** 2).sum()), len(bz)))
    print("   リングごと・30° ごとの残差の平均 %d 個: 純粋誤差で割った z の 2 乗和 %.0f(χ²(%d) の p = %.1e)"
          % (len(bz), float((bz ** 2).sum()), len(bz), pb))
    gate("★実画像: 模型と独立な雑音(純粋誤差 %.2f px)で合わせると、絶対の門(χ² の上側確率)が落ち、simcal_validate は数を"
         "取り下げる(学習の p = %.1e < %g)。リングごと・30° ごとの残差の平均も雑音では説明できない(p = %.1e)—— 板と縁の"
         "読みの食い違い" % (s_pe, g6["train"]["p"], ALPHA, pb),
         "fit_consistent_with_noise" in vA["validation"]["failed"] and not vA["theta_hat"] and pb < ALPHA)
    # (b) 食い違いを白い分散として足す(学習の残差から σ を取る)
    rB, vB, s_tot = calibrate(gt, Dt, Mt, gh, Dh, Mh, "real total")
    lap = laplace_sd(rB)
    jk, nr = ring_jackknife(gt, Dt, Mt, s_tot, "real")
    th = rB["theta_hat"]
    print("   (b) 食い違いを白い分散として足す(σ = %.2f px): 6 つの門 %s。"
          % (s_tot, "全部通過" if vB["validation"]["passed"] else "落ちた %s" % vB["validation"]["failed"]))
    for n in NAMES:
        if n in th:
            print("       %-10s %10.5g  Laplace ± %.3g  リングのジャックナイフ ± %.3g  [%s]"
                  % (n, th[n], lap[n], jk[n], next(kk["unit"] for kk in KNOBS if kk["name"] == n)))
    pj, ratio = optimism_p(jk["inv_L"], lap["inv_L"], nr)
    gate("実画像: 食い違いを白い分散として足すと 6 つの門を通り(%s)、そのときの Laplace の不確かさはリングのジャックナイフと"
         "同じ大きさ(1/L で比 %.1f、帰無仮説「Laplace は正直」の p = %.2f ≥ %g)—— この板の食い違いは、合成の 3 章のように"
         "係数の形を真似るほど低次ではない" % ("全部通過" if vB["validation"]["passed"] else "落ちた", ratio, pj, ALPHA),
         vB["validation"]["passed"] and pj >= ALPHA)
    pk, (k2lo, k2hi) = tm.PAPER["K1_px_per_mm"], tm.PAPER["K2_px_per_mm"]
    s = th["px_per_mm"]
    se = max(jk["px_per_mm"], lap["px_per_mm"])
    lo, hi = min(pk, k2lo), max(pk, k2hi)
    gate("実画像: 倍率 %.2f ± %.2f px/mm(Laplace とジャックナイフの大きい方)は、論文の K1 = %.1f・K2 = %.1f / %.1f の範囲"
         " ± 3SE に入る。族の当てはめ(実画像の章)は %.2f" % (s, se, pk, k2lo, k2hi, tm.REAL_RECORDED["px_per_mm"]),
         lo - 3 * se <= s <= hi + 3 * se)
    il = th["inv_L"]
    ise = max(jk["inv_L"], lap["inv_L"])
    ub = abs(il) + 2 * ise
    NUMBERS.update({"real_px_per_mm": s, "real_px_se": se, "real_inv_L": il, "real_inv_L_se": ise,
                    "real_pupil_min_m": 1.0 / ub, "real_ratio": ratio, "real_sigma_pe": s_pe, "real_sigma_tot": s_tot})
    inv_ento, inv_fa = 1000.0 / syn["L_ento"], 1000.0 / syn["L_fa25"]
    gate("実画像: 1/L = %.2f ± %.2f /m(%.1fσ)、2σ の上限 %.2f /m —— 入射瞳は %.2f m より遠い。2 章の通常の f = 100 mm"
         "(%.2f /m)と f = 25 mm(%.1f /m)はこの板で否定できる"
         % (il, ise, abs(il) / ise, ub, 1.0 / ub, inv_ento, inv_fa), ub < inv_ento,
         "★未解決: 1/L は 0 から %.1fσ 離れている(入射瞳 %.1f m 相当)。実画像の章の β の解析(リングの中心のずれだけを見る)は"
         " 10.5 m より遠いと言う。ここの 1/L は倍率の傾きも見るので、光軸の位置(画像の中心と仮定)や板のリングの癖と"
         "混ざりうる —— 3σ に届かない差なので、どちらとも決めない" % (abs(il) / ise, 1.0 / max(il, 1e-9)))
    return {"g": g, "h": h, "gt": gt, "Dt": Dt, "Mt": Mt, "ct": ct, "rB": rB, "Rt": Rt, "s_pe": s_pe, "s_tot": s_tot,
            "lap": lap, "jk": jk, "bins": bins, "vA": vA, "vB": vB}


# --------------------------------------------------------------------------- #
# 図                                                                            #
# --------------------------------------------------------------------------- #
def make_figures(syn, real, tm):
    d = syn["disc"]
    labels = []
    xs, ys_lap, ys_jk = [], [], []
    for i, case in enumerate(("clean", "discrepant")):
        r = d[case]
        xs.append(float(i))
        ys_lap.append(r["lap"]["inv_L"])
        ys_jk.append(r["jk"]["inv_L"])
        labels.append(case)
    series = [("Laplace(Fisher の逆)", np.array(xs), np.array(ys_lap)),
              ("リングのジャックナイフ", np.array(xs), np.array(ys_jk))]
    if real is not None:
        series.append(("実画像: Laplace", np.array([2.0]), np.array([real["lap"]["inv_L"]])))
        series.append(("実画像: ジャックナイフ", np.array([2.0]), np.array([real["jk"]["inv_L"]])))
    figs.save_plot("laplace_vs_jackknife", series, xlabel="0 = 合成(食い違いなし)、1 = 合成(食い違いあり)、2 = 実画像",
                   ylabel="1/L の標準誤差 [1/m]", kinds=["scatter"] * len(series),
                   colors=["reference", "emphasis", "reference", "emphasis"][:len(series)],
                   title="1/L の標準誤差: Laplace とリングのジャックナイフ", xlim=(-0.5, 2.5),
                   caption="【1〜3 章・実画像】入射瞳までの距離の逆数 1/L の標準誤差を 2 通りで出した。Laplace = 白い雑音を仮定した"
                           "Fisher 情報の逆、ジャックナイフ = リングを 1 本ずつ抜いて解き直した散らばり。食い違いの無い合成では"
                           "2 つは同じ大きさ、リングごとに 0〜6 次の滑らかな食い違い(RMS 0.7 px、リングの半径と中心の癖を含む)を足すと"
                           " Laplace が 2.4 倍小さく出る(楽観的)。実画像では食い違いを白い分散として足したあと、2 つは同じ"
                           "大きさ(ジャックナイフ / Laplace = %.1f)—— この板の食い違いは係数の形を真似るほど低次ではない。"
                           % (NUMBERS.get("real_ratio", float("nan"))))
    if real is None:
        return
    g = real["g"]
    gt, Mt = real["gt"], real["Mt"]
    a = gt["a"][Mt]
    dd = real["Dt"][Mt]
    res = real["Rt"][Mt]
    rgb = np.repeat(g[..., None], 3, -1) ** (1 / 1.6)
    th = real["rB"]["theta_hat"]
    pal = [(0.90, 0.62, 0.0), (0.34, 0.71, 0.91), (0.0, 0.62, 0.45), (0.94, 0.89, 0.26), (0.0, 0.45, 0.70),
           (0.84, 0.37, 0.0), (0.80, 0.47, 0.65), (0.6, 0.6, 0.6)]
    tt = np.linspace(-np.pi, np.pi, 1440)
    ov = rgb.copy()
    for i in range(8):
        if not Mt[i].any():
            continue
        py_, px_ = project(th, (i + 1) + th["rho0"], tt, real["h"])
        ov = np.asarray(fs.draw_polyline(ov, np.c_[px_, py_], color=pal[i % len(pal)], width=3, closed=True))
    # 残差を測定線の向きに 60 倍して針で描く(赤 = 外、青 = 内)
    h = real["h"]
    P = np.c_[h[0] + dd * np.sin(a), h[1] + dd * np.cos(a)]
    Q = P + 60.0 * res[:, None] * np.c_[np.sin(a), np.cos(a)]
    for (p0, q0), rv in zip(zip(P, Q), res):
        ov = np.asarray(fs.draw_polyline(ov, np.array([[p0[1], p0[0]], [q0[1], q0[0]]]),
                                         color=(0.85, 0.1, 0.1) if rv > 0 else (0.1, 0.3, 0.9), width=3))
    half = ov[::2, ::2]
    half = np.asarray(fs.text_box(half, "線 = 合わせた模型のリング、針 = 残差 × 60(赤 外 / 青 内)。1/2 に縮小", (10, 10),
                                  font_size=22))
    figs.save("real_model_residuals", half,
              "【実画像】アライメント板の生画像に、simcal で合わせた撮像の模型のリング(色の線)と、学習の測定線ごとの残差を"
              "60 倍した針を重ねた(1/2 に縮小)。残差はリングごとに同じ向きにまとまった区間がある —— 雑音(純粋誤差 %.2f px)"
              "では説明できない、板と縁の読みの食い違い(全体の残差 %.2f px)。倍率 %.2f ± %.2f px/mm、1/L = %.2f ± %.2f /m"
              "(リングのジャックナイフ)。" % (real["s_pe"], real["s_tot"], th["px_per_mm"], real["jk"]["px_per_mm"],
                                           th["inv_L"], real["jk"]["inv_L"]) + tm.REAL_SOURCE, source=tm.REAL_SOURCE)
    bins = real["bins"]
    ser = []
    for i, kk in enumerate(sorted({b[0] for b in bins})):
        bb = [b for b in bins if b[0] == kk]
        ser.append(("リング %d" % kk, np.array([b[1] + 15 for b in bb], float), np.array([b[2] for b in bb])))
    se = real["s_pe"] / math.sqrt(8.0)
    kinds = ["line" if len(x) >= 2 else "scatter" for _l, x, _y in ser]
    ser.append(("純粋誤差の ±2σ(8 点の平均)", np.array([0, 360.0]), np.array([2 * se, 2 * se])))
    ser.append(("", np.array([0, 360.0]), np.array([-2 * se, -2 * se])))
    figs.save_plot("real_ring_discrepancy", ser, xlabel="測定線の向き [度]", ylabel="残差の平均 [px]",
                   kinds=kinds + ["line", "line"], styles=[None] * (len(ser) - 2) + ["dashed", "dashed"],
                   title="リングごとの滑らかな食い違い(30° ごとの残差の平均)",
                   caption="【実画像】学習の測定線の残差を、リングごと・30° ごとに平均した(点の数は 4 以上)。破線は純粋誤差だけ"
                           "なら 8 点の平均が 95 %% 入る幅。リング 1 は 2 回の周期で ±0.9 px うねり、他のリングもばらばらの形で"
                           "幅を出る —— 撮像の模型(全リングで共通の係数)では作れない形。" + tm.REAL_SOURCE_SHORT,
                   source=tm.REAL_SOURCE)


def main():
    t0, c0 = time.time(), time.process_time()
    print("PoC テレセンの実画像から撮像模型の係数を合わせる(予算 %s)" % ("reduced" if REDUCED else "full"))
    tm = _load_sibling("poc_telecentric_metrology")
    lenses = tm.lenses()
    syn = chapter_synthetic(lenses)
    real = chapter_real(tm, syn)
    if not REDUCED and figs.target_dir() is not None:
        make_figures(syn, real, tm)
    print("\n所要 %.1f s(CPU %.1f s)、門 %d 件中 NG %d 件" % (time.time() - t0, time.process_time() - c0, len(GATES),
                                                       len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
