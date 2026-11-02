---
op: shepp_logan_3d
dim: tomography
category: ct_scan
in: 
out: voxel
gpu: なし
examples: [ct_scan_modes]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# shepp_logan_3d — TOMOGRAPHY `ct_scan` op

- **データ種**: `なし` → `voxel`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.shepp_logan_3d(size=128, supersample=2)` (実装を直接呼ぶなら `import ctscan; ctscan.shepp_logan_3d(size=128, supersample=2)`、台帳から引くなら `opstomography.get("shepp_logan_3d")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

The modified 3-D Shepp-Logan head phantom on a ``size``-cube.

The in-plane ellipses are those of :data:`tomography.SHEPP_LOGAN`, with extents
along z, so a CT reconstruction has an exact volume to be measured against, and
:func:`ellipsoid_projections` has the exact data for it.

:param size: edge of the cube, ``2 .. 1024``; or ``(Z, Y, X)``.
:param supersample: anti-alias factor per axis, ``1 .. 4``.
:returns: float64 volume spanning ``[0, 1]``.
:raises ValueError: on an oversized grid.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_scan_modes](../../../../examples/ct_scan_modes.py) — `py -3.11 examples/ct_scan_modes.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[radon_volume](../volume/radon_volume.md) · [ct_forward_project](ct_forward_project.md)

## 同カテゴリ(`ct_scan`)

[ct_scan_geometry](ct_scan_geometry.md) · [ellipsoid_phantom](ellipsoid_phantom.md) · [ellipsoid_projections](ellipsoid_projections.md) · [ct_forward_project](ct_forward_project.md) · [ct_adjoint_project](ct_adjoint_project.md) · [fdk_reconstruct](fdk_reconstruct.md) · [sirt_reconstruct](sirt_reconstruct.md) · [os_sart_reconstruct](os_sart_reconstruct.md)

---
*Provenance: ctscan.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
