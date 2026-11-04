---
op: fit_superquadric
dim: 3d
category: superquadric
in: points
out: primitive
gpu: なし
examples: [superquadric_fit]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# fit_superquadric — 3D `superquadric` op

- **データ種**: `points` → `primitive`
- **呼び出し**: `import fullseye as fs; fs.ledger.fit_superquadric(points) -> 'dict'` (実装を直接呼ぶなら `import superquadric; superquadric.fit_superquadric(points) -> 'dict'`、台帳から引くなら `ops3d.get("fit_superquadric")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

点群にスーパー2次曲面を least_squares で当てはめ dict{a,eps,R,t,residual} を返す。

初期姿勢 = 慣性テンソル固有ベクトル、初期 a = 主軸 bbox 半分、初期 eps=(1,1)。
``a`` は正、``eps`` は [0.1, 2.0] にクリップして最適化する。

尺度: 点群を重心へ寄せ、外接箱の対角長 ``L`` で割った無次元の座標で解き、``a = L·a'``、
``t = 重心 + L·t'``、``residual = L³·residual'`` で戻す(★2026-11-05 敵対的検証 N5)。
以前は生の座標のまま解いており、残差が長さの 1.5 乗で縮むため scipy 既定の ``gtol`` が
初回評価で満たされ、``s <= 1e-4`` の点群では PCA の初期値をそのまま返していた
(楕円体 a=(2,1.5,1) が 1.979/1.495/1.001、中心が 0.17·s ずれる)。いまは ``s`` に依らず同じ解。
全点が一致する点群(``L == 0``)は ``ValueError``。

Returns
-------
dict: {'a': (3,), 'eps': (2,), 'R': (3,3), 't': (3,), 'residual': float}

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [superquadric_fit](../../../../examples_3d/superquadric_fit.py) — `py -3.11 examples_3d/superquadric_fit.py`

## 型が繋がる次の op(`primitive` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [angle_between_lines](../geometry/angle_between_lines.md) · [angle_between_planes](../geometry/angle_between_planes.md) · [angle_line_plane](../geometry/angle_line_plane.md) · [distance_point_plane](../geometry/distance_point_plane.md) · [distance_point_line](../geometry/distance_point_line.md) · [distance_line_line](../geometry/distance_line_line.md) · [distance_segment_segment](../geometry/distance_segment_segment.md)

## 同カテゴリ(`superquadric`)

[sample_surface](sample_surface.md) · [inside_outside](inside_outside.md) · [superquadric_residual](superquadric_residual.md)

---
*Provenance: superquadric.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
