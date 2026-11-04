---
op: os_sart_reconstruct
dim: tomography
category: ct_scan
in: projstack × ctgeometry
out: voxel
gpu: なし
examples: [ct_scan_modes, poc_ct_casting_sparse_views]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# os_sart_reconstruct — TOMOGRAPHY `ct_scan` op

- **データ種**: `projstack × ctgeometry` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.os_sart_reconstruct(projections, geometry, n_iter=10, n_subsets=16, relaxation=0.8, initial=None, nonnegative=True, device='auto', on_iter=None)` (実装を直接呼ぶなら `import ctscan; ctscan.os_sart_reconstruct(projections, geometry, n_iter=10, n_subsets=16, relaxation=0.8, initial=None, nonnegative=True, device='auto', on_iter=None)`、台帳から引くなら `opstomography.get("os_sart_reconstruct")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

OS-SART: the SIRT update applied to one ordered subset of views at a time.

One iteration passes over all subsets, so it costs about one SIRT iteration and
moves about *n_subsets* times as far early on. With inconsistent data it settles
into a limit cycle rather than a point.

:param projections: ``(view, V, U)`` line integrals.
:param geometry: dict from :func:`ct_scan_geometry`.
:param n_iter: passes over all subsets, ``1 .. 5000``.
:param n_subsets: subsets, ``1 .. n_views``.
:param relaxation: step ``lam``, ``(0, 2)``.
:param initial: starting volume; ``None`` gives zeros.
:param nonnegative: clip to ``>= 0`` after each subset.
:param device: ``"auto"``, ``"cpu"`` or ``"cuda"``.
:param on_iter: optional ``on_iter(iteration, volume)``.
:returns: ``(Z, Y, X)`` float volume.
:raises ValueError: on a shape that disagrees with the geometry, a relaxation
    outside ``(0, 2)``, or more subsets than views. Empty input (``projections``
    with 0 elements) raises ``ValueError``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_scan_modes](../../../../examples/ct_scan_modes.py) — `py -3.11 examples/ct_scan_modes.py`
- [poc_ct_casting_sparse_views](../../../../examples/poc_ct_casting_sparse_views.py) — `py -3.11 examples/poc_ct_casting_sparse_views.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[radon_volume](../volume/radon_volume.md) · [ct_forward_project](ct_forward_project.md)

## 同カテゴリ(`ct_scan`)

[ct_scan_geometry](ct_scan_geometry.md) · [shepp_logan_3d](shepp_logan_3d.md) · [ellipsoid_phantom](ellipsoid_phantom.md) · [ellipsoid_projections](ellipsoid_projections.md) · [ct_forward_project](ct_forward_project.md) · [ct_adjoint_project](ct_adjoint_project.md) · [fdk_reconstruct](fdk_reconstruct.md) · [sirt_reconstruct](sirt_reconstruct.md)

---
*Provenance: ctscan.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
