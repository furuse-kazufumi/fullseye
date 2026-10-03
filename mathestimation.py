# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""mathestimation — 推定と統計の古典(割当・分布の距離・仮説検定・Cramér–Rao 下界・Kalman 平滑化・行列の指数と対数)。

2026-10-03 の棚卸しで、どの層にも op として無かった有名な道具(numpy + scipy だけ):

* **割当問題(Hungarian 法)** —— 追跡で「前のコマのどの点が今のどの点か」を、総コスト最小で 1 対 1 に結ぶ。
* **分布の距離**(KL・Jensen–Shannon・Bhattacharyya・Hellinger・χ²)—— ヒストグラムどうしを比べる物差し。
* **仮説検定**(対応のある t / Welch の t / Kolmogorov–Smirnov / χ² 適合度)—— 「その差は偶然で出る大きさか」。
* **Cramér–Rao 下界** —— 雑音のある計測で、**どんな不偏推定でもこれより精度は上がらない**という分散の下限。
  サブピクセル位置決めや校正の「これ以上は無理」の根拠。
* **Kalman フィルタと RTS 平滑化** —— 線形ガウスの状態空間モデルで、時系列から状態を逐次に推定する。
  平滑化の結果は、全データを一度に使う最小二乗と**厳密に同じ**になる(門)。
* **行列の指数と対数、SE(3)** —— 回転と剛体運動を「速度ベクトル」と行き来する(姿勢の補間・平均・誤差の表し方)。

