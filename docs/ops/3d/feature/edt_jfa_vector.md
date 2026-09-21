---
op: edt_jfa_vector
dim: 3d
category: feature
in: voxel
out: flow_dense
gpu: true
examples: [nearest_seed_partition]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# edt_jfa_vector — 3D `feature` op

- **データ種**: `voxel` → `flow_dense`
- **呼び出し**: `import fullseye as fs; fs.ledger.edt_jfa_vector(seed_bool, device='cpu')` (実装を直接呼ぶなら `import match3d; match3d.edt_jfa_vector(seed_bool, device='cpu')`、台帳から引くなら `ops3d.get("edt_jfa_vector")`)
- **台帳経由の戻り値**: `fullseye.ledger.edt_jfa_vector(...)` は**宣言 out 型 `flow_dense` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.edt_jfa_vector.raw(...)`、または `match3d.edt_jfa_vector` を直接呼ぶ。
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

各 voxel から最近 seed への変位 ``(3, D, H, W)``(``flow_dense``、dz, dy, dx [voxel])を **GPU の JFA** で。

``edt_jfa`` は距離の値だけを返すが、JFA は内部で最近 seed の座標を運んでいる —— それをそのまま出す(追加コストほぼ 0)。
CPU / scipy 経路は ``vol_nearest_seed_vector``(同じ値、N≤160 で厳密一致を実測)。seed が無ければ ValueError
(``edt_jfa`` は 1e6 に飽和させるが、向きに「無限遠」は無い)。返りは torch float32(台帳経由では numpy)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [nearest_seed_partition](../../../../examples_3d/nearest_seed_partition.py) — `py -3.11 examples_3d/nearest_seed_partition.py`

## 型が繋がる次の op(`flow_dense` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`feature`)

[sobel3d](sobel3d.md) · [hessian3d](hessian3d.md) · [curvature_maps](curvature_maps.md) · [edt_jfa](edt_jfa.md) · [vol_frangi](vol_frangi.md) · [vol_local_std](vol_local_std.md) · [vol_local_thickness](vol_local_thickness.md) · [vol_orientation_coherence](vol_orientation_coherence.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
