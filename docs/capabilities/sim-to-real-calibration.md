---
id: sim-to-real-calibration
title: 実物の画像から物理モデルの係数を合わせる(sim-to-real 較正)—— 画像が決めない係数には数を出さず、決まる組み合わせと理由を返す
title_en: Fit a physical model's coefficients to real images (sim-to-real calibration) — no number for a coefficient the images do not determine, the determined combination and the reason instead
category: 測る
ops: [simcal_model, simcal_simulate, simcal_observe, simcal_screen, simcal_fit, simcal_identifiability, simcal_uncertainty, simcal_validate, simcal_discrepancy, simcal_report]
examples: [simcal_tour, simcal_checks_tour]
version: 0.6.1
inputs: [images]
pipeline: [simcal_model, simcal_observe, simcal_fit, simcal_identifiability, simcal_report]
alternatives: [simcal_screen, simcal_uncertainty, simcal_validate, simcal_discrepancy, simcal_simulate, mv_confounding, mv_residual_pca, sens_morris]
limits: 推定の物差しはカメラの雑音モデル(EMVA 1288 の線形カメラかガウス)で、雑音モデルが無いと拒否する。雑音を 1/4 に見誤ると Cramér-Rao 下界も半分になり、40 組の採点は 39 組 → 29 組に落ちる(例で実測)。位置合わせは整数画素だけ。干渉縞のように谷がいくつもある問題では、小さな計画からの LM は隣の谷に落ちうる(値は返し、χ²/自由度を警告に出す)。モデルの食い違いがあると不確かさは楽観側になる(simcal_discrepancy が注記する)。
calibration: 係数はつまみの単位(px・DN・nm …)で返る。画素から mm への換算は模型の外の話で、倍率や画素ピッチをつまみに入れるなら、それが画像から決まるかを simcal_screen で先に確かめる(倍率と画素ピッチは積でしか効かない)。
---

# 実物の画像から物理モデルの係数を合わせる(sim-to-real 較正)

## できること

周辺減光の強さ・ボケの幅・膜の厚さ・カメラの利得のような**物理の係数**を、実物の画像との差が雑音の大きさになるまで自動で
合わせます(`simcal`、10 op)。模型は fullseye の op の連鎖(例 `thin_film_reflectance` → 画像 → 利得と黒レベル)で、各段の
引数を単位・範囲・線形 / 対数つきの「つまみ」にします。当てはめは雑音の分散で重みをつけた最小二乗(重みは予測で更新)。

この層の要点は**数を出さないこと**です。

- 照明の強さと利得のように**積でしか効かない**つまみは、1 つずつの値を出さずに拒否し、決まる組み合わせ(照明 x 利得 = 899.4)を返します。
- 単波長の膜の n と d は n^1 x d^0.94 しか決まりません(31 波長なら別々に決まる)。
- 白い板を撮った画像のボケのように**効かない**つまみ、範囲の端 1 % に張りついたつまみも拒否します。
- 当てはめた後も、プロファイル尤度が片側しか閉じないつまみ(小さすぎるボケ: 「σ < 0.29 px」としか言えない)は点推定を取り下げます。
- 取り置いた画像での過適合の門(8 次の周辺減光の多項式を拒否)と、残差 PCA による**モデルの食い違い**の検出(光軸のずれたレンズ)。

## What it does

Ten ops (`simcal` / `simcalcheck`) fit the physical coefficients of a forward model built from fullseye ops (knobs with units,
ranges and linear/log scales) to real images by noise-weighted least squares, and refuse to give a number for a coefficient the
images do not determine: confounded knobs (illumination x gain, n x d at one wavelength) are reported as the determined
combination, knobs without influence or pinned to a range end are refused, a profile likelihood that closes on one side only
withdraws the estimate. Over-fitting gates on held-out images reject an 8th-order vignetting polynomial, and residual PCA against
the Tracy-Widom edge of white noise detects a model discrepancy (a decentred lens).

## 向くところ / 向かないところ

- 向く: 模型の構造は正しく、係数(物理の単位)だけが分からない場合。数個〜十数個のつまみ、画像は数枚〜数十枚。
- 向く: 「この実験で決まるのはどれか」を撮る前に知りたい場合(`simcal_screen` は模型だけで答える)。
- 向かない: 模型の構造そのものを探す問題(op の並びの探索は evolve 系)。食い違いは検出するが、直しはしない。
- 確率的な順方向モデル(モンテカルロの描画器)は共通乱数と標本の分散で受けるが、収束を確かめる層はまだ無い。

## 推奨パイプライン

`simcal_model` → `simcal_observe` → `simcal_fit` → `simcal_identifiability` → `simcal_report`

`simcal_model` で連鎖・つまみ・雑音モデルを組み → `simcal_observe` で実物の画像(`images`)を付け → `simcal_fit` で拒否つきの当てはめ →
`simcal_identifiability` で下界とプロファイル(片側しか閉じないつまみは取り下げ)→ `simcal_report` で表 1 枚。

## 代替

撮る前に `simcal_screen`(効くか・交絡か・出力の次元)。区間が要るなら `simcal_uncertainty`(Laplace / ブートストラップ)、
取り置いた画像があれば `simcal_validate`(過適合の門・LOCKED は 1 回)、模型の不足を疑うなら `simcal_discrepancy`。
感度だけなら `sens_morris` / `mv_confounding`、残差の構造だけなら `mv_residual_pca`。

## 限界

雑音モデルが物差しで、これを見誤ると下界も区間も見誤ります。位置合わせは整数画素。谷がいくつもある問題(干渉の次数)では
`method="multistart"` を使い、`fit.warnings` を読むこと。モデルの食い違いがあれば不確かさは楽観側です。

## 実寸校正

係数はつまみの単位で返ります。画素ピッチと倍率は積でしか効かないので、両方をつまみにすると拒否されます —— mm/px を 1 つの
つまみにするか、片方を固定してください。

## 最初の 1 本

```python
import fullseye as fs

m = fs.ledger.simcal_model()                 # 例の模型(チャート → cos^4 の周辺減光 → 利得と黒レベル、合成の観測つき)
r = fs.ledger.simcal_fit(m)
r = fs.ledger.simcal_identifiability(r)
print(fs.ledger.simcal_report(r)["text"])
# demo: chart -> cos^4 vignetting -> gain/offset — status: accepted
#   f            = 22.0876 px  [21.8461, 22.334]
#   gain         = 899.054 DN  [893.726, 904.382]
#   offset       = 63.5621 DN  [61.2762, 65.8468]
```

## 裏づけ

- op: `simcal_model` / `simcal_simulate` / `simcal_observe` / `simcal_screen` / `simcal_fit` / `simcal_identifiability` /
  `simcal_uncertainty` / `simcal_validate` / `simcal_discrepancy` / `simcal_report`
- 例: [`simcal_tour`](../../examples/simcal_tour.py) —— 利得 x 照明の拒否と積、1 波長と 31 波長の膜、白い板とチャートのボケ、位置合わせ。
- 例: [`simcal_checks_tour`](../../examples/simcal_checks_tour.py) —— 40 組の真値で回収を採点(39 / 40 が 3 σ_CRLB 以内)、上限しか言えないボケ、
  8 次の多項式の拒否、光軸のずれたレンズの残差 PCA。
- 一次資料: Kennedy & O'Hagan 2001(較正と食い違い)、Raue ら 2009(プロファイル尤度)、Brun, Reichert & Künsch 2001(共線性指数)、
  Levenberg 1944 / Marquardt 1963、EMVA 1288 Release 4.0(雑音モデル)、Johnstone 2001(Tracy-Widom の端)。
