# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""mathspectral — FFT では足りないスペクトル推定(不等間隔の周期図・部分空間法の到来方向推定)。

2026-10-03 の棚卸しで、どの層にも op が無かった 2 系統を足す(numpy だけ):

* **Lomb–Scargle 周期図** —— 時刻が**不等間隔**な観測(欠測のある計測、天体の光度曲線、間引かれたログ)の
  周期を探す。等間隔なら古典的な周期図 |DFT|²/N に一致する(Scargle 1982)。
* **到来方向推定の部分空間法(MUSIC / ESPRIT)** —— 等間隔線形アレイの複素スナップショットから、波の来る向きを推定する。
  遅延和ビームフォーマ(``rangedoppler.beamform_doa``)の分解能は開口で決まり、1 ビーム幅の中の 2 波を分けられない
  (rangedoppler.py が「別の契約なので同じ名前に入れない」と明記していたもの)。部分空間法は**共分散と波源の数**
  を前提に、その限界を越える —— 代わりに、波源の数を間違える・波が相関していると壊れる(docstring に明記)。

規約: アレイの素子は 0..M−1、間隔 d は波長単位(既定 0.5)、到来角 θ は正面(broadside)から測り、
ステアリングベクトル a(θ)_m = exp(−2πi · d · m · sin θ)。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = ["esprit_doa", "lomb_scargle", "music_doa", "n_sources_mdl", "ula_snapshots"]


