---
op: chromatic_confocal_readout
dim: optics
category: confocal
in: table × table
out: table
examples: [poc_chromatic_confocal]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# chromatic_confocal_readout — OPTICS `confocal` op

- **データ種**: `table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.chromatic_confocal_readout(peaks, probe, layer_material=None) -> 'dict'` (実装を直接呼ぶなら `import chromconf; chromconf.chromatic_confocal_readout(peaks, probe, layer_material=None) -> 'dict'`、台帳から引くなら `opsoptics.get("chromatic_confocal_readout")`)

## 使い方

ピーク波長を較正表で高さ(z)へ戻し、2 ピークなら透明な層の厚さを出す。

peaks: :func:`chromatic_confocal_peaks` の返り値(dict の列)か、波長 [nm] の列。
probe: :func:`chromatic_confocal_probe` の dict。z は較正表を 3 次スプラインで逆引き(単調なので一意)。
layer_material: 上の 2 ピークのあいだの層の材料(材料表の名前か屈折率の数)。与えると厚さを返す:

  * ``thickness_paraxial_um`` = n(λ₂) × (z₂ − z₁) —— 見かけの厚さ × 屈折率(近軸)。λ₂ は下の面の
    ピーク波長(下の面に焦点を結んでいるのはこの色なので、群屈折率でなく位相屈折率)。
  * ``thickness_um`` = n(λ₂)(z₂ − z₁) / (1 − g/2)、g = 1/n − cos α/√(n² − sin²α)(平板が足す縦球面
    収差を厚さあたりで、応答のピークがその半分だけ深くずれる分を戻す。NA は λ₂ の較正の NA)。

返り値: ``heights_um``(各ピークの z、遠いほど大)/ ``wavelengths_nm`` / 層を指定したとき
``apparent_thickness_um`` / ``n_layer`` / ``na`` / ``thickness_paraxial_um`` / ``thickness_um``。
**Raises** ``ValueError``: 空のピーク列、較正の帯域の外の波長、層を指定したのにピークが 2 本でない
(薄すぎる膜は 1 本に潰れる —— 厚さを当て推量しない)。

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

- [poc_chromatic_confocal](../../../../examples/poc_chromatic_confocal.py) — `py -3.11 examples/poc_chromatic_confocal.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`confocal`)

[chromatic_confocal_probe](chromatic_confocal_probe.md) · [confocal_axial_response](confocal_axial_response.md) · [chromatic_confocal_spectrum](chromatic_confocal_spectrum.md) · [chromatic_confocal_peaks](chromatic_confocal_peaks.md) · [chromatic_confocal_limits](chromatic_confocal_limits.md)

---
*Provenance: chromconf.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
