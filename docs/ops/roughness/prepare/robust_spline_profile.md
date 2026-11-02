---
op: robust_spline_profile
dim: roughness
category: prepare
in: signal
out: signal
gpu: なし
examples: [poc_robust_profile_filter]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# robust_spline_profile — ROUGHNESS `prepare` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.robust_spline_profile(z, dx, lambda_c, c=4.4, robust=True, max_iter=None, tol=1e-06)` (実装を直接呼ぶなら `import roughness; roughness.robust_spline_profile(z, dx, lambda_c, c=4.4, robust=True, max_iter=None, tol=1e-06)`、台帳から引くなら `opsroughness.get("robust_spline_profile")`)
- **台帳経由の戻り値**: `fullseye.ledger.robust_spline_profile(...)` は**宣言 out 型 `signal` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.robust_spline_profile.raw(...)`、または `roughness.robust_spline_profile` を直接呼ぶ。
  - 本体の返り: `(roughness, mean_line, info)`
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

ロバスト・スプラインフィルタ(断面): 外れ値に引きずられない平均線と粗さ。

平均線 ``w`` を ``Σ δ_i (z_i - w_i)² + β Σ (Δ² w)_i²`` の最小化で求める(2 階差分の罰則つき
最小二乗 = 離散の三次平滑化スプライン、Whittaker 1923 / Eilers 2003 / Krystek, Measurement 18 (1996) 9-15)。
重み ``δ`` は biweight で反復して更新する。ガウスと違って **端に自然境界条件が付く**
ので、端を削らなくても平均線が端で外へ振れにくい。

``β = 1 / (16 sin⁴(π dx/λc))`` と置くと、線形(``robust=False``)の内部の伝達関数が
``H(λ) = 1 / (1 + (sin(π dx/λ) / sin(π dx/λc))⁴)`` になり、``λ = λc`` でちょうど 50 %
(閉形式)。``dx/λ`` が小さい極限では ``1/(1+(λc/λ)⁴)``(張力 0 の三次スプラインフィルタの形)。

戻り値は ``(roughness, mean_line, info)``。引数と fail-closed は ``robust_gaussian_profile``
と同じ(``order`` / ``truncate`` は無い)。重みを持つデータが 2 点未満なら拒否する。

## 詳しい使い方ガイド

- [surface_roughness ファミリ ガイド](../guides/surface_roughness.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_robust_profile_filter](../../../../examples/poc_robust_profile_filter.py) — `py -3.11 examples/poc_robust_profile_filter.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[robust_gaussian_profile](robust_gaussian_profile.md) · [profile_params](../measure/profile_params.md)

## 同カテゴリ(`prepare`)

[surface_form_remove](surface_form_remove.md) · [surface_filter](surface_filter.md) · [robust_gaussian_profile](robust_gaussian_profile.md) · [robust_gaussian_surface](robust_gaussian_surface.md)

---
*Provenance: roughness.py — ROUGHNESS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
