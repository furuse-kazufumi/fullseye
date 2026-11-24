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
- **呼び出し**: `import fullseye as fs; fs.ledger.particle_size_distribution(particles, calibration, *, border_policy='exclude', measurement_date=None, bin_edges=None, confidence=0.95, bootstrap_samples=2000, seed=776, upstream_records=None)` (実装を直接呼ぶなら `import pharmaparticle; pharmaparticle.particle_size_distribution(particles, calibration, *, border_policy='exclude', measurement_date=None, bin_edges=None, confidence=0.95, bootstrap_samples=2000, seed=776, upstream_records=None)`、台帳から引くなら `opsdrive.get("particle_size_distribution")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

粒子表を校正し、採否理由、3 基準のビン、D10/D50/D90 と信頼区間、来歴を返す。

D10/D50/D90 は、重複径を重みごとに集約した**重み付き経験分布の中点規約**で求める。
``unsplit`` と ``ambiguous`` の重なりは常に除外し、1 粒として黙って数えない。
上流の ``blob_split`` と ``blob_count_interval`` に由来する成分 ID、分割根拠、
来歴ハッシュ、上流の構造化 ``blob_split`` / ``blob_count_interval`` 記録、個数区間、
決定可否が必須であり、op 内で再計算したダイジェストと一致しない入力は拒否する。
``component_id`` と上流 label は一対一、各行の一意な split label、面積、面積相当径は
実際の ``blob_split`` 画像から再計算して照合する。これは同一実行内の整合性検査であり、署名または不変の外部
成果物が無いので改ざん検知ではない。改ざん検知は実行記録と署名を備えた規制対応基盤で扱う。
未決定行は ``ambiguous`` として除外する。
``border_policy="correct"`` は端粒子について ``border_inclusion_probability``、
``border_corrected_diameter_px``、``border_corrected_area_px2`` が揃う場合だけ
Horvitz--Thompson の個数重み ``1/p`` と補正寸法を使う。尺度の標準不確かさは
各径へ線形伝播し、分位点では決定的 bootstrap、尺度、端補正不確かさの
感度再標本化を保守的に合成する。端補正の径・面積・包含確率は独立と明示した周辺正規
不確かさとして扱うため、相関を持つ校正には使えない。物理範囲外の抽出値は切り詰めず
再抽出する。
有効粒子数が ``MIN_EFFECTIVE_PARTICLES`` 未満なら、母集団分位点を主張せず
``insufficient_sample`` を返す。bootstrap 区間は独立粒子の経験分布を再標本化する
**分割後に受理された粒子に条件付けた区間**であり、端補正時は設計ベース保証ではなく
実験的な不確かさである。

Parameters
----------
particles : table (dict of 1-D columns)
    必須列は ``object_id``、``diameter_px``、``area_px2``、``diameter_unit="px"``、
    ``area_unit="px2"``、``touches_border``、``split_status``、``component_id``、
    ``split_evidence``、``upstream_provenance_hash``、``upstream_component_label``、``upstream_split_label``、``count_interval_lo``、
    ``count_interval_hi``、``count_determined``。来歴ハッシュは元の ``blob_split`` と
    ``blob_count_interval`` の構造化記録を正規化して SHA-256 化したもの。
    状態は ``isolated`` / ``split`` / ``unsplit`` / ``ambiguous``。
    ``major_axis_px`` と ``minor_axis_px`` は任意。
calibration : table (one-row dict)
    ``scale`` = {``value``, ``unit="mm/px"``, ``standard_uncertainty``} と
    ``calibrator_id``、``calibrated_at``、``valid_until``。``pixel_to_world`` と同じ
    mm/px 契約だけを許す。
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
upstream_records : dict
    ``{"blob_split": blob_split出力, "blob_count_interval": blob_count_interval出力}``。
    各行の ``upstream_component_label`` と個数記録、一意な ``upstream_split_label``、
    面積、面積相当径を実際の split 画像と照合し、op がダイジェストを再計算する。
    面積は画素数の丸め幅 0.5 px2、径はその面積幅から導かれる範囲だけを許す。
    これは改ざん検知ではない。

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
>>> p = {"object_id": ["p%d" % i for i in range(30)], "diameter_px": [10.] * 30, "area_px2": [78.5] * 30,
...      "diameter_unit": "px", "area_unit": "px2", "touches_border": [False] * 30,
...      "split_status": ["isolated"] * 30, "component_id": ["c%d" % i for i in range(30)],
...      "split_evidence": ["blob_split + blob_count_interval"] * 30,
...      "upstream_provenance_hash": ["0" * 64] * 30, "upstream_split_label": list(range(1, 31)),
...      "count_interval_lo": [1] * 30,
...      "count_interval_hi": [1] * 30, "count_determined": [True] * 30}
>>> c = {"scale": {"value": .002, "unit": "mm/px", "standard_uncertainty": .00002},
...      "calibrator_id": "SM-01", "calibrated_at": "2026-01-01", "valid_until": "2026-12-31"}
>>> u = {"blob_split": np.repeat(np.arange(1, 31), 79).reshape(1, -1),
...      "blob_count_interval": {"components": {"label": np.arange(1, 31), "lo": np.ones(30, int),
...      "hi": np.ones(30, int), "status": np.array(["determined"] * 30)}}}
>>> p["upstream_component_label"] = list(range(1, 31)); p["upstream_provenance_hash"] = [_upstream_provenance_digest(u)] * 30
>>> r = particle_size_distribution(p, c, measurement_date="2026-06-01", bootstrap_samples=200, upstream_records=u)
>>> r["counts"]["accepted_observed"], r["particle_rows"][0]["diameter"]
(30, 0.02)

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
