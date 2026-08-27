# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""signal1d — 点列(1D 信号)の多項式近似・フーリエ変換・ローパス/ハイパス(簡単API)。

計測点列やプロファイルを手軽に扱うための最小 op 群。``dsp`` は音声志向(サンプリング
レート必須の Butterworth)だが、こちらは **rate 不要**・カットオフを「ナイキストに対する
割合 [0,1]」で指定する data/point-sequence 向けの簡単版:

    poly_fit / poly_eval    — 点列を多項式で近似(トレンド抽出・外挿)
    fft_spectrum            — 片側スペクトル(周波数と振幅)。何本の波が含まれるか
    lowpass / highpass      — 周波数フィルタ(平滑化 / 細部・エッジ抽出)。ガウス緩衝で
    bandpass                  リンギングを抑えた素直な実装
    smooth                  — 移動平均(最も単純な平滑化)

規約: 信号 ``y`` は 1D 実数配列(等間隔サンプル)。カットオフ ``cutoff`` は 0..1 で
ナイキスト周波数に対する割合(0.2 なら帯域の下側 20% 付近まで通す)。
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "poly_fit",
    "poly_eval",
    "fft_spectrum",
    "lowpass",
    "highpass",
    "bandpass",
    "smooth",
    "spline_fit",
    "spline_eval",
    "spline_resample",
    "spline_curve_fit",
    "spline_curve_eval",
    "spline_curve_resample",
]


def _as_1d(y, name="y"):
    a = np.asarray(y, dtype=np.float64).ravel()
    if a.size < 2:
        raise ValueError(f"{name} は長さ2以上の1D配列が必要(受領: {a.shape})")
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{name} に非有限値がある")
    return a


# --------------------------------------------------------------------------- #
# 多項式近似                                                                   #
# --------------------------------------------------------------------------- #
def poly_fit(x, y, degree):
    """点列 (x, y) を次数 degree の多項式で最小二乗近似し、係数を返す(最高次から)。

    返り値は :func:`numpy.polyval` 互換(``poly_eval`` に渡せる)。degree が小さいほど
    大まかなトレンド、大きいほど細部に追従する。
    """
    xa = _as_1d(x, "x")
    ya = _as_1d(y, "y")
    if xa.shape != ya.shape:
        raise ValueError(f"x と y の長さが不一致({xa.shape} vs {ya.shape})")
    d = int(degree)
    if d < 0:
        raise ValueError(f"degree は非負(受領: {degree})")
    if d >= xa.size:
        raise ValueError(f"degree({d}) は点数({xa.size})未満でなければならない")
    return np.polyfit(xa, ya, d)


def poly_eval(coef, x):
    """多項式係数 coef(最高次から)を点 x で評価する。"""
    return np.polyval(np.asarray(coef, dtype=np.float64), np.asarray(x, dtype=np.float64))


# --------------------------------------------------------------------------- #
# フーリエ変換(スペクトル)                                                    #
# --------------------------------------------------------------------------- #
def fft_spectrum(y, sample_spacing=1.0):
    """点列 y の片側振幅スペクトルを返す ``(freqs, magnitude)``。

    freqs は cycles/sample(sample_spacing を渡せば物理周波数)、magnitude は各周波数
    成分の振幅(正弦波の振幅にほぼ対応するよう 2/N 正規化、DC 除く)。信号に何本の
    周期成分が含まれるかを読むのに使う。
    """
    a = _as_1d(y, "y")
    n = a.size
    mag = np.abs(np.fft.rfft(a)) * (2.0 / n)
    mag[0] = np.abs(np.fft.rfft(a)[0]) / n          # DC は 1/N
    freqs = np.fft.rfftfreq(n, d=float(sample_spacing))
    return freqs, mag


# --------------------------------------------------------------------------- #
# ローパス / ハイパス / バンドパス(ガウス緩衝でリンギング抑制)                #
# --------------------------------------------------------------------------- #
def _gauss_lp_gain(n, cutoff):
    """rfft ビンごとのローパスゲイン(ナイキスト割合 cutoff のガウス緩衝)。"""
    f = np.fft.rfftfreq(n) / 0.5                     # [0,1] ナイキストに対する割合
    fc = float(np.clip(cutoff, 1e-6, 1.0))
    return np.exp(-0.5 * (f / fc) ** 2)


def _apply_gain(y, gain):
    return np.fft.irfft(np.fft.rfft(y) * gain, n=y.size)


def lowpass(y, cutoff=0.2):
    """点列 y をローパス(高周波=ノイズ/細部を落として平滑化)。cutoff=ナイキスト割合。"""
    a = _as_1d(y, "y")
    return _apply_gain(a, _gauss_lp_gain(a.size, cutoff))


def highpass(y, cutoff=0.2):
    """点列 y をハイパス(トレンド=低周波を除き、細部・エッジ・変動だけ残す)。"""
    a = _as_1d(y, "y")
    return a - _apply_gain(a, _gauss_lp_gain(a.size, cutoff))


def bandpass(y, low=0.1, high=0.4):
    """点列 y のバンドパス(low..high の中間帯だけ通す)。low<high(ナイキスト割合)。"""
    a = _as_1d(y, "y")
    if not (0.0 <= low < high <= 1.0):
        raise ValueError(f"0<=low<high<=1 が必要(受領: low={low}, high={high})")
    return _apply_gain(a, _gauss_lp_gain(a.size, high)) - _apply_gain(a, _gauss_lp_gain(a.size, low))


def smooth(y, window=5):
    """移動平均による平滑化(window は奇数の窓幅、端はエッジ複製)。"""
    a = _as_1d(y, "y")
    w = int(window)
    if w < 1:
        raise ValueError(f"window は1以上(受領: {window})")
    if w % 2 == 0:
        w += 1
    pad = w // 2
    ap = np.pad(a, pad, mode="edge")
    kern = np.ones(w) / w
    return np.convolve(ap, kern, mode="valid")


