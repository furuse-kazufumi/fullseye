---
op: vol_profile_line
dim: 3d
category: probe
in: voxel
out: pairs
examples: [wall_thickness_probe]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# vol_profile_line — 3D `probe` op

- **データ種**: `voxel` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_profile_line(vol, p0, p1, n=None, spacing=None, order=1)` (実装を直接呼ぶなら `import volprobe; volprobe.vol_profile_line(vol, p0, p1, n=None, spacing=None, order=1)`、台帳から引くなら `ops3d.get("vol_profile_line")`)
- **台帳経由の戻り値**: `fullseye.ledger.vol_profile_line(...)` は**宣言 out 型 `pairs` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.vol_profile_line.raw(...)`、または `volprobe.vol_profile_line` を直接呼ぶ。

## 使い方

Gray-value profile along the straight probe ``p0 -> p1``.

The segment between the two ``(z, y, x)`` voxel-space points (fractional
coordinates allowed) is sampled at ``n`` evenly-spaced positions with
spline interpolation of the given ``order`` (``scipy.ndimage.map_coordinates``;
1 = trilinear, the default). ``n`` defaults to one sample per unit of
*index-space* length (~1 voxel-step resolution regardless of spacing).

Parameters
----------
vol : (D, H, W) array — the volume (float64, finite; fail-closed otherwise).
p0, p1 : (z, y, x) — probe start / end, inside the volume on every axis.
n : int, optional — sample count (>= 2). Default ``ceil(index_length) + 1``.
spacing : (sz, sy, sx) or volio.VolumeMeta, optional — voxel size in mm.
order : int in [0, 5] — interpolation spline order (1 = trilinear).

Returns
-------
(t_mm, values) : two float64 arrays of length ``n``. ``t_mm[i]`` is the
*physical* distance of sample ``i`` from ``p0`` — the cumulative Euclidean
norm of the differences of the physical sample coordinates
(``index * spacing``), exact under anisotropic spacing; in plain voxel
units when ``spacing`` is None. ``values[i]`` is the interpolated gray
value.

Raises ``ValueError`` on a malformed volume, an endpoint outside the
volume, coincident endpoints (``p0 == p1``: no probe direction), ``n < 2``
or an invalid ``order`` / ``spacing``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [wall_thickness_probe](../../../../examples_3d/wall_thickness_probe.py) — `py -3.11 examples_3d/wall_thickness_probe.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`probe`)

[vol_edge_probe](vol_edge_probe.md) · [vol_wall_thickness](vol_wall_thickness.md)

---
*Provenance: volprobe.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
