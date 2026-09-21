---
op: fly_sky_1f
dim: flyvision
category: stimulus
in: 
out: image2d
examples: [poc_fly_optomotor_steering, poc_fly_vision]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# fly_sky_1f — FLYVISION `stimulus` op

- **データ種**: `なし` → `image2d`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.fly_sky_1f(width=1024, height=512, band_lo_deg=20.0, band_hi_deg=60.0, amp=0.12, seed=0, edge_deg=5.0)` (実装を直接呼ぶなら `import flyvision; flyvision.fly_sky_1f(width=1024, height=512, band_lo_deg=20.0, band_hi_deg=60.0, amp=0.12, seed=0, edge_deg=5.0)`、台帳から引くなら `opsflyvision.get("fly_sky_1f")`)

## 使い方

Synthetic equirectangular sky panorama with a banded 1/f azimuthal texture.

An equirectangular image (row = elevation +90 deg down to -90 deg, column =
azimuth 0 to 360 deg). Luminance is a vertical backlight gradient
(0.62 at the zenith to 0.95 at the nadir) modulated in azimuth by a 1/f
texture confined to an elevation band with cosine edges::

    L = gradient(el) * (1 + amp * band(el) * noise(az))   clipped to [0, 1]

where ``noise`` has unit std, is clipped to +-2, and drops azimuthal
frequencies below 2 cycles per revolution; ``band`` is 1 inside
``[band_lo_deg, band_hi_deg]`` with raised-cosine edges of width *edge_deg*.

width / height: the panorama size in pixels.
band_lo_deg / band_hi_deg / edge_deg: the textured elevation band.
amp:  the texture contrast on the backlight.
seed: integer seed for the azimuth noise (no ``None``).

Returns a float64 ``(height, width)`` image in ``[0, 1]``.

Ground truth: the standard deviation across azimuth of a row inside the band
exceeds that of a row outside it by more than 5x, and the log-log slope of the
azimuthal power spectrum of an in-band row is ``-2 +- 0.4`` (both pinned in the
tests).

**Raises** ``ValueError``: *width* / *height* outside their caps, a non-real /
string / bool parameter, a negative *amp*, a non-positive *edge_deg*, and a
band that does not satisfy ``-90 <= band_lo_deg < band_hi_deg <= 90``.

## 詳しい使い方ガイド

- [fly_vision ファミリ ガイド](../guides/fly_vision.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_fly_optomotor_steering](../../../../examples/poc_fly_optomotor_steering.py) — `py -3.11 examples/poc_fly_optomotor_steering.py`
- [poc_fly_vision](../../../../examples/poc_fly_vision.py) — `py -3.11 examples/poc_fly_vision.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fly_hex_resample](../sample/fly_hex_resample.md)

## 同カテゴリ(`stimulus`)

—

---
*Provenance: flyvision.py — FLYVISION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
