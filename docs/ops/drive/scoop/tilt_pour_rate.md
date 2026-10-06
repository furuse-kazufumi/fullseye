---
op: tilt_pour_rate
dim: drive
category: scoop
in: scalar × scalar × scalar × scalar × scalar × scalar × scalar
out: table
examples: [poc_powder_scoop_pour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# tilt_pour_rate — DRIVE `scoop` op

- **データ種**: `scalar × scalar × scalar × scalar × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.tilt_pour_rate(theta_deg: 'float', omega_deg_s: 'float', phi_deg: 'float', L: 'float', h0: 'float', B: 'float', bulk_density: 'float') -> 'dict'` (実装を直接呼ぶなら `import scoop; scoop.tilt_pour_rate(theta_deg: 'float', omega_deg_s: 'float', phi_deg: 'float', L: 'float', h0: 'float', B: 'float', bulk_density: 'float') -> 'dict'`、台帳から引くなら `opsdrive.get("tilt_pour_rate")`)

## 使い方

:func:`tilt_wedge_retained` の器を角速度 ω で傾けたときの準静的な流量 ``W = ρ_b B (−dA/dθ) ω`` [kg/s]
(供給で決まる流量: 口の通す力より遅く傾けている限り、流量は傾ける速さで決まる)。

``dA/dθ``: 斜面が奥に届く前(``x_k = h₀ / t < L``)は ``−h₀² sec²(φ−θ) / (2 t²)``、届いた後は ``−½ L² sec²(φ−θ)``
(``t = tan(φ − θ)``)。θ = 0 では ``h₀² / (2 sin² φ)``(前面の斜面の長さ ``h₀ / sin φ`` の楔)。
返り: ``rate`` [kg/s]、``rate_area``(``−dA/dθ·ω`` [m²/s])、``fraction``(出た割合)、``theta_back_deg``。
**Raises** ``ValueError``: 引数の範囲(ω ≤ 0 を含む)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_scoop_pour](../../../../examples/poc_powder_scoop_pour.py) — `py -3.11 examples/poc_powder_scoop_pour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`scoop`)

[spoon_bowl_volume](spoon_bowl_volume.md) · [scoop_synth_side](scoop_synth_side.md) · [revolution_volume_side](revolution_volume_side.md) · [two_view_volume](two_view_volume.md) · [scoop_volume_read](scoop_volume_read.md) · [scoop_count](scoop_count.md) · [scoop_image_limit](scoop_image_limit.md) · [tilt_wedge_retained](tilt_wedge_retained.md)

---
*Provenance: scoop.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
