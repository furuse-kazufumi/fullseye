# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""繊維の配向分布を測る —— 角度は 180 度周期。素朴に平均すると 90 度ずれる。

繊維強化プラスチック(FRP)や不織布・紙・骨梁の **配向分布** を画像から出す、
という仕事です。剛性も強度も配向で決まるので、成形解析(Advani–Tucker の配向
テンソル)に渡す数字はここから来ます。

真値は **撒いた繊維の角度の一覧** です。角度はフォン・ミーゼス分布から引き、
繊維は線分としてアンチエイリアスつきで描くので、平均も広がりも配向度も
標本から厳密に計算できます。

EXTEND: 実物(μCT の断面、SEM、偏光顕微鏡)に差し替えるなら
:func:`make_scene` の返す ``img`` と ``angles`` / ``len_vis`` の対を、実写画像と
「視野に入った繊維の角度と可視長さの表」に置き換えます。**角度だけの表では
足りません** —— この PoC の 3 節が示すとおり、画素ごとの測定は **長さで重みが
つく** ので、本数基準の真値と比べると系統的にずれます。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(画像全体で構造テンソルを 1 個)は単峰なら当たる**。平均 28.00 度・
   配向度 0.8382 の場面で **27.23 度 / 0.7865**(-0.77 度)。ただし出るのは
   数字 2 個だけで、分布は出ません。★**二峰では壊れます**: 0 度と 90 度の
   繊維を半々に撒くと、ゼロ点は配向度 **0.0243 =「向きが無い」** と報告する。
   実際は **どちらの群も完全に揃っている**(群ごとの配向度 0.9865 / 0.9868)。
   テンソル 1 個には峰が 1 つしか入りません。
2. ★★**素朴な算術平均は 180 度周期で壊れる**。真の平均を 13〜178 度と振ると、
   算術平均の誤差は **最大 -72.3 度**(真値 177.9 度で **105.6 度** と報告)。
   0 度付近と 179 度付近の繊維は **同じ向き** なのに、数として平均すると
   打ち消し合って 90 度へ寄ります。2 倍角の円形平均に変えると、同じ画像・
   同じ画素・同じ構造テンソルのまま誤差 **最大 1.4 度**。★これは推定器の
   性能ではなく **平均の取り方だけ** の差です。
3. ★**真値が 3 通りある**(本数基準 / 撒いた長さ基準 / 視野内の長さ基準)。
   ★対照群(長さと角度が独立)では 3 つの配向度の開きは **0.0135** しか
   なく、どれを選んでも同じ母数を推定します。★★処理群(長い繊維ほど揃う =
   射出成形の実際)にすると開きが **0.0368** に広がり、画素ごとの測定は
   面積 = 長さで重みがつくので、本数基準の真値と比べて配向度が **+4.9 %**
   ずれて見える —— **測定器の誤差ではなく、比べる相手の問題**です。
4. ★★**重みを選ばないと配向度は 3 割小さく出る**。全画素を等しく数えると
   0.5754(真値 0.8382、**-31.3 %**)—— 背景画素には向きが無く、勾配が
   雑音に支配されて **一様分布を足す** からです。勾配エネルギー重みで
   0.8315(-0.8 %)、コヒーレンス×エネルギーで 0.8396(+0.2 %)。
   ★平均角度のほうは重みを変えても 27.6 / 27.3 / 27.2 度とほとんど動かない
   —— **同じ 1 枚の絵から出した 2 つの量が、まったく違う壊れ方をします**。
5. ★★**繊維の交差 —— 予想が 2 か所とも外れました**。同じ繊維に本数を足して
   40 → 400 本にすると交差は 8 → 447 件・面積率 3.9 → 32.8 % になります。
   予想「2 方向が混ざるので配向度は落ちる」に反して、配向度の偏りは
   **-0.0062 → +0.0303 と逆向きに増えました**。混ざった画素はコヒーレンスが
   下がる = **重みも下がる** ので、分布から抜けるだけで薄めない。残るのは
   揃った画素なので、配向度はむしろ **高めに出ます**。予想「平均角度もずれる」
   も外れで、誤差は 0.34 → 0.91 度。中間角は分布の両側から等しく出ます。
6. ★★**窓を広げると配向度が上がる。ただし材料が揃ったわけではない**。積分
   スケール σ_i を 1 → 24 px と振ると配向度は **0.8148 → 0.9762**(真値
   0.8382)。★理由は代数で言えます: w·e^{2iθ} = −[(Jxx−Jyy) + 2i·Jxy] が
   恒等式で、ガウス平滑化は総和を保つので **分子 |Σ w e^{2iθ}| は σ_i に
   依らない**(実測でも 6 通りの σ_i すべてで 14347.0 と一致)。動くのは
   分母 Σw = Σ(トレース×コヒーレンス)だけで、17608 → 14697 と縮む。
   だから平均角度は **1 桁目まで動かず**(27.23 度)、配向度だけが上がります。
   ★微分スケール σ_d は役目が違い、雑音 0.02 では上げても良くならず 4 px で
   0.8400 → 0.8062 と落ちる(過平滑化)。雑音を 5 倍にすると **最適点が
   現れ**、σ_d=0 の 0.8265 が σ_d=1 px で 0.8342 に戻ります。
7. ★**画像の縁の影響は、予想よりずっと小さい**。縁 24 px を捨てる対照群と
   比べて配向度 0.8396 → 0.8335(差 **0.0061**)、平均 27.23 → 27.04 度。
   縁だけを取り出しても 0.8616 / 27.89 度で、予想した 0/90 度の偽ピークは
   見えません。勾配が視野の縁そのものを見るのは外周 2 px = 面積の 2.1 %
   だけで、しかもそこは平坦なのでエネルギー重みが小さい —— **捨てた 23 %
   の帯の大半は、ただの普通の繊維でした**。

