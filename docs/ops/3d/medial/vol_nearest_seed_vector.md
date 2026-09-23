---
op: vol_nearest_seed_vector
dim: 3d
category: medial
in: voxel
out: flow_dense
examples: [nearest_seed_partition]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# vol_nearest_seed_vector — 3D `medial` op

- **データ種**: `voxel` → `flow_dense`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_nearest_seed_vector(vol_binary, spacing=None)` (実装を直接呼ぶなら `import volops; volops.vol_nearest_seed_vector(vol_binary, spacing=None)`、台帳から引くなら `ops3d.get("vol_nearest_seed_vector")`)

## 使い方

各 voxel から**最近の seed voxel への変位ベクトル** ``(3, D, H, W)``(``flow_dense``、成分 dz, dy, dx [voxel])。

seed = 非零 voxel(``> 0.5`` で二値化)。seed の上では 0。``vol_distance_transform`` が返すのは距離の**値**だけで、
「どの voxel が最近か」は落ちる —— 骨格からの半径(表面 → 骨格の変位)、膜までの肉厚、ESDF の勾配、
ラベルのボロノイ分割はこの**向き**が要る(2026-09-21、コネクトーム基盤の穴)。``spacing`` ``(sz, sy, sx)`` を渡すと
最近傍の判定は物理距離で行う(返す変位は voxel 単位のまま —— ``|v * spacing|`` が物理距離)。
厳密解: Maurer, Qi & Raghavan (IEEE TPAMI 2003) の線形時間 EDT(``scipy.ndimage.distance_transform_edt(return_indices=True)``)。
同距離の seed が複数あるときはその実装の順序で 1 つ(順序に意味を持たせないこと)。seed が 1 つも無いと
ValueError(全 voxel が無限遠 —— 黙って 0 を返さない)。

>>> v = np.zeros((5, 5, 5)); v[2, 2, 0] = 1
>>> d = vol_nearest_seed_vector(v); d.shape, tuple(d[:, 2, 2, 4])
((3, 5, 5, 5), (0.0, 0.0, -4.0))

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [nearest_seed_partition](../../../../examples_3d/nearest_seed_partition.py) — `py -3.11 examples_3d/nearest_seed_partition.py`

## 型が繋がる次の op(`flow_dense` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`medial`)

[distance_ridge](distance_ridge.md) · [skeletonize_vol](skeletonize_vol.md) · [medial_axis_points](medial_axis_points.md) · [topology_signature](topology_signature.md) · [medial_match](medial_match.md) · [skeleton_junctions3d](skeleton_junctions3d.md) · [skeleton_endpoints3d](skeleton_endpoints3d.md) · [skeleton_prune3d](skeleton_prune3d.md)

---
*Provenance: volops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
