"""decimate_qem_manifold(境界保存・多様体厳格 QEM)のテスト。

回帰の主眼 (2026-08-30): 境界二次形式(重み 1e3)混入で Qsum が中程度に悪条件化した
とき、外れ位置ガードが緩すぎ(10×エッジ長)て「境界保存」の主張が高圧縮比で自壊
していた — 開いた半球のリム頂点が球面半径 1.0 → 0.48 へ崩壊。ガードを 1×へ強化後、
全リム頂点は半径 ≥ 1.0-1e-6 を保つ(placement は球面の外側へは僅かに出得るが、
内側への崩壊は境界保存の否定なので許さない)。
"""
import numpy as np
import pytest

from mesh_decimate import decimate_qem_manifold


def _icosphere(sub=3):
    t = (1 + 5 ** 0.5) / 2
    V = np.array([[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0],
                  [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t],
                  [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], float)
    V /= np.linalg.norm(V, axis=1, keepdims=True)
    F = np.array([[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
                  [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
                  [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
                  [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]], int)
    for _ in range(sub):
        cache = {}
        NV = list(V)
        NF = []

        def mid(a, b, NV=NV, cache=cache):     # bind per iteration (B023)
            k = (min(a, b), max(a, b))
            if k in cache:
                return cache[k]
            m = (NV[a] + NV[b]) / 2
            m = m / np.linalg.norm(m)
            NV.append(m)
            cache[k] = len(NV) - 1
            return cache[k]

        for a, b, c in F:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            NF += [[a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]]
        V = np.array(NV)
        F = np.array(NF, int)
    return V, F


def _open_hemisphere(sub=3):
    V, F = _icosphere(sub)
    keep = np.array([(V[f].mean(0)[2] > 0.05) for f in F])
    Fh = F[keep]
    used = np.unique(Fh)
    remap = -np.ones(len(V), int)
    remap[used] = np.arange(len(used))
    return V[used], remap[Fh]


def test_open_hemisphere_rim_survives_heavy_decimation():
    """Regression: 89% 面削減でも境界(リム)頂点が内側へ崩壊しない。
    修正前は radius min=0.477(悪条件 Qsum の外れ placement を 10× ガードが素通し)。"""
    Vh, Fh = _open_hemisphere(3)
    for target in (71, 150):
        Vd, Fd = decimate_qem_manifold(Vh, Fh, target_faces=target)
        r = np.linalg.norm(Vd, axis=1)
        assert r.min() > 1.0 - 1e-6, \
            f"target={target}: 頂点が球面の内側へ崩壊 (min radius {r.min():.3f})"
        assert len(Fd) <= target + 4          # 目標付近まで実際に削減している


def test_decimated_mesh_stays_edge_manifold():
    """縮約後も非多様体エッジ(3 面以上が共有)を作らない(link condition の実効)。"""
    Vh, Fh = _open_hemisphere(2)
    _Vd, Fd = decimate_qem_manifold(Vh, Fh, target_faces=40)
    edges = {}
    for f in Fd:
        for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
            k = (min(a, b), max(a, b))
            edges[k] = edges.get(k, 0) + 1
    assert max(edges.values()) <= 2


def test_fail_closed_on_bad_input():
    with pytest.raises(ValueError):
        decimate_qem_manifold(np.zeros((0, 3)), np.zeros((0, 3), int), 10)
    with pytest.raises(ValueError):
        decimate_qem_manifold([[0, 0, 0], [1, 0, 0], [0, 1, 0]],
                              [[0, 1, 5]], 10)          # 範囲外インデックス
