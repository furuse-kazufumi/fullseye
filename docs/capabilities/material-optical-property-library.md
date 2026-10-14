---
id: material-optical-property-library
title: 材料の光学物性を 1 つの表で引く(硝材・結晶・半導体・金属・液体・プラスチック 83 種、一次文献の係数と数表、硝材カタログの取り込み口)
title_en: One table of material optical constants (83 glasses, crystals, semiconductors, metals, liquids and plastics from primary literature, with a glass-catalogue importer)
category: 光と色
ops: [material_table, material_record, material_optical_constants, material_dispersion, material_extinction, material_absorption, material_transmittance, material_reflectance, abbe_number, glass_map, thermo_optic_coefficient, plate_focus_shift, silicon_free_carrier_absorption, material_from_sellmeier, material_from_curves, read_glass_catalog_agf]
examples: [poc_material_optical_library]
version: 0.6.1
---

# 材料の光学物性を 1 つの表で引く(硝材・結晶・半導体・金属・液体・プラスチック 83 種、一次文献の係数と数表、硝材カタログの取り込み口)

## できること

観察用の光学系(レンズ・窓・鏡・膜)も観察対象(ウェハ・モールド・はんだ)も、見え方は材料の光学特性で決まります。これまで Fullseye は硝材 20 種の Sellmeier(`raytrace`)、金属 5 種の 5 点の n,k(`glassmirror`)、見た目のカタログ(`surfacelib` / `metalfinish`)が別々の名前空間にあり、同じ材料を光学系側と対象側で引く口がありませんでした。この回は**1 材料 = 1 レコード**の材料表を `materials` に作り、`opsoptics` の新カテゴリ `matprop` に 16 本を足しました。

表の中身は refractiveindex.info database(CC0 1.0)の一次文献の係数と数表だけで、`tools/gen_material_tables.py` が `materials_data.py` を生成します(出典とページを各区間に残す)。硝材 46 種(4 社のカタログの Sellmeier / Schott 多項式、n_d・V_d・密度・熱膨張・dn/dT の式 A の係数)、結晶と IR 材 12 種(石英・CaF₂・BaF₂・MgF₂・LiF・KBr・CsI・サファイア・YAG・ZnSe・ZnS・水晶)、半導体 6 種(Si は Green 2008 の n,k 0.25〜1.45 µm と Salzberg の IR Sellmeier、Ge・GaAs・GaN・InP・SiC)、膜 4 種(Si₃N₄・TiO₂・Ta₂O₅・HfO₂)、金属 10 種(Ag・Au・Cu・Al・Cr・Ni・Rh・W・Ti・Pt の n,k の表、すべて測定またはそれに合わせた模型)、水(Daimon 20 ℃ と Hale の 0.2〜200 µm)、プラスチック 4 種(PMMA・PC・PS・COP)。メーカーの硝材カタログ本体(.agf)は同梱せず、`read_glass_catalog_agf` がユーザーのファイルを読みます(Zemax の分散式 1〜13 を全部受け、内部透過率の行から k を復元)。

op は材料を**名前で**受け(別名可、`material_from_sellmeier` / `material_from_curves` が返すレコードも可)、波長曲線はすべて `pairs`(λ [nm], 値)で返します —— 光源・センサ QE・ライトガイドの曲線と同じ形なので、像 = 光源 × 光学系 × 対象 × QE の波長積分にそのまま渡せます。`material_optical_constants`(1 波長の n・k・α・ε・垂直反射率と出典)、`material_dispersion` / `material_extinction` / `material_absorption`(曲線)、`material_transmittance`(平行平板、多重反射込み)、`material_reflectance`(Fresnel、角度と偏光)、`abbe_number` / `glass_map`(Abbe 図)、`thermo_optic_coefficient`(カタログの式 A の dn/dT と Δn)、`plate_focus_shift`(平行平板の焦点ずれ t(1 − 1/n) と縦球面収差)、`silicon_free_carrier_absorption`(Schroder 1978 の λ² 則)。区間外は外挿せず ValueError、k の表が無い区間は k = 0 を `k_source = None` で隠しません。

PoC は 46 種の硝材で分散式の n_d / V_d がカタログ公表値と 4e-6 / 0.005 で合うこと、Si の Green 2008 の表の点、銀の Johnson & Christy の点、Si 平板の透過率が閉形式と 1e-9、第二実装 optiland 0.6.3 と 23 点で 1e-6 を門にします。

**同じ表を引く(第 2 段、2026-10-14)**: レンズ・鏡・観察対象の op も、この表を引くようにしました。`raytrace.glass_catalog` は手元の 20 種に加えて透過材 63 種(他社の硝材・結晶・樹脂・水)を名前で引き、`lens_system` の面の `n` に `"S-LAH58"` や `"PMMA"` と書けば、その表の範囲で光線追跡・色収差・公差解析が回ります(範囲外は ValueError、金属はレンズの媒質として拒否)。`glassmirror.metal_optical_constants` / `metal_mirror_rgb` は `source="materials"` で一次文献の数表(10 金属、`MEASURED_METALS`)になり、`optscene.scene_material` の金属も `metal_source="materials"` で同じ表から作れます(既定はどちらも従来の 5 点の粗い表のままで、既存の図と値は変わりません)。raytrace が手で写していた 20 種の係数は、この表と 400〜950 nm で 4e-16 の同じ曲線でした。

