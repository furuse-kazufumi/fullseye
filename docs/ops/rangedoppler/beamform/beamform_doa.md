---
op: beamform_doa
dim: rangedoppler
category: beamform
in: beatcube
out: table
examples: [fmcw_range_doppler]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# beamform_doa — RANGEDOPPLER `beamform` op

- **データ種**: `beatcube` → `table`
- **呼び出し**: `import rangedoppler; rangedoppler.beamform_doa(cube, wavelength_m=0.0038934, element_spacing_m=None, angles_deg=None, range_bin=None, doppler_bin=None, n_targets=1, min_fraction=0.1, range_bin_m=None, velocity_bin_ms=None)` (または `opsrangedoppler.get("beamform_doa")`)

## 使い方

Direction(s) of arrival for one range-Doppler cell, in degrees.

:func:`beamform_delay_sum` followed by strict local-maximum picking on the
angle spectrum: the peaks are sorted by power, filtered at *min_fraction* of
the strongest, and the top *n_targets* returned. Two targets closer than the
array's beamwidth (``~0.886*lambda/(N_a*d)``, reported here as
``angular_resolution_deg``) merge into one lobe — delay-and-sum cannot
separate them, and this reports one peak rather than pretending otherwise.

When *range_bin_m* / *velocity_bin_ms* are supplied (from
:func:`fmcw_design`) the cell's range and velocity are converted too, giving
the complete ``(range, velocity, angle)`` detection this family exists to
produce; without them those two fields are ``None`` rather than a number in
unknown units.

Returns a ``dict``: ``angles_deg`` and ``powers`` (lists, strongest first),
``n_found``, ``grid_deg`` and ``spectrum`` (the full sweep), ``range_bin`` /
``doppler_bin`` (the cell used), ``range_m`` / ``velocity_ms``,
``angular_resolution_deg`` and ``max_unambiguous_angle_deg``.

**Raises** ``ValueError``: everything :func:`beamform_delay_sum` raises, plus
*n_targets* < 1 or a *min_fraction* outside ``[0, 1]``.

## 詳しい使い方ガイド

- [fmcw_range_doppler ファミリ ガイド](../guides/fmcw_range_doppler.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fmcw_range_doppler](../../../../examples/fmcw_range_doppler.py) — `py -3.11 examples/fmcw_range_doppler.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`beamform`)

[beamform_delay_sum](beamform_delay_sum.md)

---
*Provenance: rangedoppler.py — RANGEDOPPLER operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
