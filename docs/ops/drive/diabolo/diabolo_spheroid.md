---
op: diabolo_spheroid
dim: drive
category: diabolo
in: signal × signal × scalar
out: table
examples: [poc_diabolo_model_and_vision]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# diabolo_spheroid — DRIVE `diabolo` op

- **データ種**: `signal × signal × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.diabolo_spheroid(p_left, p_right, string_length: 'float') -> 'dict'` (実装を直接呼ぶなら `import diabolo; diabolo.diabolo_spheroid(p_left, p_right, string_length: 'float') -> 'dict'`、台帳から引くなら `opsdrive.get("diabolo_spheroid")`)

## 使い方

棒の先 2 点(焦点)と糸の長さ → 補助の回転楕円体: a = l/2、c = |x_L − x_R|/2、b = √(a² − c²)(式 1 の正しい形)。

★原文の (1b) は b = √(a² − |x_L − x_R|/2) で、長さと長さの 2 乗の差なので次元が合わない。論文の実機寸法(糸 1.45 m、棒の間隔
1.10 m)を入れると根の中が負になる(NaN)。楕円の恒等式 a² = b² + c² の形に直した(公開実装も 2 乗で書いている)。原文の値は
``b_paper_literal`` に残す。原文の前文は「半長軸 b と半短軸 a」と名前が逆(a = l/2 が半長軸)で、式の側に従う。

返り ``{"center", "axis"(x_L − x_R の単位ベクトル), "a", "b", "c", "b_paper_literal"}``。
**Raises** ``ValueError``: 間隔 ≥ 糸、棒が重なる、有限でない入力。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_diabolo_model_and_vision](../../../../examples/poc_diabolo_model_and_vision.py) — `py -3.11 examples/poc_diabolo_model_and_vision.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`diabolo`)

[diabolo_params](diabolo_params.md) · [spheroid_closest](spheroid_closest.md) · [diabolo_dynamics_step](diabolo_dynamics_step.md) · [diabolo_simulate](diabolo_simulate.md) · [diabolo_state_sequence](diabolo_state_sequence.md) · [diabolo_throw_catch_truth](diabolo_throw_catch_truth.md) · [string_tension_static](string_tension_static.md) · [string_tension_from_sag](string_tension_from_sag.md)

---
*Provenance: diabolo.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
