---
op: shape_index
dim: 3d
category: curvature
in: points
out: descriptor
examples: [curvature_grasp, itokawa_curvature]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# shape_index — 3D `curvature` op

- **データ種**: `points` → `descriptor`
- **呼び出し**: `import fullseye as fs; fs.ledger.shape_index(points, k=25, normals=None)` (実装を直接呼ぶなら `import curvature3d; curvature3d.shape_index(points, k=25, normals=None)`、台帳から引くなら `ops3d.get("shape_index")`)

## 使い方

Koenderink の shape index s∈[-1,1] (凸球+1・円柱+0.5・鞍点0・凹球-1)。→ (N,)。

umbilic/平面判定は**曲率スケール相対**(絶対しきい値なし)。緩やかな凸/凹(曲率が微小でも)は
符号=凹凸を保ち、平面はデータ全体の曲率スケールに対して相対的に 0 の点のみ s=0 とする。

normals(向き付き参照法線, (N,3))未指定時は開面の凹/凸符号が不定(凸マグニチュードで報告)。
向き付き法線を渡すと大域向きに整合し正しい符号(凹球=cup → -1)を出す。

計算(各点、``principal_curvatures`` と同じフィット):
- 平面判定: curvedness ``sqrt((k1² + k2²) / 2)`` が、全点の curvedness の中央値 × 1e-3 未満なら s = 0。中央値が 0(曲率信号なし)なら全点 0。
- 臍点判定: ``|k1 - k2| < 1e-2 × (|k1| + |k2|)`` なら s = ``sign(k1 + k2)``(厳密に ±1)。
- それ以外: ``s = (2/π) · arctan((k1 + k2) / (k1 - k2))``。

- しきい値は絶対値でなく **データ全体の曲率スケール相対** なので、同じ形でも他の点との混在具合で平面扱いになる点が変わる。単一の点群を分類する前提で使う。
- 近傍が 5 点未満の点は k1 = k2 = 0 → 平面(0)。``k`` は N-1 に切り詰め。
- ``normals`` は (N,3) で有限かつ非ゼロ行(``ValueError``)。未指定では開いた面の符号は不定(凸側)。
- 曲がりの強さは含まない。強さも要るなら ``principal_curvatures`` の 2 本を ``(N,2)`` に並べて ``curvature_to_shape_index`` に通す。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blas_threads_and_memory](../../math/guides/blas_threads_and_memory.md) — 行列分解が遅い理由の知識 — BLAS スレッド・キャッシュ・メモリ配置

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [curvature_grasp](../../../../examples_3d/curvature_grasp.py) — `py -3.11 examples_3d/curvature_grasp.py`
- [itokawa_curvature](../../../../examples_3d/itokawa_curvature.py) — `py -3.11 examples_3d/itokawa_curvature.py`

## 型が繋がる次の op(`descriptor` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [shape_distance](../shape_descriptor/shape_distance.md)

## 同カテゴリ(`curvature`)

[principal_curvatures](principal_curvatures.md) · [mean_curvature](mean_curvature.md) · [gaussian_curvature](gaussian_curvature.md) · [estimate_normals](estimate_normals.md)

---
*Provenance: curvature3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
