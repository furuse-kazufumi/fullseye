---
op: fit_bspline_curve
dim: 3d
category: freeform
in: points
out: bspline_curve
examples: [bspline_freeform]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# fit_bspline_curve — 3D `freeform` op

- **データ種**: `points` → `bspline_curve`
- **呼び出し**: `import bspline_surf; bspline_surf.fit_bspline_curve(points, smooth=0.0, k=3, nest=None)` (または `ops3d.get("fit_bspline_curve")`)

## 使い方

順序付き点列(M,D)に B スプライン曲線をフィット(splprep, パラメトリック)。

シーム/エッジ/計測プローブ軌跡など「並び順が意味を持つ」点列を滑らかな
パラメトリック曲線 r(u), u∈[0,1] として復元する。z=f(x,y) と違い多価
(折り返し・ループ)な形も表せる。

Parameters
----------
points : array_like, shape (M, D)
    順序付き頂点。D=3 が典型(3D 曲線)だが 2D 以上を許容。
smooth : float
    平滑化係数 s。0.0 で全点通過(補間)、大きいほど滑らか。
k : int
    次数(既定 3=三次)。点数が k+1 未満なら自動で下げる。
nest : int or None
    節点数の上限(splprep へそのまま渡す)。None で自動。

Returns
-------
tck : tuple
    ``(t, c, k)``。eval_bspline_curve に渡す。

Raises
------
ValueError
    点数が 2 未満、次元不整合、非有限値、または重複/縮退で splprep が
    曲線を返せない場合。

補足:
- 既定 ``smooth=0.0`` は補間(全点通過)。曲面側の既定(点数からの自動値)と違うので、ノイズ点列は明示的に ``smooth`` を与える。パラメータ u は ``splprep`` の既定(弦長に比例して [0,1] に正規化)。
- 次数 k は ``k >= m`` のとき ``m-1`` に無言で下げる(2 点なら直線)。
- 連続する重複点があると ``splprep`` が失敗し ``ValueError`` になる。前段で重複を除くか ``resample_uniform`` で等間隔化する。
- 返す tck は ``[t, c, k]`` の list(c は D 本の係数配列のリスト)。``eval_bspline_curve`` に渡す。閉曲線としては扱わない(端点は開いたまま)。
- 決定論的(乱数なし)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [bspline_freeform](../../../../examples_3d/bspline_freeform.py) — `py -3.11 examples_3d/bspline_freeform.py`

## 型が繋がる次の op(`bspline_curve` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [eval_bspline_curve](eval_bspline_curve.md)

## 同カテゴリ(`freeform`)

[fit_bspline_surface](fit_bspline_surface.md) · [eval_bspline_surface](eval_bspline_surface.md) · [surface_residual](surface_residual.md) · [eval_bspline_curve](eval_bspline_curve.md)

---
*Provenance: bspline_surf.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
