---
op: cone_profile_px
dim: drive
category: granular
in: signal × scalar × scalar
out: signal
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# cone_profile_px — DRIVE `granular` op

- **データ種**: `signal × scalar × scalar` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.cone_profile_px(u, H_px: 'float', phi_deg: 'float', toe_round_px: 'float' = 0.0, apex_blunt_px: 'float' = 0.0)` (実装を直接呼ぶなら `import granular; granular.cone_profile_px(u, H_px: 'float', phi_deg: 'float', toe_round_px: 'float' = 0.0, apex_blunt_px: 'float' = 0.0)`、台帳から引くなら `opsdrive.get("cone_profile_px")`)

## 使い方

円錐の母線の断面 ``c(u)`` [px] (``u`` = 軸からの距離 [px])。

基本は ``c = max(0, H − u tan φ)``。``apex_blunt_px`` = 頂に内接する円弧の半径(材料を削る、中心は
``(0, H − r/cos φ)``、接点 ``u = r sin φ``)。``toe_round_px`` = 裾の凹みを埋める円弧の半径(材料を
足す、中心は空気側 ``(x_t, r)``、``x_t = R + r tan(φ/2)``、接点 ``u = x_t − r sin φ``)—— どちらも
接線連続(導出: 接点で両側の高さが裾は ``r(1 − cos φ)``、頂は ``H − r sin²φ / cos φ`` で一致)。**Raises** ``ValueError``: 2 つの円弧が重なる(山が小さすぎる)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`signal` を入力に取れる)

[flight_vacuum](../ball/flight_vacuum.md) · [magnus_lift_coefficient](../ball/magnus_lift_coefficient.md) · [drag_coefficient_sphere](../ball/drag_coefficient_sphere.md) · [restitution_from_apexes](../ball/restitution_from_apexes.md) · [restitution_from_intervals](../ball/restitution_from_intervals.md) · [fit_parabola](../ball/fit_parabola.md) · [flight_fit](../ball/flight_fit.md) · [fit_aero](../ball/fit_aero.md)

## 同カテゴリ(`granular`)

[heap_volume_cone](heap_volume_cone.md) · [heap_mass](heap_mass.md) · [heap_volume_heightmap](heap_volume_heightmap.md) · [beverloo_rate](beverloo_rate.md) · [beverloo_fit](beverloo_fit.md) · [discharge_synth](discharge_synth.md) · [dispense_mass_from_video](dispense_mass_from_video.md) · [hopper_discharge_rate](hopper_discharge_rate.md)

---
*Provenance: granular.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
