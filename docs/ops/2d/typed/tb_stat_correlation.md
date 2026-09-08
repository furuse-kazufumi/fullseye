---
op: tb_stat_correlation
dim: 2d
category: typed
in: matrix
out: matrix
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# tb_stat_correlation — 2D `typed` op

- **データ種**: `matrix` → `matrix`
- **呼び出し**: `fullseye.apply(img, "tb_stat_correlation", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

![tb_stat_correlation: input → output](../../_fig/tb_stat_correlation.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

*つまみ a は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![tb_stat_correlation: stages](../../_fig/tb_stat_correlation.chain.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![tb_stat_correlation: other inputs](../../_fig/tb_stat_correlation.inputs.jpg)

## 使い方

Pearson correlation matrix of ``(N, D)`` observations → ``(D, D)``.

    Same orientation as :func:`stat_covariance` (rows = observations).
    Entries are clipped to ``[-1, 1]`` (floating-point can overshoot by an
    ulp), the diagonal is exactly ``1`` and the matrix exactly symmetric by
    construction.

    **A constant column raises ``ValueError``** (naming the column) instead of
    yielding NaN: correlation with a zero-variance variable is mathematically
    undefined (0/0), and a NaN that surfaces three ops downstream is the
    classic zero-division bug family this module fails closed against. Drop or
    perturb the constant column deliberately if that is what you mean.

    HALCON: no public tuple operator (see :func:`stat_covariance`).

Typed bridge of the math op ``stat_correlation`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. This op has no tunable parameter; ``a`` and ``b`` are unused.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
img_to_matrix 0.50 0.50
tb_stat_correlation 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

次の例は元の台帳 op `stat_correlation` を呼ぶもの。この橋渡し op は同じ実装を `fn(v, a, b)` 規約に合わせただけなので、挙動はそのまま当てはまる(呼び出し形だけ違う)。
- [math_metrology](../../../../examples/math_metrology.py) — `py -3.11 examples/math_metrology.py`
- [poc_colocalization_crosstalk](../../../../examples/poc_colocalization_crosstalk.py) — `py -3.11 examples/poc_colocalization_crosstalk.py`
- [poc_ct_fidelity](../../../../examples/poc_ct_fidelity.py) — `py -3.11 examples/poc_ct_fidelity.py`
- [poc_machine_condition_fusion](../../../../examples/poc_machine_condition_fusion.py) — `py -3.11 examples/poc_machine_condition_fusion.py`
- [poc_thermal_radiometry](../../../../examples/poc_thermal_radiometry.py) — `py -3.11 examples/poc_thermal_radiometry.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[identity](../misc/identity.md) · [tb_mat_pinv](tb_mat_pinv.md) · [tb_mat_cond](tb_mat_cond.md) · [tb_stat_covariance](tb_stat_covariance.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md) · [tb_voxel_grid_downsample](tb_voxel_grid_downsample.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
