---
op: roughness_map
dim: drive
category: walkterrain
in: depth
out: image2d
gpu: なし
examples: [walking_ops_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# roughness_map — DRIVE `walkterrain` op

- **データ種**: `depth` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.roughness_map(grid, window: 'int' = 3)` (実装を直接呼ぶなら `import terrain; terrain.roughness_map(grid, window: 'int' = 3)`、台帳から引くなら `opsdrive.get("roughness_map")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Per-cell surface roughness = local height standard deviation over a
``window`` neighbourhood. High on rubble / vegetation, ~0 on smooth ground.

★``dem_roughness``(Riley 1999 の TRI = 8 近傍との差の二乗平均平方根、近傍 1 セル固定)
とは**別の量**なので別の op として残す: こちらは窓の中の標準偏差(中心を含む、窓の幅が
つまみ)。傾き a の平面では ``a·cell·√(2/3)`` と TRI の ``a·cell·√(3/4)`` で、乱れた地形
では TRI の約 0.7 倍(実測の中央値)。:func:`foothold_score` の粗さの項はこの量。
空の入力(``grid`` が 0 要素)は形を保った空の配列を返す(理由: 観測の無い地図は形を保った空の地図で、どの格子も測っていない)。
A different quantity from ``dem_roughness`` (TRI): a windowed standard deviation.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [walking_ops_tour](../../../../examples/walking_ops_tour.py) — `py -3.11 examples/walking_ops_tour.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [ttc_from_flow](../ttc/ttc_from_flow.md) · [foe_from_flow](../ttc/foe_from_flow.md) · [perlin2](../terrain/perlin2.md) · [fbm_height](../terrain/fbm_height.md) · [fbm_gradient](../terrain/fbm_gradient.md) · [radial_periodogram](../terrain/radial_periodogram.md)

## 同カテゴリ(`walkterrain`)

[elevation_map](elevation_map.md) · [fill_gaps](fill_gaps.md) · [elevation_traversability](elevation_traversability.md) · [foothold_score](foothold_score.md) · [ground_surface](ground_surface.md) · [ground_plane](ground_plane.md) · [detect_obstacles](detect_obstacles.md) · [fuse_elevation](fuse_elevation.md)

---
*Provenance: terrain.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
