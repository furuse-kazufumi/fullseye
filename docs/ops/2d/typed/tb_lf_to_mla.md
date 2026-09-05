---
op: tb_lf_to_mla
dim: 2d
category: typed
in: lightfield
out: image
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# tb_lf_to_mla — 2D `typed` op

- **データ種**: `lightfield` → `image`
- **呼び出し**: `fullseye.apply(img, "tb_lf_to_mla", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Re-interleave a light field into a microlens-array raw frame (exact inverse).

    Inverse of :func:`lf_from_mla` with ``offset=(0, 0)``: the returned frame has
    shape ``(H*V, W*U)`` and puts ``L[v, u, t, s]`` back at raw pixel
    ``(t*V + v, s*U + u)``. ``lf_from_mla(lf_to_mla(L), (V, U))`` returns ``L``
    bit-for-bit (verified with ``np.array_equal``), which is the cheapest
    possible check that the decode's index arithmetic has no off-by-one.

    **Raises** ``ValueError``: *lf* not 4-D / non-finite / over the shape and
    element caps (see :func:`lf_from_mla`), and a raw frame whose side would
    exceed ``MAX_SPATIAL * MAX_ANGULAR``.

Typed bridge of the lightfield op ``lf_to_mla`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. This op has no tunable parameter; ``a`` and ``b`` are unused.

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
