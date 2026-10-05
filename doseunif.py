# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""doseunif — 粉の粒径から低用量製剤 1 回分の含量のばらつき(変動係数 CV)を出し、何分挽けば足りるかを逆算する(規則だけ、学習なし、2026-10-06)。

:mod:`grind`(乳鉢の粉砕を測る)の続き。粒度分布(レーザー回折の体積基準の表、または画像から測った粒の直径の標本)から、
よく混ざった粉から 1 回分を取ったときに **薬の粒の数が揺らぐだけで生じる** 含量の CV を閉形式と Monte Carlo で出し、
粉砕則(:func:`grind.comminution_law_fit`)を通して「CV が目標を下回るのに要る粉砕時間」を返す。

導出(本モジュールで行った。式の形は Yalkowsky–Bolton 型として広く引用されるものと同じだが、原論文は **未読**):

- 1 回分に入る薬の粒の数 N は平均 λ の Poisson(粉の中で粒が独立に一様に散っている = 理想的なランダム混合)、粒の質量 mᵢ は独立に
  同じ分布。1 回分の薬の量 S = Σᵢ mᵢ は複合 Poisson で、``E[S] = λ E[m]``、``Var S = λ E[m²]``。平均が狙いの量 D になる λ = D / E[m] で

      CV² = Var S / E[S]² = E[m²] / (E[m] · D)。

- 球の粒 m = c d³(c = πρ/6)なら ``CV² = c · E[d⁶] / (E[d³] · D) = c · D63³ / D``。ここで ``D63 = (E[d⁶]/E[d³])^{1/3}`` は個数基準の
  6 次と 3 次のモーメントの比の 3 乗根(モーメント径 D[6,3])。**恒等式** ``E_n[d⁶] / E_n[d³] = E_v[d³]``(個数基準の比 = 体積基準の
  d³ の平均)なので、レーザー回折の体積基準の表からは **分布の形を仮定せずに** D63 が出る(:func:`dose_cv_from_sizes` の ``"histogram"``)。
- 個数基準の対数正規(中央径 d_g、σ = ln の標準偏差)なら ``E[dᵏ] = d_gᵏ exp(k²σ²/2)`` から ``D63³ = d_g³ exp(13.5 σ²)``。体積基準の中央径
  ``d_v = d_g exp(3σ²)``(Hatch–Choate)で書けば ``D63³ = d_v³ exp(4.5 σ²)``、すなわち ``CV² = π ρ d_v³ exp(4.5 σ²) / (6 D)``。
- 粒の数を固定した取り方(N = λ を丸めた整数)なら ``Var S = N Var m`` で ``CV² = CV²_Poisson − 1/N``(λ ≫ 1 では差は無視できる)。

含量均一性の目安(規格の本文は転載しない。数は二次資料による記憶で、**公定の本文と照合していない** —— 引数で変えられる):
10 個の受入値 ``AV = |M − X̄| + k s``(k = 2.4、M は X̄ を 98.5〜101.5 % に切り詰めた値)が L1 = 15 以下なら第 1 段で合格。平均が
狙いどおり(M = X̄)なら ``s ≤ L1/k = 6.25 %`` が「AV ≤ 15 相当」の CV の目安。**ただし CV = 6.25 % の粉で 10 個を測っても合格するのは
およそ半分**(s は標本の揺らぎを持つ: ``P = P(χ²₉ ≤ 9 (6.25/CV)²)``、CV = 6.25 % で 0.56)。:func:`grind_time_for_dose_cv` は
合格の確率を指定して目標の CV を決められる(χ² の閉形式は平均のずれの項を無視した上限、Monte Carlo はその項も入れる)。

正直に(門に固定してある):