★**所見(選定の誤り)**: 初版の表は W と Pt に、電子エネルギー損失(REELS)から逆算した表(Werner 2009)を選んでいて、550 nm の垂直反射率が W 0.84・Pt 0.93 と、別の測定(W 0.50、Pt 0.64〜0.73)から大きく外れていました。W は Weaver の測定、Pt は Tselin 2024 の分光エリプソメトリに差し替え、反射率を別の一次文献の値と突き合わせる門を足しました。同じ金属でも一次文献で反射率が 0.3 違うので、表を 1 本に決めるなら独立の表との突き合わせが要ります。

## What it does

Sixteen ops in the new `matprop` category of `opsoptics`, backed by one record per material in `materials_data.py` (generated from the refractiveindex.info database, CC0: primary-literature coefficients and tables with their citation on every wavelength segment). 46 catalogue glasses from four makers, 12 crystals and IR materials, 6 semiconductors (Si with Green 2008 n,k and the Salzberg IR Sellmeier), 4 films, 10 metals, water and 4 plastics. Every curve comes back as `pairs` (λ nm, value) so sources, optics, targets and sensor QE share one shape. `read_glass_catalog_agf` reads the user's own .agf catalogues (all 13 Zemax dispersion formulas, k from internal-transmittance lines); vendor catalogues are not bundled. Gates: catalogue n_d / V_d of all 46 glasses within 4e-6 / 0.005, the published Green 2008 and Johnson & Christy points, slab transmittance against the closed form, and optiland 0.6.3 as a second implementation at 23 points.

Step 2 (2026-10-14) connects the lens, mirror and scene ops to the same table: `raytrace.glass_catalog` resolves the 63 transparent materials (other makers' glasses, crystals, plastics, water) by name, `glassmirror.metal_optical_constants` / `metal_mirror_rgb` take `source="materials"` for the measured tables of 10 metals, and `optscene.scene_material` takes `metal_source="materials"`; the defaults stay on the old coarse table, so existing figures do not move. Finding: the first table picked REELS-derived data (Werner 2009) for W and Pt, giving 550 nm reflectances of 0.84 / 0.93 against 0.50 / 0.64-0.73 from other measurements; W now uses Weaver and Pt Tselin 2024, and a gate checks reflectance against an independent dataset.

## 向くところ / 向かないところ

**向く**: NIR / SWIR の透過検査の波長選び(Si の吸収端 1.1 µm、厚さとドーピングで決まる透過率)、ウェハ越し・窓越しの結像の焦点ずれと収差、鏡の材料選び(Ag / Al / Au / Rh の反射率と色)、硝子とプラスチックの分散と温度、自分の硝材カタログの取り込みと公表値との照合、観察対象の材料(Si・金属・樹脂)の反射・透過を同じ表から引く設計。

**向かない**: ★同梱の数値は**一次文献の 1 条件**(温度・結晶方位・成膜条件)です。Si の k は真性(バンド間)で、ドーピングは `silicon_free_carrier_absorption` で足します。Ge は結晶(Nunley 0.19〜2.48 µm + Burnett 2〜14 µm)、SiC は 4H の常光線(Wang、0.40〜5 µm)、膜(TiO₂ など)は成膜条件で 1〜5 % 動きます。2 つの出典が重なる所は、前の出典の範囲の最後の 3 % で線形に混ぜます(Si の 1.45 µm・Ge の 2.48 µm・水の 1.13 µm、継ぎ目の差はどれも 0.01 未満)。★初版の Ge は膜に近い表、SiC はスパッタ膜の表を継いでいて、継ぎ目で n が 0.044 / 0.66 跳んでいました(2026-10-14 に差し替え、独立の結晶の表と 0.005 以内を門に)。GaAs は 0.83〜0.97 µm に一次文献の穴があり、その波長は ValueError(外挿しない)。X 線の質量減衰係数・音響・熱伝導の列はこの回には無く、次の系列(X 線・SAM・サーモグラフィ)で足します。多層膜の干渉(保護銀・誘電体多層)は `thin_film_reflectance` 側で、この表は材料の n,k を渡すところまでです。

## 最初の 1 本

```python
import materials as M

# Si ウェハ 775 µm は何 nm から透けるか: 1.0 µm で 0.3 %、1.2 µm で 52 %(多重反射込み)
T = M.material_transmittance("SI", thickness_mm=0.775, wl_min_nm=900, wl_max_nm=1400, n_points=101)
print(T[20], T[60])                              # (λ nm, T)

# 同じ表から鏡の材料: 銀は 500 nm で 0.98、アルミは 820 nm に谷
R = M.material_reflectance("AG", 300, 1900, 161)

# 自分の硝材カタログ(.agf)を読んで、同梱の公表値と照合する
recs = M.read_glass_catalog_agf(None)            # None = 同梱の雛形、パスか os.environ["FULLSEYE_GLASS_DIR"] を渡す
print(M.abbe_number(recs[0])["nd"], M.abbe_number("N-BK7")["nd_catalog"])

# レンズも同じ表から: 他社の硝材や樹脂を面の n に名前で書く
import raytrace as RT
lens = RT.lens_system([{"R": 50.0, "t": 4.0, "n": "S-LAH58", "ap": 8}, {"R": -50.0, "t": None, "n": 1.0}])
print(RT.chromatic_shift(lens)["efl_range"])     # F 線と C 線の焦点距離の差 [mm]
```

走らせて見るなら `py -3.11 examples/poc_material_optical_library.py`(図は `FULLSEYE_FIGURE_DIR` を指定したとき)。
