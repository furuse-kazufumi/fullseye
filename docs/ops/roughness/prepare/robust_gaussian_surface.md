---
op: robust_gaussian_surface
dim: roughness
category: prepare
in: depth
out: depth
examples: [poc_robust_profile_filter]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# robust_gaussian_surface — ROUGHNESS `prepare` op

- **データ種**: `depth` → `depth`
- **呼び出し**: `import fullseye as fs; fs.ledger.robust_gaussian_surface(z, dx, lambda_c, c=4.4, order=1, robust=True, truncate=1.0, dy=None, max_iter=None, tol=1e-06)` (実装を直接呼ぶなら `import roughness; roughness.robust_gaussian_surface(z, dx, lambda_c, c=4.4, order=1, robust=True, truncate=1.0, dy=None, max_iter=None, tol=1e-06)`、台帳から引くなら `opsroughness.get("robust_gaussian_surface")`)
- **台帳経由の戻り値**: `fullseye.ledger.robust_gaussian_surface(...)` は**宣言 out 型 `depth` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.robust_gaussian_surface.raw(...)`、または `roughness.robust_gaussian_surface` を直接呼ぶ。
  - 本体の返り: `(roughness, mean_surface, info)`

## 使い方

ロバスト・ガウシアン回帰フィルタ(面): 傷・突起に引きずられない面のうねりと粗さ。

``robust_gaussian_profile`` の 2 次元版(核は x・y に可分、局所面 ``c + p u + q v`` の
回帰、biweight は面全体の残差の中央値で作る)。重みが非可分でも、必要なのは重み画像と
``u^a v^b`` を掛けた核との可分相関だけなので、 ``O(N · 窓幅)`` で済む。

戻り値は ``(roughness, mean_surface, info)``。端は削らず全面を返す。引数・fail-closed は
断面版と同じ(``dy=None`` は正方画素、``z`` は 8x8 以上の 2 次元)。

## 詳しい使い方ガイド

- [surface_roughness ファミリ ガイド](../guides/surface_roughness.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_robust_profile_filter](../../../../examples/poc_robust_profile_filter.py) — `py -3.11 examples/poc_robust_profile_filter.py`

## 型が繋がる次の op(`depth` を入力に取れる)

[surface_form_remove](surface_form_remove.md) · [surface_filter](surface_filter.md) · [surface_params](../measure/surface_params.md) · [surface_psd](../measure/surface_psd.md)

## 同カテゴリ(`prepare`)

[surface_form_remove](surface_form_remove.md) · [surface_filter](surface_filter.md) · [robust_gaussian_profile](robust_gaussian_profile.md) · [robust_spline_profile](robust_spline_profile.md)

---
*Provenance: roughness.py — ROUGHNESS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
