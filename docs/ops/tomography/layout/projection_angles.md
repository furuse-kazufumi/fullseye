---
op: projection_angles
dim: tomography
category: layout
in: 
out: signal
examples: [ct_reconstruction, tomography_reconstruct]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# projection_angles — TOMOGRAPHY `layout` op

- **データ種**: `` → `signal`
- **呼び出し**: `import tomography; tomography.projection_angles(n_angles=180, span_deg=180.0, scheme='uniform', start_deg=0.0)` (または `opstomography.get("projection_angles")`)

## 使い方

The angle sequence of a scan, in **degrees**, as a 1-D float64 array.

Three schemes, and the difference between them is what happens when a scan is
cut short:

* ``"uniform"`` — ``start + span * k / n``. The textbook scan. A prefix of it
  covers only a wedge, so an interrupted uniform scan is a limited-angle scan.
* ``"golden"`` — increments of ``180/phi = 111.246...`` degrees, wrapped into
  ``[start, start+span)``. Every prefix is near-uniform, so an interrupted
  golden scan is a *sparse* scan, which is a far easier problem. Largest
  angular gap left by a scan that stops early, measured:

    scheme          after 32 of 180    all 180
    uniform            149.000 deg     1.000 deg
    golden              10.031 deg     1.464 deg
    bit-reversed         8.000 deg     1.000 deg

  Uniform's 149-degree hole is the entire limited-angle problem arriving by
  accident. Bit-reversed is the only one of the three that is good at both
  ends; golden's price for working at *every* prefix length rather than only
  at powers of two is a completed set 1.46x less even than the grid.
* ``"bit-reversed"`` — the uniform grid, visited in bit-reversed order. Same
  guarantee as golden for power-of-two prefixes and exactly uniform at the
  end, which golden is not.

*span_deg* is the total angular range. 180 degrees is the complete data set
for parallel beam — projections at ``theta`` and ``theta+180`` are mirror
images and carry no new information — so a 360-degree span is redundancy, not
resolution, and anything under 180 is the limited-angle problem.

:param n_angles: number of views, ``1 .. 65536``.
:param span_deg: total angular range in degrees, ``> 0``.
:param scheme: one of :data:`ANGLE_SCHEMES`.
:param start_deg: angle of the first view.
:returns: ``(n_angles,)`` float64 array of degrees.
:raises ValueError: on a non-int count, a non-positive span, a non-finite
    start, or an unknown scheme.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_reconstruction](../../../../examples/ct_reconstruction.py) — `py -3.11 examples/ct_reconstruction.py`
- [tomography_reconstruct](../../../../examples/tomography_reconstruct.py) — `py -3.11 examples/tomography_reconstruct.py`

## 型が繋がる次の op(`signal` を入力に取れる)

—

## 同カテゴリ(`layout`)

[sinogram_design](sinogram_design.md)

---
*Provenance: tomography.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
