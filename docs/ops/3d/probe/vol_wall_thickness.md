---
op: vol_wall_thickness
dim: 3d
category: probe
in: voxel
out: signal
examples: [wall_thickness_probe]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# vol_wall_thickness — 3D `probe` op

- **データ種**: `voxel` → `signal`
- **呼び出し**: `import volprobe; volprobe.vol_wall_thickness(vol, p0, p1, sigma=1.0, threshold=0.1, spacing=None)` (または `ops3d.get("vol_wall_thickness")`)

## 使い方

Wall thicknesses along the probe ``p0 -> p1`` — the industrial-CT

measurement itself.

Runs :func:`vol_edge_probe` (all polarities) and pairs consecutive
opposite-polarity edges *rising -> falling* in probe order: each pair is
one traversal of bright material (entry surface -> exit surface), and its
thickness is the difference of the two edges' ``t_mm`` (physical units —
mm with a spacing, voxels without). A probe crossing both walls of a pipe
therefore yields two thicknesses.

Edges that do not complete a rising -> falling pair (a probe starting or
ending inside material, consecutive same-polarity edges) are **ignored**,
not paired creatively — the count of returned thicknesses can be smaller
than ``len(edges) // 2``. Dark walls on a bright background need an
inverted volume (the pairing convention is bright material).

Returns a list of float thicknesses, in probe order (possibly empty).
Raises ``ValueError`` on the same malformed inputs as
:func:`vol_edge_probe`.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [wall_thickness_probe](../../../../examples_3d/wall_thickness_probe.py) — `py -3.11 examples_3d/wall_thickness_probe.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`probe`)

[vol_profile_line](vol_profile_line.md) · [vol_edge_probe](vol_edge_probe.md)

---
*Provenance: volprobe.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