来歴(公開文献のみ): Advani & Tucker, *J. Rheology* 31 (1987) 751 —— 配向
テンソル / Bigün & Granlund, *ICCV* (1987) 433 —— 構造テンソル / Jähne,
*Digital Image Processing* (Springer, 2005) 第 13 章 —— 微分スケールと積分
スケール / Mardia & Jupp, *Directional Statistics* (Wiley, 2000) —— 2 倍角の
円形統計。
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
N_PIX = 384              # 視野 [px]
N_FIB = 140              # 繊維の本数(既定)
LEN_LO, LEN_HI = 60.0, 140.0     # 繊維の長さ [px]
WIDTH = 2.6              # 繊維の太さ [px]
MU_DEG = 30.0            # 配向の平均 [deg](真値)
KAPPA = 4.0              # フォン・ミーゼスの集中度(2 倍角の領域で)
FG, BG = 0.85, 0.12      # 繊維と背景の明るさ
NOISE = 0.02             # 撮像ノイズ(1σ)
SIG_D, SIG_I = 1.0, 2.0  # 微分スケール / 積分スケール [px]
SEED = 21

_LAB = fs.ledger


# --------------------------------------------------------------------------- #
# 1. 場面を作る —— 真値は撒いた角度の一覧                                       #
# --------------------------------------------------------------------------- #
def _gauss2d(x, sigma: float):
    """2-D ガウス平滑化を **fullseye の 1-D 関数**(:func:`smooth_funct_1d_gauss`)
    を行・列に掛けて組む。

    σ を直に渡せる 2-D のぼかしが公開経路に無いので分離可能性を使う(末尾
    「道具の穴」(a))。σ <= 0 は素通し。
    """
    if sigma <= 0:
        return np.asarray(x, np.float64)
    y = np.apply_along_axis(lambda v: fs.smooth_funct_1d_gauss(v, sigma), 1,
                            np.asarray(x, np.float64))
    return np.apply_along_axis(lambda v: fs.smooth_funct_1d_gauss(v, sigma), 0, y)


def _clip_len(c, d, half_len, n_pix):
    """線分 c ± half_len·d のうち **視野に入っている長さ** [px]。"""
    t_lo, t_hi = -half_len, half_len
    for k in (0, 1):
        if abs(d[k]) < 1e-12:
            if not (0.0 <= c[k] <= n_pix - 1):
                return 0.0
            continue
        a = (0.0 - c[k]) / d[k]
        b = ((n_pix - 1) - c[k]) / d[k]
        lo, hi = min(a, b), max(a, b)
        t_lo, t_hi = max(t_lo, lo), min(t_hi, hi)
    return max(0.0, t_hi - t_lo)


def make_scene(n_fibers: int = N_FIB, mu_deg: float = MU_DEG, kappa: float = KAPPA,
               seed: int = SEED, n_pix: int = N_PIX, bimodal: bool = False,
               couple: bool = False, n_pool: int | None = None,
               noise: float = NOISE) -> dict:
    """線分としての繊維を撒いた画像と、その真値を返す。

    角度は **2 倍角の領域** でフォン・ミーゼス分布から引く(向きは 180 度
    周期なので、素朴に vonmises(μ, κ) を引くと 360 度周期の量になってしまう)。
    中心は視野の外にもはみ出させる —— 縁で切れる繊維が無いと 7 節が測れない。

    ``n_pool`` を渡すと **その本数ぶんの繊維を作ってから先頭 n_fibers 本だけ
    描く**。密度を振るときに「同じ繊維に足していく」ためで、これをしないと
    本数を変えるたびに別の標本になり、密度の効果と標本のばらつきが混ざる。

    ``couple`` は **長さと角度に相関を入れる**(長い繊維ほど揃う ——
    射出成形の実際に近い)。3 節の処理群。
    """
    rng = np.random.default_rng(seed)
    pool = int(n_pool or n_fibers)
    length = rng.uniform(LEN_LO, LEN_HI, pool)
    if bimodal:
        half = pool // 2
        ang = np.concatenate([rng.vonmises(0.0, 40.0, half) / 2.0,
                              rng.vonmises(np.pi, 40.0, pool - half) / 2.0])
    else:
        mu2 = np.mod(2.0 * np.radians(mu_deg) + np.pi, 2.0 * np.pi) - np.pi
        kap = kappa
        if couple:
            # 長さで κ を 0.6 -> 20 と変える(短い繊維はほぼ無秩序)
            f = (length - LEN_LO) / (LEN_HI - LEN_LO)
            kap = 0.6 + 19.4 * f ** 2
        ang = rng.vonmises(mu2, kap, pool) / 2.0
    ang = np.mod(ang, np.pi)
    margin = 0.5 * LEN_HI
    cx = rng.uniform(-margin, n_pix + margin, pool)
    cy = rng.uniform(-margin, n_pix + margin, pool)
    ang, length = ang[:n_fibers], length[:n_fibers]
    cx, cy = cx[:n_fibers], cy[:n_fibers]

    img = np.zeros((n_pix, n_pix))
    yy, xx = np.mgrid[0:n_pix, 0:n_pix]
    hw = 0.5 * WIDTH
    len_vis = np.zeros(n_fibers)
    for i in range(n_fibers):
        dx, dy = np.cos(ang[i]), np.sin(ang[i])
        h = 0.5 * length[i]
        len_vis[i] = _clip_len((cx[i], cy[i]), (dx, dy), h, n_pix)
        if len_vis[i] <= 0.0:
            continue
        r0 = int(max(0, min(cy[i] - h, cy[i] + h) - 3))
        r1 = int(min(n_pix, max(cy[i] - h, cy[i] + h) + 4))
        c0 = int(max(0, min(cx[i] - h, cx[i] + h) - 3))
        c1 = int(min(n_pix, max(cx[i] - h, cx[i] + h) + 4))
        if r1 <= r0 or c1 <= c0:
            continue
        px = xx[r0:r1, c0:c1] - cx[i]
        py = yy[r0:r1, c0:c1] - cy[i]
        t = np.clip(px * dx + py * dy, -h, h)
        dist = np.hypot(px - t * dx, py - t * dy)
        img[r0:r1, c0:c1] = np.maximum(img[r0:r1, c0:c1],
                                       np.clip(hw + 0.5 - dist, 0.0, 1.0))
    obs = BG + (FG - BG) * img + rng.normal(0.0, noise, img.shape)
    return {"img": np.clip(obs, 0.0, 1.0), "angles": ang, "length": length,
            "len_vis": len_vis, "cx": cx, "cy": cy, "n_pix": n_pix,
            "mu_deg": mu_deg, "kappa": kappa}


