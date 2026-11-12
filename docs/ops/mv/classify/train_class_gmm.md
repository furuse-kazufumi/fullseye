---
op: train_class_gmm
dim: mv
category: classify
in: matrix
out: table
halcon: train_class_gmm
gpu: なし
examples: [machine_vision_tour, poc_real_typewritten_ocr, poc_surface_defect_classifiers]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# train_class_gmm — MV `classify` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.train_class_gmm(features, labels, n_centers=1, iterations=100, tol=1e-06, regularize=1e-06, seed=0)` (実装を直接呼ぶなら `import mvclass; mvclass.train_class_gmm(features, labels, n_centers=1, iterations=100, tol=1e-06, regularize=1e-06, seed=0)`、台帳から引くなら `opsmv.get("train_class_gmm")`)
- **HALCON 相当**: `train_class_gmm`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

クラスごとに混合正規分布を EM で学習する。

事前確率はクラスの行数の比。``n_centers=1`` は 2 次判別分析と同じ。
空の入力(``features`` が 0 要素)は ValueError。

Args:
    features: (N, D) の特徴。
    labels: 長さ N のクラス(2 種類以上)。
    n_centers: クラスあたりの成分数(>= 1)。
    iterations: EM の上限回数(>= 1)。
    tol: 対数尤度の相対変化の収束判定。
    regularize: 共分散の対角に足す値(> 0)。
    seed: 初期中心を選ぶ乱数の種。

Returns:
    ``classes``、``priors``、``components`` を持つモデルの dict。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`
- [poc_real_typewritten_ocr](../../../../examples/poc_real_typewritten_ocr.py) — `py -3.11 examples/poc_real_typewritten_ocr.py`
- [poc_surface_defect_classifiers](../../../../examples/poc_surface_defect_classifiers.py) — `py -3.11 examples/poc_surface_defect_classifiers.py`

## 型が繋がる次の op(`table` を入力に取れる)

[map_image](../resample/map_image.md) · [rectify_to_world_plane](../resample/rectify_to_world_plane.md) · [change_radial_distortion_image](../resample/change_radial_distortion_image.md) · [find_ncc_models](../detect/find_ncc_models.md) · [run_bg_esti](../tracking/run_bg_esti.md) · [give_bg_esti](../tracking/give_bg_esti.md) · [update_bg_esti](../tracking/update_bg_esti.md) · [classify_class_gmm](classify_class_gmm.md)

## 同カテゴリ(`classify`)

[classify_class_gmm](classify_class_gmm.md) · [evaluate_class_gmm](evaluate_class_gmm.md) · [train_class_knn](train_class_knn.md) · [classify_class_knn](classify_class_knn.md) · [train_class_mlp](train_class_mlp.md) · [classify_class_mlp](classify_class_mlp.md) · [train_class_svm](train_class_svm.md) · [classify_class_svm](classify_class_svm.md)

---
*Provenance: mvclass.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
