---
id: dual-energy-xray-material-discrimination
title: X 線の 2 つのエネルギーで厚みと材質を分ける(デュアルエナジー / フォトンカウンティング: スペクトル → 窓 → 基底分解 → 実効 Z)
title_en: Separate thickness from material with two X-ray energies (dual-energy and photon-counting X-ray: spectrum, energy windows, basis decomposition, effective Z)
category: 見つける
ops: [material_xray_table, material_xray_attenuation, material_xray_constants, material_effective_z, xray_tube_spectrum, xray_beam_quality, photon_counting_channels, dual_kvp_channels, xray_channel_projection, basis_material_decompose, basis_decomposition_crlb, r_value_map, effective_z_map, dual_energy_separability]
examples: [poc_dual_energy_xray]
version: 0.6.1
inputs: [images]
pipeline: [xray_tube_spectrum, photon_counting_channels, basis_decomposition_crlb, basis_material_decompose, effective_z_map]
alternatives: [dual_kvp_channels, r_value_map, dual_energy_separability, xray_channel_projection, material_xray_attenuation]
limits: 散乱線・検出器の K 蛍光の逃げ・パイルアップ・画素間の電荷共有の二重計数は入っていない。X 線管のスペクトルは簡易模型(半価層は IEC の線質と 6 % 以内)。肉に埋まった異物の見かけの Z は組成だけでなく密度でも動き(PVC は 13.9 が 18.7 に見える)、無機物の向きは Al(13)から Cu(29)まで狭い角度に詰まるので、Z を 1 刻みでは読めない。
calibration: 較正の op は無い。管電圧・ろ過・検出器の材料と厚さ・窓のしきい値・エネルギー分解能・電荷共有の割合を既知として `photon_counting_channels` に入れる —— 応答を知らずに分解すると肉が Al に化ける(PoC の門)。実機では厚さの分かった 2 材料の段の撮影でチャネルの応答を合わせる。
---

# X 線の 2 つのエネルギーで厚みと材質を分ける(デュアルエナジー / フォトンカウンティング)

## できること

1 枚の X 線透過像は、各画素で L = −ln(I/I₀) = Σ μₘ tₘ という**1 つの数**しか測りません。厚い肉と薄い骨片・ガラスは同じ L を作れるので、厚みと材質は分けられません。光子のエネルギーを 2 つ以上の窓で数え分ける検出器(フォトンカウンティング)か、2 つの管電圧で撮ると、μ(E) の**形**が材質で違う(光電効果は ≈ Z³/E³、コンプトン散乱は電子密度だけ)ので、各画素で方程式が窓の数だけ立ち、2 つの基底物質の厚みに分けられます(Alvarez & Macovski 1976、Lehmann ら 1981)。

- 材料表(`materials`)に **X 線の列**があります。`material_xray_attenuation` / `material_xray_constants` は質量減衰係数 μ/ρ(E)(1 keV〜1 MeV)を、光学の列と**同じ名前**で引きます。元素 49 種と化合物 21 種(水・ICRU 44 の筋肉・脂肪・皮質骨・PE・PMMA・PVC・PTFE・ガラス・CsI・CdTe …)は NIST SRD 126(Hubbell & Seltzer)の表の部分集合そのもの、組成の分かる材料(サファイア、ソーダ石灰ガラス、天然ゴム、方解石、ステンレス、はんだ …)と化学式(`"Al2O3"`)は混合則で作ります。組成が公表されていない硝材は拒否します。`material_effective_z` は Mayneord の式の実効原子番号と電子密度です。
- `xray_tube_spectrum` は W 陽極の管のスペクトル(Kramers の厚い陽極 + 電子の深さ + 自己吸収 + K 線 + フィルタ)、`xray_beam_quality` はその半価層(空気カーマで定義)・均等度・実効エネルギーです。
- `photon_counting_channels` はエネルギーの窓(検出器の吸収効率・エネルギー分解能・電荷共有の尾つき)、`dual_kvp_channels` は 2 管電圧のエネルギー積分型です。
- `xray_channel_projection` は材料ごとの厚み図からチャネルごとの計数像を作ります(Poisson 雑音は `photoncount.photon_sample`)。
- `basis_material_decompose` は多色の順方向模型を画素ごとに Gauss–Newton で解き、基底物質の厚み図を返します。収束しない・信号 0・飛ぶ画素は NaN にして数えます(黙って値を作らない)。`basis_decomposition_crlb` はその分散の下限(Fisher 情報の逆行列)です。
- `r_value_map` は R = L_低 / L_高(単色なら材質だけで決まる指標)、`effective_z_map` は R を元素の曲線と同じ L_高 で照合した実効 Z、`dual_energy_separability` は 2 つの材料(高い窓で同じ L になる「交絡の組」も作れる)の d′ と誤り率 Φ(−d′/2) の閉形式です。

