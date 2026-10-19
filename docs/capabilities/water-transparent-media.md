---
id: water-transparent-media
title: 水と透明媒質(海の波・水面のフレネルと屈折・水中の色と散乱・瓶のレンズ作用)
title_en: Water and transparent media (ocean waves, Fresnel and refraction at the surface, colour and scattering under water, a bottle as a lens)
category: 光と色
ops: [ocean_spectrum, ocean_height_field, fresnel_water_air, snell_window, refracted_view, water_attenuation, underwater_image, phase_function_hg, scattering_phase_petzold, cylinder_lens_caustic]
examples: [poc_water_transparent_media]
version: 0.7.0
inputs: [rgbimage, image2d]
pipeline: [ocean_height_field, refracted_view, water_attenuation, underwater_image]
alternatives: [ocean_spectrum, fresnel_water_air, snell_window, phase_function_hg, scattering_phase_petzold, cylinder_lens_caustic]
limits: 平らな水の見かけの深さ d/n は真上の近傍だけ(30° で 7 %、60° で 52 % の過大評価)。PM / JONSWAP の海は毛管波を持たず、格子で解ける波の傾きは Cox & Munk の 1〜2 割(飽和域を毛管波数まで延ばすと 5 m/s では合うが 10 m/s は 4 割届かない)。水の吸収は 380〜727.5 nm、ジャーロフの表は 400〜700 nm(3C は 650 nm、5C は 575 nm まで)で、外は拒否する。Kd を視線に沿った減衰として使うのは近似で、実際は距離と深さで変わる。波面の屈折は焦線の近くで経路が複数あり、見つけた 1 本だけを返す(式を満たさなければ NaN)。
calibration: 水の種類は実測の Kd(またはディスク透視度)から最も近いジャーロフ型を選ぶ。屈折率は波長ごとの材料表なので、塩分・温度の違いは n_water で与える。カメラ画像の色は、センサの分光感度と露出で変わるので、RGB は 3 つの代表波長の近似(分光画像なら波長を渡す)。瓶の焦線は光軸に直交する断面の 2 次元の光線追跡で、円柱の長さ方向の曲がりは無い。
---

# 水と透明媒質(海の波・水面のフレネルと屈折・水中の色と散乱・瓶のレンズ作用)

## できること

水は、上から見れば動くレンズ、下から見れば距離で濃くなる色フィルタです。`watermedia` の 10 本は、その両方を閉形式と公表値の表に載せ、数値解は別の経路で確かめられるようにしたものです。`ocean_spectrum` は風速から Pierson–Moskowitz(1964)と JONSWAP(1973)の波のスペクトル、有義波高、周期を返し、`ocean_height_field` はそれを Tessendorf(2001)の FFT で 2 次元の海にして(高さ・傾き・法線・荒れによる水平変位、水深の分散関係)返します。

`fresnel_water_air` は水の屈折率(材料表の実部で、波長による分散込み)から反射率・透過率・屈折角・全反射の旗を、`snell_window` は窓の半径と見かけの深さを返します。`refracted_view` は水中の点が水面の上のカメラにどこに見えるかを、光路長の停留点(フェルマーの原理)として求めます。平らな水は二分法で機械精度、波のある水は高さの双 3 次補間の勾配のニュートン法で、見つけた点でベクトルのスネルの式を検算し、合わない点は NaN と `converged = False` にします。

`water_attenuation` は純水の吸収(Pope & Fry 1997)と散乱(Smith & Baker 1981)、およびジャーロフの水の型(I から 9C)の a・b・Kd(Solonenko & Mobley 2015)と深さごとの透過率を、`underwater_image` はそれを使って Akkaynak & Treibitz(2018)の画像形成(直接光の減衰 + 後方散乱のベール)で水中の見え方を作ります。`phase_function_hg` と `scattering_phase_petzold` は散乱の位相関数、`cylinder_lens_caustic` は円柱(棒・瓶)の近軸焦点と実光線の焦線で、水を入れた瓶だけが光を 1 本の線に集めることを示します。

## What it does

