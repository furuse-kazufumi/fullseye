---
op: ou_estimate
dim: drive
category: traffic
in: signal
out: table
examples: [poc_driving_traffic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# ou_estimate — DRIVE `traffic` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.ou_estimate(x, dt: 'float') -> 'Dict[str, float]'` (実装を直接呼ぶなら `import drivetraffic; drivetraffic.ou_estimate(x, dt: 'float') -> 'Dict[str, float]'`、台帳から引くなら `opsdrive.get("ou_estimate")`)

## 使い方

横ふらつき(平均 0 の OU 過程 dX = −θX dt + σ dW)の母数を、等間隔 dt の観測の列から読む。

厳密離散化 x_{k+1} = φ x_k + ε_k(φ = e^{−θ dt}、ε ~ N(0, q²)、q² = σ²(1 − φ²)/(2θ))の条件つき最尤:

    φ̂ = Σ x_k x_{k+1} / Σ x_k²,  q̂² = mean((x_{k+1} − φ̂ x_k)²),  θ̂ = −ln φ̂ / dt,  σ̂ = q̂ sqrt(2θ̂ / (1 − φ̂²))

(Euler の (1 − φ̂)/dt でなく ln を使うので dt が粗くても偏らない)。標準誤差は漸近式: se(φ̂) = sqrt((1 − φ²)/n)、
se(q̂) = q/sqrt(2n)、θ̂・σ̂ はデルタ法。``sigma_increment`` = sqrt(mean(Δx²)/dt) は θ を使わない粗い推定
(E[Δx²] = σ²(1 − φ)/θ なので θ dt → 0 で σ。相関時間の長い系列を短く見るとき、位置の標本 SD より σ を安定に読める)。

戻り値 dict: ``theta``, ``sigma``, ``sd``(定常 SD σ/√(2θ))、``phi``, ``q``, ``n``(増分の数)、``se_theta``,
``se_sigma``, ``sigma_increment``。

**Raises** ``ValueError``: 1-D でない・3 点未満・非有限、dt ≤ 0、φ̂ ∉ (0, 1)(この dt では平均へ戻る過程に見えない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_traffic](../../../../examples/poc_driving_traffic.py) — `py -3.11 examples/poc_driving_traffic.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`traffic`)

[idm_accel](idm_accel.md) · [idm_equilibrium_gap](idm_equilibrium_gap.md) · [idm_platoon_simulate](idm_platoon_simulate.md) · [driver_style](driver_style.md) · [lateral_wobble](lateral_wobble.md) · [social_force_step](social_force_step.md) · [pedestrian_crossing](pedestrian_crossing.md) · [occlusion_reveal_distance](occlusion_reveal_distance.md)

---
*Provenance: drivetraffic.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
