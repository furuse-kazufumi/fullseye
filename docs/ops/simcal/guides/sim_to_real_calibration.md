---
guide: sim_to_real_calibration
dim: simcal
title: sim-to-real 較正(実物の画像から物理モデルの係数を合わせ、決まらない係数には数を出さない) — 使い方ガイド
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
---

# sim-to-real 較正 — 使い方ガイド

## この族が答えている問い

実物の画像を与えたら、誤差をフィードバックして、計算に使う係数(周辺減光の強さ、ボケの幅、膜の厚さ、カメラの利得 …)を
自動で合わせたい。ここで一番危ないのは、**画像が決めていない係数にもっともらしい数を出してしまう**ことです。

- 照明の強さとカメラの利得は、どちらも画像を同じように明るくします。画像から決まるのは積だけで、1 つずつの値は決まりません。
- 1 波長で一様な膜を撮ると、屈折率 n と膜厚 d は n x d(光路長)の形でしか効きません。
- 白い板を撮った画像では、ボケ(PSF の幅)は何も変えません。

最適化はこういう場合も「収束」して数を返します。この族は、その数を**返さずに拒否**し、代わりに理由と、画像が決めている
組み合わせ(照明 x 利得 = 899.4 のような)を返します。台帳は `opssimcal.py`、本体は `simcal.py`。

## 流れ

```mermaid
flowchart LR
  A[simcal_model<br/>連鎖・つまみ・雑音モデル] --> B[simcal_observe<br/>位置合わせ・ROI・露出]
  A --> S[simcal_screen<br/>効くか・交絡か・出力の次元]
  B --> S
  B --> F[simcal_fit<br/>重みつき最小二乗]
  F -->|決まらない・端・雑音モデル無し| X[拒否: 理由と決まる組み合わせ]
  F --> R[calresult]
```

## 模型(model)

| やりたいこと | op | 要点 |
|---|---|---|
| 順方向の模型を組む | `simcal_model` | 連鎖の各段は登録済みの op(例 `thin_film_reflectance`)か組み込みの段(`stage:gain_offset`・`stage:scale`・`stage:radial_cos4`・`stage:radial_poly`・`stage:gaussian_blur`・`stage:as_image`・`stage:mc_sample`)。つまみは 1 つの段の 1 つの引数に結びつき、単位・範囲・線形 / 対数・事前分布を持つ。組んだ時点で 1 回走らせ、走らない模型は拒否 |
| 模型を走らせる | `simcal_simulate` | 条件(露光・波長 …)ごとに 2-D の画像 1 枚 |
| 実画像を付ける | `simcal_observe` | 位相相関(`phase_correlation_fft`)で整数画素のずれを戻し、巻き込んだ縁は使わない。**露出の正規化と利得つまみの同時は拒否**(どちらも信号を倍にするので区別できず、正規化した雑音を 2 回数える) |

雑音モデルは必須です。EMVA 1288 の線形カメラなら `{"kind": "emva", "K": ..., "sigma_d": ..., "dark": ...}`
(`sensorchar.emva_photon_transfer` の結果をそのまま渡せる。暗雑音が推定できなかった場合は上限を使う)、
単純な場合は `{"kind": "gaussian", "sigma": ...}`。雑音の分散が無いと「決まる」の物差しが無いので、当てはめは拒否します。

モンテカルロの描画器のような**確率的な模型**は `stochastic={"seed": s, "sample_var": "estimate"}` で受けます。
種を固定する(共通乱数)と模型が決定的になり、ヤコビアンが壊れません。模型自身の標本の分散は雑音に足します ——
足さないと残差が雑音より大きく見え、後段の門が誤作動します。

## 合わせ(fit)

| やりたいこと | op | 要点 |
|---|---|---|
| どのつまみが効くか、交絡しているか | `simcal_screen` | 雑音で割った出力の主成分ごとに Morris / Sobol'(`sens_morris` / `sens_sobol` を再利用)。全範囲を動かしても雑音の 1.96 倍に届かないつまみは「効かない」。共線性指数(`mv_confounding`)で交絡の組、`mv_residual_pca` で雑音を越える出力の次元数 |
| 係数を合わせる | `simcal_fit` | 雑音の分散で重みをつけた最小二乗(重みは予測で更新)。出発点は計画(ラテン超方格)の最良点。`lm`(範囲を出る一歩はそのまま取らない)・`nm`・`multistart`。**決まらない・効かない・範囲の端 1 % に張りつく**つまみがあれば拒否し、理由と決まる組み合わせを返す。`allow_undetermined=True` なら、それらのつまみには値を付けずに残りを返す |

当てはめが違う谷(薄膜の隣の干渉次数など)に落ちたときは、値は返しますが `fit.warnings` に
「χ²/自由度が雑音の何倍か、multistart を試せ」と書きます。

## 最初の 1 本

```python
import fullseye as fs

m = fs.ledger.simcal_model()                  # 例の模型: チャート -> cos^4 の周辺減光 -> 利得と黒レベル(合成の観測つき)
print(fs.ledger.simcal_screen(m)["class"])    # {'f': 'determined', 'gain': 'determined', 'offset': 'determined'}
r = fs.ledger.simcal_fit(m)
print(r["status"], {k: round(v, 2) for k, v in r["theta_hat"].items()})
# accepted {'f': 22.09, 'gain': 899.05, 'offset': 63.56}   (真値 22 / 900 / 64)
```

## 例

`examples/simcal_tour.py` —— 利得 x 照明の拒否と積、1 波長と 31 波長の膜、白い板とチャートのボケ、ずれた画像の位置合わせ。
