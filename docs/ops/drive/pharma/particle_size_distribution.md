---
op: particle_size_distribution
dim: drive
category: pharma
in: table × table
out: table
gpu: なし
examples: [poc_compendial_particle_microscopy]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# particle_size_distribution — DRIVE `pharma` op

- **データ種**: `table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.particle_size_distribution(particles, calibration, *, border_policy='exclude', measurement_date=None, bin_edges=None, confidence=0.95, bootstrap_samples=2000, seed=776)` (実装を直接呼ぶなら `import pharmaparticle; pharmaparticle.particle_size_distribution(particles, calibration, *, border_policy='exclude', measurement_date=None, bin_edges=None, confidence=0.95, bootstrap_samples=2000, seed=776)`、台帳から引くなら `opsdrive.get("particle_size_distribution")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

粒子表を校正し、採否理由、3 基準のビン、D10/D50/D90 と信頼区間、来歴を返す。

``unsplit`` と ``ambiguous`` の重なりは常に除外し、1 粒として黙って数えない。
``border_policy="correct"`` は端粒子について ``border_inclusion_probability``、
``border_corrected_diameter_px``、``border_corrected_area_px2`` が揃う場合だけ
Horvitz--Thompson の個数重み ``1/p`` と補正寸法を使う。尺度の標準不確かさは
各径へ線形伝播し、分位点では決定的 bootstrap の標本区間と尺度区間を合成する。

Parameters
----------
particles : table (dict of 1-D columns)
    必須列は ``object_id``、``diameter_px``、``area_px2``、``touches_border``、
    ``split_status``。状態は ``isolated`` / ``split`` / ``unsplit`` / ``ambiguous``。
    ``major_axis_px`` と ``minor_axis_px`` は任意。
calibration : table (one-row dict)
    ``scale_per_px``、``unit``(``nm/px`` / ``um/px`` / ``µm/px`` / ``mm/px``)、
    ``uncertainty_per_px``、``calibrator_id``、``calibrated_at``、``valid_until``。
border_policy : {"include", "exclude", "correct"}
    端粒子を切れた測定のまま含める、除外する、必要情報を使って補正する方針。
measurement_date : str
    測定日 ``YYYY-MM-DD``。省略不可。校正日より前、期限後なら拒否する。
bin_edges : sequence or None
    物理径のビン端。None なら採用径の範囲に固定した対数 12 ビン。
confidence : float
    両側信頼水準。
bootstrap_samples : int
    決定的 bootstrap の反復数。200 以上。
seed : int
    bootstrap の乱数種。

Returns
-------
table
    ``particle_rows``、``counts``、``bins``(number / area / volume)、``quantiles``、
    ``calibration_provenance``、``accepted_proportion_ci`` を持つ。

Raises
------
ValueError
    空表、列不整合、非有限・非正、補正情報不足、校正期間外、採用粒子ゼロを拒否する。

English: combine microscopy particles and a calibration record into an auditable report.
Unresolved overlaps are excluded; border correction is refused without inclusion probability
and corrected dimensions. Number, area and volume bases remain distinct and are not treated
as an interchangeable laser-diffraction result.

Examples
--------
>>> p = {"object_id": ["a", "b"], "diameter_px": [10., 20.], "area_px2": [78.5, 314.],
...      "touches_border": [False, False], "split_status": ["isolated", "split"]}
>>> c = {"scale_per_px": 2., "unit": "um/px", "uncertainty_per_px": .02,
...      "calibrator_id": "SM-01", "calibrated_at": "2026-01-01", "valid_until": "2026-12-31"}
>>> r = particle_size_distribution(p, c, measurement_date="2026-06-01", bootstrap_samples=200)
>>> r["counts"]["accepted_observed"], r["particle_rows"][0]["diameter"]
(2, 20.0)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_compendial_particle_microscopy](../../../../examples/poc_compendial_particle_microscopy.py) — `py -3.11 examples/poc_compendial_particle_microscopy.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pharma`)

—

---
*Provenance: pharmaparticle.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
