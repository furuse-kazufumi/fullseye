---
op: lens_field_profile
dim: optics
category: linescan
in: table
out: table
examples: [poc_tdi_linescan]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# lens_field_profile — OPTICS `linescan` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.lens_field_profile(system=None, image_heights_mm=None, frequencies_lp_mm=(10.0, 20.0, 35.0), grid=96, wavelength_um=None)` (実装を直接呼ぶなら `import linescan; linescan.lens_field_profile(system=None, image_heights_mm=None, frequencies_lp_mm=(10.0, 20.0, 35.0), grid=96, wavelength_um=None)`、台帳から引くなら `opsoptics.get("lens_field_profile")`)

## 使い方

像高ごとの**相対照度**と **MTF** を光線追跡で(``table``、有限距離の物体 = ラインスキャンの使い方)。

照度: Lambert の物点から射影立体角の一様格子で光線を出し、像面に届いた光束を数える(``_flux_trace``)。
像面の照度 = 光束 ÷ 像の面積要素(径方向の倍率 × 接線方向の倍率、像高の有限差分 —— 歪曲も入る)。
相対照度は 3 つの積に**厳密に**分かれる(どれも返す):

  ``relative_illumination = cos4 × pupil_factor × area_gain``

* ``cos4``: 物体側の主光線角(物点から近軸の入射瞳の中心へ)の cos⁴ —— 自然な周辺減光の閉形式
  (``optics.relative_illumination`` と同じ式)。
* ``pupil_factor`` = (光束の比) / cos4: 1 なら理想の cos⁴、1 未満は**口径食**(鏡筒・レンズの縁・面の
  球の端で光束が欠ける)、1 より大きいのは軸外で入射瞳が広がって見える(瞳収差)。
* ``area_gain`` = 軸上の面積要素 / その像高の面積要素: 樽型歪曲は像を縮めるので照度を**上げる**。

MTF: 通った光線の像面の座標から幾何光学の OTF の絶対値 |⟨exp(−2πi ν (x − x̄))⟩|(各光線は等しい光束)を、
サジタル(像高に直交、x)とタンジェンシャル(像高の向き、y)で。回折の MTF(円形瞳、近軸の作動 F 値)を
``mtf_diffraction`` に並べ、``mtf_sagittal`` / ``mtf_tangential`` は幾何 × 回折(積の近似 —— 収差が回折より
十分大きいか小さいときに良い)。ラインセンサは径方向に 1 列に並ぶので、**タンジェンシャル = 幅方向
(画素の並び)、サジタル = 流れ方向**。

*system*: ``raytrace.lens_system``(有限距離の物体、既定 = ``linescan_lens_example("linescan")``)。
*image_heights_mm*: 像高(既定 0〜28.672 mm = 8192 × 7 µm の半分を 9 点)—— 物体高は近軸倍率で割って出す。
像高の位置(面積要素)は主光線、主光線が通らなければ通った光線の重心で測る。
返り値 dict: ``image_height_mm`` / ``object_height_mm`` / ``chief_image_mm`` / ``distortion_percent`` /
``relative_illumination`` / ``cos4`` / ``pupil_factor`` / ``area_gain`` / ``flux_ratio`` /
``frequencies_lp_mm`` / ``mtf_sagittal`` / ``mtf_tangential``(像高 × 周波数)/ ``mtf_geometric_sagittal`` /
``mtf_geometric_tangential`` / ``mtf_diffraction`` / ``covered``(光線が 3 本以上届いたか)/
``magnification`` / ``working_fno``。届かない像高は照度 0・MTF NaN(``covered`` False)。

**Raises** ``ValueError``: 物体が無限遠(像の面積要素の扱いが違う —— ``optics.relative_illumination`` /
``lensimage`` を使う)/ 像高・周波数が非有限か負 / grid が [16, 256] の外 / 軸上で光線が 1 本も通らない /
窓を広げても光線が窓の縁を通る。

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

- [poc_tdi_linescan](../../../../examples/poc_tdi_linescan.py) — `py -3.11 examples/poc_tdi_linescan.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`linescan`)

[tdi_snr](tdi_snr.md) · [tdi_sync_mtf](tdi_sync_mtf.md) · [linescan_acquire](linescan_acquire.md) · [linescan_lens_columns](linescan_lens_columns.md) · [linescan_lens_example](linescan_lens_example.md)

---
*Provenance: linescan.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
