---
op: relative_illumination
dim: optics
category: geometric
in: 
out: pairs
examples: [optics_imaging]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# relative_illumination — OPTICS `geometric` op

- **データ種**: `` → `pairs`
- **呼び出し**: `import optics; optics.relative_illumination(half_angle_deg=20.0, samples=64, exponent=4.0)` (または `opsoptics.get("relative_illumination")`)

## 使い方

Natural vignetting: relative image-plane illuminance versus field angle.

The cosine-fourth law ``E(theta)/E(0) = cos(theta)^4`` — one cosine from the
inverse-square increase in distance to the off-axis point (twice), one from
the tilt of the exit pupil as seen from there, one from the tilt of the
image plane. Sampled uniformly in angle from 0 to *half_angle_deg*.

Returns an ``(samples, 2)`` float64 ``pairs`` array: column 0 the field
angle in degrees, column 1 the relative illuminance in [0, 1].

*exponent* exists because the fourth power is the *ideal symmetric* case:
a lens with pupil aberration, or a telecentric design, or one with a tilted
entrance pupil, falls off closer to ``cos^3`` (or is deliberately corrected
flatter still). Setting the exponent is how you say which lens you have —
it is not a fudge factor to be tuned after the fact.

Ground truth it reproduces exactly: ``cos^4(45 deg) = 1/4`` and
``cos^4(60 deg) = 1/16``, both to machine precision; the curve is 1.0 on
axis and monotonically decreasing.

**Raises** ``ValueError``: *half_angle_deg* outside ``(0, 90)`` — at 90
degrees the illuminance is exactly 0 and the "relative" curve carries no
information; *samples* outside ``[2, MAX_GRID]``; a negative or non-finite
*exponent*.

This is the *natural* falloff only. Mechanical vignetting (a stop clipping
the oblique beam) is a separate, lens-specific effect that no closed form
covers — measure it with a flat field.

## ファミリ共通の入力契約(fail-closed)

optics の全 op は入力を検証してから計算する(黙って通さない):

- **単位は引数名に埋め込む** — `_mm` / `_um` / `_deg` / `_mrad`。mm と µm の取り違えは crash ではなく「もっともらしく間違った答え」なので、名前で防ぐ。大きさから単位を推測する処理は一切しない。
- **文字列は `ValueError`** — `float('50')` は成功してしまうため、未パースの設定値が長さとして通り抜ける(実測: `thin_lens('50', '200')` がもっともらしい 66.667 mm を返していた)。bool も `True == 1` の暗黙昇格として拒否。
- **complex / masked array は `ValueError`**(実数枠のみ。虚部の無言切り捨て・マスク剥がしを拒否)。**NaN/Inf は全入力で `ValueError`**。
- **0 除算とその親戚を名指しで拒否**: 焦点距離 0・曲率半径 0・屈折率 <= 0・不透明な開口(全 0 なので正規化が 0/0)・総和 <= 0 の PSF・S0 = 0 の Stokes ベクトル・物体が前側焦点にある(像が無限遠)。
- **非有限を返すのは 2 op だけ、しかも契約として明記**: `depth_of_field` の過焦点距離以遠の `far_mm = inf`(それが過焦点距離の定義)と `gaussian_beam` のウエストでの `wavefront_radius_mm = inf`(平面波面の曲率半径)。どちらも有限の相棒(`far_is_infinite` / `curvature_per_mm`)を併せて返す。**それ以外の無言 NaN/Inf は内部で検出して `ValueError`** —「float64 が溢れた」と「答えが無限大」は別の主張なので、後者の顔で前者を返さない。
- **サイズ上限**: 生成格子は `optics.MAX_GRID`(4096)、供給された場/PSF/開口は `optics.MAX_FIELD_ELEMENTS`(2^24)、ABCD 素子列は `optics.MAX_SYSTEM_ELEMENTS`(1024)、Zernike は `MAX_ZERNIKE_TERMS`(512)/ `MAX_ZERNIKE_ORDER`(40)/ `MAX_ZERNIKE_BASIS`(2^25)。小さな引数から巨大な内部確保が起きる経路(実測: n_max=40 × 4096² で 108 GB)を fail-closed で塞ぐ。
- **物理的に不可能な状態も拒否**: 偏光度 > 1 の Stokes ベクトル、負の透過率、負の強度、n-|m| が奇数などの不正な Zernike 添字。

## 詳しい使い方ガイド

- [optics_imaging ファミリ ガイド](../guides/optics_imaging.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [optics_imaging](../../../../examples/optics_imaging.py) — `py -3.11 examples/optics_imaging.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

—

## 同カテゴリ(`geometric`)

[thin_lens](thin_lens.md) · [abcd_matrix](abcd_matrix.md) · [abcd_trace](abcd_trace.md) · [depth_of_field](depth_of_field.md)

---
*Provenance: optics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