門は ``tests/test_mathestimation.py``(閉じた式・定理・第 2 実装)。
"""
from __future__ import annotations

import itertools
import math

import numpy as np
from scipy import linalg, optimize, stats

__all__ = [
    "assign_hungarian",
    "hist_distance",
    "stat_ttest_paired", "stat_ttest_welch", "stat_ks_test", "stat_chi2_gof",
    "crlb_gaussian",
    "kalman_smooth",
    "mat_expm", "mat_logm", "se3_exp", "se3_log",
]


# ---------------------------------------------------------------------------- #
# 割当
# ---------------------------------------------------------------------------- #
def assign_hungarian(cost, *, maximize: bool = False) -> dict:
    """コスト行列 (n, m) の割当問題を解く(Kuhn 1955 / Munkres 1957 の Hungarian 法、scipy の実装)。

    行と列を 1 対 1 に結び、選んだコストの総和を最小(``maximize=True`` で最大)にする。n != m なら短い側が全部結ばれる。
    返り値 ``{"rows", "cols", "total", "pairs"}``。門: 小さな行列で全順列の総当たりと一致する。
    """
    C = np.asarray(cost, dtype=np.float64)
    if C.ndim != 2 or C.size == 0:
        raise ValueError("assign_hungarian: コストは空でない 2-D 行列")
    if not np.all(np.isfinite(C)):
        raise ValueError("assign_hungarian: コストに NaN/inf がある(禁止の組は大きな有限値で表す)")
    r, c = optimize.linear_sum_assignment(C, maximize=bool(maximize))
    return {"rows": r, "cols": c, "total": float(C[r, c].sum()), "pairs": np.stack([r, c], axis=1)}


def _assign_bruteforce(C, maximize=False):
    """門のための総当たり(n <= 8)。"""
    n, m = C.shape
    best = None
    if n <= m:
        for perm in itertools.permutations(range(m), n):
            v = sum(C[i, perm[i]] for i in range(n))
            if best is None or (v > best if maximize else v < best):
                best = v
    else:
        best = _assign_bruteforce(C.T, maximize)
    return float(best)


# ---------------------------------------------------------------------------- #
# 分布の距離
# ---------------------------------------------------------------------------- #
def hist_distance(p, q, metric: str = "kl", *, eps: float = 1e-12) -> float:
    """2 つのヒストグラム(非負、和で正規化する)の距離・発散。

    * ``"kl"`` —— Kullback–Leibler D(p‖q) = Σ p log(p/q)(非対称。q が 0 で p が正だと無限大 → eps で床)。
    * ``"js"`` —— Jensen–Shannon(対称、0..log 2、平方根は距離の公理を満たす)。
    * ``"bhattacharyya"`` —— −log Σ √(pq)。 ``"hellinger"`` —— √(1 − Σ √(pq))(0..1)。
    * ``"chi2"`` —— ½ Σ (p−q)²/(p+q)。
    門: 正規分布どうしの KL の閉じた式 / KL ≥ 0 で等号は同一分布 / MI = KL(p_xy ‖ p_x p_y)。
    """
    p = np.asarray(p, dtype=np.float64).ravel()
    q = np.asarray(q, dtype=np.float64).ravel()
    if p.shape != q.shape or p.size == 0:
        raise ValueError("hist_distance: p と q は同じ長さ(1 以上)")
    if np.any(p < 0) or np.any(q < 0) or not (np.all(np.isfinite(p)) and np.all(np.isfinite(q))):
        raise ValueError("hist_distance: ヒストグラムは有限な非負")
    sp, sq = p.sum(), q.sum()
    if sp <= 0 or sq <= 0:
        raise ValueError("hist_distance: 和が 0 のヒストグラムは比べられない")
    p, q = p / sp, q / sq
    if metric == "kl":
        # ★床(eps)は q が**ちょうど 0** の所だけに掛ける。最初は q 全体を np.maximum(q, eps) で床上げしていて、
        #   1e-49 のような小さな q が 1e-12 に持ち上がり p より大きくなって、KL(p‖p) が −3e-10(負!)になった
        #   (KL ≥ 0 の門で 2026-10-03 に捕まえた)。
        m = p > 0
        qm = np.where(q[m] > 0, q[m], eps)
        # KL ≥ 0 は定理。床を直したあとに残る負は丸め(~1e-16)だけなので 0 で切る。
        return float(max(0.0, np.sum(p[m] * (np.log(p[m]) - np.log(qm)))))
    if metric == "js":
        mm = 0.5 * (p + q)
        return 0.5 * hist_distance(p, mm, "kl") + 0.5 * hist_distance(q, mm, "kl")
    bc = float(np.sum(np.sqrt(p * q)))
    if metric == "bhattacharyya":
        return float(-math.log(max(bc, eps)))
    if metric == "hellinger":
        return float(math.sqrt(max(0.0, 1.0 - bc)))
    if metric == "chi2":
        s = p + q
        m = s > 0
        return float(0.5 * np.sum((p[m] - q[m]) ** 2 / s[m]))
    raise ValueError("hist_distance: metric は kl / js / bhattacharyya / hellinger / chi2(得たのは %r)" % (metric,))


# ---------------------------------------------------------------------------- #
# 仮説検定
# ---------------------------------------------------------------------------- #
def _sample(x, name, n_min=2):
    a = np.asarray(x, dtype=np.float64).ravel()
    if a.size < n_min or not np.all(np.isfinite(a)):
        raise ValueError("%s: 有限な標本が %d 個以上要る" % (name, n_min))
    return a


def stat_ttest_paired(x, y) -> dict:
    """対応のある t 検定: 同じ対象を 2 回測った差 d = x − y の平均が 0 か。

    t = mean(d) / (sd(d)/√n)、自由度 n−1、両側の p 値。返り値 ``{"t", "df", "p", "mean_diff"}``。
    """
    x, y = _sample(x, "stat_ttest_paired"), _sample(y, "stat_ttest_paired")
    if x.shape != y.shape:
        raise ValueError("stat_ttest_paired: 対応のある標本は同じ長さ")
    d = x - y
    n = d.size
    sd = float(np.std(d, ddof=1))
    if sd == 0:
        raise ValueError("stat_ttest_paired: 差がすべて同じ(分散 0)で t が定義されない")
    t = float(d.mean() / (sd / math.sqrt(n)))
    return {"t": t, "df": n - 1, "p": float(2 * stats.t.sf(abs(t), n - 1)), "mean_diff": float(d.mean())}


def stat_ttest_welch(x, y) -> dict:
    """Welch の t 検定: 分散が等しいと仮定しない 2 群の平均の差(自由度は Welch–Satterthwaite)。"""
    x, y = _sample(x, "stat_ttest_welch"), _sample(y, "stat_ttest_welch")
    vx, vy = np.var(x, ddof=1) / x.size, np.var(y, ddof=1) / y.size
    if vx + vy == 0:
        raise ValueError("stat_ttest_welch: 両群とも分散 0")
    t = float((x.mean() - y.mean()) / math.sqrt(vx + vy))
    df = float((vx + vy) ** 2 / (vx ** 2 / (x.size - 1) + vy ** 2 / (y.size - 1)))
    return {"t": t, "df": df, "p": float(2 * stats.t.sf(abs(t), df)), "mean_diff": float(x.mean() - y.mean())}


def stat_ks_test(x, y=None, *, dist: str = "norm") -> dict:
    """Kolmogorov–Smirnov 検定。``y`` を与えれば 2 標本(同じ分布から来たか)、無ければ標準正規分布との適合。

    D = 経験分布関数どうしの最大の差。p 値は scipy(厳密/漸近を自動で選ぶ)。
    """
    x = _sample(x, "stat_ks_test")
    if y is None:
        if dist != "norm":
            raise ValueError("stat_ks_test: 1 標本の比較先は 'norm'(標準正規)だけ")
        r = stats.kstest(x, "norm")
    else:
        r = stats.ks_2samp(x, _sample(y, "stat_ks_test"))
    return {"D": float(r.statistic), "p": float(r.pvalue)}


def stat_chi2_gof(observed, expected=None) -> dict:
    """χ² 適合度検定: 度数 ``observed`` が期待度数(既定は一様)に合うか。自由度 = 区分数 − 1。

    期待度数が 5 未満の区分があると近似が悪い(``low_expected`` に数を返す)。
    """
    o = _sample(observed, "stat_chi2_gof")
    if np.any(o < 0):
        raise ValueError("stat_chi2_gof: 度数は非負")
    e = np.full_like(o, o.sum() / o.size) if expected is None else _sample(expected, "stat_chi2_gof")
    if e.shape != o.shape or np.any(e <= 0):
        raise ValueError("stat_chi2_gof: 期待度数は同じ長さで正")
    e = e * (o.sum() / e.sum())
    chi2 = float(np.sum((o - e) ** 2 / e))
    df = o.size - 1
    return {"chi2": chi2, "df": df, "p": float(stats.chi2.sf(chi2, df)), "low_expected": int(np.sum(e < 5))}


# ---------------------------------------------------------------------------- #
# Cramér–Rao 下界
# ---------------------------------------------------------------------------- #
_MODELS = {
    # 名前 → f(x, θ)(θ は配列)。計測でよく当てはめる形。
    "constant": lambda x, th: np.full_like(x, th[0], dtype=np.float64),
    "line": lambda x, th: th[0] + th[1] * x,
    "gaussian_peak": lambda x, th: th[0] * np.exp(-0.5 * ((x - th[1]) / th[2]) ** 2),
    "exp_decay": lambda x, th: th[0] * np.exp(-th[1] * x),
    "sinusoid": lambda x, th: th[0] * np.sin(2 * math.pi * th[1] * x + th[2]),
}


def crlb_gaussian(x, theta, sigma: float = 1.0, *, model: str = "gaussian_peak") -> dict:
    """白色ガウス雑音(標準偏差 sigma)の下での Cramér–Rao 下界。

    y_i = f(x_i; θ) + ε_i、ε ~ N(0, σ²) のとき Fisher 情報行列 I = JᵀJ / σ²(J = ∂f/∂θ、中心差分)、
    **どんな不偏推定量の共分散も I⁻¹ 以上**。``std`` は各パラメータの標準偏差の下限 √diag(I⁻¹)。
    ``model``: ``constant``(c)/ ``line``(a + bx)/ ``gaussian_peak``(A, μ, s)/ ``exp_decay``(A, k)/ ``sinusoid``(A, f, φ)。
    門: 定数の平均なら σ²/n。直線の最小二乗(効率的な推定量)のモンテカルロ分散が下界に一致する。
    """
    x = _sample(x, "crlb_gaussian", 1)
    th = np.asarray(theta, dtype=np.float64).ravel()
    if model not in _MODELS:
        raise ValueError("crlb_gaussian: model は %s(得たのは %r)" % (sorted(_MODELS), model))
    sigma = float(sigma)
    if not sigma > 0:
        raise ValueError("crlb_gaussian: sigma は正")
    f = _MODELS[model]
    J = np.empty((x.size, th.size))
    for k in range(th.size):
        h = 1e-6 * max(1.0, abs(th[k]))
        tp, tm = th.copy(), th.copy()
        tp[k] += h
        tm[k] -= h
        J[:, k] = (f(x, tp) - f(x, tm)) / (2 * h)
    info = J.T @ J / sigma ** 2
    if np.linalg.matrix_rank(info) < th.size:
        raise ValueError("crlb_gaussian: Fisher 情報が退化(この x ではパラメータを区別できない)")
    cov = np.linalg.inv(info)
    return {"fisher": info, "cov": cov, "std": np.sqrt(np.diag(cov)), "model": model}


# ---------------------------------------------------------------------------- #
# Kalman フィルタと RTS 平滑化
# ---------------------------------------------------------------------------- #
def kalman_smooth(z, F, H, Q, R, x0, P0) -> dict:
    """線形ガウス状態空間モデル x_{k+1} = F x_k + w(w ~ N(0,Q))、z_k = H x_k + v(v ~ N(0,R))の
    Kalman フィルタ(前向き)と Rauch–Tung–Striebel 平滑化(後ろ向き)。

    ``z`` は (T, m) の観測(NaN の行は欠測として更新を飛ばす)。返り値 ``{"x_filt", "P_filt", "x_smooth", "P_smooth", "nll"}``。
    門: 平滑化の結果は、全観測と事前分布を一度に使う最小二乗(一括の MAP)と厳密に一致する。
    """
    z = np.atleast_2d(np.asarray(z, dtype=np.float64))
    if z.shape[0] == 1 and z.shape[1] > 1 and np.asarray(H).ndim == 2 and np.asarray(H).shape[0] == 1:
        z = z.T
    F, H, Q, R = (np.atleast_2d(np.asarray(a, dtype=np.float64)) for a in (F, H, Q, R))
    x = np.asarray(x0, dtype=np.float64).ravel()
    P = np.atleast_2d(np.asarray(P0, dtype=np.float64))
    n, m, T = x.size, H.shape[0], z.shape[0]
    if F.shape != (n, n) or H.shape != (m, n) or Q.shape != (n, n) or R.shape != (m, m) or P.shape != (n, n):
        raise ValueError("kalman_smooth: 行列の形が合わない(状態 %d、観測 %d)" % (n, m))
    if z.shape[1] != m:
        raise ValueError("kalman_smooth: 観測は (T, %d)" % m)
    xf, Pf, xp, Pp = np.empty((T, n)), np.empty((T, n, n)), np.empty((T, n)), np.empty((T, n, n))
    nll = 0.0
    for k in range(T):
        if k > 0:
            x = F @ x
            P = F @ P @ F.T + Q
        xp[k], Pp[k] = x, P
        if np.all(np.isfinite(z[k])):
            S = H @ P @ H.T + R
            K = linalg.solve(S, H @ P, assume_a="pos").T
            r = z[k] - H @ x
            x = x + K @ r
            P = (np.eye(n) - K @ H) @ P
            P = 0.5 * (P + P.T)
            nll += 0.5 * float(r @ linalg.solve(S, r) + np.linalg.slogdet(2 * math.pi * S)[1])
        xf[k], Pf[k] = x, P
    xs, Ps = xf.copy(), Pf.copy()
    for k in range(T - 2, -1, -1):
        C = linalg.solve(Pp[k + 1], F @ Pf[k], assume_a="pos").T
        xs[k] = xf[k] + C @ (xs[k + 1] - xp[k + 1])
        Ps[k] = Pf[k] + C @ (Ps[k + 1] - Pp[k + 1]) @ C.T
    return {"x_filt": xf, "P_filt": Pf, "x_smooth": xs, "P_smooth": Ps, "nll": nll}


# ---------------------------------------------------------------------------- #
# 行列の指数と対数、SE(3)
# ---------------------------------------------------------------------------- #
def mat_expm(A) -> np.ndarray:
    """行列の指数関数 e^A(Padé 近似 + scaling-and-squaring、scipy)。

    線形 ODE x' = A x の解 x(t) = e^{At} x(0)。歪対称 3×3 なら回転行列(Rodrigues の公式と一致)。
    """
    A = np.asarray(A, dtype=np.float64)
    if A.ndim != 2 or A.shape[0] != A.shape[1] or not np.all(np.isfinite(A)):
        raise ValueError("mat_expm: 有限な正方行列")
    return linalg.expm(A)


def mat_logm(A) -> np.ndarray:
    """行列の主対数 log A(e^X = A となる X のうち固有値の虚部が (−π, π] のもの、scipy)。

    負の実固有値を持つ行列は実の主対数を持たない → ValueError(複素数を黙って返さない)。
    """
    A = np.asarray(A, dtype=np.float64)
    if A.ndim != 2 or A.shape[0] != A.shape[1] or not np.all(np.isfinite(A)):
        raise ValueError("mat_logm: 有限な正方行列")
    ev = np.linalg.eigvals(A)
    if np.any((np.abs(ev.imag) < 1e-12) & (ev.real <= 0)):
        raise ValueError("mat_logm: 0 か負の実固有値がある(実の主対数が無い)")
    L = linalg.logm(A)
    return np.real_if_close(L, tol=1e6).astype(np.float64) if np.iscomplexobj(L) else L


def _hat(w):
    return np.array([[0.0, -w[2], w[1]], [w[2], 0.0, -w[0]], [-w[1], w[0], 0.0]])


def se3_exp(xi) -> np.ndarray:
    """SE(3) の指数写像: 6 次元のねじれ ξ = (v, ω)(並進速度 v、回転ベクトル ω)→ 4×4 の剛体変換。

    閉じた式(Rodrigues + 左ヤコビアン): R = I + sinθ/θ ω̂ + (1−cosθ)/θ² ω̂²、t = V v、
    V = I + (1−cosθ)/θ² ω̂ + (θ−sinθ)/θ³ ω̂²。θ → 0 は級数で。門: 4×4 の生成元の mat_expm と一致。
    """
    xi = np.asarray(xi, dtype=np.float64).ravel()
    if xi.size != 6 or not np.all(np.isfinite(xi)):
        raise ValueError("se3_exp: ξ は有限な 6 成分 (v, ω)")
    v, w = xi[:3], xi[3:]
    th = float(np.linalg.norm(w))
    W = _hat(w)
    if th < 1e-8:
        A, B, Cc = 1.0 - th ** 2 / 6, 0.5 - th ** 2 / 24, 1.0 / 6 - th ** 2 / 120
    else:
        A, B, Cc = math.sin(th) / th, (1 - math.cos(th)) / th ** 2, (th - math.sin(th)) / th ** 3
    R = np.eye(3) + A * W + B * W @ W
    V = np.eye(3) + B * W + Cc * W @ W
    T = np.eye(4)
    T[:3, :3], T[:3, 3] = R, V @ v
    return T


def se3_log(T) -> np.ndarray:
    """SE(3) の対数写像: 4×4 の剛体変換 → 6 次元のねじれ ξ = (v, ω)(回転角 < π)。門: se3_log(se3_exp(ξ)) = ξ。"""
    T = np.asarray(T, dtype=np.float64)
    if T.shape != (4, 4) or not np.all(np.isfinite(T)):
        raise ValueError("se3_log: 4×4 の有限な剛体変換")
    R, t = T[:3, :3], T[:3, 3]
    if np.abs(R @ R.T - np.eye(3)).max() > 1e-6 or abs(np.linalg.det(R) - 1) > 1e-6:
        raise ValueError("se3_log: 左上 3×3 が回転行列でない")
    c = float(np.clip((np.trace(R) - 1) / 2, -1.0, 1.0))
    th = math.acos(c)
    if th < 1e-8:
        w = 0.5 * np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    elif math.pi - th < 1e-6:
        raise ValueError("se3_log: 回転角が π に近く軸の向きが定まらない")
    else:
        w = th / (2 * math.sin(th)) * np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    W = _hat(w)
    th = float(np.linalg.norm(w))
    if th < 1e-8:
        Vinv = np.eye(3) - 0.5 * W
    else:
        Vinv = np.eye(3) - 0.5 * W + (1 / th ** 2) * (1 - th * math.sin(th) / (2 * (1 - math.cos(th)))) * W @ W
    return np.concatenate([Vinv @ t, w])
