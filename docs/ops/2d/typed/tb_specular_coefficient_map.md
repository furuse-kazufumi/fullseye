---
op: tb_specular_coefficient_map
dim: 2d
category: typed
in: rgbimage
out: image
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# tb_specular_coefficient_map — 2D `typed` op

- **データ種**: `rgbimage` → `image`
- **呼び出し**: `fullseye.apply(img, "tb_specular_coefficient_map", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

The scalar interface (specular) coefficient of the dichromatic model. → (H, W).

    The same decomposition as :func:`specular_diffuse_split`, returning the
    scalar ``m_s(x)`` instead of the coloured image ``m_s(x) * G``. That scalar
    is what an inspection routine thresholds: it is the amount of light the
    surface reflected *as a mirror does*, in the units of the input radiance,
    and it is zero wherever the surface behaved as a Lambertian body.

    ``specular_coefficient_map(...) * illuminant_unit`` equals the second return
    value of :func:`specular_diffuse_split` exactly, by construction — the two
    operators share one core.

    Arguments, guards and honest limits are identical to
    :func:`specular_diffuse_split` — including the fact that the two guards
    bound gross violations only.

    **Raises** ``ValueError``: exactly the same conditions as
    :func:`specular_diffuse_split` (invalid image, invalid illuminant,
    identically zero image, body colour parallel to the illuminant, either
    guard firing, fewer than 3 pixels on the uniform-body route, invalid
    *body_rgb*).

Typed bridge of the specular op ``specular_coefficient_map`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. ``a`` drives ``max_rank_ratio`` (default 0.1) and ``b`` drives ``max_negative_frac`` (default 0.02).

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
