"""行列演算(HALCON "Matrix" chapter の genuine 実装, numpy 線形代数).

生成・算術・要素演算・分解・固有値・solve。純粋な線形代数=曖昧さのない genuine 実装。
HALCON の "_mod"(in-place)版は関数的には同結果ゆえ同一実装へマップ。行列は 2D numpy。
"""
from __future__ import annotations

import numpy as np


def _m(a):
    return np.asarray(a, dtype=np.float64)


def create_matrix(rows: int, cols: int, value=0.0):
    return np.full((int(rows), int(cols)), float(value))


def transpose_matrix(M):
    return _m(M).T


def invert_matrix(M):
    return np.linalg.inv(_m(M))


def mult_matrix(A, B):
    return _m(A) @ _m(B)


def add_matrix(A, B):
    return _m(A) + _m(B)


def sub_matrix(A, B):
    return _m(A) - _m(B)


def scale_matrix(M, factor=1.0):
    return _m(M) * float(factor)


def mult_element_matrix(A, B):
    return _m(A) * _m(B)


def div_element_matrix(A, B):
    return _m(A) / _m(B)


def pow_element_matrix(M, p=2.0):
    return np.power(_m(M), float(p))


def pow_scalar_element_matrix(M, base=2.0):
    return np.power(float(base), _m(M))


def pow_matrix(M, p=2):
    return np.linalg.matrix_power(_m(M), int(p))


def abs_matrix(M):
    return np.abs(_m(M))


def sqrt_matrix(M):
    return np.sqrt(np.clip(_m(M), 0, None))


def determinant_matrix(M) -> float:
    return float(np.linalg.det(_m(M)))


def norm_matrix(M, ord=None) -> float:
    return float(np.linalg.norm(_m(M), ord=ord))


def solve_matrix(A, b):
    return np.linalg.solve(_m(A), _m(b))


def svd_matrix(M):
    U, S, Vt = np.linalg.svd(_m(M), full_matrices=False)
    return {"U": U, "S": S, "V": Vt.T}


def eigenvalues_general_matrix(M):
    w = np.linalg.eigvals(_m(M))
    return {"real": w.real, "imag": w.imag}


def eigenvalues_symmetric_matrix(M):
    return np.linalg.eigvalsh(_m(M))


def generalized_eigenvalues_general_matrix(A, B):
    from scipy.linalg import eig
    w = eig(_m(A), _m(B), right=False)
    return {"real": np.real(w), "imag": np.imag(w)}


def generalized_eigenvalues_symmetric_matrix(A, B):
    from scipy.linalg import eigh
    return eigh(_m(A), _m(B), eigvals_only=True)


def decompose_matrix(M):
    """LU 分解(P,L,U)を返す(decompose_matrix)。"""
    from scipy.linalg import lu
    P, L, U = lu(_m(M))
    return {"P": P, "L": L, "U": U}


def orthogonal_decompose_matrix(M):
    """QR 直交分解を返す(orthogonal_decompose_matrix)。"""
    Q, R = np.linalg.qr(_m(M))
    return {"Q": Q, "R": R}


def get_diagonal_matrix(M):
    return np.diag(_m(M))


def set_diagonal_matrix(M, vec):
    out = _m(M).copy()
    np.fill_diagonal(out, _m(vec))
    return out


def get_sub_matrix(M, row=0, col=0, rows=1, cols=1):
    M = _m(M)
    return M[int(row):int(row) + int(rows), int(col):int(col) + int(cols)]


def set_sub_matrix(M, sub, row=0, col=0):
    out = _m(M).copy()
    s = _m(sub)
    out[int(row):int(row) + s.shape[0], int(col):int(col) + s.shape[1]] = s
    return out


def sum_matrix(M, axis=None):
    return np.asarray(_m(M).sum(axis=axis))


def mean_matrix(M, axis=None):
    return np.asarray(_m(M).mean(axis=axis))


def min_matrix(M, axis=None):
    return np.asarray(_m(M).min(axis=axis))


def max_matrix(M, axis=None):
    return np.asarray(_m(M).max(axis=axis))


def repeat_matrix(M, ry=1, rc=1):
    return np.tile(_m(M), (int(ry), int(rc)))