- **画像の標本から出す CV は偏る**。2026-10-06 の試走で「写真から出した CV が 4 つの径で一貫して 6 % 低い」と見えたが、4 つの径は
  画素の単位で **同じ 12 枚の画像**(種 0〜11、画素ピッチを径に比例させた)を縮尺違いで測っていただけで、独立な 4 回ではなかった。
  多数の独立な束(12 枚 = 約 600 粒ずつ)で分けると(PoC の門 5・6): (1) **縁に触れる粒を捨てると大きい粒ほど捨てられやすく、平均で
  約 −5 %**(主因)。Miles–Lantuéjoul の重み 1/((H−2)p − d)((W−2)p − d) で大半が戻る。(2) d⁶ の標本平均は少数の大粒に支配され
  (最大 1 % の粒が Σd⁶ の約 4 割)、**平均は偏らないが中央値は約 −2 %、束ごとの散らばり ±11〜12 %** —— 1 回の測定はたいてい低く出る。
  (3) 対数正規を当てて出すと散らばりが半分(±5.6 %)になり、平均の偏りは +0.4 % 以内(Miles–Lantuéjoul の重みと併用)。モーメントの
  百分位 bootstrap の 90 % 区間は真値を約 2/3 しか覆わない(重い裾の典型)ので、
  既定は対数正規の当てはめと、その区間(bootstrap と、Kish の有効数を使うデルタ法)。対数正規でない分布では対数正規の当てはめ自体が偏る
  (実データの門で、体積基準の表から形を仮定せずに出した値との差を報告)。
- 含量のばらつきは **粒の数の揺らぎだけ**。混合の不完全さ・偏析・錠剤の質量のばらつき・分析誤差は入らない(実際の CV はこれより大きい
  —— この値は下限)。粒は球、密度は一様、凝集していない、と仮定。レーザー回折の D63 は粗い裾(装置の分解能が最も悪い所)に支配される
  (返り値の ``coarse_share``)。

単位: 径 µm、1 回分の薬の量 ``dose_mg`` [mg]、真密度 ``density`` [g/cm³]、CV は割合(0.05 = 5 %)。失敗はすべて ValueError(fail-closed)。

呼び出し例(既存の grind の op と繋ぐ。tests/test_doseunif.py が実行する)::

    import numpy as np
    import grind, doseunif
    psd = grind.particle_size_synth(60.0, 0.45)                    # 体積基準の粒度分布(装置の 74 区間)
    r = doseunif.dose_cv_from_sizes(psd, 5.0, 1.6)                 # 5 mg、真密度 1.6 g/cm³ → 形を仮定しない CV
    im = grind.particle_image_synth(60, 12.0, 0.35, (256, 256), seed=1)
    d = grind.particle_image_d50(im["image"], im["pitch"], basis="number")["diameters"]
    s = doseunif.dose_cv_from_sizes(d, 0.02, 1.3, frame=(256, 256, im["pitch"]))   # 写真の粒 → CV と区間(縁の重み)
    t = np.array([0.0, 5.0, 10.0, 20.0])
    d63 = np.array([grind.comminution_energy(400.0, law="bond", energy=0.004 * x)["x_product"] for x in t])
    g = doseunif.grind_time_for_dose_cv(t, d63, 5.0, 1.6, pass_probability=0.95)   # 95 % 通すのに要る時間
    print(round(r["cv"], 4), round(s["cv"], 3), s["ci_delta"], round(g["t_req"], 1), g["law"])
