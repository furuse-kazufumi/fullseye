---
op: min_enclosing_sphere
dim: 3d
category: bounds
in: points
out: primitive
examples: [hull_bounds]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# min_enclosing_sphere — 3D `bounds` op

- **データ種**: `points` → `primitive`
- **呼び出し**: `import fullseye as fs; fs.ledger.min_enclosing_sphere(points, refine_iters: 'int' = 1000) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import hull3d; hull3d.min_enclosing_sphere(points, refine_iters: 'int' = 1000) -> 'Dict[str, object]'`、台帳から引くなら `ops3d.get("min_enclosing_sphere")`)

## 使い方

点群 (N,3) → 全点を含む(近似)最小包含球 {center(3), radius}。

``fit_sphere_3d``(球面フィット)や ``ransac_sphere`` / ``hough_sphere_3d``(球検出)とは
異なり、**全点を内包する最小の球**(minimum enclosing ball, MEB)を解く。2 段構成で
「全点内包」を厳守しつつ半径を詰める:

1. **Ritter (1990) 初期化** — 最遠の点対を粗く取り初期球にし、各点を走査して球外の点が
   あれば「その点と既存球の両方を含む」最小の球へ 1 回膨らませる(膨張式
   ``new_r=(r+d)/2`` / 中心を点方向へ ``(d-r)/(2d)`` 進める)。新球が旧球を完全に含むため、
   1 パスで全点内包を保証する。
2. **Bădoiu–Clarkson (2003) core-set 反復による精緻化** — 反復 ``i`` で最遠点 ``q`` へ
   中心を ``1/(i+2)`` だけ寄せる。真の最小包含球へ単調収束する(半径過大な Ritter の
   ドリフトを詰める)。最後に半径を「中心からの最大距離」で確定するので、精緻化後も
   **必ず全点を内包**(近似ゆえ半径が過小になり点が漏れることはない、安全側)。

精緻化した中心が Ritter より外接半径を縮められたときのみ採用する(常に Ritter 以下)。
真の最小球(厳密解は Welzl の乱択線形時間法)ではなく高速な (1+ε) 近似。

Parameters
----------
points : array_like (N,3)
    入力点群(>= 1 点)。
refine_iters : int
    Bădoiu–Clarkson 精緻化の反復数(既定 1000)。0 で Ritter のみ。

Returns
-------
dict
    - ``center``: (3,) float64 — 球中心(世界座標)。
    - ``radius``: float — 半径(全点を内包)。

Raises
------
ValueError
    形状不正・非有限・点数 0、または ``refine_iters`` が負のとき(fail-closed)。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [hull_bounds](../../../../examples_3d/hull_bounds.py) — `py -3.11 examples_3d/hull_bounds.py`

## 型が繋がる次の op(`primitive` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [angle_between_lines](../geometry/angle_between_lines.md) · [angle_between_planes](../geometry/angle_between_planes.md) · [angle_line_plane](../geometry/angle_line_plane.md) · [distance_point_plane](../geometry/distance_point_plane.md) · [distance_point_line](../geometry/distance_point_line.md) · [distance_line_line](../geometry/distance_line_line.md) · [distance_segment_segment](../geometry/distance_segment_segment.md)

## 同カテゴリ(`bounds`)

[convex_hull](convex_hull.md) · [aabb](aabb.md) · [obb](obb.md)

---
*Provenance: hull3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
