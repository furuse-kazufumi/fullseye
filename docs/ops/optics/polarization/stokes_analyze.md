---
op: stokes_analyze
dim: optics
category: polarization
in: stokes
out: table
examples: [optics_imaging]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# stokes_analyze — OPTICS `polarization` op

- **データ種**: `stokes` → `table`
- **呼び出し**: `import optics; optics.stokes_analyze(stokes)` (または `opsoptics.get("stokes_analyze")`)

## 使い方

Read a Stokes vector: degree of polarisation, azimuth, ellipticity.

Returns a dict: ``intensity`` ``S0`` · ``dop`` degree of polarisation
``sqrt(S1^2+S2^2+S3^2)/S0`` · ``dolp`` linear part ``sqrt(S1^2+S2^2)/S0`` ·
``docp`` circular part ``|S3|/S0`` · ``azimuth_deg`` orientation of the
polarisation ellipse ``0.5*atan2(S2, S1)`` mapped into ``[0, 180)`` ·
``ellipticity_deg`` ``0.5*asin(S3/|S|)`` in ``[-45, +45]`` ·
``handedness`` one of ``"right"`` / ``"left"`` / ``"linear"``.

**``azimuth_deg`` and ``ellipticity_deg`` are ``None`` when they are
undefined** — azimuth when the linear part is exactly zero (circular or
unpolarised light has no orientation), ellipticity when the polarised part
is zero (unpolarised light has no ellipse). Returning 0.0 there would be a
fabricated angle; ``None`` says the truth and forces the caller to handle
it.

Ground truth it reproduces exactly: ``[1,1,0,0]`` -> dop 1, azimuth 0,
ellipticity 0, linear; ``[1,-1,0,0]`` -> azimuth 90; ``[1,0,1,0]`` ->
azimuth 45; ``[1,0,0,1]`` -> docp 1, ellipticity +45, right-handed;
``[1,0,0,0]`` -> dop 0 with both angles ``None``;
``[2,1,0,0]`` -> dop 0.5 (a partially polarised beam, which is exactly the
case Jones algebra cannot express).

**Raises** ``ValueError``: *stokes* is not a 1-D 4-vector, is complex /
masked / non-finite, is unphysical (``S0 < 0`` or degree of polarisation
above 1 — which is how you find out a Mueller matrix was not physical), or
has ``S0 == 0`` (no light at all: every ratio would be 0/0, and "the
polarisation of darkness" is not a question with an answer).

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

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md)

## 同カテゴリ(`polarization`)

[jones_element](jones_element.md) · [jones_apply](jones_apply.md) · [stokes_from_jones](stokes_from_jones.md) · [mueller_element](mueller_element.md) · [mueller_apply](mueller_apply.md)

---
*Provenance: optics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
