# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""縁が暗い天体の輪郭はどこか —— 周辺減光があると「50 % 法」は半径を小さく見る。

    py -3.11 examples/poc_solar_limb_darkening.py

太陽面をシーイング(大気ゆらぎ)越しに撮った、という場面です。**真値は円板の
半径と中心**。面積を持つ天体なので、「点源をどこまで細かく測れるか」を扱った
``examples/poc_astro_photometry.py``(測光)や ``examples/poc_star_astrometry.py``
(測位)とは別の問いになります —— **輪郭がにじんだ天体の「縁」をどこと決めるか**。

周辺減光は Eddington 近似 ``I(µ)/I(0) = 1 - u(1 - µ)``(µ = cos θ = √(1-(r/R)²))で
作ります。この式のおかげで**総フラックスの閉形式** ``πR²(1 - u/3)`` が使えるので、
描画そのものを 1 節で検算できます。

EXTEND: 実写に差し替えるなら :func:`render` を実画像に置き換え、
:data:`R_TRUE` / :data:`C_TRUE` を「別の手段で測った半径と中心」(たとえば
天体暦から計算した視半径)に置き換えます。**同じ画像から別のアルゴリズムで
出した値を真値と呼ぶと、この PoC の主題(手法ごとの偏り)が定義ごと消えます**。

この PoC が示すこと(数字はすべて実行時に印字される実測値):

 1. ★★**「50 % 法の偏りは減光係数 u に比例する」という予想は外れた**。
    比例ではなく **u = 0.5 を境に折れ曲がる**。u < 0.5 では縁の明るさ
    (1-u)I₀ がまだ 50 % より上なので、交差はぼけの斜面の中で起き、偏りは
    ほぼ一定(-1.9 px)。u > 0.5 では 50 % 面が**円板の内側に入り込み**、
    偏りは幾何学で決まる `R(√(1-(1-0.5/u)²) - 1)` に沿って一気に伸びます
    (u=0.8 で -13.4 px)。**機構が途中で入れ替わります**。
 2. ★★**ぼけの効き方は「どの明るさで縁と決めるか」で符号が変わり、
    打ち消し点が実在する**。u=0.6 でしきい値を 0.2〜0.7 と振ると、
    シーイングを 1→4 px に強めたときの半径の変化は **+2.2 px(しきい値 0.2)
    から -1.9 px(0.7)**へ連続的に反転し、**0.36 付近で 0**。そこは「正しい」の
    ではなく、外へ広がる裾と内へ食い込む斜面が釣り合っているだけで、
    **u を変えると打ち消し点も動きます**。
 3. 勾配最大(fullseye のキャリパー)は 50 % 法より 1 桁良いが**無偏では
    ない** —— u=0.6 / σ=2 px で -0.63 px。減光で縁の内側にすでに傾きが
    あるぶん、勾配の山が内へ寄ります。
 4. ★**減光モデルを当てはめて外挿すると 0.03 px** まで戻る(u も同時に
    推定して 0.6 に対し 0.601)。ただし**モデルを間違えると 50 % 法より
    悪くなる**: u を 0 と決め打つと +5.5 px 外れます。
 5. ★黒点(縁に近い暗斑)は 50 % 法の当てはめを **-1.30 px** 引っぱる。
    外れ値を落とす当てはめ(残差 2.5 MAD で刈る)で **-0.02 px** まで直る
    —— **円の当てはめは、点の 3 % が外れただけで半径が動きます**。

来歴(公開文献のみ): Eddington, *The Internal Constitution of the Stars*
(1926) —— 線形周辺減光則 / Neckel & Labs, *Solar Physics* 153 (1994) 91 ——
太陽の減光係数の実測 / Kåsa (1976) / Coope, *J. Optim. Theory Appl.* 76
(1993) 381 —— 代数的な円の当てはめ。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
N_PIX = 512
R_TRUE = 180.0                  # 円板の半径 [px](真値)
C_TRUE = (255.37, 258.83)       # 円板の中心 (row, col) [px](真値、非整数)
U_TRUE = 0.6                    # 周辺減光係数(可視光の太陽で 0.6 前後)
SEEING = 2.0                    # シーイングのガウス σ [px]
SKY = 0.02                      # 背景の空
NOISE = 0.004                   # 雑音 σ
N_RAYS = 180                    # 縁を拾う放射状の測定線の本数


