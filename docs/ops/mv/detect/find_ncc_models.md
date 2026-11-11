---
op: find_ncc_models
dim: mv
category: detect
in: table × image2d
out: table
halcon: find_ncc_models
gpu: なし
examples: [machine_vision_tour, poc_real_stereo_multiscanline]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# find_ncc_models — MV `detect` op

- **データ種**: `table × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.find_ncc_models(model, image, min_score=0.5, max_matches=10, min_distance=5)` (実装を直接呼ぶなら `import shapematch; shapematch.find_ncc_models(model, image, min_score=0.5, max_matches=10, min_distance=5)`、台帳から引くなら `opsmv.get("find_ncc_models")`)
- **HALCON 相当**: `find_ncc_models`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

1 つまたは複数の NCC モデルを 1 枚の画像から探す(find_ncc_models)。

``model`` がモデルのリストなら全モデルを探し、各一致に ``model``(リストの添字)を付けて
スコアの順に並べ、``min_distance`` より近い一致は強い方だけ残す。一致が無いと ``matches`` が
空で ``num`` が 0 を返す(理由: 見つからないのは正常な結果)。
空の入力(``model`` のリストが 0 要素)は ValueError。

``model`` が 1 つのときは ``min_distance`` を共通検索核へ渡す旧入口のまま。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`
- [poc_real_stereo_multiscanline](../../../../examples/poc_real_stereo_multiscanline.py) — `py -3.11 examples/poc_real_stereo_multiscanline.py`

## 型が繋がる次の op(`table` を入力に取れる)

[map_image](../resample/map_image.md) · [rectify_to_world_plane](../resample/rectify_to_world_plane.md) · [change_radial_distortion_image](../resample/change_radial_distortion_image.md) · [run_bg_esti](../tracking/run_bg_esti.md) · [give_bg_esti](../tracking/give_bg_esti.md) · [update_bg_esti](../tracking/update_bg_esti.md) · [classify_class_gmm](../classify/classify_class_gmm.md) · [evaluate_class_gmm](../classify/evaluate_class_gmm.md)

## 同カテゴリ(`detect`)

[points_lepetit](points_lepetit.md) · [create_ncc_model](create_ncc_model.md)

---
*Provenance: shapematch.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
