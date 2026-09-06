---
op: shape_pca
dim: shapestat
category: model
in: shapeset
out: shapemodel
examples: [shapestat_landmark_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# shape_pca — SHAPESTAT `model` op

- **データ種**: `shapeset` → `shapemodel`
- **呼び出し**: `import shapestats; shapestats.shape_pca(shapes, n_components: 'int' = 0, align: 'bool' = True)` (または `opsshapestat.get("shape_pca")`)

## 使い方

形態 PCA(統計形状モデル)。→ dict(``shapemodel``)。

返す辞書: ``mean`` ``(N,3)`` / ``components`` ``(k, N*3)`` / ``variance``
``(k,)`` / ``n_points`` / ``total_variance`` / ``aligned`` ``(K,N,3)``。

``n_components=0``(既定)は ``min(K-1, N*3)`` 本すべて。
``align=True`` なら先に :func:`generalized_procrustes` を掛ける
(揃えずに PCA を取ると、第 1 主成分が「位置の違い」になって形の話が消える)。

★ **分散は標本分散(``K-1`` で割る)**。K が小さいと固有値は系統的に大きく
出る。個体数が二桁に届かないうちは、固有値そのものより**比**を見ること。

★★ **``align=True`` は「大きさの違い」も消すので、大きさに近いモードの分散を
食う。** :func:`shape_synth_family` は第 1 モードを「長軸の伸び縮み」、第 2 を
「曲げ」にしてあり、重みの比は 0.30 : 0.12 なので**分散比の真値は 6.25**。
実測(K=40、N=80、seed=7):

==========================  ==========  ======================
前処理                      分散比      寄与率(第 1 / 第 2)
==========================  ==========  ======================
``align=False``                  6.981        0.8747 / 0.1253
GPA(``scaling=False``)          6.981        0.8747 / 0.1253
``align=True``(既定)            2.565        0.7188 / 0.2803
==========================  ==========  ======================

伸びは一様拡大とよく似ているので、Procrustes のスケール除去がその半分以上を
持っていく。**間違いではなく定義の帰結** —— 「大きさを形質に数えるか」を
先に決めていないと、同じデータから違う主成分が出る。成長や体格差を形の話に
含めたいなら ``align=False``(または ``generalized_procrustes(scaling=False)``
を通してから ``align=False``)にすること。

## 詳しい使い方ガイド

- [shape_statistics ファミリ ガイド](../guides/shape_statistics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shapestat_landmark_tour](../../../../examples/shapestat_landmark_tour.py) — `py -3.11 examples/shapestat_landmark_tour.py`

## 型が繋がる次の op(`shapemodel` を入力に取れる)

[shape_project](shape_project.md) · [shape_reconstruct](shape_reconstruct.md) · [shape_mahalanobis](shape_mahalanobis.md) · [shape_explained_variance](shape_explained_variance.md) · [shape_synthesize](shape_synthesize.md)

## 同カテゴリ(`model`)

[shape_project](shape_project.md) · [shape_reconstruct](shape_reconstruct.md) · [shape_mahalanobis](shape_mahalanobis.md) · [shape_explained_variance](shape_explained_variance.md) · [shape_synthesize](shape_synthesize.md)

---
*Provenance: shapestats.py — SHAPESTAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