def _blur(img: np.ndarray, sigma: float) -> np.ndarray:
    """σ を指定したガウス平滑。**公開経路の op は σ<=3.0 まで**なので、
    σ/√k を k 回掛けて任意の σ を作る(道具の穴 (a))。"""
    if sigma <= 0:
        return np.asarray(img, np.float64)
    k = max(1, int(np.ceil((sigma / 3.0) ** 2)))
    s = sigma / np.sqrt(k)
    out = np.asarray(img, np.float64)
    for _ in range(k):
        out = np.asarray(fs.apply(out, "gauss_filter", a=(s - 0.3) / 2.7))
    return out


def limb_darkening(r: np.ndarray, radius: float, u: float) -> np.ndarray:
    """Eddington 近似 ``I/I0 = 1 - u(1-µ)``、µ = √(1-(r/R)²)。円板の外は 0。"""
    t = np.clip(np.asarray(r, np.float64) / radius, 0.0, 1.0)
    mu = np.sqrt(np.clip(1.0 - t * t, 0.0, 1.0))
    return np.where(np.asarray(r) <= radius, 1.0 - u * (1.0 - mu), 0.0)


def render(radius: float = R_TRUE, centre=C_TRUE, u: float = U_TRUE,
           seeing: float = SEEING, sky: float = SKY, noise: float = NOISE,
           spot=None, ss: int = 4, seed: int = 5) -> np.ndarray:
    """太陽面を描く。``spot`` = (r/R, 角度 deg, 半径/R, 暗さ) で黒点を 1 つ置く。"""
    off = (np.arange(ss) + 0.5) / ss - 0.5
    yy = np.arange(N_PIX)[:, None, None, None] + off[None, None, :, None]
    xx = np.arange(N_PIX)[None, :, None, None] + off[None, None, None, :]
    dy, dx = yy - centre[0], xx - centre[1]
    r = np.hypot(dy, dx)
    val = limb_darkening(r, radius, u)
    if spot is not None:
        fr, ang, frad, dark = spot
        a = np.radians(ang)
        sy = centre[0] + fr * radius * np.sin(a)
        sx = centre[1] + fr * radius * np.cos(a)
        inside = np.hypot(yy - sy, xx - sx) <= frad * radius
        val = np.where(inside & (r <= radius), val * dark, val)
    img = val.mean(axis=(2, 3))
    img = _blur(img, seeing) + sky
    if noise > 0.0:
        img = img + np.random.default_rng(seed).normal(0.0, noise, img.shape)
    return img


# --------------------------------------------------------------------------- #
# 縁を拾う 2 通り + 円の当てはめ                                                #
# --------------------------------------------------------------------------- #
def rough_geometry(img: np.ndarray) -> tuple[float, float, float]:
    """**真値を一切見ずに**中心と半径のあたりを付ける(重心と、面積からの等価半径)。"""
    lo, hi = float(np.percentile(img, 2.0)), float(np.percentile(img, 98.0))
    m = img >= 0.5 * (lo + hi)
    yy, xx = np.mgrid[0:N_PIX, 0:N_PIX]
    s = float(m.sum())
    return (float((m * yy).sum() / s), float((m * xx).sum() / s),
            float(np.sqrt(s / np.pi)))


def _levels(img: np.ndarray, centre, r_rough: float) -> tuple[float, float]:
    """円板中心付近の明るさ I0 と背景 sky を**画像から**測る。"""
    yy, xx = np.mgrid[0:N_PIX, 0:N_PIX]
    r = np.hypot(yy - centre[0], xx - centre[1])
    i0 = float(np.median(img[r < 0.25 * r_rough]))
    bg = float(np.median(img[r > 1.30 * r_rough]))
    return i0, bg