def lomb_scargle(t, y, freqs) -> dict:
    """不等間隔の時系列 (t, y) の Lomb–Scargle 周期図(Scargle 1982 の時刻ずらし τ つき、平均を引いてから)。

    P(f) = ½ [ (Σ y_c cos ω(t−τ))² / Σ cos² ω(t−τ) + (Σ y_c sin ω(t−τ))² / Σ sin² ω(t−τ) ]、ω = 2πf、
    tan 2ωτ = Σ sin 2ωt / Σ cos 2ωt。f は周波数(t の単位の逆数)。f = 0 は定義されないので拒否する。

    門: 等間隔の標本ではフーリエ周波数 k/(NΔt) で |DFT|²/N に一致する。
    返り値 ``{"freq", "power", "peak_freq"}``。
    """
    t = np.asarray(t, dtype=np.float64).ravel()
    y = np.asarray(y, dtype=np.float64).ravel()
    f = np.asarray(freqs, dtype=np.float64).ravel()
    if t.shape != y.shape or t.size < 3:
        raise ValueError("lomb_scargle: t と y は同じ長さ(3 以上)")
    if not (np.all(np.isfinite(t)) and np.all(np.isfinite(y)) and np.all(np.isfinite(f))):
        raise ValueError("lomb_scargle: NaN/inf がある")
    if np.any(f <= 0):
        raise ValueError("lomb_scargle: 周波数は正(f = 0 では τ が定まらない)")
    yc = y - y.mean()
    w = 2.0 * math.pi * f[:, None]
    tau = np.arctan2(np.sum(np.sin(2 * w * t), axis=1), np.sum(np.cos(2 * w * t), axis=1))[:, None] / (2 * w)
    arg = w * (t[None, :] - tau)
    c, s = np.cos(arg), np.sin(arg)
    cc, ss = np.sum(c * c, axis=1), np.sum(s * s, axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        p = 0.5 * (np.where(cc > 0, (c @ yc) ** 2 / cc, 0.0) + np.where(ss > 0, (s @ yc) ** 2 / ss, 0.0))
    return {"freq": f, "power": p, "peak_freq": float(f[int(np.argmax(p))])}


def _steer(M, d, theta):
    m = np.arange(M)[:, None]
    return np.exp(-2j * math.pi * d * m * np.sin(np.atleast_1d(theta))[None, :])


def ula_snapshots(angles_deg=(10.0, 16.0), n_elements: int = 8, n_snapshots: int = 200, *, spacing: float = 0.5,
                  snr_db: float | None = None, seed: int = 0) -> np.ndarray:
    """等間隔線形アレイが受ける複素スナップショット (M, K) を作る(到来方向推定の答えの決まる入力)。

    波源ごとに独立な複素ガウスの信号(無相関)。``snr_db`` を与えると素子ごとの白色雑音を足す(None = 雑音なし)。
    """
    th = np.radians(np.atleast_1d(np.asarray(angles_deg, dtype=np.float64)))
    M, K = int(n_elements), int(n_snapshots)
    if M < 2 or K < 1 or th.size >= M:
        raise ValueError("ula_snapshots: 素子 >= 2、スナップショット >= 1、波源の数 < 素子の数")
    rng = np.random.default_rng(seed)
    S = (rng.normal(size=(th.size, K)) + 1j * rng.normal(size=(th.size, K))) / math.sqrt(2)
    X = _steer(M, float(spacing), th) @ S
    if snr_db is not None:
        sig = 10 ** (-float(snr_db) / 20)
        X = X + sig * (rng.normal(size=X.shape) + 1j * rng.normal(size=X.shape)) / math.sqrt(2)
    return X


def n_sources_mdl(X) -> dict:
    """スナップショットから波源の数を MDL 基準で推定する(Wax & Kailath 1985)。

    共分散の固有値を大きい順に並べ、「下から M−k 個が等しい(= 雑音)」という仮説ごとに
    MDL(k) = −K (M−k) log(幾何平均 / 算術平均) + ½ k (2M−k) log K を計算し、最小の k を選ぶ。
    雑音が白色で、スナップショット数 K が素子数 M より十分多いことが前提。
    """
    X = np.asarray(X)
    if X.ndim != 2 or X.shape[0] < 2 or not np.all(np.isfinite(X)):
        raise ValueError("n_sources_mdl: スナップショットは有限な (M >= 2, K) の 2-D")
    M, K = X.shape
    vals = np.clip(np.linalg.eigvalsh(X @ X.conj().T / K)[::-1], 1e-300, None)
    mdl = []
    for k in range(M):
        tail = vals[k:]
        ratio = math.exp(np.mean(np.log(tail))) / np.mean(tail)
        mdl.append(-K * (M - k) * math.log(max(ratio, 1e-300)) + 0.5 * k * (2 * M - k) * math.log(K))
    return {"n_sources": int(np.argmin(mdl[:M - 1])), "mdl": np.asarray(mdl), "eigenvalues": vals}


def _cov_subspace(X, n_sources):
    X = np.asarray(X)
    if X.ndim != 2 or X.shape[0] < 2:
        raise ValueError("到来方向推定: スナップショットは (素子数 M >= 2, K) の 2-D")
    if not np.all(np.isfinite(X)):
        raise ValueError("到来方向推定: NaN/inf がある")
    M = X.shape[0]
    n = n_sources_mdl(X)["n_sources"] if n_sources is None else int(n_sources)
    if not 1 <= n < M:
        raise ValueError("到来方向推定: 1 <= 波源の数 < 素子の数(%d)" % M)
    R = X @ X.conj().T / X.shape[1]
    vals, vecs = np.linalg.eigh(R)                    # 昇順
    return R, vals[::-1], vecs[:, ::-1], n, M


def music_doa(X, n_sources: int | None = None, *, spacing: float = 0.5, grid_deg=None) -> dict:
    """MUSIC(Schmidt 1986): 共分散の雑音部分空間に直交する向きを探す。

    P(θ) = 1 / ‖E_nᴴ a(θ)‖²。真の向きでは分母がほぼ 0 になり鋭い峰が立つ。
    **前提**: 波源の数が正しい・波源どうしが無相関(相関した波 = 多重反射では部分空間が潰れて峰が消える)。
    ``n_sources=None`` なら :func:`n_sources_mdl` で推定し、返り値の ``n_sources_estimated`` を True にする。
    返り値 ``{"grid_deg", "pseudo_spectrum_db", "doa_deg", "eigenvalues"}``(doa は峰の大きい順に n 個、格子の分解能)。
    """
    _R, vals, vecs, n, M = _cov_subspace(X, n_sources)
    g = np.linspace(-90, 90, 3601) if grid_deg is None else np.asarray(grid_deg, dtype=np.float64)
    En = vecs[:, n:]
    A = _steer(M, float(spacing), np.radians(g))
    denom = np.sum(np.abs(En.conj().T @ A) ** 2, axis=0)
    P = 1.0 / np.maximum(denom, 1e-300)
    Pdb = 10 * np.log10(P / P.max())
    pk = np.flatnonzero((Pdb[1:-1] > Pdb[:-2]) & (Pdb[1:-1] >= Pdb[2:])) + 1
    pk = pk[np.argsort(Pdb[pk])[::-1]][:n]
    return {"grid_deg": g, "pseudo_spectrum_db": Pdb, "doa_deg": np.sort(g[pk]), "eigenvalues": vals,
            "n_sources": n, "n_sources_estimated": n_sources is None}


def esprit_doa(X, n_sources: int | None = None, *, spacing: float = 0.5) -> dict:
    """ESPRIT(Roy & Kailath 1989): アレイの「1 素子ずらし」の不変性から、格子を使わずに向きを解く。

    信号部分空間 E_s の上 M−1 行と下 M−1 行を最小二乗で結ぶ Φ の固有値 λ_k = exp(−2πi d sin θ_k) から
    θ_k = arcsin(−arg λ_k / (2π d))。雑音なし・無相関なら厳密(格子の分解能に縛られない)。
    ``n_sources=None`` なら MDL で推定する。返り値 ``{"doa_deg", "eigenvalues", "n_sources", "n_sources_estimated"}``。
    """
    _R, vals, vecs, n, M = _cov_subspace(X, n_sources)
    d = float(spacing)
    Es = vecs[:, :n]
    Phi = np.linalg.lstsq(Es[:-1], Es[1:], rcond=None)[0]
    lam = np.linalg.eigvals(Phi)
    s = np.clip(-np.angle(lam) / (2 * math.pi * d), -1.0, 1.0)
    return {"doa_deg": np.sort(np.degrees(np.arcsin(s))), "eigenvalues": vals,
            "n_sources": n, "n_sources_estimated": n_sources is None}
