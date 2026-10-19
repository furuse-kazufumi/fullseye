---
op: robust_gaussian_profile
dim: roughness
category: prepare
in: signal
out: signal
examples: [example_robust_profile_filter, poc_robust_profile_filter]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.1  # fullseye lib version this note was generated for
---

# robust_gaussian_profile — ROUGHNESS `prepare` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.robust_gaussian_profile(z, dx, lambda_c, c=4.4, order=1, robust=True, truncate=1.0, max_iter=None, tol=1e-06)` (実装を直接呼ぶなら `import roughness; roughness.robust_gaussian_profile(z, dx, lambda_c, c=4.4, order=1, robust=True, truncate=1.0, max_iter=None, tol=1e-06)`、台帳から引くなら `opsroughness.get("robust_gaussian_profile")`)
- **台帳経由の戻り値**: `fullseye.ledger.robust_gaussian_profile(...)` は**宣言 out 型 `signal` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.robust_gaussian_profile.raw(...)`、または `roughness.robust_gaussian_profile` を直接呼ぶ。
  - 本体の返り: `(roughness, mean_line, info)`

## 使い方

ロバスト・ガウシアン回帰フィルタ(断面): 外れ値・傷に引きずられない平均線と粗さ。

ガウス重みの局所回帰(次数 ``order``)に Tukey の biweight を掛けて反復する。普通の
ガウスフィルタは深い溝や突起にそのまま引きずられ、平均線が傷の側へ凹む。この op は
傷の部分の重みを下げる(``|r| ≥ c·median|r|`` で 0)ので、平均線は傷を無視する。

戻り値は ``(roughness, mean_line, info)``。``roughness = z - mean_line``。端は **削らず**
全長を返す(窓に入るデータだけで回帰するので、ガウス平均と違って端でも偏らない。
端の信頼度が気になるなら両端 ``λc/2`` を捨てる)。``info`` は反復回数・収束・重みの要約。

引数
  z          断面 ``z[i]``(1 次元、有限値のみ)。
  dx         標本間隔。
  lambda_c   カットオフ波長(透過率 50 %)。``2*dx`` 以上、評価長さ以下。
  c          biweight の定数(既定 4.4)。しきい値は ``c × median|残差|``。
  order      0 = 重み付き平均、1 = 局所直線(既定)。内部の核はどちらも同じで、
             カットオフでの透過率は 0.5(閉形式 ``exp(-π (α λc f)²)``、``f = 1/λc``)。
  robust     ``False`` なら重み 1 のまま(普通の線形ガウス回帰。比較・基準用)。
  truncate   窓の半径 ``truncate·λc``(0.5 以上)。既定 1.0。0.75(``GAUSS_TRUNCATE``)に
             すると、既存の ``surface_filter`` と内部で一致する(0.5 は規格の文面の打ち切り)。
  max_iter   反復の上限(``None`` = 200)。収束しなければ **拒否する**。
  tol        収束判定: 平均線の変化の最大が ``tol × median|残差|`` 以下。

fail-closed
  * 配列が 1 次元でない / 8 点未満 / NaN・Inf を含む。
  * ``dx`` / ``lambda_c`` / ``c`` / ``tol`` が有限の正でない、``lambda_c`` が範囲外、
    ``order`` が 0/1 以外、``truncate`` < 0.5。
  * 窓の中に重みを持つデータが無い(傷が窓より広い)/ 正規方程式が退化する。
  * biweight の反復が ``max_iter`` 回で収束しない(外れ値が半数に近い等)。

出典(式は論文のものを再実装。規格の本文は写していない): ISO 16610-21 / -31 の
ガウス回帰の考え方、Seewig, "Gaussian Regression Filters"(*Computational Surface and Roundness Metrology*, Springer 2009)、沼田・藤原・舟橋・輿水、
精密工学会誌 76 (2010)(高速 M 推定)。

## 詳しい使い方ガイド

- [surface_roughness ファミリ ガイド](../guides/surface_roughness.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [example_robust_profile_filter](../../../../examples/example_robust_profile_filter.py) — `py -3.11 examples/example_robust_profile_filter.py`
- [poc_robust_profile_filter](../../../../examples/poc_robust_profile_filter.py) — `py -3.11 examples/poc_robust_profile_filter.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[robust_spline_profile](robust_spline_profile.md) · [profile_params](../measure/profile_params.md)

## 同カテゴリ(`prepare`)

[surface_form_remove](surface_form_remove.md) · [surface_filter](surface_filter.md) · [robust_spline_profile](robust_spline_profile.md) · [robust_gaussian_surface](robust_gaussian_surface.md)

---
*Provenance: roughness.py — ROUGHNESS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
