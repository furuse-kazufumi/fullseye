---
op: sem_image
dim: generative
category: sem
in: image2d
out: image2d
examples: [poc_virtual_sem_kv_cd_bse]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# sem_image — GENERATIVE `sem` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.sem_image(height, material_map=None, *, materials=('SI',), substrate='SI', energy_kev: 'float' = 5.0, pixel_nm: 'float' = 2.0, beam_sigma_nm: 'float' = 1.0, electrons_per_pixel: 'int' = 30, detector: 'str' = 'inlens', layer_bottom_nm=0.0, buried=None, gain=None, seed: 'int' = 0, return_signals: 'bool' = False)` (実装を直接呼ぶなら `import sem; sem.sem_image(height, material_map=None, *, materials=('SI',), substrate='SI', energy_kev: 'float' = 5.0, pixel_nm: 'float' = 2.0, beam_sigma_nm: 'float' = 1.0, electrons_per_pixel: 'int' = 30, detector: 'str' = 'inlens', layer_bottom_nm=0.0, buried=None, gain=None, seed: 'int' = 0, return_signals: 'bool' = False)`、台帳から引くなら `opsgenerative.get("sem_image")`)

## 使い方

高さ場と材料の地図から、画素ごとに電子を撃って SEM 像を作る(MC の直接計算)。

各画素に ``electrons_per_pixel`` 個の一次電子(ビーム幅 ``beam_sigma_nm`` のガウシアン)
を撃ち、検出器の信号を電子 1 個あたりで平均する。**雑音は撃った電子の数そのもの**
(反射電子も二次電子も 1 個ずつの統計)なので、別のポアソン雑音は載せない。

Parameters
----------
height : array_like
    (H, W) の高さ場 [nm] (上が正)。
material_map : array_like of int, optional
    (H, W) の材料番号(``materials`` の添字)。表面から ``layer_bottom_nm`` までの柱の
    材料。それより深い所は ``substrate``。``None`` は全部 ``materials[0]``。
materials : sequence of str
    材料表の名前の列。
substrate : str
    基板の材料。
energy_kev, pixel_nm, beam_sigma_nm : float
    加速電圧 [keV]・画素の一辺 [nm]・ビームの σ [nm]。
electrons_per_pixel : int
    画素あたりの一次電子の数(像の S/N を決める)。
detector : str
    ``inlens``(レンズ内の二次電子)/ ``everhart``(側方の二次電子、+x 側、SE3 込み)/
    ``bse``(真上の環状の反射電子、エネルギー重み)/ ``se_total``(検出器なしの全収率)。
layer_bottom_nm : float or array_like
    材料の柱の下端の z [nm] (0 = 基板の上面。正は基板の中へ)。
buried : list, optional
    埋もれた箱 ``[(材料名, (H, W) のマスク, 上端の深さ, 下端の深さ), ...]`` [nm]。
gain : float, optional
    信号 → [0,1] の固定の倍率(既定は検出器ごとの定数。画像ごとに正規化しない)。
seed : int
    乱数の種。
return_signals : bool
    True なら像の代わりに dict(4 検出器の信号の地図と η の地図)を返す。

Returns
-------
numpy.ndarray
    (H, W) の float64、[0,1]。

Examples
--------
>>> import numpy as np
>>> img = sem_image(np.zeros((6, 6)), energy_kev=1.0, electrons_per_pixel=5)
>>> img.shape, bool(0.0 <= img.min() and img.max() <= 1.0)
((6, 6), True)

## 詳しい使い方ガイド

- [generative_art ファミリ ガイド](../guides/generative_art.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_virtual_sem_kv_cd_bse](../../../../examples/poc_virtual_sem_kv_cd_bse.py) — `py -3.11 examples/poc_virtual_sem_kv_cd_bse.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[sem_render](sem_render.md) · [sem_charging_series](sem_charging_series.md) · [pl_image_simulate](../pl/pl_image_simulate.md)

## 同カテゴリ(`sem`)

[sem_render](sem_render.md) · [sem_electron_mc](sem_electron_mc.md) · [sem_se_universal_curve](sem_se_universal_curve.md) · [sem_yield_curve](sem_yield_curve.md) · [sem_line_profile](sem_line_profile.md) · [sem_cd_measure](sem_cd_measure.md) · [sem_se_escape_fraction](sem_se_escape_fraction.md) · [sem_charging_series](sem_charging_series.md)

---
*Provenance: sem.py — GENERATIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
