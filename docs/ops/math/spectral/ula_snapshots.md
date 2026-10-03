---
op: ula_snapshots
dim: math
category: spectral
in: signal
out: matrix
examples: [spectral_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# ula_snapshots — MATH `spectral` op

- **データ種**: `signal` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.ula_snapshots(angles_deg=(10.0, 16.0), n_elements: 'int' = 8, n_snapshots: 'int' = 200, *, spacing: 'float' = 0.5, snr_db: 'float | None' = None, seed: 'int' = 0) -> 'np.ndarray'` (実装を直接呼ぶなら `import mathspectral; mathspectral.ula_snapshots(angles_deg=(10.0, 16.0), n_elements: 'int' = 8, n_snapshots: 'int' = 200, *, spacing: 'float' = 0.5, snr_db: 'float | None' = None, seed: 'int' = 0) -> 'np.ndarray'`、台帳から引くなら `opsmath.get("ula_snapshots")`)

## 使い方

等間隔線形アレイが受ける複素スナップショット (M, K) を作る(到来方向推定の答えの決まる入力)。

波源ごとに独立な複素ガウスの信号(無相関)。``snr_db`` を与えると素子ごとの白色雑音を足す(None = 雑音なし)。

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

## 型が繋がる次の op(`matrix` を入力に取れる)

[mat_solve](../linalg/mat_solve.md) · [mat_lstsq](../linalg/mat_lstsq.md) · [mat_svd](../linalg/mat_svd.md) · [mat_eigh](../linalg/mat_eigh.md) · [mat_pinv](../linalg/mat_pinv.md) · [mat_cond](../linalg/mat_cond.md) · [stat_covariance](../stats/stat_covariance.md) · [stat_correlation](../stats/stat_correlation.md)

## 同カテゴリ(`spectral`)

[lomb_scargle](lomb_scargle.md) · [music_doa](music_doa.md) · [esprit_doa](esprit_doa.md) · [n_sources_mdl](n_sources_mdl.md) · [hilbert_analytic](hilbert_analytic.md)

---
*Provenance: mathspectral.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
