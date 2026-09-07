---
op: surface_residual
dim: 3d
category: freeform
in: image2d × image2d × image2d × bspline_surface
out: measurement
examples: [bspline_freeform]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# surface_residual — 3D `freeform` op

- **データ種**: `image2d × image2d × image2d × bspline_surface` → `measurement`
- **呼び出し**: `import bspline_surf; bspline_surf.surface_residual(x, y, z, tck)` (または `ops3d.get("surface_residual")`)
- **台帳経由の戻り値**: `fullseye.ledger.surface_residual(...)` は**宣言 out 型 `measurement` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.surface_residual.raw(...)`、または `bspline_surf.surface_residual` を直接呼ぶ。
  - 本体の返り: `{"rms","max","pv"} → pv float`

## 使い方

散布データと曲面 tck の残差統計を返す(形状誤差=フィットからの逸脱)。

各サンプル位置で曲面高さを評価し、観測 z との差の RMS / 最大絶対値 / PV
(peak-to-valley = 最大 - 最小)を計測する。検査ではこれが自由曲面からの
ずれ量(打痕・うねり・欠肉)の定量指標になる。

Returns
-------
dict
    ``{"rms": float, "max": float, "pv": float}``。max は最大絶対残差、
    pv は符号付き残差の最大 - 最小(片側だけの凸/凹も捉える)。

補足:
- 残差の符号は ``resid = z - zhat``(観測 − 曲面)。正 = 曲面より高い(盛り上がり)、負 = 低い(欠肉)。``max`` は絶対値なので向きは分からず、向きが要るなら ``eval_bspline_surface`` で ``zhat`` を取り自分で差を取る。
- x, y, z は任意 shape を受け、内部で ``eval_bspline_surface(tck, x, y, grid=False)`` を通す(tck の種類検査もそこで行われ、曲線 tck や多項式 dict は ``ValueError``)。z と x の要素数が違うと numpy の形状エラーになる(専用の検査は無く、z が 1 要素だと黙って broadcast される)。
- 単位は z と同じ。``rms`` は全点の二乗平均平方根なので局所的な打痕は平均で薄まる。局所欠陥は ``max`` か ``pv`` で見る。
- 典型: ``fit_bspline_surface`` → 本 op。フィットに使った点で評価すると smooth が小さいほど残差は 0 に近づく(過適合の指標にもなる)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [bspline_freeform](../../../../examples_3d/bspline_freeform.py) — `py -3.11 examples_3d/bspline_freeform.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`freeform`)

[fit_bspline_surface](fit_bspline_surface.md) · [eval_bspline_surface](eval_bspline_surface.md) · [fit_bspline_curve](fit_bspline_curve.md) · [eval_bspline_curve](eval_bspline_curve.md)

---
*Provenance: bspline_surf.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
