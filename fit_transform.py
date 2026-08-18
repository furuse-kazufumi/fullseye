"""対応点からの変換推定(HALCON "Transformations" chapter の genuine 実装, numpy).

点対応から アフィン/剛体/相似 の 2D 同次変換行列を最小二乗で求める。点は (row, col)。
純粋な線形代数 / Umeyama 法=曖昧さのない genuine 実装。
"""
from __future__ import annotations

import numpy as np


def _pts(a):
    return np.asarray(a, dtype=np.float64).reshape(-1, 2)


def vector_to_hom_mat2d(src, dst) -> np.ndarray:
    """対応点から 2D アフィン変換行列(3x3)を最小二乗で求める(vector_to_hom_mat2d)。"""
    s, d = _pts(src), _pts(dst)
    A = np.column_stack([s, np.ones(len(s))])            # [row, col, 1]
    # row', col' を別々に回帰
    cr, *_ = np.linalg.lstsq(A, d[:, 0], rcond=None)
    cc, *_ = np.linalg.lstsq(A, d[:, 1], rcond=None)
    H = np.eye(3)
    H[0] = [cr[0], cr[1], cr[2]]                          # row' = a*row + b*col + c
    H[1] = [cc[0], cc[1], cc[2]]
    return H


def vector_to_rigid(src, dst) -> np.ndarray:
    """対応点から 2D 剛体変換(回転+並進、Kabsch)を求める(vector_to_rigid)。"""
    s, d = _pts(src), _pts(dst)
    sc, dc = s.mean(0), d.mean(0)
    H_ = (s - sc).T @ (d - dc)
    U, _, Vt = np.linalg.svd(H_)
    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[-1] *= -1
        R = Vt.T @ U.T
    t = dc - R @ sc
    M = np.eye(3)
    M[:2, :2] = R
    M[:2, 2] = t
    return M


def vector_to_similarity(src, dst) -> np.ndarray:
    """対応点から 2D 相似変換(回転+スケール+並進、Umeyama)を求める(vector_to_similarity)。"""
    s, d = _pts(src), _pts(dst)
    sc, dc = s.mean(0), d.mean(0)
    sd, dd = s - sc, d - dc
    H_ = sd.T @ dd / len(s)
    U, D, Vt = np.linalg.svd(H_)
    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[-1] *= -1
        R = Vt.T @ U.T
        D = D.copy(); D[-1] *= -1
    var = (sd ** 2).sum() / len(s)
    scale = D.sum() / (var + 1e-12)
    t = dc - scale * R @ sc
    M = np.eye(3)
    M[:2, :2] = scale * R
    M[:2, 2] = t
    return M


def vector_angle_to_rigid(row1, col1, angle1, row2, col2, angle2) -> np.ndarray:
    """1 組の (点, 角度) から 2D 剛体変換を求める(vector_angle_to_rigid)。"""
    dphi = angle2 - angle1
    c, s = np.cos(dphi), np.sin(dphi)
    R = np.array([[c, -s], [s, c]])
    t = np.array([row2, col2]) - R @ np.array([row1, col1])
    M = np.eye(3)
    M[:2, :2] = R
    M[:2, 2] = t
    return M


def hom_vector_to_proj_hom_mat2d(src, dst) -> np.ndarray:
    """4 点以上の対応から射影変換(homography, DLT)3x3 を求める(hom_vector_to_proj_hom_mat2d)。"""
    s, d = _pts(src), _pts(dst)
    A = []
    for (r, c), (r2, c2) in zip(s, d):
        A.append([c, r, 1, 0, 0, 0, -c2 * c, -c2 * r, -c2])
        A.append([0, 0, 0, c, r, 1, -r2 * c, -r2 * r, -r2])
    _, _, Vt = np.linalg.svd(np.asarray(A, float))
    H = Vt[-1].reshape(3, 3)
    return H / (H[2, 2] + 1e-12)
