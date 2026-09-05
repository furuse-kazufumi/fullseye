---
op: tb_quat_normalize_image
dim: 2d
category: typed
in: qimage
out: qimage
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# tb_quat_normalize_image — 2D `typed` op

- **データ種**: `qimage` → `qimage`
- **呼び出し**: `fullseye.apply(img, "tb_quat_normalize_image", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Per-pixel normalisation to unit modulus. → (H, W, 4).

    **Fail-closed on a zero pixel.** A quaternion image routinely contains exact
    zeros — a black pixel is ``(0,0,0,0)`` — so the case is not hypothetical, and
    a zero quaternion has no direction to normalise towards. It is refused by
    name, with the count and the first offending pixel's row and column in the
    message, rather than divided by ``norm + eps``: that idiom returns zero, and
    a zero used as a rotor becomes the **identity rotation** with no exception
    and no NaN to mark it. (``pose_quat.quat_normalize`` did exactly that until
    2026-09-01 and now fail-closes too; see :func:`quat_color_rotate`.)

    **Raises** ``ValueError``: any pixel has modulus 0.

Typed bridge of the quat op ``quat_normalize_image`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. This op has no tunable parameter; ``a`` and ``b`` are unused.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`qimage` を入力に取れる)

[identity](../misc/identity.md) · [tb_quaternion_to_rgb](tb_quaternion_to_rgb.md) · [tb_quat_norm](tb_quat_norm.md) · [tb_quat_conjugate_image](tb_quat_conjugate_image.md) · [tb_monogenic_amplitude](tb_monogenic_amplitude.md) · [tb_monogenic_phase](tb_monogenic_phase.md) · [tb_monogenic_orientation](tb_monogenic_orientation.md) · [tb_quat_color_rotate](tb_quat_color_rotate.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
