---
op: center_from_symmetric_edges
dim: aoi
category: symmetry
in: image2d
out: table
examples: [poc_symmetry_self_reference_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# center_from_symmetric_edges — AOI `symmetry` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.center_from_symmetric_edges(image, threshold=0.08, sigma=1.0, min_span=6.0, mad_z=3.5, diagonals=False)` (実装を直接呼ぶなら `import symmetry2d; symmetry2d.center_from_symmetric_edges(image, threshold=0.08, sigma=1.0, min_span=6.0, mad_z=3.5, diagonals=False)`、台帳から引くなら `opsaoi.get("center_from_symmetric_edges")`)

## 使い方

対称な外側エッジ対の中点を頑健に集約し、2-D 中心を返す。

Parameters
----------
image : array-like, shape (H, W)
    グレー画像または region。各行・列のプロファイルを既存の
    :func:`measuring1d.measure_pos` でサブピクセル計測する。
threshold : float, default 0.08
    エッジ振幅の下限。画像ダイナミックレンジに対する比で、範囲は (0, 1]。
sigma : float, default 1.0
    1-D プロファイルを微分する前の Gaussian sigma [px]。範囲は [0, 10]。
min_span : float, default 6.0
    採用する外側エッジ対の最小間隔 [px]。範囲は (0, min(H,W)]。
mad_z : float, default 3.5
    中点を残す MAD 尺度。範囲は [1, 20]。
diagonals : bool, default False
    True なら ±45 度の走査線も中心候補に加える。

Returns
-------
dict
    ``center=(row,col)``、採用対数、MAD、走査方向別の中点を持つ table。

Notes
-----
片側の欠けは少数の中点だけを動かすため面積重心より頑健だが、欠けのない滑らかな
領域では全画素を使う重心の方が精密になり得る。対が 3 本未満、定数入力、対象が
画像端で切れる場合は ``ValueError``。内部模様の最外エッジが外形より強い場合や、
欠けが走査線の半数を超える場合は頑健集約でも救えない。

Liu, Hel-Or, Kaplan and Van Gool, Computational Symmetry in Computer Vision
and Computer Graphics, FnT CGV 5(1-2), 2010.

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

[reflection_axis](reflection_axis.md) · [rotational_symmetry](rotational_symmetry.md) · [symmetry_difference_map](symmetry_difference_map.md) · [symmetry_score](symmetry_score.md)

---
*Provenance: symmetry2d.py — AOI operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
