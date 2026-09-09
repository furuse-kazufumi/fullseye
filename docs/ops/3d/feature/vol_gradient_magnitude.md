---
op: vol_gradient_magnitude
dim: 3d
category: feature
in: voxel
out: voxel
examples: [vessel_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# vol_gradient_magnitude — 3D `feature` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_gradient_magnitude(vol)` (実装を直接呼ぶなら `import volops; volops.vol_gradient_magnitude(vol)`、台帳から引くなら `ops3d.get("vol_gradient_magnitude")`)

## 使い方

3-D Sobel gradient magnitude ``sqrt(gz**2 + gy**2 + gx**2)``.

Each ``g*`` is a ``scipy.ndimage.sobel`` derivative along one axis. The
response localises at intensity boundaries (a step edge lights up on the
interface and is ~0 in flat regions). Returns a ``(D, H, W)`` float64 volume.

計算: ``scipy.ndimage.sobel`` を axis 0 (z), 1 (y), 2 (x) の順に掛け、
``sqrt(gz**2 + gy**2 + gx**2)`` を返す。Sobel は微分 [-1,0,1] と平滑 [1,2,1] の
分離カーネル(直交 2 軸で各 4 倍)なので、軸に垂直な単位ステップ(0→1)に対する
応答は 1 ではなく **16**(界面をはさむ 2 voxel で 16.0、平坦部は 0。scipy の既定
重み・境界 ``mode='reflect'``)。値は正規化しない(``[0, 1]`` には収まらない)。
spacing は受けず、voxel 単位の差分(異方 voxel でも軸ごとに補正しない)。

検証(``ValueError``): 3-D でない / NaN・Inf を含む / voxel 数が ``MAX_VOXELS``
(``1 << 27``)を超える。

使いどころ: ``vol_watershed`` の地形(landscape)入力、``vol_local_maxima`` で
界面の峰を拾う、``vol_stretch`` で ``[0, 1]`` に正規化して表示。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [vessel_metrology](../../../../examples_3d/vessel_metrology.py) — `py -3.11 examples_3d/vessel_metrology.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](sobel3d.md) · [hessian3d](hessian3d.md) · [curvature_maps](curvature_maps.md) · [edt_jfa](edt_jfa.md)

## 同カテゴリ(`feature`)

[sobel3d](sobel3d.md) · [hessian3d](hessian3d.md) · [curvature_maps](curvature_maps.md) · [edt_jfa](edt_jfa.md) · [vol_frangi](vol_frangi.md) · [vol_sato](vol_sato.md) · [vol_hessian_blobness](vol_hessian_blobness.md) · [vol_local_maxima](vol_local_maxima.md)

---
*Provenance: volops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
