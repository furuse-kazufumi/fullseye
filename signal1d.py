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