def count_crossings(scene: dict) -> int:
    """視野の中で線分どうしが交わる回数(交差の量の真値)。"""
    n = scene["angles"].size
    d = np.column_stack([np.cos(scene["angles"]), np.sin(scene["angles"])])
    h = 0.5 * scene["length"]
    c = np.column_stack([scene["cx"], scene["cy"]])
    p = c - d * h[:, None]
    q = c + d * h[:, None]
    hits = 0
    for i in range(n - 1):
        r = q[i] - p[i]
        s = q[i + 1:] - p[i + 1:]
        den = r[0] * s[:, 1] - r[1] * s[:, 0]
        ok = np.abs(den) > 1e-9
        w = p[i + 1:] - p[i]
        t = np.where(ok, (w[:, 0] * s[:, 1] - w[:, 1] * s[:, 0]) / np.where(ok, den, 1), -1)
        u = np.where(ok, (w[:, 0] * r[1] - w[:, 1] * r[0]) / np.where(ok, -den, 1), -1)
        inside = ok & (t >= 0) & (t <= 1) & (u >= 0) & (u <= 1)
        pts = p[i] + t[:, None] * r
        inside &= (pts[:, 0] >= 0) & (pts[:, 0] <= scene["n_pix"] - 1) & \
                  (pts[:, 1] >= 0) & (pts[:, 1] <= scene["n_pix"] - 1)
        hits += int(inside.sum())
    return hits


# --------------------------------------------------------------------------- #
# 2. 角度の統計 —— 素朴な平均と、2 倍角の円形平均                               #
# --------------------------------------------------------------------------- #
def naive_mean_deg(theta_rad, weights=None) -> float:
    """**素朴な算術平均**(まず壊れるところを見せるために置く)。

    角度を [0, 180) に畳んでから、ただの重み付き平均を取る。0 度と 179 度が
    同じ向きであることをこの式は知らない。
    """
    a = np.degrees(np.mod(np.asarray(theta_rad, np.float64), np.pi))
    w = np.ones_like(a) if weights is None else np.asarray(weights, np.float64)
    return float(np.sum(w * a) / max(np.sum(w), 1e-12))


def circ_stats(theta_rad, weights=None) -> dict:
    """2 倍角の円形統計。``mean_deg`` [0,180) と ``R``(合成ベクトル長 = 配向度)。

    向きは 180 度周期なので、2θ に写してから平均する(Mardia & Jupp)。
    ``R`` は Advani–Tucker の配向テンソルの固有値差 λ1−λ2 に厳密に一致する。
    """
    a = np.asarray(theta_rad, np.float64)
    w = np.ones_like(a) if weights is None else np.asarray(weights, np.float64)
    sw = max(float(np.sum(w)), 1e-12)
    z = complex(float(np.sum(w * np.cos(2 * a)) / sw),
                float(np.sum(w * np.sin(2 * a)) / sw))
    return {"mean_deg": float(np.degrees(np.mod(np.angle(z) / 2.0, np.pi))),
            "R": float(abs(z))}


def orientation_tensor(theta_rad, weights=None) -> dict:
    """配向テンソル ⟨p pᵀ⟩ を **fullseye の** :func:`ledger.moment_axes` で解く。

    ``p`` と ``−p`` を両方入れた点群にすると重心が原点になり、共分散が
    そのまま ⟨p pᵀ⟩(Advani–Tucker)になる。固有値の差が配向度。
    """
    a = np.asarray(theta_rad, np.float64).ravel()
    w = np.ones_like(a) if weights is None else np.asarray(weights, np.float64).ravel()
    # 重みは複製回数では表せないので、重みの大きい順に間引いて等重みの点群にする
    keep = w > 0
    a, w = a[keep], w[keep]
    if a.size == 0:
        return {"a1": np.nan, "a2": np.nan, "aniso": np.nan, "deg": np.nan}
    m = min(a.size, 20000)
    idx = np.argsort(-w)[:m]
    a = np.repeat(a[idx], np.maximum(1, np.rint(w[idx] / w[idx].max() * 8)).astype(int))
    p = np.column_stack([np.cos(a), np.sin(a)])
    pts = np.vstack([p, -p])
    _, axes, eig = fs.ledger.moment_axes(pts)
    a1, a2 = float(eig[0]), float(eig[1])
    v = np.asarray(axes)[:, 0]
    return {"a1": a1, "a2": a2, "aniso": a1 - a2,
            "deg": float(np.degrees(np.mod(np.arctan2(v[1], v[0]), np.pi)))}


# --------------------------------------------------------------------------- #
# 3. 構造テンソル —— 勾配は fullseye の sobel_amp / sobel_dir から組む          #
# --------------------------------------------------------------------------- #
def structure_tensor(img, sigma_d: float = SIG_D, sigma_i: float = SIG_I) -> dict:
    """局所構造テンソルと、そこから出る配向角・コヒーレンス。

    勾配は進化 op の ``sobel_amp``(振幅)と ``sobel_dir``(向き、[0,1] に
    写像)を組み合わせて (gx, gy) に戻す。振幅は最大値で正規化されているが、
    固有ベクトルもコヒーレンスも **比** なので全体倍率は効かない。

    ``sigma_d`` = 微分スケール(勾配を取る前のぼかし)、``sigma_i`` = 積分
    スケール(外積を平均する窓)。**2 つは別物** で、片方で代用できない。
    """
    sm = _gauss2d(img, sigma_d)
    amp = np.asarray(fs.apply(sm, "sobel_amp"))
    ang = (2.0 * np.asarray(fs.apply(sm, "sobel_dir")) - 1.0) * np.pi
    gx, gy = amp * np.cos(ang), amp * np.sin(ang)
    jxx = _gauss2d(gx * gx, sigma_i)
    jyy = _gauss2d(gy * gy, sigma_i)
    jxy = _gauss2d(gx * gy, sigma_i)
    phi = 0.5 * np.arctan2(2.0 * jxy, jxx - jyy)          # 勾配の主方向
    theta = np.mod(phi + 0.5 * np.pi, np.pi)              # 繊維の向き
    tr = jxx + jyy
    dif = np.hypot(jxx - jyy, 2.0 * jxy)
    return {"theta": theta, "energy": tr, "coh": dif / (tr + 1e-12),
            "jxx": jxx, "jyy": jyy, "jxy": jxy}


