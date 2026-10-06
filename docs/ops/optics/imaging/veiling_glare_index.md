---
op: veiling_glare_index
dim: optics
category: imaging
in: image2d × image2d × image2d
out: table
examples: [poc_veiling_glare]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# veiling_glare_index — OPTICS `imaging` op

- **データ種**: `image2d × image2d × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.veiling_glare_index(img, dark_mask, bright_mask)` (実装を直接呼ぶなら `import edgesfr; edgesfr.veiling_glare_index(img, dark_mask, bright_mask)`、台帳から引くなら `opsoptics.get("veiling_glare_index")`)

## 使い方

迷光(ベーリンググレア)指数: 黒い点の中心の明るさの平均 / 白地の明るさの平均(ISO 9358 の考え方)。

*dark_mask*(必須): 黒い点の**中心部**の画素(点の縁の ぼけ を含めない —— 縁を含めるとコアの ぼけ まで迷光に数える)。
*bright_mask*(必須): 白地の画素。★黒い点の大きさ(と光源の広さ)で答えが変わる: 裾が 1/(1+(r/r0)²) のレンズでは
黒い点の一辺を 16 → 256 px にすると同じレンズの指数が 19.6 % → 4.5 %(`poc_veiling_glare` 3 節)。点の大きさは結果と一緒に報告すること。

返り値 ``{"vgi": 比, "dark": 黒点の平均, "bright": 白地の平均, "n_dark", "n_bright"}``。暗電流・黒レベルは引かない
(引いた像を渡す)。

**Raises** ``ValueError``: 画像・マスクの形が違う / マスクが bool でない・空・重なる / 白地の平均が 0 以下。

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

## 背景知識ガイド(この op の手前にある物理・規約)

- [measurement_uncertainty](../../math/guides/measurement_uncertainty.md) — 計測の不確かさと校正の知識 — 「測れている」を主張するために
- [mv_cameras](../guides/mv_cameras.md) — 産業用カメラメーカー（センサとの紐付け・ラインスキャン / TDI）
- [virtual_machine_vision](../guides/virtual_machine_vision.md) — 仮想マシンビジョン — パラメータの洗い出しとオブジェクト模型

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_veiling_glare](../../../../examples/poc_veiling_glare.py) — `py -3.11 examples/poc_veiling_glare.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](wavefront_stats.md) · [sfr_from_edge](sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`imaging`)

[psf_to_mtf](psf_to_mtf.md) · [mtf_diffraction](mtf_diffraction.md) · [wavefront_stats](wavefront_stats.md) · [edge_spread](edge_spread.md) · [sfr_from_edge](sfr_from_edge.md) · [mtf50](mtf50.md)

---
*Provenance: edgesfr.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
