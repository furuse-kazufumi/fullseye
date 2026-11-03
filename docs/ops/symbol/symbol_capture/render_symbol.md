---
op: render_symbol
dim: symbol
category: symbol_capture
in: table
out: image2d
gpu: なし
examples: [poc_symbol_package_1d, poc_symbol_part_dpm]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# render_symbol — SYMBOL `symbol_capture` op

- **データ種**: `table` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.render_symbol(symbol, module_px=4.0, *, quiet=None, bar_height=None, rotate_deg=0.0, tilt_deg=0.0, tilt_axis_deg=0.0, distance_ratio=10.0, offset_px=(0.0, 0.0), ink_gain=0.0, dot=None, dark=0.05, light=0.85, margin_modules=2.0, supersample=4, return_geometry=False)` (実装を直接呼ぶなら `import symrender; symrender.render_symbol(symbol, module_px=4.0, *, quiet=None, bar_height=None, rotate_deg=0.0, tilt_deg=0.0, tilt_axis_deg=0.0, distance_ratio=10.0, offset_px=(0.0, 0.0), ink_gain=0.0, dot=None, dark=0.05, light=0.85, margin_modules=2.0, supersample=4, return_geometry=False)`、台帳から引くなら `opssymbol.get("render_symbol")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

シンボル(1-D の幅か 2-D のモジュール格子)を、平面の反射率画像として描く(``image2d``)。

Render a symbol as the reflectance image a pinhole camera sees. ``module_px`` is
the module (X dimension) size in pixels at the symbol centre; ``rotate_deg`` turns
the symbol in its plane (counter-clockwise on screen), ``tilt_deg`` tilts the plane
about an in-plane axis at ``tilt_axis_deg`` (perspective; the camera sits
``distance_ratio`` symbol sizes away, so 10 means mild keystone). ``ink_gain``
(modules) widens dark areas (bar width gain, > 0) or narrows them (< 0); ``dot``
draws 2-D dark modules as discs of that diameter (modules). Reflectances are
``dark`` (ink) and ``light`` (substrate); each pixel is the mean of
``supersample``² point samples (area coverage). The canvas holds the symbol, its
quiet zone (``quiet`` modules; default 4 for QR and raw grids, 2 for the table
from ``dm_encode`` unless the table says otherwise; for 1-D the table's own quiet
zones and ``quiet`` is the margin above and below the bars) and a further
``margin_modules`` of substrate.

``return_geometry=True`` returns a table instead: ``image``, ``homography``
(plane ``[u, v, 1]`` in modules → ``[col, row, w]``), ``plane_size`` (modules),
``module_px``.

空の入力(モジュール格子が 0 行)は ``ValueError``。
拒否(``ValueError``): 表に ``modules`` も ``edges`` も無い、``module_px`` <= 0.5、
``dark >= light``、反射率が [0, 1] の外、``|tilt_deg| >= 80``、``|ink_gain| > 0.9``、
``supersample`` が 1..16 の外、キャンバスが 4000 画素を超える。

## 詳しい使い方ガイド

- [symbol_reading ファミリ ガイド](../guides/symbol_reading.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_symbol_package_1d](../../../../examples/poc_symbol_package_1d.py) — `py -3.11 examples/poc_symbol_package_1d.py`
- [poc_symbol_part_dpm](../../../../examples/poc_symbol_part_dpm.py) — `py -3.11 examples/poc_symbol_part_dpm.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[barcode_scan_profiles](../barcode1d/barcode_scan_profiles.md) · [read_barcode1d](../barcode1d/read_barcode1d.md) · [qr_locate](../datacode2d/qr_locate.md) · [qr_sample](../datacode2d/qr_sample.md) · [qr_read](../datacode2d/qr_read.md) · [dm_locate](../datacode2d/dm_locate.md) · [dm_sample](../datacode2d/dm_sample.md) · [dm_read](../datacode2d/dm_read.md)

## 同カテゴリ(`symbol_capture`)

[capture_degrade](capture_degrade.md)

---
*Provenance: symrender.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
