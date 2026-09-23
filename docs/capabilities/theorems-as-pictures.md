---
id: theorems-as-pictures
title: 定理が門になる図(アポロニウス・フォード・測地ドーム・葉序・IFS・空間充填曲線)
title_en: Theorems as pictures (Apollonian, Ford, geodesic dome, phyllotaxis, IFS, space-filling curves)
category: 描く
ops: [circle_packing_apollonian, ford_circles, phyllotaxis_pattern, neighbour_index_gaps, ifs_fractal, ifs_similarity_dimension, space_filling_curve, curve_locality, geodesic_dome]
examples: [poc_theorems_as_pictures]
version: 0.2.4
---

# 定理が門になる図(アポロニウス・フォード・測地ドーム・葉序・IFS・空間充填曲線)

## できること

数学的に美しい図を描きます —— 互いに接する円の充填、ファレイ数列のフォード円、正二十面体からの測地ドーム、葉序の螺旋、IFS のアトラクタ、空間充填曲線。

★**これらの図はきれいなので、合っているかを誰も確かめません。** 実装が少し間違っていても、円は詰まるし螺旋は回るしフラクタルはフラクタルに見えます。そこでこの層は、**絵とは独立の真値**を必ず持つものだけを入れています(実測):

- ★**デカルトの円定理** —— 接している 4 円は `(Σk)² = 2Σk²`。生成は反射 `k' = 2(k₁+k₂+k₃) − k₄` で行うので、**接触を距離から探し直して**定理に入れると、中心の計算まで一度に効きます。depth 4 の 164 円で、見つかった接触 4 円の組すべてが相対ずれ 1e-13 以下。
- ★**整数充填** —— 種 `(−1, 2, 2, 3)` から始めた充填は**どこまで行っても曲率が整数**(Lagarias–Mallows–Wilks)。実装が少しでもずれれば整数から外れます —— 絵では絶対に見えない種類の誤りです。
- ★**整数の等式 |p·s − q·r| = 1** —— フォード円が接するのはこのときに限ります。こちらは 2 次元の距離を測り、あちらは整数を見る。分母 12 までの 47 円・1,081 組で**不一致 0**。個数もオイラーの関数の和 `1 + Σφ(k)` と一致します。
- ★★**オイラーの公式** —— 測地ドームは、どれだけ細分しても**次数 5 の頂点がちょうど 12 個**。11 個でも 13 個でも球になりません。次数は**既存の別実装**(`conngraph.graph_degree_table`)に数えさせています —— 自分で数え直して自分と一致しても、何も確かめたことになりません。f = 1, 2, 3, 4, 6 すべてで 12、`V − E + F = 2`。
- ★**フィボナッチの斜列** —— 葉序の螺旋は角度をどう選んでも螺旋に見えるので、絵を見ずに近傍の**番号差**を数えます。黄金角では山の **7/7** がフィボナッチ数(8, 13, 21, 34, 55, 89, 144)、対照群の 137.0° では 2/7、90° でも 2/7。
- ★**モランの式と既存 op** —— 相似次元 `Σrᵢᵈ = 1` は**描く前に**解けます。描いた点のほうは既存 `fractal_dimension`(箱数え)が測ります。導出も入力も違うので、一致は偶然では起きません(シェルピンスキーで閉形式 1.5850 / 箱数え 1.6164)。相似でない写像(バーンズリーのシダ)には**使えないと拒否**します。
- **置換であること** —— 空間充填曲線は 4ⁿ 点をちょうど 1 回ずつ通り、隣は必ず距離 1。局所性は主張でなく**表**にします(ヒルベルトは k=32 で 6.38 ≈ √32、走査線は 16.07)。

## What it does

Draw mathematically beautiful figures whose correctness is asserted by a theorem rather than by eye: an Apollonian gasket (every tangent quadruple satisfies Descartes' circle theorem to 1e-13, and an integral seed stays integral for ever), Ford circles (tangency agrees with `|ps - qr| = 1` on all 1,081 pairs, and the count matches `1 + sum of Euler's totient`), a geodesic dome (exactly 12 degree-5 vertices at every subdivision — counted by the existing `graph_degree_table`, not by this module), Vogel's phyllotactic spiral (neighbour index gaps land on Fibonacci numbers only at the golden angle: 7/7 against 2/7 for the controls), IFS attractors (Moran's closed-form dimension agrees with the existing box-counting `fractal_dimension`, and non-similarity maps are refused), and space-filling curves (a permutation of 4^n cells with unit steps; locality reported as a table, not a slogan).

## 向くところ / 向かないところ

**向く**: 数学の図版(記事・教材・表紙)を**採点つき**で作る。空間充填曲線の局所性を根拠つきで比べる(ストレージ配置・タイル順・描画順)。測地ドームを構造や球面サンプリングの下地にする。葉序を点の配り方(ほぼ一様で格子でない)として使う。

**向かない**: アポロニウスの充填は `depth` に対し円が **3 のべき**で増えます(depth 10 で 118,100 個)。フォード円は分母の二乗で半径が縮むので、分母 30 を超えると多くが 1 画素を割ります。IFS のカオスゲームは点を打つので、**細かい隙間は点数を増やさないと埋まりません**(箱数えの次元が閉形式より上に出るのはそのため)。空間充填曲線は `order` に対し 4 のべきで点が増えます(order 10 で 1,048,576 点)。モランの式は**相似写像にしか使えません** —— アフィンだが相似でない写像(シダ)は拒否します。

## 最初の 1 本

```python
import fullseye as fs

# 定理が門になる: 接している 4 円は (Σk)² = 2Σk² を満たす
t = fs.ledger.circle_packing_apollonian(curvatures=(-1, 2, 2, 3), depth=4)
print(len(t["x"]), "円 / 曲率は整数のまま:", abs(t["curvature"] - t["curvature"].round()).max())

# 絵を見ずに斜列を数える(黄金角のときだけフィボナッチ)
pts = fs.ledger.phyllotaxis_pattern(n_points=800)
gaps = fs.ledger.neighbour_index_gaps(pts, k=6)
print("番号差の山:", gaps.argsort()[::-1][:5])
```

## 裏づけ

- op: `circle_packing_apollonian` / `ford_circles` / `phyllotaxis_pattern` / `neighbour_index_gaps` / `ifs_fractal` / `ifs_similarity_dimension` / `space_filling_curve` / `curve_locality` / `geodesic_dome`
- 例: [`poc_theorems_as_pictures`](../../examples/poc_theorems_as_pictures.py)
- 先行: R. Descartes (1643) と F. Soddy, "The kiss precise", *Nature* 137 (1936); J. Lagarias, C. Mallows, A. Wilks, "Beyond the Descartes circle theorem", *Amer. Math. Monthly* 109 (2002); L. R. Ford, "Fractions", *Amer. Math. Monthly* 45 (1938); H. Vogel, "A better way to construct the sunflower head", *Math. Biosci.* 44 (1979); P. A. P. Moran, "Additive functions of intervals and Hausdorff measure", *Proc. Camb. Phil. Soc.* 42 (1946); D. Hilbert (1891) と E. H. Moore (1900)。
