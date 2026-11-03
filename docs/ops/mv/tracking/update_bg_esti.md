---
op: update_bg_esti
dim: mv
category: tracking
in: table × image2d × mask
out: table
halcon: update_bg_esti
gpu: なし
examples: [machine_vision_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# update_bg_esti — MV `tracking` op

- **データ種**: `table × image2d × mask` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.update_bg_esti(model, image, update_region)` (実装を直接呼ぶなら `import mvtrack; mvtrack.update_bg_esti(model, image, update_region)`、台帳から引くなら `opsmv.get("update_bg_esti")`)
- **HALCON 相当**: `update_bg_esti`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

指定した領域の画素だけ、画像で背景を更新する(領域の外は分散も動かない)。

空の入力(``image`` が 0 要素)は ValueError。

Args:
    model: :func:`create_bg_esti` の返り。
    image: 現在の画像(モデルと同じ形)。
    update_region: 更新する画素の bool 配列(同じ形)。

Returns:
    更新後のモデルの dict。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[map_image](../resample/map_image.md) · [rectify_to_world_plane](../resample/rectify_to_world_plane.md) · [change_radial_distortion_image](../resample/change_radial_distortion_image.md) · [find_ncc_models](../detect/find_ncc_models.md) · [run_bg_esti](run_bg_esti.md) · [give_bg_esti](give_bg_esti.md) · [classify_class_gmm](../classify/classify_class_gmm.md) · [evaluate_class_gmm](../classify/evaluate_class_gmm.md)

## 同カテゴリ(`tracking`)

[filter_kalman](filter_kalman.md) · [create_bg_esti](create_bg_esti.md) · [run_bg_esti](run_bg_esti.md) · [give_bg_esti](give_bg_esti.md)

---
*Provenance: mvtrack.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
