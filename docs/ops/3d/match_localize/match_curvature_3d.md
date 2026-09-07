---
op: match_curvature_3d
dim: 3d
category: match_localize
in: voxel × voxel
out: position
gpu: true
examples: [matching_localize]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# match_curvature_3d — 3D `match_localize` op

- **データ種**: `voxel × voxel` → `position`
- **呼び出し**: `import fullseye as fs; fs.ledger.match_curvature_3d(scene, template, device='cpu', mc=0.000625, subvoxel=True)` (実装を直接呼ぶなら `import match3d; match3d.match_curvature_3d(scene, template, device='cpu', mc=0.000625, subvoxel=True)`、台帳から引くなら `ops3d.get("match_curvature_3d")`)
- **台帳経由の戻り値**: `fullseye.ledger.match_curvature_3d(...)` は**宣言 out 型 `position` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.match_curvature_3d.raw(...)`、または `match3d.match_curvature_3d` を直接呼ぶ。
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

曲率(shape index)マッチング。voxel × 曲率列(線→面リフトの本丸)。

scene/template を **curvedness で重み付けした shape-index 場**へ変換 → 既存 3D NCC で定位。
強度でなく **局所曲面形状**で一致を測るため、同じ強度でも形が違う対象(球 vs 円柱/鞍点)を
区別できる。S は回転不変なので回転にもある程度頑健。返り値 [score, d, h, w]。

手順: 両 volume で ``curvature_maps`` → ``S × curvedness × mask`` の重み付き shape-index 場
``w`` を作り、テンプレ側は ``|w| > 0.1·max|w|`` の bbox を切り出して
``accel_match.ncc_locate_3d`` に渡す。返り値 ``[NCC, z, y, x]`` float64、NCC ∈ [−1, 1]。
- **位置は切り出した bbox テンプレの中心**が scene に載る座標。元テンプレ volume の中心とは
bbox のオフセット分ずれる(元テンプレ座標に戻すには bbox の lo を足し直す)。
- ``mc``: ``curvature_maps`` の勾配マスク閾値(真の勾配単位、voxel あたり)。平坦部を除いて
曲率ノイズを抑える。
- テンプレの曲率場が全 0(平坦・``mc`` が高すぎ)なら ``[0,0,0,0]`` を返す。
- 曲率は 2 階微分なのでノイズに敏感。ノイズが多い volume は先に ``points_to_voxel`` の
``smooth`` 等で滑らかにする。
``subvoxel=True`` で NCC ピークの ±2 近傍重心に精緻化。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [matching_localize](../../../../examples_3d/matching_localize.py) — `py -3.11 examples_3d/matching_localize.py`

## 型が繋がる次の op(`position` を入力に取れる)

[refine_peak_newton](../refine/refine_peak_newton.md) · [refine_translation_lk](../refine/refine_translation_lk.md) · [refine_lm](../refine/refine_lm.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`match_localize`)

[match_shape_3d](match_shape_3d.md) · [match_chamfer_3d](match_chamfer_3d.md) · [match_hough_3d](match_hough_3d.md) · [match_mip_2d](match_mip_2d.md) · [match_points_ncc](match_points_ncc.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
