---
op: fit_bspline_surface
dim: 3d
category: freeform
in: image2d × image2d × image2d
out: bspline_surface
examples: [bspline_freeform]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# fit_bspline_surface — 3D `freeform` op

- **データ種**: `image2d × image2d × image2d` → `bspline_surface`
- **呼び出し**: `import fullseye as fs; fs.ledger.fit_bspline_surface(x, y, z, kx=3, ky=3, smooth=None)` (実装を直接呼ぶなら `import bspline_surf; bspline_surf.fit_bspline_surface(x, y, z, kx=3, ky=3, smooth=None)`、台帳から引くなら `ops3d.get("fit_bspline_surface")`)

## 使い方

散布 (x, y, z) に双三次(既定)B スプライン曲面を最小二乗フィット(bisplrep)。

Parameters
----------
x, y, z : array_like
    同数の散布サンプル座標と高さ。任意形状で与えてよく内部で 1 次元化する。
kx, ky : int
    x/y 方向の B スプライン次数(1=線形, 3=三次)。点数が (kx+1)*(ky+1) に
    満たない場合は自動で下げる(縮退回避)。
smooth : float or None
    平滑化係数 s。None は点数ベースの自動値(``_auto_surface_smooth``)。
    0.0 で全点通過(補間寄り=過適合しやすい)、大きいほど滑らか。

Returns
-------
tck : list
    ``[tx, ty, c, kx, ky]``。eval_bspline_surface / surface_residual に渡す。

Raises
------
ValueError
    点数が線形曲面にすら足りない(m<4)、x/y/z の長さ不一致、非有限値、
    あるいは共線・重複による FITPACK 縮退で近似が得られない場合。

補足(実装の裏取り):
- 座標系は自由: x, y は任意の平面座標(row/col でも実寸でも可)、z は高さ。3 配列は ``ravel`` で 1 次元化するので格子入力でも散布入力でも同じに扱う。
- 次数の自動降格は ``(kx+1)*(ky+1) > m`` の間、大きい方(同点なら kx)を 1 ずつ下げ、両方 1 になったら止まる。降格は例外でなく無言で行われるので、実際の次数は返り値 ``tck[3]``, ``tck[4]`` で確認できる。
- ``smooth=None`` の自動値は ``max(0, m - sqrt(2m))``(FITPACK の推奨)。z のノイズ分散が 1 相当という前提の式なので、z の単位が小さく残差二乗和が小さいデータでは過平滑になりやすい。その場合は明示的に小さい ``smooth`` を渡す。
- FITPACK の警告(反復打ち切り等)は握り潰して tck を返す。例外はすべて ``ValueError`` に翻訳し、係数が空のときも ``ValueError``。
- 決定論的(乱数なし)。
- 後段は ``eval_bspline_surface``(評価)と ``surface_residual``(逸脱量)。大域的な低次のうねりだけで良ければ ``fit_poly_surface`` / ``eval_poly_surface`` があるが、tck と多項式 dict は互換でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [bspline_freeform](../../../../examples_3d/bspline_freeform.py) — `py -3.11 examples_3d/bspline_freeform.py`

## 型が繋がる次の op(`bspline_surface` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [eval_bspline_surface](eval_bspline_surface.md) · [surface_residual](surface_residual.md)

## 同カテゴリ(`freeform`)

[eval_bspline_surface](eval_bspline_surface.md) · [surface_residual](surface_residual.md) · [fit_bspline_curve](fit_bspline_curve.md) · [eval_bspline_curve](eval_bspline_curve.md)

---
*Provenance: bspline_surf.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