def edge_points(img: np.ndarray, centre, r_rough: float, how: str = "level",
                level: float = 0.5) -> np.ndarray:
    """放射状の測定線で縁の (row, col) を拾う。``how`` = level / gradient。

    * ``level`` —— 明るさが「中心の ``level`` 倍(背景基準)」を切る位置。
      ゼロ点にあたる素朴な決め方(``level=0.5`` が「輝度の 50 %」)。
    * ``gradient`` —— **fullseye のキャリパー**(``gen_measure_rectangle2`` +
      ``measure_pos``)で勾配が最大の位置をサブピクセルで拾う。
    """
    i0, bg = _levels(img, centre, r_rough)
    thr = bg + level * (i0 - bg)
    rmax = 1.35 * r_rough
    n = int(rmax) + 1
    pts = []
    for a in np.linspace(0.0, 2.0 * np.pi, N_RAYS, endpoint=False):
        dy, dx = np.sin(a), np.cos(a)
        if how == "gradient":
            m = fs.ledger.gen_measure_rectangle2(
                centre[0] + 0.5 * rmax * dy, centre[1] + 0.5 * rmax * dx, a,
                0.5 * rmax, 3, (N_PIX, N_PIX))
            edges = fs.ledger.measure_pos(img, m, sigma=1.0,
                                          threshold=0.25 * (i0 - bg),
                                          transition="negative")
            if not edges:
                continue
            e = max(edges, key=lambda d: abs(d["amplitude"]))
            pts.append((e["row"], e["col"]))
            continue
        prof = fs.line_profile(img, (centre[0], centre[1]),
                               (centre[0] + rmax * dy, centre[1] + rmax * dx), n)
        idx = np.nonzero(prof >= thr)[0]
        if idx.size == 0 or idx[-1] >= n - 1:
            continue
        k = int(idx[-1])
        a0, b0 = prof[k], prof[k + 1]
        f = 0.0 if abs(a0 - b0) < 1e-12 else (a0 - thr) / (a0 - b0)
        d = (k + float(np.clip(f, 0.0, 1.0))) * rmax / (n - 1)
        pts.append((centre[0] + d * dy, centre[1] + d * dx))
    return np.asarray(pts, np.float64).reshape(-1, 2)


def fit_disc(img: np.ndarray, how: str = "level", level: float = 0.5,
             robust: bool = False) -> dict:
    """縁を拾って円を当てはめる(中心は重心 -> 1 回だけ当てはめ直して精度を出す)。"""
    cy, cx, r_rough = rough_geometry(img)
    c = (cy, cx)
    out = None
    for _ in range(2):
        pts = edge_points(img, c, r_rough, how, level)
        if len(pts) < 3:
            return {"r": float("nan"), "cy": float("nan"), "cx": float("nan"),
                    "n": 0, "rms": float("nan")}
        out = fs.fit_circle(pts)
        if robust:
            d = np.hypot(pts[:, 0] - out["cy"], pts[:, 1] - out["cx"]) - out["r"]
            mad = np.median(np.abs(d - np.median(d))) + 1e-12
            keep = np.abs(d - np.median(d)) < 2.5 * 1.4826 * mad
            if keep.sum() >= 3:
                out = fs.fit_circle(pts[keep])
                out = dict(out, n_drop=int((~keep).sum()))
        c = (out["cy"], out["cx"])
    return dict(out, n=len(pts))


# --------------------------------------------------------------------------- #
# 減光モデルの当てはめ(1 次元の動径プロファイルに前向きモデルを合わせる)      #
# --------------------------------------------------------------------------- #
def radial_profile(img: np.ndarray, centre, rmax: float, n: int) -> np.ndarray:
    """方位平均した動径プロファイル(``fs.line_profile`` を N_RAYS 本平均)。"""
    acc = np.zeros(n)
    for a in np.linspace(0.0, 2.0 * np.pi, N_RAYS, endpoint=False):
        acc += fs.line_profile(img, (centre[0], centre[1]),
                               (centre[0] + rmax * np.sin(a),
                                centre[1] + rmax * np.cos(a)), n)
    return acc / N_RAYS


def _model_profile(rr: np.ndarray, radius: float, u: float, seeing: float) -> np.ndarray:
    """モデルの動径プロファイル(1 次元でぼかす。R >> σ での近似)。"""
    step = rr[1] - rr[0]
    half = int(np.ceil(4.0 * seeing / step))
    t = np.arange(-half, half + 1) * step
    k = np.exp(-0.5 * (t / seeing) ** 2)
    k = k / k.sum()
    fine = limb_darkening(rr, radius, u)
    return np.convolve(np.concatenate([fine[::-1][:-1], fine]), k,
                       mode="same")[len(fine) - 1:]


