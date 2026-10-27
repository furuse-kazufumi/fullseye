---
id: photoelasticity
title: 光弾性で応力を測る(応力場 → 縞 → 偏光像 → 位相差と主軸)
title_en: Measure stress by photoelasticity (stress field, fringes, polarisation images, retardation and axis)
category: 測る
ops: [brazilian_disc_stress, kirsch_plate_stress, principal_stress, photoelastic_retardation, retardation_from_birefringence, retardation_convert, cubic_photoelastic_birefringence, silicon_piezo_optic_coefficients, polariscope_intensity, photoelastic_polarization_images, photoelastic_phase_estimate, retardation_unwrap_multiwavelength, polarization_demosaic]
examples: [poc_photoelasticity]
version: 0.8.1
inputs: [image2d]
pipeline: [polarization_demosaic, photoelastic_phase_estimate]
alternatives: [polarization_stokes, mueller_from_intensities, unwrap_phase_2d]
limits: 平面応力と薄い試験片(光が板厚方向に一様な応力を通る)を仮定し、応力光学係数の分散は扱わない。4 方位の偏光カメラだけでは位相差は 1/4 波長まで。
calibration: 円板の直径圧縮(荷重既知)を撮って応力光学係数(材料縞値)を合わせ、波長と板厚は SI(m)で渡す。
---

# 光弾性で応力を測る

## できること

透明な試験片や単結晶ウェハを偏光で撮り、縞から**主応力差と主応力の向き**を読む族です。真値つきの応力場(直径方向に圧縮した円板 `brazilian_disc_stress`、穴のある無限板の一軸引張 `kirsch_plate_stress`)、主応力 `principal_stress`、等方材料の応力光学則 `photoelastic_retardation`(δ = 2π t C (σ1−σ2)/λ と材料縞値)、立方晶 {100} 面の異方性 `cubic_photoelastic_birefringence`(Si などで結晶方位により位相差が変わる。係数は `silicon_piezo_optic_coefficients` が出典つきで返す)、平面・円偏光器の明暗視野の強度 `polariscope_intensity`、円偏光照明の試料を偏光カメラ(0/45/90/135 度)や 6 強度の偏光計で撮った像 `photoelastic_polarization_images` と、その閉形式の逆算 `photoelastic_phase_estimate`、多波長からの次数決定 `retardation_unwrap_multiwavelength` まで揃います。

位相差は **rad・nm・縞次数を並べて返し**、長さは m、応力は Pa、係数は Pa⁻¹ で受けます。6 mm を 6 と、550 nm を 550 と、表の ×10⁻⁷ MPa⁻¹ をそのまま Pa⁻¹ として渡すと ValueError で止まります。

## What it does

A photoelasticity family: closed-form stress fields with known truth (a
diametrically compressed disc, Kirsch's plate with a hole), principal stresses,
the stress-optic law for isotropic materials and for cubic crystals cut on a
{100} plane (silicon coefficients with their published source), plane and
circular polariscope intensities, the four-direction polarisation-camera and
six-intensity polarimeter images of a specimen under circular light, their
closed-form inversion to retardation and principal axis, and multi-wavelength
order resolution. Retardation is always returned in rad, nm and fringe order
together; lengths are metres, stresses Pa, coefficients Pa⁻¹, and unit slips
(mm as m, nm as m, a table value in ×10⁻⁷ MPa⁻¹ as Pa⁻¹) raise ValueError.

## 向くところ / 向かないところ

透明樹脂・ガラス・Si ウェハの残留応力や荷重下の応力分布、偏光カメラ 1 枚からの主軸と位相差の読み取り、教材や検査アルゴリズムの真値づくりに向きます。厚い試験片の 3 次元応力(凍結法・散乱光法)、塑性域、応力光学係数の波長分散を含む高次の縞の厳密な解析には向きません。

## 最初の 1 本

```python
import numpy as np
import photoelastic as pe

# 直径 50 mm・厚さ 6 mm の円板を 500 N で直径方向に圧縮(真値は閉形式)
disc = pe.brazilian_disc_stress(radius_m=0.025, thickness_m=0.006, load_n=500.0, size=129)
p = pe.principal_stress(disc["sxx"], disc["syy"], disc["txy"])
# 応力光学係数 C [Pa^-1](樹脂の桁)・波長 550 nm で位相差に
ret = pe.photoelastic_retardation(p["difference"], 0.006, 5e-11, 5.5e-7)
print("centre fringe order:", round(float(ret["fringe_order"][64, 64]), 3))

# 円偏光照明の試料を 6 強度の偏光計で撮り、閉形式で δ と主軸を戻す
images = pe.photoelastic_polarization_images(ret["delta_rad"], p["angle_deg"], "stokes6")
est = pe.photoelastic_phase_estimate(images, "stokes6")
ok = disc["inside"] & (ret["delta_rad"] > 0.05) & (ret["delta_rad"] < np.pi - 0.05)
back = est["delta_rad"] * 5.5e-7 / (2 * np.pi * 0.006 * 5e-11)
print("max relative error of sigma1 - sigma2:",
      float(np.max(np.abs(back[ok] - p["difference"][ok]) / p["difference"][ok])))

# Si(100) ウェハ: 同じせん断でも結晶方位で位相差が変わる
si = pe.silicon_piezo_optic_coefficients("stoehr2020")
for phi in (0.0, 22.5, 45.0):
    dn = pe.cubic_photoelastic_birefringence(0.0, 0.0, 1e7, si["pi11_minus_pi12"], si["pi44"],
                                             3.5, crystal_angle_deg=phi)["delta_n"]
    print(phi, "deg  delta_n =", float(dn))
```

## 推奨パイプライン

`polarization_demosaic` → `photoelastic_phase_estimate`。

偏光カメラの生のモザイク 1 枚を 0/45/90/135 度の 4 枚に戻し、そのまま位相差 δ(1/4 波長まで)と主軸を読みます。1/2 波長まで要るときは右・左回りの円の検光子 2 枚を足して `analyzers="stokes6"`、それ以上は波長を変えて撮り `retardation_unwrap_multiwavelength` で次数を決めます。

## 代替

視野全体の偏光状態だけなら `polarization_stokes`、試料の Mueller 行列を丸ごと取るなら `mueller_from_intensities`、空間的につながった位相を 1 波長でつなぐなら `unwrap_phase_2d`(等方点の近くで壊れることに注意)。

## 限界

平面応力・薄い試験片を仮定します(板厚方向に応力が一様)。応力光学係数の分散は扱わず、多波長の次数決定は分散なしを仮定します。4 方位の直線検光子だけでは cos δ の符号が見えないので δ ≤ π/2 に限られ、(δ, θ) と (−δ, θ+90°) は同じ像になります。立方晶は {100} 面に垂直に光を通す場合だけです。Si の係数は Stoehr ら(2020)の表 1 の値で、同論文の測定値以外の 4 行は同表が引用した値です(原論文は照合していません)。

## 実寸校正

荷重既知の円板(`brazilian_disc_stress` の中心値 −6P/(πDt) と 2P/(πDt))を同じ光学系で撮り、読んだ縞次数から応力光学係数(材料縞値 f_σ = λ/C)を合わせます。板厚と波長は m で、応力は Pa で渡します。
