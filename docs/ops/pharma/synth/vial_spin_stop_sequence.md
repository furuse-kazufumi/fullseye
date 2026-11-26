---
op: vial_spin_stop_sequence
dim: pharma
category: synth
in: 
out: video
gpu: なし
examples: [poc_vial_particle_pod]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# vial_spin_stop_sequence — PHARMA `synth` op

- **データ種**: `なし` → `video`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.vial_spin_stop_sequence(shape=(96, 72), *, n_frames=18, frame_interval_s=0.04, initial_omega_rad_s=10.0, decay_time_s=0.25, vial_radius_mm=10.0, liquid_height_mm=28.0, particle_diameter_um=80.0, particle_density_kg_m3=1450.0, particle_contrast=0.16, illumination='back', n_particles=1, n_bubbles=1, n_scratches=1, viscosity_pa_s=0.003, fluid_density_kg_m3=1000.0, pixel_size_um=280.0, noise_sigma=0.012, seed=0)` (実装を直接呼ぶなら `import vialops; vialops.vial_spin_stop_sequence(shape=(96, 72), *, n_frames=18, frame_interval_s=0.04, initial_omega_rad_s=10.0, decay_time_s=0.25, vial_radius_mm=10.0, liquid_height_mm=28.0, particle_diameter_um=80.0, particle_density_kg_m3=1450.0, particle_contrast=0.16, illumination='back', n_particles=1, n_bubbles=1, n_scratches=1, viscosity_pa_s=0.003, fluid_density_kg_m3=1000.0, pixel_size_um=280.0, noise_sigma=0.012, seed=0)`、台帳から引くなら `opspharma.get("vial_spin_stop_sequence")`)
- **台帳経由の戻り値**: `fullseye.ledger.vial_spin_stop_sequence(...)` は**宣言 out 型 `video` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.vial_spin_stop_sequence.raw(...)`、または `vialops.vial_spin_stop_sequence` を直接呼ぶ。
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

回転停止後のバイアル画像列と物体ごとの真値軌跡を作る。

The liquid azimuthal velocity is the axisymmetric, prescribed field
``u_theta(r,t) = omega0 exp(-t/tau) r``; it is not a Navier--Stokes
solution.  A particle has that in-plane advection plus its Stokes terminal
velocity ``v_t = 2 r_p^2 (rho_p-rho_f) g / (9 mu)`` in the image-downward
direction.  Bubbles use ``rho_p=1.2 kg/m^3`` and therefore rise.  The model
is restricted to small Reynolds number / isolated spherical objects where
Stokes drag is appropriate; it does not model turbulent wake, aggregation,
meniscus forces, or wall-corrected drag.  At the cylindrical wall positions
are reflected, which prevents a silent escape but is not a hydrodynamic wall
model.  Refraction through glass and liquid is deliberately simplified to a
fixed apparent contrast and Gaussian PSF in this first stage.

``illumination`` is ``"back"`` or ``"side"``.  A fixed ``seed`` determines
object positions, sensor noise, and scratches.  The direct return is
``(frames, truth)``; ``truth`` contains a row table with object type, frame,
projected positions, physical positions and visibility, plus angular-speed
truth.  The ledger adapter returns only the ``video`` frames.

The rendered outline is a display-only 2R-like profile, not a metrology
calibration.  Its public dimensional source is ISO 8362-1:2018(E), Table 1
(2R: 16 mm body, 13 mm finish, 35 mm overall height, 8 mm finish height),
previewed at
``https://cdn.standards.iteh.ai/samples/74398/343407bc7b564f6184bfa0a9decede14/ISO-8362-1-2018.pdf``.
An independent public 2R product listing confirms the 16 mm body and 35 mm
overall height at
``https://www.westpharma.com/es-es/products/vial-containment-solutions/vials/nuova-ompi-sg-ez-fill-glass-vials-sterile-3-8-10``.
描画外形は計測校正ではなく、公開 ISO 8362-1:2018(E) Table 1 の 2R 比率を
使う表示モデルである。独立した公開製品寸法も上記 URL で確認する。

Raises ``ValueError`` for nonphysical dimensions, an unknown illumination,
or a nonintegral object count.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_vial_particle_pod](../../../../examples/poc_vial_particle_pod.py) — `py -3.11 examples/poc_vial_particle_pod.py`

## 型が繋がる次の op(`video` を入力に取れる)

[track_moving_particles](../track/track_moving_particles.md)

## 同カテゴリ(`synth`)

—

---
*Provenance: vialops.py — PHARMA operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