def fit_limb_model(img: np.ndarray, centre, seeing: float = SEEING,
                   u_grid=None, r0: float = R_TRUE) -> dict:
    """★対比 —— 減光モデルを当てはめて縁を**外挿**する(A と背景は線形に解く)。

    ``u_grid`` に 1 点だけ渡すと「u をこう決め打つ」版になります。
    """
    rmax = 1.35 * R_TRUE
    n = 541
    rr = np.linspace(0.0, rmax, n)
    obs = radial_profile(img, centre, rmax, n)
    us = np.linspace(0.0, 1.0, 51) if u_grid is None else np.atleast_1d(u_grid)
    rs = r0 + np.arange(-8.0, 8.01, 0.05)
    best = (np.inf, np.nan, np.nan)
    for u in us:
        for radius in rs:
            m = _model_profile(rr, radius, u, seeing)
            a = np.column_stack([m, np.ones(n)])
            sol = fs.mat_lstsq(a, obs)
            ss = float(np.atleast_1d(sol["residual_ss"])[0])
            if ss < best[0]:
                best = (ss, radius, float(u))
    return {"r": best[1], "u": best[2], "ss": best[0]}


# --------------------------------------------------------------------------- #
# 1. 合成器の検算                                                               #
# --------------------------------------------------------------------------- #
def section_sanity() -> None:
    print("\n" + "=" * 78)
    print("1) 合成器の検算 —— 描いた円板が本当に真値どおりか")
    print("=" * 78)

    # 総フラックスの閉形式 πR²(1 - u/3) と突き合わせる(ぼけも背景も雑音も無し)
    for u in (0.0, 0.6, 1.0):
        img = render(u=u, seeing=0.0, sky=0.0, noise=0.0, ss=8)
        want = np.pi * R_TRUE ** 2 * (1.0 - u / 3.0)
        got = float(img.sum())
        print("  u=%.1f  総フラックス 実測 %.1f / 閉形式 %.1f  相対差 %.2e" % (
            u, got, want, abs(got - want) / want))
        assert abs(got - want) / want < 2e-4

    # ぼけはフラックスを保存する(縁の判定がずれても総量は動かない)
    a = render(seeing=0.0, sky=0.0, noise=0.0)
    b = _blur(a, 4.0)
    print("  ぼけ σ=4 の前後で総フラックス 相対差 %.2e" % (
        abs(b.sum() - a.sum()) / a.sum()))
    assert abs(b.sum() - a.sum()) / a.sum() < 1e-6

    # 円の当てはめは、厳密な円上の点なら厳密に戻す
    ang = np.linspace(0, 2 * np.pi, 37)[:-1]
    p = np.column_stack([C_TRUE[0] + R_TRUE * np.sin(ang),
                         C_TRUE[1] + R_TRUE * np.cos(ang)])
    f = fs.fit_circle(p)
    print("  fit_circle が厳密な円上の 36 点から戻す半径の誤差 %.2e px"
          % abs(f["r"] - R_TRUE))
    assert abs(f["r"] - R_TRUE) < 1e-9

    # 1 次元でぼかす近似が 2 次元のぼけとどれだけ違うか(モデル当てはめの前提)
    img = render(seeing=SEEING, sky=0.0, noise=0.0)
    rmax = 1.35 * R_TRUE
    rr = np.linspace(0.0, rmax, 541)
    obs = radial_profile(img, C_TRUE, rmax, 541)
    mod = _model_profile(rr, R_TRUE, U_TRUE, SEEING)
    near = np.abs(rr - R_TRUE) < 4 * SEEING
    print("  1 次元近似モデルと 2 次元描画の差(縁の ±4σ)最大 %.4f(中心の %.2f %%)"
          % (float(np.max(np.abs(obs - mod)[near])),
             100 * float(np.max(np.abs(obs - mod)[near]))))
    print("  -> R=%.0f px に対し σ=%.1f px なので曲率の効きは小さい。以後この近似を使う。"
          % (R_TRUE, SEEING))


