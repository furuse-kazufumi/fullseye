---
op: binocular_distance_ms
dim: mv
category: stereo
in: image2d × image2d
out: table
halcon: binocular_distance_ms
gpu: なし
examples: [machine_vision_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# binocular_distance_ms — MV `stereo` op

- **データ種**: `image2d × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.binocular_distance_ms(left, right, focal, baseline, doffs=0.0, max_disp=32, window=5, P1=5.0, P2=50.0, paths=4, lr_tolerance=1.0)` (実装を直接呼ぶなら `import mvstereo; mvstereo.binocular_distance_ms(left, right, focal, baseline, doffs=0.0, max_disp=32, window=5, P1=5.0, P2=50.0, paths=4, lr_tolerance=1.0)`、台帳から引くなら `opsmv.get("binocular_distance_ms")`)
- **HALCON 相当**: `binocular_distance_ms`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

平行化ステレオの距離画像を求める(``Z = focal * baseline / (disparity + doffs)``)。

視差は :func:`binocular_disparity_ms` の値をそのまま使う。無効の画素と、視差が 0 以下で
距離の決まらない画素は ``distance`` が NaN になる。
空の入力(``left`` が 0 要素)は ValueError。

Args:
    left: 左の画像 (H, W)。
    right: 右の画像 (H, W)。
    focal: 焦点距離(画素、> 0)。
    baseline: 基線長(距離の単位がこの単位になる、> 0)。
    doffs: 主点の差 ``cx_right - cx_left``(画素)。
    max_disp: 探す視差の上限。
    window: census と SAD の窓(奇数)。
    P1: 視差 1 の段差の罰則。
    P2: 視差 2 以上の段差の罰則。
    paths: 集約の方向数(2 / 4)。
    lr_tolerance: 左右一致の許容差(画素)。

Returns:
    ``distance``(無効は NaN)、``disparity``、``valid``、``score`` を持つ dict。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[map_image](../resample/map_image.md) · [rectify_to_world_plane](../resample/rectify_to_world_plane.md) · [change_radial_distortion_image](../resample/change_radial_distortion_image.md) · [find_ncc_models](../detect/find_ncc_models.md) · [run_bg_esti](../tracking/run_bg_esti.md) · [give_bg_esti](../tracking/give_bg_esti.md) · [update_bg_esti](../tracking/update_bg_esti.md) · [classify_class_gmm](../classify/classify_class_gmm.md)

## 同カテゴリ(`stereo`)

[binocular_disparity_ms](binocular_disparity_ms.md) · [reconstruct_surface_stereo](reconstruct_surface_stereo.md)

---
*Provenance: mvstereo.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