Ten ops in `watermedia` (category `watermedia` of `opsoptics`): the wave spectrum of a wind sea (Pierson-Moskowitz, JONSWAP) and a Tessendorf FFT sea with slopes, normals, choppiness and finite depth; Fresnel reflectance and transmittance of the air-water interface with the dispersive index of the material table; Snell's window and the apparent depth; the apparent position of an underwater point as a stationary point of the optical path (bisection on a flat surface, Newton iteration with the vector Snell law verified on a wavy one); pure-water absorption (Pope & Fry 1997), scattering (Smith & Baker 1981) and the diffuse attenuation of the Jerlov water types (Solonenko & Mobley 2015); underwater image formation (Akkaynak & Treibitz 2018); the Henyey-Greenstein and Petzold phase functions; and the paraxial focus and real-ray caustic of a cylinder. Inputs outside a table, unknown water types, |g| >= 1 and n <= 1 are refused; a path that does not satisfy Snell's law is returned as NaN.

## 向くところ / 向かないところ

**向く**: プールや水槽・水面越しの計測の見かけの位置ずれの見積り、波による画像の揺れの模擬(動画の試験データ)、水中カメラの色と到達距離の見積り(深さごとに何が見えなくなるか)、スネルの窓や全反射の設計、液面検査の照明(水を入れた瓶だけに明るい線が出る)の下調べ、散乱の位相関数をモンテカルロの光線追跡に渡す準備。

**向かない**: 毛管波を含む荒れた海の傾きの分布(Cox & Munk を合わせる用途は、毛管波を持つスペクトルが要る)。強い波の砕波・泡・飛沫。吸収と散乱が場所で変わる濁り(型は一様な水)。偏光を含む水中の撮像。瓶の長さ方向の曲がりと、ガラスの厚みの不均一。

## 推奨パイプライン

`ocean_height_field` → `refracted_view` → `water_attenuation` → `underwater_image`

海(または水槽の波)の高さと傾きを作り → `refracted_view` に点とカメラと高さの表を渡して見かけの位置を得て → `water_attenuation` で水の種類と深さの減衰を引き → `underwater_image` で色票や場面の記録された色を作る。

## 代替

波のスペクトルだけなら `ocean_spectrum`、水面の反射と全反射の角度だけなら `fresnel_water_air` / `snell_window`、散乱の位相関数は `phase_function_hg`(解析式)か `scattering_phase_petzold`(実測)、瓶や円柱の焦線は `cylinder_lens_caustic`。

## 限界

- 平らな水の見かけの深さ d/n は真上の近傍だけ。30° で 7 %、60° で 52 % の過大評価(`snell_window` の `view_angle_deg` で厳密値)。
- PM / JONSWAP の海は毛管波を持たず、格子で解ける波の傾きは Cox & Munk の 1〜2 割。飽和域を毛管波数まで延ばすと 5 m/s では合う(−2.5 %)が 10 m/s は 4 割届かない(−38.7 %)。
- 表の外は拒否: 純水の吸収は 380〜727.5 nm、ジャーロフの型は 400〜700 nm(3C は 650 nm、5C は 575 nm まで)。I と IA の散乱は原著者が自分の定数と合わないと注記している(`b_suspect`)。
- Kd を視線に沿った減衰として使う(Akkaynak & Treibitz が示すように実際は距離と深さで変わる)。後方散乱のベールは 1 回散乱の近似。
- 波面の屈折は焦線の近くで経路が複数になる。見つけた 1 本だけを返し、スネルの式を満たさないときは NaN。

## 実寸校正

水の種類は、実測の Kd(またはディスク透視度)から最も近いジャーロフ型を選びます。屈折率は波長ごとの材料表の値で、塩分や温度の違いは `n_water` で与えます。RGB の画像は 3 つの代表波長(0.61 / 0.54 / 0.465 µm)の近似で、分光画像なら波長を渡します。瓶の焦線は光軸に直交する断面の 2 次元の光線追跡です。

## 最初の 1 本

```python
import watermedia as WM

# 風速 8 m/s の海の有義波高(閉形式 0.21 U²/g に近い)と、水の吸収の最小(Pope & Fry の表)
sp = WM.ocean_spectrum(8.0)
print(round(sp["hs_m"], 3), round(0.21 * 8.0 ** 2 / 9.80665, 3))      # 1.366 1.371
w = WM.water_attenuation(0.4175, "pure")
print(round(float(w["a"][0]), 5))                                       # 0.00442 (1/m、417.5 nm)

# 真上から見た水深 2 m の点は、1.5 m の深さ(d / n)に見える
r = WM.refracted_view([[0.0, 0.0, -2.0]], [0.0, 0.0, 4.0], n_water=4.0 / 3.0)
print(round(float(r["apparent_depth_m"][0]), 6))                        # 1.5
```

走らせて見るなら `py -3.11 examples/poc_water_transparent_media.py`(図は `FULLSEYE_FIGURE_DIR` を指定したとき)。
