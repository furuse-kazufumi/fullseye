---
op: binocular_disparity_ms
dim: mv
category: stereo
in: image2d × image2d
out: table
halcon: binocular_disparity_ms
gpu: なし
examples: [machine_vision_tour, poc_3d_sensor_modalities, poc_real_stereo_multiscanline]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# binocular_disparity_ms — MV `stereo` op

- **データ種**: `image2d × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.binocular_disparity_ms(left, right, max_disp=32, window=5, P1=5.0, P2=50.0, paths=4, lr_tolerance=1.0)` (実装を直接呼ぶなら `import mvstereo; mvstereo.binocular_disparity_ms(left, right, max_disp=32, window=5, P1=5.0, P2=50.0, paths=4, lr_tolerance=1.0)`、台帳から引くなら `opsmv.get("binocular_disparity_ms")`)
- **HALCON 相当**: `binocular_disparity_ms`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

平行化ステレオの視差を半大域マッチングで求め、左右一致で検査して小数へ補間する。

左基準と右基準の視差を ``stereo.disparity_sgm`` で 1 回ずつ計算し、対応点で
``lr_tolerance`` より食い違う画素と参照できない左端の列を無効にする。残りの画素は SAD の
3 点放物線で小数の視差へ補間する。無効の画素は ``disparity`` が NaN になる。
空の入力(``left`` が 0 要素)は ValueError。

Args:
    left: 左の画像 (H, W)。視差はこの画像を基準にする。
    right: 右の画像 (H, W)。
    max_disp: 探す視差の上限(画素、>= 1)。
    window: census と SAD の窓(奇数)。
    P1: 視差 1 の段差の罰則。
    P2: 視差 2 以上の段差の罰則。
    paths: 集約の方向数(2 / 4)。
    lr_tolerance: 左右一致の許容差(画素)。

Returns:
    ``disparity``(float、無効は NaN)、``valid``(bool)、``score``(0..1、大きいほど
    コストの谷が深い)を持つ dict。

出典: H. Hirschmüller, IEEE Trans. PAMI 30(2), 328-341 (2008), doi:10.1109/TPAMI.2007.1166。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`
- [poc_3d_sensor_modalities](../../../../examples/poc_3d_sensor_modalities.py) — `py -3.11 examples/poc_3d_sensor_modalities.py`
- [poc_real_stereo_multiscanline](../../../../examples/poc_real_stereo_multiscanline.py) — `py -3.11 examples/poc_real_stereo_multiscanline.py`

## 型が繋がる次の op(`table` を入力に取れる)

[map_image](../resample/map_image.md) · [rectify_to_world_plane](../resample/rectify_to_world_plane.md) · [change_radial_distortion_image](../resample/change_radial_distortion_image.md) · [find_ncc_models](../detect/find_ncc_models.md) · [run_bg_esti](../tracking/run_bg_esti.md) · [give_bg_esti](../tracking/give_bg_esti.md) · [update_bg_esti](../tracking/update_bg_esti.md) · [classify_class_gmm](../classify/classify_class_gmm.md)

## 同カテゴリ(`stereo`)

[binocular_distance_ms](binocular_distance_ms.md) · [reconstruct_surface_stereo](reconstruct_surface_stereo.md)

---
*Provenance: mvstereo.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
