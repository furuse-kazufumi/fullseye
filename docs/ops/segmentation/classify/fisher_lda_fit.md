---
op: fisher_lda_fit
dim: segmentation
category: classify
in: matrix × signal
out: table
gpu: なし
examples: [poc_weed_rice_ratio]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# fisher_lda_fit — SEGMENTATION `classify` op

- **データ種**: `matrix × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.fisher_lda_fit(X, y, *, ridge: 'float' = 1e-06, prior1: 'Optional[float]' = None) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import cropweed; cropweed.fisher_lda_fit(X, y, *, ridge: 'float' = 1e-06, prior1: 'Optional[float]' = None) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("fisher_lda_fit")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

2 クラスの Fisher 線形判別を学習する(閉形式。反復なし)。

``X`` は (N, D) の特徴(``superpixel_color_texture_features`` の返りの dict もそのまま渡せる)、
``y`` は 0 / 1 の N 個のクラス。特徴を全体の平均と標準偏差で標準化し(分散 0 の列は尺度 1 のまま
``constant_columns`` に記録)、クラス内の共通共分散 Σ = (S₀ + S₁)/(N − 2) に
``ridge`` × tr(Σ)/D を足してから w = Σ⁻¹(μ₁ − μ₀)。判定の切片は 2 つの等分散正規分布の対数尤度比
w·z − w·(μ₀ + μ₁)/2 + log(π₁/π₀) が 0 になる点(``prior1`` = π₁、既定は学習データの割合)。
返す: ``w``・``bias``(score = z·w + bias、正ならクラス 1)・``mean``・``scale``・``mu0``・``mu1``・
``fisher_ratio``(J = (w·Δμ)²/(wᵀΣw)。分離の強さ)・``n0``・``n1``・``prior1``・``constant_columns``・``cond``。
空の入力・y が 0/1 でない・各クラス 2 個未満・N ≤ 2・共分散の条件数が 1e12 を超える(向きが決まらない)・
2 クラスの平均が同じとき(J = 0)は ``ValueError`` で拒否する。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_weed_rice_ratio](../../../../examples/poc_weed_rice_ratio.py) — `py -3.11 examples/poc_weed_rice_ratio.py`

## 型が繋がる次の op(`table` を入力に取れる)

[class_ndim_norm](class_ndim_norm.md) · [fisher_lda_score](fisher_lda_score.md)

## 同カテゴリ(`classify`)

[class_2dim_sup](class_2dim_sup.md) · [class_2dim_unsup](class_2dim_unsup.md) · [learn_ndim_norm](learn_ndim_norm.md) · [class_ndim_norm](class_ndim_norm.md) · [classify_image_class_lut](classify_image_class_lut.md) · [fisher_lda_score](fisher_lda_score.md)

---
*Provenance: cropweed.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
