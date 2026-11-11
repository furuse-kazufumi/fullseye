---
op: sirt_reconstruct
dim: tomography
category: ct_scan
in: projstack × ctgeometry
out: voxel
gpu: なし
examples: [ct_scan_modes, poc_ct_casting_sparse_views, poc_real_walnut_cbct]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# sirt_reconstruct — TOMOGRAPHY `ct_scan` op

- **データ種**: `projstack × ctgeometry` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.sirt_reconstruct(projections, geometry, n_iter=50, relaxation=1.0, initial=None, nonnegative=True, device='auto', on_iter=None)` (実装を直接呼ぶなら `import ctscan; ctscan.sirt_reconstruct(projections, geometry, n_iter=50, relaxation=1.0, initial=None, nonnegative=True, device='auto', on_iter=None)`、台帳から引くなら `opstomography.get("sirt_reconstruct")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

SIRT: every view at once, ``x <- x + lam C A^T R (p - A x)``.

``R`` and ``C`` are the inverse row and column sums of ``A``. With the matched
pair of this family it minimises a weighted least-squares error, and it needs no
formula, so it is the route for tomosynthesis, few views and limited angle.

:param projections: ``(view, V, U)`` line integrals.
:param geometry: dict from :func:`ct_scan_geometry`.
:param n_iter: iterations, ``1 .. 5000``.
:param relaxation: step ``lam``, ``(0, 2)``.
:param initial: starting volume; ``None`` gives zeros.
:param nonnegative: clip to ``>= 0`` after each iteration.
:param device: ``"auto"``, ``"cpu"`` or ``"cuda"``.
:param on_iter: optional ``on_iter(iteration, volume)`` for a convergence curve;
    returning a boolean ``True`` (``bool`` or ``numpy.bool_``) stops after
    that iteration; any other return value (``None``, numbers, dicts,
    arrays) is ignored.
:returns: ``(Z, Y, X)`` float volume.
:raises ValueError: on a shape that disagrees with the geometry or a relaxation
    outside ``(0, 2)``. Empty input (``projections`` with 0 elements) raises
    ``ValueError``.

**The default 50 iterations is not converged.** SIRT moves slowly. On
consistent data (24^3 Shepp-Logan, cone, 20 views) the relative residual is
0.0318 at 50 iterations and 0.0087 at 200, and the nRMS to the truth drops
from 0.0407 to 0.0232 (43 %); on the measured walnut (fan, 50 views) the RMSE
to the reference is 0.0055 /mm at 60 iterations and 0.0036 at 400 (2026-11-09
audit). Comparing methods at the defaults makes SIRT look worse than it is.
Choose ``n_iter`` from a curve: ``on_iter`` can compute the residual
``|A x - p| / |p|`` (``ct_forward_project``) or the error on held-out views,
and return ``True`` once its relative change falls below e.g. ``1e-3``. With
noisy data the error to the truth reaches a minimum and then rises again
(semi-convergence), so the residual alone is not a stopping rule there.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_scan_modes](../../../../examples/ct_scan_modes.py) — `py -3.11 examples/ct_scan_modes.py`
- [poc_ct_casting_sparse_views](../../../../examples/poc_ct_casting_sparse_views.py) — `py -3.11 examples/poc_ct_casting_sparse_views.py`
- [poc_real_walnut_cbct](../../../../examples/poc_real_walnut_cbct.py) — `py -3.11 examples/poc_real_walnut_cbct.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[radon_volume](../volume/radon_volume.md) · [ct_forward_project](ct_forward_project.md)

## 同カテゴリ(`ct_scan`)

[ct_scan_geometry](ct_scan_geometry.md) · [shepp_logan_3d](shepp_logan_3d.md) · [ellipsoid_phantom](ellipsoid_phantom.md) · [ellipsoid_projections](ellipsoid_projections.md) · [ct_forward_project](ct_forward_project.md) · [ct_adjoint_project](ct_adjoint_project.md) · [fdk_reconstruct](fdk_reconstruct.md) · [os_sart_reconstruct](os_sart_reconstruct.md)

---
*Provenance: ctscan.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