# --------------------------------------------------------------------------- #
# スプライン補間(専用の spline object を返す)                                 #
# --------------------------------------------------------------------------- #
def spline_fit(x, y, smooth=0.0):
    """点列 (x, y) を3次スプラインで補間/平滑化し、評価可能な spline object を返す。

    smooth=0 なら **全点を通る補間スプライン**(C2 連続、区分多項式より滑らか)、
    smooth>0 なら **平滑化スプライン**(ノイズを許容し全点を通らない)。返り値は
    :func:`spline_eval` / :func:`spline_resample` に渡せる(scipy の呼び出し可能オブジェクト)。
    x は昇順でなくてよい(内部でソートする)。
    """
    from scipy.interpolate import CubicSpline, UnivariateSpline
    xa = _as_1d(x, "x")
    ya = _as_1d(y, "y")
    if xa.shape != ya.shape:
        raise ValueError(f"x と y の長さが不一致({xa.shape} vs {ya.shape})")
    order = np.argsort(xa)
    xs, ys = xa[order], ya[order]
    if np.any(np.diff(xs) <= 0):
        raise ValueError("x に重複値があり補間できない(単調増加に整列できない)")
    s = float(smooth)
    if s < 0:
        raise ValueError(f"smooth は非負(受領: {smooth})")
    if s > 0:
        return UnivariateSpline(xs, ys, s=s)               # 平滑化(s=scipy 平滑化係数)
    return CubicSpline(xs, ys)                              # 補間(全点を通る)


def spline_eval(spline, x):
    """spline object を点 x で評価する。"""
    return np.asarray(spline(np.asarray(x, dtype=np.float64)), dtype=np.float64)


def spline_resample(x, y, n, smooth=0.0):
    """点列を n 点に等間隔で滑らかに再サンプルし ``(x_new, y_new)`` を返す。

    まばら/不揃いな点列を、スプラインで補間して密で等間隔な曲線に直すのに使う。
    """
    xa = _as_1d(x, "x")
    if int(n) < 2:
        raise ValueError(f"n は2以上(受領: {n})")
    spl = spline_fit(xa, y, smooth=smooth)
    x_new = np.linspace(float(xa.min()), float(xa.max()), int(n))
    return x_new, spline_eval(spl, x_new)


# --------------------------------------------------------------------------- #
# パラメトリック曲線スプライン(開曲線 / 閉曲線)                                #
# --------------------------------------------------------------------------- #
# 曲線は「大枠 Polygon(点列)と同じ」= 点列に closed 属性が付いただけ、と捉える。
# spline_curve_fit は {"points","closed","tck","u","dim"}(= 点列 + 属性)を返す。
# 閉曲線は周期境界(接線がシームで連続)、開曲線は端点自由、を closed で使い分ける。
# 点列は 2D でも 3D でもよい(D=2 は輪郭、D=3 は空間曲線)。
def _as_ptsND(points, name="points"):
    p = np.asarray(points, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] < 2:
        raise ValueError(f"{name} は (N, D>=2) の曲線点列が必要(受領: {p.shape})")
    if p.shape[0] < 4:
        raise ValueError(f"{name} は4点以上必要(3次スプライン, 受領: {p.shape[0]})")
    if not np.all(np.isfinite(p)):
        raise ValueError(f"{name} に非有限値がある")
    return p


def spline_curve_fit(points, closed=False, smooth=0.0):
    """点列を **弧長パラメトリック3次スプライン** で当てはめる(2D 輪郭 / 3D 空間曲線)。

    ``closed=False`` は**開曲線**(端点自由)、``closed=True`` は**閉曲線**(周期境界で
    シームの接線が連続=ループが滑らかに閉じる)。輪郭/ポリゴンと同じ点列表現に属性を
    足しただけの軽い object を返す(新しい重い型は作らない):

        {"points": (N,D) 制御点, "closed": bool, "tck": 係数, "u": 制御点の parameter, "dim": D}

    D=2 なら x(t),y(t)、D=3 なら x(t),y(t),z(t)(3D 空間曲線)を同じ API で扱える。
    ``smooth`` は scipy の平滑化係数(0=全点を通る補間、>0=ノイズ許容の近似)。
    """
    from scipy.interpolate import splprep
    p = _as_ptsND(points)
    per = 1 if closed else 0
    if closed and not np.allclose(p[0], p[-1]):
        p = np.vstack([p, p[0]])                         # splprep periodic は先頭==末尾を期待
    tck, u = splprep([p[:, j] for j in range(p.shape[1])], s=float(smooth), per=per, k=3)
    return {"points": p, "closed": bool(closed), "tck": tck,
            "u": np.asarray(u, dtype=np.float64), "dim": int(p.shape[1])}


def spline_curve_eval(model, t):
    """曲線スプライン model をパラメータ t∈[0,1] で評価し (M,D) 点を返す(D=2 or 3)。"""
    from scipy.interpolate import splev
    coords = splev(np.asarray(t, dtype=np.float64), model["tck"])
    return np.column_stack([np.asarray(c, dtype=np.float64) for c in coords])


def spline_curve_resample(points, n, closed=False, smooth=0.0):
    """曲線点列を n 点に滑らかに再サンプルして (n,D) を返す(2D/3D、閉曲線はシーム非重複)。"""
    if int(n) < 4:
        raise ValueError(f"n は4以上(受領: {n})")
    m = spline_curve_fit(points, closed=closed, smooth=smooth)
    t = np.linspace(0.0, 1.0, int(n), endpoint=not closed)
    return spline_curve_eval(m, t)
