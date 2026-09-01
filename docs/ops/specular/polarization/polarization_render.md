---
op: polarization_render
dim: specular
category: polarization
in: image2d × image2d
out: polsweep
examples: [specular_photometric]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# polarization_render — SPECULAR `polarization` op

- **データ種**: `image2d × image2d` → `polsweep`
- **呼び出し**: `import specularity; specularity.polarization_render(diffuse, specular, angles_deg=(0.0, 45.0, 90.0, 135.0), azimuth_deg=0.0)` (または `opsspecular.get("polarization_render")`)

## 使い方

Forward model of a polariser sweep: turn a known split into the frames a polarisation camera would record. → (N, H, W).

``I(t) = 0.5 * diffuse + specular * cos^2(t - azimuth)``. The diffuse term is
treated as completely unpolarised, so it contributes half its radiance at
every analyser angle; the specular term is treated as completely linearly
polarised at *azimuth_deg*, so it follows Malus's law. Those are the two
assumptions :func:`polarization_separate` inverts, and rendering with them
is how the inversion gets a ground truth to be exact against.

Physically the assumptions hold near Brewster's angle for a dielectric and
fail at normal incidence; the module docstring says where. This operator
does not model the incidence angle at all — it takes the two radiance maps
you specify and produces the sweep they imply.

**Raises** ``ValueError``: *diffuse* / *specular* are not 2-D arrays of the
same shape, or are complex / masked / non-finite / string-typed; either has
a negative value (a negative radiance is not a scene); *angles_deg* has
fewer than 3 entries or does not determine the three unknowns.

## 詳しい使い方ガイド

- [specular_photometric ファミリ ガイド](../guides/specular_photometric.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [specular_photometric](../../../../examples/specular_photometric.py) — `py -3.11 examples/specular_photometric.py`

## 型が繋がる次の op(`polsweep` を入力に取れる)

[polarization_separate](polarization_separate.md) · [polarization_dolp_map](polarization_dolp_map.md) · [polarization_stokes](polarization_stokes.md)

## 同カテゴリ(`polarization`)

[polarization_separate](polarization_separate.md) · [polarization_dolp_map](polarization_dolp_map.md) · [polarization_stokes](polarization_stokes.md)

---
*Provenance: specularity.py — SPECULAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
