"""1D 関数(プロファイル)演算(HALCON "Tools" chapter の genuine 実装, numpy).

1D 信号(gray プロファイル等)の平滑化・微分・積分・ゼロ交差・極大極小。純粋な信号処理。
入力 y は 1D 配列。
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def smooth_funct_1d_gauss(y, sigma: float = 1.0):
    """1D ガウス平滑化(smooth_funct_1d_gauss)。"""
    return ndimage.gaussian_filter1d(np.asarray(y, float), sigma=float(sigma))


def derivate_funct_1d(y):
    """1D 微分(中心差分、derivate_funct_1d)。"""
    return np.gradient(np.asarray(y, float))


def integrate_funct_1d(y):
    """1D 累積積分(台形則、integrate_funct_1d)。"""
    y = np.asarray(y, float)
    out = np.zeros_like(y)
    out[1:] = np.cumsum((y[:-1] + y[1:]) / 2.0)
    return out


def zero_crossings_funct_1d(y):
    """符号が変わる位置(ゼロ交差)の index を返す(zero_crossings_funct_1d)。"""
    y = np.asarray(y, float)
    s = np.sign(y)
    return np.nonzero((s[:-1] * s[1:]) < 0)[0]


def local_min_max_funct_1d(y):
    """局所極大/極小の index を返す(local_min_max_funct_1d)。"""
    y = np.asarray(y, float)
    mx = np.nonzero((y[1:-1] > y[:-2]) & (y[1:-1] > y[2:]))[0] + 1
    mn = np.nonzero((y[1:-1] < y[:-2]) & (y[1:-1] < y[2:]))[0] + 1
    return {"max": mx, "min": mn}


def funct_1d_to_pairs(y):
    """1D 関数を (x, y) の対に変換(funct_1d_to_pairs)。"""
    y = np.asarray(y, float)
    return np.column_stack([np.arange(len(y)), y])


def abs_funct_1d(y):
    """y 値の絶対値(abs_funct_1d)。"""
    return np.abs(np.asarray(y, float))


def negate_funct_1d(y):
    """y 値の符号反転(negate_funct_1d)。"""
    return -np.asarray(y, float)


def scale_y_funct_1d(y, mult=1.0, add=0.0):
    """y 値を線形変換 mult*y+add(scale_y_funct_1d)。"""
    return float(mult) * np.asarray(y, float) + float(add)


def compose_funct_1d(y1, y2):
    """2 関数の合成 y1(y2)(値域を index として参照、compose_funct_1d)。"""
    y1 = np.asarray(y1, float); y2 = np.asarray(y2, float)
    idx = np.clip(np.round(y2).astype(int), 0, len(y1) - 1)
    return y1[idx]


def num_points_funct_1d(y) -> int:
    """関数の点数(num_points_funct_1d)。"""
    return int(len(np.asarray(y)))


def distance_funct_1d(y1, y2, mode="max") -> float:
    """2 関数間の距離(max=上限, mean=平均、distance_funct_1d)。"""
    d = np.abs(np.asarray(y1, float) - np.asarray(y2, float))
    return float(d.max() if mode == "max" else d.mean())


def sample_funct_1d(y, step=2):
    """関数を step 間隔で再標本化(sample_funct_1d)。"""
    return np.asarray(y, float)[::int(step)]


def get_pair_funct_1d(y, index=0):
    """index の (x, y) 対を返す(get_pair_funct_1d)。"""
    y = np.asarray(y, float)
    i = int(np.clip(index, 0, len(y) - 1))
    return np.array([float(i), float(y[i])])
