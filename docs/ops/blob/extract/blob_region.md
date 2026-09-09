---
op: blob_region
dim: blob
category: extract
in: labels2d
out: mask
examples: [poc_gear_tooth_metrology, poc_particle_sizing]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# blob_region — BLOB `extract` op

- **データ種**: `labels2d` → `mask`
- **呼び出し**: `import fullseye as fs; fs.ledger.blob_region(labels: 'Any', index: 'int') -> 'np.ndarray'` (実装を直接呼ぶなら `import blob2d; blob2d.blob_region(labels: 'Any', index: 'int') -> 'np.ndarray'`、台帳から引くなら `opsblob.get("blob_region")`)

## 使い方

物体 1 個を二値領域(bool)として抜く。``index`` は **1 起点**。

``labels == index`` を返すだけの選択 op。番号は ``blob_label`` が付けた 1..n の
連番で、0 は背景。

- ``labels``: 2-D の整数ラベル画像(``blob_label`` / ``blob_select`` /
  ``blob_split`` の出力)。**bool マスクは拒否**(「複数物体を 1 個として測る」
  事故を防ぐため、先に ``blob_label`` を掛けるよう促す)。float も拒否
  (``0.999`` がどの物体か決められない)。負の番号があれば ``ValueError``。
- ``index``: ``1 <= index <= labels.max()`` の int。0(背景)や範囲外は
  ``ValueError``。``blob_features`` の ``label`` 列、``blob_select_largest`` の
  結果(1 から振り直される)と同じ番号体系。
- 返り値: ``(H, W)`` の bool。空になることはない(番号は必ず存在する
  ―― ただし ``blob_select`` で番号を振り直していない自作ラベルに欠番があれば
  全 False が返りうる)。

抜いた領域は ``blob_distance``(距離変換)や ``blob_overlay`` の重ね描き、
``annotate_outline`` の輪郭描画にそのまま渡せる。

## 詳しい使い方ガイド

- [blob_analysis ファミリ ガイド](../guides/blob_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_gear_tooth_metrology](../../../../examples/poc_gear_tooth_metrology.py) — `py -3.11 examples/poc_gear_tooth_metrology.py`
- [poc_particle_sizing](../../../../examples/poc_particle_sizing.py) — `py -3.11 examples/poc_particle_sizing.py`

## 型が繋がる次の op(`mask` を入力に取れる)

[blob_label](../connect/blob_label.md) · [blob_distance](../split/blob_distance.md)

## 同カテゴリ(`extract`)

[blob_boundaries](blob_boundaries.md) · [blob_overlay](blob_overlay.md)

---
*Provenance: blob2d.py — BLOB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
