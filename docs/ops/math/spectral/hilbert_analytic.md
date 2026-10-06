---
op: hilbert_analytic
dim: math
category: spectral
in: signal
out: table
examples: [spectral_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# hilbert_analytic — MATH `spectral` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.hilbert_analytic(x, fs: 'float' = 1.0) -> 'dict'` (実装を直接呼ぶなら `import mathspectral; mathspectral.hilbert_analytic(x, fs: 'float' = 1.0) -> 'dict'`、台帳から引くなら `opsmath.get("hilbert_analytic")`)

## 使い方

解析信号 z = x + i·H[x] (FFT で負の周波数を消す)と、そこから読む振幅・瞬時位相・瞬時周波数。

Args:
    x: 実の 1-D 信号。
    fs: 標本化周波数(瞬時周波数の単位を決める)。

Returns:
    ``analytic`` 複素の解析信号、``amplitude`` |z|(包絡線)、``phase`` 連続につないだ位相 [rad]、
    ``frequency`` 瞬時周波数 = 位相の時間微分 / 2π(中心差分、長さは x と同じ)。

門: cos → sin(Hilbert 変換の定義)、線形チャープの瞬時周波数が f0 + k·t、Bedrosian の定理(包絡線が
搬送波より低い帯域なら AM 信号の振幅がそのまま戻る)。端は周期の仮定で乱れる(信号を窓で絞ると減る)。

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

- [spectral_tour](../../../../examples/spectral_tour.py) — `py -3.11 examples/spectral_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[dynsys_poincare_section](../dynsys/dynsys_poincare_section.md) · [dwt_inverse](../transform/dwt_inverse.md) · [chebyshev_eval_nd](../numerics/chebyshev_eval_nd.md)

## 同カテゴリ(`spectral`)

[lomb_scargle](lomb_scargle.md) · [ula_snapshots](ula_snapshots.md) · [music_doa](music_doa.md) · [esprit_doa](esprit_doa.md) · [n_sources_mdl](n_sources_mdl.md)

---
*Provenance: mathspectral.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
