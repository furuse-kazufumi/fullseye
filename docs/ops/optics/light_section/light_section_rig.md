---
op: light_section_rig
dim: optics
category: light_section
in: 
out: table
gpu: なし
examples: [poc_light_section_step_weld_floor]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# light_section_rig — OPTICS `light_section` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.light_section_rig(theta_deg=30.0, standoff_mm=200.0, focal_px=2000.0, image_shape=(480, 640))` (実装を直接呼ぶなら `import lightsection; lightsection.light_section_rig(theta_deg=30.0, standoff_mm=200.0, focal_px=2000.0, image_shape=(480, 640))`、台帳から引くなら `opsoptics.get("light_section_rig")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

A light-section rig with known geometry (``table``): pinhole camera + laser plane.

世界座標: X = 光条に沿う向き、Y = 走査(搬送)の向き、Z = 上。レーザーは真上から
``Y = 0`` の面に光を立てる。カメラは Y–Z 面の中で光面から ``theta_deg`` 傾いた向きから、
距離 ``standoff_mm`` で原点を見る(画像の u = 世界の X、高さが増えると光条は画像の上へ)。
``K`` は主点が画像の中心(:mod:`camera` の画素中心の約束)。

World frame: X along the line, Y the scan direction, Z up; the laser plane is ``Y = 0``.
The camera looks at the origin from ``standoff_mm`` away, tilted ``theta_deg`` from the
laser plane in the Y–Z plane (camera x = world X). Returns ``{"kind": "light_section_rig",
"K", "R", "t" (world → camera, X_c = R X_w + t), "plane_normal", "plane_d" (laser plane in
camera coordinates, n·X_c = d), "theta_deg", "standoff_mm", "image_shape",
"plane_normal_world", "plane_d_world"}``.

Ground truth: the camera centre ``−Rᵀ t`` is at distance ``standoff_mm`` from the origin and
the plane's camera-frame equation maps world points with ``Y = 0`` to residual 0 (1e-12).

## ファミリ共通の入力契約(fail-closed)

optics の全 op は入力を検証してから計算する(黙って通さない):

- **単位は引数名に埋め込む** — `_mm` / `_um` / `_deg` / `_mrad`。mm と µm の取り違えは crash ではなく「もっともらしく間違った答え」なので、名前で防ぐ。大きさから単位を推測する処理は一切しない。
- **文字列は `ValueError`** — `float('50')` は成功してしまうため、未パースの設定値が長さとして通り抜ける(実測: `thin_lens('50', '200')` がもっともらしい 66.667 mm を返していた)。bool も `True == 1` の暗黙昇格として拒否。
- **complex / masked array は `ValueError`**(実数枠のみ。虚部の無言切り捨て・マスク剥がしを拒否)。**NaN/Inf は全入力で `ValueError`**。ただし宣言された欠測を除く: `bottle_fit_from_pattern` の `u_map` は測れなかった画素を NaN で受け取る(∞ は拒否)。
- **0 除算とその親戚を名指しで拒否**: 焦点距離 0・曲率半径 0・屈折率 <= 0・不透明な開口(全 0 なので正規化が 0/0)・総和 <= 0 の PSF・S0 = 0 の Stokes ベクトル・物体が前側焦点にある(像が無限遠)。
- **非有限を返すのは 2 op だけ、しかも契約として明記**: `depth_of_field` の過焦点距離以遠の `far_mm = inf`(それが過焦点距離の定義)と `gaussian_beam` のウエストでの `wavefront_radius_mm = inf`(平面波面の曲率半径)。どちらも有限の相棒(`far_is_infinite` / `curvature_per_mm`)を併せて返す。**それ以外の無言 NaN/Inf は内部で検出して `ValueError`** —「float64 が溢れた」と「答えが無限大」は別の主張なので、後者の顔で前者を返さない。ただし宣言された欠測を除く: `bottle_background_map` は光線が使えない画素(全反射など)の `u_mm` を NaN で返し、`valid` マスクと本数を併せて返す。
- **サイズ上限**: 生成格子は `optics.MAX_GRID`(4096)、供給された場/PSF/開口は `optics.MAX_FIELD_ELEMENTS`(2^24)、ABCD 素子列は `optics.MAX_SYSTEM_ELEMENTS`(1024)、Zernike は `MAX_ZERNIKE_TERMS`(512)/ `MAX_ZERNIKE_ORDER`(40)/ `MAX_ZERNIKE_BASIS`(2^25)。小さな引数から巨大な内部確保が起きる経路(実測: n_max=40 × 4096² で 108 GB)を fail-closed で塞ぐ。
- **物理的に不可能な状態も拒否**: 偏光度 > 1 の Stokes ベクトル、負の透過率、負の強度、n-|m| が奇数などの不正な Zernike 添字。

## 詳しい使い方ガイド

- [optics_imaging ファミリ ガイド](../guides/optics_imaging.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_light_section_step_weld_floor](../../../../examples/poc_light_section_step_weld_floor.py) — `py -3.11 examples/poc_light_section_step_weld_floor.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`light_section`)

[laser_line_center_centroid](laser_line_center_centroid.md) · [laser_line_center_gauss](laser_line_center_gauss.md) · [laser_line_center_steger](laser_line_center_steger.md) · [light_section_targets](light_section_targets.md) · [light_section_render](light_section_render.md) · [light_plane_calibrate](light_plane_calibrate.md) · [light_section_profile](light_section_profile.md) · [light_section_scan](light_section_scan.md)

---
*Provenance: lightsection.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
