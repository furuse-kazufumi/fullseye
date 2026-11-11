---
op: give_bg_esti
dim: mv
category: tracking
in: table
out: image2d
halcon: give_bg_esti
gpu: なし
examples: [machine_vision_tour, poc_real_bg_kalman_tracking]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# give_bg_esti — MV `tracking` op

- **データ種**: `table` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.give_bg_esti(model)` (実装を直接呼ぶなら `import mvtrack; mvtrack.give_bg_esti(model)`、台帳から引くなら `opsmv.get("give_bg_esti")`)
- **HALCON 相当**: `give_bg_esti`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

モデルの現在の背景の画像を返す(コピー)。

空の入力は無い(モデルは ``create_bg_esti`` が必ず 1 画素以上で作る)。形の違う値は ValueError。

Args:
    model: :func:`create_bg_esti` の返り。

Returns:
    背景の float 画像。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`
- [poc_real_bg_kalman_tracking](../../../../examples/poc_real_bg_kalman_tracking.py) — `py -3.11 examples/poc_real_bg_kalman_tracking.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[binocular_disparity_ms](../stereo/binocular_disparity_ms.md) · [binocular_distance_ms](../stereo/binocular_distance_ms.md) · [reconstruct_surface_stereo](../stereo/reconstruct_surface_stereo.md) · [map_image](../resample/map_image.md) · [rectify_to_world_plane](../resample/rectify_to_world_plane.md) · [change_radial_distortion_image](../resample/change_radial_distortion_image.md) · [crop_rectangle2](../resample/crop_rectangle2.md) · [atan2_image](../gray/atan2_image.md)

## 同カテゴリ(`tracking`)

[filter_kalman](filter_kalman.md) · [create_bg_esti](create_bg_esti.md) · [run_bg_esti](run_bg_esti.md) · [update_bg_esti](update_bg_esti.md)

---
*Provenance: mvtrack.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