# --------------------------------------------------------------------------- #
# 2. ★ゼロ点(50 % 法)vs 勾配最大 vs 減光モデル                                #
# --------------------------------------------------------------------------- #
def section_zero_point() -> dict:
    print("\n" + "=" * 78)
    print("2) ★ゼロ点(輝度 50 % で縁と決める)vs 勾配最大 vs 減光モデル")
    print("=" * 78)
    print("  手法                半径 [px]   誤差       中心の誤差 [px]   点数")

    img = render()
    out = {}
    for name, kw in (("ゼロ点(50 %)", {"how": "level", "level": 0.5}),
                     ("勾配最大(caliper)", {"how": "gradient"})):
        f = fit_disc(img, **kw)
        d = float(np.hypot(f["cy"] - C_TRUE[0], f["cx"] - C_TRUE[1]))
        out[name] = (f["r"] - R_TRUE, d)
        print("  %-20s %8.3f  %+7.3f       %.3f          %d" % (
            name, f["r"], f["r"] - R_TRUE, d, f["n"]))

    c = fit_disc(img, "level", 0.5)
    m = fit_limb_model(img, (c["cy"], c["cx"]))
    out["減光モデル"] = (m["r"] - R_TRUE, float("nan"))
    print("  %-20s %8.3f  %+7.3f       (中心は 50 %% 法から)  u=%.3f (真 %.2f)" % (
        "減光モデル", m["r"], m["r"] - R_TRUE, m["u"], U_TRUE))

    m0 = fit_limb_model(img, (c["cy"], c["cx"]), u_grid=0.0)
    out["減光モデル(u=0 と誤認)"] = (m0["r"] - R_TRUE, float("nan"))
    print("  %-20s %8.3f  %+7.3f       <- モデルを間違えると 50 %% 法より悪い" % (
        "同 u=0 と決め打ち", m0["r"], m0["r"] - R_TRUE))

    print("\n  ★50 %% 法は %+.2f px。勾配最大は %+.2f px で 1 桁良いが**無偏ではない**。"
          % (out["ゼロ点(50 %)"][0], out["勾配最大(caliper)"][0]))
    print("  減光モデルは %+.3f px まで戻り、u も %.3f(真 %.2f)と当てる。"
          % (out["減光モデル"][0], m["u"], U_TRUE))
    print("  ただし u=0 と決め打つと %+.2f px —— **モデルの正しさが精度を決める**。"
          % out["減光モデル(u=0 と誤認)"][0])
    return out


# --------------------------------------------------------------------------- #
# 3. ★★減光係数 u を振る —— 比例ではなく折れ曲がる                             #
# --------------------------------------------------------------------------- #
U_GRID = (0.0, 0.2, 0.4, 0.5, 0.6, 0.8)


def _geometric_prediction(u: float) -> float:
    """50 % 面が円板の**内側**に入るときの、幾何だけで決まる半径の偏り [px]。"""
    if u <= 0.5:
        return float("nan")
    mu = 1.0 - 0.5 / u
    return R_TRUE * (np.sqrt(max(0.0, 1.0 - mu * mu)) - 1.0)


def section_u_sweep() -> dict:
    print("\n" + "=" * 78)
    print("3) ★★減光係数 u を振る —— 予想した比例ではなく u=0.5 で折れ曲がる")
    print("=" * 78)
    print("     u     50 %% 法の誤差   幾何の予測    勾配最大の誤差")

    lv, gr, pred = [], [], []
    for u in U_GRID:
        img = render(u=u)
        f = fit_disc(img, "level", 0.5)
        g = fit_disc(img, "gradient")
        p = _geometric_prediction(u)
        lv.append(f["r"] - R_TRUE)
        gr.append(g["r"] - R_TRUE)
        pred.append(p)
        print("   %.2f     %+8.3f     %s     %+8.3f" % (
            u, f["r"] - R_TRUE,
            "  (無し)  " if np.isnan(p) else "%+8.3f" % p, g["r"] - R_TRUE))

    print("\n  ★★**予想が外れた**。「偏りは u に比例する」と踏んでいたが、")
    print("  u<=0.5 ではほぼ一定(%+.2f 〜 %+.2f px)で、u>0.5 から急に伸びる。"
          % (lv[0], lv[3]))
    print("  機構が入れ替わっている:")
    print("   * u<=0.5 —— 縁の明るさ (1-u)I0 がまだ 50 %% より上なので、交差は")
    print("     **ぼけの斜面の中**で起きる。偏りはシーイングで決まり u に鈍い。")
    print("   * u>0.5 —— 50 %% の等輝度面が**円板の内側に入り込む**。偏りは")
    print("     幾何だけで決まり、u=0.8 の実測 %+.2f px は予測 %+.2f px と一致。"
          % (lv[-1], pred[-1]))
    print("  勾配最大は u に対して %+.2f 〜 %+.2f px と鈍い(縁の位置を明るさで"
          % (min(gr), max(gr)))
    print("  決めていないため)。")
    return {"u": list(U_GRID), "level": lv, "grad": gr, "pred": pred}


