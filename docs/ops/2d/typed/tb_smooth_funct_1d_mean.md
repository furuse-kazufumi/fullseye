---
op: tb_smooth_funct_1d_mean
dim: 2d
category: typed
in: signal
out: signal
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# tb_smooth_funct_1d_mean — 2D `typed` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `fullseye.apply(img, "tb_smooth_funct_1d_mean", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

![tb_smooth_funct_1d_mean: input → output](../../_fig/tb_smooth_funct_1d_mean.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![tb_smooth_funct_1d_mean: knob a sweep](../../_fig/tb_smooth_funct_1d_mean.a.jpg)

**つまみ b を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![tb_smooth_funct_1d_mean: knob b sweep](../../_fig/tb_smooth_funct_1d_mean.b.jpg)

**段階**(前置きの op → この op。左から順):

![tb_smooth_funct_1d_mean: stages](../../_fig/tb_smooth_funct_1d_mean.chain.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![tb_smooth_funct_1d_mean: other inputs](../../_fig/tb_smooth_funct_1d_mean.inputs.jpg)

## 使い方

Iterated moving-average smoothing (HALCON ``smooth_funct_1d_mean``).

    Applies a length-*size* uniform (box) filter *iterations* times with
    ``nearest`` (edge-replicating) boundary handling. Repeated box filtering
    approaches a Gaussian (central limit theorem).

    :param y: 1-D function, at least 1 sample.
    :param size: window length in samples; truncated to int, must be >= 1.
        **Even sizes are accepted but shift the window origin by half a sample**
        (scipy's origin convention) — prefer odd sizes for a symmetric window.
    :param iterations: number of passes; truncated to int, must be >= 0.
        ``iterations=0`` returns the (float64-coerced) input unchanged.
    :returns: smoothed float64 array, same length as *y*.
    :raises ValueError: non-1-D / NaN / Inf input, empty input, ``size < 1``,
        or ``iterations < 0``.

Typed bridge of the 1d op ``smooth_funct_1d_mean`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. ``a`` drives ``size`` (default 3) and ``b`` drives ``iterations`` (default 1).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
img_to_signal 0.50 0.50
tb_smooth_funct_1d_mean 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

次の例は元の台帳 op `smooth_funct_1d_mean` を呼ぶもの。この橋渡し op は同じ実装を `fn(v, a, b)` 規約に合わせただけなので、挙動はそのまま当てはまる(呼び出し形だけ違う)。
- [poc_weld_bead_profile](../../../../examples/poc_weld_bead_profile.py) — `py -3.11 examples/poc_weld_bead_profile.py`
- [signal_funct1d](../../../../examples/signal_funct1d.py) — `py -3.11 examples/signal_funct1d.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[identity](../misc/identity.md) · [tb_create_funct_1d_array](tb_create_funct_1d_array.md) · [tb_smooth_funct_1d_gauss](tb_smooth_funct_1d_gauss.md) · [tb_derivate_funct_1d](tb_derivate_funct_1d.md) · [tb_integrate_funct_1d](tb_integrate_funct_1d.md) · [tb_zero_crossings_funct_1d](tb_zero_crossings_funct_1d.md) · [tb_abs_funct_1d](tb_abs_funct_1d.md) · [tb_negate_funct_1d](tb_negate_funct_1d.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md) · [tb_voxel_grid_downsample](tb_voxel_grid_downsample.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