def global_tensor(img, sigma_d: float = SIG_D) -> dict:
    """**ゼロ点**: 画像全体で構造テンソルを 1 個だけ作る(局所平均をしない)。"""
    sm = _gauss2d(img, sigma_d)
    amp = np.asarray(fs.apply(sm, "sobel_amp"))
    ang = (2.0 * np.asarray(fs.apply(sm, "sobel_dir")) - 1.0) * np.pi
    gx, gy = amp * np.cos(ang), amp * np.sin(ang)
    jxx, jyy, jxy = float((gx * gx).mean()), float((gy * gy).mean()), float((gx * gy).mean())
    phi = 0.5 * np.arctan2(2.0 * jxy, jxx - jyy)
    tr = jxx + jyy
    return {"deg": float(np.degrees(np.mod(phi + 0.5 * np.pi, np.pi))),
            "R": float(np.hypot(jxx - jyy, 2.0 * jxy) / (tr + 1e-12))}


def measure(scene: dict, sigma_d: float = SIG_D, sigma_i: float = SIG_I,
            weight: str = "coh", margin: int = 0) -> dict:
    """構造テンソル → 重み付き円形統計。``weight`` = none / energy / coh。"""
    st = structure_tensor(scene["img"], sigma_d, sigma_i)
    th, en, co = st["theta"], st["energy"], st["coh"]
    if margin:
        th, en, co = (a[margin:-margin, margin:-margin] for a in (th, en, co))
    w = {"none": np.ones_like(en), "energy": en, "coh": en * co}[weight]
    cs = circ_stats(th.ravel(), w.ravel())
    return {"mean_deg": cs["mean_deg"], "R": cs["R"],
            "naive_deg": naive_mean_deg(th.ravel(), w.ravel()),
            "theta": th, "w": w, "st": st}


# --------------------------------------------------------------------------- #
# 節 1. ゼロ点 —— 画像全体で 1 個の構造テンソル                                 #
# --------------------------------------------------------------------------- #
def section_zero_point() -> dict:
    print("\n" + "=" * 78)
    print("1) ゼロ点 —— 画像全体で構造テンソルを 1 個(局所平均をしない)")
    print("=" * 78)

    sc = make_scene()
    truth = circ_stats(sc["angles"], sc["len_vis"])
    g = global_tensor(sc["img"])
    print("  単峰(平均 %.0f 度・κ=%.0f):" % (MU_DEG, KAPPA))
    print("    真値(視野内の長さ基準)  平均 %.2f 度 / 配向度 %.4f"
          % (truth["mean_deg"], truth["R"]))
    print("    ゼロ点                    平均 %.2f 度 / 配向度 %.4f  (%+.2f 度)"
          % (g["deg"], g["R"], g["deg"] - truth["mean_deg"]))
    print("    -> 単峰ならよく当たる。ただし出るのは **数字 2 個だけ** で、"
          "分布は出ない。")

    sc2 = make_scene(bimodal=True)
    g2 = global_tensor(sc2["img"])
    t2 = circ_stats(sc2["angles"], sc2["len_vis"])
    a = sc2["angles"]
    grp0 = np.abs(np.mod(a + np.pi / 4, np.pi) - np.pi / 4) < np.pi / 4
    r0 = circ_stats(a[grp0], sc2["len_vis"][grp0])["R"]
    r1 = circ_stats(a[~grp0], sc2["len_vis"][~grp0])["R"]
    print("\n  ★二峰(0 度と 90 度を半々):")
    print("    ゼロ点  平均 %.2f 度 / 配向度 %.4f  <- 「向きが無い」と報告する"
          % (g2["deg"], g2["R"]))
    print("    真値    全体の配向度 %.4f だが、**群ごと** の配向度は %.4f / %.4f"
          % (t2["R"], r0, r1))
    print("    -> テンソル 1 個には峰が 1 つしか入らない。**分布を測る必要がある**。")

    figs.save_grid("scene",
                   [sc["img"], sc2["img"]],
                   ["単峰 平均 %.0f 度 κ=%.0f" % (MU_DEG, KAPPA),
                    "二峰 0 度と 90 度"],
                   title="繊維を撒いた場面(%d px 角、%d 本)" % (N_PIX, N_FIB))
    return {"truth": truth, "zero": g, "bimodal": (g2, r0, r1)}


# --------------------------------------------------------------------------- #
# 節 2. ★★素朴な平均が 180 度周期で壊れる                                      #
# --------------------------------------------------------------------------- #
def section_wrap_around() -> dict:
    print("\n" + "=" * 78)
    print("2) ★★素朴な算術平均は 180 度周期で壊れる(円形平均に変えるだけで直る)")
    print("=" * 78)
    print("   真の平均 [deg]   算術平均 [deg]  誤差      円形平均 [deg]  誤差")

    mus, naive, circ, tru = [], [], [], []
    for mu in (0.0, 15.0, 30.0, 60.0, 90.0, 150.0, 175.0):
        sc = make_scene(mu_deg=mu)
        t = circ_stats(sc["angles"], sc["len_vis"])["mean_deg"]
        m = measure(sc)
        e_n = _ang_err(m["naive_deg"], t)
        e_c = _ang_err(m["mean_deg"], t)
        mus.append(mu)
        naive.append(m["naive_deg"])
        circ.append(m["mean_deg"])
        tru.append(t)
        print("      %6.1f          %6.2f     %+7.2f      %6.2f     %+6.2f"
              % (t, m["naive_deg"], e_n, m["mean_deg"], e_c))

    en = [abs(_ang_err(n, t)) for n, t in zip(naive, tru)]
    ec = [abs(_ang_err(c, t)) for c, t in zip(circ, tru)]
    print("\n  ★★算術平均の誤差は最大 %.1f 度(真の平均 %.0f 度のとき %.1f 度と"
          "報告する)。" % (max(en), tru[int(np.argmax(en))], naive[int(np.argmax(en))]))
    print("     0 度付近と 179 度付近の繊維は **同じ向き** なのに、数として"
          "平均すると打ち消して 90 度へ寄る。")
    print("  ★2 倍角の円形平均に変えると誤差は最大 %.1f 度。**画像も測定も"
          "1 ビットも変えていない** —— 平均の取り方だけの差。" % max(ec))

    figs.save_plot("wrap",
                   [("算術平均", tru, naive), ("2 倍角の円形平均", tru, circ),
                    ("真値(y=x)", tru, tru)],
                   xlabel="真の平均角度 [deg]", ylabel="推定した平均角度 [deg]",
                   title="180 度周期を無視した平均は 90 度へ寄る")
    return {"mu": mus, "naive": naive, "circ": circ, "true": tru}


