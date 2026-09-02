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


def _hartley_norm(p: np.ndarray):
    """Hartley 等方正規化: 重心を原点へ、原点からの平均距離を sqrt(2) へ。→ (T (3x3), p_n)。"""
    c = p.mean(0)
    md = float(np.mean(np.linalg.norm(p - c, axis=1)))
    s = np.sqrt(2.0) / md if md > 1e-12 else 1.0
    T = np.array([[s, 0.0, -s * c[0]], [0.0, s, -s * c[1]], [0.0, 0.0, 1.0]])
    return T, (p - c) * s


def hom_vector_to_proj_hom_mat2d(src, dst) -> np.ndarray:
    """4 点以上の対応から射影変換(homography, DLT)3x3 を求める(hom_vector_to_proj_hom_mat2d)。

    本モジュールの契約どおり点は ``(row, col)``: 返る ``H`` は ``(row, col, 1)`` の同次ベクトルに
    左から掛けて ``(row', col', w)`` を与える(``transforms.projective_trans_point_2d(H, row, col)``
    と整合)。数値安定化のため両点集合を Hartley 正規化してから DLT を解き
    ``H = T_dst⁻¹ · H_n · T_src`` で戻す。

    (旧実装は DLT 行を ``(col, row)`` 順で組んでいたため、``(row, col, 1)`` に適用すると
    2 座標を取り違えた行列を返していた — 2026-09-02 実測 max err 27 px。)
    """
    s, d = _pts(src), _pts(dst)
    if len(s) < 4 or len(s) != len(d):
        raise ValueError("hom_vector_to_proj_hom_mat2d needs >= 4 matching (row, col) pairs")
    Ts, sn = _hartley_norm(s)
    Td, dn = _hartley_norm(d)
    A = []
    for (r, c), (r2, c2) in zip(sn, dn):
        A.append([r, c, 1, 0, 0, 0, -r2 * r, -r2 * c, -r2])
        A.append([0, 0, 0, r, c, 1, -c2 * r, -c2 * c, -c2])
    _, _, Vt = np.linalg.svd(np.asarray(A, float))
    Hn = Vt[-1].reshape(3, 3)
    H = np.linalg.inv(Td) @ Hn @ Ts
    if abs(H[2, 2]) > 1e-12:
        H = H / H[2, 2]
    return H
