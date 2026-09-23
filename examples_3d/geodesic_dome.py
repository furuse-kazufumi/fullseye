# 測地ドーム — render3d.geodesic_dome
# 実問題: 球面を「ほぼ等しい三角形」で覆いたい(構造物、球面サンプリング、
# 環境マップ、測地格子)。緯度経度の格子は極で密度が破綻するので、正二十面体を
# 細分して球に射影する —— これが測地ドーム(Buckminster Fuller)である。
#
# ★この例の要点は絵ではなく**オイラーの公式**: V − E + F = 2 から、次数 5 の
#   頂点は**どれだけ細分してもちょうど 12 個**になる。11 個でも 13 個でも球には
#   ならない。ここでは次数を **別実装の op**(conngraph.graph_degree_table)に
#   数えさせて確かめる —— 自分で数え直して自分と一致しても、何も確かめたことに
#   ならないため。
#
# repo をそのまま clone した状態でも動くように、リポジトリ直下を import パスへ入れる。
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import numpy as np

import conngraph
import render3d

print("f    V     E      F     次数5  次数6   V-E+F  辺長 min/max")
for freq in (1, 2, 3, 4, 6):
    V, F = render3d.geodesic_dome(frequency=freq)

    # 面から無向の隣接行列を組む(既存 op に次数を数えさせるための入口)
    n = V.shape[0]
    W = np.zeros((n, n), dtype=np.float64)
    for a, b, c in F:
        for i, j in ((a, b), (b, c), (c, a)):
            W[int(i), int(j)] = W[int(j), int(i)] = 1.0

    deg = conngraph.graph_degree_table(W)["in_degree"]
    n5, n6 = int((deg == 5).sum()), int((deg == 6).sum())
    edges = int(W.sum() // 2)
    euler = n - edges + F.shape[0]

    ij = np.argwhere(np.triu(W, 1) > 0)
    lengths = np.linalg.norm(V[ij[:, 0]] - V[ij[:, 1]], axis=1)

    print("%d  %5d %6d %6d   %4d  %5d   %d     %.4f / %.4f"
          % (freq, n, edges, F.shape[0], n5, n6, euler,
             lengths.min(), lengths.max()))

    # --- 門 -------------------------------------------------------------- #
    assert n == 10 * freq * freq + 2, (freq, n)
    assert F.shape[0] == 20 * freq * freq, (freq, F.shape)
    # ★オイラーの公式の帰結。細分しても 12 から動かない。
    assert n5 == 12, ("次数 5 の頂点が %d 個(12 のはず)" % n5)
    assert n6 == n - 12, (freq, n6)
    assert euler == 2, (freq, euler)
    # 射影が効いていること(全頂点が単位球面上)
    assert np.allclose(np.linalg.norm(V, axis=1), 1.0, atol=1e-12)

# 半径と中心を変えても位相は変わらない(幾何だけが動く)
V2, F2 = render3d.geodesic_dome(frequency=3, radius=2.5)
assert np.allclose(np.linalg.norm(V2, axis=1), 2.5, atol=1e-12)

# 半球は切り口を持つので閉じた球ではない(頂点数が減る)
Vh, Fh = render3d.geodesic_dome(frequency=3, hemisphere=True)
assert Vh.shape[0] < V2.shape[0] and Fh.shape[0] < F2.shape[0]
print("半球 f=3: V=%d F=%d(全球は V=%d F=%d)"
      % (Vh.shape[0], Fh.shape[0], V2.shape[0], F2.shape[0]))

print("OK: 次数 5 の頂点はどの分割でもちょうど 12 個(V - E + F = 2)")
