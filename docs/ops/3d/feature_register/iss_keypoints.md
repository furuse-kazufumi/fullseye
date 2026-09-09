---
op: iss_keypoints
dim: 3d
category: feature_register
in: points
out: indices
examples: [feature_register]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# iss_keypoints — 3D `feature_register` op

- **データ種**: `points` → `indices`
- **呼び出し**: `import fullseye as fs; fs.ledger.iss_keypoints(points, radius, nms_radius=None, gamma21=0.99, gamma32=0.99, max_kp=400, min_neighbors=8)` (実装を直接呼ぶなら `import feat_shot; feat_shot.iss_keypoints(points, radius, nms_radius=None, gamma21=0.99, gamma32=0.99, max_kp=400, min_neighbors=8)`、台帳から引くなら `ops3d.get("iss_keypoints")`)

## 使い方

ISS(Intrinsic Shape Signatures、3D Harris 相当)キーポイント検出。

局所共分散の最小固有値 λ3 を saliency とし、固有値が distinct(向きが
well-defined)な点のみ候補にして NMS で疎に選ぶ。回転不変。返り値=点 index 配列。

引数:
- ``points`` (N,3)。``radius``: saliency 用の近傍球半径(点群と同じ単位)。
- ``nms_radius``: 非最大抑制の距離。None なら ``0.6*radius``。
- ``gamma21``・``gamma32``: 固有値比 λ2/λ1、λ3/λ2 の上限(既定 0.99)。両方ともこれ
未満の点だけが候補(比が 1 に近い=等方で向きが決まらない点を除く)。
- ``max_kp``: 返す上限。``min_neighbors``: 近傍がこれ未満の点は候補にしない(既定 8)。
手順: 各点で ``radius`` 内の近傍を集め、注目点を原点とした 2 次モーメント行列
``(qᵀq)/n`` の固有値 λ1≥λ2≥λ3 を求める(λ1 が 1e-12 以下なら除外)。λ3 を saliency と
して降順に走査し、採用済みの点から ``nms_radius`` 未満にあるものを捨てる貪欲 NMS。
返り値は int64 の点インデックス配列(saliency 降順)。候補が無ければ長さ 0。
注意: 近傍は注目点で中心化する(重心ではない)ため、平面上の点でも λ3 は厳密には 0 に
ならない。全点で近傍探索する Python ループなので、数万点を超える雲は
``voxel_grid_downsample`` で間引いてから使う。``shot_descriptor`` のキーポイント入力に
直結し、``register_shot`` は内部で ``radius`` の 0.6 倍・NMS 0.3 倍で呼ぶ。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blas_threads_and_memory](../../math/guides/blas_threads_and_memory.md) — 行列分解が遅い理由の知識 — BLAS スレッド・キャッシュ・メモリ配置

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [feature_register](../../../../examples_3d/feature_register.py) — `py -3.11 examples_3d/feature_register.py`

## 型が繋がる次の op(`indices` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`feature_register`)

[harris3d_keypoints](harris3d_keypoints.md) · [compute_fpfh](compute_fpfh.md) · [shot_descriptor](shot_descriptor.md) · [register_spin](register_spin.md) · [register_fpfh](register_fpfh.md) · [register_shot](register_shot.md)

---
*Provenance: feat_shot.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
