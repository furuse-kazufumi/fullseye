---
op: poisson_blend
dim: colortransport
category: blend
in: image2d × image2d × mask
out: image2d
examples: [color_transport]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# poisson_blend — COLORTRANSPORT `blend` op

- **データ種**: `image2d × image2d × mask` → `image2d`
- **呼び出し**: `import colortransport; colortransport.poisson_blend(src, dst, mask, offset=(0, 0))` (または `opscolortransport.get("poisson_blend")`)

## 使い方

勾配場を運ぶ継ぎ目なし合成(Pérez, Gangnet & Blake, SIGGRAPH 2003)。

``mask`` の内部で **``src`` の勾配**を保ちつつ、**境界で ``dst`` の値**に
一致する像を解く。よって出力は次の 2 つを**構成上**満たし、
それが正しさの検算になる:

* 内部のラプラシアンが ``src`` のラプラシアンと一致(解の残差ぶんまで)
* マスクの外は ``dst`` と**厳密に一致**(1 画素も触らない)

**貼った物の色は変わる。** それが目的の処理だが、「貼った物体の色を測る」
用途にそのまま流すと**測っているのは貼り先の色**になる。返り値は
``(blended, info)`` で、``info["changed_pixels"]`` と
``info["max_shift"]`` が実際にどれだけ動いたかを言う。

Parameters
----------
src : array_like
    貼る絵。``(H, W)`` または ``(H, W, C)``。
dst : array_like
    貼り先。``src`` 以上の大きさ。
mask : array_like
    ``src`` と同じ ``(H, W)`` の真偽値。**縁に接していてはいけない**
    (境界条件が取れないため明示的に拒否する)。
offset : (int, int)
    ``dst`` の中で ``src`` の左上を置く ``(row, col)``。

Returns
-------
(ndarray, dict)

## 背景知識ガイド(この op の手前にある物理・規約)

- [colorimetry](../../2d/guides/colorimetry.md) — 測色と分光の知識 — 色は「分光 × 光源 × 観測者」でしか決まらない

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [color_transport](../../../../examples/color_transport.py) — `py -3.11 examples/color_transport.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[histogram_match](../matching/histogram_match.md)

## 同カテゴリ(`blend`)

—

---
*Provenance: colortransport.py — COLORTRANSPORT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
