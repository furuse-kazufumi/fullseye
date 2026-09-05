---
op: piv_outlier_mask
dim: piv
category: validate
in: flow2d
out: mask
examples: [piv_flow_from_particles]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# piv_outlier_mask — PIV `validate` op

- **データ種**: `flow2d` → `mask`
- **呼び出し**: `import pivops; pivops.piv_outlier_mask(flow, threshold=2.0, epsilon=0.1)` (または `opspiv.get("piv_outlier_mask")`)

## 使い方

正規化中央値検定(Westerweel & Scarano 2005)で外れベクトルを見つける。

各ベクトルについて、8 近傍の中央値からの残差を**近傍残差の中央値**で割る。
分母に ``epsilon``(既定 0.1 px、PIV の測定不確かさの目安)を足すのは、
一様な場で分母が 0 になって全部が外れ値になるのを防ぐため —— この項が
無いと、**理想的な入力ほど検定が壊れる**。

★**勾配の急な場では害になる**(2026-09-06 実測)。Rankine 型の渦
(芯の半径 28 px)で多段 PIV を掛けたところ、閾値 2 が拾った 5 本は
すべて**芯の縁**(中心から 32 px)に並び、実際の誤差は 0.07-0.45 px ——
外れ値ではなく**速度分布が折れている場所**だった。近傍中央値で均すと
RMS が 0.134 から 0.230 へ**悪化**する(閾値 5 では 1 本も拾わず 0.134 のまま)。

検定は「近傍と違う = 間違い」という仮定に立つので、**本物の不連続を
間違いと呼ぶ**。掛けるかどうかは場の性質を見て決めること。

Args:
    flow: ``(2, h, w)``。
    threshold: この値を超えたら外れ値。慣行は 2。
    epsilon: 分母の下駄 [px]。
Returns:
    ``(h, w)`` の bool。``True`` が外れ値(``nan`` も ``True``)。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [piv_flow_from_particles](../../../../examples/piv_flow_from_particles.py) — `py -3.11 examples/piv_flow_from_particles.py`

## 型が繋がる次の op(`mask` を入力に取れる)

[piv_replace_outliers](piv_replace_outliers.md)

## 同カテゴリ(`validate`)

[piv_replace_outliers](piv_replace_outliers.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
