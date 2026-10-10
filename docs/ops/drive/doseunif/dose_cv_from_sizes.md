---
op: dose_cv_from_sizes
dim: drive
category: doseunif
in: any × scalar × scalar
out: table
examples: [poc_dose_uniformity_from_grinding]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# dose_cv_from_sizes — DRIVE `doseunif` op

- **データ種**: `any × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.dose_cv_from_sizes(sizes, dose_mg: 'float', density: 'float', estimator: 'str | None' = None, frame=None, ci: 'float' = 0.9, n_boot: 'int' = 400, seed: 'int' = 0) -> 'dict'` (実装を直接呼ぶなら `import doseunif; doseunif.dose_cv_from_sizes(sizes, dose_mg: 'float', density: 'float', estimator: 'str | None' = None, frame=None, ci: 'float' = 0.9, n_boot: 'int' = 400, seed: 'int' = 0) -> 'dict'`、台帳から引くなら `opsdrive.get("dose_cv_from_sizes")`)

## 使い方

測った粒径から 1 回分の含量の CV(粒の数の揺らぎだけ、Poisson)と、その偏りと区間。

``sizes`` は 2 通り:

- **1-D の配列** = 個数基準の粒の直径の標本 [µm] (:func:`grind.particle_image_d50` の ``diameters`` など)。``estimator``:
  ``"lognormal"``(既定 —— ln d の平均と分散から ``D63 = exp(m + 4.5 v)``)/ ``"moment"``(``D63³ = Σd⁶/Σd³`` をそのまま。
  平均は偏らないが少数の大粒に支配され、中央値は低く出る)。``frame = (H_px, W_px, pitch_um)`` を渡すと、縁に触れる粒を捨てた
  測定(``particle_image_d50`` の ``border="exclude"``: 外周の画素に掛かった粒を捨てる)の大粒の取りこぼしを Miles–Lantuéjoul の重み
  ``1 / (((H−2)p − d)((W−2)p − d))`` で直す(省くと平均で −5 % 程度低い、モジュール冒頭)。区間は ``ci``(両側)の百分位 bootstrap
  (``n_boot`` 回、両方の推定量)と、対数正規のデルタ法(Kish の有効数 n_eff、``Var ln CV = (9v/n_eff + 364.5 v²/(n_eff − 1))/4``)。
- **dict(``edges``・``volume``)** = レーザー回折の体積基準の表(:func:`grind.particle_size_read` / :func:`grind.particle_size_synth`)。
  ``estimator``: ``"histogram"``(既定 —— 恒等式 ``D63³ = E_v[d³]`` を区間ごとに「ln d について一様」の積分で、**分布の形を仮定しない**)/
  ``"lognormal"``(``σ = ln(D84/D16)/2``、``D63 = D50 exp(1.5σ²)``)。表に粒の数は無いので標本の区間は出さない(``ci_bootstrap`` は None)。
  ``coarse_share`` = E_v[d³] のうち D90 より上の区間が占める割合(粗い裾への依存の度合い)。

返り: ``cv``(選んだ推定量)、``d63``、推定量ごとの ``cv_*``・``d63_*``、``sigma_ln``、``d_number_median``(標本)/ ``d50_volume``(表)、
``particles_per_dose``、``n``・``n_eff``、``top1pct_share_d6``(標本: 最大 1 % の粒が Σd⁶ に占める割合)、``ci_bootstrap``・``ci_delta``、
``estimator``・``source``(``"sample"`` / ``"psd"``)・``edge_corrected``。
**Raises** ValueError: 粒が 10 未満・非有限・非正、表が壊れている(:func:`grind.particle_size_dx` と同じ検査)、frame に収まらない粒、綴り違い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dose_uniformity_from_grinding](../../../../examples/poc_dose_uniformity_from_grinding.py) — `py -3.11 examples/poc_dose_uniformity_from_grinding.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`doseunif`)

[dose_cv_lognormal](dose_cv_lognormal.md) · [grind_time_for_dose_cv](grind_time_for_dose_cv.md)

---
*Provenance: doseunif.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
