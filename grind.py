# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""乳鉢の粉砕を測る —— 粒度分布の D10/D50/D90、粉砕則の当てはめ、独立試行のばらつき、AE の帯域電力(規則だけ、学習なし、2026-10-05)。

物理シミュ × Fullseye 系列(granular / scoop に続く粉体の 3 本目)。題材はロボットの乳鉢粉砕を音響放射(AE)で見張る研究
(公開データ: Zenodo 概念 DOI 10.5281/zenodo.18064323、CC BY 4.0。解析コードは MIT)。**外から来る真値はレーザー回折の
粒度分布そのもの**(NaCl / クエン酸 / グルタミン酸ナトリウム × 独立 3 回 × 粉砕 3〜25 min の 7 時点、+ 粉砕前・60 min・手作業)。
データは repo に入れない(PoC は環境変数で場所を受け取る)。

一次情報で確かめた定義と式(読んだものだけ):

- **D50 の定義**: 装置の CSV は ``SizeClasses`` の列が **区間の端**で、``VolumeDensity(%)`` の i 行目は端 i と i+1 の間の体積
  (最後の行は 0)。ヘッダの ``Dx (50)`` は「端での累積を **log(径)** で線形補間」した値と全 90 ファイルで一致した
  (相対差 1e-14 級、:func:`particle_size_dx` の ``convention="log_edges"``)。公開の解析コードには定義が 2 つある:
  材料の比較の段は ``Dx (50)`` の行を読み、AE の模型の学習の段は ``np.interp(total/2, cumsum(v), sizes)``(累積を区間の
  **下の端**に置く)で、こちらは 1 区間分(比 1.136)小さく **−11.9 %**(``convention="lower_cumsum"`` で再現)。
- **粉砕則**(Reddy, "Energy requirements in size reduction of solids", 国立冶金研究所の紀要 pp. 67–76 の式 (1)・(5)〜(7)):
  一般式 ``dE = −C dx / x^n``(Walker, Lewis, McAdams, Gilliland)、``n = 2`` Rittinger ``E = C (1/x₂ − 1/x₁)``、``n = 1`` Kick
  ``E = C ln(x₁/x₂)``、``n = 1.5`` Bond ``E = 2C (1/√x₂ − 1/√x₁)``。Bond の作業指数の形 ``W = 10 Wi (1/√P80 − 1/√F80)``
  [kWh/t、µm] は ``C = 5 Wi`` と同じ式(Bond 1952 の原文 Trans. AIME 193, 484–494 は **未読**、Wi の値は引用しない)。
- **一次の破砕速度**(Deniz, Eur. J. Mineral Process. Environ. Prot. 4 (2004) 162–167 の式 (1)〜(3)、出典 Austin 1972 /
  Austin ほか 1984): 最上位の粒度区間の ``dw₁/dt = −S₁ w₁``、``w₁(t) = w₁(0) exp(−S₁ t)``、``Sᵢ = a_T Xᵢ^α``。
  Austin の原著(1972、1984 の成書)は **未読**。式 (1) が厳密なのは **最上位の区間だけ**(上から生まれ込む粒が無い)なので、
  任意の径より上の累積体積に当てた速度は「見かけの」速度として返す(``apparent=True``)。

時間とエネルギーの約束: 粉砕則はエネルギーの式だが、データにエネルギーは無い。**一定の力と速さで擦る ⇒ 投入エネルギー ∝ 正味の
粉砕時間**と仮定し、時間を ``E/C`` の代わりに使う(:func:`comminution_law_fit` の ``k`` は単位時間あたりの ``E/C``)。
この仮定は当てはめの良し悪しで検証できない(どの則にも同じだけ効く)ので、比較は則どうしの相対だけに使う。

座標と単位: 径は µm(正の有限値)、体積は % でも割合でもよい(内部で総和で割る)。画像は ``(H, W)`` の被覆率 [0, 1]、
``pitch`` は 1 画素の辺 [µm]。失敗はすべて ``ValueError``(綴り違い・空・負・非有限・区間に割り当てられない体積)。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "INSTRUMENT_RATIO", "LAWS",
    "particle_size_read", "particle_size_dx", "particle_size_oversize", "particle_size_synth",
    "comminution_energy", "comminution_law_fit", "breakage_first_order_fit",
    "replicate_compare",
    "ae_read_csv", "ae_band_power", "ae_size_correspondence",
    "particle_image_synth", "particle_image_d50",
]

#: 公開データの装置の区間の比(隣り合う端の比、74 端で 0.09953〜1109.43 µm)。実測 1.13616。
INSTRUMENT_RATIO = 1.1361640
_INSTRUMENT_FIRST = 0.09953
_INSTRUMENT_N = 74

#: 粉砕則の名前 → 一般式の指数 n(Reddy の式 (1) の特別な場合)。"walker" は n を当てはめる。
LAWS = {"kick": 1.0, "bond": 1.5, "rittinger": 2.0}
_CONVENTIONS = ("log_edges", "linear_edges", "lower_cumsum")


# ----------------------------------------------------------------------------------------------
# 引数の検査(fail-closed)
# ----------------------------------------------------------------------------------------------
def _pos(v, name, allow_inf=False):
    if isinstance(v, bool):
        raise ValueError("%s must be a number > 0, got %r" % (name, v))
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s must be a number > 0, got %r" % (name, v))
    if math.isnan(f) or f <= 0.0 or (math.isinf(f) and not allow_inf):
        raise ValueError("%s must be a finite number > 0, got %r" % (name, v))
    return f


