---
op: whitney_wrench
dim: drive
category: pegtactile
in: table × text × scalar × scalar × scalar × scalar
out: table
examples: [poc_peg_insertion_tactile]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# whitney_wrench — DRIVE `pegtactile` op

- **データ種**: `table × text × scalar × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.whitney_wrench(kp, state: 'str', theta: 'float', depth: 'float', mu: 'float', fn_tip: 'float', fn_mouth: 'float' = 0.0, g=None) -> 'dict'` (実装を直接呼ぶなら `import pegtactile; pegtactile.whitney_wrench(kp, state: 'str', theta: 'float', depth: 'float', mu: 'float', fn_tip: 'float', fn_mouth: 'float' = 0.0, g=None) -> 'dict'`、台帳から引くなら `opsdrive.get("whitney_wrench")`)

## 使い方

閉形式の接触レンチ(Whitney の準静的な平面、真値つきの合成): 傾き θ(軸の上端が +x へ)・先端深さ ``depth``(口の面から)の
ペグに、``state`` = ``"one_point"``(先端の縁が −x の壁)/ ``"mouth"``(胴が +x の最狭部の縁)/ ``"two_point"``(両方)で、法線力
``fn_tip``・``fn_mouth`` と下へ滑る Coulomb 摩擦 μ を与える。二点は depth = W + l₂(θ) で胴も縁に触れる(閉形式)。``g`` は把持点
(省略時は先端から軸に沿って ペグ長 − 8 mm)。返り ``F``・``M_g``(把持点まわり)・``g``・``tip``・``axis``・``points``。
**Raises** ValueError: state が語彙の外、θ が (0, π/2) の外、depth・μ・法線力が有限でないか負。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_insertion_tactile](../../../../examples/poc_peg_insertion_tactile.py) — `py -3.11 examples/poc_peg_insertion_tactile.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegtactile`)

[pad_params](pad_params.md) · [pad_context](pad_context.md) · [peg_wrench_to_pad_loads](peg_wrench_to_pad_loads.md) · [pad_loads_to_peg_wrench](pad_loads_to_peg_wrench.md) · [pad_shear_asymmetry](pad_shear_asymmetry.md) · [pad_marker_displacement](pad_marker_displacement.md) · [pad_tactile_frame](pad_tactile_frame.md) · [pad_tactile_read](pad_tactile_read.md)

---
*Provenance: pegtactile.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