def _ang_err(est_deg: float, true_deg: float) -> float:
    """180 度周期で測った符号つきの角度差 [deg]("最も近い方向" までの差)。"""
    d = (est_deg - true_deg + 90.0) % 180.0 - 90.0
    return float(d)


# --------------------------------------------------------------------------- #
# 節 3. 真値が 3 通りある                                                       #
# --------------------------------------------------------------------------- #
def section_which_truth() -> dict:
    print("\n" + "=" * 78)
    print("3) ★真値が 3 通りある —— 本数 / 撒いた長さ / 視野内の長さ")
    print("=" * 78)

    out = {}
    for tag, couple in (("対照群: 長さと角度は独立", False),
                        ("処理群: 長い繊維ほど揃う(射出成形)", True)):
        sc = make_scene(couple=couple)
        ws = [("本数基準", None), ("撒いた長さ基準", sc["length"]),
              ("視野内の長さ基準", sc["len_vis"])]
        print("\n  %s" % tag)
        stats = []
        for name, w in ws:
            t = circ_stats(sc["angles"], w)
            ot = orientation_tensor(sc["angles"], w)
            stats.append((name, t))
            print("    %-18s 平均 %6.2f 度 / 配向度 %.4f  "
                  "(配向テンソル λ1-λ2 = %.4f)"
                  % (name, t["mean_deg"], t["R"], ot["aniso"]))
        m = measure(sc)
        print("    %-18s 平均 %6.2f 度 / 配向度 %.4f" % ("推定(画素)",
                                                          m["mean_deg"], m["R"]))
        dr = [abs(m["R"] - t["R"]) for _, t in stats]
        print("    -> 配向度で見ていちばん近い真値: **%s**(差 %.4f)。"
              "本数基準との差は %.4f。"
              % (stats[int(np.argmin(dr))][0], min(dr), dr[0]))
        out[tag] = (stats, m)

    (s_ctl, m_ctl), (s_cpl, m_cpl) = out.values()
    spread_ctl = max(t["R"] for _, t in s_ctl) - min(t["R"] for _, t in s_ctl)
    spread_cpl = max(t["R"] for _, t in s_cpl) - min(t["R"] for _, t in s_cpl)
    print("\n  ★対照群では 3 つの真値の配向度の開きは %.4f しかない —— 長さと角度が"
          "独立なら、どれで重みを付けても同じ母数を推定するから。" % spread_ctl)
    print("  ★★処理群(長さと角度に相関を入れる)では開きが %.4f に広がり、"
          "**どれを真値と呼ぶかで結論が変わる**。" % spread_cpl)
    print("     画素ごとの測定は面積 = 長さで重みがつくので、本数基準の真値と"
          "比べると配向度が %+.1f %% ずれて見える(測定器のせいではない)。"
          % (100 * (m_cpl["R"] - s_cpl[0][1]["R"]) / s_cpl[0][1]["R"]))
    print("  検算: 配向テンソルの固有値差 λ1-λ2 は 2 倍角の合成ベクトル長 R に"
          "厳密に一致する(上の表の 2 列が同じ値)。")
    return {"ctl": (s_ctl, m_ctl), "cpl": (s_cpl, m_cpl)}


# --------------------------------------------------------------------------- #
# 節 4. ★★重みを選ばないと配向度は必ず小さく出る                               #
# --------------------------------------------------------------------------- #
def section_weights() -> dict:
    print("\n" + "=" * 78)
    print("4) ★★重みの選び方 —— 平均角度は動かないのに、配向度は 3 割変わる")
    print("=" * 78)

    sc = make_scene()
    truth = circ_stats(sc["angles"], sc["len_vis"])
    print("   重み                平均 [deg]  誤差     配向度    真値との比")
    rows = []
    for w, name in (("none", "全画素を等しく"), ("energy", "勾配エネルギー"),
                    ("coh", "コヒーレンス×エネルギー")):
        m = measure(sc, weight=w)
        rows.append((name, m["mean_deg"], m["R"]))
        print("   %-22s %6.2f    %+5.2f    %.4f    %+.1f %%"
              % (name, m["mean_deg"], _ang_err(m["mean_deg"], truth["mean_deg"]),
                 m["R"], 100 * (m["R"] - truth["R"]) / truth["R"]))
    print("   %-22s %6.2f      --      %.4f       --" % ("真値(視野内の長さ)",
                                                          truth["mean_deg"], truth["R"]))

    print("\n  ★★全画素を等しく数えると配向度が %+.0f %% —— 背景には向きが無く、"
          "勾配が雑音に支配されて **一様分布を足す** から。"
          % (100 * (rows[0][2] - truth["R"]) / truth["R"]))
    print("  ★平均角度のほうは重みを変えてもほとんど動かない(%.1f / %.1f / %.1f 度)。"
          % (rows[0][1], rows[1][1], rows[2][1]))
    print("     **同じ 1 枚の絵から出した 2 つの量が、まったく違う壊れ方をする** ——"
          "\n     どちらか片方だけを見て「よく合っている」と言えない。")

    m = measure(sc)
    # ★角度は周期量なので colorize_depth で塗ると 0 度と 179 度が正反対の色に
    #   なる。fullseye には循環 LUT の名前は無いが、colorize_flow に
    #   (cos2θ, sin2θ) を渡すと 2 倍角の循環 LUT になる(末尾「道具の穴」(f))。
    hue = np.asarray(fs.colorize_flow(np.cos(2 * m["theta"]) * m["st"]["coh"],
                                      np.sin(2 * m["theta"]) * m["st"]["coh"]))
    figs.save_grid("field",
                   [sc["img"], hue, m["st"]["coh"]],
                   ["観測画像", "配向角(循環 LUT)", "コヒーレンス"],
                   title="局所構造テンソルの出力(σ_d=%.0f, σ_i=%.0f px)"
                         % (SIG_D, SIG_I), ncols=3)

    # ヒストグラム(重みの有無で形がどう変わるか)
    edges = np.linspace(0, 180, 61)
    ctr = 0.5 * (edges[1:] + edges[:-1])
    h_true, _ = np.histogram(np.degrees(sc["angles"]), edges, weights=sc["len_vis"])
    m_none = measure(sc, weight="none")
    h_none, _ = np.histogram(np.degrees(m_none["theta"]).ravel(), edges)
    h_coh, _ = np.histogram(np.degrees(m["theta"]).ravel(), edges,
                            weights=m["w"].ravel())
    figs.save_plot("histogram",
                   [("真値(視野内の長さ)", ctr, h_true / h_true.sum()),
                    ("重みなし", ctr, h_none / h_none.sum()),
                    ("コヒーレンス×エネルギー", ctr, h_coh / h_coh.sum())],
                   xlabel="配向角 [deg]", ylabel="確率(3 度ごと)",
                   title="重みなしの分布は背景の一様成分で薄まる")
    return {"rows": rows, "truth": truth}


