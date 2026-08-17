"""ステレオ/深度の 3D 再構成(HALCON "3D Reconstruction" chapter の genuine core, numpy).

視差 <-> 距離 <-> 3D 点 の幾何変換、行列間変換。実センサ handle でなく純粋な幾何式を本物で実装。
"""
from __future__ import annotations

import numpy as np


def disparity_to_distance(disparity, focal: float = 500.0, baseline: float = 0.1):
    """視差 d を距離 Z = f*baseline/d に変換(disparity_to_distance)。"""
    d = np.asarray(disparity, dtype=np.float64)
    return focal * baseline / np.where(np.abs(d) < 1e-9, np.nan, d)


def distance_to_disparity(distance, focal: float = 500.0, baseline: float = 0.1):
    """距離 Z を視差 d = f*baseline/Z に変換(distance_to_disparity)。"""
    z = np.asarray(distance, dtype=np.float64)
    return focal * baseline / np.where(np.abs(z) < 1e-9, np.nan, z)


def disparity_to_point_3d(row, col, disparity, focal: float = 500.0,
                          baseline: float = 0.1, cx: float = 0.0, cy: float = 0.0):
    """画像点 (row,col) と視差 disparity から 3D 点 (X,Y,Z) を計算(disparity_to_point_3d)。"""
    d = float(disparity)
    if abs(d) < 1e-9:
        return np.array([np.nan, np.nan, np.nan])
    z = focal * baseline / d
    x = (col - cx) * baseline / d
    y = (row - cy) * baseline / d
    return np.array([x, y, z])


def essential_to_fundamental_matrix(E, K1, K2=None) -> np.ndarray:
    """基本行列 F = K2^-T E K1^-1 を本質行列 E から計算(essential_to_fundamental_matrix)。"""
    E = np.asarray(E, dtype=np.float64)
    K1 = np.asarray(K1, dtype=np.float64)
    K2 = K1 if K2 is None else np.asarray(K2, dtype=np.float64)
    return np.linalg.inv(K2).T @ E @ np.linalg.inv(K1)
