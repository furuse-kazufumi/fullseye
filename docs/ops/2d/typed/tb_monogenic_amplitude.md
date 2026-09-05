---
op: tb_monogenic_amplitude
dim: 2d
category: typed
in: qimage
out: image
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# tb_monogenic_amplitude — 2D `typed` op

- **データ種**: `qimage` → `image`
- **呼び出し**: `fullseye.apply(img, "tb_monogenic_amplitude", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Local amplitude ``sqrt(f^2 + R1^2 + R2^2)`` of a monogenic signal. → (H, W).

    The local contrast at the signal's scale, and the confidence map for
    :func:`monogenic_phase` / :func:`monogenic_orientation`, which mean nothing
    where this is at the rounding floor. **Raw / unnormalised** (a contrast is a
    metric quantity), in the same spirit as ``complexops.cx_magnitude``.

    For a unit-contrast grating at the band centre it is exactly 1.0 (measured
    spread 8.9e-16 over a 64x64 frame) and, unlike a squared oriented-filter
    response, it is *isotropic*: rotating the grating does not change it.
    Measured over eight grid-exact orientations the amplitude spans
    ``[0.99999999999999911, 1.0000000000000011]`` — a total spread of 2.0e-15
    across all of them, which is the isotropy claim as a number.

    **Raises** ``ValueError``: the input is not a valid quaternion field, or its
    ``k`` component is non-zero (see :func:`_require_monogenic`).

Typed bridge of the quat op ``monogenic_amplitude`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. This op has no tunable parameter; ``a`` and ``b`` are unused.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
