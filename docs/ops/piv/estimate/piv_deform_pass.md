---
op: piv_deform_pass
dim: piv
category: estimate
in: image2d × image2d × flow2d
out: flow2d
examples: [piv_field_analysis_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# piv_deform_pass — PIV `estimate` op

- **データ種**: `image2d × image2d × flow2d` → `flow2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.piv_deform_pass(a, b, flow, info, window=32, overlap=0.5, peak='gauss3', window_func='hann', order=3)` (実装を直接呼ぶなら `import pivops; pivops.piv_deform_pass(a, b, flow, info, window=32, overlap=0.5, peak='gauss3', window_func='hann', order=3)`、台帳から引くなら `opspiv.get("piv_deform_pass")`)
- **台帳経由の戻り値**: `fullseye.ledger.piv_deform_pass(...)` は**宣言 out 型 `flow2d` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.piv_deform_pass.raw(...)`、または `pivops.piv_deform_pass` を直接呼ぶ。
  - 本体の返り: `(flow, info) -> flow2d`

## 使い方

窓変形つきの 1 段。予測変位で**画像そのものを歪めてから**相関を取る。

整数ずらし(:func:`piv_cross_correlate` の ``shift``)は、窓の中で変位が
一定という仮定を置く。回転やせん断のように**窓の中で変位が変わる**場では
相関ピークが潰れるので、2 枚を予測の半分ずつ逆向きに歪めてから相関する
(中央差分の変形)。

Args:
    a, b: 画像対。
    flow: 予測変位 ``(2, h, w)``(``piv_multipass`` などの出力)。
    info: その ``info``(窓中心の座標が要る)。
    window / overlap / peak / window_func: 新しい段の設定。
    order: 変形に使う補間の次数(3 = 3 次スプライン)。
Returns:
    ``(flow (2, h', w'), info)``。返る変位は**元の画像座標での総変位**。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [piv_field_analysis_tour](../../../../examples/piv_field_analysis_tour.py) — `py -3.11 examples/piv_field_analysis_tour.py`

## 型が繋がる次の op(`flow2d` を入力に取れる)

[piv_outlier_mask](../validate/piv_outlier_mask.md) · [piv_replace_outliers](../validate/piv_replace_outliers.md) · [piv_vorticity](../field/piv_vorticity.md) · [piv_divergence](../field/piv_divergence.md) · [piv_flow_magnitude](../field/piv_flow_magnitude.md) · [piv_to_velocity](../field/piv_to_velocity.md) · [piv_velocity_gradient](../field/piv_velocity_gradient.md) · [piv_q_criterion](../field/piv_q_criterion.md)

## 同カテゴリ(`estimate`)

[piv_cross_correlate](piv_cross_correlate.md) · [piv_multipass](piv_multipass.md) · [piv_ensemble_correlate](piv_ensemble_correlate.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
