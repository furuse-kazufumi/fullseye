---
op: effective_z_map
dim: tomography
category: spectral_xray
in: images
out: image2d
gpu: なし
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# effective_z_map — TOMOGRAPHY `spectral_xray` op

- **データ種**: `images` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.effective_z_map(signal, channels=None, photons_per_pixel: 'float' = 100000.0, low: 'int' = 0, high: 'int' = -1, flat=None, min_log: 'float' = 0.05) -> 'np.ndarray'` (実装を直接呼ぶなら `import dualxray; dualxray.effective_z_map(signal, channels=None, photons_per_pixel: 'float' = 100000.0, low: 'int' = 0, high: 'int' = -1, flat=None, min_log: 'float' = 0.05) -> 'np.ndarray'`、台帳から引くなら `opstomography.get("effective_z_map")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

デュアルエナジーの像から実効原子番号の像を推定する(R を元素の曲線と照合)。

各元素 Z(:data:`EFFECTIVE_Z_REFERENCES`、H〜Fe)について、同じチャネルで質量厚さを振った
(L_high, R) の曲線を作り、画素の L_high での R_Z を読む。画素の R を挟む 2 つの元素の間を
Z について線形に補間した値が実効 Z。厚みの効果(ビーム硬化)は「同じ L_high で比べる」ことで
打ち消す —— 厚い軽元素と薄い重元素が同じ L_high でも R で分かれる。

**拒否**: L_high < ``min_log``、R が H より小さいか Fe より大きい(範囲の外 —— Fe より重い元素は R が
ほとんど同じで Z を区別できず、さらに重い金属は K 端がスペクトルの中にあって R が単調でない)画素は NaN。照合の曲線が Z について単調で
ない(窓の選び方で K 端が入る)ときは ValueError。

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
