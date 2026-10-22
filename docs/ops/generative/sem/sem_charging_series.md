---
op: sem_charging_series
dim: generative
category: sem
in: image2d
out: video
examples: [poc_virtual_sem_kv_cd_bse]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# sem_charging_series — GENERATIVE `sem` op

- **データ種**: `image2d` → `video`
- **呼び出し**: `import fullseye as fs; fs.ledger.sem_charging_series(height, material_map=None, *, materials=('PMMA',), substrate='SI', energy_kev: 'float' = 1.0, pixel_nm: 'float' = 2.0, beam_sigma_nm: 'float' = 1.0, electrons_per_pixel: 'int' = 30, detector: 'str' = 'inlens', frames: 'int' = 12, layer_bottom_nm=0.0, volts_per_electron: 'float' = 0.05, leak_frames: 'float' = 0.0, spread_px: 'float' = 1.0, phi_ev: 'float' = 2.0, gain=None, seed: 'int' = 0, return_potential: 'bool' = False)` (実装を直接呼ぶなら `import sem; sem.sem_charging_series(height, material_map=None, *, materials=('PMMA',), substrate='SI', energy_kev: 'float' = 1.0, pixel_nm: 'float' = 2.0, beam_sigma_nm: 'float' = 1.0, electrons_per_pixel: 'int' = 30, detector: 'str' = 'inlens', frames: 'int' = 12, layer_bottom_nm=0.0, volts_per_electron: 'float' = 0.05, leak_frames: 'float' = 0.0, spread_px: 'float' = 1.0, phi_ev: 'float' = 2.0, gain=None, seed: 'int' = 0, return_potential: 'bool' = False)`、台帳から引くなら `opsgenerative.get("sem_charging_series")`)

## 使い方

絶縁物の帯電を走査のコマごとに進め、像の時間変化(``video``、(T, H, W))を返す。

1 コマで画素あたり ``electrons_per_pixel`` 個の電子が入り、η + δ·F(V) 個が出ていく。
差し引き 1 − η − δ·F(V) 個が絶縁物の面に溜まり、電位を ``volts_per_electron`` [V/個]
ずつ動かす(負の電子が溜まれば V は下がる)。電位は ``spread_px`` で横に広がり、
``leak_frames``(> 0 なら)の時定数で抜ける。導体の面は接地(V = 0)。

* **正の帯電**(η + δ > 1、低加速で多い): 二次電子が面に引き戻され(F(V)、
  :func:`sem_se_escape_fraction`)、像は暗くなる。放出が減ると正味の流れも 0 に
  近づくので、電位は η + δ·F(V*) = 1 の V* で止まる(自己調整)。
* **負の帯電**(η + δ < 1、高加速): 面の負の電位が二次電子を押し出し、像は
  ``1 + |V| / (|V| + 20 V)`` 倍に明るくなる(★現象論の式で、2 定数は固定 ——
  ``_NEG_GAIN``・``_NEG_SCALE_V``。
  着地エネルギーの低下とビームの曲がりは入れない)。

η と δ は :func:`sem_image` のモンテカルロ(``return_signals``)で 1 回だけ求め、
コマごとの雑音は検出された電子の数のポアソンで載せる。

Returns
-------
numpy.ndarray
    (frames, H, W) の float64、[0,1] (``sem_image`` と同じ固定の倍率)。
    ``return_potential`` なら dict(``video`` と、コマごとの電位 ``potential_v`` (T, H, W)、
    絶縁物の面のマスク ``insulator``)。

Examples
--------
>>> import numpy as np
>>> v = sem_charging_series(np.zeros((4, 4)), materials=("PMMA",), substrate="PMMA",
...                         electrons_per_pixel=5, frames=3)
>>> v.shape
(3, 4, 4)

## 詳しい使い方ガイド

- [generative_art ファミリ ガイド](../guides/generative_art.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_virtual_sem_kv_cd_bse](../../../../examples/poc_virtual_sem_kv_cd_bse.py) — `py -3.11 examples/poc_virtual_sem_kv_cd_bse.py`

## 型が繋がる次の op(`video` を入力に取れる)

—

## 同カテゴリ(`sem`)

[sem_render](sem_render.md) · [sem_electron_mc](sem_electron_mc.md) · [sem_se_universal_curve](sem_se_universal_curve.md) · [sem_yield_curve](sem_yield_curve.md) · [sem_line_profile](sem_line_profile.md) · [sem_cd_measure](sem_cd_measure.md) · [sem_image](sem_image.md) · [sem_se_escape_fraction](sem_se_escape_fraction.md)

---
*Provenance: sem.py — GENERATIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
