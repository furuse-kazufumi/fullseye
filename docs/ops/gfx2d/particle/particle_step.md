---
op: particle_step
dim: gfx2d
category: particle
in: table
out: table
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# particle_step — GFX2D `particle` op

- **データ種**: `table` → `table`
- **呼び出し**: `import gfx2d; gfx2d.particle_step(state, dt, gravity=(0.0, 98.0), drag=0.0)` (または `opsgfx2d.get("particle_step")`)

## 使い方

Advance a particle state by ``dt`` seconds. Returns a **new** dict.

Semi-implicit (symplectic) Euler::

    v <- v + (g - drag*v) * dt
    p <- p + v * dt
    age <- age + dt

which makes the closed form exact and checkable: with ``gravity=(0,0)`` and
``drag=0`` the position after ``k`` steps is ``p0 + v0*k*dt``, and with drag
the speed is ``v0 * (1 - drag*dt)**k``. Both are compared as equalities in
the test suite.

``gravity`` is ``(gx, gy)`` in px/s^2, positive ``gy`` pulling **down** the
screen. The input dict is never mutated.

Raises ValueError: ``dt <= 0``; ``drag * dt >= 1``, which is the point where
explicit drag stops decaying the speed and starts reversing it — an
instability that otherwise shows up as particles flying backwards rather
than as an error.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`table` を入力に取れる)

[layer_stack](../composite/layer_stack.md) · [particle_render](particle_render.md)

## 同カテゴリ(`particle`)

[particle_emit](particle_emit.md) · [particle_render](particle_render.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
