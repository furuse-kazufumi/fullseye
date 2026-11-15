---
op: convex_hull_gap
dim: 3d
category: bounds
in: points × points
out: table
gpu: なし
examples: [convex_hull_gap_clearance]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# convex_hull_gap — 3D `bounds` op

- **データ種**: `points × points` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.convex_hull_gap(points_a, points_b, tol: 'float' = 1e-09, max_iter: 'int' = 1000, check: 'str' = 'lp') -> 'Dict[str, object]'` (実装を直接呼ぶなら `import hull3d; hull3d.convex_hull_gap(points_a, points_b, tol: 'float' = 1e-09, max_iter: 'int' = 1000, check: 'str' = 'lp') -> 'Dict[str, object]'`、台帳から引くなら `ops3d.get("convex_hull_gap")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

2 つの頂点集合の凸包どうしの隙間(最短距離)を、保証つきの上下限と一緒に返す。

凸包 conv(A) と conv(B) の距離 ``min ‖a − b‖``(a ∈ conv(A), b ∈ conv(B))は、差の集合
D = {aᵢ − bⱼ} の凸包の中で原点に最も近い点のノルムに等しい。これを **Wolfe (1976) の最小ノルム
点の方法**で解く。D を作らずに ``argmin x·p`` だけを A と B から別々に引く(``A @ x`` の最小と
``B @ x`` の最大)ので、手間は 1 反復 O(N_A + N_B)。Wolfe の方法は有限回で厳密な点に着く
(Frank–Wolfe の O(1/k) の収束ではない)。

止める条件は上下限の差 ``≤ tol``:

* 上限 ``gap_upper = ‖b* − a*‖`` —— a* ∈ conv(A)、b* ∈ conv(B) を重みつきで実際に作った点の距離。
* 下限 ``gap_lower = min_b n·b − max_a n·a`` —— n = (b* − a*)/‖b* − a*‖ の向きの、頂点から直接
  測った**分離の帯の幅**(この幅の帯があることがそのまま「離れている」証明)。

``check="lp"``(既定)では、最小ノルム点と何も共有しない線形計画(scipy の HiGHS)で離れ方を
別に決める: ``‖w‖∞ ≤ 1`` で ``w·a ≤ c ≤ w·b − t`` を満たす最大の t。t > 0 ⇔ 離れていて
``t/√d ≤ 隙間 ≤ t``、t = 0 ⇔ 接するか重なる。2 つの答えが食い違えば RuntimeError(黙って片方を
返さない)。``check="none"`` で線形計画を省く(numpy だけで走る)。

**頂点どうしの距離では重なりを否定できない**(製作の教訓): 細い棒 2 本の十字は、凸包が交わるのに
頂点の間は離れている。hausdorff_distance や最近頂点の距離は「離れている」と出すが、この op は
重なり(``separated = False``)と判定する。

* 非凸の物体(部品・リンクのメッシュ)に直接使うと、**凸包の**重なりを部品の干渉と読み違える。
  凸に分けた部品ごとに使うこと(凸包は物体より大きいので、離れていれば物体も離れている)。
* 重なっているときの**貫通の深さは返さない**(``gap = 0``、``witness_a`` ≈ ``witness_b`` は共通の点)。
* ``gap ≤ tol`` は接触と数える(``separated = False``)。座標は平均を引いてから解く(並進で値が
  変わらない)。2-D の点 (N, 2) にも使える(線形計画の比は √2)。

Parameters
----------
points_a, points_b : array_like (N, 3) または (N, 2)
    凸包の頂点(全点でもよい。凸包を先に作らなくてよい)。次元はそろえる。1 点なら (d,) も可。
tol : float
    上下限の差の許容(座標と同じ単位、既定 1e-9)。> 0。
max_iter : int
    Wolfe の反復(主・副の合計)の上限(既定 1000)。上下限の差が ``tol`` を切る前に届いたら
    RuntimeError(保証の無い近似値を黙って返さない)。
check : {"lp", "none"}
    線形計画の独立な判定を足すか。

Returns
-------
dict
    ``separated`` (bool)、``gap``(離れていれば隙間 = ``gap_upper``、接触・重なりなら 0.0)、
    ``gap_lower``・``gap_upper``(保証つきの下限と上限)、``witness_a``・``witness_b``(最も近い点の組、
    (d,))、``separating_normal``(A から B へ向く単位ベクトル (d,)、離れていなければ None)、
    ``lp_t``(線形計画の t、``check="none"`` なら None)、``iterations``。

Raises
------
ValueError
    形状不正・非有限・次元の不一致・``tol ≤ 0``・``max_iter < 1``・``check`` が未知のとき(fail-closed)。
RuntimeError
    ``max_iter`` までに上下限の差が ``tol`` を切らないとき、線形計画が解けないとき、最小ノルム点と
    線形計画の離れ方の判定が食い違うとき。

空の入力(``points_a`` が 0 要素)は ValueError で拒否する。

English: distance between the convex hulls of two vertex sets by Wolfe's minimum-norm-point method on
the implicit Minkowski difference (finite and exact, not Frank–Wolfe), returned with certified bounds
(an explicit pair of hull points above, a separating slab below). An independent HiGHS LP decides
separation (t > 0 iff disjoint, ``t/sqrt(d) <= gap <= t``); a disagreement raises. Penetration depth
is not computed. Use convex pieces: the hull of a non-convex part over-reports contact.

呼び出し例::

    import numpy as np
    import hull3d
    g = np.array(np.meshgrid([0, 1], [0, 1], [0, 1])).reshape(3, -1).T.astype(float)
    r = hull3d.convex_hull_gap(g, g + [1.25, 0.0, 0.0])            # x に 0.25 離れた単位立方体
    assert r["separated"] and abs(r["gap"] - 0.25) < 1e-12
    rod_a = np.array([[-1.0, -0.01, 0.0], [1.0, -0.01, 0.0], [-1.0, 0.01, 0.0], [1.0, 0.01, 0.0]])
    rod_b = rod_a[:, [1, 0, 2]]                                    # 十字に交わる棒
    assert not hull3d.convex_hull_gap(rod_a, rod_b)["separated"]  # 頂点の間は 1.4 離れている

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [convex_hull_gap_clearance](../../../../examples_3d/convex_hull_gap_clearance.py) — `py -3.11 examples_3d/convex_hull_gap_clearance.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [mesh_select_lod](../resolution/mesh_select_lod.md)

## 同カテゴリ(`bounds`)

[convex_hull](convex_hull.md) · [aabb](aabb.md) · [obb](obb.md) · [min_enclosing_sphere](min_enclosing_sphere.md)

---
*Provenance: hull3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
