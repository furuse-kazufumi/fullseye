---
op: blob_boundaries
dim: blob
category: extract
in: labels2d
out: mask
examples: [poc_gear_tooth_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# blob_boundaries — BLOB `extract` op

- **データ種**: `labels2d` → `mask`
- **呼び出し**: `import blob2d; blob2d.blob_boundaries(labels: 'Any') -> 'np.ndarray'` (または `opsblob.get("blob_boundaries")`)

## 使い方

物体の輪郭(1 画素幅、bool)。**隣り合う物体の境目も残る**。

内側の縁を取る(自分と違うラベルに隣接する前景画素)ので、輪郭は必ず
物体の内部にある —— 外側を取ると隣の物体の画素を輪郭だと言うことになる。

手順: 3x3(8 近傍)のグレー収縮 ``lo`` と膨張 ``hi`` をラベル画像に掛け、
``(labels > 0) & ((lo != labels) | (hi != labels))``。「近傍に自分と違う番号
(背景 0 も含む)がある前景画素」= 内側 1 画素幅の縁。収縮だけだと番号の
小さい物体側の境目が消えるので、膨張も見て対称にしてある。

- ``labels``: 2-D の整数ラベル画像(``blob_label`` の出力)。bool / float / 負の
  番号は ``ValueError``(``blob_region`` と同じ契約)。
- 返り値: ``(H, W)`` の bool。全物体の縁が 1 枚に重なる(物体ごとに分けたいなら
  ``blob_region`` で抜いてから掛ける)。
- 画像の縁に接する物体は、scipy の既定(反射境界)で画像端の外を自分の値と
  みなすため、**画像端に沿った辺は縁として出ない**。
- 1 画素幅の細い物体は全画素が縁になる。

``blob_features`` の周長は別の係数法で測っており、この縁の画素数とは一致しない。
輪郭を折れ線として使うなら ``annotate_outline_layout`` が (x, y) の閉多角形を返す。

## 詳しい使い方ガイド

- [blob_analysis ファミリ ガイド](../guides/blob_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_gear_tooth_metrology](../../../../examples/poc_gear_tooth_metrology.py) — `py -3.11 examples/poc_gear_tooth_metrology.py`

## 型が繋がる次の op(`mask` を入力に取れる)

[blob_label](../connect/blob_label.md) · [blob_distance](../split/blob_distance.md)

## 同カテゴリ(`extract`)

[blob_region](blob_region.md) · [blob_overlay](blob_overlay.md)

---
*Provenance: blob2d.py — BLOB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