## What it does

Dual-energy and photon-counting X-ray material discrimination. The material table gains an X-ray column: mass attenuation coefficients from a bundled subset of NIST SRD 126 (Hubbell and Seltzer; 49 elements, 21 materials, 1 keV to 1 MeV) and the mixture rule for anything with a known composition, under the same names as the optical column. On top of it: a tungsten-anode tube spectrum and its half-value layer, photon-counting energy windows (absorption efficiency, energy resolution, charge-sharing tail) and dual-kVp channels, a noisy channel projection, a per-pixel polychromatic basis-material decomposition that rejects pixels it cannot solve, its Cramér-Rao bound, the R value, an effective-Z map and the closed-form separability of two materials. The PoC finds bone and glass fragments that a single X-ray image buries under the thickness variation of meat.

## 向くところ / 向かないところ

**向く**: 食品の異物検査(骨片・ガラス・金属・石を、肉や包装の厚みのむらから切り離す)、電池・電子部品の検査、リサイクルの選別、検査系の設計(窓のしきい値・管電圧・光子数を変えたときの雑音の下限と、分けられなくなる厚さの見積り)。

**向かない**: ★肉に埋まった異物は肉を押しのけるので、2 つのエネルギーで測れるのは「異物 − 同じ厚さの肉」の向きで、見かけの Z は組成だけでなく密度でも動きます(PVC は組成の Z_eff 13.9 が 18.7 に見える)。無機物の向きは Al(13)から Cu(29)まで狭い角度に詰まるので、Z を 1 刻みでは読めず、骨・ガラス・アルミは同じ仲間になります。肉より軽い有機物(PE・ゴム)は画素ごとには雑音に埋もれます。散乱線、検出器の K 蛍光の逃げ(CdTe の 23〜31 keV)、パイルアップ、画素間の電荷共有の二重計数、ヒール効果は入っていません。

## 推奨パイプライン

`xray_tube_spectrum` → `photon_counting_channels` → `basis_decomposition_crlb` → `basis_material_decompose` → `effective_z_map`

管電圧とろ過から `xray_tube_spectrum` でスペクトルを作り → `photon_counting_channels` で窓に分け(検出器の応答も入れる) → 撮る前に `basis_decomposition_crlb` で狙う厚さの雑音の下限を見積もって窓のしきい値を選び → 撮った計数像を `basis_material_decompose` で基底(肉なら赤身と Al)の厚み図に分け、Al の像で異物を見つける → 材質の当たりは `effective_z_map`(素の板)か、基底の向き(埋まった異物)で読む。

## 代替

2 管電圧の装置なら `dual_kvp_channels`。分解をせずに材質の指標だけ見るなら `r_value_map`。「この厚さの組は分けられるか」だけなら `dual_energy_separability`。撮る前に絵で確かめるなら `xray_channel_projection`。材料の μ(E) を見るだけなら `material_xray_attenuation`。

## 限界

