# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Probability of detection (POD) — MIL-HDBK-1823A の â vs a / hit-miss 解析(numpy + scipy のみ)。

外観検査の性能を「この傷の大きさなら何 % の確率で見つかるか」で言う枠組み。
欠陥の大きさ ``a`` と検査系の応答 ``â``(あるいは見つけた/見落とした)の組から、
POD(a) 曲線・a50・a90・**a90/95**(a90 の 95 % 信頼上限 = 「90 % の確率で見つかると
95 % の信頼で言える最小の大きさ」)と、無欠陥部位の応答から誤検出確率を出す。
判定閾値 ``âdec`` を上げれば誤検出は減り a90/95 は伸びる —— その取引表まで。

5 つの op(並びは解析の順):

  * :func:`pod_ahat_fit` — â vs a の回帰 ``y = β0 + β1 x + ε, ε ~ N(0, σ²)`` を、
    **左右の打ち切り**つきの最尤法(Tobit 型)で当てる(1823A G.3.4)。雑音床より下の
    応答と飽和した応答は「その値以下 / 以上だった」としか分からない —— それを
    普通の最小二乗に入れると傾きが寝て σ が縮み、POD が楽観側にずれる。
    打ち切りが無ければ最小二乗の β と ``σ = sqrt(RSS/n)`` に**厳密に**一致する。
  * :func:`pod_from_ahat` — 回帰から POD(a) へ(1823A G.3.4.3)。
    ``POD(x) = Φ((x − μ)/σ_pod)``、``μ = (y_dec − β0)/β1``、``σ_pod = σ/β1``。
    a90/95 は (μ, σ_pod) の共分散をデルタ法で作り、``x90 + z_0.95 · se(x90)``。
  * :func:`pod_hitmiss_fit` — 見つけた/見落としたの 2 値データを一般化線形モデル
    (logit / probit / cloglog)で当てる(1823A G.4.1)。a90/95 は Wald(デルタ法)と
    尤度比(プロファイル尤度)の両方(G.4.2.2)。
  * :func:`pod_false_call` — 無欠陥部位の応答から誤検出確率(PFP)。経験値、
    二項の片側上限 PFP(50/90/95)(G.4.6 の表 G-I と同じ定義)、正規当てはめ(G.3.5)。
  * :func:`pod_decision_tradeoff` — ``âdec`` を振ったときの (a90/95, PFP) の取引表
    (G.3.6.2.4.1、図 G-28 の数表)。

座標の約束: ``log_size`` / ``log_response`` を立てると、回帰も POD 曲線も
``x = ln a`` / ``y = ln â`` の座標で行い、a50 などの大きさは**元の単位に戻して**返す。
打ち切りの閾値 ``censor_low`` / ``censor_high`` と ``a_dec`` は常に**元の â の単位**で渡す。

★仮定(1823A G.3.3 が「明示せよ」と言うもの): 散らばりは x によらず一定の正規、
POD 曲線のパラメータの不確かさは漸近正規(デルタ法)。データ数が少ないと
デルタ法の区間は楽観側に出る —— ``tests/test_pod.py`` の被覆率の門がそれを数える。

