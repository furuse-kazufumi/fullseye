---
op: create_lexicon
dim: mv
category: classify
in: 
out: table
halcon: create_lexicon
gpu: なし
examples: [machine_vision_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# create_lexicon — MV `classify` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.create_lexicon(words)` (実装を直接呼ぶなら `import mvclass; mvclass.create_lexicon(words)`、台帳から引くなら `opsmv.get("create_lexicon")`)
- **HALCON 相当**: `create_lexicon`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

照合に使う語の一覧を作る(重複を除き、順を固定する)。

空の入力(``words`` が 0 要素)は ValueError。

Args:
    words: 文字列の並び。

Returns:
    ``words``(ソートした語のリスト)を持つ dict。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[map_image](../resample/map_image.md) · [rectify_to_world_plane](../resample/rectify_to_world_plane.md) · [change_radial_distortion_image](../resample/change_radial_distortion_image.md) · [find_ncc_models](../detect/find_ncc_models.md) · [run_bg_esti](../tracking/run_bg_esti.md) · [give_bg_esti](../tracking/give_bg_esti.md) · [update_bg_esti](../tracking/update_bg_esti.md) · [classify_class_gmm](classify_class_gmm.md)

## 同カテゴリ(`classify`)

[train_class_gmm](train_class_gmm.md) · [classify_class_gmm](classify_class_gmm.md) · [evaluate_class_gmm](evaluate_class_gmm.md) · [train_class_knn](train_class_knn.md) · [classify_class_knn](classify_class_knn.md) · [train_class_mlp](train_class_mlp.md) · [classify_class_mlp](classify_class_mlp.md) · [train_class_svm](train_class_svm.md)

---
*Provenance: mvclass.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
