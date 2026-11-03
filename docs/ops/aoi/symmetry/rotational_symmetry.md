---
op: rotational_symmetry
dim: aoi
category: symmetry
in: image2d
out: table
examples: [poc_symmetry_self_reference_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# rotational_symmetry — AOI `symmetry` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.rotational_symmetry(image, max_order=12, angular_samples=720, score_threshold=0.18)` (実装を直接呼ぶなら `import symmetry2d; symmetry2d.rotational_symmetry(image, max_order=12, angular_samples=720, score_threshold=0.18)`、台帳から引くなら `opsaoi.get("rotational_symmetry")`)

## 使い方

180 度の点対称中心と極座標自己相関による回転対称次数を返す。

Parameters
----------
image : array-like, shape (H, W)
    グレー画像または region。
max_order : int, default 12
    調べる最大次数。範囲は [2, 36]。
angular_samples : int, default 720
    極座標の角度標本数。範囲は [180, 2880] で、2..max_order の公倍数を推奨。
score_threshold : float, default 0.18
    正規化 RMS 差を対称とみなす上限。範囲は (0, 1)。

Returns
-------
dict
    ``center=(row,col)``、``point_symmetric``、``order``、各次数の polar
    autocorrelation と差を持つ table。order=1 は非回転対称を表す。

Notes
-----
中心は外側エッジ対から推定し、その中心で極座標画像を作る。角度方向に 360/n 度
循環シフトした自己相関を測り、しきい値を満たす最大 n を次数とする。定数入力、中心が
求まらない入力は ``ValueError``。同心円のように連続回転対称な像、角度標本数で割り切れ
ない次数、中心から画像端まで対象が切れる像では次数は多義または不安定になる。

Loy and Zelinsky, Fast radial symmetry for detecting points of interest,
IEEE TPAMI 25(8), 2003; Liu et al., FnT CGV 5(1-2), 2010.

## 詳しい使い方ガイド

- [aoi_frontend ファミリ ガイド](../guides/aoi_frontend.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_symmetry_self_reference_inspection](../../../../examples/poc_symmetry_self_reference_inspection.py) — `py -3.11 examples/poc_symmetry_self_reference_inspection.py`

## 型が繋がる次の op(`table` を入力に取れる)

[symmetry_difference_map](symmetry_difference_map.md) · [symmetry_score](symmetry_score.md)

## 同カテゴリ(`symmetry`)

[center_from_symmetric_edges](center_from_symmetric_edges.md) · [reflection_axis](reflection_axis.md) · [symmetry_difference_map](symmetry_difference_map.md) · [symmetry_score](symmetry_score.md)

---
*Provenance: symmetry2d.py — AOI operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
