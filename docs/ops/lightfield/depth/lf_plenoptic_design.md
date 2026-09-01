---
op: lf_plenoptic_design
dim: lightfield
category: depth
in: 
out: table
examples: [lightfield_depth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# lf_plenoptic_design — LIGHTFIELD `depth` op

- **データ種**: `` → `table`
- **呼び出し**: `import lightfield; lightfield.lf_plenoptic_design(focal_mm=50.0, f_number=8.0, object_mm=300.0, pixel_um=3.45, mla_pitch_um=27.6, sensor_px=(2048, 2448), *, subpixel_px=0.1)` (または `opslightfield.get("lf_plenoptic_design")`)

## 使い方

Size a plenoptic camera: what angular/spatial resolution and depth range you buy.

The plenoptic trade in one table. A microlens spanning ``mla_pitch_um /
pixel_um`` pixels turns that many pixels into that many *directions*, so the
sensor's pixel count is unchanged but the image is ``U*V`` times smaller and
carries ``U*V`` viewpoints. This operator composes :mod:`optics` rather than
re-deriving it: ``optics.thin_lens`` places the image, and
``optics.depth_of_field`` is called **twice** — once with the pixel pitch as
the circle of confusion (the depth of field of a single refocused slice) and
once with the *microlens* pitch (the range over which refocusing can still
recover a sharp image). Their ratio is the refocusing gain, and it comes out
at the angular resolution, which is the textbook result — measured
2026-09-01 at ``f = 50 mm``, ``N = 8``, ``s_o = 300 mm``: an 8x8 angular
grid gives ``refocus_gain = 8.0038``, 10x10 gives ``10.0075`` and 6x6 gives
``6.0016``.

Returns a dict — ``angular_u`` / ``angular_v`` (whole pixels per microlens,
from ``floor``) · ``angular_exact`` (the unrounded ratio) and
``pitch_is_integer`` (whether the MLA pitch is a whole number of pixels; it
usually is not, which is why real decoding needs sub-pixel calibration) ·
``spatial_w`` / ``spatial_h`` (microlenses = sub-aperture image size) ·
``n_views`` · ``resolution_loss`` (``U*V``) · ``image_mm`` /
``magnification`` / ``working_distance_mm`` from the thin lens ·
``aperture_mm`` (``f/N``) · ``baseline_mm`` (viewpoint spacing across the
pupil, ``aperture / (U - 1)``) · ``focal_px_subaperture`` (focal length in
units of the *microlens* pitch, the pixel of a sub-aperture image) ·
``dof_pixel_mm`` / ``dof_refocus_mm`` and ``refocus_gain`` · and
``depth_precision_mm``, the object-side distance change that moves the
disparity by *subpixel_px* pixels (``Z^2 * dp / (focal_px * baseline)``) —
the honest depth resolution at *object_mm*.

**Raises** ``ValueError``: any non-positive or non-finite length, an
``mla_pitch_um`` smaller than two *pixel_um* (fewer than 2 directions is not
a light field), a sensor smaller than one microlens, a non-positive
*subpixel_px*, ``object_mm == focal_mm`` (propagated from
``optics.thin_lens``: the object images at infinity), and an angular
resolution of 1 in either axis, where the baseline would be a 0/0.

## 詳しい使い方ガイド

- [lightfield_depth ファミリ ガイド](../guides/lightfield_depth.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lightfield_depth](../../../../examples/lightfield_depth.py) — `py -3.11 examples/lightfield_depth.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`depth`)

[lf_depth_from_focus](lf_depth_from_focus.md) · [lf_epi_slope](lf_epi_slope.md) · [lf_disparity_to_depth](lf_disparity_to_depth.md) · [lf_all_in_focus](lf_all_in_focus.md)

---
*Provenance: lightfield.py — LIGHTFIELD operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