# --------------------------------------------------------------------------- #
# 節 5-7. 密度 / 平滑化の窓 / 縁                                                #
# --------------------------------------------------------------------------- #
def section_density() -> dict:
    print("\n" + "=" * 78)
    print("5) ★★繊維の交差 —— 予想と逆に、配向度は **高め** にずれる")
    print("=" * 78)
    print("  **同じ繊維に本数を足していく**(400 本の池から先頭 n 本)—— こうしないと"
          "\n  本数を変えるたびに別の標本になり、密度の効果と標本のばらつきが混ざる。")
    print("\n   本数   交差点 [件]  面積率 [%]  配向度(推定)  真値    偏り"
          "     平均角度の誤差")

    ns, cross, bias, errs, rs = [], [], [], [], []
    for n in (40, 100, 200, 400):
        sc = make_scene(n_fibers=n, n_pool=400)
        cr = count_crossings(sc)
        t = circ_stats(sc["angles"], sc["len_vis"])
        m = measure(sc)
        frac = 100 * float((sc["img"] > 0.5 * (FG + BG)).mean())
        ns.append(n)
        cross.append(cr)
        rs.append(m["R"])
        bias.append(m["R"] - t["R"])
        errs.append(abs(_ang_err(m["mean_deg"], t["mean_deg"])))
        print("   %4d    %6d      %5.1f       %.4f     %.4f  %+.4f      %+5.2f 度"
              % (n, cr, frac, m["R"], t["R"], m["R"] - t["R"],
                 _ang_err(m["mean_deg"], t["mean_deg"])))

    print("\n  ★★予想が外れた(2 か所)。")
    print("   1) 「交差点では 2 方向が混ざるので配向度は落ちる」と踏んでいたが、"
          "**偏りは %+.4f -> %+.4f と逆向きに増える**。"
          % (bias[0], bias[-1]))
    print("      混ざった画素はコヒーレンスが下がる = **重みも下がる** ので、"
          "分布から抜けるだけで薄めない。\n      残るのは揃った画素なので、"
          "配向度はむしろ **高めに出る**。")
    print("   2) 「平均角度もずれる」も外れ: 誤差は %.2f -> %.2f 度でほとんど"
          "動かない。中間角は分布の **両側から等しく** 出る。"
          % (errs[0], errs[-1]))
    figs.save_plot("density",
                   [("配向度の偏り(推定−真値)", cross, bias),
                    ("平均角度の誤差 [deg]", cross, errs),
                    ("偏りゼロ", cross, [0.0] * len(cross))],
                   xlabel="視野内の交差点 [件]", ylabel="偏り / 誤差 [deg]",
                   title="交差は配向度を **高め** にずらす(予想と逆)")
    return {"n": ns, "cross": cross, "R": rs, "bias": bias, "err": errs}


