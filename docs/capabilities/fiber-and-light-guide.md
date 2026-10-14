---
id: fiber-and-light-guide
title: 光ファイバとライトガイド(ガラスの分散 → LP モード → モード径 → 照明の効率)
title_en: Optical fibres and light guides (glass dispersion, LP modes, mode field diameter, illumination efficiency)
category: 光と色
ops: [material_group_index, material_gvd, fiber_numerical_aperture, fiber_v_number, fiber_lp_modes, fiber_mode_field_diameter, fiber_bundle_coupling]
examples: [poc_fiber_light_guide]
version: 0.6.1
---

# 光ファイバとライトガイド(ガラスの分散 → LP モード → モード径 → 照明の効率)

## できること

検査の照明はライトガイド(ファイバの束)で運び、干渉・分光の光は単一モードファイバで運びます。どちらもガラスの分散と導波の式で決まるので、`fiberoptics` の 7 本は材料表(`materials`)のガラスを名前で受けます。

ガラスの分散は `material_group_index`(群屈折率 n − λ dn/dλ)と `material_gvd`(分散パラメータ D = −(λ/c) d²n/dλ²、ps/(nm·km))で、どちらも材料の曲線と同じ pairs(λ nm, 値)。ファイバは `fiber_numerical_aperture`(NA と受け入れ角、屈折率は数か材料名)、`fiber_v_number`(V と単一モードの遮断波長)、`fiber_lp_modes`(弱導波の LP_lm の特性方程式を区間ごとに二分法で解き、各モードの u・w・b と縮退込みのモード数)、`fiber_mode_field_diameter`(LP01 の厳密な場に重なり最大のガウスを当てた MFD と、Marcuse の近似式・2 次モーメントの定義の値)。照明は `fiber_bundle_coupling`(充填率 × 端面の Fresnel × NA の受け入れ × 減衰)。

PoC `poc_fiber_light_guide` は、遮断が Bessel の零点で切り替わること、V = 30 でモード数が V²/2 になること、b(V) と MFD が公表の近似式と合うこと、溶融石英の材料分散の零点が 1.27 µm にあること、ITU-T G.652 の MFD の範囲に入る設計を外の真値で採点します。

## What it does

Seven ops in `fiberoptics` (category `fiber`): group index and material dispersion D(λ) from the material table, numerical aperture, V number and cutoff wavelength, LP_lm modes by solving the weakly guiding characteristic equation, the mode field diameter of LP01 (best-overlap Gaussian, with the Marcuse fit and the second-moment definition alongside), and the efficiency of a light guide (packing fraction, end-face Fresnel, NA acceptance, attenuation). Gates: Bessel-zero cutoffs, V²/2 mode count, the Rudolph–Neumann b(V) and Marcuse MFD fits, the 1.27 µm zero of silica's material dispersion, and the ITU-T G.652 MFD range.

## 向くところ / 向かないところ

**向く**: ライトガイドの選定(NA と充填率と長さで何割届くか)、単一モードファイバの設計(遮断波長・MFD)、分光・OCT・干渉計のファイバの分散の見積り、ガラスの群屈折率と分散の比較。

**向かない**: ★弱導波(Δ ≪ 1)のスカラー近似です。高 NA のファイバ(Δ が大きい)・偏波保持・フォトニック結晶ファイバ・曲げ損失・グレーデッド型は扱いません。LP0m(m ≥ 2)は遮断の直上で束縛が指数関数的に弱く、遮断から V で約 0.05 以内は根が浮動小数で表せず数えません(PoC の門で明示)。コアとクラッドの屈折率差は材料表に無い(ドープした石英の表は未同梱)ので、NA か屈折率の数で渡してください。ライトガイドの受け入れは Lambert の光源の立体角の比で、束の中の混ざり方や出口の配光は扱いません。

## 最初の 1 本

```python
import fiberoptics as F

# 標準の単一モードファイバ(コア半径 4.1 µm、NA 0.12): 1310 nm で単一モードか、MFD は
v = F.fiber_v_number(4.1, 0.12, 1310.0)
print(v["single_mode"], round(v["cutoff_wavelength_nm"]))            # True 1285
print(round(F.fiber_mode_field_diameter(4.1, v["v"])["mfd_um"], 2))  # 9.06(G.652 は 8.6〜9.5 µm)

# 溶融石英の材料分散の零点(≈ 1.27 µm)
D = F.material_gvd("SILICA", 1200.0, 1350.0, 151)
```

走らせて見るなら `py -3.11 examples/poc_fiber_light_guide.py`(図は `FULLSEYE_FIGURE_DIR` を指定したとき)。
