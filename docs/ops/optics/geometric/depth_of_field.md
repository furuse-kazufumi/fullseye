---
op: depth_of_field
dim: optics
category: geometric
in: 
out: table
examples: [optics_imaging]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# depth_of_field — OPTICS `geometric` op

- **データ種**: `` → `table`
- **呼び出し**: `import optics; optics.depth_of_field(focal_mm=50.0, f_number=8.0, subject_mm=2000.0, coc_mm=0.03)` (または `opsoptics.get("depth_of_field")`)

## 使い方

Photographic depth of field: near limit, far limit and hyperfocal distance.

The classical circle-of-confusion model. With ``H = f^2/(N*c) + f`` the
hyperfocal distance and ``s`` the focused subject distance:

``near = s*(H - f) / (H + s - 2f)`` and ``far = s*(H - f) / (H - s)``.

Returns a dict: ``near_mm`` · ``far_mm`` · ``depth_mm`` (``far - near``) ·
``hyperfocal_mm`` · ``far_is_infinite`` (a bool, so a caller never has to
test for ``inf`` by accident).

**``far_mm`` is ``inf`` at or beyond the hyperfocal distance, by contract,
not by accident** — focus at ``H`` and everything from ``H/2`` to infinity
is acceptably sharp, which is the whole point of the hyperfocal distance.
``depth_mm`` is then ``inf`` too. ``far_is_infinite`` says so explicitly,
and the identity ``near(H) == H/2`` is exact (verified in the tests).

*coc_mm* is the acceptable circle of confusion **in the image plane**: the
35 mm convention is 0.03 mm, a machine-vision rule of thumb is 1-2 pixel
pitches. It is a *choice*, not a property of the lens — halve it and the
depth of field halves with it, which is why two depth-of-field calculators
disagree.

Ground truth: ``f = 50, N = 8, c = 0.03`` gives ``H = 10466.67 mm``; at
``s = H`` the near limit is exactly ``H/2 = 5233.33 mm`` and the far limit
is ``inf``; the near/far limits bracket the subject for every ``s < H``.

**Raises** ``ValueError``: non-positive or non-finite *focal_mm*,
*f_number*, *subject_mm*, *coc_mm*; ``subject_mm <= focal_mm`` (an object
inside the front focal length cannot be imaged by this lens — see
:func:`thin_lens`); a hyperfocal distance that is not greater than the
focal length (a degenerate combination of ``N`` and ``c``).

Paraxial, thin, and blur-circle based: it ignores diffraction, which for
small apertures becomes the real resolution limit — compare with
:func:`mtf_diffraction` before trusting an ``N = 22`` calculation.

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

[thin_lens](thin_lens.md) · [abcd_matrix](abcd_matrix.md) · [abcd_trace](abcd_trace.md) · [relative_illumination](relative_illumination.md)

---
*Provenance: optics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
