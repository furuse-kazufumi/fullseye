---
op: data_range_of
dim: imgmetrics
category: report
in: image2d
out: scalar
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# data_range_of — IMGMETRICS `report` op

- **データ種**: `image2d` → `scalar`
- **呼び出し**: `import imgmetrics; imgmetrics.data_range_of(*arrays, data_range=None)` (または `opsimgmetrics.get("data_range_of")`)

## 使い方

画素値が取りうる幅を決める。**推測はしない**。

整数 dtype は dtype から一意に決まる。float は ``[0, 1]`` に収まっている
ときだけ 1.0 とみなし、それ以外は ``data_range`` の明示を要求する。

``[0, 1]`` の float を 255 だと思って PSNR を測ると **48.13 dB** ずれるが
例外は出ない ―― それらしい数値が出るだけなので、ここで止める。

Parameters
----------
*arrays : ndarray
    同じ画素値の約束を共有するはずの配列(通常 2 枚)。
data_range : float, optional
    明示する場合の幅。正の有限値でなければ ``ValueError``。

Returns
-------
float

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`report`)

[compare_images](compare_images.md) · [measure_with](measure_with.md) · [metrics_table](metrics_table.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