出典(公開文書のみ): MIL-HDBK-1823A, *Nondestructive Evaluation System Reliability
Assessment*, 2009(Distribution A)/ J. Tobin, *Econometrica* 26:24, 1958(打ち切り回帰)/
R. J. Olsen, *Econometrica* 46:1211, 1978(Tobit の対数尤度が凹になる再パラメータ化)/
P. McCullagh & J. A. Nelder, *Generalized Linear Models*, 2nd ed., 1989 /
C. J. Clopper & E. S. Pearson, *Biometrika* 26:404, 1934(二項の信頼限界)。
"""
from __future__ import annotations

import math
import numbers

import numpy as np

#: 1 つの表で受け付ける行数の上限(float64 へ上げる前に拒む)。
MAX_POD_ROWS = 1 << 20

_LINKS = ("logit", "probit", "cloglog")


def _proportion_inputs(k, n, confidence, op):
    """Validate scalar binomial-count inputs without silently truncating them."""
    if isinstance(k, (bool, np.bool_)) or not isinstance(k, numbers.Integral):
        raise ValueError("%s: k must be an integer, got %r" % (op, k))
    if isinstance(n, (bool, np.bool_)) or not isinstance(n, numbers.Integral):
        raise ValueError("%s: n must be an integer, got %r" % (op, n))
    k, n = int(k), int(n)
    if n < 1:
        raise ValueError("%s: n must be at least 1, got %d" % (op, n))
    if not 0 <= k <= n:
        raise ValueError("%s: require 0 <= k <= n, got k=%d, n=%d" % (op, k, n))
    if isinstance(confidence, (bool, np.bool_)):
        raise ValueError("%s: confidence must be in (0, 1), got %r" % (op, confidence))
    try:
        confidence = float(confidence)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("%s: confidence must be a finite number in (0, 1)" % op) from exc
    if not math.isfinite(confidence) or not 0.0 < confidence < 1.0:
        raise ValueError("%s: confidence must be in (0, 1), got %r" % (op, confidence))
    return k, n, confidence


def proportion_interval(k, n, *, confidence=0.95, sides="two", method="clopper_pearson"):
    """二項比率 ``k/n`` の点推定と信頼限界を返す(``table``)。

    ``sides`` は ``"two"``(両側)、``"lower"``(片側下限)、``"upper"``
    (片側上限)、``method`` は ``"clopper_pearson"``、``"wilson"``、
    ``"jeffreys"``。返り値は ``estimate``、``lower``、``upper``、``method``、
    ``confidence``、``sides``、``k``、``n`` を持つ。保証・合否判定には正確で
    保守的な Clopper--Pearson、推定には Wilson / Jeffreys を使い分ける。

    ``k=0`` / ``k=n`` も有限の限界を返す。たとえば 10/10 の 95 % 片側
    下限は 0.7411、0/20 の片側上限は 0.1391 である。

    空の入力(``n=0``)は ``ValueError`` を返す(理由: 比率を定義できない)。
    拒否(``ValueError``): 非整数の ``k`` / ``n``、``0 <= k <= n`` 違反、
    ``confidence`` が (0, 1) 外、未知の ``sides`` / ``method``。
    """
    op = "proportion_interval"
    k, n, confidence = _proportion_inputs(k, n, confidence, op)
    if sides not in ("two", "lower", "upper"):
        raise ValueError("%s: sides must be 'two', 'lower', or 'upper', got %r" % (op, sides))
    if method not in ("clopper_pearson", "wilson", "jeffreys"):
        raise ValueError("%s: unknown method %r" % (op, method))
    alpha = 1.0 - confidence
    tail = alpha / 2.0 if sides == "two" else alpha
    phat = k / n
    st = _stats()

    if method == "clopper_pearson":
        lower = 0.0 if k == 0 else float(st.beta.ppf(tail, k, n - k + 1))
        upper = 1.0 if k == n else float(st.beta.ppf(1.0 - tail, k + 1, n - k))
    elif method == "wilson":
        z = float(st.norm.ppf(1.0 - tail))
        den = 1.0 + z * z / n
        center = (phat + z * z / (2.0 * n)) / den
        half = z * math.sqrt(phat * (1.0 - phat) / n + z * z / (4.0 * n * n)) / den
        lower, upper = max(0.0, center - half), min(1.0, center + half)
    else:
        lower = 0.0 if k == 0 else float(st.beta.ppf(tail, k + 0.5, n - k + 0.5))
        upper = 1.0 if k == n else float(st.beta.ppf(1.0 - tail, k + 0.5, n - k + 0.5))

    if sides == "lower":
        upper = 1.0
    elif sides == "upper":
        lower = 0.0
    return {"estimate": phat, "lower": lower, "upper": upper, "method": method,
            "confidence": confidence, "sides": sides, "k": k, "n": n}


def trials_for_all_success(p_min, *, confidence=0.95):
    """全数成功で ``p >= p_min`` を片側 ``confidence`` で示す最小試行数(``scalar``)。

    返り値は整数で、Clopper--Pearson の全数成功時の閉形式
    ``(1-confidence)**(1/n) >= p_min`` に基づく。たとえば POD >= 0.90 を
    95 % 信頼で示すには 29/29 が必要である。誤警報率 ``p <= p_max`` を
    0 件で示す件数は ``trials_for_all_success(1-p_max, confidence=...)`` と同じ。

    拒否(``ValueError``): ``p_min`` または ``confidence`` が有限な (0, 1) 外。
    """
    op = "trials_for_all_success"
    for name, value in (("p_min", p_min), ("confidence", confidence)):
        if isinstance(value, (bool, np.bool_)):
            raise ValueError("%s: %s must be in (0, 1), got %r" % (op, name, value))
        try:
            fv = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("%s: %s must be a finite number in (0, 1)" % (op, name)) from exc
        if not math.isfinite(fv) or not 0.0 < fv < 1.0:
            raise ValueError("%s: %s must be in (0, 1), got %r" % (op, name, value))
        if name == "p_min":
            p_min = fv
        else:
            confidence = fv
    n = max(1, int(math.ceil(math.log1p(-confidence) / math.log(p_min))))
    # Guard against a quotient rounded onto an adjacent integer boundary.
    while (1.0 - confidence) ** (1.0 / n) < p_min:
        n += 1
    while n > 1 and (1.0 - confidence) ** (1.0 / (n - 1)) >= p_min:
        n -= 1
    return n


# --------------------------------------------------------------------------- #
# scipy は関数内で取る(spc.py と同じ作法: numpy だけの環境で import が落ちない)
# --------------------------------------------------------------------------- #
def _special():
    from scipy import special as _sp          # noqa: PLC0415 — 遅延 import は意図
    return _sp


def _stats():
    from scipy import stats as _st             # noqa: PLC0415
    return _st


# --------------------------------------------------------------------------- #
# 入力の検証(fail-closed)
# --------------------------------------------------------------------------- #
def _cols(table, op, needed):
    """表(列名 -> 1-D 配列)から必要な列を取り出す。長さが揃わなければ拒む。"""
    if not isinstance(table, dict):
        raise ValueError("%s: expected a table (a dict of column name -> 1-D array), got %s"
                         % (op, type(table).__name__))
    missing = [c for c in needed if c not in table]
    if missing:
        raise ValueError("%s: the table lacks column(s) %s — it has %s"
                         % (op, missing, sorted(map(str, table))))
    out, n = {}, None
    for c in needed:
        a = table[c]
        if isinstance(a, (str, bytes)):
            raise ValueError("%s: column %r is a string — expected an array" % (op, c))
        a = np.asarray(a).reshape(-1)
        if a.size > MAX_POD_ROWS:
            raise ValueError("%s: column %r has %d rows, over the %d cap"
                             % (op, c, a.size, MAX_POD_ROWS))
        if n is None:
            n = a.shape[0]
        elif a.shape[0] != n:
            raise ValueError("%s: column %r has %d rows but %r has %d — the columns of one "
                             "table must line up" % (op, c, a.shape[0], needed[0], n))
        out[c] = a
    if not n:
        raise ValueError("%s: the table is empty" % op)
    return out


def _real(a, name, op):
    """実数の 1-D 配列へ。文字列・object・複素・真偽・非有限は拒む。"""
    if np.ma.is_masked(a):
        raise ValueError("%s: %s is a masked array with masked entries" % (op, name))
    arr = np.asarray(a)
    if arr.dtype.kind not in "iuf":
        raise ValueError("%s: %s has dtype %r — expected real numbers" % (op, name, str(arr.dtype)))
    arr = arr.astype(np.float64).reshape(-1)
    if arr.size == 0:
        raise ValueError("%s: %s is empty" % (op, name))
    if not np.isfinite(arr).all():
        raise ValueError("%s: %s has non-finite values (nan/inf)" % (op, name))
    return arr


def _scalar(v, name, op):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, float, np.integer, np.floating)):
        raise ValueError("%s: %s must be a real number, got %r" % (op, name, v))
    v = float(v)
    if not math.isfinite(v):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, v))
    return v


def _level(level, op):
    lv = _scalar(level, "level", op)
    if not 0.5 < lv < 1.0:
        raise ValueError("%s: level must be in (0.5, 1) — a one-sided confidence, got %r" % (op, lv))
    return lv


def _flag(v, name, op):
    if not isinstance(v, (bool, np.bool_)):
        raise ValueError("%s: %s must be True or False, got %r" % (op, name, v))
    return bool(v)


def _to_x(a, log_size, op, what="size"):
    if log_size:
        if (a <= 0).any():
            raise ValueError("%s: log_size=True needs every %s > 0 (got min %g)"
                             % (op, what, float(a.min())))
        return np.log(a)
    return a.astype(np.float64)


def _from_x(x, log_size):
    return np.exp(x) if log_size else x


# --------------------------------------------------------------------------- #
# 共通: POD(x) = F((x − μ)/σ) の分位点と、その片側上限(水平方向のデルタ法)
# --------------------------------------------------------------------------- #
def _quantile_upper(mu, sig, cov, q, zl):
    """``x_q = μ + qσ`` と ``x_q + zl·se(x_q)``(``var = vμ + q² vσ + 2q c``)。"""
    q = np.asarray(q, dtype=np.float64)
    var = cov[0, 0] + q * q * cov[1, 1] + 2.0 * q * cov[0, 1]
    se = np.sqrt(np.maximum(var, 0.0))
    xq = mu + q * sig
    return xq, xq + zl * se, se


def _lower_curve(mu, sig, cov, zl, xgrid, qmin, qmax):
    """各 x について ``x_q + zl·se(x_q) = x`` を満たす q を二分法で解く(ベクトル化)。

    1823A の POD 曲線の信頼下限は「各 POD 水準 p の大きさ a_p の上限」をつないだ線
    —— だから a90/95 はこの線が 0.9 を横切る点と**厳密に**一致する(縦に区間を
    取る作り方では一致しない)。q の範囲の端に張り付いた点は端の値を返す。
    """
    lo = np.full(xgrid.shape, qmin)
    hi = np.full(xgrid.shape, qmax)
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        up = _quantile_upper(mu, sig, cov, mid, zl)[1]
        go_up = up < xgrid
        lo = np.where(go_up, mid, lo)
        hi = np.where(go_up, hi, mid)
    return 0.5 * (lo + hi)


def _bound_is_monotone(sig, cov, zl):
    """上限 ``x_q + zl se(x_q)`` が q について単調増加である十分条件 ``σ > zl·se(σ)``。

    Cauchy–Schwarz(``vμ vσ ≥ c²``)から ``|d se/dq| ≤ sqrt(vσ)`` なので、
    ``σ − zl sqrt(vσ) > 0`` なら下限曲線は 1 価で、二分法の根は一意。
    """
    return bool(sig - zl * math.sqrt(max(cov[1, 1], 0.0)) > 0.0)


def _size_grid(fit_lo, fit_hi, log_size, n):
    if log_size:
        return np.exp(np.linspace(math.log(fit_lo) - math.log(2.0),
                                  math.log(fit_hi) + math.log(1.5), n))
    span = fit_hi - fit_lo
    return np.linspace(fit_lo - 0.25 * span, fit_hi + 0.25 * span, n)


def _count(v, name, lo, hi, op):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s: %s must be an integer, got %r" % (op, name, v))
    v = int(v)
    if not lo <= v <= hi:
        raise ValueError("%s: %s must be in [%d, %d], got %d" % (op, name, lo, hi, v))
    return v


# =========================================================================== #
# 1. â vs a — 打ち切りつきの回帰(Tobit 型の最尤法)
# =========================================================================== #
def _tobit_terms(gam, th, X, y, st, sp):
    """Olsen の再パラメータ化 (γ = β/σ, θ = 1/σ) での対数尤度・勾配・ヘッセ行列。

    ★この座標では対数尤度が**大域的に凹**(Olsen 1978)なので、ニュートン法が
    初期値によらず唯一の最大へ行く。``st`` は -1 = 左打ち切り(y はその閾値)、
    0 = 観測、+1 = 右打ち切り。
    """
    k = X.shape[1]
    eta = X @ gam
    ll = 0.0
    g = np.zeros(k + 1)
    H = np.zeros((k + 1, k + 1))
    m = st == 0
    if m.any():
        Xo, yo = X[m], y[m]
        r = th * yo - eta[m]
        ll += m.sum() * (math.log(th) - 0.5 * math.log(2.0 * math.pi)) - 0.5 * float(r @ r)
        g[:k] += Xo.T @ r
        g[k] += m.sum() / th - float(r @ yo)
        H[:k, :k] -= Xo.T @ Xo
        H[:k, k] += Xo.T @ yo
        H[k, k] -= m.sum() / th ** 2 + float(yo @ yo)
    for side in (-1, 1):
        m = st == side
        if not m.any():
            continue
        Xc, yc = X[m], y[m]
        # 左: u = θL − x'γ、P = Φ(u)。右: u = x'γ − θH、P = Φ(u)。
        u = (th * yc - eta[m]) if side < 0 else (eta[m] - th * yc)
        lc = sp.log_ndtr(u)
        lam = np.exp(-0.5 * u * u - 0.5 * math.log(2.0 * math.pi) - lc)    # φ/Φ(安定)
        d2 = -lam * (u + lam)
        ll += float(lc.sum())
        # du/dγ = ∓x、du/dθ = ±y
        sx = -1.0 if side < 0 else 1.0
        sy = -sx
        g[:k] += sx * (Xc.T @ lam)
        g[k] += sy * float(lam @ yc)
        H[:k, :k] += (Xc.T * d2) @ Xc
        H[:k, k] += sx * sy * (Xc.T @ (d2 * yc))
        H[k, k] += float(d2 @ (yc * yc))
    H[k, :k] = H[:k, k]
    return ll, g, H


def pod_ahat_fit(table, size="a", response="ahat", log_size=False, log_response=False,
                 censor_low=None, censor_high=None):
    """â vs a の回帰を、左右の打ち切りつき最尤法で当てる(``table``)。

    モデル(MIL-HDBK-1823A G.3.4)は ``y = β0 + β1 x + ε, ε ~ N(0, σ²)``、
    ``x = a`` または ``ln a``、``y = â`` または ``ln â``。応答が ``censor_low`` 以下の
    行は**左打ち切り**(雑音床に埋もれて「それ以下だった」としか分からない)、
    ``censor_high`` 以上の行は**右打ち切り**(飽和)として、対数尤度に
    ``ln Φ((y_L − μ_i)/σ)`` / ``ln Φ((μ_i − y_H)/σ)`` で入る(Tobin 1958)。

    最大化は Olsen(1978)の座標 ``(γ, θ) = (β/σ, 1/σ)`` でのニュートン法 ——
    そこでは対数尤度が大域的に凹なので、解は一意で初期値に依らない。共分散は
    観測情報行列の逆を ``(β0, β1, σ)`` へ写したもの(最尤点では勾配が 0 なので
    ヤコビアンで厳密に写る)。

    ★打ち切りが 1 つも無ければ、最尤解は**最小二乗そのもの**: β は ``np.polyfit``
    と一致し、σ は ``sqrt(RSS/n)``(n で割る最尤推定。``n − 2`` ではない)。
    ★比較のため、打ち切りを無視して記録値のまま最小二乗した ``ols_beta0`` /
    ``ols_beta1`` / ``ols_sigma`` も返す —— 打ち切りの多いデータでは傾きが寝て
    σ が縮む(このモデルが要る理由)。

    返り: ``beta0`` ``beta1`` ``sigma`` ``cov``(3x3、並びは ``param_names``)、
    ``n`` ``n_left`` ``n_right`` ``n_censored`` ``loglik`` ``iterations``、座標の印
    ``log_size`` ``log_response``、打ち切り閾値、大きさの範囲 ``size_min`` / ``size_max``、
    当てに使った ``x`` ``y`` ``status``(-1 左 / 0 観測 / +1 右)。

    空の入力(``table`` が 0 行、または空の dict)は ValueError。
    拒否(``ValueError``): 空の表・列の欠け・長さ違い・非有限・文字列、観測(打ち切り
    でない)が 3 点未満か大きさが 1 種類しかない、応答が定数で散らばりが 0
    (POD が階段になりモデルが立たない)、``censor_low >= censor_high``、対数座標で 0 以下。
    """
    op = "pod_ahat_fit"
    lsz = _flag(log_size, "log_size", op)
    lrs = _flag(log_response, "log_response", op)
    c = _cols(table, op, (size, response))
    a = _real(c[size], size, op)
    ah = _real(c[response], response, op)
    lo = None if censor_low is None else _scalar(censor_low, "censor_low", op)
    hi = None if censor_high is None else _scalar(censor_high, "censor_high", op)
    if lo is not None and hi is not None and not lo < hi:
        raise ValueError("%s: censor_low (%g) must be below censor_high (%g)" % (op, lo, hi))
    st = np.zeros(a.size, dtype=np.int64)
    if lo is not None:
        st[ah <= lo] = -1
    if hi is not None:
        st[ah >= hi] = 1
    x = _to_x(a, lsz, op)
    # 応答の座標。打ち切りの行は閾値に置く(尤度はその値しか使わない)。
    yraw = ah.copy()
    if lo is not None:
        yraw[st == -1] = lo
    if hi is not None:
        yraw[st == 1] = hi
    if lrs:
        if (yraw <= 0).any():
            raise ValueError("%s: log_response=True needs every response (and censor_low) > 0 "
                             "— a response at or below 0 must be left-censored at a positive "
                             "censor_low" % op)
        y = np.log(yraw)
    else:
        y = yraw
    obs = st == 0
    if obs.sum() < 3:
        raise ValueError("%s: only %d uncensored response(s) — the scatter cannot be estimated "
                         "from fewer than 3" % (op, int(obs.sum())))
    if np.ptp(x[obs]) <= 0:
        raise ValueError("%s: every uncensored response comes from the same size — the slope "
                         "is not estimable" % op)

    X = np.column_stack([np.ones_like(x), x])
    # 素朴な最小二乗(比較用・初期値)
    b_all, *_ = np.linalg.lstsq(X, y, rcond=None)
    r_all = y - X @ b_all
    ols_sigma = float(np.sqrt((r_all @ r_all) / y.size))
    b0, *_ = np.linalg.lstsq(X[obs], y[obs], rcond=None)
    r0 = y[obs] - X[obs] @ b0
    s0 = float(np.sqrt((r0 @ r0) / obs.sum()))
    scale = max(float(np.ptp(y)), float(np.abs(y).max()), 1e-300)
    if s0 <= 1e-12 * scale:
        raise ValueError("%s: the uncensored responses lie exactly on a line (or are constant) "
                         "— the scatter sigma is 0, POD(a) would be a step and the model has "
                         "nothing to estimate" % op)

    sp = _special()
    th = 1.0 / s0
    gam = b0 * th
    ll, g, H = _tobit_terms(gam, th, X, y, st, sp)
    it = 0
    for it in range(1, 201):
        try:
            step = np.linalg.solve(-H, g)
        except np.linalg.LinAlgError as exc:
            raise ValueError("%s: the information matrix is singular — the data do not "
                             "identify the model" % op) from exc
        t = 1.0
        while True:
            th_n = th + t * step[2]
            if th_n > 0:
                gn = gam + t * step[:2]
                lln, g2, H2 = _tobit_terms(gn, th_n, X, y, st, sp)
                if lln >= ll - 1e-12 * abs(ll):
                    break
            t *= 0.5
            if t < 1e-12:
                raise ValueError("%s: the likelihood maximisation stalled" % op)
        gam, th, ll, g, H = gn, th_n, lln, g2, H2
        if float(np.max(np.abs(t * step) / np.maximum(1.0, np.abs(np.r_[gam, th])))) < 1e-11:
            break
    else:
        raise ValueError("%s: Newton iteration did not converge in 200 steps" % op)

    sigma = 1.0 / th
    beta = gam * sigma
    try:
        cov_gt = np.linalg.inv(-H)
    except np.linalg.LinAlgError as exc:
        raise ValueError("%s: the observed information is singular" % op) from exc
    # (γ0, γ1, θ) -> (β0, β1, σ): β = γ/θ, σ = 1/θ
    J = np.array([[sigma, 0.0, -gam[0] * sigma ** 2],
                  [0.0, sigma, -gam[1] * sigma ** 2],
                  [0.0, 0.0, -sigma ** 2]])
    cov = J @ cov_gt @ J.T
    cov = 0.5 * (cov + cov.T)
    if not (np.isfinite(cov).all() and np.all(np.diag(cov) > 0)):
        raise ValueError("%s: the parameter covariance is not positive — the data do not "
                         "identify the model" % op)
    return {
        "beta0": float(beta[0]), "beta1": float(beta[1]), "sigma": float(sigma),
        "cov": cov, "param_names": np.array(["beta0", "beta1", "sigma"], dtype=object),
        "n": int(a.size), "n_left": int((st == -1).sum()), "n_right": int((st == 1).sum()),
        "n_censored": int((st != 0).sum()), "loglik": float(ll), "iterations": int(it),
        "log_size": lsz, "log_response": lrs,
        "censor_low": lo, "censor_high": hi,
        "size_min": float(a.min()), "size_max": float(a.max()),
        "ols_beta0": float(b_all[0]), "ols_beta1": float(b_all[1]), "ols_sigma": ols_sigma,
        "x": x, "y": y, "status": st,
    }


def _check_ahat_fit(fit, op, zl):
    if not isinstance(fit, dict):
        raise ValueError("%s: fit must be the table returned by pod_ahat_fit, got %s"
                         % (op, type(fit).__name__))
    need = ("beta0", "beta1", "sigma", "cov", "log_size", "log_response", "size_min", "size_max")
    miss = [k for k in need if k not in fit]
    if miss:
        raise ValueError("%s: fit lacks %s — pass the table returned by pod_ahat_fit" % (op, miss))
    b0 = _scalar(fit["beta0"], "beta0", op)
    b1 = _scalar(fit["beta1"], "beta1", op)
    s = _scalar(fit["sigma"], "sigma", op)
    cov = np.asarray(fit["cov"], dtype=np.float64)
    if cov.shape != (3, 3) or not np.isfinite(cov).all():
        raise ValueError("%s: fit['cov'] must be a finite 3x3 matrix" % op)
    if s <= 0:
        raise ValueError("%s: sigma must be > 0, got %g" % (op, s))
    if b1 <= 0:
        raise ValueError("%s: the slope beta1 = %g is not positive — the response does not grow "
                         "with size, so there is no detection curve (POD would fall with size "
                         "or be flat)" % (op, b1))
    _slope_is_significant(b1, cov[1, 1], zl, op)
    return b0, b1, s, cov


def _slope_is_significant(b1, var_b1, zl, op):
    """β1 が自分の標準誤差の ``z_level`` 倍を超えていなければ拒む。

    ★正の傾きでも、誤差の範囲で 0 と区別できなければ「応答が大きさとともに増える」
    とは言えない。その β1 で ``μ = (y_dec − β0)/β1`` を割ると a50 が 10^12 µm のような
    **もっともらしくない数**になり、それでも数としては返ってしまう(PoC の暗視野照明で
    実際に出た: β1 = 0.035 ± 0.033 から a90/95 = 7e46 µm)。数を返さず理由を返す。
    """
    se = math.sqrt(max(var_b1, 0.0))
    if not b1 > zl * se:
        raise ValueError("%s: the slope beta1 = %.4g is not distinguishable from 0 (standard "
                         "error %.3g, beta1/se = %.2f <= %.3f) — the data do not show the response "
                         "growing with size, so there is no detection curve to report"
                         % (op, b1, se, b1 / se if se > 0 else float("inf"), zl))


def _pod_params_from_ahat(b0, b1, s, cov, y_dec):
    """(β0, β1, σ) と y_dec から (μ, σ_pod) とその 2x2 共分散(デルタ法、1823A G.3.4.3)。"""
    mu = (y_dec - b0) / b1
    sp = s / b1
    J = np.array([[-1.0 / b1, -mu / b1, 0.0],
                  [0.0, -sp / b1, 1.0 / b1]])
    return mu, sp, J @ cov @ J.T


def _y_dec(a_dec, log_response, op):
    v = _scalar(a_dec, "a_dec", op)
    if log_response:
        if v <= 0:
            raise ValueError("%s: a_dec must be > 0 when the response is on a log scale" % op)
        return math.log(v)
    return v


def pod_from_ahat(fit, a_dec, level=0.95, n_grid=200, a=None):
    """â vs a の回帰と判定閾値 ``a_dec`` から POD(a) 曲線と a50 / a90 / a90/95(``table``)。

    判定は ``â > a_dec`` で「検出」。回帰 ``y = β0 + β1 x + ε`` のもとで
    ``POD(x) = Φ((x − μ)/σ_pod)``、``μ = (y_dec − β0)/β1``、``σ_pod = σ/β1``
    (MIL-HDBK-1823A G.3.4.3。``y_dec`` は ``a_dec`` を回帰の y 座標へ写したもの)。
    ``a50 = μ``、``a90 = μ + z_0.9 σ_pod``(``z_0.9 = 1.281552``)を元の単位へ戻す。

    a90/95 はデルタ法: ``(β0, β1, σ)`` の共分散をヤコビアン
    ``∂(μ, σ_pod)/∂(β0, β1, σ)`` で写し、``x90 + z_level · sqrt(vμ + z_0.9² vσ + 2 z_0.9 c)``。
    ``level`` は片側の信頼水準(既定 0.95 → ``z = 1.644854``)。

    曲線の下限 ``pod_lower`` は「各 POD 水準 p の大きさ a_p の上限」をつないだ線
    (水平方向のデルタ法)。だから下限が 0.9 を横切る大きさは a90/95 と**一致する**。
    ``bound_monotone`` が False のとき(``σ_pod`` が自分の標準誤差の z 倍に届かない =
    データが少なすぎる)下限曲線は 1 価にならず、読まないこと。

    ★``a90_95_beyond_data`` が True のとき、a90/95 は**試した最大の大きさより先**にある
    —— 回帰の直線を試験の外へ延ばした外挿で、1823A が「データの外で POD を語るな」と
    いう領域。数は返すが、その数で合否を決めてはいけないことを旗で同伴させる
    (PoC の暗視野照明: 試した最大 300 µm に対し a90/95 = 5,952 µm)。

    *a* を渡すとその大きさで曲線を評価する。省略時は当てに使った大きさの範囲を
    少し広げた ``n_grid`` 点(対数座標なら等比)。

    空の入力(``fit`` が空の dict)は ValueError。
    拒否(``ValueError``): ``pod_ahat_fit`` の表でない、``β1 <= 0``(応答が大きさとともに
    増えない = 検出曲線が無い)、``β1`` が自分の標準誤差の ``z_level`` 倍以下(増えると
    言えない —— その傾きで割った a50 は 10^12 µm のような数になる)、``a_dec`` が
    非有限(対数座標で 0 以下)、``level`` が (0.5, 1) の外。
    """
    op = "pod_from_ahat"
    lv = _level(level, op)
    st = _stats()
    zl = float(st.norm.ppf(lv))
    b0, b1, s, cov = _check_ahat_fit(fit, op, zl)
    lsz = bool(fit["log_size"])
    yd = _y_dec(a_dec, bool(fit["log_response"]), op)
    ng = _count(n_grid, "n_grid", 2, 100_000, op)
    z90 = float(st.norm.ppf(0.9))
    mu, sp, cpod = _pod_params_from_ahat(b0, b1, s, cov, yd)
    x90, x9095, se90 = _quantile_upper(mu, sp, cpod, z90, zl)
    if a is None:
        grid = _size_grid(float(fit["size_min"]), float(fit["size_max"]), lsz, ng)
    else:
        grid = _real(a, "a", op)
    xg = _to_x(grid, lsz, op, what="a")
    pod = st.norm.cdf((xg - mu) / sp)
    qlo = _lower_curve(mu, sp, cpod, zl, xg, -8.0, 8.0)
    return {
        "mu": float(mu), "sigma_pod": float(sp), "cov_pod": cpod,
        "a50": float(_from_x(mu, lsz)), "a90": float(_from_x(x90, lsz)),
        "a90_95": float(_from_x(x9095, lsz)), "se_x90": float(se90),
        "a_dec": float(a_dec), "y_dec": float(yd), "level": lv,
        "log_size": lsz, "bound_monotone": _bound_is_monotone(sp, cpod, zl),
        "a90_95_beyond_data": bool(_from_x(x9095, lsz) > float(fit["size_max"])),
        "a": grid, "pod": pod, "pod_lower": st.norm.cdf(qlo),
    }


# =========================================================================== #
# 2. hit / miss — 2 値の一般化線形モデル
# =========================================================================== #
def _glm_terms(eta, y, link, sp):
    """対数尤度と、η についての 1 階・2 階微分(観測、要素ごと)。

    logit:   dℓ/dη = y − F,               d² = −F(1−F)
    probit:  dℓ/dη = yλ(η) − (1−y)λ(−η), d² = −yλ(η)(η+λ(η)) − (1−y)λ(−η)(λ(−η)−η)
    cloglog: u = e^η、r = u/(e^u − 1):  y=1: d = r, d² = r(1 − u − r) / y=0: d = d² = −u
    (λ = φ/Φ。cloglog の y=1 の形は u → 0 でも大でも桁落ちしない)。
    どのリンクも F と 1−F が対数凹なので対数尤度は β について凹。
    """
    if link == "logit":
        F = sp.expit(eta)
        ll = float(np.sum(y * eta - np.logaddexp(0.0, eta)))
        return ll, y - F, -F * (1.0 - F)
    if link == "probit":
        l1 = sp.log_ndtr(eta)
        l0 = sp.log_ndtr(-eta)
        c = -0.5 * eta * eta - 0.5 * math.log(2.0 * math.pi)
        lam1 = np.exp(c - l1)
        lam0 = np.exp(c - l0)
        ll = float(np.sum(y * l1 + (1.0 - y) * l0))
        d1 = y * lam1 - (1.0 - y) * lam0
        d2 = -y * lam1 * (eta + lam1) - (1.0 - y) * lam0 * (lam0 - eta)
        return ll, d1, d2
    # cloglog
    u = np.exp(np.minimum(eta, 700.0))
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        em = np.expm1(np.minimum(u, 700.0))
        r = np.where(u > 700.0, 0.0, np.where(u < 1e-300, 1.0, u / np.where(em == 0, 1.0, em)))
        lF = np.log(-np.expm1(-u))
    ll = float(np.sum(np.where(y > 0, lF, -u)))
    d1 = np.where(y > 0, r, -u)
    d2 = np.where(y > 0, r * (1.0 - u - r), -u)
    return ll, d1, d2


def _link_ppf(p, link, sp):
    if link == "logit":
        return float(sp.logit(p))
    if link == "probit":
        return float(sp.ndtri(p))
    return float(math.log(-math.log1p(-p)))


def _link_cdf(eta, link, sp):
    if link == "logit":
        return sp.expit(eta)
    if link == "probit":
        return sp.ndtr(eta)
    return -np.expm1(-np.exp(np.minimum(eta, 700.0)))


def _glm_newton(X, y, link, sp, beta0, offset=None, op="pod_hitmiss_fit", maxit=200):
    """ニュートン法(= 観測情報の反復重み付き最小二乗)。step halving で尤度を単調に上げる。"""
    off = 0.0 if offset is None else offset
    beta = np.array(beta0, dtype=np.float64)
    ll, d1, d2 = _glm_terms(X @ beta + off, y, link, sp)
    for it in range(1, maxit + 1):
        g = X.T @ d1
        H = (X.T * d2) @ X
        try:
            step = np.linalg.solve(-H, g)
        except np.linalg.LinAlgError as exc:
            raise ValueError("%s: the information matrix is singular" % op) from exc
        t = 1.0
        while True:
            bn = beta + t * step
            lln, e1, e2 = _glm_terms(X @ bn + off, y, link, sp)
            if np.isfinite(lln) and lln >= ll - 1e-12 * abs(ll):
                break
            t *= 0.5
            if t < 1e-12:
                raise ValueError("%s: the likelihood maximisation stalled" % op)
        beta, ll, d1, d2 = bn, lln, e1, e2
        if float(np.max(np.abs(t * step) / np.maximum(1.0, np.abs(beta)))) < 1e-11:
            return beta, ll, d1, d2, it
    raise ValueError("%s: Newton iteration did not converge in %d steps" % (op, maxit))


def pod_hitmiss_fit(table, size="a", hit="hit", link="logit", log_size=False, level=0.95,
                    n_grid=200):
    """見つけた/見落としたの 2 値データから POD(a) を一般化線形モデルで当てる(``table``)。

    ``POD(a) = F(β0 + β1 x)``、``x = a`` または ``ln a``、``F`` はリンクの逆
    (``logit`` / ``probit`` / ``cloglog``、MIL-HDBK-1823A G.4.1.1)。最尤推定は
    ニュートン法(logit では反復重み付き最小二乗と同じ)、共分散は観測情報の逆。

    ``a_p = (F⁻¹(p) − β0)/β1`` で a50 / a90 を出す(logit なら ``a50 = −β0/β1``)。
    a90/95 は 2 通り返す:

      * ``a90_95``(Wald / デルタ法): ``x90 + z_level · se(x90)``、
        ``var(x90) = [vβ0 + 2 x90 c + x90² vβ1]/β1²``。
      * ``a90_95_lr``(尤度比、G.4.2.2): x90 を固定して β1 について最大化した
        **プロファイル対数尤度** ``ℓp(x90)`` が ``ℓmax − χ²₁(2·level − 1)/2`` まで落ちる
        x90(片側なので 95 % なら χ² の 90 % 点 2.7055)。1823A のソフトは
        (μ, σ) の 2 次元の信頼域の包絡線を描くが、ここで返すのは a90 という
        1 つの量に対する境界なので自由度 1 のプロファイルを使う —— **定義が違う**ことを
        明示しておく。尤度が十分に落ちない(データが少なく上限が無い)ときは
        ``None`` と ``lr_status = "unbounded"``。

    曲線 ``pod`` / ``pod_lower``(Wald、水平方向)は ``n_grid`` 点。``a90_95_beyond_data``
    は Wald の a90/95 が試した最大の大きさを超えた(外挿である)ことの旗。

    空の入力(``table`` が 0 行、または空の dict)は ValueError。
    拒否(``ValueError``): 空の表・列の欠け、``hit`` が 0/1 以外、全部検出か全部
    見落とし(曲線が立たない)、**完全分離**(ある大きさを境に全部見落とし/全部検出 =
    最尤推定が無限大へ発散する)、``β1 <= 0`` または標準誤差の ``z_level`` 倍以下、未知の ``link``。
    """
    op = "pod_hitmiss_fit"
    if link not in _LINKS:
        raise ValueError("%s: link must be one of %s, got %r" % (op, _LINKS, link))
    lsz = _flag(log_size, "log_size", op)
    lv = _level(level, op)
    ng = _count(n_grid, "n_grid", 2, 100_000, op)
    c = _cols(table, op, (size, hit))
    a = _real(c[size], size, op)
    h = np.asarray(c[hit])
    if h.dtype.kind == "b":
        yv = h.astype(np.float64)
    elif h.dtype.kind in "iuf":
        yv = h.astype(np.float64)
        if not np.isfinite(yv).all() or not np.isin(yv, (0.0, 1.0)).all():
            raise ValueError("%s: column %r must hold only 0 / 1 (or booleans)" % (op, hit))
    else:
        raise ValueError("%s: column %r has dtype %r — expected 0/1 or booleans"
                         % (op, hit, str(h.dtype)))
    k = int(yv.sum())
    if k == 0 or k == yv.size:
        raise ValueError("%s: all %d targets were %s — a POD curve needs both hits and misses"
                         % (op, yv.size, "missed" if k == 0 else "found"))
    x = _to_x(a, lsz, op)
    if np.ptp(x) <= 0:
        raise ValueError("%s: every target has the same size — the slope is not estimable" % op)
    if x[yv == 0].max() <= x[yv == 1].min():
        raise ValueError("%s: complete separation — every miss is at or below every hit "
                         "(sizes <= %g missed, >= %g found); the maximum-likelihood slope is "
                         "infinite, so there is no a90/95 to report from these data"
                         % (op, float(_from_x(x[yv == 0].max(), lsz)),
                            float(_from_x(x[yv == 1].min(), lsz))))
    if x[yv == 1].max() <= x[yv == 0].min():
        raise ValueError("%s: complete separation in the wrong direction — every hit is at or "
                         "below every miss; POD falls with size" % op)

    sp = _special()
    st = _stats()
    X = np.column_stack([np.ones_like(x), x])
    beta, ll, d1, d2, it = _glm_newton(X, yv, link, sp, [0.0, 0.0], op=op)
    b0, b1 = float(beta[0]), float(beta[1])
    if b1 <= 0:
        raise ValueError("%s: the fitted slope beta1 = %g is not positive — POD does not grow "
                         "with size" % (op, b1))
    H = (X.T * d2) @ X
    try:
        cov = np.linalg.inv(-H)
    except np.linalg.LinAlgError as exc:
        raise ValueError("%s: the observed information is singular" % op) from exc
    cov = 0.5 * (cov + cov.T)
    if not (np.isfinite(cov).all() and np.all(np.diag(cov) > 0)):
        raise ValueError("%s: the parameter covariance is not positive" % op)

    zl = float(st.norm.ppf(lv))
    _slope_is_significant(b1, cov[1, 1], zl, op)
    # POD(x) = F((x − μ)/σ) の形に直す: μ = −β0/β1、σ = 1/β1
    mu, sg = -b0 / b1, 1.0 / b1
    J = np.array([[-1.0 / b1, b0 / b1 ** 2], [0.0, -1.0 / b1 ** 2]])
    cpod = J @ cov @ J.T
    q50, q90 = _link_ppf(0.5, link, sp), _link_ppf(0.9, link, sp)
    x50 = mu + q50 * sg
    x90, x9095, se90 = _quantile_upper(mu, sg, cpod, q90, zl)

    # 尤度比(プロファイル)の上限
    crit = float(st.chi2.ppf(2.0 * lv - 1.0, 1))

    def prof_dev(t):
        d = (x - t)[:, None]
        try:
            bb, lp, _, _, _ = _glm_newton(d, yv, link, sp, [b1], offset=q90, op=op)
        except ValueError:
            return math.inf
        if bb[0] <= 0:
            return math.inf
        return 2.0 * (ll - lp)

    lr, lr_status = None, "ok"
    stepx = max(float(se90), 1e-6 * max(1.0, abs(float(x90))))
    lo_t, hi_t = float(x90), None
    for kk in range(0, 14):
        t = float(x90) + stepx * (2.0 ** kk)
        if prof_dev(t) > crit:
            hi_t = t
            break
        lo_t = t
    if hi_t is None:
        lr_status = "unbounded"
    else:
        # 二分法(プロファイルが発散する側は inf を返すので、補間する根探しは使わない)
        for _ in range(80):
            mid = 0.5 * (lo_t + hi_t)
            if prof_dev(mid) > crit:
                hi_t = mid
            else:
                lo_t = mid
            if hi_t - lo_t <= 1e-13 * max(1.0, abs(mid)):
                break
        lr = float(_from_x(0.5 * (lo_t + hi_t), lsz))

    grid = _size_grid(float(a.min()), float(a.max()), lsz, ng)
    xg = _to_x(grid, lsz, op, what="a")
    pod = _link_cdf(b0 + b1 * xg, link, sp)
    qmin, qmax = _link_ppf(1e-6, link, sp), _link_ppf(1.0 - 1e-6, link, sp)
    qlo = _lower_curve(mu, sg, cpod, zl, xg, qmin, qmax)
    return {
        "beta0": b0, "beta1": b1, "cov": cov,
        "param_names": np.array(["beta0", "beta1"], dtype=object),
        "link": link, "log_size": lsz, "level": lv,
        "n": int(yv.size), "n_hit": k, "loglik": float(ll), "iterations": int(it),
        "a50": float(_from_x(x50, lsz)), "a90": float(_from_x(x90, lsz)),
        "a90_95": float(_from_x(x9095, lsz)), "se_x90": float(se90),
        "a90_95_lr": lr, "lr_status": lr_status, "lr_chi2": crit,
        "bound_monotone": _bound_is_monotone(sg, cpod, zl),
        "a90_95_beyond_data": bool(_from_x(x9095, lsz) > float(a.max())),
        "a": grid, "pod": pod, "pod_lower": _link_cdf(qlo, link, sp),
    }


# =========================================================================== #
# 3. 誤検出(雑音)
# =========================================================================== #
_PFP_CONF = (0.5, 0.9, 0.95)


def _pfp_bounds(k, n):
    """k 回の誤検出 / n 機会の片側上限(Clopper–Pearson)。k = n なら 1。"""
    return tuple(proportion_interval(k, n, confidence=cf, sides="upper")["upper"]
                 for cf in _PFP_CONF)


def _noise_stats(noise, log_response, op):
    v = _real(noise, "noise", op)
    if v.size < 2:
        raise ValueError("%s: need at least 2 noise measurements, got %d" % (op, v.size))
    yv = _to_x(v, log_response, op, what="noise response")
    sd = float(np.std(yv, ddof=1))
    if not sd > 0:
        raise ValueError("%s: every noise response is the same (%g) — a normal noise model "
                         "has no spread; measure more unflawed sites" % (op, float(v[0])))
    return v, yv, float(np.mean(yv)), sd


def pod_false_call(noise, a_dec, log_response=False):
    """無欠陥部位の応答 ``noise`` と判定閾値 ``a_dec`` から誤検出確率(``table``)。

    判定は ``â > a_dec`` で「検出」(POD と同じ規則)。3 通りで返す:

      * ``pfp_empirical = k/n`` —— 素の比率。
      * ``pfp50`` / ``pfp90`` / ``pfp95`` —— k 回 / n 機会の**二項の片側上限**
        (Clopper–Pearson、``Beta⁻¹(c; k+1, n−k)``)。MIL-HDBK-1823A G.4.6 の
        表 G-I と同じ定義で、0 回でも 0 にはならない(150 機会で 0 回なら
        PFP50 = 0.0046)。1823A は報告とリスク計算に PFP50 を使えと言う。
      * ``pfp_normal`` —— 雑音を正規と見た ``1 − Φ((y_dec − m)/s)``(G.3.5.3、
        ``log_response`` なら対数座標で)。裾の外挿なので、分布の仮定に敏感
        (1823A G.3.4.2 が警告するとおり)。

    空の入力(``noise`` が 0 要素)は ValueError。
    拒否(``ValueError``): 空・非有限・2 点未満、雑音がすべて同じ値(正規の幅が 0)、
    ``a_dec`` が非有限(対数座標で 0 以下)。
    """
    op = "pod_false_call"
    lrs = _flag(log_response, "log_response", op)
    v, yv, m, s = _noise_stats(noise, lrs, op)
    yd = _y_dec(a_dec, lrs, op)
    k = int((v > float(a_dec)).sum())
    n = int(v.size)
    p50, p90, p95 = _pfp_bounds(k, n)
    st = _stats()
    return {
        "n": n, "n_false": k, "pfp_empirical": k / n,
        "pfp50": p50, "pfp90": p90, "pfp95": p95,
        "noise_mean": m, "noise_sd": s,
        "pfp_normal": float(st.norm.sf((yd - m) / s)),
        "a_dec": float(a_dec), "log_response": lrs,
    }


# =========================================================================== #
# 4. 判定閾値の取引表
# =========================================================================== #
def pod_decision_tradeoff(fit, noise, a_dec_grid=None, n_grid=25, level=0.95):
    """判定閾値 ``a_dec`` を振ったときの (a50, a90, a90/95, 誤検出確率) の取引表(``table``)。

    MIL-HDBK-1823A G.3.6.2.4.1(図 G-28)の数表版。閾値を上げれば誤検出は減り、
    同じ回帰から出る a90/95 は大きくなる —— 「どこに閾値を置くか」は統計ではなく
    運用の判断で、この表はその判断の材料を並べるだけ(最適点は選ばない)。

    *fit* は ``pod_ahat_fit`` の表、*noise* は無欠陥部位の応答(元の â の単位、
    座標は *fit* の ``log_response`` に従う)。*a_dec_grid* を省略すると、雑音の
    中央値から「雑音の平均 + 6 標準偏差」までを ``n_grid`` 点(対数座標なら等比)。
    各行は ``pod_from_ahat`` と ``pod_false_call`` を同じ閾値で呼んだものと一致する。

    返り: 列 ``a_dec`` ``a50`` ``a90`` ``a90_95`` ``pfp_normal`` ``pfp_empirical``
    ``pfp50`` ``pfp95``(すべて長さ ``n_grid`` か ``len(a_dec_grid)``)。

    空の入力(``fit`` が空の dict)は ValueError。
    拒否(``ValueError``): ``pod_ahat_fit`` の表でない・``β1`` が 0 と区別できない、雑音が空・定数・
    非有限、閾値が非有限(対数座標で 0 以下)。
    """
    op = "pod_decision_tradeoff"
    lv = _level(level, op)
    b0, b1, s, cov = _check_ahat_fit(fit, op, float(_stats().norm.ppf(lv)))
    lsz, lrs = bool(fit["log_size"]), bool(fit["log_response"])
    v, yv, m, sd = _noise_stats(noise, lrs, op)
    if a_dec_grid is None:
        ng = _count(n_grid, "n_grid", 2, 10_000, op)
        ylo, yhi = float(np.median(yv)), m + 6.0 * sd
        ys = np.linspace(ylo, yhi, ng)
        grid = np.exp(ys) if lrs else ys
    else:
        grid = _real(a_dec_grid, "a_dec_grid", op)
        if lrs and (grid <= 0).any():
            raise ValueError("%s: a_dec_grid must be > 0 on a log response scale" % op)
        ys = np.log(grid) if lrs else grid
    st = _stats()
    zl = float(st.norm.ppf(lv))
    z90 = float(st.norm.ppf(0.9))
    a50 = np.empty(grid.size)
    a90 = np.empty(grid.size)
    a9095 = np.empty(grid.size)
    pe = np.empty(grid.size)
    p50 = np.empty(grid.size)
    p95 = np.empty(grid.size)
    for i, (ad, yd) in enumerate(zip(grid, ys)):
        mu, spd, cp = _pod_params_from_ahat(b0, b1, s, cov, float(yd))
        x90, x9095, _ = _quantile_upper(mu, spd, cp, z90, zl)
        a50[i] = _from_x(mu, lsz)
        a90[i] = _from_x(x90, lsz)
        a9095[i] = _from_x(x9095, lsz)
        k = int((v > ad).sum())
        pe[i] = k / v.size
        p50[i], _, p95[i] = _pfp_bounds(k, v.size)
    return {
        "a_dec": grid, "a50": a50, "a90": a90, "a90_95": a9095,
        "pfp_normal": st.norm.sf((ys - m) / sd), "pfp_empirical": pe,
        "pfp50": p50, "pfp95": p95, "level": lv,
    }


# --------------------------------------------------------------------------- #
def _registry():
    """このモジュールが publish する op(名前 -> 関数)。手書きせずモジュールから作る。"""
    public = {"proportion_interval", "trials_for_all_success"}
    return {name: obj for name, obj in sorted(globals().items())
            if (name.startswith("pod_") or name in public) and callable(obj)}


POD = _registry()

__all__ = ["pod_ahat_fit", "pod_from_ahat", "pod_hitmiss_fit", "pod_false_call",
           "pod_decision_tradeoff", "proportion_interval", "trials_for_all_success"]
