---
op: gray_histo
dim: mv
category: gray
in: image2d
out: table
halcon: gray_histo
gpu: なし
examples: [machine_vision_tour, poc_real_typewritten_ocr]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# gray_histo — MV `gray` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.gray_histo(image, region=None, bins=256)` (実装を直接呼ぶなら `import image_gray; image_gray.gray_histo(image, region=None, bins=256)`、台帳から引くなら `opsmv.get("gray_histo")`)
- **HALCON 相当**: `gray_histo`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

灰色値のヒストグラムを絶対度数と相対度数で返す(gray_histo)。

範囲は ``[0, 1]`` に固定する。範囲の外の画素があると ValueError(``np.histogram`` は外の値を
黙って捨て、8 bit の画像を渡すとほぼ空の表が返るため)。
空の入力(``image`` が 0 要素)は ValueError。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`
- [poc_real_typewritten_ocr](../../../../examples/poc_real_typewritten_ocr.py) — `py -3.11 examples/poc_real_typewritten_ocr.py`

## 型が繋がる次の op(`table` を入力に取れる)

[map_image](../resample/map_image.md) · [rectify_to_world_plane](../resample/rectify_to_world_plane.md) · [change_radial_distortion_image](../resample/change_radial_distortion_image.md) · [find_ncc_models](../detect/find_ncc_models.md) · [run_bg_esti](../tracking/run_bg_esti.md) · [give_bg_esti](../tracking/give_bg_esti.md) · [update_bg_esti](../tracking/update_bg_esti.md) · [classify_class_gmm](../classify/classify_class_gmm.md)

## 同カテゴリ(`gray`)

[atan2_image](atan2_image.md) · [area_center_gray](area_center_gray.md) · [gray_projections](gray_projections.md) · [get_grayval_contour_xld](get_grayval_contour_xld.md)

---
*Provenance: image_gray.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
