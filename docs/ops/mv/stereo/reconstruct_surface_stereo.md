---
op: reconstruct_surface_stereo
dim: mv
category: stereo
in: image2d
out: points
halcon: reconstruct_surface_stereo
gpu: なし
examples: [machine_vision_tour, poc_real_stereo_multiscanline]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# reconstruct_surface_stereo — MV `stereo` op

- **データ種**: `image2d` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.reconstruct_surface_stereo(disparity, focal=500.0, baseline=0.1, cx=0.0, cy=0.0)` (実装を直接呼ぶなら `import reconstruction; reconstruction.reconstruct_surface_stereo(disparity, focal=500.0, baseline=0.1, cx=0.0, cy=0.0)`、台帳から引くなら `opsmv.get("reconstruct_surface_stereo")`)
- **HALCON 相当**: `reconstruct_surface_stereo`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

視差画像の有効な画素を 3-D の点へ写す(reconstruct_surface_stereo)。

``Z = focal * baseline / d``、``X = (col - cx) * baseline / d``、``Y = (row - cy) * baseline / d``。
NaN と inf と 0 の視差は無効として落とす。有効な画素が無いと (0, 3) の空を返す(理由: 無効の
画素は点を作らない)。空の入力(``disparity`` が 0 要素)は ValueError。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`
- [poc_real_stereo_multiscanline](../../../../examples/poc_real_stereo_multiscanline.py) — `py -3.11 examples/poc_real_stereo_multiscanline.py`

## 型が繋がる次の op(`points` を入力に取れる)

—

## 同カテゴリ(`stereo`)

[binocular_disparity_ms](binocular_disparity_ms.md) · [binocular_distance_ms](binocular_distance_ms.md)

---
*Provenance: reconstruction.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
