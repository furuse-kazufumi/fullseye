---
op: fit_circle_xld
dim: shape2d
category: descriptor
in: contour
out: table
gpu: なし
examples: [fit_circle_xld_bore]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# fit_circle_xld — SHAPE2D `descriptor` op

- **データ種**: `contour` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.fit_circle_xld(contour, method='geometric')` (実装を直接呼ぶなら `import fourierdesc; fourierdesc.fit_circle_xld(contour, method='geometric')`、台帳から引くなら `opsshape2d.get("fit_circle_xld")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

XLD 輪郭 1 本ごとに円を当てはめ、中心の行・列と半径を返す(``table``)。

HALCON ``fit_circle_contour_xld`` の Row / Column / Radius にあたる。進化 op の
``hx_fit_circle_contour`` は残差(正規化 feature)しか返さないので、輪郭から
**位置と大きさ**を読むのはこちら。座標は XLD と同じ **(row, col)**、単位は画素。

``method`` は ``"geometric"``(既定。点から円までの距離の二乗和を
Levenberg--Marquardt で最小化、Chernov & Lesort 2005 = ``measure.fit_circle_geometric``)
か ``"algebraic"``(Kåsa / Coope の代数的最小二乗 = ``measure.fit_circle``。
短い円弧では半径が小さく偏る)。返す dict の ``row``・``col``・``radius``・``rms``
(点の動径残差の二乗平均平方根)・``n_points`` は輪郭の並び順の list で、
``n_contours`` が当てた本数、``n_skipped`` が点が 3 個未満で飛ばした本数、
``method`` が使った方法。

空の入力(``contour`` が 0 要素 = 輪郭が 1 本も無い)は ``ValueError``。
拒否(``ValueError``): XLD の dict(``{"shape", "cs"}``)でない、未知の ``method``、
点が 3 個以上ある輪郭が 1 本も無い、非有限の座標、点が一直線に並ぶ(円が決まらない)。

## 詳しい使い方ガイド

- [shape_description_2d ファミリ ガイド](../guides/shape_description_2d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fit_circle_xld_bore](../../../../examples/fit_circle_xld_bore.py) — `py -3.11 examples/fit_circle_xld_bore.py`

## 型が繋がる次の op(`table` を入力に取れる)

[from_xld](from_xld.md)

## 同カテゴリ(`descriptor`)

[elliptic_fourier](elliptic_fourier.md) · [reconstruct](reconstruct.md) · [invariants](invariants.md) · [normalize](normalize.md) · [descriptor_distance](descriptor_distance.md) · [fourier_smooth](fourier_smooth.md) · [from_xld](from_xld.md) · [contour_fourier_complex](contour_fourier_complex.md)

---
*Provenance: fourierdesc.py — SHAPE2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