# --------------------------------------------------------------------------- #
# 4. ★★ぼけの効き方はしきい値で符号が変わる(打ち消し点)                       #
# --------------------------------------------------------------------------- #
LEVEL_GRID = (0.2, 0.3, 0.4, 0.5, 0.6, 0.7)
SEEING_GRID = (1.0, 4.0)


def section_seeing_levels() -> dict:
    print("\n" + "=" * 78)
    print("4) ★★シーイングは半径を大きくも小さくもする —— 打ち消し点は正しさではない")
    print("=" * 78)
    print("  しきい値   σ=1 px の誤差   σ=4 px の誤差   ぼけによる変化")

    d = {}
    for lv in LEVEL_GRID:
        e = [fit_disc(render(seeing=s), "level", lv)["r"] - R_TRUE
             for s in SEEING_GRID]
        d[lv] = (e[0], e[1], e[1] - e[0])
        print("    %.2f      %+8.3f       %+8.3f       %+8.3f" % (
            lv, e[0], e[1], e[1] - e[0]))

    ks = list(LEVEL_GRID)
    ch = [d[k][2] for k in ks]
    zero = None
    for i in range(len(ks) - 1):
        if ch[i] * ch[i + 1] < 0:
            zero = ks[i] + (-ch[i] / (ch[i + 1] - ch[i])) * (ks[i + 1] - ks[i])
            break
    print("\n  ★★ぼけによる半径の変化は %+.2f px(しきい値 %.1f)から %+.2f px(%.1f)へ"
          % (ch[0], ks[0], ch[-1], ks[-1]))
    print("  **符号を変える**。低いしきい値では**外へ広がる裾**が勝ち、高いしきい値")
    print("  では**内へ食い込む斜面**が勝つ。ゼロを横切るのは %s 付近。"
          % ("%.2f" % zero if zero else "(範囲外)"))
    print("  そこは「シーイングに強い」のではなく**釣り合っているだけ**で、")

    # 対照群: u を変えると打ち消し点が動く -> 「良い設定」ではないことの証拠
    d2 = {}
    for lv in LEVEL_GRID:
        e = [fit_disc(render(u=0.3, seeing=s), "level", lv)["r"] - R_TRUE
             for s in SEEING_GRID]
        d2[lv] = e[1] - e[0]
    ch2 = [d2[k] for k in ks]
    z2 = None
    for i in range(len(ks) - 1):
        if ch2[i] * ch2[i + 1] < 0:
            z2 = ks[i] + (-ch2[i] / (ch2[i + 1] - ch2[i])) * (ks[i + 1] - ks[i])
            break
    print("  **対照群がそれを示す**: u を 0.6 -> 0.3 に変えると打ち消し点は")
    print("  %s -> %s へ動く。減光係数を知らずにしきい値を選べません。"
          % ("%.2f" % zero if zero else "範囲外", "%.2f" % z2 if z2 else "範囲外"))
    return {"levels": ks, "s1": [d[k][0] for k in ks], "s4": [d[k][1] for k in ks],
            "change": ch, "change_u03": ch2, "zero": zero, "zero_u03": z2}


