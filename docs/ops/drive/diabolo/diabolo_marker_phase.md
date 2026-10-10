---
op: diabolo_marker_phase
dim: drive
category: diabolo
in: rgb × table × table × table
out: table
examples: [poc_diabolo_model_and_vision]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# diabolo_marker_phase — DRIVE `diabolo` op

- **データ種**: `rgb × table × table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.diabolo_marker_phase(img, cam: 'dict', params: 'dict', pose: 'dict', *, nbins: 'int' = 720, widths=None) -> 'dict'` (実装を直接呼ぶなら `import diabolo; diabolo.diabolo_marker_phase(img, cam: 'dict', params: 'dict', pose: 'dict', *, nbins: 'int' = 720, widths=None) -> 'dict'`、台帳から引くなら `opsdrive.get("diabolo_marker_phase")`)

## 使い方

1 コマのマーカーから回転の位相 ψ(体の系 e1 から、右ねじ)と回転ぶれの弧の幅 |ω|·露光 [rad] を読む。

``pose`` は :func:`diabolo_axis_from_image` の返り(軸・中心・分割)。マーカーの画素を推定した姿勢でマーカーの円の面へ戻し、
方位角の度数(白さで重みづけ)を作る → 弧の幅ごとの型紙(反射 3 か所 + 灰のダミー 5 か所、非対称なので向きが一意)と円周
相互相関(FFT)で最大を取り、位相は放物線で副標本。返り ``{"phase", "smear", "score", "profile"}``。
**Raises** ``ValueError``: 画像の形、pose が軸の推定の返りでない、nbins < 16、マーカーが写っていない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_diabolo_model_and_vision](../../../../examples/poc_diabolo_model_and_vision.py) — `py -3.11 examples/poc_diabolo_model_and_vision.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`diabolo`)

[diabolo_params](diabolo_params.md) · [diabolo_spheroid](diabolo_spheroid.md) · [spheroid_closest](spheroid_closest.md) · [diabolo_dynamics_step](diabolo_dynamics_step.md) · [diabolo_simulate](diabolo_simulate.md) · [diabolo_state_sequence](diabolo_state_sequence.md) · [diabolo_throw_catch_truth](diabolo_throw_catch_truth.md) · [string_tension_static](string_tension_static.md)

---
*Provenance: diabolo.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
