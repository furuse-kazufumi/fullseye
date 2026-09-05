---
op: tb_quat_color_filter
dim: 2d
category: typed
in: qimage
out: qimage
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# tb_quat_color_filter — 2D `typed` op

- **データ種**: `qimage` → `qimage`
- **呼び出し**: `fullseye.apply(img, "tb_quat_color_filter", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Keep or remove one colour direction, exactly. → (H, W, 4).

    ``mode="remove"`` returns ``v - (v.g) g`` for the unit RGB direction ``g``:
    the component along ``g`` is **exactly zero everywhere afterwards**, to
    machine precision (measured max residual 5.8e-16 and 6.5e-16 on two random
    colour images — seed-dependent only at the 1e-16 level),
    and ``remove + keep`` reproduces the input to **0.0** exactly.
    ``mode="keep"`` returns the complementary ``(v.g) g``. The scalar part is
    passed through untouched in both.

    **There is no default mode.** The two are opposites, both return a valid
    picture, and neither raises — so choosing for the caller would be a coin flip
    that never announces itself.

    Not a new algorithm, and this docstring will not pretend otherwise
    -----------------------------------------------------------------
    The ``remove`` branch **is** the specular-invariant projection of Mallick et
    al. (2005), which this repository already implements as
    ``specularity.specular_free_transform`` for the ``rgbimage`` sort. Rather
    than write the same three lines twice, this operator *delegates* to it — so
    agreement between the two sorts is by construction rather than by luck, and a
    future fix in one is a fix in both. What is added here is the ``keep``
    branch (which has no counterpart there) and the ``qimage`` sort, so the
    projection composes with :func:`quat_color_rotate` and :func:`qft2`.

    What this can do that a channelwise pipeline cannot
    ---------------------------------------------------
    A per-channel filter applies a diagonal matrix, and ``I - g g^T`` is diagonal
    only when ``g`` is a coordinate axis. For ``g = (1,1,1)/sqrt(3)`` — remove
    the grey axis, i.e. keep only chromatic content — the *best possible*
    diagonal approximation is off by ``||P - diag(P)||_2 = 0.666667`` in operator
    norm. Concretely, a pure red pixel ``(1, 0, 0)`` must become
    ``(0.666667, -0.333333, -0.333333)``; the best diagonal filter can only reach
    ``(0.666667, 0, 0)``, an error of ``0.471405`` — it cannot put anything into
    the green and blue channels, because it multiplies each channel by a number
    and both start at zero. The impossibility is structural, not a tuning gap.
    (A full 3x3 colour matrix, of course, does it exactly; see
    :func:`quat_color_rotate` for that half of the accounting.)

    **Raises** ``ValueError``: *qimage* is not a valid ``(H, W, 4)`` field;
    *direction_rgb* is not a finite non-zero 3-vector; *mode* is not
    ``'remove'`` / ``'keep'``.

Typed bridge of the quat op ``quat_color_filter`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. This op has no tunable parameter; ``a`` and ``b`` are unused.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`qimage` を入力に取れる)

[identity](../misc/identity.md) · [tb_quaternion_to_rgb](tb_quaternion_to_rgb.md) · [tb_quat_norm](tb_quat_norm.md) · [tb_quat_conjugate_image](tb_quat_conjugate_image.md) · [tb_quat_normalize_image](tb_quat_normalize_image.md) · [tb_monogenic_amplitude](tb_monogenic_amplitude.md) · [tb_monogenic_phase](tb_monogenic_phase.md) · [tb_monogenic_orientation](tb_monogenic_orientation.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
