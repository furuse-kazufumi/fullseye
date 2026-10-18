---
op: photon_counting_channels
dim: tomography
category: spectral_xray
in: pairs
out: table
examples: [poc_dual_energy_xray]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# photon_counting_channels — TOMOGRAPHY `spectral_xray` op

- **データ種**: `pairs` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.photon_counting_channels(spectrum, thresholds_kev=(20.0, 50.0), detector: 'str' = 'CDTE', detector_mm: 'float' = 2.0, energy_resolution_fwhm_kev: 'float' = 0.0, charge_sharing: 'float' = 0.0, upper_kev=None) -> 'dict'` (実装を直接呼ぶなら `import dualxray; dualxray.photon_counting_channels(spectrum, thresholds_kev=(20.0, 50.0), detector: 'str' = 'CDTE', detector_mm: 'float' = 2.0, energy_resolution_fwhm_kev: 'float' = 0.0, charge_sharing: 'float' = 0.0, upper_kev=None) -> 'dict'`、台帳から引くなら `opstomography.get("photon_counting_channels")`)

## 使い方

フォトンカウンティング検出器のエネルギーの窓 → チャネル(1 光子 1 カウント)。

``thresholds_kev`` = (T₁, T₂, …): チャネル c は堆積エネルギーが [T_c, T_{c+1}) の光子を数える
(最後の窓の上限は ``upper_kev``、既定は無限大)。検出器の応答:
  * 吸収効率 1 − e^{−μ d}(``detector`` の X 線の列、既定 CdTe 2 mm)。
  * エネルギー分解能: 堆積エネルギーに FWHM ``energy_resolution_fwhm_kev`` のガウスのぼけ。
  * 電荷共有: 割合 ``charge_sharing`` の光子は電荷の一部しか集まらず、堆積エネルギーが
    [0, E] に一様に散らばる(低いエネルギーへの尾。1 画素の中の模型で、隣の画素への二重計数は
    入れない)。
返り値: dict(energy_kev, weights (C, K) = 入射光子 1 個がチャネル c に数えられる確率 × スペクトル
のビンの重み, gain = 1(計数), mode = "counting", labels, thresholds_kev, response)。
窓が 1 つも光子を拾わないときは ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dual_energy_xray](../../../../examples/poc_dual_energy_xray.py) — `py -3.11 examples/poc_dual_energy_xray.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`spectral_xray`)

[material_xray_table](material_xray_table.md) · [material_xray_attenuation](material_xray_attenuation.md) · [material_xray_constants](material_xray_constants.md) · [material_effective_z](material_effective_z.md) · [xray_tube_spectrum](xray_tube_spectrum.md) · [xray_beam_quality](xray_beam_quality.md) · [dual_kvp_channels](dual_kvp_channels.md) · [xray_channel_projection](xray_channel_projection.md)

---
*Provenance: dualxray.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
