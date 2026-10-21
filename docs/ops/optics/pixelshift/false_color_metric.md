---
op: false_color_metric
dim: optics
category: pixelshift
in: rgbimage
out: table
examples: [poc_pixel_shift]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# false_color_metric — OPTICS `pixelshift` op

- **データ種**: `rgbimage` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.false_color_metric(rgb, reference=None, border=0)` (実装を直接呼ぶなら `import pixelshift; pixelshift.false_color_metric(rgb, reference=None, border=0)`、台帳から引くなら `opsoptics.get("false_color_metric")`)

## 使い方

偽色の量: 色差(BT.601 の Cb, Cr)の大きさの統計。

*reference* が無ければ被写体を**無彩色**とみなし、各画素の √(Cb² + Cr²) そのものを偽色とする(白黒の配線・
織物・網点・解像チャートを撮った場合)。*reference* ``(H, W, 3)`` があれば、その色差との差の大きさを取る
(色のある被写体)。*border* 画素ぶん四辺を除いてから数える(端の差し戻しを数えないため)。

返り値 ``{"mean", "rms", "p99", "max", "fraction_over_0.02", "n_pixels"}``。値は入力の階調(0〜1 なら 0〜1)
の色差。0.02 は 8 bit で約 5 階調。

**Raises** ``ValueError``: rgb が ``(H, W, 3)`` の有限の実数でない / reference の形が違う / border が負・画像を
食い尽くす。

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

- [poc_pixel_shift](../../../../examples/poc_pixel_shift.py) — `py -3.11 examples/poc_pixel_shift.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`pixelshift`)

[pixel_shift_pattern](pixel_shift_pattern.md) · [pixel_shift_capture](pixel_shift_capture.md) · [pixel_shift_merge](pixel_shift_merge.md) · [pixel_shift_motion_mask](pixel_shift_motion_mask.md) · [pixel_shift_resolution_budget](pixel_shift_resolution_budget.md)

---
*Provenance: pixelshift.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
