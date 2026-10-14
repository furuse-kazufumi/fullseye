---
id: thin-film-reflectometry
title: 薄膜の膜厚を分光反射率で測る(転送行列 → 干渉色 → FFT・モデルあてはめ・膜厚マップ)
title_en: Thin-film thickness by spectral reflectometry (transfer matrix, interference colour, FFT, model fit, thickness maps)
category: 光と色
ops: [multilayer_reflectance, film_color, film_thickness_fft, film_thickness_fit, film_thickness_map]
examples: [poc_thin_film_reflectometry]
version: 0.6.1
inputs: [pairs, images]
pipeline: [multilayer_reflectance, film_thickness_fft, film_thickness_fit, film_thickness_map]
alternatives: [thin_film_reflectance, film_color]
limits: 直入射のモデルは顕微分光の膜を薄く読む(実測で −5.7 %、NA を入れると −2.7 %)。FFT は縞 2 本未満(400〜800 nm の SiO₂ で約 540 nm 未満)で破綻。RGB は色が周期的に似るので次数を取り違える画素が残る。
calibration: 反射率の絶対値は裸の Si(材料表の Si の Fresnel)を基準にする(実測と中央値 0.4 % 差)。任意単位の分光器は fit_scale=True、カメラは裸の Si の領域で白を合わせる。
---

# 薄膜の膜厚を分光反射率で測る(転送行列 → 干渉色 → FFT・モデルあてはめ・膜厚マップ)

## できること

Si 上の SiO₂・Si₃N₄、コート、AR 膜の膜厚は、反射スペクトルの干渉縞から非接触で測ります(分光干渉式の膜厚計)。`filmoptics` の 5 本は、膜も基板も材料表(`materials`)の鍵で受けます。観察用の光学系と観察対象が同じ材料表を引くので、膜の n,k をどこかで別に持つ必要がありません。

順問題は `multilayer_reflectance`(特性行列 = 転送行列の厳密解。斜入射・s/p・対物の NA の角度平均・共形な粗さの Debye–Waller、反射率・透過率・吸収率を pairs(λ nm, 値)で)と `film_color`(膜厚を振ったときの干渉色。D65 か任意の照明で sRGB・CIELAB・色相を返す、ウェハの色見本)。逆問題は `film_thickness_fft`(縞の周期 → 膜厚。分散は材料表の n(λ) で補正し、測れる下限の閉形式 2/Δx も返す)、`film_thickness_fit`(転送行列の非線形最小二乗。格子探索で大域、黄金分割で精密化し、局所解の候補を全部返す)、`film_thickness_map`(分光画像か RGB 画像の画素ごとの膜厚と、候補の数の地図)。

PoC `poc_thin_film_reflectometry` の主役は、他人が測った実物のデータでの採点です(どちらも CC BY 4.0、抜き出した表と縮小写真を `data/thin_film_real/` に同梱、出典と改変は同じ場所の README.md)。Schwarz ら(Adv. Opt. Mater. 2024、Zenodo 10.5281/zenodo.13753754)の顕微分光では、裸の Si の実測反射率が材料表の Si と中央値 0.4 % 差、SiO₂ の膜厚は直入射のモデルで 92.9 nm(基準 98.5 nm と −5.7 %)、残差で選んだ NA 0.5 で 95.8 nm。実物のカラー顕微鏡写真からは、裸の Si で白を合わせるだけで画素ごとの膜厚が出て中央値 87.5 nm(−11 %)。Sánchez-Arriaga ら(Sensors 2023)の安価な分光器では、標準 476.3 nm が 2 % 以内、198.7 nm は中央値 +6.6 % で、1 本は最良の候補が外れ正しい値は 2 番目の候補に残ります。そのあと、Airy の式(別実装)・多層膜の閉形式・FFT の下限 2/Δx・材料の取り違えと NA の偏りを閉形式で、公表の色表(Pliskin & Conrad 1964 の写し)との色相を弱い門で、合成のウェハ(スピンコート欠陥の量は文献表に結びつけた模型)の膜厚マップを真値で採点します。

## What it does

