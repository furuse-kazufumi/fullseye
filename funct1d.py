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


def smooth_funct_1d_mean(y, size=3, iterations=1):
    """1D 移動平均平滑化(smooth_funct_1d_mean)。"""
    from scipy.ndimage import uniform_filter1d
    y = np.asarray(y, float)
    for _ in range(int(iterations)):
        y = uniform_filter1d(y, int(size), mode="nearest")
    return y


def invert_funct_1d(y):
    """関数 y=f(x) を x=f^-1(y) へ反転(単調区間で線形補間)(invert_funct_1d)。"""
    y = np.asarray(y, float); x = np.arange(len(y))
    order = np.argsort(y)
    return {"x": y[order], "y": x[order].astype(float)}


def transform_funct_1d(y, mult_x=1.0, add_x=0.0, mult_y=1.0, add_y=0.0):
    """1D 関数のアフィン変換(x,y 独立、transform_funct_1d)。(x,y) 対を返す。"""
    y = np.asarray(y, float); x = np.arange(len(y)).astype(float)
    return np.column_stack([mult_x * x + add_x, mult_y * y + add_y])


def x_range_funct_1d(y):
    """関数の x 範囲(min,max)(x_range_funct_1d)。"""
    n = len(np.asarray(y))
    return (0.0, float(n - 1))


def y_range_funct_1d(y):
    """関数の y 範囲(min,max)(y_range_funct_1d)。"""
    y = np.asarray(y, float)
    return (float(y.min()), float(y.max()))


def get_y_value_funct_1d(y, x, interpolate=True):
    """指定 x での y 値(線形補間可)(get_y_value_funct_1d)。"""
    y = np.asarray(y, float)
    if interpolate:
        return float(np.interp(x, np.arange(len(y)), y))
    i = int(np.clip(round(x), 0, len(y) - 1))
    return float(y[i])


def create_funct_1d_array(y):
    """等間隔サンプル配列から 1D 関数を作る(create_funct_1d_array)。"""
    return np.asarray(y, float)


def create_funct_1d_pairs(x, y):
    """(x,y) 対から等間隔 1D 関数へ再標本化(create_funct_1d_pairs)。"""
    x = np.asarray(x, float); y = np.asarray(y, float)
    order = np.argsort(x); x, y = x[order], y[order]
    xi = np.arange(int(np.floor(x.min())), int(np.ceil(x.max())) + 1)
    return np.interp(xi, x, y)


def match_funct_1d_trans(y1, y2):
    """2 つの 1D 関数間の最良シフト(相互相関ピーク)を推定(match_funct_1d_trans)。"""
    a = np.asarray(y1, float) - np.mean(y1); b = np.asarray(y2, float) - np.mean(y2)
    corr = np.correlate(a, b, mode="full")
    shift = corr.argmax() - (len(b) - 1)
    return {"shift": int(shift), "score": float(corr.max())}
