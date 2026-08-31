---
op: thin_lens
dim: optics
category: geometric
in: 
out: table
examples: [optics_imaging]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# thin_lens — OPTICS `geometric` op

- **データ種**: `` → `table`
- **呼び出し**: `import optics; optics.thin_lens(focal_mm=50.0, object_mm=200.0)` (または `opsoptics.get("thin_lens")`)

## 使い方

Gaussian thin-lens imaging: where the image lands and how big it is.

Solves ``1/f = 1/s_o + 1/s_i`` in the **real-is-positive** convention:
*object_mm* (``s_o``) is the lens-to-object distance and must be positive;
the returned ``image_mm`` (``s_i``) is positive for a real image on the far
side of the lens and **negative for a virtual image** on the object side
(which is what a diverging lens, ``focal_mm < 0``, always produces).

Returns a dict: ``image_mm`` · ``magnification`` ``m = -s_i/s_o``
(*negative = inverted*, the normal case for a real image; ``|m| < 1`` is a
demagnified, i.e. machine-vision, geometry) · ``object_mm`` and
``focal_mm`` echoed back so a table of results is self-describing ·
``working_distance_mm`` ``= s_o + s_i`` for a real image, the
object-to-sensor span a machine builder actually has to fit.

Ground truth it reproduces exactly (verified in ``tests/test_optics.py``):
``f = 50, s_o = 200`` gives ``s_i = 200/3 = 66.6667`` and ``m = -1/3``; at
``s_o = 2f`` the image is at ``2f`` with ``m = -1`` (the 1:1 conjugate);
the reciprocal identity ``1/f - 1/s_o - 1/s_i`` is 0 to machine precision
over the whole tested range.

**Raises** ``ValueError``: ``focal_mm == 0`` (not a lens), non-positive or
non-finite *object_mm*, and — explicitly, instead of returning ``inf`` —
``object_mm == focal_mm``, where the object sits at the front focal point
and images at infinity (a collimator, not an imaging conjugate).

Paraxial and thin: no aberration, no principal-plane separation. HALCON has
no equivalent (its camera model starts after the lens, at the projection).

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

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md)

## 同カテゴリ(`geometric`)

[abcd_matrix](abcd_matrix.md) · [abcd_trace](abcd_trace.md) · [depth_of_field](depth_of_field.md) · [relative_illumination](relative_illumination.md)

---
*Provenance: optics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
