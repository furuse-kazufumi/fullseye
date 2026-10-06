---
op: harmonic_rotation
dim: residue
category: image
in: image2d × image2d
out: table
examples: [poc_residue_crt]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# harmonic_rotation — RESIDUE `image` op

- **データ種**: `image2d × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.harmonic_rotation(image, reference, orders=(3, 4, 5), rings=((14, 24), (30, 40), (46, 56)), center=None, tol=0.05) -> 'dict'` (実装を直接呼ぶなら `import residue; residue.harmonic_rotation(image, reference, orders=(3, 4, 5), rings=((14, 24), (30, 40), (46, 56)), center=None, tol=0.05) -> 'dict'`、台帳から引くなら `opsresidue.get("harmonic_rotation")`)

## 使い方

Absolute in-plane rotation of ``image`` relative to ``reference`` over 360 degrees -> ``dict``.

A feature with n-fold symmetry (n lobes, n holes, n slots) tells the
rotation only modulo ``360/n`` degrees: its order-``n`` circular harmonic has
phase ``n*theta``. Features of several orders, each ambiguous alone, fix
``theta`` uniquely whenever the orders have no common divisor (3 and 4: 360 /
gcd = 360). This op samples each annulus ``rings[i]`` (radii in px around
``center``, default the image centre), takes the order ``orders[i]`` angular
Fourier coefficient of image and reference, and solves the angle by
:func:`residue_crt` with the coefficient amplitudes as weights.

Returns ``{"angle_deg", "per_order_deg", "residual_deg", "margin", "suspect",
"amplitude"}``. ``angle_deg`` is counter-clockwise on screen (rows down) — the
convention of ``scipy.ndimage.rotate`` — in ``[0, 360)``. ``suspect`` is the index of the ring whose residual is
worst relative to its period (or ``-1`` if all are within ``tol``) — a smudged,
occluded or broken feature shows up there before it corrupts the angle.
With >= 3 orders and only one corrupted, :func:`residue_fault_locate` gives a
hard decision; this op keeps the soft one.

Rotate greyscale images (interpolate, then threshold if needed): rotating a
binary mask with nearest-neighbour sampling roughens the edges and biases the
harmonics.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_residue_crt](../../../../examples/poc_residue_crt.py) — `py -3.11 examples/poc_residue_crt.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`image`)

[crt_displacement](crt_displacement.md)

---
*Provenance: residue.py — RESIDUE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
