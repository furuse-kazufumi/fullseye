---
op: shape_mahalanobis
dim: shapestat
category: model
in: shapemodel × points
out: measurement
examples: [shapestat_landmark_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# shape_mahalanobis — SHAPESTAT `model` op

- **データ種**: `shapemodel × points` → `measurement`
- **呼び出し**: `import shapestats; shapestats.shape_mahalanobis(model, shape, align: 'bool' = True, cumulative: 'float' = 0.99, n_modes: 'int' = 0)` (または `opsshapestat.get("shape_mahalanobis")`)

## 使い方

モデルから見てその形がどれだけ**異常**か。→ float。

``sqrt(sum(score_i^2 / variance_i))`` を**先頭の何本かに限って**足す。

★ **全成分を足してはいけない。** K 個体の群から出る主成分は K-1 本だが、
後ろのほうは分散が数値的なゼロまで落ちる。実測(K=12、N=80、真のモードは
2 本)の分散: ``3.2e-02, 5.6e-03, 4.0e-05, 6.7e-13, 9.7e-14, 9.9e-17, …,
1.0e-31``。この裾で割ると値が意味を失う:

==========  ===========  ==================
使う本数    群内の個体   0.5 の膨らみを注入
==========  ===========  ==================
1                 0.428               1.821
2                 0.885               2.617
3                 1.035              18.134
5                 1.373        1393035.060
11(全部)      46613.636       9.3e+13
==========  ===========  ==================

5 本で群内の個体が 1.37 なのに外れが 100 万、11 本では**群内ですら 46614**。
「異常度」ではなく「数値ゼロで割った回数」を測っている。

そこで既定は**累積寄与率 ``cumulative``(0.99)までの成分だけ**を使う。
上の群では 2 本(0.99895)が選ばれ、群内 0.885 / 外れ 2.617 と素直に並ぶ。
``n_modes`` を正の数で与えればその本数に固定する(比較のため本数を揃えたい
ときに使う)。**どちらを使ったかで値が変わる**ので、報告するときは本数も一緒に。

## 詳しい使い方ガイド

- [shape_statistics ファミリ ガイド](../guides/shape_statistics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shapestat_landmark_tour](../../../../examples/shapestat_landmark_tour.py) — `py -3.11 examples/shapestat_landmark_tour.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`model`)

[shape_pca](shape_pca.md) · [shape_project](shape_project.md) · [shape_reconstruct](shape_reconstruct.md) · [shape_explained_variance](shape_explained_variance.md) · [shape_synthesize](shape_synthesize.md)

---
*Provenance: shapestats.py — SHAPESTAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
