---
op: create_bg_esti
dim: mv
category: tracking
in: image2d
out: table
halcon: create_bg_esti
gpu: なし
examples: [machine_vision_tour, poc_real_bg_kalman_tracking]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# create_bg_esti — MV `tracking` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.create_bg_esti(image, process_noise=0.0001, measurement_noise=0.001, threshold=0.1, foreground_gain=0.05)` (実装を直接呼ぶなら `import mvtrack; mvtrack.create_bg_esti(image, process_noise=0.0001, measurement_noise=0.001, threshold=0.1, foreground_gain=0.05)`、台帳から引くなら `opsmv.get("create_bg_esti")`)
- **HALCON 相当**: `create_bg_esti`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

最初の画像から画素ごとのカルマン背景モデルを作る。

各画素の背景はランダムウォークと見なし、過程の雑音 ``process_noise`` と観測の雑音
``measurement_noise`` の分散からゲインが決まる。前景と判定された画素はゲインに
``foreground_gain`` を掛けて弱く更新し、通過する物体を背景に取り込まない。
画素値は **[0, 1] の float**(``threshold`` と雑音の分散も同じ尺度)。整数 dtype の画像と
[0, 1] の外の値は ValueError(uint8 は ``/ 255`` してから渡す)。
空の入力(``image`` が 0 要素)は ValueError。

Args:
    image: 最初の画像 (H, W)。
    process_noise: 過程の雑音の分散(> 0)。
    measurement_noise: 観測の雑音の分散(> 0)。
    threshold: 前景と判定する残差の絶対値(> 0)。
    foreground_gain: 前景の画素のゲイン倍率(0..1)。

Returns:
    背景 ``background`` と分散 ``variance`` を持つモデルの dict。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`
- [poc_real_bg_kalman_tracking](../../../../examples/poc_real_bg_kalman_tracking.py) — `py -3.11 examples/poc_real_bg_kalman_tracking.py`

## 型が繋がる次の op(`table` を入力に取れる)

[map_image](../resample/map_image.md) · [rectify_to_world_plane](../resample/rectify_to_world_plane.md) · [change_radial_distortion_image](../resample/change_radial_distortion_image.md) · [find_ncc_models](../detect/find_ncc_models.md) · [run_bg_esti](run_bg_esti.md) · [give_bg_esti](give_bg_esti.md) · [update_bg_esti](update_bg_esti.md) · [classify_class_gmm](../classify/classify_class_gmm.md)

## 同カテゴリ(`tracking`)

[filter_kalman](filter_kalman.md) · [run_bg_esti](run_bg_esti.md) · [give_bg_esti](give_bg_esti.md) · [update_bg_esti](update_bg_esti.md)

---
*Provenance: mvtrack.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
