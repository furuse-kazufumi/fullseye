---
op: sprite_blit
dim: gfx2d
category: sprite
in: rgba × rgba
out: rgba
examples: [gfx2d_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# sprite_blit — GFX2D `sprite` op

- **データ種**: `rgba × rgba` → `rgba`
- **呼び出し**: `import gfx2d; gfx2d.sprite_blit(dst, sprite, x=0, y=0, anchor='top_left', flip_x=False, flip_y=False, opacity=1.0)` (または `opsgfx2d.get("sprite_blit")`)

## 使い方

Composite ``sprite`` onto a copy of ``dst`` at integer ``(x, y)``.

``x`` is the column and ``y`` the row of the sprite's ``anchor`` point;
``anchor`` is one of ``"top_left"``, ``"top_right"``, ``"bottom_left"``,
``"bottom_right"``, ``"center"``.

**Out-of-bounds behaviour is to clip silently, and that is a decision, not
an oversight.** Half a sprite hanging off the edge of the screen is the
normal case in this family, and raising there would make the common path the
exceptional one. A sprite entirely outside returns ``dst`` unchanged. The
contrast with :func:`viewport` — which raises for the same situation — is
deliberate: a camera asking for pixels that do not exist is a bug in the
caller's arithmetic, a sprite walking off screen is not.

``x``/``y`` must be **integers**. Sub-pixel placement changes the picture
(it resamples), so it is :func:`sprite_transform`'s job and not a silent
rounding here.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gfx2d_scene](../../../../examples/gfx2d_scene.py) — `py -3.11 examples/gfx2d_scene.py`

## 型が繋がる次の op(`rgba` を入力に取れる)

[premultiply](../composite/premultiply.md) · [alpha_composite](../composite/alpha_composite.md) · [sprite_transform](sprite_transform.md) · [sprite_sheet_slice](sprite_sheet_slice.md) · [nine_slice](nine_slice.md)

## 同カテゴリ(`sprite`)

[sprite_synthesize](sprite_synthesize.md) · [sprite_transform](sprite_transform.md) · [sprite_sheet_slice](sprite_sheet_slice.md) · [nine_slice](nine_slice.md)

---
*Provenance: gfx2d.py — GFX2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
