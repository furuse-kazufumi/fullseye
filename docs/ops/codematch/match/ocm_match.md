---
op: ocm_match
dim: codematch
category: match
in: image2d × image2d
out: table
examples: [poc_code_matching_breakdown]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# ocm_match — CODEMATCH `match` op

- **データ種**: `image2d × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.ocm_match(image, template, n_codes=16, grad_thresh=0.05, min_valid=32, min_valid_fraction=0.05) -> 'dict'` (実装を直接呼ぶなら `import codematch; codematch.ocm_match(image, template, n_codes=16, grad_thresh=0.05, min_valid=32, min_valid_fraction=0.05) -> 'dict'`、台帳から引くなら `opscodematch.get("ocm_match")`)

## 使い方

方向符号照合(OCM)。符号の巡回差の平均が最小の位置を返す。

相違度は画素ごとに ``D(m, n)``(m = テンプレート側、n = 画像側の符号):
両方有効なら巡回差 ``min(|m-n|, N-|m-n|)``、テンプレート側が無効なら 0、
画像側だけ無効なら ``N/4``。全画素の平均を ``N/2`` で割った相違度 ``h`` を
``dissimilarity_map`` に、``score = 1 - h``(1 が完全一致)を ``score_map`` に返す。
和は 4 倍して整数で数える(FFT の丸めを ``rint`` で消す)ので、同じ入力の答えは
環境によらず同じ。

**テンプレートの有効な符号が** ``max(min_valid, min_valid_fraction × 画素数)``
**に満たなければ ValueError**(平坦なテンプレートは位置を決めない)。

返り: ``row`` / ``col``(テンプレート中心)、``score``、``dissimilarity``、
``second_score``・``margin``(最良から離れた次点との差)、``valid_fraction``
(テンプレートの有効符号の割合)、``valid_required``・``refusal_margin``(拒否まで
あと何画素の余裕があるか)、``score_map``、``dissimilarity_map``。

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

[isc_match](isc_match.md) · [scc_match](scc_match.md)

---
*Provenance: codematch.py — CODEMATCH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
