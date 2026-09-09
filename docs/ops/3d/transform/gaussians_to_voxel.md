---
op: gaussians_to_voxel
dim: 3d
category: transform
in: points
out: voxel
gpu: true
examples: [transforms_repr]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# gaussians_to_voxel — 3D `transform` op

- **データ種**: `points` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.gaussians_to_voxel(means, scales, opacities, size, bounds, device='cpu')` (実装を直接呼ぶなら `import match3d; match3d.gaussians_to_voxel(means, scales, opacities, size, bounds, device='cpu')`、台帳から引くなら `ops3d.get("gaussians_to_voxel")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

3DGS(異方性ガウス)→ 密度 voxel。各ガウスを means に opacity で置き、平均 scale で平滑。

近似(等方 splat + 平滑): 厳密な異方共分散ラスタライズは重いので、まず means を opacity 重み
で splat → scale 平均ぶん gaussian 平滑。マッチングの coarse alignment には十分。

引数: ``means`` (N,3) 中心、``opacities`` は長さ N に reshape されて splat の重みになる
(``points_to_voxel`` が 1 を足すところに opacity を足す)。``scales`` は形を問わず
**平均値 1 つ**にまとめ、``σ = mean(scales)/mean(hi − lo)·size``(world 長 → voxel 長)を
平滑幅にする(下限 0.5 voxel。``scales`` が空なら σ=1)。異方性・回転は無視される。
``bounds=(lo, hi)`` は必須(None 不可。``_lo_hi`` で検証し不正なら ValueError)。範囲外の
中心は端 voxel に clip される。返り値 ``(size, size, size)`` float64、軸順は ``means`` の列順。
opacity の総和はほぼ保存されるが正規化はしない。点群に落とすなら ``gaussians_to_points``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [transforms_repr](../../../../examples_3d/transforms_repr.py) — `py -3.11 examples_3d/transforms_repr.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](voxel_to_mips.md) · [voxel_to_mesh](voxel_to_mesh.md) · [signed_distance_field](signed_distance_field.md) · [to_points](to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`transform`)

[points_to_voxel](points_to_voxel.md) · [mesh_to_voxel](mesh_to_voxel.md) · [mesh_to_points](mesh_to_points.md) · [depth_to_points](depth_to_points.md) · [voxel_to_mips](voxel_to_mips.md) · [voxel_to_mesh](voxel_to_mesh.md) · [tsdf_from_depth](tsdf_from_depth.md) · [signed_distance_field](signed_distance_field.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
