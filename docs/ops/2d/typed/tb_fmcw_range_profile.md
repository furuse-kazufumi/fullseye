---
op: tb_fmcw_range_profile
dim: 2d
category: typed
in: beatcube
out: signal
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# tb_fmcw_range_profile — 2D `typed` op

- **データ種**: `beatcube` → `signal`
- **呼び出し**: `fullseye.apply(img, "tb_fmcw_range_profile", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

![tb_fmcw_range_profile: input → output](../../_fig/tb_fmcw_range_profile.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

*つまみ a は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![tb_fmcw_range_profile: stages](../../_fig/tb_fmcw_range_profile.chain.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![tb_fmcw_range_profile: other inputs](../../_fig/tb_fmcw_range_profile.inputs.jpg)

## 使い方

Range-only profile: the fast-time FFT magnitude, averaged over the rest.

    The 1-D marginal of :func:`range_doppler_map` — what a static scene needs,
    and what a single chirp can give. Magnitudes are averaged (never the complex
    values) over chirps and antennas, so the average is independent of the
    target's velocity and angle: ``|FFT|`` does not rotate with the Doppler
    phase, only the phase does.

    Bin ``j`` is ``j * c*f_s/(2*S*N_s)`` metres. With ``normalize=True`` a
    bin-centred target of amplitude ``a`` peaks at exactly ``a``.

    *chirp* / *antenna* select one slice instead of averaging. Returns a 1-D
    float64 array of length ``n_samples`` — a plain signal, so :mod:`dsp` and
    :mod:`funct1d` (``find_peaks``, ``smooth_funct_1d_gauss``, ``spectrum``)
    apply to it directly.

    **Raises** ``ValueError``: as :func:`range_doppler_map`, plus an
    out-of-bounds *chirp* index.

Typed bridge of the rangedoppler op ``fmcw_range_profile`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. This op has no tunable parameter; ``a`` and ``b`` are unused.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
img_to_beatcube 0.50 0.50
tb_fmcw_range_profile 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

次の例は元の台帳 op `fmcw_range_profile` を呼ぶもの。この橋渡し op は同じ実装を `fn(v, a, b)` 規約に合わせただけなので、挙動はそのまま当てはまる(呼び出し形だけ違う)。
- [fmcw_range_doppler](../../../../examples/fmcw_range_doppler.py) — `py -3.11 examples/fmcw_range_doppler.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[identity](../misc/identity.md) · [tb_create_funct_1d_array](tb_create_funct_1d_array.md) · [tb_smooth_funct_1d_gauss](tb_smooth_funct_1d_gauss.md) · [tb_smooth_funct_1d_mean](tb_smooth_funct_1d_mean.md) · [tb_derivate_funct_1d](tb_derivate_funct_1d.md) · [tb_integrate_funct_1d](tb_integrate_funct_1d.md) · [tb_zero_crossings_funct_1d](tb_zero_crossings_funct_1d.md) · [tb_abs_funct_1d](tb_abs_funct_1d.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md) · [tb_voxel_grid_downsample](tb_voxel_grid_downsample.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
