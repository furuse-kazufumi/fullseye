---
op: tb_lf_refocus
dim: 2d
category: typed
in: lightfield
out: image
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# tb_lf_refocus — 2D `typed` op

- **データ種**: `lightfield` → `image`
- **呼び出し**: `fullseye.apply(img, "tb_lf_refocus", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

![tb_lf_refocus: input → output](../../_fig/tb_lf_refocus.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

*つまみ a は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![tb_lf_refocus: stages](../../_fig/tb_lf_refocus.chain.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![tb_lf_refocus: other inputs](../../_fig/tb_lf_refocus.inputs.jpg)

## 使い方

Shift-and-add refocus: the synthetic-aperture image focused at *slope*.

    Every view ``(v, u)`` is shifted by ``(-s*(v - v_c), -s*(u - u_c))`` — the
    **minus** undoes the parallax of a point at slope ``s`` — and the shifted
    views are averaged. Points at that slope add coherently and stay sharp;
    everything else is smeared by an amount proportional to its slope
    difference times the angular baseline. ``slope=0`` is the plane the array
    was already focused on and returns the plain average of the views.

    Ground truth it reproduces exactly (pinned in ``tests/test_lightfield.py``):
    a single-layer field synthesised at slope ``s0`` and refocused at ``s0``
    with ``edge="wrap"`` and an integer ``s0`` returns the original texture to
    5.6e-16; sweeping the slope, the variance of the result peaks at ``s0``
    (measured exactly on the sweep grid in all 18 texture/slope combinations
    listed in the module docstring), and refocusing at ``-s0`` does *not* —
    which is the check that catches a flipped shift sign.

    Returns a ``(H, W)`` 2-D image.

    **Raises** ``ValueError``: *lf* not a valid light field, a non-finite or
    over-large *slope* (:data:`MAX_ABS_SLOPE`), unknown *interp* / *edge*.

Typed bridge of the lightfield op ``lf_refocus`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. This op has no tunable parameter; ``a`` and ``b`` are unused.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
img_to_lightfield 0.50 0.50
tb_lf_refocus 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

次の例は元の台帳 op `lf_refocus` を呼ぶもの。この橋渡し op は同じ実装を `fn(v, a, b)` 規約に合わせただけなので、挙動はそのまま当てはまる(呼び出し形だけ違う)。
- [lightfield_depth](../../../../examples/lightfield_depth.py) — `py -3.11 examples/lightfield_depth.py`
- [poc_lightfield_depth](../../../../examples/poc_lightfield_depth.py) — `py -3.11 examples/poc_lightfield_depth.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md) · [tb_voxel_grid_downsample](tb_voxel_grid_downsample.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
