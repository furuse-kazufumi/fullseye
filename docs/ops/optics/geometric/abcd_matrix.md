---
op: abcd_matrix
dim: optics
category: geometric
in: table
out: matrix
examples: [optics_imaging]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# abcd_matrix — OPTICS `geometric` op

- **データ種**: `table` → `matrix`
- **呼び出し**: `import optics; optics.abcd_matrix(elements)` (または `opsoptics.get("abcd_matrix")`)

## 使い方

Compose a paraxial system into one 2x2 ray-transfer (ABCD) matrix.

*elements* is a sequence of ``(kind, *params)`` **in the order light meets
them** (the matrix product is formed right-to-left accordingly, so the list
reads like the optical layout, not like the algebra):

``("free", d_mm)`` free-space / homogeneous medium of length ``d >= 0`` ·
``("lens", f_mm)`` thin lens of focal length ``f != 0`` (negative =
diverging) · ``("mirror", r_mm)`` curved mirror of radius ``r`` in the
unfolded system (power ``-2/r``) · ``("interface", n1, n2)`` flat refracting
surface · ``("curved", n1, n2, r_mm)`` curved refracting surface.

Returns a ``(2, 2)`` float64 matrix acting on the ray state
``[y_mm, theta_rad]`` — feed it to :func:`abcd_trace`, which handles the
milliradian conversion at the API boundary.

Ground truth it reproduces exactly: a single free-space section is
``[[1, d], [0, 1]]``; ``det(M) = n_in / n_out``, hence **exactly 1** for any
system that starts and ends in the same medium (checked to ~1e-16 in the
tests, and the cheapest correctness self-check you have); two thin lenses
separated by ``d`` compose to the classical combined power
``1/f = 1/f1 + 1/f2 - d/(f1*f2)``; a lens sandwiched between two
free-space sections of length ``f`` gives the ``[[0, f], [-1/f, 0]]``
Fourier-transform geometry.

**Raises** ``ValueError``: an empty system, more than
:data:`MAX_SYSTEM_ELEMENTS` elements, an element that is not a sequence, an
unknown kind, the wrong parameter count for a kind, a negative free-space
distance (reverse the list instead of running light backwards), a zero
focal length or radius, a non-positive refractive index, or any non-finite
parameter.

HALCON: no equivalent (its optics stop at the pinhole camera model).

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

## 型が繋がる次の op(`matrix` を入力に取れる)

[abcd_trace](abcd_trace.md) · [mueller_apply](../polarization/mueller_apply.md)

## 同カテゴリ(`geometric`)

[thin_lens](thin_lens.md) · [abcd_trace](abcd_trace.md) · [depth_of_field](depth_of_field.md) · [relative_illumination](relative_illumination.md)

---
*Provenance: optics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
