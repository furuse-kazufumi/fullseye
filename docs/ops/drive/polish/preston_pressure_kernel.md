---
op: preston_pressure_kernel
dim: drive
category: polish
in: scalar × scalar × scalar
out: image2d
examples: [poc_polish_wipe_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# preston_pressure_kernel — DRIVE `polish` op

- **データ種**: `scalar × scalar × scalar` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.preston_pressure_kernel(force: 'float', radius: 'float', res: 'float', kind: 'str' = 'flat', estar=None, normalize: 'bool' = False) -> 'np.ndarray'` (実装を直接呼ぶなら `import polish; polish.preston_pressure_kernel(force: 'float', radius: 'float', res: 'float', kind: 'str' = 'flat', estar=None, normalize: 'bool' = False) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("preston_pressure_kernel")`)

## 使い方

工具の下の圧力 [Pa] を画素中心で標本化した窓(奇数 × 奇数、中心の画素が工具の中心)。平板は円の内側で一様 F/(πa²)、
Hertz は p0 √(1 − r²/a²)(``radius`` = 球の半径 R、``estar`` が要る)。``normalize=True`` なら Σ p · res² = F に合わせる
(画素で数えた円の面積の誤差を消す。FFT の畳み込みで体積を保つため)。
**Raises** ValueError: 力・半径・画素が正でない、kind が不明、Hertz で estar が無い、接触半径が 1 画素より小さい。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_polish_wipe_measure](../../../../examples/poc_polish_wipe_measure.py) — `py -3.11 examples/poc_polish_wipe_measure.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [ttc_from_flow](../ttc/ttc_from_flow.md) · [foe_from_flow](../ttc/foe_from_flow.md) · [perlin2](../terrain/perlin2.md) · [fbm_height](../terrain/fbm_height.md) · [fbm_gradient](../terrain/fbm_gradient.md) · [radial_periodogram](../terrain/radial_periodogram.md)

## 同カテゴリ(`polish`)

[preston_removal_map](preston_removal_map.md) · [preston_track_profile](preston_track_profile.md) · [wipe_band_width](wipe_band_width.md) · [raster_wipe_area](raster_wipe_area.md) · [coat_image](coat_image.md) · [coat_thickness_from_image](coat_thickness_from_image.md) · [wipe_coverage](wipe_coverage.md) · [band_width_profile](band_width_profile.md)

---
*Provenance: polish.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
