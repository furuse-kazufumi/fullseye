---
op: piv_q_criterion
dim: piv
category: field
in: flow2d
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# piv_q_criterion — PIV `field` op

- **データ種**: `flow2d` → `image2d`
- **呼び出し**: `import pivops; pivops.piv_q_criterion(flow, spacing=1.0)` (または `opspiv.get("piv_q_criterion")`)

## 使い方

Q 基準 ``-tr(J^2)/2``。**回転がひずみを上回る**場所が正になる。

渦度だけを見るとせん断層も光る(層流の壁近傍が渦に見える)ので、渦の抽出には
こちらを使う。閉形式(解析場を直接与えた実測):

* 剛体回転 ω=0.01 → ``+1.0e-4`` (= ω^2)
* 一様膨張 s=0.01 → ``-1.0e-4`` (= -s^2)
* 単純せん断 g=0.02 → ``0.0``(**せん断は渦ではない**、が要点)

★ 閾値を必要とする量である。``Q > 0`` だけでは薄い領域まで拾うので、
閾値をどう決めたかを書かない渦可視化は、絵の美しさが閾値の産物である
可能性を隠している。閾値を振ったときの面積変化を併記すること。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image2d` を入力に取れる)

[piv_cross_correlate](../estimate/piv_cross_correlate.md) · [piv_multipass](../estimate/piv_multipass.md) · [piv_deform_pass](../estimate/piv_deform_pass.md)

## 同カテゴリ(`field`)

[piv_vorticity](piv_vorticity.md) · [piv_divergence](piv_divergence.md) · [piv_flow_magnitude](piv_flow_magnitude.md) · [piv_to_velocity](piv_to_velocity.md) · [piv_velocity_gradient](piv_velocity_gradient.md) · [piv_swirling_strength](piv_swirling_strength.md) · [piv_strain_rate](piv_strain_rate.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
