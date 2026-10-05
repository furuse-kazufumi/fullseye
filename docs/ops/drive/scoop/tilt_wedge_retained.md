---
op: tilt_wedge_retained
dim: drive
category: scoop
in: scalar × scalar × scalar × scalar
out: table
examples: [poc_powder_scoop_pour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# tilt_wedge_retained — DRIVE `scoop` op

- **データ種**: `scalar × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.tilt_wedge_retained(theta_deg: 'float', phi_deg: 'float', L: 'float', h0: 'float') -> 'dict'` (実装を直接呼ぶなら `import scoop; scoop.tilt_wedge_retained(theta_deg: 'float', phi_deg: 'float', L: 'float', h0: 'float') -> 'dict'`、台帳から引くなら `opsdrive.get("tilt_wedge_retained")`)

## 使い方

口に壁の無い器(床の長さ ``L``、奥壁は床に垂直で十分高い)に深さ ``h0`` で平らに盛った粉を、口を下げて θ 傾けた
ときに残る量(2 次元断面、準静的、**自分の導出**)。

口の前面は初めから安息角 φ の斜面(口に壁が無いので垂直の崖は立たない)。傾けると口を通る斜面は水平から φ を
保ち、床から見ると ``φ − θ``。奥の平らな面は床に平行のまま(``θ < φ`` で安定)。保持断面
``A(θ) = ∫₀ᴸ min(h₀, x tan(φ − θ)) dx``、出た割合 ``F = 1 − A(θ) / A(0)``。出始めは θ = 0⁺(前面の楔からすぐ
こぼれる)、斜面が奥壁に届く角 ``θ_b = φ − atan(h₀ / L)``、θ ≥ φ で全部出る。
式は granular の ``spoon_tilt_dispense(lip="open")`` を呼ぶ(保持断面の式は granular の 1 か所だけ)。参考に口に縁がある器
(``lip="wall"``、初めの量 ``L h₀``、θ_c までこぼれない)の割合 ``F_lip_wall`` と ``theta_c_lip_wall_deg`` も返す(MuJoCo の
口の開いた樋でどちらが合うかを比べるため)。
返り: ``A``, ``A0``, ``fraction``, ``theta_back_deg``, ``F_lip_wall``, ``theta_c_lip_wall_deg``。
**Raises** ``ValueError``: θ が [0, 90) の外、φ が (0, 90) の外、``L``・``h0`` が ≤ 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_scoop_pour](../../../../examples/poc_powder_scoop_pour.py) — `py -3.11 examples/poc_powder_scoop_pour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`scoop`)

[spoon_bowl_volume](spoon_bowl_volume.md) · [scoop_synth_side](scoop_synth_side.md) · [revolution_volume_side](revolution_volume_side.md) · [two_view_volume](two_view_volume.md) · [scoop_volume_read](scoop_volume_read.md) · [scoop_count](scoop_count.md) · [scoop_image_limit](scoop_image_limit.md) · [tilt_pour_rate](tilt_pour_rate.md)

---
*Provenance: scoop.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
