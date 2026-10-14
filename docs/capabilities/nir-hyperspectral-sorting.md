---
id: nir-hyperspectral-sorting
title: 近赤外のハイパースペクトルで見た目が同じ異物を選別する(材料表の吸収帯 → 散乱層の反射 → InGaAs の帯域ごとの電子数)
title_en: Sorting look-alike foreign matter with NIR hyperspectral imaging (material absorption bands, scattering-layer reflectance, InGaAs band electrons)
category: 光と色
ops: [material_nir_absorption, carbon_black_absorption, nir_model_info, ingaas_photodiode_qe, kubelka_munk_reflectance, spectral_reflectance_from_material, hyperspectral_band_weights, hyperspectral_capture]
examples: [poc_hyperspectral_foreign_matter]
version: 0.6.1
---

# 近赤外のハイパースペクトルで見た目が同じ異物を選別する(材料表の吸収帯 → 散乱層の反射 → InGaAs の帯域ごとの電子数)

## できること

食品のライン(ナッツ・茶葉・米)に混じる殻・木片・樹脂片や、リサイクルの PET / PP / PE / PS は、色を合わせられると RGB のカメラでは分かりません。近赤外(0.9〜2.5 µm)では C-H の倍音・結合音と O-H の吸収帯が材料ごとに違うので、分光で分けられます。ここはその鎖を、観察対象と光学系が**同じ材料表**を引く形で組む 8 本です。

対象の側: `material_nir_absorption` が吸収帯の重ね合わせで α(λ) [1/mm] を返します(樹脂・脂質・タンパク質・炭水化物・リグニンと、それを分率で足すナッツの仁・殻・木片。帯の中心は一次文献の実測、幅と強さは推定。水だけは表の n,k から)。`carbon_black_absorption` は黒い樹脂の顔料、`nir_model_info` は帯と出典の印。`kubelka_munk_reflectance` は散乱する層の拡散反射の閉形式(無限厚と、背景の上の有限厚)、`spectral_reflectance_from_material` はそれに粒径の散乱と Saunderson の界面の補正を足して、材料名から反射スペクトルを作ります。

光学系の側: `ingaas_photodiode_qe`(吸収層と InP の窓の直接遷移の吸収端、標準 1.7 µm と拡張品)、`hyperspectral_band_weights`(ハロゲン × レンズのガラスの透過率(材料表)× 帯域 × QE × 画素 × 露光 = 反射率から電子数への線形写像)、`hyperspectral_capture`(1 本のスペクトルの帯域ごとの電子数と雑音)。画像(キューブ)は同じ写像を画素ごとに掛ける `spectralrad.hyperspectral_capture_cube`、帯域選択は `specops.spec_band_selection_fisher`(Fisher 比と前向き選択)。

PoC は**公開の実画像 2 つ**(樹脂の破片 6 種・豚バラの上の異物 10 種、どちらも CC BY 4.0)を主役にし、`read_envi` → `spec_continuum_removal` → `spec_angle_mapper` / `spec_band_selection_fisher` → 線形判別で分類して、データの正解ラベルで採点します(樹脂: クラス平均の再現率 0.816、材料表の物理モデルだけをライブラリにすると PP / PET / PE を 0.628。豚バラ: 全帯の LDA で検出 0.92・誤警報 1.1 %)。合成の鎖はその壊れ方(濡れ・ランプ・光子・黒い樹脂)を既知の量で振る補助です。

★2026-10-15 に材料表の水を直しました: RII の Hale & Querry の表は NIR を 0.2 µm おきにしか持たず、1.45 / 1.94 µm の吸収帯を線形補間で 1/3 に潰していました。k だけ Segelstein 1981 にして、Kou ら 1993 の実測と 10 % 以内です。

## What it does

Eight ops build the NIR sorting chain with the object and the optics reading the same material table: absorption bands for polymers, lipids, proteins, carbohydrates and lignin (and nut kernels, shells and wood as mixtures; water from the table's n,k), carbon black, the Kubelka–Munk reflectance of a scattering layer, reflectance from a material name with grain-size scattering and the Saunderson surface correction, an InGaAs QE from the direct-gap absorption edges, and the linear map from reflectance to electrons per band through a halogen lamp, the lens glass, the band filters and the QE. Gates: the Kubelka–Munk limits and inverse, measured polymer trough positions within 5 nm, water absorption within 10 % of Kou 1993, linearity and the EMVA variance of the captured cube, and the Fisher ratio's two-class closed form.

## 向くところ / 向かないところ

**向く**: 選別機の帯域と InGaAs の品種(標準か拡張か)の当たりをつけること、マルチスペクトルの帯域を Fisher 比で選ぶこと、濡れ・ランプのずれ・光子の数・黒い樹脂でどこから壊れるかを真値つきで数えること、粒径と厚さで反射がどう変わるかを閉形式で見ること。

**向かない**: ★帯の幅と強さは推定で、実測のスペクトルに合わせていません(`material_nir_absorption(..., bands=...)` で実測の帯に差し替えてください)。場面と分類器のライブラリを同じモデルから作ると逆犯罪になり、精度は実機の上限にしかなりません —— PoC はライブラリが知らないゆがみを足して、その分を数えています。Kubelka–Munk は 2 流束の近似で、鏡面の光沢・層の不均一・強い異方散乱は扱いません。InGaAs の QE は形のモデルで、データシートの曲線の代わりではありません。

## 最初の 1 本

```python
import spectralrad as S

# 仁と PE 片の反射スペクトル(材料表の吸収帯 + Kubelka–Munk)を、標準の InGaAs で 2 m/s のラインスキャン(露光 250 µs)
kernel = S.spectral_reflectance_from_material("NUT_KERNEL")
pe = S.spectral_reflectance_from_material("PE", thickness_mm=2.0, background_reflectance=0.22)
for r in (kernel, pe):
    c = S.hyperspectral_capture(r, exposure_s=250e-6, irradiance_w_m2=3000.0, pixel_um=15.0, read_noise_e=80.0)
    print((c["electrons"] / c["white_electrons"])[[25, 50]])     # 1200 nm と 1450 nm の平場補正した反射率
```

走らせて見るなら `py -3.11 examples/poc_hyperspectral_foreign_matter.py`(図は `FULLSEYE_FIGURE_DIR` を指定したとき)。
