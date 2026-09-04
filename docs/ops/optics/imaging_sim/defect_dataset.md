---
op: defect_dataset
dim: optics
category: imaging_sim
in: 
out: table
examples: [lens_defect_dataset_demo]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# defect_dataset — OPTICS `imaging_sim` op

- **データ種**: `` → `table`
- **呼び出し**: `import lensimage; lensimage.defect_dataset(n=8, system=None, size=(256, 256), kinds=('scratch', 'pits', 'crack', 'blob'), pixel_pitch_um=5.5, noise=True, seed=0, out_dir=None, zones=3, field_of_view=None, texture='orange_peel', max_defects=2)` (または `opsoptics.get("defect_dataset")`)

## 使い方

Synthetic defect images through a designed lens, with aligned masks (``table``).

Each of the *n* records draws 1–*max_defects* defects of the listed *kinds*
(``defectgen`` scratch / pits / crack / blob with parameters sampled from
*seed*) on a ``surface_texture`` background of *size*, renders the composite
with :func:`render_through_lens` (*system* defaults to the cemented doublet
of :func:`raytrace.example_system`; *noise* as there, default sensor
noise on), and pushes **each defect's mask through the same distortion
remap only** (nearest-neighbour, no blur) so the annotation sits where the
blurred defect actually landed. A record is
``{"image", "mask", "defects": [{"kind", "params", "bbox" [x, y, w, h],
"area"}], "lens": {"efl", "fno", "rms_spot_center", "rms_spot_corner",
"max_distortion_pct"}, "seed"}`` with arrays, or with file paths when
*out_dir* is given (``img_0000.png`` / ``mask_0000.png`` written with
``imgio.save`` plus a COCO-like ``annotations.json``: images, annotations
with bbox/area/params, categories). Deterministic for *seed*; a defect
that lands entirely outside the sensor after distortion is dropped from
the annotations rather than reported with an empty box.

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

- [mv_cables](../guides/mv_cables.md) — ケーブル（規格・速度・給電・ロボットケーブル）
- [mv_cameras](../guides/mv_cameras.md) — 産業用カメラメーカー（センサとの紐付け・ラインスキャン / TDI）
- [mv_frame_grabbers](../guides/mv_frame_grabbers.md) — フレームグラバーボード（光学系ではないが、撮れるかを決める）
- [mv_image_sensors](../guides/mv_image_sensors.md) — 産業用イメージセンサ（現行品中心）
- [mv_standards](../guides/mv_standards.md) — カメラインターフェースの規格と団体
- [virtual_machine_vision](../guides/virtual_machine_vision.md) — 仮想マシンビジョン — パラメータの洗い出しとオブジェクト模型

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lens_defect_dataset_demo](../../../../examples/lens_defect_dataset_demo.py) — `py -3.11 examples/lens_defect_dataset_demo.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md) · [spot_diagram](../design/spot_diagram.md)

## 同カテゴリ(`imaging_sim`)

[psf_from_opd](psf_from_opd.md) · [distortion_map](distortion_map.md) · [render_through_lens](render_through_lens.md) · [calibration_views](calibration_views.md)

---
*Provenance: lensimage.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
