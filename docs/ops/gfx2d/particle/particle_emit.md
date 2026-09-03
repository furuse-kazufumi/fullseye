---
op: particle_emit
dim: gfx2d
category: particle
in: 
out: table
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# particle_emit — GFX2D `particle` op

- **データ種**: `` → `table`
- **呼び出し**: `import gfx2d; gfx2d.particle_emit(count, seed, origin=(0.0, 0.0), spread=0.0, speed=(10.0, 40.0), direction=(0.0, 360.0), life=(0.5, 1.5), size=(1.0, 3.0), color='emphasis', scheme='okabe_ito')` (または `opsgfx2d.get("particle_emit")`)

## 使い方

Emit ``count`` particles from ``origin``, deterministically from ``seed``.

Returns the particle state as a dict of arrays::

    {"pos": (N,2) as (x, y), "vel": (N,2) px/s, "age": (N,), "life": (N,),
     "size": (N,) radius in px, "color": (N,4) straight rgba}

Ranges are ``(low, high)`` pairs sampled uniformly; ``direction`` is in
degrees measured clockwise from the +x axis (again because the row axis
points down). ``spread`` is the radius of the uniform disc the start
positions are jittered over.

All randomness comes from ``numpy.random.default_rng(seed)`` — the same seed
gives the same bytes, which the test suite pins with a SHA-256.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`table` を入力に取れる)

[layer_stack](../composite/layer_stack.md) · [particle_step](particle_step.md) · [particle_render](particle_render.md)

## 同カテゴリ(`particle`)

[particle_step](particle_step.md) · [particle_render](particle_render.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
