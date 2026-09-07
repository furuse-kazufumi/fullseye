---
op: fit_ellipsoid
dim: 3d
category: robust_fit
in: points
out: primitive
examples: [fit_primitives_ext]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# fit_ellipsoid — 3D `robust_fit` op

- **データ種**: `points` → `primitive`
- **呼び出し**: `import fullseye as fs; fs.ledger.fit_ellipsoid(points) -> 'dict'` (実装を直接呼ぶなら `import fit_primitives_ext; fit_primitives_ext.fit_ellipsoid(points) -> 'dict'`、台帳から引くなら `ops3d.get("fit_ellipsoid")`)

## 使い方

点群に任意姿勢の 3 軸楕円体を代数フィットし ``{center, axes, radii, residual}`` を返す。

一般二次曲面 ``xᵀA x + b·x + c = 0`` を、楕円体を保証する拘束 ``4J − I² = 1`` の下で
一般化固有問題 ``Sr v1 = λ C v1``(``scipy.linalg.eig``)として解く(Li & Griffiths 2004)。
各実固有ベクトルを楕円体へ復元し、**正定値(= 実在する楕円体)へ復元でき残差 RMS が最小**
のものを採用する(復元時の正定値検査そのものが厳密な楕円体判定)。初期値不要・決定論・
大域解。数値安定化のため点群を
重心と RMS 半径で無次元化してから解き、パラメータを world 座標へ戻す。

Args:
    points: (N,3) 点群(最低 10 点)。外れ値には無防備(必要なら事前に inlier 選別)。

Returns:
    dict: ``{"center": (3,), "axes": (3,3) 列=主軸(半径降順), "radii": (3,) 半径(降順),
    "residual": float Taubin 近似の点-面距離 RMS}``。

Raises:
    ValueError: 形状不正/点数不足/正定値な楕円体解が得られない(平面状の退化・
        非楕円面・被覆不足)など fail-closed。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blas_threads_and_memory](../../math/guides/blas_threads_and_memory.md) — 行列分解が遅い理由の知識 — BLAS スレッド・キャッシュ・メモリ配置

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fit_primitives_ext](../../../../examples_3d/fit_primitives_ext.py) — `py -3.11 examples_3d/fit_primitives_ext.py`

## 型が繋がる次の op(`primitive` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [angle_between_lines](../geometry/angle_between_lines.md) · [angle_between_planes](../geometry/angle_between_planes.md) · [angle_line_plane](../geometry/angle_line_plane.md) · [distance_point_plane](../geometry/distance_point_plane.md) · [distance_point_line](../geometry/distance_point_line.md) · [distance_line_line](../geometry/distance_line_line.md) · [distance_segment_segment](../geometry/distance_segment_segment.md)

## 同カテゴリ(`robust_fit`)

[ransac_plane](ransac_plane.md) · [ransac_sphere](ransac_sphere.md) · [ransac_line](ransac_line.md) · [ransac_cylinder](ransac_cylinder.md) · [fit_cone](fit_cone.md) · [fit_torus](fit_torus.md)

---
*Provenance: fit_primitives_ext.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
