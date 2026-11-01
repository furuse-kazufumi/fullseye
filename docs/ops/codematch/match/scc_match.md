---
op: scc_match
dim: codematch
category: match
in: image2d × image2d
out: table
gpu: なし
examples: [poc_code_matching_breakdown]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# scc_match — CODEMATCH `match` op

- **データ種**: `image2d × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.scc_match(image, template, flat_thresh=0.01, min_valid=32, min_mask_fraction=None, mask_extension=True, z_mask=4.0) -> 'dict'` (実装を直接呼ぶなら `import codematch; codematch.scc_match(image, template, flat_thresh=0.01, min_valid=32, min_mask_fraction=None, mask_extension=True, z_mask=4.0) -> 'dict'`、台帳から引くなら `opscodematch.get("scc_match")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

選択的相関係数(SCC)。増分符号の一致する画素だけで正規化相関を取る。

テンプレートの列を (0,1), (2,3), … の組にし、組ごとに右の画素が左以上かの符号
``b`` を作る。画像の窓の同じ組の符号 ``b'`` と一致すれば、その組の 2 画素の
基本マスク ``c = 1``、違えば 0。
``r = Σ c (f - f̄)(g - ḡ) / sqrt(Σ c (f - f̄)² · Σ c (g - ḡ)²)``、
``f̄`` と ``ḡ`` は窓とテンプレートの**全画素**の平均。マスクが全部 1 なら NCC と
厳密に一致する(列数が奇数なら最後の列は組を作らず、マスク 0)。

``mask_extension=True``(既定、論文の 3 章の拡張マスク)は、基本マスクの要素を
2 行 × 2 組(画素で 2 × 4)ずつ束ね、4 つのうち 2 つ以上が不一致なら 4 つとも外し、
そうでなければ 4 つとも使う。不一致の起こる確率が ``p`` の所で、外される確率は
``1 - (1-p)^4 - 4 p (1-p)^3``(p = 0.5 の遮蔽部で 0.6875)。端の余りの要素は基本マスクのまま。
``False`` は基本マスク(全位置を FFT で数えるので速い)。

fail-closed:
* テンプレートの組の増分のうち ``|Δ| > flat_thresh`` のものが ``min_valid`` 未満 → ValueError。
* 使った画素が窓の ``min_mask_fraction`` 未満の位置、窓の選ばれた画素の
  分散が 0 の位置は採点しない(``valid_map`` が False、``score_map`` は -1)。
* 採点できる位置が 1 つも無ければ ValueError。

``min_mask_fraction=None``(既定)は、**無相関の位置で期待される使用率**に
``z_mask`` 標準偏差を足した値を床にする。無相関なら増分符号は半々で一致するので、
基本マスクの使用率の期待値は 1/2、拡張マスクは 4 要素の群で
``(1/2)^4 + 4 (1/2)^4 = 5/16``。標準偏差は群を独立な試行とみた 2 項分布の値。
★この床が無いと、SCC は「たまたま符号の合った画素だけ」を選んだ偽の位置で
相関が 1 近くまで上がり、NCC より先に壊れる(選択の偏り。PoC で実測)。
この床は論文の式には無く、論文の統計モデル(無相関で 0.5)から足した fail-closed。

返り: ``row`` / ``col``、``score``、``mask_fraction``(最良位置で使った画素の割合)、
``mask``(最良位置のマスク、テンプレートと同じ形)、``score_map``、``valid_map``、
``mask_fraction_map``、``refusal_margin``(テンプレートの組の余裕)。

## 詳しい使い方ガイド

- [robust_code_matching ファミリ ガイド](../guides/robust_code_matching.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_code_matching_breakdown](../../../../examples/poc_code_matching_breakdown.py) — `py -3.11 examples/poc_code_matching_breakdown.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`match`)

[ocm_match](ocm_match.md) · [isc_match](isc_match.md)

---
*Provenance: codematch.py — CODEMATCH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
