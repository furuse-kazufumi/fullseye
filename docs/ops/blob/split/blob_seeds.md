---
op: blob_seeds
dim: blob
category: split
in: image2d
out: labels2d
examples: [blob_split_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# blob_seeds — BLOB `split` op

- **データ種**: `image2d` → `labels2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.blob_seeds(distance: 'Any', h: 'float', connectivity: 'int' = 8) -> 'np.ndarray'` (実装を直接呼ぶなら `import blob2d; blob2d.blob_seeds(distance: 'Any', h: 'float', connectivity: 'int' = 8) -> 'np.ndarray'`、台帳から引くなら `opsblob.get("blob_seeds")`)

## 使い方

h-maxima の種。**``h`` は ``distance`` と同じ単位の絶対値**。

「高さ ``h`` 以上そびえている極大」だけを残し、連結成分に番号を振って返す。
融合した塊を割るときの種として使う。

**既存の ``fs.op.xsk2_h_maxima`` と違う点**(``poc_cell_counting`` が
記録した穴):

* あちらは入力を ``[0, 1]`` に**切り詰める**ので、生の距離マップを渡すと
  壊れる(2 px も 20 px も 1.0 になる)。ここは切り詰めない。
* あちらの ``h`` は ``0.05 + 0.3a`` = **正規化画像に対する比**なので、
  画像に大きい物体が 1 つ入るだけで小さい物体側の実効 ``h`` が上がる
  (実測で下限が 0.42 → 0.80 px へ動いた)。ここは画素(または物理単位)。

**速さ**: 再構成は**連結成分ごとの外接箱の中でだけ**回す。背景を通る
伝播が消えるので、512x512 に 200 個の円で **237.7 ms → 15.3 ms(15.5 倍)**、
結果は全画素一致(2026-09-06 実測)。

Parameters
----------
distance : array_like
    2-D の実数場。ふつうは :func:`blob_distance` の出力。
h : float
    そびえの高さ。``distance`` と同じ単位で、**0 より大きいこと**。
    大きくすると種が減る(= 割りすぎが減り、割り残しが増える)。
connectivity : {4, 8}
    極大の連結の取り方。

Returns
-------
numpy.ndarray
    ``int32`` のラベル画像(背景 0、種 1..n)。

## 詳しい使い方ガイド

- [blob_analysis ファミリ ガイド](../guides/blob_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [blob_split_tour](../../../../examples/blob_split_tour.py) — `py -3.11 examples/blob_split_tour.py`

## 型が繋がる次の op(`labels2d` を入力に取れる)

[blob_features](../measure/blob_features.md) · [blob_select](../select/blob_select.md) · [blob_select_largest](../select/blob_select_largest.md) · [blob_split](blob_split.md) · [blob_region](../extract/blob_region.md) · [blob_boundaries](../extract/blob_boundaries.md) · [blob_overlay](../extract/blob_overlay.md)

## 同カテゴリ(`split`)

[blob_distance](blob_distance.md) · [blob_split](blob_split.md)

---
*Provenance: blob2d.py — BLOB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
