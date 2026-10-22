---
op: sem_render
dim: generative
category: sem
in: image2d
out: image2d
examples: [poc_sem_tem_same_particle, poc_sem_wafer_defect_edge_bias]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# sem_render — GENERATIVE `sem` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.sem_render(height, *, pixel_nm: 'float' = 1.0, psf_px: 'float' = 1.5, edge_gain: 'float' = 1.0, base: 'float' = 0.25, dose: 'float' = 0.0, charging: 'float' = 0.0, seed: 'int' = 0, tilt_max_deg: 'float' = 80.0) -> 'np.ndarray'` (実装を直接呼ぶなら `import sem; sem.sem_render(height, *, pixel_nm: 'float' = 1.0, psf_px: 'float' = 1.5, edge_gain: 'float' = 1.0, base: 'float' = 0.25, dose: 'float' = 0.0, charging: 'float' = 0.0, seed: 'int' = 0, tilt_max_deg: 'float' = 80.0) -> 'np.ndarray'`、台帳から引くなら `opsgenerative.get("sem_render")`)

## 使い方

高さ場から SEM 像(二次電子の縁効果 + ビーム PSF + ショット雑音)を描く。

Parameters
----------
height : array_like
    2-D の高さ場[同じ単位は ``pixel_nm``]。欠陥の形そのもの。
pixel_nm : float
    画素 1 個の一辺[nm]。傾きは ``arctan(|∇h| / pixel_nm)`` で測る。
psf_px : float
    ビーム PSF のガウシアン σ[px]。段差の明るい縁はこの幅に広がる。
edge_gain : float
    縁効果の強さの指数。``sec(θ) ** edge_gain``。既定 1.0 が sec θ の素のモデル。
base : float
    平らな面(θ=0)の明るさ[0,1]。斜面は ``base·sec θ`` に乗る(飽和で 1 に頭打ち)。
dose : float
    画素あたりの電子数。``> 0`` でポアソン雑音を載せる。``0`` は雑音なし(決定論)。
charging : float
    帯電による緩い横方向の輝度勾配(0 で無効)。収差でなく系統的な明暗。
seed : int
    ポアソン雑音の種(``dose > 0`` のときだけ効く)。
tilt_max_deg : float
    sec θ が発散しないよう θ を頭打ちにする角度[度]。既定 80 度(sec ≈ 5.76)。

Returns
-------
numpy.ndarray
    ``(H, W)`` の float64、[0,1]。平らな面は ``base``、斜面は ``base·sec θ``。

Notes
-----
正規化は**画素ごとでなく固定の線形写像**(``·base`` と [0,1] クリップ)。
1 枚ごとに min/max で正規化すると平面に対する比が壊れ、sec θ の真値を
測れなくなる(``poc_real_defect_floor`` が ``colorize_depth`` の per-image
正規化で踏んだ罠と同じ)。

Examples
--------
>>> import numpy as np
>>> flat = np.zeros((16, 16))
>>> img = sem_render(flat)
>>> float(np.ptp(img))            # 平らな面は一様
0.0
>>> ramp = np.tile(np.linspace(0, 15, 16), (16, 1))   # 一様斜面
>>> r = sem_render(ramp, pixel_nm=1.0)
>>> theta = np.arctan(1.0)                            # 勾配 1 → 45 度
>>> abs(float(r[8, 8]) / 0.25 - 1.0 / np.cos(theta)) < 1e-6
True

## 詳しい使い方ガイド

- [generative_art ファミリ ガイド](../guides/generative_art.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_sem_tem_same_particle](../../../../examples/poc_sem_tem_same_particle.py) — `py -3.11 examples/poc_sem_tem_same_particle.py`
- [poc_sem_wafer_defect_edge_bias](../../../../examples/poc_sem_wafer_defect_edge_bias.py) — `py -3.11 examples/poc_sem_wafer_defect_edge_bias.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[sem_image](sem_image.md) · [sem_charging_series](sem_charging_series.md) · [pl_image_simulate](../pl/pl_image_simulate.md)

## 同カテゴリ(`sem`)

[sem_electron_mc](sem_electron_mc.md) · [sem_se_universal_curve](sem_se_universal_curve.md) · [sem_yield_curve](sem_yield_curve.md) · [sem_line_profile](sem_line_profile.md) · [sem_cd_measure](sem_cd_measure.md) · [sem_image](sem_image.md) · [sem_se_escape_fraction](sem_se_escape_fraction.md) · [sem_charging_series](sem_charging_series.md)

---
*Provenance: sem.py — GENERATIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
