---
op: gen_nurbs_interp
dim: mv
category: curve
in: keypoints
out: table
halcon: gen_nurbs_interp
gpu: なし
examples: [machine_vision_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# gen_nurbs_interp — MV `curve` op

- **データ種**: `keypoints` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.gen_nurbs_interp(points, degree=3)` (実装を直接呼ぶなら `import mvtext; mvtext.gen_nurbs_interp(points, degree=3)`、台帳から引くなら `opsmv.get("gen_nurbs_interp")`)
- **HALCON 相当**: `gen_nurbs_interp`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

点列を全部通る非有理 B スプラインの制御点を求める(大域補間)。

媒介変数は弦長、節点は媒介変数の平均(The NURBS Book の 9.2.1)で決め、基底の線形方程式を
解く。重みは全部 1 なので、返りをそのまま ``nurbs_curve`` に渡せる(``knots`` と ``degree``
も一緒に渡す)。連続する同じ点は ValueError(弦長が 0 になり媒介変数が決まらない)。
空の入力(``points`` が 0 要素)は ValueError。

Args:
    points: (N, d) の点列(N > degree)。
    degree: 次数(>= 1)。

Returns:
    ``control_points`` (N, d)、``knots`` (N+degree+1,)、``weights``、``degree``、``u`` を持つ dict。

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

## 同カテゴリ(`curve`)

—

---
*Provenance: mvtext.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