# --------------------------------------------------------------------------- #
# 5. ★黒点 —— 3 % の外れ点で半径が動く                                          #
# --------------------------------------------------------------------------- #
def section_spot() -> dict:
    print("\n" + "=" * 78)
    print("5) ★縁に近い黒点 —— 当てはめを引っぱる量と、外れ値を落として直す量")
    print("=" * 78)
    print("  条件                   当てはめ    半径の誤差   中心の誤差   落とした点")

    out = {}
    for label, spot in (("黒点なし(対照群)", None),
                        ("黒点 r=0.85R", (0.85, 32.0, 0.07, 0.35)),
                        ("黒点 r=0.97R(縁上)", (0.97, 32.0, 0.07, 0.35))):
        img = render(spot=spot)
        for robust in (False, True):
            f = fit_disc(img, "level", 0.5, robust=robust)
            dc = float(np.hypot(f["cy"] - C_TRUE[0], f["cx"] - C_TRUE[1]))
            out[(label, robust)] = (f["r"] - R_TRUE, dc)
            print("  %-22s %-9s  %+8.3f     %7.3f      %s" % (
                label, "ロバスト" if robust else "最小二乗",
                f["r"] - R_TRUE, dc,
                f.get("n_drop", "-") if robust else "-"))

    a = out[("黒点 r=0.97R(縁上)", False)][0]
    b = out[("黒点 r=0.97R(縁上)", True)][0]
    c = out[("黒点なし(対照群)", False)][0]
    print("\n  ★縁に載った黒点は半径を %+.2f px 動かす(対照群 %+.2f px からの差 %.2f px)。"
          % (a, c, abs(a - c)))
    print("  外れ値を落とすと %+.2f px。**円の当てはめは点の数 %% の汚染で動きます** ——"
          % b)
    print("  黒点が円板の内側(r=0.85R)にあるうちは縁の点列に入らないので効きません。")
    return out


# --------------------------------------------------------------------------- #
# 6. 図                                                                         #
# --------------------------------------------------------------------------- #
def section_figures(us: dict, sl: dict, spot: dict) -> None:
    if not figs.enabled():
        return
    img = render(spot=(0.97, 32.0, 0.07, 0.35))
    flat = render(u=0.0, spot=None)
    yy, xx = np.mgrid[0:N_PIX, 0:N_PIX]
    ring = (np.abs(np.hypot(yy - C_TRUE[0], xx - C_TRUE[1]) - R_TRUE) < 1.5)
    figs.save_grid("scene",
                   [img, flat, img - flat, np.where(ring, 1.0, img)],
                   ["u=0.6 + 黒点", "u=0(減光なし)", "差", "真の縁を重ねた"],
                   title="太陽面 R=%.0f px / シーイング σ=%.1f px" % (R_TRUE, SEEING),
                   ncols=2, signed=[False, False, True, False])

    pu = np.asarray(us["pred"], float)
    figs.save_plot("bias_vs_u",
                   [("50 % 法", np.asarray(us["u"]), np.asarray(us["level"])),
                    ("幾何の予測(u>0.5)", np.asarray(us["u"]), pu),
                    ("勾配最大", np.asarray(us["u"]), np.asarray(us["grad"])),
                    ("誤差ゼロ", np.asarray(us["u"]), np.zeros(len(us["u"])))],
                   xlabel="周辺減光係数 u", ylabel="半径の誤差 [px]",
                   title="u=0.5 で機構が入れ替わる(比例ではない)")

    figs.save_plot("seeing_cancel",
                   [("u=0.6", np.asarray(sl["levels"]), np.asarray(sl["change"])),
                    ("u=0.3(対照群)", np.asarray(sl["levels"]),
                     np.asarray(sl["change_u03"])),
                    ("変化ゼロ", np.asarray(sl["levels"]), np.zeros(len(sl["levels"])))],
                   xlabel="縁と決める明るさ(中心の何倍か)",
                   ylabel="σ 1->4 px での半径の変化 [px]",
                   title="ぼけの効き方はしきい値で符号が変わる")

    rows = [[k[0], "ロバスト" if k[1] else "最小二乗",
             "%+.3f" % v[0], "%.3f" % v[1]] for k, v in spot.items()]
    figs.save_table("sunspot", ["条件", "当てはめ", "半径の誤差 [px]", "中心 [px]"],
                    rows, title="黒点が円の当てはめを引く量",
                    caption="縁に載った黒点だけが効く(内側の黒点は縁の点列に入らない)。")


