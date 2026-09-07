---
op: moment_axes
dim: 3d
category: match_pose
in: points
out: axes
examples: [itokawa_pose_canonical]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# moment_axes — 3D `match_pose` op

- **データ種**: `points` → `axes`
- **呼び出し**: `import fullseye as fs; fs.ledger.moment_axes(points, weights=None)` (実装を直接呼ぶなら `import match3d; match3d.moment_axes(points, weights=None)`、台帳から引くなら `ops3d.get("moment_axes")`)

## 使い方

点群/重み付き点の **重心 + 主軸**(慣性テンソルの固有ベクトル)。姿勢推定の基礎。

返り値 (centroid(3,), axes(3,3) 列=主軸, eigvals(3,))。固有値降順。回転の正準化に使う。

定義: ``w`` を総和 1 に正規化し、重心 ``c = Σ w p``、散布行列 ``C = Σ w (p−c)(p−c)ᵀ``
(共分散。慣性テンソル ``tr(C)I − C`` と固有ベクトルは共通で固有値の順序が逆)を ``eigh`` で
分解する。``axes[:, i]`` が i 番目に大きい固有値の主軸(降順)。固有値は分散(長さ²)。
- 固有ベクトルの符号は任意で、``axes`` は左手系(det=−1)になり得る(``match_pca`` は第 3 軸を
反転して右手系にしている)。
- ``weights`` は長さ N。総和 0 は 0 除算で NaN(例外は出ない)。点数 0 は失敗する(検証は無い)。
- 主軸が縮退(球など)なら軸の向きは不定。
後段: ``match_pca``、``obb``(有向 bbox)、正準姿勢への回転。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [itokawa_pose_canonical](../../../../examples_3d/itokawa_pose_canonical.py) — `py -3.11 examples_3d/itokawa_pose_canonical.py`

## 型が繋がる次の op(`axes` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`match_pose`)

[match_phase_3d](match_phase_3d.md) · [match_pca](match_pca.md) · [match_logpolar_z](match_logpolar_z.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
