---
op: monogenic_phase
dim: quat
category: riesz
in: qimage
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# monogenic_phase — QUAT `riesz` op

- **データ種**: `qimage` → `image2d`
- **呼び出し**: `import quatimage; quatimage.monogenic_phase(qimage, display: 'bool' = False) -> 'np.ndarray'` (または `opsquat.get("monogenic_phase")`)

## 使い方

Local phase ``atan2(|R|, f)`` of a monogenic signal. → (H, W).

In ``[0, pi]`` — the monogenic phase is measured against the *magnitude* of
the Riesz vector, whose sign is carried by the orientation instead, so the
range is a half turn rather than a full one. That is the standard
convention (Felsberg & Sommer) and it is stated here because a caller
arriving from ``complexops.cx_phase`` (whose raw range is ``(-pi, pi]``) will
otherwise assume a full turn and see a "wrapped" map that is not wrapped.

``display=True`` maps ``[0, pi]`` to ``[0, 1]`` for viewing; the default is
``False`` — the **opposite** of ``cx_phase``'s default, deliberately,
because the consumers of this quantity in this module are numerical, and a
display scaling that arrives silently in a measurement is a factor of ``pi``
that nothing announces.

Phase is the quantity a translation shifts linearly, which is why the whole
motion half of this module reads it. For an edge, phase 0 means the peak of
a bright line, ``pi/2`` a step edge and ``pi`` the peak of a dark line — the
local *structure type*, independent of contrast.

**Raises** ``ValueError``: the input is not a valid quaternion field, or its
``k`` component is non-zero; *display* is not a bool.

## 詳しい使い方ガイド

- [quaternion_monogenic ファミリ ガイド](../guides/quaternion_monogenic.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image2d` を入力に取れる)

[riesz_transform](riesz_transform.md) · [monogenic_signal](monogenic_signal.md)

## 同カテゴリ(`riesz`)

[riesz_transform](riesz_transform.md) · [monogenic_signal](monogenic_signal.md) · [monogenic_amplitude](monogenic_amplitude.md) · [monogenic_orientation](monogenic_orientation.md)

---
*Provenance: quatimage.py — QUAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
