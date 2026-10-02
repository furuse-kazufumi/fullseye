---
op: swt_map
dim: text
category: stroke
in: image2d
out: table
examples: [poc_text_region_truth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# swt_map — TEXT `stroke` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.swt_map(img, dark_on_light: 'bool' = True, sigma: 'float' = 1.0, max_width: 'int' = 64, angle_tol: 'float' = 0.5235987755982988)` (実装を直接呼ぶなら `import textregion; textregion.swt_map(img, dark_on_light: 'bool' = True, sigma: 'float' = 1.0, max_width: 'int' = 64, angle_tol: 'float' = 0.5235987755982988)`、台帳から引くなら `opstext.get("swt_map")`)

## 使い方

Stroke Width Transform —— 各画素に、その画素を含むストロークの幅を書く。

文字側の境界画素から、勾配の向きに沿って文字の内側へ光線を飛ばし、向かい合う境界
画素(勾配がほぼ逆向き)に当たったら、光線上の全画素に幅(境界画素の中心間距離 + 1)
を書く(既に小さい値があれば小さい方)。Epshtein 2010 §3 の手順で、2 回目の走査で
光線上の中央値より大きい値を中央値に置き換える(角の過大を抑える)。エッジの規約は
:func:`_edges_and_gradient` に書いた(矩形ストロークで幅が厳密に整数になる)。

Returns dict: ``swt``(幅の配列、ストローク外は 0)/ ``edges`` / ``n_rays`` /
``n_hits``(向かい合うエッジに当たった光線の数)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_text_region_truth](../../../../examples/poc_text_region_truth.py) — `py -3.11 examples/poc_text_region_truth.py`

## 型が繋がる次の op(`table` を入力に取れる)

[text_lines](../layout/text_lines.md)

## 同カテゴリ(`stroke`)

—

---
*Provenance: textregion.py — TEXT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
