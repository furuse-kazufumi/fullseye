---
op: r_value_map
dim: tomography
category: spectral_xray
in: images
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# r_value_map — TOMOGRAPHY `spectral_xray` op

- **データ種**: `images` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.r_value_map(signal, channels=None, photons_per_pixel: 'float' = 100000.0, low: 'int' = 0, high: 'int' = -1, flat=None, min_log: 'float' = 0.02) -> 'np.ndarray'` (実装を直接呼ぶなら `import dualxray; dualxray.r_value_map(signal, channels=None, photons_per_pixel: 'float' = 100000.0, low: 'int' = 0, high: 'int' = -1, flat=None, min_log: 'float' = 0.02) -> 'np.ndarray'`、台帳から引くなら `opstomography.get("r_value_map")`)

## 使い方

R = L_low / L_high(低エネルギーと高エネルギーの対数減衰の比)の像を返す。

単色なら R = μ(E_low)/μ(E_high) で**厚みに依らず材質だけで決まる**(Z が大きいほど光電効果で
低エネルギーの μ が大きく、R が大きい)。多色ではビーム硬化で厚みとともに少し動く —— その動き
が「厚い軽元素と薄い重元素」の交絡の源。L_high < ``min_log`` の画素(ほぼ素通しで比が雑音だけ
になる)と信号が 0 以下の画素は NaN(拒否)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image2d` を入力に取れる)

[radon_transform](../forward/radon_transform.md)

## 同カテゴリ(`spectral_xray`)

[material_xray_table](material_xray_table.md) · [material_xray_attenuation](material_xray_attenuation.md) · [material_xray_constants](material_xray_constants.md) · [material_effective_z](material_effective_z.md) · [xray_tube_spectrum](xray_tube_spectrum.md) · [xray_beam_quality](xray_beam_quality.md) · [photon_counting_channels](photon_counting_channels.md) · [dual_kvp_channels](dual_kvp_channels.md)

---
*Provenance: dualxray.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
