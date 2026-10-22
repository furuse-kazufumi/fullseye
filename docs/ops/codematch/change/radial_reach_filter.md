---
op: radial_reach_filter
dim: codematch
category: change
in: image2d × image2d
out: table
examples: [poc_code_matching_breakdown]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# radial_reach_filter — CODEMATCH `change` op

- **データ種**: `image2d × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.radial_reach_filter(background, image, t_p=0.08, agree_thresh=0.625, max_reach=32, min_dirs=4, min_decided_fraction=0.01) -> 'dict'` (実装を直接呼ぶなら `import codematch; codematch.radial_reach_filter(background, image, t_p=0.08, agree_thresh=0.625, max_reach=32, min_dirs=4, min_decided_fraction=0.01) -> 'dict'`、台帳から引くなら `opscodematch.get("radial_reach_filter")`)

## 使い方

Radial Reach Filter(RRF)。背景と現在の画像を、8 方向の reach の符号で比べる。

背景 ``B`` の画素 ``p`` から方向 ``d_k`` へ 1, 2, … と進み、``|B(p + r d_k) - B(p)| >= t_p``
になる最初の ``r`` を reach ``r_k``(``max_reach`` まで。画像の外に出たらその方向は
無効)。符号 ``b_k = [B(p + r_k d_k) >= B(p)]``、現在の画像でも同じ位置の組で
``b'_k = [I(p + r_k d_k) >= I(p)]`` を作り、一致した方向の数を RRC とする。
有効な方向のうち一致した割合が ``agree_thresh`` 未満の画素を前景にする
(8 方向が全部有効なら、既定 0.625 は「一致 5 未満」)。

現在の画像に狭義単調増加の明るさの変換を掛けても、結果は 1 ビットも変わらない。
影(局所の掛け算)の内側も同じ理由で前景にならない。

fail-closed: 有効な方向が ``min_dirs`` 未満の画素は判定しない(``decided`` が False、
``rrc`` が -1、前景にもしない)。判定できた画素が ``min_decided_fraction`` 未満なら
ValueError(背景が平坦すぎて、変化を言えない)。

返り: ``foreground``(bool)、``decided``(bool)、``rrc``(一致した方向の数、
判定しない画素は -1)、``valid_dirs``、``agree_fraction``(判定しない画素は 1.0)、
``reach``((8, H, W)、無効は 0)、``decided_fraction``、``foreground_fraction``、
``refusal_margin``(判定できた割合 − ``min_decided_fraction``)。

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

## 同カテゴリ(`change`)

—

---
*Provenance: codematch.py — CODEMATCH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
