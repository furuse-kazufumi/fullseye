---
op: ae_band_power
dim: drive
category: grind
in: signal × scalar
out: table
examples: [poc_powder_grinding_ae]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# ae_band_power — DRIVE `grind` op

- **データ種**: `signal × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.ae_band_power(x, rate: 'float', f_lo: 'float' = 100000.0, f_hi: 'float' = 1000000.0, start: 'int' = 0, stop: 'int | None' = None, win: 'int' = 4096) -> 'dict'` (実装を直接呼ぶなら `import grind; grind.ae_band_power(x, rate: 'float', f_lo: 'float' = 100000.0, f_hi: 'float' = 1000000.0, start: 'int' = 0, stop: 'int | None' = None, win: 'int' = 4096) -> 'dict'`、台帳から引くなら `opsdrive.get("ae_band_power")`)

## 使い方

AE の帯域電力を 2 通りで出す(一方は公開の解析コードの定義、他方は ``acoustics.stft`` の密度スペクトル)。

- ``power_fft``: 窓なし FFT の振幅 ``2|X|/N`` の二乗を ``f_lo ≤ f ≤ f_hi`` で足した値 [V²] (解析コードと同じ。正弦波の振幅 A なら A²)。
- ``power_stft``: ``acoustics.stft(scaling="density")`` の内側のコマの PSD を帯域で積分した平均 [V²] (= 帯域の平均二乗)。
  Parseval で ``power_fft ≈ 2 · power_stft``(振幅² は平均二乗の 2 倍)。比 ``ratio = power_fft / (2 power_stft)`` を返す。
- ``band_series`` / ``times``: コマごとの帯域電力(スペクトログラムの帯の時間変化)、``spectrogram_db`` は表示用(帯に関係なく全帯域)。
``start`` / ``stop`` は標本の切り出し(解析コードは雑音の区間を飛ばすため 200013 から)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_grinding_ae](../../../../examples/poc_powder_grinding_ae.py) — `py -3.11 examples/poc_powder_grinding_ae.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`grind`)

[particle_size_read](particle_size_read.md) · [particle_size_dx](particle_size_dx.md) · [particle_size_oversize](particle_size_oversize.md) · [particle_size_synth](particle_size_synth.md) · [comminution_energy](comminution_energy.md) · [comminution_law_fit](comminution_law_fit.md) · [breakage_first_order_fit](breakage_first_order_fit.md) · [replicate_compare](replicate_compare.md)

---
*Provenance: grind.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
