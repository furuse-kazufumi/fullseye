---
op: sampson_distance
dim: 3d
category: two_view
in: image2d × image2d
out: signal
examples: [two_view_pose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# sampson_distance — 3D `two_view` op

- **データ種**: `image2d × image2d` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.sampson_distance(F, pts1, pts2)` (実装を直接呼ぶなら `import twoview; twoview.sampson_distance(F, pts1, pts2)`、台帳から引くなら `ops3d.get("sampson_distance")`)

## 使い方

エピポーラ拘束の Sampson 距離(1 次幾何誤差、各対応)。→ (N,)。

Raises ValueError: 点が (N,2) でない/非有限/対応数不一致。

計算: 同次座標 x1=(u1,v1,1)、x2=(u2,v2,1) で ``(x2ᵀ F x1)² / ((F x1)_0² + (F x1)_1² + (Fᵀ x2)_0² + (Fᵀ x2)_1² + 1e-12)``。

- **単位は画素の 2 乗**(距離の 2 乗)。画素で閾値を切るなら ``sqrt`` を取るか、閾値側を 2 乗する。
- F は ``fundamental_8point`` の規約 ``x2ᵀ F x1 = 0``(pts1 → x1、pts2 → x2)。順序を入れ替えるなら F を転置する。
- 分母に 1e-12 を足しているので F=0 でも例外にはならず 0 を返す(F の検査は行わない)。
- 返り値は float64 (N,)。決定論的。(N,2) でない・非有限・点数不一致は ``ValueError``。
- 典型: ``fundamental_8point`` の当てはまり確認、誤対応(大きい値)の選別、``recover_pose`` 前の前処理。

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [two_view_pose](../../../../examples_3d/two_view_pose.py) — `py -3.11 examples_3d/two_view_pose.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`two_view`)

[fundamental_8point](fundamental_8point.md) · [essential_8point](essential_8point.md) · [recover_pose](recover_pose.md) · [triangulate](triangulate.md)

---
*Provenance: twoview.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
