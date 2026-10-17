---
op: xray_tube_spectrum
dim: tomography
category: spectral_xray
in: 
out: pairs
examples: [poc_dual_energy_xray]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# xray_tube_spectrum — TOMOGRAPHY `spectral_xray` op

- **データ種**: `なし` → `pairs`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.xray_tube_spectrum(kvp: 'float' = 80.0, anode: 'str' = 'W', takeoff_deg: 'float' = 12.0, filtration=(('AL', 2.5),), e_min_kev: 'float' = 5.0, de_kev: 'float' = 0.5, characteristic: 'bool' = True, self_absorption: 'bool' = True) -> 'np.ndarray'` (実装を直接呼ぶなら `import dualxray; dualxray.xray_tube_spectrum(kvp: 'float' = 80.0, anode: 'str' = 'W', takeoff_deg: 'float' = 12.0, filtration=(('AL', 2.5),), e_min_kev: 'float' = 5.0, de_kev: 'float' = 0.5, characteristic: 'bool' = True, self_absorption: 'bool' = True) -> 'np.ndarray'`、台帳から引くなら `opstomography.get("xray_tube_spectrum")`)

## 使い方

X 線管の光子スペクトルを ``pairs``(E [keV], 光子数 / keV)で返す(Σ φ ΔE = 1 に正規化)。

模型(厚い陽極):
  * 制動放射は Kramers の薄い標的の断面積 ∝ 1/(T·E) を、電子が T = E₀ から E まで減速する
    あいだ積分する。減速は到達深さ x(T) = R(E₀) − R(T)(Kanaya–Okayama の R ∝ T^1.67)で表す。
    自己吸収が無ければ積分は Kramers の式 φ(E) ∝ (E₀ − E)/E そのものになる(門で確かめる)。
  * 陽極の自己吸収: 深さ x で生まれた光子は取り出し角 θ の方向へ x/sin θ だけ陽極の中を通る
    (μ は materials の X 線の列から W を引く)。
  * 特性線(管電圧が K 端より高いとき): Kα₂ / Kα₁ / Kβ₁ / Kβ₂(X-ray Data Booklet の
    エネルギーと相対強度)、総数は (U − 1)^1.63(U = E₀/E_K)に比例。各線は 1 つのビンに入る。
  * フィルタ: ``filtration`` = ((材料, 厚さ mm), …)。既定の Al 2.5 mm は管の固有ろ過の代表値。

``kvp`` は 15〜300 kV、``de_kev`` はビン幅(0.05〜5 keV)。返り値の E はビンの中心。
特性線の強さは簡易模型(``K_SCALE``)で、実測のスペクトルとは数 % ずれる。線質の門は
``xray_beam_quality`` の半価層を公表の線質と比べる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dual_energy_xray](../../../../examples/poc_dual_energy_xray.py) — `py -3.11 examples/poc_dual_energy_xray.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[xray_beam_quality](xray_beam_quality.md) · [photon_counting_channels](photon_counting_channels.md) · [dual_kvp_channels](dual_kvp_channels.md)

## 同カテゴリ(`spectral_xray`)

[material_xray_table](material_xray_table.md) · [material_xray_attenuation](material_xray_attenuation.md) · [material_xray_constants](material_xray_constants.md) · [material_effective_z](material_effective_z.md) · [xray_beam_quality](xray_beam_quality.md) · [photon_counting_channels](photon_counting_channels.md) · [dual_kvp_channels](dual_kvp_channels.md) · [xray_channel_projection](xray_channel_projection.md)

---
*Provenance: dualxray.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
