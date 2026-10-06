---
op: normal_error_map
dim: drive
category: tacscalib
in: normalmap × normalmap
out: image2d
examples: [poc_tacscalib_sphere_lut]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# normal_error_map — DRIVE `tacscalib` op

- **データ種**: `normalmap × normalmap` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.normal_error_map(n_a, n_b) -> 'np.ndarray'` (実装を直接呼ぶなら `import tacscalib; tacscalib.normal_error_map(n_a, n_b) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("normal_error_map")`)

## 使い方

2 つの法線場の画素ごとの角度 [度] = atan2(|a × b|, a · b)(正規化しない —— 長さは atan2 の比で消える)。
acos(a · b) は単位ベクトルの近くで丸めの床を持つ(1e-7° を 1e-4° と答える)ので使わない。
**Raises** ``ValueError``: 形が違う / 最後の軸が 3 でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacscalib_sphere_lut](../../../../examples/poc_tacscalib_sphere_lut.py) — `py -3.11 examples/poc_tacscalib_sphere_lut.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [ttc_from_flow](../ttc/ttc_from_flow.md) · [foe_from_flow](../ttc/foe_from_flow.md) · [perlin2](../terrain/perlin2.md) · [fbm_height](../terrain/fbm_height.md) · [fbm_gradient](../terrain/fbm_gradient.md) · [radial_periodogram](../terrain/radial_periodogram.md)

## 同カテゴリ(`tacscalib`)

[calib_pack_load](calib_pack_load.md) · [sphere_normals_known](sphere_normals_known.md) · [lights_fit_from_sphere](lights_fit_from_sphere.md) · [membrane_predict_rgb](membrane_predict_rgb.md) · [gradient_lut_build](gradient_lut_build.md) · [gradient_lut_invert](gradient_lut_invert.md) · [sphere_cap_height](sphere_cap_height.md) · [field_position_sweep](field_position_sweep.md)

---
*Provenance: tacscalib.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
