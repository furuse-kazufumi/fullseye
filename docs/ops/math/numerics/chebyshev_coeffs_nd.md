---
op: chebyshev_coeffs_nd
dim: math
category: numerics
in: image2d
out: table
examples: [numerics_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# chebyshev_coeffs_nd — MATH `numerics` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.chebyshev_coeffs_nd(values, box=None) -> 'dict'` (実装を直接呼ぶなら `import mathnumerics; mathnumerics.chebyshev_coeffs_nd(values, box=None) -> 'dict'`、台帳から引くなら `opsmath.get("chebyshev_coeffs_nd")`)

## 使い方

テンソル積の Chebyshev–Lobatto 格子で標本化した値から、N 次元の Chebyshev 係数を求める(DCT-I)。

Args:
    values: 形 (n1, …, nd) の配列。軸 i の標本は ``chebyshev_nodes(n_i, lo_i, hi_i)``(昇順)の上の値。
    box: 軸ごとの区間 [(lo, hi), …] (省略で全軸 [−1, 1]、1 組なら全軸に共通)。

Returns:
    ``coeffs`` (n1, …, nd): f ≈ Σ c[k] Π T_{k_i}(t_i)(t_i は [−1, 1] に写した座標)、``box``、
    ``decay`` = 軸ごとに |c| の最大を次数ごとに並べた列(滑らかな関数は幾何級数的に落ちる = スペクトル収束)、
    ``tail`` = 各軸の最後の 2 次数の |c| の最大(打ち切り誤差の目安。小さいほど点数が足りている)。

門: 次数が各軸 n_i − 1 以下の多項式は厳密に再現する / 1/(a − x) 型の極を持つ関数の係数は
ρ^−k(ρ = a + √(a² − 1)、Bernstein の楕円)で落ちる。画像では、照明むら・反りなどの**滑らかな面**を
数十の係数で表す(多項式のべき基底は高次で悪条件、Chebyshev は安定)。

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

- [numerics_tour](../../../../examples/numerics_tour.py) — `py -3.11 examples/numerics_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[dynsys_poincare_section](../dynsys/dynsys_poincare_section.md) · [dwt_inverse](../transform/dwt_inverse.md) · [chebyshev_eval_nd](chebyshev_eval_nd.md)

## 同カテゴリ(`numerics`)

[erf](erf.md) · [erfc](erfc.md) · [bessel](bessel.md) · [gauss_quadrature](gauss_quadrature.md) · [gauss_cubature](gauss_cubature.md) · [chebyshev_eval_nd](chebyshev_eval_nd.md) · [low_discrepancy](low_discrepancy.md) · [chebyshev_nodes](chebyshev_nodes.md)

---
*Provenance: mathnumerics.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