# --------------------------------------------------------------------------- #
# 7. 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("6) 道具の穴(3 層すべて引いてみて)")
    print("=" * 78)

    # (a) σ を指定できるガウス平滑が無い
    import ops
    op = {o.name: o for o in ops.REGISTRY}["gauss_filter"]
    assert "0.3〜3.0" in (op.doc or ""), op.doc
    print("  (a) σ を指定するガウス平滑が公開経路に無い(進化 op は σ<=3.0)。")
    print("      シーイングは 4 px を超えるのが普通なので、この PoC は σ/√k を")
    print("      k 回掛けて作っている。")

    # (b) 2-D のロバスト円当てはめが無い(3-D の球/円筒/平面にはある)
    assert hasattr(fs, "fit_sphere_ransac") and hasattr(fs, "fit_plane_ransac")
    for n in ("fit_circle_ransac", "ransac_circle"):
        assert not hasattr(fs, n) and not hasattr(fs.ledger, n), n
    print("  (b) **2-D のロバスト円当てはめが無い**。3-D には fit_sphere_ransac /")
    print("      fit_plane_ransac / ransac_line があるのに、画像の円には無い ——")
    print("      黒点・雲・視野の切れは 2-D でこそ起きるので、ここは非対称。")
    print("      この PoC は残差 MAD で刈って当てはめ直している(5 節)。")

    # (c) 円の当てはめが不確かさを返さない
    f = fs.fit_circle(np.array([[0.0, 1.0], [1.0, 0.0], [0.0, -1.0], [-1.0, 0.02]]))
    assert set(f) == {"cy", "cx", "r", "rms"}, sorted(f)
    print("  (c) fit_circle が返すのは cy/cx/r/rms だけ。**半径の標準誤差**も")
    print("      inlier マスクも返さないので、'R = 180.03 ± ?' が書けない。")
    print("      mat_lstsq は residual_ss まで返すのに、幾何当てはめは返さない。")

    # (d) 動径プロファイル(方位平均)を返す口が無い
    for n in ("radial_profile", "azimuthal_average", "polar_profile"):
        assert not hasattr(fs, n) and not hasattr(fs.ledger, n), n
    assert hasattr(fs, "line_profile")
    print("  (d) 方位平均した**動径プロファイル**を返す口が無い。line_profile を")
    print("      %d 本回して自前で平均している。円対称な天体・レンズの MTF・" % N_RAYS)
    print("      粒子の散乱像など、要る場面は多い。")

    # (e) 周辺減光則そのものが無い(optics 族には点像分布関数はあるのに)
    for n in ("limb_darkening", "eddington_limb"):
        assert not hasattr(fs, n) and not hasattr(fs.ledger, n), n
    assert hasattr(fs, "PSF_MODELS")
    print("  (e) 周辺減光則(Eddington / Claret)が 3 層のどこにも無い。天体側の")
    print("      放射モデルは PSF_MODELS('gaussian','moffat')だけで、面を持つ")
    print("      天体の輝度分布が扱えない。")


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    print("=" * 78)
    print("縁が暗い天体の輪郭はどこか —— 周辺減光と 50 %% 法")
    print("R=%.0f px / 中心 (%.2f, %.2f) / u=%.1f / シーイング σ=%.1f px / 雑音 %.3f"
          % (R_TRUE, C_TRUE[0], C_TRUE[1], U_TRUE, SEEING, NOISE))
    print("=" * 78)

    section_sanity()
    zp = section_zero_point()
    us = section_u_sweep()
    sl = section_seeing_levels()
    spot = section_spot()
    section_figures(us, sl, spot)
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 50 %% 法の偏りは u に比例しない。u=0.5 で**機構が入れ替わる**")
    print("    (u<=0.5 はぼけが決め、u>0.5 は幾何が決める)。")
    print("  * ぼけの効き方はしきい値で符号が変わり、打ち消し点は u で動く。")
    print("  * 減光モデルを当てはめれば %+.3f px まで戻るが、u を誤ると %+.2f px。"
          % (zp["減光モデル"][0], zp["減光モデル(u=0 と誤認)"][0]))
    print("  * 縁に載った黒点は数 %% の点で半径を動かす。刈れば戻る。")
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
