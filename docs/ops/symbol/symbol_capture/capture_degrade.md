---
op: capture_degrade
dim: symbol
category: symbol_capture
in: image2d
out: image2d
gpu: なし
examples: [poc_symbol_lot_ocr, poc_symbol_package_1d, poc_symbol_part_dpm]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# capture_degrade — SYMBOL `symbol_capture` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.capture_degrade(image, *, defocus_px=0.0, motion_px=0.0, motion_deg=0.0, gauss_px=0.0, illum_slope=0.0, illum_deg=0.0, vignette=0.0, exposure=1.0, full_well_e=None, read_noise_e=0.0, bits=None, seed=0)` (実装を直接呼ぶなら `import symrender; symrender.capture_degrade(image, *, defocus_px=0.0, motion_px=0.0, motion_deg=0.0, gauss_px=0.0, illum_slope=0.0, illum_deg=0.0, vignette=0.0, exposure=1.0, full_well_e=None, read_noise_e=0.0, bits=None, seed=0)`、台帳から引くなら `opssymbol.get("capture_degrade")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

反射率の画像に撮像の劣化(照明・ぼけ・センサ雑音)を掛ける(``image2d``)。

Apply the capture chain to a reflectance image, in physical order:

1. illumination: ``E = exposure · (1 + illum_slope · s) · (1 − vignette · ρ²)`` with
   ``s`` in [−0.5, 0.5] across the image along ``illum_deg`` and ``ρ`` = radius / half
   diagonal (so ``illum_slope = 0.4`` means 40 % more light on one side than the other);
2. lens: defocus as a uniform disc of diameter ``defocus_px`` (the geometric blur
   circle ``c = A·|Δz|/z'`` in pixels), uniform motion over ``motion_px`` along
   ``motion_deg``, and a Gaussian of standard deviation ``gauss_px`` (residual
   aberrations / diffraction), each area-integrated, borders replicated;
3. sensor (only if ``full_well_e`` is given): the irradiance 1.0 fills
   ``full_well_e`` electrons; Poisson shot noise, Gaussian read noise
   ``read_noise_e`` (electrons), saturation at full well, and ``bits``-bit
   quantisation if given. Output = electrons / full_well_e, in [0, 1].

Deterministic for a given ``seed``. Without ``full_well_e`` the result is noise-free
(``read_noise_e`` must then be 0).

空の入力(辺が 0)は ``ValueError``。
拒否(``ValueError``): 2-D でない、非有限、負のぼけ量、``|illum_slope| >= 2``、
``vignette`` が [0, 1) の外、``full_well_e`` < 10、``read_noise_e`` < 0 または
``full_well_e`` 無しで > 0、``bits`` が 1..16 の外。

## 詳しい使い方ガイド

- [symbol_reading ファミリ ガイド](../guides/symbol_reading.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_symbol_lot_ocr](../../../../examples/poc_symbol_lot_ocr.py) — `py -3.11 examples/poc_symbol_lot_ocr.py`
- [poc_symbol_package_1d](../../../../examples/poc_symbol_package_1d.py) — `py -3.11 examples/poc_symbol_package_1d.py`
- [poc_symbol_part_dpm](../../../../examples/poc_symbol_part_dpm.py) — `py -3.11 examples/poc_symbol_part_dpm.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[barcode_scan_profiles](../barcode1d/barcode_scan_profiles.md) · [read_barcode1d](../barcode1d/read_barcode1d.md) · [qr_locate](../datacode2d/qr_locate.md) · [qr_sample](../datacode2d/qr_sample.md) · [qr_read](../datacode2d/qr_read.md) · [dm_locate](../datacode2d/dm_locate.md) · [dm_sample](../datacode2d/dm_sample.md) · [dm_read](../datacode2d/dm_read.md)

## 同カテゴリ(`symbol_capture`)

[render_symbol](render_symbol.md)

---
*Provenance: symrender.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
