---
op: scintillator_sensor_qe
dim: tomography
category: spectral_xray
in: 
out: table
examples: [scintillator_sensor_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# scintillator_sensor_qe — TOMOGRAPHY `spectral_xray` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.scintillator_sensor_qe(scintillator='CSI:TL', thickness_mm: 'float' = 0.6, e_min_kev: 'float' = 10.0, e_max_kev: 'float' = 150.0, n_points: 'int' = 141, photodetector_qe=None, emission_spectrum=None, light_yield_per_mev=None, light_collection: 'float' = 1.0, emission_geometry=None) -> 'dict'` (実装を直接呼ぶなら `import dualxray; dualxray.scintillator_sensor_qe(scintillator='CSI:TL', thickness_mm: 'float' = 0.6, e_min_kev: 'float' = 10.0, e_max_kev: 'float' = 150.0, n_points: 'int' = 141, photodetector_qe=None, emission_spectrum=None, light_yield_per_mev=None, light_collection: 'float' = 1.0, emission_geometry=None) -> 'dict'`、台帳から引くなら `opstomography.get("scintillator_sensor_qe")`)

## 使い方

シンチレータ積層のセンサの量子効率: X 線 1 個 → シンチレータの吸収 → 発光 → 光検出器の電子の数。

エネルギー E の X 線 1 個あたり:

  * 吸収効率 A(E) = 1 − exp(−μ(E) t)。μ は ``scintillator`` のレコードの X 線の列(NIST SRD 126)と密度、
    t = ``thickness_mm``。:func:`dual_kvp_channels` と同じ関数で計算する(CSI:TL は既定の ``CSI`` と同じ値)。
  * 光子の数 N(E) = A(E) · Y · E · η_c。Y = 光収率(単位 photons/MeV。材料表の値で、``light_yield_per_mev``
    で上書き)、E は MeV、η_c = ``light_collection``(光が光検出器に届く割合、既定 1 = 全部届く理想)。
    吸収した X 線はエネルギーを全部置いていくとみなす(入れないものは下に並べる)。
  * 重なり Q̄ = ∫ S(λ) QE(λ) dλ(S は ∫ S dλ = 1 に正規化した発光スペクトル)。電子の数 = N(E) · Q̄。

光収率の物理上限(エネルギー保存): 光の光子のエネルギーの和は吸収したエネルギーを超えないので、
Y · ⟨E_ph⟩ ≤ 10⁶ eV/MeV を満たさない Y は ValueError(上書きの値も表の値も同じ門を通る)。⟨E_ph⟩ は
**使う発光スペクトルの光子のエネルギーの平均**(重心。ピークの波長ではない): ``emission_spectrum`` なら
∫ S(λ) hc/λ dλ、材料表の成分なら Σ wᵢ hc/λᵢ(エネルギー軸のガウスの平均は中心)、極大の線なら hc/λ_peak。
BGO(480 nm、2.58 eV)の上限は約 387,000 photons/MeV。禁制帯幅 E_g からのもっときつい上限
Y ≤ 10⁶/(β E_g)(β ≈ 2.35〜2.5)は、材料表に E_g が無いので置いていない。

入れないもの:

  * K 蛍光の逃げとコンプトンの逃げ(吸収した X 線はエネルギーを全部置いていくとみなす)。重い元素の K 端の
    すぐ上では、逃げる K X 線が持ち出すエネルギーが大きいので、高 Z の材料ほど電子の数を大きく見積もる。
  * 光収率のエネルギー非比例性(材料表の光収率は γ 線、多くは 662 keV 前後で測った値で、それを
    10〜150 keV に一律に掛けている)。

光収率の幅: 材料表に幅(文献の絶対値のばらつき。CdWO4 は 20,000〜28,000、LYSO は 26,000〜27,000)が
あれば、両端で数えた電子の数も返す(``electrons_light_yield_range``、1 行目が下限・2 行目が上限)。電子の数は
光収率に比例するので、両端の電子の数は中央の値の Y_lo/Y 倍と Y_hi/Y 倍。``light_yield_per_mev`` で
上書きしたとき・表に幅が無いときは ``None``。

発光スペクトル S: ``emission_spectrum`` に (λ nm, 相対強度) の pairs を渡せばそれを正規化して使う。
渡さなければ材料表の**発光の成分の並び**から作る —— 1 成分 = 中心・FWHM [eV]・重み。ガウスは**エネルギー軸**
で作り、波長軸へはヤコビアン hc/λ² を掛けて移す(Q̄ = Σ wᵢ ∫ gᵢ(λ) QE(λ) dλ)。FWHM の無い成分は線で、
GD2O2S:TB の Tb³⁺ の線の束は Q̄ = Σ wᵢ·QE(λᵢ)。幅は全部、一次文献の図から読み取った値(室温の X 線・γ 線
励起で FWHM を数値で書いた一次文献は見つからなかった)で、成分ごとに出典と ``digitized_from_figure`` の印を
返す。成分の中心は**エネルギー軸の**中心なので、波長軸の山はヤコビアンの分だけ短波長に出る(BGO: 中心
480 nm・FWHM 0.70 eV で山 468 nm)。公表の「極大」が波長軸の値だとすると中心はやや長波長で、Q̄ の差は
1.4 % 以内(BGO −0.8 %、LSO +1.4 %)。幅の分からない材料(CSI:TL・NAI:TL)は**発光の極大の 1 本の線**
(Q̄ = QE(λ_peak))。
``emission_model`` がどれを使ったかを言う。QE が上に凸の山の上では、線は帯より大きく出る(BGO で +6.6 %)。

``emission_geometry`` は表の成分の測定配置: ``"surface"``(励起した面から出る光)か
``"thick_crystal_transmission"``(厚い結晶の中を通って出てくる光。LSO は Ce³⁺ の自己吸収で極大が
402 → 453 nm に動く)。``None`` は表の既定(表面の成分があれば表面、無ければ表にある唯一の配置)。
表にその配置が無い材料・成分の無い材料・``emission_spectrum`` と同時に渡すと ValueError。

``photodetector_qe`` は (λ nm, QE) の pairs で、既定は ``spectralrad.silicon_photodiode_qe()``
(Si フォトダイオード、集める深さ 3 µm、反射防止膜なし)。
発光が QE の波長範囲の外にはみ出すと ValueError(外の光を 0 と数えて重なりを小さく出さない)。

返り値: dict(scintillator, thickness_mm, energy_kev, absorption_efficiency, light_photons, electrons,
overlap = Q̄, light_yield_photons_per_mev, light_yield_range_photons_per_mev, electrons_light_yield_range,
light_collection, emission_model, emission(帯の部分の正規化した pairs、線だけなら None),
emission_components(成分ごとの中心・幅・重み・qe_overlap・出典、表を使わなければ None), emission_geometry,
emission_peak_nm, photodetector, decay_time_ns, sources(使った値の出典), unverified, notes(材料表の注記 ——
値はあるが使い方に条件が付くもの。GD2O2S:TB の密度は塊の値で、粉末のスクリーンでは充填率の分だけ下がる))。
光収率の無い材料(GD2O2S:TB)で ``light_yield_per_mev`` を渡さなければ ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [scintillator_sensor_tour](../../../../examples/scintillator_sensor_tour.py) — `py -3.11 examples/scintillator_sensor_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`spectral_xray`)

[material_xray_table](material_xray_table.md) · [material_xray_attenuation](material_xray_attenuation.md) · [material_xray_constants](material_xray_constants.md) · [material_effective_z](material_effective_z.md) · [xray_tube_spectrum](xray_tube_spectrum.md) · [xray_beam_quality](xray_beam_quality.md) · [photon_counting_channels](photon_counting_channels.md) · [dual_kvp_channels](dual_kvp_channels.md)

---
*Provenance: dualxray.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
