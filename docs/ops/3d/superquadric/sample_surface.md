---
op: sample_surface
dim: 3d
category: superquadric
in: vector
out: points
examples: [mesh_lod_download, superquadric_fit]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# sample_surface — 3D `superquadric` op

- **データ種**: `vector` → `points`
- **呼び出し**: `import superquadric; superquadric.sample_surface(a, eps, n_u: 'int' = 40, n_v: 'int' = 40, R=None, t=None) -> 'np.ndarray'` (または `ops3d.get("sample_surface")`)

## 使い方

スーパー2次曲面の表面点を (eta, omega) パラメトリックにサンプリング。

``x = a1 * sgn|cos eta|^eps1 * sgn|cos omega|^eps2`` などの符号付きべきで
全 8 象限を張る(eta in [-pi/2, pi/2], omega in [-pi, pi])。生成点は
厳密に ``F = 1`` を満たす(cos^2+sin^2=1 が指数を打ち消すため)。

Parameters
----------
a, eps : inside_outside と同じ
n_u : omega(経度)方向サンプル数
n_v : eta(緯度)方向サンプル数
R, t : 姿勢(body→world: X_world = R @ X_body + t)

Returns
-------
np.ndarray, shape (n_u*n_v, 3)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [mesh_lod_download](../../../../examples_3d/mesh_lod_download.py) — `py -3.11 examples_3d/mesh_lod_download.py`
- [superquadric_fit](../../../../examples_3d/superquadric_fit.py) — `py -3.11 examples_3d/superquadric_fit.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [gaussians_to_voxel](../transform/gaussians_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md)

## 同カテゴリ(`superquadric`)

[fit_superquadric](fit_superquadric.md) · [inside_outside](inside_outside.md) · [superquadric_residual](superquadric_residual.md)

---
*Provenance: superquadric.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
