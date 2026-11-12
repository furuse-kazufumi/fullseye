---
op: wave_dominant_frequency
dim: math
category: wave
in: image2d
out: table
gpu: なし
examples: [wave_dominant_frequency_grating]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# wave_dominant_frequency — MATH `wave` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.wave_dominant_frequency(image, window='hann')` (実装を直接呼ぶなら `import mathops; mathops.wave_dominant_frequency(image, window='hann')`、台帳から引くなら `opsmath.get("wave_dominant_frequency")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

画像の最も強い周期(2-D FFT の DC 以外で最大の山)の周波数・周期・向きを返す(``table``)。

平均を引き、``window="hann"``(既定)なら 2-D の Hann 窓を掛けてから ``fft2`` の
パワーの最大(DC は除く)を探し、山の 3 点に**対数の放物線**を行・列それぞれで当てて
ビンより細かく読む(:func:`wave_fringe_period` の 2-D 版。あちらは 1 軸の周期だけ)。
``window="none"`` は窓を掛けない(周期が画像幅にちょうど整数個入るときだけ厳密)。

返す dict: ``fx`` / ``fy``(列方向・行方向の空間周波数 [cycles/px]、山は ``fx >= 0`` の
半平面に揃える)、``freq_cpp``(``hypot(fx, fy)``)、``period_px``(``1 / freq_cpp``)、
``angle_deg``(波数ベクトルの向き = 縞に**垂直**な向き。+列から +行へ回る角で
``[0, 180)``。縞 ``cos(2π(x cosθ + y sinθ)/p)`` なら θ)、``peak_fraction``(山の
ビンとその鏡像が DC 以外の全パワーに占める割合 = 周期の確からしさ)、``window``。

★前提: 照明むらのような低周波は山を奪う(画像より長い周期は DC の隣に出る)。
むらがある画像は先に背景を引くか高域通過を掛けること。

空の入力(``image`` が 0 要素)は ``ValueError``。
拒否(``ValueError``): 2-D でない、どちらかの辺が 8 画素未満、非有限の値、
平らな画像(周期が無い)、未知の ``window``。

## ファミリ共通の入力契約(fail-closed)

mathops の全 op は入力を検証してから計算する(黙って通さない):

- **complex 入力は `ValueError`** — float64 への強制変換は虚部を黙って捨てる(numpy は ComplexWarning だけ出して「もっともらしく間違った」実数を返す)。`.real`/`.imag`/`abs()` を明示するか、複素対応の complexops を使う。
- **masked array(masked 要素あり)は `ValueError`** — マスクを剥がして下の生値を使う暗黙変換を拒否。埋める/落とすを明示する。
- **NaN/Inf は全入力で `ValueError`**(件数を明示して拒否 — 結果全体に伝播するため)。
- **形状は厳格**: 1-D と 2-D を暗黙昇格・ブロードキャストしない(vector 枠に matrix、matrix 枠に vector は `ValueError`。reshape を明示する)。
- **サイズ上限**: 行列を取る op と `stat_histogram` の bins は `mathops.MAX_ELEMENTS`(2^26 ≈ 6700 万要素)超で `ValueError`。

## 詳しい使い方ガイド

- [math_metrology ファミリ ガイド](../guides/math_metrology.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [wave_dominant_frequency_grating](../../../../examples/wave_dominant_frequency_grating.py) — `py -3.11 examples/wave_dominant_frequency_grating.py`

## 型が繋がる次の op(`table` を入力に取れる)

[dynsys_poincare_section](../dynsys/dynsys_poincare_section.md) · [dwt_inverse](../transform/dwt_inverse.md) · [chebyshev_eval_nd](../numerics/chebyshev_eval_nd.md)

## 同カテゴリ(`wave`)

[wave_membrane_mode](wave_membrane_mode.md) · [wave_mode_frequencies](wave_mode_frequencies.md) · [wave_nodal_lines](wave_nodal_lines.md) · [wave_two_slit](wave_two_slit.md) · [wave_fringe_period](wave_fringe_period.md) · [wave_grating_orders](wave_grating_orders.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
