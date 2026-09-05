---
op: piv_peak_locking
dim: piv
category: assess
in: flow2d
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# piv_peak_locking — PIV `assess` op

- **データ種**: `flow2d` → `table`
- **呼び出し**: `import pivops; pivops.piv_peak_locking(flow, bins=20)` (または `opspiv.get("piv_peak_locking")`)

## 使い方

ピークロッキングの強さ。小数部の分布が一様からどれだけ外れているか。

サブピクセル推定は、真の変位の小数部が 0 や 0.5 のときにそこへ引き寄せられる
偏りを持つ(相関ピークの形と当てはめる関数の形が違うことから来る、PIV の
教科書的な系統誤差)。**流れが一様でなければ小数部は一様分布に近いはず**で、
そこからのずれを測る。

指標 ``c0`` は**標本数に依らない**カイ二乗型のずれ:
``sum((n_i - n_bar)^2 / n_bar) / (bins - 1)``。一様分布から標本を取ると
期待値 1 になるので、**1 前後なら一様と区別できない**、大きいほど偏っている。

★ ただしこの指標は「真の変位の小数部が一様である」ことを仮定する。窓の数が
少ない場や、変位がゆっくり変わる場では**真値そのものの c0 も大きくなる**
(実測: 線形ランプの真値で 82 —— 窓格子が 19 列しか無く小数部が離散的に
しか現れないため)。したがって c0 は**同じ入力の真値と比べて**読むこと。

**決定的な診断は別にある** —— 一様並進の小数部を 0 から 0.9 まで振り、
推定値が対角線に乗るかを見る。実測(win=32、density 0.02):

==========  =================  ==================
推定法      小数部誤差の RMS   最大絶対誤差
==========  =================  ==================
gauss3      0.0037 px          0.0088 px
parabolic   0.0104 px          0.0151 px
centroid    0.2259 px          0.3701 px
==========  =================  ==================

``centroid`` は真値 0.1 を 0.02、0.9 を 0.98 と答える —— 整数へ引き寄せる
教科書どおりの S 字。**出るはずのものが出た**ことの確認であって、
実装の不具合ではない(だから 3 つとも残してある)。

Args:
    flow: ``(2, h, w)``。
    bins: 小数部のヒストグラムの階級数。
Returns:
    dict: ``c0``(両成分合わせた指標)、``hist``(``(2, bins)``)、
    ``frac_mean`` / ``frac_std``、``bins``。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`assess`)

[piv_sample_at_windows](piv_sample_at_windows.md) · [piv_error_stats](piv_error_stats.md) · [piv_time_statistics](piv_time_statistics.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
