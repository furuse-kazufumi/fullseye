---
op: vol_edge_probe
dim: 3d
category: probe
in: voxel
out: table
examples: [wall_thickness_probe]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# vol_edge_probe — 3D `probe` op

- **データ種**: `voxel` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_edge_probe(vol, p0, p1, sigma=1.0, threshold=0.1, spacing=None, polarity='all')` (実装を直接呼ぶなら `import volprobe; volprobe.vol_edge_probe(vol, p0, p1, sigma=1.0, threshold=0.1, spacing=None, polarity='all')`、台帳から引くなら `ops3d.get("vol_edge_probe")`)

## 使い方

Sub-sample edges along the probe ``p0 -> p1``.

The profile (default sampling of :func:`vol_profile_line`) is smoothed
with a 1-D Gaussian of ``sigma`` **samples**, differentiated with respect
to the physical abscissa ``t_mm``, and local extrema of the derivative
magnitude are taken as edges. Each is refined to sub-sample precision by a
3-point parabolic fit; plateau twins closer than 1.5 samples are merged.

``threshold`` is an **absolute** derivative amplitude in intensity per
physical distance unit (per mm when ``spacing`` is given, per voxel
otherwise) — edges with ``|d gray / d t| < threshold`` at the peak are
discarded. It is *not* relative to the profile's own maximum: choose it
for your data's intensity range and spacing.

``polarity`` selects ``"positive"`` (rising, dark -> bright along the
probe), ``"negative"`` (falling) or ``"all"``.

Returns a list of dicts ordered by distance, each::

    {"t_mm":      physical distance of the edge from p0,
     "position":  (z, y, x) interpolated voxel coordinate of the edge,
     "amplitude": |d gray / d t| at the peak (intensity / distance unit),
     "polarity":  +1 rising, -1 falling}

Raises ``ValueError`` on the same malformed inputs as
:func:`vol_profile_line`, a negative / non-finite ``sigma`` or
``threshold``, or an unknown ``polarity``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [wall_thickness_probe](../../../../examples_3d/wall_thickness_probe.py) — `py -3.11 examples_3d/wall_thickness_probe.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [mesh_select_lod](../resolution/mesh_select_lod.md)

## 同カテゴリ(`probe`)

[vol_profile_line](vol_profile_line.md) · [vol_wall_thickness](vol_wall_thickness.md)

---
*Provenance: volprobe.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
