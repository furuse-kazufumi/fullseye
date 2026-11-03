---
op: reflection_axis
dim: aoi
category: symmetry
in: image2d
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# reflection_axis — AOI `symmetry` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.reflection_axis(image, angle_step=2.0, offset_search=4.0)` (実装を直接呼ぶなら `import symmetry2d; symmetry2d.reflection_axis(image, angle_step=2.0, offset_search=4.0)`、台帳から引くなら `opsaoi.get("reflection_axis")`)

## 使い方

線対称な 2-D 画像から反射軸の角度とオフセットを推定する。

Parameters
----------
image : array-like, shape (H, W)
    グレー画像または region。回転済みの試験像はグレーを補間してから二値化する。
angle_step : float, default 2.0
    粗い角度走査の刻み [degree]。範囲は [0.25, 15]。最良点は連続最適化で詰める。
offset_search : float, default 4.0
    エッジ対中心から軸法線方向に探索する半幅 [px]。範囲は [0.5, min(H,W)/3]。

Returns
-------
dict
    ``angle_deg`` は +col 軸から +row 方向へ測る [0,180) 度、``offset_px`` は
    画像中心から軸の法線方向への符号付き距離。score、2位との差 margin も返す。

Notes
-----
線形補間した鏡像との正規化絶対差を最小化する。定数入力、外側エッジ対が足りない
入力は ``ValueError``。円・正方形・回転対称と線対称を併せ持つ図形では軸が多義で、
小さい ``margin`` がその警告になる。画像外で切れた対象や反射で等価な内部模様も
一意な軸を保証しない。

Liu et al., Computational Symmetry in Computer Vision and Computer Graphics,
FnT CGV 5(1-2), 2010.

## 詳しい使い方ガイド

- [aoi_frontend ファミリ ガイド](../guides/aoi_frontend.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[symmetry_difference_map](symmetry_difference_map.md) · [symmetry_score](symmetry_score.md)

## 同カテゴリ(`symmetry`)

[center_from_symmetric_edges](center_from_symmetric_edges.md) · [rotational_symmetry](rotational_symmetry.md) · [symmetry_difference_map](symmetry_difference_map.md) · [symmetry_score](symmetry_score.md)

---
*Provenance: symmetry2d.py — AOI operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