"""
from __future__ import annotations

import math

import numpy as np

import grind as G

__all__ = ["dose_cv_lognormal", "dose_cv_from_sizes", "grind_time_for_dose_cv"]

_BASES = ("number", "volume")
_METHODS = ("closed", "monte_carlo")
_SAMPLING = ("poisson", "fixed_count")
_ESTIMATORS_SAMPLE = ("lognormal", "moment")
_ESTIMATORS_PSD = ("histogram", "lognormal")
_Z95 = 1.6448536269514722          # 片側 95 %(両側 90 %)の正規分位


# ----------------------------------------------------------------------------------------------------------------------
# 引数の検査(fail-closed)
def _pos(v, name, op):
    if isinstance(v, bool):
        raise ValueError("%s: %s must be a finite number > 0, got %r" % (op, name, v))
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a finite number > 0, got %r" % (op, name, v)) from None
    if not (math.isfinite(f) and f > 0.0):
        raise ValueError("%s: %s must be a finite number > 0, got %r" % (op, name, v))
    return f


def _choice(v, name, allowed, op):
    if not isinstance(v, str) or v not in allowed:
        raise ValueError("%s: %s must be one of %r, got %r" % (op, name, tuple(allowed), v))
    return v


def _int_ge(v, name, lo, op):
    if isinstance(v, bool):
        raise ValueError("%s: %s must be an integer >= %d, got %r" % (op, name, lo, v))
    try:
        i = int(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be an integer >= %d, got %r" % (op, name, lo, v)) from None
    if i != v or i < lo:
        raise ValueError("%s: %s must be an integer >= %d, got %r" % (op, name, lo, v))
    return i


def _c_mg_per_um3(density):
    """球の質量の係数 c [mg/µm³]: m = c d³、c = (π/6) ρ、ρ [g/cm³] → 1 µm³ = 1e-12 cm³、1 g = 1e3 mg。"""
    return math.pi / 6.0 * density * 1e-9


def _cv_from_d63(d63, dose_mg, density):
    return math.sqrt(_c_mg_per_um3(density) * d63 ** 3 / dose_mg)


# ======================================================================================================================
# 1. 対数正規の閉形式と Monte Carlo
def dose_cv_lognormal(d_median: float, sigma_ln: float, dose_mg: float, density: float, basis: str = "number",
                      method: str = "closed", sampling: str = "poisson", n_rep: int = 2000, seed: int = 0,
                      max_draws: int = 20_000_000) -> dict:
    """粒径が対数正規の粉から 1 回分(薬 ``dose_mg``)を取ったときの含量の CV(粒の数の揺らぎだけ)。

    閉形式(モジュール冒頭の導出): ``CV² = c · D63³ / D``、c = πρ/6、``D63³ = d_g³ exp(13.5 σ²) = d_v³ exp(4.5 σ²)``。``basis``:
    ``"number"``(``d_median`` は個数基準の中央径 d_g、画像の粒の数え方)/ ``"volume"``(体積基準の中央径 d_v、レーザー回折の D50)。
    ``sampling``: ``"poisson"``(既定、粒の数 N が Poisson)/ ``"fixed_count"``(N = λ を丸めた整数に固定、``CV² = CV²_Poisson − 1/N``)。
    ``method="monte_carlo"``: 1 回分を ``n_rep`` 回作り(N を引き、N 個の径を対数正規から引いて質量を足す)標本の CV を返す —— 閉形式と
    **独立な経路**(式を使わない)。標準誤差 ``cv_mc_se`` は 20 個の束の散らばりから。引く径の総数が ``max_draws`` を超えるなら
    黙って減らさず ValueError(λ × n_rep を見て n_rep を減らすか閉形式を使う)。

    返り: ``cv``(``method`` の値)、``cv_closed``、``particles_per_dose``(λ、fixed_count では整数 N)、``mean_particle_mg``、``d63``、
    ``d_number_median``・``d_volume_median`` [µm]、``basis``・``sampling``・``method``、Monte Carlo なら ``cv_mc``・``cv_mc_se``・``n_rep``・``draws``。
    **Raises** ValueError: 正であるべき量が正でない、綴り違い、fixed_count で N < 2、Monte Carlo の総数が上限を超える。
    """
    op = "dose_cv_lognormal"
    dm = _pos(d_median, "d_median", op)
    sg = _pos(sigma_ln, "sigma_ln", op)
    D = _pos(dose_mg, "dose_mg", op)
    rho = _pos(density, "density", op)
    _choice(basis, "basis", _BASES, op)
    _choice(method, "method", _METHODS, op)
    _choice(sampling, "sampling", _SAMPLING, op)
    if sg > 2.0:
        raise ValueError("%s: sigma_ln %.3g > 2 (exp(13.5 sigma^2) overflows any useful precision)" % (op, sg))
    dg = dm if basis == "number" else dm * math.exp(-3.0 * sg * sg)
    dv = dg * math.exp(3.0 * sg * sg)
    c = _c_mg_per_um3(rho)
    d63 = dg * math.exp(4.5 * sg * sg)                       # (d_g³ exp(13.5σ²))^{1/3}
    m_mean = c * dg ** 3 * math.exp(4.5 * sg * sg)           # E[m] = c E[d³] = c d_g³ exp(9σ²/2)
    lam = D / m_mean
    cv2 = c * d63 ** 3 / D
    if sampling == "fixed_count":
        N = int(round(lam))
        if N < 2:
            raise ValueError("%s: fixed_count needs at least 2 particles per dose (lambda = %.3g)" % (op, lam))
        # CV² = Var m / (N E[m]²) = (E[m²]/E[m]² − 1)/N、E[m²]/E[m]² = exp(9σ²)
        cv2 = (math.exp(9.0 * sg * sg) - 1.0) / N
        lam_out = float(N)
    else:
        lam_out = float(lam)
    out = {"cv": math.sqrt(cv2), "cv_closed": math.sqrt(cv2), "particles_per_dose": lam_out, "mean_particle_mg": float(m_mean),
           "d63": float(d63), "d_number_median": float(dg), "d_volume_median": float(dv), "basis": basis, "sampling": sampling,
           "method": method}
    if method == "closed":
        return out
    nr = _int_ge(n_rep, "n_rep", 40, op)
    mx = _int_ge(max_draws, "max_draws", 1, op)
    expected = lam_out * nr
    if expected > mx:
        raise ValueError("%s: Monte Carlo would draw about %.3g diameters (> max_draws %d); lower n_rep or use method='closed'"
                         % (op, expected, mx))
    rng = np.random.default_rng(int(seed))
    doses = np.empty(nr)
    chunk = max(1, int(2_000_000 // max(lam_out, 1.0)))
    draws = 0
    lg = math.log(dg)
    for s0 in range(0, nr, chunk):
        k = min(chunk, nr - s0)
        cnt = rng.poisson(lam, k) if sampling == "poisson" else np.full(k, int(lam_out))
        tot = int(cnt.sum())
        draws += tot
        d = np.exp(rng.normal(lg, sg, tot))
        doses[s0:s0 + k] = np.bincount(np.repeat(np.arange(k), cnt), weights=c * d ** 3, minlength=k)
    if not np.all(np.isfinite(doses)) or doses.mean() <= 0:
        raise ValueError("%s: Monte Carlo produced no drug (lambda %.3g too small for n_rep %d)" % (op, lam_out, nr))
    cv_mc = float(doses.std(ddof=1) / doses.mean())
    batches = np.array_split(doses, 20)
    cvb = np.array([b.std(ddof=1) / b.mean() for b in batches])
    out.update({"cv": cv_mc, "cv_mc": cv_mc, "cv_mc_se": float(cvb.std(ddof=1) / math.sqrt(len(cvb))), "n_rep": nr, "draws": int(draws),
                "dose_mean_mg": float(doses.mean())})
    return out


# ======================================================================================================================
# 2. 測った粒径(画像の標本 / レーザー回折の表)から
def _psd_bin_d3(edges):
    """区間 [e_i, e_{i+1}] の中で体積が ln d について一様なときの d³ の平均 = (e₂³ − e₁³) / (3 ln(e₂/e₁))(最後の行は 0)。"""
    e1, e2 = edges[:-1], edges[1:]
    m = (e2 ** 3 - e1 ** 3) / (3.0 * np.log(e2 / e1))
    return np.concatenate([m, [0.0]])


def _wstats_log(d, w):
    """重み w の ln d の平均と分散(Kish の有効数で不偏化)と有効数。"""
    sw = float(w.sum())
    l = np.log(d)
    m = float(np.sum(w * l) / sw)
    n_eff = sw * sw / float(np.sum(w * w))
    v = float(np.sum(w * (l - m) ** 2) / sw)
    v *= n_eff / max(n_eff - 1.0, 1e-12)
    return m, v, n_eff


def _d63_moment(d, w):
    return float((np.sum(w * d ** 6) / np.sum(w * d ** 3)) ** (1.0 / 3.0))


def _d63_logn(d, w):
    m, v, _ = _wstats_log(d, w)
    return float(math.exp(m + 4.5 * v))                      # (exp(3m + 13.5v))^{1/3}


def dose_cv_from_sizes(sizes, dose_mg: float, density: float, estimator: str | None = None, frame=None, ci: float = 0.9,
                       n_boot: int = 400, seed: int = 0) -> dict:
    """測った粒径から 1 回分の含量の CV(粒の数の揺らぎだけ、Poisson)と、その偏りと区間。

    ``sizes`` は 2 通り:

    - **1-D の配列** = 個数基準の粒の直径の標本 [µm] (:func:`grind.particle_image_d50` の ``diameters`` など)。``estimator``:
      ``"lognormal"``(既定 —— ln d の平均と分散から ``D63 = exp(m + 4.5 v)``)/ ``"moment"``(``D63³ = Σd⁶/Σd³`` をそのまま。
      平均は偏らないが少数の大粒に支配され、中央値は低く出る)。``frame = (H_px, W_px, pitch_um)`` を渡すと、縁に触れる粒を捨てた
      測定(``particle_image_d50`` の ``border="exclude"``: 外周の画素に掛かった粒を捨てる)の大粒の取りこぼしを Miles–Lantuéjoul の重み
      ``1 / (((H−2)p − d)((W−2)p − d))`` で直す(省くと平均で −5 % 程度低い、モジュール冒頭)。区間は ``ci``(両側)の百分位 bootstrap
      (``n_boot`` 回、両方の推定量)と、対数正規のデルタ法(Kish の有効数 n_eff、``Var ln CV = (9v/n_eff + 364.5 v²/(n_eff − 1))/4``)。
    - **dict(``edges``・``volume``)** = レーザー回折の体積基準の表(:func:`grind.particle_size_read` / :func:`grind.particle_size_synth`)。
      ``estimator``: ``"histogram"``(既定 —— 恒等式 ``D63³ = E_v[d³]`` を区間ごとに「ln d について一様」の積分で、**分布の形を仮定しない**)/
      ``"lognormal"``(``σ = ln(D84/D16)/2``、``D63 = D50 exp(1.5σ²)``)。表に粒の数は無いので標本の区間は出さない(``ci_bootstrap`` は None)。
      ``coarse_share`` = E_v[d³] のうち D90 より上の区間が占める割合(粗い裾への依存の度合い)。

    返り: ``cv``(選んだ推定量)、``d63``、推定量ごとの ``cv_*``・``d63_*``、``sigma_ln``、``d_number_median``(標本)/ ``d50_volume``(表)、
    ``particles_per_dose``、``n``・``n_eff``、``top1pct_share_d6``(標本: 最大 1 % の粒が Σd⁶ に占める割合)、``ci_bootstrap``・``ci_delta``、
    ``estimator``・``source``(``"sample"`` / ``"psd"``)・``edge_corrected``。
    **Raises** ValueError: 粒が 10 未満・非有限・非正、表が壊れている(:func:`grind.particle_size_dx` と同じ検査)、frame に収まらない粒、綴り違い。
    """
    op = "dose_cv_from_sizes"
    D = _pos(dose_mg, "dose_mg", op)
    rho = _pos(density, "density", op)
    cc = float(ci) if not isinstance(ci, bool) else float("nan")
    if not (0.5 <= cc < 1.0):
        raise ValueError("%s: ci must satisfy 0.5 <= ci < 1, got %r" % (op, ci))
    c = _c_mg_per_um3(rho)
    if isinstance(sizes, dict):
        est = "histogram" if estimator is None else _choice(estimator, "estimator", _ESTIMATORS_PSD, op)
        if frame is not None:
            raise ValueError("%s: frame is only for a sample of diameters, not for a size table" % op)
        e, f = G._psd(sizes, op + ": sizes")
        bin_d3 = _psd_bin_d3(e)
        ev_d3 = float(np.sum(f * bin_d3))
        d63_h = ev_d3 ** (1.0 / 3.0)
        d16, d50, d84, d90 = (G.particle_size_dx(sizes, q) for q in (15.865525393145708, 50.0, 84.13447460685429, 90.0))
        sg = 0.5 * math.log(d84 / d16)
        d63_l = d50 * math.exp(1.5 * sg * sg)
        coarse = float(np.sum(np.where(e >= d90, f * bin_d3, 0.0)) / ev_d3)
        # 端 i ≥ D90 の区間を「粗い」とする(D90 を跨ぐ区間は含めない側に倒す)
        d63 = d63_h if est == "histogram" else d63_l
        # 個数基準の E[d³] = 1 / E_v[d⁻³] (体積 → 個数の変換)。区間内 ln d 一様の積分 (e₁⁻³ − e₂⁻³)/(3 ln(e₂/e₁))
        e1, e2 = e[:-1], e[1:]
        inv3 = np.concatenate([(e1 ** -3 - e2 ** -3) / (3.0 * np.log(e2 / e1)), [0.0]])
        en_d3 = 1.0 / float(np.sum(f * inv3))
        return {"cv": _cv_from_d63(d63, D, rho), "d63": float(d63), "cv_histogram": _cv_from_d63(d63_h, D, rho),
                "cv_lognormal": _cv_from_d63(d63_l, D, rho), "d63_histogram": float(d63_h), "d63_lognormal": float(d63_l),
                "sigma_ln": float(sg), "d50_volume": float(d50), "coarse_share": coarse,
                "particles_per_dose": float(D / (c * en_d3)), "n": None, "n_eff": None, "top1pct_share_d6": None,
                "ci_bootstrap": None, "ci_delta": None, "estimator": est, "source": "psd", "edge_corrected": False,
                "ci_note": "a size table carries no particle count, so no sampling interval"}
    est = "lognormal" if estimator is None else _choice(estimator, "estimator", _ESTIMATORS_SAMPLE, op)
    try:
        d = np.asarray(sizes, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("%s: sizes must be a 1-D array of diameters or a size-table dict" % op) from None
    if d.ndim != 1 or d.size < 10:
        raise ValueError("%s: need a 1-D array of at least 10 diameters, got shape %r" % (op, d.shape))
    if not (np.all(np.isfinite(d)) and np.all(d > 0)):
        raise ValueError("%s: diameters must be finite and > 0" % op)
    nb = _int_ge(n_boot, "n_boot", 50, op)
    if frame is None:
        w = np.ones_like(d)
    else:
        try:
            Hp, Wp, pt = (float(frame[0]), float(frame[1]), float(frame[2]))
        except (TypeError, ValueError, IndexError):
            raise ValueError("%s: frame must be (H_px, W_px, pitch_um)" % op) from None
        if not (Hp >= 3 and Wp >= 3 and pt > 0 and all(map(math.isfinite, (Hp, Wp, pt)))):
            raise ValueError("%s: frame must be (H_px >= 3, W_px >= 3, pitch_um > 0)" % op)
        a_h, a_w = (Hp - 2.0) * pt - d, (Wp - 2.0) * pt - d
        if np.any(a_h <= 0) or np.any(a_w <= 0):
            raise ValueError("%s: a particle (max %.4g um) does not fit inside the frame; the edge correction is undefined" % (op, d.max()))
        w = 1.0 / (a_h * a_w)
        w = w / w.mean()
    m, v, n_eff = _wstats_log(d, w)
    d63_m, d63_l = _d63_moment(d, w), _d63_logn(d, w)
    cv_m, cv_l = _cv_from_d63(d63_m, D, rho), _cv_from_d63(d63_l, D, rho)
    rng = np.random.default_rng(int(seed))
    bm, bl = np.empty(nb), np.empty(nb)
    for k in range(nb):
        i = rng.integers(0, d.size, d.size)
        bm[k] = _cv_from_d63(_d63_moment(d[i], w[i]), D, rho)
        bl[k] = _cv_from_d63(_d63_logn(d[i], w[i]), D, rho)
    lo_q, hi_q = 50.0 * (1.0 - cc), 50.0 * (1.0 + cc)
    from statistics import NormalDist
    z = NormalDist().inv_cdf(0.5 + 0.5 * cc)
    sd_log = 0.5 * math.sqrt(9.0 * v / n_eff + 364.5 * v * v / max(n_eff - 1.0, 1e-12))
    o = np.argsort(d)[::-1]
    k1 = max(1, int(math.ceil(0.01 * d.size)))
    w6 = w * d ** 6
    en_d3 = float(np.sum(w * d ** 3) / np.sum(w))
    return {"cv": cv_l if est == "lognormal" else cv_m, "d63": d63_l if est == "lognormal" else d63_m,
            "cv_lognormal": cv_l, "cv_moment": cv_m, "d63_lognormal": d63_l, "d63_moment": d63_m, "sigma_ln": float(math.sqrt(v)),
            "d_number_median": float(math.exp(m)), "particles_per_dose": float(D / (c * en_d3)), "n": int(d.size), "n_eff": float(n_eff),
            "top1pct_share_d6": float(w6[o[:k1]].sum() / w6.sum()),
            "ci_bootstrap": {"lognormal": (float(np.percentile(bl, lo_q)), float(np.percentile(bl, hi_q))),
                             "moment": (float(np.percentile(bm, lo_q)), float(np.percentile(bm, hi_q)))},
            "ci_delta": (cv_l * math.exp(-z * sd_log), cv_l * math.exp(z * sd_log)), "ci": cc,
            "estimator": est, "source": "sample", "edge_corrected": frame is not None}


# ======================================================================================================================
# 3. 粉砕則で逆算
def _stage1_pass_mc(cv, n_units, k_accept, limit_av, ref_range, n_mc, seed):
    """第 1 段の受入値の模擬: X_i = 100 (1 + cv z_i)(正規近似)、AV = |M − X̄| + k s、M = clip(X̄, ref_range)。"""
    rng = np.random.default_rng(int(seed))
    X = 100.0 * (1.0 + cv * rng.standard_normal((n_mc, n_units)))
    xb = X.mean(axis=1)
    s = X.std(axis=1, ddof=1)
    M = np.clip(xb, ref_range[0], ref_range[1])
    av = np.abs(M - xb) + k_accept * s
    return float(np.mean(av <= limit_av))


def _law_time(fit, n, d_req):
    """当てはめた則で径が d_req に届く時間(Kick: ln(x0/d)/k、n ≠ 1: (d^{1−n} − x0^{1−n})/((n−1)k)、x0 = inf なら第 2 項 0)。"""
    k, x0 = fit["k"], fit["x0"]
    if abs(n - 1.0) < 1e-9:
        return math.log(x0 / d_req) / k
    u0 = 0.0 if math.isinf(x0) else x0 ** (1.0 - n)
    return (d_req ** (1.0 - n) - u0) / ((n - 1.0) * k)


def grind_time_for_dose_cv(t, d63, dose_mg: float, density: float, target_cv: float | None = None,
                           pass_probability: float | None = None, law: str = "best", k_accept: float = 2.4,
                           limit_av: float = 15.0, n_units: int = 10, ref_range=(98.5, 101.5), n_mc: int = 20000,
                           seed: int = 0) -> dict:
    """モーメント径 D63 の時間変化に粉砕則を当て、含量の CV が目標まで下がるのに要る粉砕時間を逆算する。

    ``t``: 粉砕時間(エネルギーの代わり、:mod:`grind` の約束)、``d63``: その時点の D63 [µm] (:func:`dose_cv_from_sizes` の ``d63``。
    D50 でなく D63 を使うのは、CV が D63 だけで決まり分布の形の仮定が要らないから —— 粉砕則を D63 に当てるのは D50 に当てるのと同じく仮定)。
    目標: ``target_cv`` を直接、または ``pass_probability`` = 10 個の第 1 段に合格する確率(χ² の閉形式、平均のずれを無視した上限)から
    ``CV = (L1/k) √((n−1)/χ²_p(n−1)) / 100``。どちらも無ければ ``L1/k/100``(= 0.0625、「AV ≤ 15 相当」の目安、合格はおよそ半分)。
    必要な D63 は ``(CV² D / c)^{1/3}``(Poisson、c = πρ/6)。3 則(kick / bond / rittinger)全部で時間を出し、``law="best"`` は
    log の rms が最小の則、名前を渡せばその則。則による違いは ``t_req_by_law`` と ``t_req_spread`` に(模型の不確かさとして読む)。
    返り: ``t_req``、``law``、``d63_req``、``target_cv``、``t_req_by_law``、``t_req_spread``(min, max)、``extrapolated``(t_req が測った範囲を超える)・
    ``extrap_ratio``、``already_met``(最初の点で既に目標以下)、``cv_observed``(各点の CV)、``pass_probability_chi2``(目標の CV での
    上限)・``pass_probability_mc``(平均のずれの項も入れた Monte Carlo、正規近似)、``fits``(:func:`grind.comminution_law_fit` の要約)。
    **Raises** ValueError: 点が 3 未満・非正・長さ違い、target と pass_probability の両方、範囲外の確率・CV、綴り違い。
    """
    op = "grind_time_for_dose_cv"
    D = _pos(dose_mg, "dose_mg", op)
    rho = _pos(density, "density", op)
    k_acc = _pos(k_accept, "k_accept", op)
    L1 = _pos(limit_av, "limit_av", op)
    nu = _int_ge(n_units, "n_units", 2, op)
    nmc = _int_ge(n_mc, "n_mc", 1000, op)
    try:
        lo_r, hi_r = float(ref_range[0]), float(ref_range[1])
    except (TypeError, ValueError, IndexError):
        raise ValueError("%s: ref_range must be (low, high) in %% of label claim" % op) from None
    if not (math.isfinite(lo_r) and math.isfinite(hi_r) and lo_r <= 100.0 <= hi_r):
        raise ValueError("%s: ref_range must contain 100 (%% of label claim)" % op)
    _choice(law, "law", ("best",) + tuple(G.LAWS), op)
    from scipy.stats import chi2
    if target_cv is not None and pass_probability is not None:
        raise ValueError("%s: give at most one of target_cv and pass_probability" % op)
    if pass_probability is not None:
        p = float(pass_probability) if not isinstance(pass_probability, bool) else float("nan")
        if not (0.0 < p < 1.0):
            raise ValueError("%s: pass_probability must satisfy 0 < p < 1, got %r" % (op, pass_probability))
        tgt = (L1 / k_acc) / 100.0 * math.sqrt((nu - 1) / chi2.ppf(p, nu - 1))
    elif target_cv is not None:
        tgt = _pos(target_cv, "target_cv", op)
        if tgt >= 1.0:
            raise ValueError("%s: target_cv is a fraction (0.05 = 5 %%), got %r" % (op, target_cv))
    else:
        tgt = (L1 / k_acc) / 100.0
    tt = np.asarray(t, dtype=np.float64)
    dd = np.asarray(d63, dtype=np.float64)
    if tt.ndim != 1 or dd.ndim != 1 or tt.size != dd.size or tt.size < 3:
        raise ValueError("%s: t and d63 must be 1-D arrays of the same length >= 3" % op)
    fit = G.comminution_law_fit(tt, dd, law="all")
    c = _c_mg_per_um3(rho)
    d_req = (tgt * tgt * D / c) ** (1.0 / 3.0)
    by = {}
    for nm in G.LAWS:
        f = fit["fits"][nm]
        if not math.isinf(f["x0"]) and d_req >= f["x0"]:
            by[nm] = 0.0
        else:
            by[nm] = float(max(_law_time(f, G.LAWS[nm], d_req), 0.0))
    chosen = fit["best_fixed"] if law == "best" else law
    t_req = by[chosen]
    tmax = float(tt.max())
    cv_obs = np.sqrt(c * dd ** 3 / D)
    i0 = int(np.argmin(tt))
    p_chi = float(chi2.cdf((nu - 1) * (L1 / (k_acc * 100.0 * tgt)) ** 2, nu - 1))
    p_mc = _stage1_pass_mc(tgt, nu, k_acc, L1, (lo_r, hi_r), nmc, seed)
    return {"t_req": t_req, "law": chosen, "d63_req": float(d_req), "target_cv": float(tgt), "t_req_by_law": by,
            "t_req_spread": (min(by.values()), max(by.values())), "extrapolated": bool(t_req > tmax),
            "extrap_ratio": float(t_req / tmax) if tmax > 0 else math.inf, "already_met": bool(cv_obs[i0] <= tgt),
            "cv_observed": cv_obs, "pass_probability_chi2": p_chi, "pass_probability_mc": p_mc,
            "fits": {nm: {k: fit["fits"][nm][k] for k in ("n", "x0", "k", "rms_log")} for nm in fit["fits"]},
            "acceptance": {"k": k_acc, "L1": L1, "n_units": nu, "ref_range": (lo_r, hi_r),
                           "note": "numbers from secondary sources, not checked against the official text"}}