Five ops in `filmoptics` (category `film`), with every film and substrate given by its key in the material table: the transfer-matrix reflectance, transmittance and absorptance of a multilayer stack (oblique incidence, s/p, the angular average of a focusing NA, conformal roughness), the interference colour against thickness (the wafer colour chart, in sRGB and CIELAB under D65 or any illuminant), thickness from the fringe period by FFT (dispersion-corrected, with the closed-form lower limit 2/Δx), thickness by a non-linear least-squares fit of the transfer-matrix model (global grid then golden-section refinement, all local candidates returned), and per-pixel thickness maps from a spectral or an RGB image together with a map of how many thicknesses fit equally well.

## 向くところ / 向かないところ

**向く**: 分光膜厚計の解析(FFT とあてはめの使い分け、薄い膜は FFT でなくあてはめ)、顕微分光の対物の NA による見かけの膜厚の補正、材料(屈折率)の取り違えの検出(あてはめの残差)、ウェハ・フィルムの色むらから膜厚むらを読む検査の設計(RGB で足りるか、分光カメラが要るか)、AR 膜・誘電体ミラーの設計の検算。

**向かない**: ★膜は均質・等方で、界面は平行です(くさび・勾配屈折率・複屈折の膜は扱いません)。粗さは共形(すべての界面が同じ高さで揺れる)だけで、散乱光の行き先は持たないので、粗さ > 0 では透過率と吸収率を出しません。集光の NA は瞳を一様に満たす照明の円錐の平均で、斜入射との併用はできません。材料表の波長範囲の外(例: PMMA は 437 nm から)は拒否します。RGB の判定は CIE 1931 の等色関数のカメラ(Luther 条件を満たす理想)で、実機のカメラの分光感度ではありません。

## 最初の 1 本

```python
import filmoptics as F

# Si 上の SiO2 1000 nm の反射スペクトル(400〜800 nm)から膜厚を 2 通りで
sp = F.multilayer_reflectance([("SIO2", 1000.0)], "SI", 400.0, 800.0, 401)
print(round(F.film_thickness_fft(sp)["thickness_nm"], 1))                    # 1002.2(縞の周期)
print(round(F.film_thickness_fit(sp, "SIO2", "SI", 0, 3000)["thickness_nm"], 1))  # 1000.0(モデル)

# 材料を取り違える(Si3N4 の n で読む)と、光学的厚さ n d を保って薄く出る
print(round(F.film_thickness_fit(sp, "SI3N4", "SI", 0, 3000)["thickness_nm"]))   # 708

# 膜厚 100〜500 nm の干渉色(D65、sRGB)
print(F.film_color("SIO2", "SI", 100.0, 500.0, 5)["srgb"].round(2))
```

走らせて見るなら `py -3.11 examples/poc_thin_film_reflectometry.py`(図は `FULLSEYE_FIGURE_DIR` を指定したとき)。

## 推奨パイプライン

`multilayer_reflectance` → `film_thickness_fft` → `film_thickness_fit` → `film_thickness_map`

積層を材料表の鍵で書いて順問題を確かめ(`multilayer_reflectance`)→ 縞が 2 本以上あれば `film_thickness_fft` で初期値と「信頼できるか」を見て → `film_thickness_fit` で決める(候補を全部見る)→ 面で見るなら分光画像を `film_thickness_map`。

## 代替

単層だけなら `thin_film_reflectance`(Airy の式)。色の見本・RGB の判定は `film_color`。

## 限界

直入射のモデルは顕微分光の膜を薄く読む(実測で −5.7 %、NA を入れると −2.7 %)。FFT は縞 2 本未満(400〜800 nm の SiO₂ で約 540 nm 未満)で破綻する。RGB は色が周期的に似るので次数を取り違える画素が残る。安価な分光器の 198.7 nm の標準では最良の候補が外れた例があり、候補の 2 番目を見る。

## 実寸校正

反射率の絶対値は裸の Si(材料表の Si の Fresnel)を基準にする(公開の実測と中央値 0.4 % 差)。任意単位の分光器は `fit_scale=True`、カメラは裸の Si の領域でチャンネルごとに白を合わせる。

## 裏づけ

- op: `multilayer_reflectance`、`film_color`、`film_thickness_fft`、`film_thickness_fit`、`film_thickness_map`
- 例: [`poc_thin_film_reflectometry`](../../examples/poc_thin_film_reflectometry.py)
- 実測データ(CC BY 4.0): Schwarz ら 2024(Zenodo 10.5281/zenodo.13753754)、Sánchez-Arriaga ら 2023(10.15131/shef.data.23285603)。出典と改変は `data/thin_film_real/README.md`。
