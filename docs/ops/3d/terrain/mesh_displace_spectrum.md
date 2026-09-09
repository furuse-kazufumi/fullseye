---
op: mesh_displace_spectrum
dim: 3d
category: terrain
in: mesh
out: mesh
examples: [itokawa_regolith_hero]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# mesh_displace_spectrum — 3D `terrain` op

- **データ種**: `mesh` → `mesh`
- **呼び出し**: `import fullseye as fs; fs.ledger.mesh_displace_spectrum(V, F, wavelengths=(0.06, 0.03, 0.015, 0.0075, 0.00375), amplitudes=(0.003, 0.00176, 0.00103, 0.0006, 0.00035), *, seed: 'int' = 0, nyquist: 'float' = 2.0, fade: 'float' = 1.0, weights=None, local_edge=None)` (実装を直接呼ぶなら `import render3d; render3d.mesh_displace_spectrum(V, F, wavelengths=(0.06, 0.03, 0.015, 0.0075, 0.00375), amplitudes=(0.003, 0.00176, 0.00103, 0.0006, 0.00035), *, seed: 'int' = 0, nyquist: 'float' = 2.0, fade: 'float' = 1.0, weights=None, local_edge=None)`、台帳から引くなら `ops3d.get("mesh_displace_spectrum")`)

## 使い方

Displace vertices along their normals with a **stated amplitude spectrum**, band-limited

per vertex → ``(V, F)``.

``displacement_i = Σ_k A_k · n_k(x_i) · gate_k(i) · w_k(i)`` with one seeded value-noise
octave ``n_k ∈ [−1, 1]`` per ``(wavelength_k, amplitude_k)`` pair (mesh units — the
Itokawa STL is in km, so the default is 3 m at 60 m falling as ``A ∝ λ^0.77`` to
0.35 m at 3.75 m), ``gate`` = :func:`displacement_band_weights` on *this* mesh
(an octave shorter than ``nyquist × local edge`` is not applied — it would alias into
facet noise; route it to :func:`bump_normals_fbm` instead) and ``weights`` = optional
``(N,)`` per-vertex or ``(K, N)`` per-octave-per-vertex factor in [0,1] (e.g. the
synthetic-relief weight ``1 − gate`` of the source model). The peak displacement at a
vertex is at most ``Σ_k A_k`` (tests pin it). Unlike :func:`mesh_displace_fbm` (one
amplitude, octave ratio 2, no band limit) every octave's amplitude is explicit.
Deterministic under ``seed``. Fail-closed on shapes / non-finite / negative values.

手順: (1) :func:`displacement_band_weights` で ``gate (K,N)`` を作る、(2) ``weights`` が
あれば掛ける、(3) オクターブ ``k`` ごとに seed 固定の value noise
``n_k(x) ∈ [-1,1]``(波長 ``λ_k``、格子オフセットはオクターブ番号で変える)を評価し
``Σ_k A_k · gate_k · n_k`` を法線方向の変位にする、(4) 面積重み付き頂点法線に沿って
頂点を動かす。返り値 ``(V' (N,3) float64, F のコピー)``。

- ``wavelengths`` / ``amplitudes``: 同じ長さ(1〜32 個)の正の列。メッシュ単位。
  個数不一致・空・33 個以上・負の振幅・``amplitudes=None`` は ``ValueError``。振幅 0 の
  オクターブは評価を飛ばす。
- ``nyquist`` / ``fade`` / ``local_edge``: 帯域ゲートの設定(``displacement_band_weights``
  と同じ)。
- ``weights``: ``(N,)`` なら全オクターブ共通、``(K,N)`` ならオクターブ別の係数。値は
  [0, 1] に限り、範囲外・形不一致は ``ValueError``。
- ``seed``: 同じ seed なら ``bump_normals_fbm`` と同じ格子を共有する(幾何で担えない
  オクターブを陰影側へ連続して渡せる)。

``mesh_displace_fbm`` との違いは、振幅をオクターブごとに明示すること、頂点ごとに
辺長で帯域を切ること。粗いメッシュに短波長を与えても折り返さず、単に無視される。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [itokawa_regolith_hero](../../../../examples_3d/itokawa_regolith_hero.py) — `py -3.11 examples_3d/itokawa_regolith_hero.py`

## 型が繋がる次の op(`mesh` を入力に取れる)

[mesh_to_voxel](../transform/mesh_to_voxel.md) · [mesh_to_points](../transform/mesh_to_points.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [ambient_occlusion](../render/ambient_occlusion.md) · [cast_shadow](../render/cast_shadow.md) · [supersample_mesh](../render/supersample_mesh.md) · [render_beauty](../render/render_beauty.md)

## 同カテゴリ(`terrain`)

[mesh_displace_fbm](mesh_displace_fbm.md) · [terrain_region_mask](terrain_region_mask.md) · [mesh_scatter_boulders](mesh_scatter_boulders.md) · [mesh_edge_lengths](mesh_edge_lengths.md) · [mesh_subdivide](mesh_subdivide.md) · [displacement_band_weights](displacement_band_weights.md) · [bump_normals_fbm](bump_normals_fbm.md)

---
*Provenance: render3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