def _choice(v, name, allowed):
    if not isinstance(v, str) or v not in allowed:
        raise ValueError("%s must be one of %r, got %r" % (name, tuple(allowed), v))
    return v


def _vec(a, name, min_len=1, positive=False, nonneg=False):
    try:
        x = np.asarray(a, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("%s must be a numeric 1-D array" % name)
    if x.ndim != 1 or x.size < min_len:
        raise ValueError("%s must be 1-D with at least %d values, got shape %r" % (name, min_len, np.shape(a)))
    if not np.all(np.isfinite(x)):
        raise ValueError("%s contains nan/inf" % name)
    if positive and np.any(x <= 0):
        raise ValueError("%s must be > 0 everywhere" % name)
    if nonneg and np.any(x < 0):
        raise ValueError("%s must be >= 0 everywhere" % name)
    return x


def _psd(psd, name="psd"):
    """粒度分布の表(dict: ``edges``・``volume``)を検査して (edges, 割合) を返す。"""
    if not isinstance(psd, dict) or "edges" not in psd or "volume" not in psd:
        raise ValueError("%s must be a dict with 'edges' and 'volume' (see particle_size_read)" % name)
    e = _vec(psd["edges"], name + "['edges']", min_len=3, positive=True)
    v = _vec(psd["volume"], name + "['volume']", min_len=3, nonneg=True)
    if e.size != v.size:
        raise ValueError("%s: edges and volume must have the same length (%d vs %d)" % (name, e.size, v.size))
    if np.any(np.diff(e) <= 0):
        raise ValueError("%s['edges'] must be strictly increasing" % name)
    if v[-1] > 0:
        raise ValueError("%s: the last volume row must be 0 (row i is the bin between edge i and i+1; "
                         "a positive last row has no upper edge)" % name)
    tot = float(v.sum())
    if tot <= 0:
        raise ValueError("%s: total volume is zero" % name)
    return e, v / tot


def _cum_at_edges(frac):
    """端 i での累積(端 0 で 0、最後の端で 1)。"""
    return np.concatenate([[0.0], np.cumsum(frac[:-1])])


# ----------------------------------------------------------------------------------------------
# 粒度分布: 読み込み・Dx・篩上・合成
# ----------------------------------------------------------------------------------------------
def particle_size_read(path) -> dict:
    """レーザー回折の粒度分布 CSV(ヘッダの ``key,value`` 行 + ``SizeClasses`` で始まる表)を読む。

    返り: ``edges`` [µm] (表の 1 列目 = 区間の端)、``volume``(2 列目 = 端 i と i+1 の間の体積 %)、``header``
    (文字列の dict)、``dx50_reported``(ヘッダの ``Dx (50)``、無ければ None)、``total_percent``(体積の総和)、
    ``n_rows``。読み込んだパスは返り値に残さない。表が無い・数値でない・最後の行が 0 でない → ``ValueError``。
    """
    try:
        text = open(path, "r", encoding="utf-8", errors="replace").read()
    except OSError as exc:
        raise ValueError("particle_size_read: cannot read the file (%s)" % type(exc).__name__)
    header, edges, vol, in_table = {}, [], [], False
    for line in text.splitlines():
        if not in_table:
            if line.strip().startswith("SizeClasses"):
                in_table = True
                continue
            parts = line.split(",")
            if parts and parts[0].strip():
                header[parts[0].strip()] = parts[1].strip() if len(parts) > 1 else ""
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 2 or not parts[0]:
            continue
        try:
            edges.append(float(parts[0]))
            vol.append(float(parts[1]))
        except ValueError:
            raise ValueError("particle_size_read: non-numeric row in the size table: %r" % line[:60])
    if not in_table or len(edges) < 3:
        raise ValueError("particle_size_read: no 'SizeClasses' table with at least 3 rows")
    out = {"edges": np.asarray(edges, float), "volume": np.asarray(vol, float)}
    _psd(out, "particle_size_read")
    dx = header.get("Dx (50)")
    try:
        dx50 = float(dx) if dx not in (None, "") else None
    except ValueError:
        dx50 = None
    out.update({"header": header, "dx50_reported": dx50, "total_percent": float(np.sum(vol)), "n_rows": len(edges)})
    return out


def particle_size_dx(psd: dict, q: float = 50.0, convention: str = "log_edges") -> float:
    """体積累積 ``q`` % の径 Dq [µm] (D10 / D50 / D90 は ``q`` = 10 / 50 / 90)。

    ``convention``:

    - ``"log_edges"``(既定、装置のヘッダの ``Dx (50)`` と一致): 端 i の累積に対して log(径) を線形補間。
    - ``"linear_edges"``: 端の累積に対して径そのものを線形補間(区間内の体積が径について一様、の仮定)。
    - ``"lower_cumsum"``: 公開の解析コードの学習の段の定義 ``np.interp(q/100, cumsum(v), edges)``(累積を区間の下の端に置く)。
      1 区間分小さく出る(この装置で −11.9 %)。比較のために再現しているだけで、推奨しない。
    """
    e, f = _psd(psd)
    qq = float(q) if not isinstance(q, bool) else float("nan")
    if not (0.0 < qq < 100.0):
        raise ValueError("particle_size_dx: q must satisfy 0 < q < 100, got %r" % (q,))
    _choice(convention, "convention", _CONVENTIONS)
    p = qq / 100.0
    if convention == "lower_cumsum":
        return float(np.interp(p, np.cumsum(f), e))
    c = _cum_at_edges(f)
    # 累積が平らな区間(体積 0)で補間が割り切れないよう、狭義単調な部分だけを使う
    keep = np.concatenate([[True], np.diff(c) > 0])
    cc, ee = c[keep], e[keep]
    if convention == "log_edges":
        return float(np.exp(np.interp(p, cc, np.log(ee))))
    return float(np.interp(p, cc, ee))


def particle_size_oversize(psd: dict, x: float) -> float:
    """径 ``x`` [µm] より上の体積の割合(篩上 R(x)、0〜1)。端の累積を log(径) で補間(:func:`particle_size_dx` の既定と同じ約束)。"""
    e, f = _psd(psd)
    xx = _pos(x, "x")
    c = _cum_at_edges(f)
    return float(1.0 - np.interp(math.log(xx), np.log(e), c))


def particle_size_synth(d50: float, sigma_ln: float, edges=None) -> dict:
    """対数正規の **体積** 分布を装置と同じ区間に割り付けた粒度分布(真値つき)。

    体積の累積 ``F(x) = Φ((ln x − ln d50) / σ)``。``edges`` を省くと公開データの装置の 74 端(比 1.13616)。
    返り: ``edges``・``volume``(%)と ``truth``(``d10``・``d50``・``d90`` = ``d50 · exp(±1.28155 σ)``、``sigma_ln``)。
    区間の外にはみ出す体積が 1e-6 を超えると ``ValueError``(端で切ると D10/D90 が黙って動く)。
    """
    m = _pos(d50, "d50")
    s = _pos(sigma_ln, "sigma_ln")
    if edges is None:
        e = _INSTRUMENT_FIRST * INSTRUMENT_RATIO ** np.arange(_INSTRUMENT_N)
    else:
        e = _vec(edges, "edges", min_len=3, positive=True)
        if np.any(np.diff(e) <= 0):
            raise ValueError("edges must be strictly increasing")
    from math import erf
    z = (np.log(e) - math.log(m)) / s
    F = 0.5 * (1.0 + np.array([erf(t / math.sqrt(2.0)) for t in z]))
    if F[0] > 1e-6 or F[-1] < 1.0 - 1e-6:
        raise ValueError("particle_size_synth: the distribution spills outside the edges (F at ends %.2e, %.6f)"
                         % (F[0], F[-1]))
    vol = np.concatenate([np.diff(F), [0.0]]) * 100.0
    zq = 1.2815515655446004
    return {"edges": e, "volume": vol,
            "truth": {"d10": m * math.exp(-zq * s), "d50": m, "d90": m * math.exp(zq * s), "sigma_ln": s}}


# ----------------------------------------------------------------------------------------------
# 粉砕則(閉形式と当てはめ)
# ----------------------------------------------------------------------------------------------
def _law_n(law, n):
    if law == "walker":
        if n is None:
            raise ValueError("law 'walker' needs the exponent n")
        nn = _pos(n, "n")
        return nn
    if n is not None:
        raise ValueError("n is only for law 'walker' (law %r fixes n = %g)" % (law, LAWS[law]))
    return LAWS[law]


def comminution_energy(x_feed: float, x_product: float | None = None, law: str = "bond", C: float = 1.0,
                       n: float | None = None, energy: float | None = None) -> dict:
    """粉砕則の閉形式(Reddy の式 (1)・(5)〜(7))。``x_product`` と ``energy`` の **ちょうど一方** を与える。

    一般式 ``dE = −C dx / x^n`` を積分して ``E = C/(n−1) (x₂^{1−n} − x₁^{1−n})``(n ≠ 1)、``E = C ln(x₁/x₂)``(n = 1)。
    ``law``: ``"kick"``(n = 1)、``"bond"``(n = 1.5、``E = 2C(1/√x₂ − 1/√x₁)``)、``"rittinger"``(n = 2)、``"walker"``(``n`` を渡す)、
    ``"bond_wi"``(``W = 10 Wi (1/√P80 − 1/√F80)``、``C`` を作業指数 Wi [kWh/t] と読み、径は µm、= ``bond`` で ``C = 5 Wi``)。
    ``x_feed`` は n > 1 なら ``inf`` を許す(無限大の供給からの全エネルギー、Reddy の式 (2)〜(4))。
    返り: ``E``・``x_feed``・``x_product``・``law``・``n``・``C``。細かくならない(``x_product ≥ x_feed``)・負のエネルギー → ``ValueError``。
    """
    _choice(law, "law", tuple(LAWS) + ("walker", "bond_wi"))
    CC = _pos(C, "C")
    if law == "bond_wi":
        nn, Ce = _law_n("bond", n), 5.0 * CC
    else:
        nn, Ce = _law_n(law, n), CC
    x1 = _pos(x_feed, "x_feed", allow_inf=nn > 1.0)
    if (x_product is None) == (energy is None):
        raise ValueError("give exactly one of x_product and energy")

    def u(x):            # x^{1-n}(n > 1 なら inf → 0)
        return 0.0 if math.isinf(x) else x ** (1.0 - nn)

    if x_product is not None:
        x2 = _pos(x_product, "x_product")
        if not x2 < x1:
            raise ValueError("x_product (%g) must be smaller than x_feed (%g)" % (x2, x1))
        if abs(nn - 1.0) < 1e-12:
            E = Ce * math.log(x1 / x2)
        else:
            E = Ce / (nn - 1.0) * (u(x2) - u(x1))
    else:
        E = float(energy) if not isinstance(energy, bool) else float("nan")
        if not (math.isfinite(E) and E >= 0.0):
            raise ValueError("energy must be a finite number >= 0, got %r" % (energy,))
        if abs(nn - 1.0) < 1e-12:
            x2 = x1 * math.exp(-E / Ce)
        else:
            val = u(x1) + (nn - 1.0) * E / Ce
            if nn < 1.0 and val <= 0.0:
                raise ValueError("energy exceeds what law n < 1 can absorb (the product size reaches 0)")
            x2 = val ** (1.0 / (1.0 - nn))
    return {"E": float(E), "x_feed": float(x1), "x_product": float(x2), "law": law, "n": float(nn), "C": float(CC)}


def _law_fit_one(t, y_log, n_fixed):
    """ln x(t) を 1 つの則で当てる。n_fixed=None なら n も当てる。返り: params dict と残差。"""
    from scipy.optimize import least_squares
    x = np.exp(y_log)

    def pred(p, n):
        if abs(n - 1.0) < 1e-9:
            return p[0] - np.exp(p[1]) * t                      # ln x = ln x0 − k t
        u0 = p[0] ** 2                                          # u0 = x0^{1−n} ≥ 0(n > 1 なら x0 = inf も許す)
        uu = u0 + (n - 1.0) * np.exp(p[1]) * t
        if n < 1.0:
            uu = np.maximum(uu, 1e-300)
        return np.log(np.maximum(uu, 1e-300)) / (1.0 - n)

    def start(n):
        # 変換した空間で直線を当てて初期値にする
        if abs(n - 1.0) < 1e-9:
            A = np.vstack([np.ones_like(t), -t]).T
            c = np.linalg.lstsq(A, y_log, rcond=None)[0]
            return np.array([c[0], math.log(max(c[1], 1e-9))])
        uu = x ** (1.0 - n)
        A = np.vstack([np.ones_like(t), t]).T
        c = np.linalg.lstsq(A, uu, rcond=None)[0]
        slope = max(c[1] / (n - 1.0), 1e-12)
        return np.array([math.sqrt(max(c[0], 0.0)), math.log(slope)])

    if n_fixed is not None:
        p0 = start(n_fixed)
        r = least_squares(lambda p: pred(p, n_fixed) - y_log, p0, method="lm", xtol=1e-14, ftol=1e-14)
        p, n = r.x, n_fixed
    else:
        best = None
        for n0 in (1.2, 1.5, 2.0, 2.5, 3.0):
            p0 = np.concatenate([start(n0), [n0]])
            p0[1] = float(np.clip(p0[1], -49.0, 49.0))
            r = least_squares(lambda q: pred(q[:2], q[2]) - y_log, p0, bounds=([-np.inf, -50, 1.01], [np.inf, 50, 6.0]),
                              xtol=1e-14, ftol=1e-14)
            if best is None or r.cost < best.cost:
                best = r
        p, n = best.x[:2], float(best.x[2])
    res = pred(p, n) - y_log
    if abs(n - 1.0) < 1e-9:
        x0 = float(math.exp(p[0]))
    else:
        u0 = float(p[0] ** 2)
        u_end = float(np.max(u0 + (n - 1.0) * math.exp(p[1]) * t)) if n > 1.0 else 0.0
        # 供給径の項が終点の値の 1e-9 未満なら「要らない」= x0 = inf(有限の巨大数を x0 として返さない)
        x0 = math.inf if (n > 1.0 and u0 <= 1e-9 * u_end) or u0 < 1e-300 else float(u0 ** (1.0 / (1.0 - n)))
    return {"n": float(n), "x0": x0, "k": float(math.exp(p[1])), "residual_log": res}


def comminution_law_fit(t, d, law: str = "all") -> dict:
    """粒径の時間変化 ``d(t)`` に粉砕則を当てる(エネルギー ∝ ``t`` の仮定、モジュール冒頭)。誤差は **log(径)** で測る。

    ``t``: 正味の粉砕時間(エネルギーの代わり、≥ 0)、``d``: その時点の代表径 [µm] (D50 など)。独立試行は同じ ``t`` に複数並べてよい。
    模型: Kick ``ln x = ln x₀ − k t``、n ≠ 1 の則は ``x^{1−n} = x₀^{1−n} + (n−1) k t``(``k`` = 単位時間あたりの E/C)。
    ``law``: ``"all"``(kick / bond / rittinger / walker を全部)か 1 つの名前。返り: ``fits``(則 → ``n``・``x0``・``k``・
    ``rms_log``・``aic``・``residual_log``)、``best_fixed``(n を固定した 3 則のうち ``rms_log`` 最小)、``n_points``。
    ``x0`` が ``inf`` になるのは「供給径の項が要らない」(n > 1 で x₀^{1−n} → 0)という当てはめの結果で、正直にそう返す。
    点が 3 未満・径が非正 → ``ValueError``。
    """
    tt = _vec(t, "t", min_len=3, nonneg=True)
    dd = _vec(d, "d", min_len=3, positive=True)
    if tt.size != dd.size:
        raise ValueError("t and d must have the same length (%d vs %d)" % (tt.size, dd.size))
    if np.ptp(tt) <= 0:
        raise ValueError("t must take at least 2 distinct values")
    _choice(law, "law", ("all", "walker") + tuple(LAWS))
    names = ["kick", "bond", "rittinger", "walker"] if law == "all" else [law]
    y = np.log(dd)
    fits = {}
    for nm in names:
        f = _law_fit_one(tt, y, None if nm == "walker" else LAWS[nm])
        k_par = 3 if nm == "walker" else 2
        rss = float(np.sum(f["residual_log"] ** 2))
        f["rms_log"] = float(math.sqrt(rss / tt.size))
        f["aic"] = float(tt.size * math.log(max(rss / tt.size, 1e-300)) + 2 * k_par)
        fits[nm] = f
    fixed = [nm for nm in fits if nm in LAWS]
    best = min(fixed, key=lambda nm: fits[nm]["rms_log"]) if fixed else None
    return {"fits": fits, "best_fixed": best, "n_points": int(tt.size)}


def breakage_first_order_fit(t, w, x=None) -> dict:
    """一次の破砕速度 ``w(t) = w₀ exp(−S t)`` を当てる(Deniz 2004 の式 (2)、出典 Austin)。

    ``w`` が 1-D: ある区間(または径 ``x`` より上の累積)の体積割合の時系列。返り: ``S``・``w0``・``rms_log``・``r2``
    (ln w の直線の決定係数)・``S_early`` / ``S_late``(前半・後半の時点だけで当てた S、一次なら等しい —— 遅くなるなら一次から外れる)。
    ``w`` が 2-D ``(n_x, n_t)`` で ``x``(各行の径、µm)を渡すと、行ごとの S と ``S = a_T x^α``(Deniz の式 (3))の ``a_T``・``alpha``。
    ``apparent=True`` は「最上位の区間でない(上から生まれ込む粒がある)ので式 (1) は厳密でない」の自己申告で、累積に当てた場合は常に True。
    割合が 0 以下・1 超・点が 3 未満 → ``ValueError``。
    """
    tt = _vec(t, "t", min_len=3, nonneg=True)
    W = np.asarray(w, dtype=np.float64)
    if W.ndim == 1:
        W = W[None, :]
        xs = None if x is None else np.atleast_1d(_pos(x, "x"))
    elif W.ndim == 2:
        if x is None:
            raise ValueError("2-D w needs x (one size per row)")
        xs = _vec(x, "x", min_len=1, positive=True)
        if xs.size != W.shape[0]:
            raise ValueError("x must have one value per row of w")
    else:
        raise ValueError("w must be 1-D or 2-D")
    if W.shape[1] != tt.size:
        raise ValueError("w must have one column per time (%d vs %d)" % (W.shape[1], tt.size))
    if not np.all(np.isfinite(W)) or np.any(W <= 0) or np.any(W > 1):
        raise ValueError("w must be fractions in (0, 1]")
    if np.ptp(tt) <= 0:
        raise ValueError("t must take at least 2 distinct values")
    order = np.argsort(tt, kind="stable")
    half = tt.size // 2

    def line(tv, yv):
        A = np.vstack([np.ones_like(tv), tv]).T
        c = np.linalg.lstsq(A, yv, rcond=None)[0]
        return c, yv - A @ c

    rows = []
    for row in W:
        y = np.log(row)
        c, r = line(tt, y)
        ss = float(np.sum((y - y.mean()) ** 2))
        e_idx, l_idx = order[:max(half, 2)], order[min(half, tt.size - 2):]
        ce = line(tt[e_idx], y[e_idx])[0] if np.ptp(tt[e_idx]) > 0 else (np.nan, np.nan)
        cl = line(tt[l_idx], y[l_idx])[0] if np.ptp(tt[l_idx]) > 0 else (np.nan, np.nan)
        rows.append({"S": float(-c[1]), "w0": float(math.exp(c[0])), "rms_log": float(math.sqrt(np.mean(r ** 2))),
                     "r2": float(1.0 - np.sum(r ** 2) / ss) if ss > 0 else float("nan"),
                     "S_early": float(-ce[1]), "S_late": float(-cl[1])})
    out = dict(rows[0]) if len(rows) == 1 else {"rows": rows}
    out["apparent"] = True
    if xs is not None and len(rows) >= 2:
        S = np.array([r["S"] for r in rows])
        ok = S > 0
        if np.sum(ok) >= 2:
            c = np.polyfit(np.log(xs[ok]), np.log(S[ok]), 1)
            out.update({"x": xs, "S_per_x": S, "a_T": float(math.exp(c[1])), "alpha": float(c[0])})
        else:
            out.update({"x": xs, "S_per_x": S, "a_T": float("nan"), "alpha": float("nan")})
    return out


# ----------------------------------------------------------------------------------------------
# 独立試行のばらつきと材料の差
# ----------------------------------------------------------------------------------------------
def replicate_compare(groups: dict, log: bool = True) -> dict:
    """独立試行のばらつきと、群(材料)どうしの差を同じ物差しで並べる。

    ``groups``: 名前 → ``(n_runs, n_conditions)`` の配列(例: 材料ごとに 3 回 × 7 時点の D50)。全群で ``n_conditions`` が同じ。
    ``log=True`` は ln をとってから比べる(径の比のばらつき = 変動係数に近い)。返り: ``spread``(群 → 条件ごとの ``mean``・``sd``・
    ``cv``(SD/平均、元の尺度)、``cv_pooled``(cv の二乗平均の根)、``cv_max``)、``separation``(群の組 → 条件ごとの
    ``|Δ平均| / √(SE₁² + SE₂²)``(SE = SD/√n)と、その最小 ``min_z``。鍵は ``"名前1|名前2"`` の文字列)。試行が 2 未満 → ``ValueError``。
    """
    if not isinstance(groups, dict) or len(groups) < 1:
        raise ValueError("groups must be a non-empty dict name -> (n_runs, n_conditions) array")
    arrs, n_cond = {}, None
    for name, a in groups.items():
        A = np.asarray(a, dtype=np.float64)
        if A.ndim != 2 or A.shape[0] < 2:
            raise ValueError("group %r must be 2-D with at least 2 runs, got shape %r" % (name, np.shape(a)))
        if not np.all(np.isfinite(A)) or (log and np.any(A <= 0)):
            raise ValueError("group %r must be finite%s" % (name, " and > 0 (log=True)" if log else ""))
        if n_cond is None:
            n_cond = A.shape[1]
        elif A.shape[1] != n_cond:
            raise ValueError("all groups must have the same number of conditions")
        arrs[name] = A
    spread, stats = {}, {}
    for name, A in arrs.items():
        m, sd = A.mean(axis=0), A.std(axis=0, ddof=1)
        cv = sd / np.abs(m)
        spread[name] = {"mean": m, "sd": sd, "cv": cv, "cv_pooled": float(math.sqrt(np.mean(cv ** 2))),
                        "cv_max": float(np.max(cv)), "n_runs": int(A.shape[0])}
        L = np.log(A) if log else A
        stats[name] = (L.mean(axis=0), L.std(axis=0, ddof=1) / math.sqrt(A.shape[0]))
    sep = {}
    names = list(arrs)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            (m1, s1), (m2, s2) = stats[names[i]], stats[names[j]]
            den = np.sqrt(s1 ** 2 + s2 ** 2)
            z = np.where(den > 0, np.abs(m1 - m2) / np.where(den > 0, den, 1.0), np.inf)
            sep["%s|%s" % (names[i], names[j])] = {"z": z, "min_z": float(np.min(z)), "argmin": int(np.argmin(z)),
                                                  "pair": (str(names[i]), str(names[j]))}
    return {"spread": spread, "separation": sep, "log": bool(log)}


# ----------------------------------------------------------------------------------------------
# 音響放射(AE)
# ----------------------------------------------------------------------------------------------
def ae_read_csv(path, header_lines: int = 12, offset: float = 32768.0, full_scale: float = 32768.0) -> np.ndarray:
    """AE の生の CSV(ヘッダ ``header_lines`` 行 + 1 行 1 標本の ADC 値)を電圧 [V] の信号にする。

    公開データの ADC は 16 bit・±1 V・ストレートオフセットバイナリ(0 → −1 V、32768 → 0 V、65535 → +1 V)なので
    ``(raw − offset) / full_scale``(解析コードの変換と同じ)。パスは返り値に残さない。数値でない行・空 → ``ValueError``。
    """
    nh = int(header_lines)
    if isinstance(header_lines, bool) or nh != header_lines or nh < 0:
        raise ValueError("header_lines must be an integer >= 0")
    off = float(offset)
    fsc = _pos(full_scale, "full_scale")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError as exc:
        raise ValueError("ae_read_csv: cannot read the file (%s)" % type(exc).__name__)
    body = [s for s in lines[nh:] if s.strip()]
    if len(body) < 2:
        raise ValueError("ae_read_csv: fewer than 2 samples after %d header lines" % nh)
    try:
        raw = np.asarray(body, dtype=np.float64)
    except ValueError:
        raise ValueError("ae_read_csv: non-numeric sample (wrong header_lines?)")
    if not np.all(np.isfinite(raw)):
        raise ValueError("ae_read_csv: non-finite sample")
    return (raw - off) / fsc


def ae_band_power(x, rate: float, f_lo: float = 1e5, f_hi: float = 1e6, start: int = 0, stop: int | None = None,
                  win: int = 4096) -> dict:
    """AE の帯域電力を 2 通りで出す(一方は公開の解析コードの定義、他方は ``acoustics.stft`` の密度スペクトル)。

    - ``power_fft``: 窓なし FFT の振幅 ``2|X|/N`` の二乗を ``f_lo ≤ f ≤ f_hi`` で足した値 [V²] (解析コードと同じ。正弦波の振幅 A なら A²)。
    - ``power_stft``: ``acoustics.stft(scaling="density")`` の内側のコマの PSD を帯域で積分した平均 [V²] (= 帯域の平均二乗)。
      Parseval で ``power_fft ≈ 2 · power_stft``(振幅² は平均二乗の 2 倍)。比 ``ratio = power_fft / (2 power_stft)`` を返す。
    - ``band_series`` / ``times``: コマごとの帯域電力(スペクトログラムの帯の時間変化)、``spectrogram_db`` は表示用(帯に関係なく全帯域)。
    ``start`` / ``stop`` は標本の切り出し(解析コードは雑音の区間を飛ばすため 200013 から)。
    """
    import acoustics
    fs = _pos(rate, "rate")
    lo, hi = _pos(f_lo, "f_lo"), _pos(f_hi, "f_hi")
    if not lo < hi <= fs / 2.0:
        raise ValueError("need 0 < f_lo < f_hi <= rate/2, got %g, %g, rate %g" % (lo, hi, fs))
    s = _vec(x, "x", min_len=8)
    a = int(start)
    b = s.size if stop is None else int(stop)
    if isinstance(start, bool) or a != start or a < 0 or not (a < b <= s.size) or b - a < 8:
        raise ValueError("start/stop must select at least 8 samples inside the signal")
    seg = s[a:b]
    N = seg.size
    amp = np.abs(np.fft.rfft(seg)) / N * 2.0
    f = np.fft.rfftfreq(N, 1.0 / fs)
    band = (f >= lo) & (f <= hi)
    if not np.any(band):
        raise ValueError("no FFT bin inside the band")
    p_fft = float(np.sum(amp[band] ** 2))
    w = int(win)
    if isinstance(win, bool) or w != win or w < 16 or w > N:
        raise ValueError("win must be an integer in [16, len(segment)]")
    st = acoustics.stft(seg, fs, win=w, hop=w // 2, scaling="density")
    inner = st["interior"]
    if int(np.sum(inner)) < 1:
        raise ValueError("segment too short for one interior STFT frame")
    P = np.abs(st["spectra"][:, inner]) ** 2
    fb = (st["freqs"] >= lo) & (st["freqs"] <= hi)
    df = float(st["freqs"][1] - st["freqs"][0])
    series = P[fb].sum(axis=0) * df
    p_stft = float(series.mean())
    return {"power_fft": p_fft, "power_stft": p_stft, "ratio": p_fft / (2.0 * p_stft) if p_stft > 0 else float("nan"),
            "band_series": series, "times": np.asarray(st["times"])[inner] + a / fs,
            "freqs": np.asarray(st["freqs"]), "spectrogram_db": 10.0 * np.log10(P + 1e-30),
            "n_samples": int(N), "band_hz": (lo, hi)}


def ae_size_correspondence(power, d50, group=None) -> dict:
    """AE の帯域電力と D50 の対応(単調性・相関・log–log の傾き α、``P ∝ D50^α``)。

    ``group`` を渡すと群(材料)ごとに出す(材料で電力の水準が桁で違うので、混ぜた相関は水準の差を拾う —— ``pooled`` は参考)。
    返り: 群 → ``n``・``spearman``(順位相関)・``alpha``(ln P を ln D50 に当てた傾き)・``sign_agree``(全ての組で
    「D50 が大きい方が P も大きい」の割合)。**点が 2 つなら spearman は ±1 しか取れない**(``n`` を必ず併記する)。
    """
    P = _vec(power, "power", min_len=2, positive=True)
    D = _vec(d50, "d50", min_len=2, positive=True)
    if P.size != D.size:
        raise ValueError("power and d50 must have the same length")
    if group is None:
        g = np.zeros(P.size, dtype=int)
        labels = [0]
    else:
        g_in = list(group)
        if len(g_in) != P.size:
            raise ValueError("group must have one label per point")
        labels = list(dict.fromkeys(g_in))
        g = np.array([labels.index(v) for v in g_in])

    def rank(v):
        o = np.argsort(v, kind="stable")
        r = np.empty(v.size)
        r[o] = np.arange(v.size, dtype=float)
        for val in np.unique(v):                    # 同順位は平均順位
            m = v == val
            r[m] = r[m].mean()
        return r

    def one(p, d):
        n = p.size
        if n < 2 or np.ptp(d) <= 0:
            return {"n": int(n), "spearman": float("nan"), "alpha": float("nan"), "sign_agree": float("nan")}
        rp, rd = rank(p), rank(d)
        sp = float(np.corrcoef(rp, rd)[0, 1]) if np.ptp(rp) > 0 else float("nan")
        alpha = float(np.polyfit(np.log(d), np.log(p), 1)[0])
        agree, tot = 0, 0
        for i in range(n):
            for j in range(i + 1, n):
                if d[i] != d[j]:
                    tot += 1
                    agree += int((d[i] - d[j]) * (p[i] - p[j]) > 0)
        return {"n": int(n), "spearman": sp, "alpha": alpha, "sign_agree": agree / tot if tot else float("nan")}

    out = {"groups": {lab: one(P[g == k], D[g == k]) for k, lab in enumerate(labels)}}
    out["pooled"] = one(P, D)
    return out


# ----------------------------------------------------------------------------------------------
# 画像から D50(合成の門だけ。外から 1 つの規律は上の実データが満たす)
# ----------------------------------------------------------------------------------------------
def particle_image_synth(n: int = 60, d_med: float = 12.0, sigma_ln: float = 0.35, shape=(256, 256),
                         pitch: float = 1.0, seed: int = 0, gap: float = 3.0, supersample: int = 4) -> dict:
    """重ならない円板(粒子の投影)を撒いた被覆率の画像と真値(直径 [µm] の対数正規、``pitch`` µm/px)。

    円板どうしは ``gap`` px 以上離す(融合は別の問題で、poc_particle_sizing が扱う)。既定 3 px: 2 px だと両側の部分画素が
    斜めに隣り合い、8 連結のラベルで 2 個が 1 個になった(12 枚中 4 枚、体積基準の D50 が最大 8.5 % ずれた)。縁は ``supersample`` で反エイリアス。
    返り: ``image``(``(H, W)`` 被覆率)、``pitch``、``truth``(``diameters`` µm、``centres`` px、``touches_border``)。
    置けなかった粒子があれば ``n_placed < n``(黙って詰めない)。
    """
    nn = int(n)
    if isinstance(n, bool) or nn != n or nn < 1:
        raise ValueError("n must be an integer >= 1")
    dm, sg, pt = _pos(d_med, "d_med"), _pos(sigma_ln, "sigma_ln"), _pos(pitch, "pitch")
    try:
        H, W = (int(shape[0]), int(shape[1]))
    except (TypeError, ValueError, IndexError):
        raise ValueError("shape must be (H, W)")
    if H < 16 or W < 16:
        raise ValueError("shape must be at least 16 x 16")
    ss = int(supersample)
    if ss < 1 or ss > 16:
        raise ValueError("supersample must be in [1, 16]")
    gp = float(gap)
    if not math.isfinite(gp) or gp < 0:
        raise ValueError("gap must be >= 0")
    rng = np.random.default_rng(int(seed))
    d_px = np.exp(rng.normal(math.log(dm / pt), sg, nn))
    d_px = np.clip(d_px, 3.0, 0.25 * min(H, W))
    cen, rad = [], []
    for d in sorted(d_px, reverse=True):
        r = 0.5 * d
        for _ in range(400):
            c = (rng.uniform(-0.3 * r, H + 0.3 * r), rng.uniform(-0.3 * r, W + 0.3 * r))
            # 外周の画素の帯の境目から ±0.25 px 以内に円の縁が来る置き方は捨てる(掛かったか否かが閾値の被覆率で決まり、
            # 真値の「縁に触れる」と計測が 1 個ずれる —— 体積基準は大きい 1 個で D50 が 4 % 動いた)
            m_edge = min(c[0] - r - 1.0, H - 1.0 - c[0] - r, c[1] - r - 1.0, W - 1.0 - c[1] - r)
            if abs(m_edge) < 0.25:
                continue
            if all(math.hypot(c[0] - q[0], c[1] - q[1]) >= r + rq + gp for q, rq in zip(cen, rad)):
                cen.append(c)
                rad.append(r)
                break
    img = np.zeros((H, W))
    off = (np.arange(ss) + 0.5) / ss
    for (cr, cc), r in zip(cen, rad):
        r0, r1 = max(int(cr - r) - 1, 0), min(int(cr + r) + 2, H)
        c0, c1 = max(int(cc - r) - 1, 0), min(int(cc + r) + 2, W)
        if r0 >= r1 or c0 >= c1:
            continue
        yy = (np.arange(r0, r1)[:, None] + off[None, :]).ravel()
        xx = (np.arange(c0, c1)[:, None] + off[None, :]).ravel()
        inside = ((yy[:, None] - cr) ** 2 + (xx[None, :] - cc) ** 2) <= r * r
        cov = inside.reshape(r1 - r0, ss, c1 - c0, ss).mean(axis=(1, 3))
        img[r0:r1, c0:c1] = np.maximum(img[r0:r1, c0:c1], cov)
    rad_a = np.asarray(rad)
    cen_a = np.asarray(cen).reshape(-1, 2)
    # 縁に触れる = 円板が外周の画素(行 0 は [0, 1) の帯)に掛かる。計測の側の「ラベルが外周の画素を含む」と同じ規約に
    # しないと、外周の画素に少しだけ掛かる粒子で真値と推定の数が合わない(円が画像の外へ出るか、で決めた最初の版で踏んだ)。
    touch = ((cen_a[:, 0] - rad_a < 1) | (cen_a[:, 0] + rad_a > H - 1) | (cen_a[:, 1] - rad_a < 1)
             | (cen_a[:, 1] + rad_a > W - 1)) if rad_a.size else np.zeros(0, bool)
    return {"image": img, "pitch": pt, "n_placed": int(rad_a.size),
            "truth": {"diameters": 2.0 * rad_a * pt, "centres": cen_a, "touches_border": touch}}


def _weighted_quantiles(d, w, qs):
    """重み ``w`` の累積に対して log(径) を補間した分位(粒度分布の ``log_edges`` と同じ精神、点の分布版: 中点則)。"""
    o = np.argsort(d)
    d, w = d[o], w[o]
    c = (np.cumsum(w) - 0.5 * w) / np.sum(w)
    return [float(np.exp(np.interp(q / 100.0, c, np.log(d)))) for q in qs]


def particle_image_d50(image, pitch: float, basis: str = "volume", threshold: float = 0.02, border: str = "exclude") -> dict:
    """被覆率の画像の粒子から D10 / D50 / D90 [µm]。面積は **ラベルの中の被覆率の和**(縁の部分画素を数える、閾値で太らない)。

    ``basis``: ``"volume"``(球と見て d³ の重み —— レーザー回折と同じ体積基準)、``"number"``(個数基準)。同じ画像でも
    この 2 つは別の分布で、体積基準が大きく出る。``border``: ``"exclude"``(縁に触れる粒子を捨てる)/ ``"include"``。
    返り: ``d10``・``d50``・``d90``・``diameters``(等価円直径 µm)・``n``・``n_border``・``basis``。粒子が 3 未満 → ``ValueError``。
    融合した粒子は 1 個に数える(分けない —— 塗れた面積の分離は別の op の仕事)。
    """
    import blob2d
    img = np.asarray(image, dtype=np.float64)
    if img.ndim != 2 or min(img.shape) < 3 or not np.all(np.isfinite(img)):
        raise ValueError("image must be a finite 2-D array of at least 3x3")
    pt = _pos(pitch, "pitch")
    _choice(basis, "basis", ("volume", "number"))
    _choice(border, "border", ("exclude", "include"))
    th = float(threshold)
    if not (0.0 < th < 1.0):
        raise ValueError("threshold must satisfy 0 < threshold < 1")
    lab = blob2d.blob_label(img > th)
    nlab = int(lab.max())
    if nlab < 1:
        raise ValueError("no particle above the threshold")
    area_px = np.bincount(lab.ravel(), weights=np.clip(img, 0, 1).ravel(), minlength=nlab + 1)[1:]
    H, W = img.shape
    edge = np.zeros(nlab + 1, bool)
    for side in (lab[0], lab[-1], lab[:, 0], lab[:, -1]):
        edge[np.unique(side)] = True
    edge = edge[1:]
    keep = ~edge if border == "exclude" else np.ones(nlab, bool)
    d = 2.0 * np.sqrt(area_px[keep] / math.pi) * pt
    if d.size < 3:
        raise ValueError("fewer than 3 particles to measure (%d)" % d.size)
    wts = d ** 3 if basis == "volume" else np.ones_like(d)
    d10, d50, d90 = _weighted_quantiles(d, wts, (10, 50, 90))
    return {"d10": d10, "d50": d50, "d90": d90, "diameters": d, "n": int(d.size), "n_border": int(edge.sum()),
            "basis": basis, "weights_quantile": "log-diameter interpolation of the mid-point cumulative weight"}
