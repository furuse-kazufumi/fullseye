---
op: lf_synthesize
dim: lightfield
category: synthesis
in: 
out: lightfield
examples: [lightfield_depth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# lf_synthesize — LIGHTFIELD `synthesis` op

- **データ種**: `` → `lightfield`
- **呼び出し**: `import lightfield; lightfield.lf_synthesize(slopes=(0.0,), angular=(5, 5), shape=(64, 64), *, occlusion=True, coverage=0.55, texture_sigma=2.0, interp='linear', edge='wrap', seed=0)` (または `opslightfield.get("lf_synthesize")`)

## 使い方

Build a light field of textured layers at **known** slopes (the test bed).

Each entry of *slopes* is one fronto-parallel layer, given as its slope
``s = dx/du`` in **pixels of image shift per angular step**; the layer's
texture is band-limited noise (Gaussian-smoothed, ``texture_sigma`` px) and
view ``(v, u)`` sees it displaced by ``(s*(v - v_c), s*(u - u_c))``. Because
the displacement is exactly linear in the angular index, every downstream
answer is closed-form: the refocus sharpness peaks at ``s``, the EPI lines
have slope ``s``, and the disparity between the extreme views is
``s * (U - 1)``.

*angular* is ``(V, U)`` and *shape* is ``(H, W)``.

With ``occlusion=True`` (default) the layers are composited front-to-back by
``|slope|`` (largest ``|s|`` = nearest = drawn last) through random binary
masks covering roughly *coverage* of the frame, and the **last** entry of
*slopes* is forced opaque as the background. That is what makes a
see-through synthetic-aperture test meaningful. With ``occlusion=False`` the
layers are averaged instead — a transparent superposition, which is the
cleanest possible input for refocusing because each layer survives the
average untouched.

Returns ``(light_field, slope_map)``: the ``(V, U, H, W)`` array and the
``(H, W)`` map of the front-most layer's slope at each pixel — the ground
truth for :func:`lf_depth_from_focus` and :func:`lf_epi_slope`. The map is
in **centre-view** coordinates (the masks are stated unshifted, and the
centre view is the one view whose shift is zero), which is also the frame a
refocused image lands in. With
``occlusion=False`` the light field also contains the *other* layers at
every pixel, so a depth estimator will legitimately disagree with the map
wherever layers overlap; the single-layer case is unambiguous and is what
the exactness tests use.

``edge="wrap"`` (default) makes the scene periodic so an integer slope is a
pure ``np.roll`` and the whole pipeline is bit-exact end to end (measured
round-trip error 5.6e-16); ``edge="nearest"`` reproduces a real camera's
border clamping.

**Raises** ``ValueError``: an empty or over-long *slopes* list
(:data:`MAX_LAYERS`), a non-finite or over-large slope
(:data:`MAX_ABS_SLOPE`), an angular or spatial shape outside
``[1, MAX_ANGULAR]`` / ``[1, MAX_SPATIAL]``, a total size over
:data:`MAX_LF_ELEMENTS`, *coverage* outside ``(0, 1]``, a *texture_sigma*
so large the smoothed texture's dynamic range falls below
:data:`MIN_TEXTURE_RANGE`, and an unknown *interp* / *edge*.

## 詳しい使い方ガイド

- [lightfield_depth ファミリ ガイド](../guides/lightfield_depth.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lightfield_depth](../../../../examples/lightfield_depth.py) — `py -3.11 examples/lightfield_depth.py`

## 型が繋がる次の op(`lightfield` を入力に取れる)

[lf_to_mla](../decode/lf_to_mla.md) · [lf_stats](../decode/lf_stats.md) · [lf_subaperture](../views/lf_subaperture.md) · [lf_center_view](../views/lf_center_view.md) · [lf_views](../views/lf_views.md) · [lf_epi](../views/lf_epi.md) · [lf_refocus](../refocus/lf_refocus.md) · [lf_focal_stack](../refocus/lf_focal_stack.md)

## 同カテゴリ(`synthesis`)

—

---
*Provenance: lightfield.py — LIGHTFIELD operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
