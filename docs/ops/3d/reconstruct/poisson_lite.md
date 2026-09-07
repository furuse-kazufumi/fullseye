---
op: poisson_lite
dim: 3d
category: reconstruct
in: points
out: mesh
examples: [poisson_surface_recon]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# poisson_lite — 3D `reconstruct` op

- **データ種**: `points` → `mesh`
- **呼び出し**: `import fullseye as fs; fs.ledger.poisson_lite(points, size=64, sigma=1.0, iso=0.5, normals=None)` (実装を直接呼ぶなら `import recon3d; recon3d.poisson_lite(points, size=64, sigma=1.0, iso=0.5, normals=None)`、台帳から引くなら `ops3d.get("poisson_lite")`)

## 使い方

点群 (N,3) → (vertices(V,3), faces(F,3)) の表面メッシュ(スクリーンド Poisson 軽量近似)。

点群を size³ の voxel 格子へ splat し、等値面場を作って marching cubes で三角形メッシュ化する。
出力頂点は入力点群と同じ**世界座標**(bbox から逆写像)。bounds は点群 bbox(+σ 依存の padding)。

2 モード:
  * ``normals is None``: **占有(occupancy)** をガウス平滑・[0,1] 正規化し、``iso`` で二値化した
    表面バンドの内部を ``binary_fill_holes`` で充填してから再平滑し、単一の外殻を ``iso`` で抜く。
    占有(unsigned)場は内外対称で、平滑した薄殻の等値面は内スロープ・外スロープの二か所を通り
    **同心二重殻**になってしまう。内部充填で内外対称性を破ることで、**閉じた**表面サンプルからは
    (格子/σ に対し十分密なら)単一殻が得られる。開いた曲面は充填されず薄い面のまま。疎すぎる/σ が
    小さいと隙間から充填が漏れ二重殻へ縮退しうる(厳密な内外判定が要るなら ``normals`` 指定を使う)。
  * ``normals`` 指定: 向き付き点の **winding number** で内外指標場を作りガウス平滑、``iso``
    (既定 0.5)で表面抜き。表面のみサンプルでも内部を埋めて閉曲面を得られる。

Parameters
----------
points : array_like (N,3)
    入力点群。
size : int
    voxel 格子の一辺(既定 64)。大きいほど精細だが O(size³)。
sigma : float
    ガウス平滑の標準偏差(voxel 単位、既定 1.0)。padding は ⌈3σ⌉+2 voxel を自動確保。
iso : float
    等値面レベル。正規化場 [0,1] 上の値(既定 0.5)。
normals : array_like (N,3) or None
    点法線。与えると winding number モード、None なら占有モード。

Returns
-------
vertices : numpy.ndarray (V,3) float64
    世界座標の頂点。
faces : numpy.ndarray (F,3) int64
    三角形の頂点インデックス(vertices を参照)。

Raises
------
ValueError
    点数不足(<4)、size が小さすぎる、占有/指標場が薄く iso が場の値域外、など。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poisson_surface_recon](../../../../examples_3d/poisson_surface_recon.py) — `py -3.11 examples_3d/poisson_surface_recon.py`

## 型が繋がる次の op(`mesh` を入力に取れる)

[mesh_to_voxel](../transform/mesh_to_voxel.md) · [mesh_to_points](../transform/mesh_to_points.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [ambient_occlusion](../render/ambient_occlusion.md) · [cast_shadow](../render/cast_shadow.md) · [supersample_mesh](../render/supersample_mesh.md) · [render_beauty](../render/render_beauty.md)

## 同カテゴリ(`reconstruct`)

[alpha_shape_mesh](alpha_shape_mesh.md) · [alpha_shape_boundary](alpha_shape_boundary.md) · [estimate_alpha](estimate_alpha.md)

---
*Provenance: recon3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
