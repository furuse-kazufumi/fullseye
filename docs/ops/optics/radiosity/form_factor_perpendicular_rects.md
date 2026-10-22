---
op: form_factor_perpendicular_rects
dim: optics
category: radiosity
in: 
out: measurement
examples: [poc_pocket_interreflection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# form_factor_perpendicular_rects — OPTICS `radiosity` op

- **データ種**: `なし` → `measurement`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.form_factor_perpendicular_rects(h=1.0, w=1.0, length=1.0)` (実装を直接呼ぶなら `import radiosity3d; radiosity3d.form_factor_perpendicular_rects(h=1.0, w=1.0, length=1.0)`、台帳から引くなら `opsoptics.get("form_factor_perpendicular_rects")`)

## 使い方

View factor from a rectangle w × l to a rectangle h × l sharing the edge of length l at 90° (Howell's catalogue C-14, closed form).

With ``H = h/l`` and ``W = w/l`` (surface 1 is the ``w`` side, surface 2 the ``h``
side)::

    F_12 = 1/(π W) ( W atan(1/W) + H atan(1/H) − √(H²+W²) atan(1/√(H²+W²))
           + ¼ ln{ (1+W²)(1+H²)/(1+W²+H²)
                   · [W²(1+W²+H²)/((1+W²)(W²+H²))]^(W²)
                   · [H²(1+H²+W²)/((1+H²)(H²+W²))]^(H²) } )

``H = W = 1`` (two unit squares on a common edge) gives 0.200044. Reciprocity:
``w F_12 = h F_21`` (``form_factor_perpendicular_rects(w, h, l)`` is ``F_21``).

Returns the view factor ``F_12`` (``measurement``).

**Raises** ``ValueError``: a non-positive or non-finite length.

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

- [poc_pocket_interreflection](../../../../examples/poc_pocket_interreflection.py) — `py -3.11 examples/poc_pocket_interreflection.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`radiosity`)

[form_factor_parallel_rects](form_factor_parallel_rects.md) · [form_factor_polygons](form_factor_polygons.md) · [radiosity_patches](radiosity_patches.md) · [form_factor_matrix](form_factor_matrix.md) · [radiosity_progressive_3d](radiosity_progressive_3d.md) · [render_optscene_gi](render_optscene_gi.md)

---
*Provenance: radiosity3d.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
