---
op: ct_dual_energy_reconstruct
dim: tomography
category: ct_scan
in: projstack × projstack × ctgeometry
out: table
gpu: なし
examples: [poc_real_walnut_cbct]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# ct_dual_energy_reconstruct — TOMOGRAPHY `ct_scan` op

- **データ種**: `projstack × projstack × ctgeometry` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.ct_dual_energy_reconstruct(proj_low, proj_high, geometry, mu_low=(1.0, 0.4), mu_high=(0.6, 0.3), method='fdk', device='auto', **options)` (実装を直接呼ぶなら `import ctscan; ctscan.ct_dual_energy_reconstruct(proj_low, proj_high, geometry, mu_low=(1.0, 0.4), mu_high=(0.6, 0.3), method='fdk', device='auto', **options)`、台帳から引くなら `opstomography.get("ct_dual_energy_reconstruct")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Two scans of one geometry to two basis-material volumes.

At each detector sample the two line integrals are two linear equations in the two
material path lengths, ``L = M t`` (Alvarez & Macovski 1976). The system is solved
in the projection domain, where beam hardening has not yet been smeared across the
volume, and each material is reconstructed on its own. *mu_low* and *mu_high* are
effective attenuation coefficients; for a polychromatic beam, call
:func:`dualxray.basis_material_decompose` per view first and reconstruct its output.

The noise of the two path lengths grows with the condition number of ``M``, which
is returned.

:param proj_low: ``(view, V, U)`` line integrals of the low-energy scan.
:param proj_high: the high-energy scan, same shape.
:param geometry: dict from :func:`ct_scan_geometry`.
:param mu_low: attenuation of the two basis materials at the low energy.
:param mu_high: attenuation of the two basis materials at the high energy.
:param method: ``"fdk"``, ``"sirt"``, ``"os_sart"`` or ``"tv"``.
:param device: ``"auto"``, ``"cpu"`` or ``"cuda"``.
:param options: passed to the reconstruction.
:returns: dict with ``basis_0`` and ``basis_1`` (path-length densities, volumes),
    and ``condition``.
:raises ValueError: on mismatched shapes or a singular matrix. Empty input
    (``proj_low`` with 0 elements) raises ``ValueError``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_real_walnut_cbct](../../../../examples/poc_real_walnut_cbct.py) — `py -3.11 examples/poc_real_walnut_cbct.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`ct_scan`)

[ct_scan_geometry](ct_scan_geometry.md) · [shepp_logan_3d](shepp_logan_3d.md) · [ellipsoid_phantom](ellipsoid_phantom.md) · [ellipsoid_projections](ellipsoid_projections.md) · [ct_forward_project](ct_forward_project.md) · [ct_adjoint_project](ct_adjoint_project.md) · [fdk_reconstruct](fdk_reconstruct.md) · [sirt_reconstruct](sirt_reconstruct.md)

---
*Provenance: ctscan.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
