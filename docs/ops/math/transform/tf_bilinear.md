---
op: tf_bilinear
dim: math
category: transform
in: signal × signal
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# tf_bilinear — MATH `transform` op

- **データ種**: `signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.tf_bilinear(num, den, fs: 'float' = 1.0, *, prewarp_hz: 'float | None' = None) -> 'dict'` (実装を直接呼ぶなら `import mathtransforms; mathtransforms.tf_bilinear(num, den, fs: 'float' = 1.0, *, prewarp_hz: 'float | None' = None) -> 'dict'`、台帳から引くなら `opsmath.get("tf_bilinear")`)

## 使い方

Tustin(双一次)変換 s = K (z − 1)/(z + 1) で連続系を離散系に写す。

K = 2·fs(素の Tustin)か、``prewarp_hz`` を与えると K = ω₀ / tan(ω₀ / (2 fs))
(その周波数で連続系と離散系の応答が**厳密に一致**する。それ以外の周波数は tan で歪む)。
返り値の係数は z の降べき(``np.polyval(num_z, z)``)。安定な連続系は安定な離散系になる(左半面 → 単位円内)。

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

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[dynsys_poincare_section](../dynsys/dynsys_poincare_section.md) · [dwt_inverse](dwt_inverse.md)

## 同カテゴリ(`transform`)

[abel_transform](abel_transform.md) · [abel_inverse](abel_inverse.md) · [abel_inverse_image](abel_inverse_image.md) · [abel_revolve](abel_revolve.md) · [hankel_transform](hankel_transform.md) · [tf_poles_zeros](tf_poles_zeros.md) · [tf_freq_response](tf_freq_response.md) · [tf_impulse_response](tf_impulse_response.md)

---
*Provenance: mathtransforms.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