def section_scales() -> dict:
    print("\n" + "=" * 78)
    print("6) ★平滑化の窓 —— 微分スケールと積分スケールは別物")
    print("=" * 78)

    sc = make_scene()
    truth = circ_stats(sc["angles"], sc["len_vis"])
    print("   σ_i [px]  平均 [deg]  誤差     配向度   Σw(重みの総和)  分子 |Σ w e^{2iθ}|")
    sig, rr, ee = [], [], []
    for s in (1.0, 2.0, 4.0, 8.0, 16.0, 24.0):
        m = measure(sc, sigma_i=s)
        num = abs(np.sum(m["w"] * np.exp(2j * m["theta"])))
        sig.append(s)
        rr.append(m["R"])
        ee.append(abs(_ang_err(m["mean_deg"], truth["mean_deg"])))
        print("    %5.1f     %6.2f    %+5.2f    %.4f    %10.1f        %10.1f"
              % (s, m["mean_deg"], _ang_err(m["mean_deg"], truth["mean_deg"]),
                 m["R"], float(np.sum(m["w"])), float(num)))

    print("\n  ★★平均角度が σ_i を変えても **1 桁目まで動かない** のは偶然では"
          "ありません(上の最後の列)。")
    print("     w·e^{2iθ} = −[(Jxx−Jyy) + 2i·Jxy] が恒等式で、ガウス平滑化は"
          "総和を保つので、**分子は σ_i に依らない**。")
    print("     一方 Σw = Σ(トレース×コヒーレンス)は平滑化で局所の打ち消しが"
          "増えるぶん縮む。だから")
    print("  ★★配向度は σ_i とともに **単調に上がる**(%.4f -> %.4f、真値 %.4f)"
          " —— 揃ったのではなく **分母が縮んだだけ**。"
          % (rr[0], rr[-1], truth["R"]))
    print("     窓を広げると配向度が良く見える、というのは測っている量の性質で、"
          "材料の性質ではない。")

    # --- 微分スケールの役目は別 —— 雑音を上げた対照群で切り分ける ---------- #
    print("\n   微分スケール σ_d を振る(雑音 1σ を 2 段階で)。σ_i = %.0f px 固定:"
          % SIG_I)
    print("   σ_d [px]   雑音 %.3f: 平均 / 誤差 / 配向度      雑音 %.3f: 平均 / 誤差 / 配向度"
          % (NOISE, 5 * NOISE))
    sd_list, sd_r_lo, sd_r_hi, sd_e_lo = [], [], [], []
    sc_hi = make_scene(noise=5 * NOISE)
    t_hi = circ_stats(sc_hi["angles"], sc_hi["len_vis"])
    for sd in (0.0, 0.5, 1.0, 2.0, 4.0):
        a = measure(sc, sigma_d=sd)
        b = measure(sc_hi, sigma_d=sd)
        sd_list.append(sd)
        sd_r_lo.append(a["R"])
        sd_r_hi.append(b["R"])
        sd_e_lo.append(abs(_ang_err(a["mean_deg"], truth["mean_deg"])))
        print("     %4.1f      %6.2f / %+5.2f / %.4f          %6.2f / %+5.2f / %.4f"
              % (sd, a["mean_deg"], _ang_err(a["mean_deg"], truth["mean_deg"]), a["R"],
                 b["mean_deg"], _ang_err(b["mean_deg"], t_hi["mean_deg"]), b["R"]))
    j_hi = int(np.argmax(sd_r_hi))
    print("  ★σ_d の効き方は σ_i と違う。雑音 %.3f では上げても配向度は良くならず、"
          "%.1f px では %.4f -> %.4f と落ちる(過平滑化)。" %
          (NOISE, sd_list[-1], sd_r_lo[0], sd_r_lo[-1]))
    print("     雑音を 5 倍にすると **最適点が現れる**: σ_d=0 の %.4f が "
          "σ_d=%.1f px で %.4f(真値 %.4f)。"
          % (sd_r_hi[0], sd_list[j_hi], sd_r_hi[j_hi], t_hi["R"]))
    print("     σ_i を増やしても代わりにならない —— σ_i は方向を集めるが、"
          "雑音の勾配そのものは消せない。")
    print("  ★ここでも 2 つの量が別々に動く: 平均角度の誤差は σ_d とともに"
          "**単調に改善**(%.2f -> %.2f 度)、配向度は途中で悪化に転じる。"
          % (sd_e_lo[0], sd_e_lo[-1]))
    figs.save_plot("scales",
                   [("配向度(推定)", sig, rr),
                    ("真値の配向度", sig, [truth["R"]] * len(sig)),
                    ("平均角度の誤差 [deg]", sig, ee)],
                   xlabel="積分スケール σ_i [px]", ylabel="配向度 / 誤差 [deg]",
                   title="窓を広げると配向度が上がる(分母が縮むだけ)")
    return {"sigma": sig, "R": rr, "err": ee, "sd": sd_list,
            "sd_r_lo": sd_r_lo, "sd_r_hi": sd_r_hi, "truth": truth}


def section_border() -> dict:
    print("\n" + "=" * 78)
    print("7) ★画像の縁 —— 対照群で切り分ける")
    print("=" * 78)

    sc = make_scene()
    truth = circ_stats(sc["angles"], sc["len_vis"])
    m_all = measure(sc, margin=0)
    m_in = measure(sc, margin=24)
    st = structure_tensor(sc["img"])
    mask = np.ones_like(st["coh"], bool)
    mask[24:-24, 24:-24] = False
    w = (st["energy"] * st["coh"])[mask]
    edge = circ_stats(st["theta"][mask], w)
    print("   全面        平均 %.2f 度 / 配向度 %.4f" % (m_all["mean_deg"], m_all["R"]))
    print("   縁 24 px を捨てる  平均 %.2f 度 / 配向度 %.4f"
          % (m_in["mean_deg"], m_in["R"]))
    print("   縁 24 px **だけ**  平均 %.2f 度 / 配向度 %.4f"
          % (edge["mean_deg"], edge["R"]))
    print("   真値              平均 %.2f 度 / 配向度 %.4f"
          % (truth["mean_deg"], truth["R"]))
    print("\n  ★予想が外れた: 「縁に沿った 0/90 度の偽ピークが立つ」と踏んでいたが、"
          "\n     全面 %.4f と縁を捨てた %.4f の差は %.4f しかない。"
          % (m_all["R"], m_in["R"], abs(m_all["R"] - m_in["R"])))
    print("     縁だけを取り出しても配向度 %.4f・平均 %.1f 度で、"
          "偽ピークは見えない。" % (edge["R"], edge["mean_deg"]))
    band = 100 * (1.0 - ((N_PIX - 4) / N_PIX) ** 2)
    print("     理由は面積比と重み: 勾配が縁を見るのは外周 2 px の帯 = 視野の "
          "%.1f %% だけで、\n     しかもそこは平坦なのでエネルギー重みが小さい。"
          "捨てた 24 px の帯(%.0f %%)の大半は普通の繊維だった。"
          % (band, 100 * (1 - ((N_PIX - 48) / N_PIX) ** 2)))
    return {"all": m_all, "inner": m_in, "edge": edge, "truth": truth}