- X 線管のスペクトルは簡易模型。強さと深さの尺度の 4 定数を SpekPy(MIT)のスペクトルの形に合わせてあり、合わせに使っていない IEC 61267 の線質 8 つ(RQR / RQA)の半価層と 5.8 % 以内(`tests/test_dualxray.py`)。
- μ/ρ の表は 1 keV〜1 MeV(外挿しない)。化合物の表に吸収端の点が無いので、端の ±15 % では混合則と表が数 % ずれる。
- 散乱線、K 蛍光の逃げ、パイルアップ、画素間の電荷共有の二重計数、ヒール効果は入っていない。
- 埋まった異物の見かけの Z は密度でも動く。無機物の Z の読みは粗い。

## 実寸校正

Fullseye に較正の op は無い。管電圧・ろ過・検出器の材料と厚さ・窓のしきい値・エネルギー分解能・電荷共有の割合を既知として `photon_counting_channels` に入れる。PoC の門のとおり、電荷共有 25 % と分解能 8 keV を知らずに分解すると、肉 1 画素あたり Al が −3.2 mm(雑音の 14 倍)も出る —— 実機では厚さの分かった 2 材料の段(例: PMMA と Al の楔)を撮ってチャネルの応答を合わせる。

## 最初の 1 本

```python
import numpy as np
import fullseye as fs

spec = fs.ledger.xray_tube_spectrum(80.0, filtration=(("AL", 2.5),))   # 80 kV、Al 2.5 mm
ch = fs.ledger.photon_counting_channels(spec, (20.0, 45.0))            # 窓 20〜45 keV と 45 keV 以上
t = np.zeros((2, 32, 32))
t[0] = 4.0                                                             # 赤身 4 cm
t[1, 10:20, 10:20] = 0.2                                               # 皮質骨 2 mm
sig = fs.ledger.xray_channel_projection(t, ["MUSCLE_ICRU44", "BONE_CORTICAL_ICRU44"], ch, 5e4, seed=1)
b = fs.ledger.basis_material_decompose(sig, ch, ("MUSCLE_ICRU44", "AL"), 5e4)   # (2, 32, 32) [cm]
print("骨の位置の Al 相当 %.3f cm、外 %.3f cm" % (b[1, 12:18, 12:18].mean(), b[1, 22:, 22:].mean()))
print(fs.ledger.material_xray_constants("CU", 8.0)["mu_rho_cm2_g"])     # 52.55(NIST)
```

走らせて見るなら `py -3.11 examples/poc_dual_energy_xray.py`(図は `FULLSEYE_FIGURE_DIR` か既定の `out/figures/<PoC 名>/`)。

## 裏づけ

- op: `material_xray_table` / `material_xray_attenuation` / `material_xray_constants` / `material_effective_z` / `xray_tube_spectrum` / `xray_beam_quality` / `photon_counting_channels` / `dual_kvp_channels` / `xray_channel_projection` / `basis_material_decompose` / `basis_decomposition_crlb` / `r_value_map` / `effective_z_map` / `dual_energy_separability`
- 門: `tests/test_dualxray.py`(NIST の公表値 11 点と K 端、元素の表 × 組成の混合則と NIST の化合物の表、水の Z_eff 7.42、Kramers の閉形式、IEC 61267 の線質 8 つ、雑音なしの分解の回収 1e-14、CRLB と分解の雑音、誤り率の閉形式とモンテカルロ、fail-closed 10 本、xraylib と SpekPy があれば第 2 実装と照合)と PoC の 21 門。
- 出典: Alvarez & Macovski, Phys. Med. Biol. 21, 733 (1976) / Lehmann ら, Med. Phys. 8, 659 (1981) / Roessl & Herrmann, Phys. Med. Biol. 54, 1307 (2009) / Hubbell & Seltzer, NIST SRD 126 (2004) / ICRU Report 44 (1989) / Kanaya & Okayama, J. Phys. D 5, 43 (1972) / X-ray Data Booklet (LBNL 2009) / Poludniowski ら(SpekPy), Med. Phys. 48, 3630 (2021) / IEC 61267:2005 の値は Tanguay & Persson, arXiv:2205.03362 表 I。
