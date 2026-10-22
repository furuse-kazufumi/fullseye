---
id: photograph-through-prescription
title: 処方どおりのレンズ越しに 3 次元の場面を撮る(被写界深度・猫の目のボケ・隅の光量・色収差・ゴースト)
title_en: Photographing a 3-D scene through the actual lens prescription (depth of field, cat's-eye bokeh, corner illumination, colour fringes, ghosts)
category: 描く
ops: [lens_scene, exit_pupil_samples, trace_sensor_rays, scene_radiance, render_scene_through_lens, bokeh_shape, render_ghost_overlay, render_compare_prescriptions]
examples: [poc_photograph_through_prescription]
version: 0.7.0
inputs: [table]
pipeline: [lens_system, lens_scene, render_scene_through_lens, render_compare_prescriptions]
alternatives: [exit_pupil_samples, trace_sensor_rays, scene_radiance, bokeh_shape, render_ghost_overlay, render_through_lens, ghost_analysis]
limits: 幾何光学のみ(回折が無いので、絞った良いレンズの点像は Airy より小さく描かれる。F/11 の三枚玉で Airy の 0.32 倍)。射出瞳は近軸の位置と大きさで標本化する(瞳収差で実際の瞳がはみ出すレンズはその分の光を取りこぼす)。透過率はフレネル損失なし(fresnel=True で非偏光のフレネル損失、コーティングとガラスの吸収は無し)。ゴーストは 2 回反射だけ。点光源は前向きの追跡で重ねるので遮られず影を作らない。非軸対称の系(偏心・傾き)の点光源とボケの形は未対応(拒否)。
calibration: センサは画素ピッチ・QE・フルウェル・読み出しノイズ・暗電子・ビット数の実測値で与える(EMVA 1288 の値)。光源の強さは分光放射照度(W/m²/nm)か分光強度(W/sr/nm)、露光は秒で、電子数は E dλ A t (λ/hc) QE の閉形式に 1e-3 以内で合う。処方は raytrace.lens_system(.zmx の読み込みは lensfile)。
---

# 処方どおりのレンズ越しに 3 次元の場面を撮る(被写界深度・猫の目のボケ・隅の光量・色収差・ゴースト)

## できること

レンズ設計の画面は、スポットダイアグラムや MTF の数字までは出してくれますが、「この処方で 1 m 先の資料を撮ると、絵は実際どう写るのか」までは見せてくれません。`lensrender` の 8 本は、センサ側から射出瞳を標本化して処方の全面を**逆向きに**追跡し(Kolb, Mitchell & Hanrahan 1995)、物体空間の場面で陰影をつけて、光子・ショットノイズ・読み出しノイズ・量子化まで通します。

`lens_scene` は平面(テクスチャつき)・球・三角形のメッシュ・平行光と点光源・点光源の像(ボケ・ゴースト用)を持つ場面の表を検証して作ります。`exit_pupil_samples` は近軸の射出瞳の位置と半径から標本点と面積の重みを、`trace_sensor_rays` はセンサの点 → 瞳の点 → 全面(スネルの式と分散・非球面・鏡・口径・全反射)を逆向きに通って物体空間の光線にし、ケラレた光線を印つきで返します(`ray_bundle` の逆と 1e-9 mm、方向 1e-12 で一致)。`scene_radiance` は光線がシーンに当たったときのランバート面 + ブリン・フォンの反射 + 影の放射輝度、`render_scene_through_lens` はそれを画素ごと・瞳の点ごと・波長ごとに足して放射照度 → 電子数 → ノイズ → 画像にします。

`bokeh_shape` はピントのはずれた点の形(猫の目)と軸上の円との面積比、`render_ghost_overlay` は `raytrace3d` の 2 回反射のゴーストを電子数で重ね、`render_compare_prescriptions` は同じ場面を複数の処方で撮って、RMS スポット・隅の光量・歪み・横色収差・刃の立ち上がりと MTF50 の表にします。

## What it does

Eight ops in `lensrender` (category `lensrender` of `opsoptics`) photograph a 3-D scene through a `raytrace.lens_system` prescription by sensor-side ray tracing (Kolb, Mitchell & Hanrahan 1995): the exit pupil is sampled for every sensor point, each ray is traced backwards through every surface (Snell's law with dispersion, conics and aspheres, mirrors, semi-diameters as stops, total internal reflection) into object space, the scene is shaded there (textured planes, spheres, triangle meshes, Lambertian plus a Blinn-Phong lobe, shadows, point sources splatted by forward tracing) and the radiance is summed with the weight cos^2(theta)/d^2 of the pupil sample. The irradiance becomes electrons (E dlambda A t (lambda/hc) QE) and goes through shot noise, dark electrons, read noise and the quantiser. `bokeh_shape` gives the out-of-focus footprint (the cat's eye), `render_ghost_overlay` adds the two-reflection ghosts of a bright point and `render_compare_prescriptions` renders one scene through several prescriptions and tabulates RMS spots, corner illumination, distortion, lateral colour and the edge rise and MTF50. Geometric optics only: no diffraction.

## 向くところ / 向かないところ

**向く**: 設計の数字を「絵」で確かめる(同じ EFL の 2 本の処方の解像チャート・傷の見え方・ボケの形・隅の光量・色収差・ゴースト)、被写界深度と絞りの効果の見積り、検査用の画像のシミュレーション(傷が写るか、どの距離まで合焦と言えるか)、レンズの試作前の画像データ作り。

**向かない**: 回折が支配する絞り込んだ撮像(Airy 円盤より小さく描かれる)、コーティングの角度・波長依存と散乱によるフレア、偏光、非軸対称の系の点光源(拒否する)、実写の代わり(場面は平面・球・三角形と点光源の簡単なもの)。

## 推奨パイプライン

`lens_system` → `lens_scene` → `render_scene_through_lens` → `render_compare_prescriptions`

処方を作り(または `lensfile` で読み)、場面を `lens_scene` で作って、`render_scene_through_lens` で撮ります。複数の処方を比べるなら `render_compare_prescriptions` に処方の列を渡します。合焦は `focus_mm`(その距離の近軸の像面にセンサを置く)、ピントのずれは `defocus_mm`、センサの一部だけを撮るときは `sensor["center_mm"]` です。

## 代替

射出瞳の標本点だけなら `exit_pupil_samples`、1 本ずつの光線は `trace_sensor_rays`、場面の陰影だけなら `scene_radiance`、ボケの形だけなら `bokeh_shape`、ゴーストの重ねだけなら `render_ghost_overlay`。平らな絵をレンズの PSF で劣化させるだけなら `render_through_lens`(2.5 次元の近似)、ゴーストの表だけなら `ghost_analysis`。

## 限界

- 幾何光学のみ。絞った良いレンズの点像は Airy 円盤より小さく描かれる(F/11 の三枚玉で EE 83.8 % の半径が Airy の 0.32 倍、F/6.25 は収差が支配で 2.7 倍)。
- 射出瞳は近軸の位置と大きさで標本化する。瞳収差で実際の瞳が外へはみ出すレンズは、はみ出した分の光を取りこぼす(`aim="stop"` の `ray_bundle` との差は 15° で 1.7 %)。
- 白い面の相対照度は `lensimage` と 0.7 視野まで 2 % 以内(1.61 %)。8.7° では 3.2 % 離れる(`lensimage` は物体側の cos⁴、描画は像側の cos⁴)。
- 像面湾曲や非点収差のあるレンズでは、猫の目の面積比と瞳の通過率は一致しない(ボケの円盤そのものが変わる)。収差ゼロの理想レンズでは、2 つの円の重なりの閉形式と 5 % 以内で一致する。
- ゴーストは 2 回反射だけで、反射率は面ごとに一定(角度依存のコーティングは `raytrace3d.surface_reflectance` の指定を渡す)。点光源は遮られず、影を作らない。
- 図のざらつきは瞳の標本化の確率誤差(瞳の点を増やすと √ で減る)で、センサのノイズではない。

## 実寸校正

センサは画素ピッチ・QE・フルウェル・読み出しノイズ・暗電子・ビット数の実測値(EMVA 1288 の測定値)で与えます。光源は分光放射照度 W/m²/nm(平行光)か分光強度 W/sr/nm(点光源)、露光は秒で、電子数は E dλ A t (λ/hc) QE の閉形式に 1e-3 以内で合います(門)。波長は 3 つの代表波長(F・d・C 線)が既定で、分光の絵なら波長の列を渡します。RGB の反射率は 3 つの代表波長(0.61 / 0.54 / 0.465 µm)の近似です。

## 最初の 1 本

```python
import lensrender as LR
import raytrace as RT

# EFL 50 mm の理想レンズで 1 m の白い面(反射率 0.5、平行光 1 W/m²/nm)を撮る: 放射照度は π L sin²α の閉形式 0.0044721 に合う
s = RT.lens_system([{"f": 50.0, "t": None, "ap": 5.0}], stop=0, object_mm=1000.0)
scene = LR.lens_scene([{"type": "plane", "z_mm": -1000.0, "albedo": 0.5}],
                      [{"type": "directional", "to_light": (0, 0, 1), "irradiance_W_m2_nm": 1.0}])
r = LR.render_scene_through_lens(s, scene, {"size": (3, 3), "pixel_pitch_um": 10.0}, pupil_samples=64,
                                 wavelengths=[0.588], add_noise=False)
print(round(float(r["irradiance_W_m2_nm"][0][1, 1]), 5))                 # 0.00447

# 1 mm ピントがずれた点光源のボケの円の直径は 2 |Δz| NA'(NA' = 0.095)
b = LR.bokeh_shape(s, (0.0, 0.0), 1.0, 300)
print(round(2.0 * (b["axis_area_mm2"] / 3.141592653589793) ** 0.5, 3))   # 0.19
```

走らせて見るなら `py -3.11 examples/poc_photograph_through_prescription.py`(図は `FULLSEYE_FIGURE_DIR` を指定したとき)。