# --------------------------------------------------------------------------- #
# 節 8. 道具の穴                                                                #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("8) 道具の穴(この PoC で fullseye を使ってみて)")
    print("=" * 78)

    # (a) 2-D の構造テンソルが 3 層のどこにも無い
    for name in ("structure_tensor", "structure_tensor2d", "orientation_field"):
        assert not hasattr(fs, name) and not hasattr(fs.ledger, name), name
    import ops
    reg = {o.name for o in ops.REGISTRY}
    assert "dc_structure_texture" in reg          # 名前は似ているが構造分解(別物)
    # ★"coherence" という名前は在るが、信号処理の 2 信号コヒーレンス(別物)
    import inspect as _insp
    assert hasattr(fs, "coherence")
    assert "Pxy" in (_insp.getdoc(fs.coherence) or ""), "中身が変わった"
    print("  (a) 2-D の構造テンソル(勾配の外積の局所平均)が facade にも台帳にも"
          "op にも無い。dc_structure_texture は名前が似ているが構造/テクスチャ"
          "分解で別物。この PoC は sobel_amp + sobel_dir から自前で組んだ。")
    print("      ★紛らわしい: fs.coherence は **在る** が、これは信号処理の"
          "2 信号コヒーレンス γ²(f)。構造テンソルのコヒーレンスとは無関係で、"
          "名前で探すと取り違える。")

    # (b) 符号つきの 2-D 勾配 (gx, gy) を返す口が無い
    assert "sobel_amp" in reg and "sobel_dir" in reg
    assert not hasattr(fs, "gradient2d") and not hasattr(fs.ledger, "gradient2d")
    assert hasattr(fs.ledger, "gradient3d"), "3-D 側にはある"
    print("  (b) 符号つきの 2-D 勾配 (gx, gy) を返す関数が無い(3-D の gradient3d "
          "はある)。振幅と向きに分かれた進化 op から三角関数で戻すしかない。")

    # (c) σ を直に渡す 2-D ガウスぼかしが公開経路に無い
    assert not hasattr(fs, "gauss_filter") and not hasattr(fs.ledger, "gauss_filter")
    assert hasattr(fs, "smooth_funct_1d_gauss")
    print("  (c) σ を引数に取る 2-D ガウスぼかしが無い。この PoC は 1-D の "
          "smooth_funct_1d_gauss を行と列に掛けて代用した(分離可能なので厳密)。")

    # (d) 円形統計が無い
    for name in ("circular_mean", "circmean", "circular_variance", "von_mises_fit"):
        assert not hasattr(fs, name) and not hasattr(fs.ledger, name), name
    print("  (d) 円形統計(2 倍角の平均・合成ベクトル長・フォン・ミーゼス当てはめ)"
          "が無い。この PoC の 2 節が示すとおり、**無いと確実に間違える** 種類の"
          "道具なので、族に入れる価値が高い。")

    # (e) ★同じ族の 2 本で入力検査が食い違う
    p2 = np.random.default_rng(0).normal(size=(30, 2))
    got = fs.ledger.moment_axes(p2)               # (N,2) を **黙って受ける**
    assert np.asarray(got[1]).shape == (2, 2)
    try:
        fs.ledger.principal_moments(p2)           # 同じ族なのに (N,2) を拒む
        raise AssertionError("拒まなくなった(この節を書き換えること)")
    except ValueError:
        pass
    print("  (e) ★moment_axes は (N,2) の点群を **黙って受けて 2x2 を返す** のに、"
          "同じ族の principal_moments は (N,3) 以外を拒む。台帳の宣言は両方とも"
          "3-D。受けるほうが便利だったので本 PoC は使っているが、"
          "**同じ族で入力検査が食い違うのは事故のもと**。")

    # (f) 角度画像を「周期的な量」として塗る LUT —— 直接の口は無いが代用が在る
    assert hasattr(fs, "colorize_depth") and hasattr(fs, "diverging_lut")
    for name in ("cyclic_lut", "hsv_lut", "colorize_angle", "colorize_orientation"):
        assert not hasattr(fs, name) and not hasattr(fs.ledger, name), name
    assert hasattr(fs, "colorize_flow")           # ★これが代用になる
    th = np.linspace(0.0, np.pi, 32)
    rgb = np.asarray(fs.colorize_flow(np.cos(2 * th)[None, :], np.sin(2 * th)[None, :]))
    assert np.allclose(rgb[0, 0], rgb[0, -1], atol=0.02), "0 度と 180 度の色が違う"
    print("  (f) 角度(周期量)を塗る循環 LUT の **直接の口は無い**"
          "(colorize_depth で塗ると 0 度と 179 度が正反対の色になる)。"
          "★ただし colorize_flow に (cos2θ, sin2θ) を渡すと循環 LUT になる ——"
          "0 度と 180 度が同じ色になることを上で検算した。名前からは見つからない"
          "ので、族の説明に書く価値がある。")


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    print("=" * 78)
    print("繊維の配向分布を測る —— 角度は 180 度周期")
    print("視野 %d px 角 / 繊維 %d 本 / 長さ %.0f-%.0f px / 太さ %.1f px"
          % (N_PIX, N_FIB, LEN_LO, LEN_HI, WIDTH))
    print("真の分布: 2 倍角のフォン・ミーゼス(平均 %.0f 度、κ=%.0f)"
          % (MU_DEG, KAPPA))
    print("=" * 78)

    section_zero_point()
    section_wrap_around()
    section_which_truth()
    w = section_weights()
    section_density()
    section_scales()
    b = section_border()
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 角度は 180 度周期。算術平均は使わない(2 倍角の円形平均に固定する)。")
    print("  * 平均角度と配向度は別々に壊れる。片方が合っていても他方は %+.0f %% "
          "ずれうる。" % (100 * (w["rows"][0][2] - w["truth"]["R"]) / w["truth"]["R"]))
    print("  * 画素ごとの測定は長さで重みがつく。長さと角度に相関がある材料では、"
          "本数基準の真値と比べてはいけない。")
    print("  * 交差は配向度を **高め** にずらす(混ざった画素は重みが下がって"
          "抜けるだけ)。中心はずらさない。")
    print("  * 窓(σ_i)を広げると配向度は上がるが、分子は不変 —— 分母が縮んだ"
          "だけで、材料は揃っていない。")
    print("  * 縁の影響は(この場面では)%.4f と小さい。予想は外れた。"
          % abs(b["all"]["R"] - b["inner"]["R"]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
