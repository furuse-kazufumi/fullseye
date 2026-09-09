# 成熟度台帳(Maturity)

**Language:** 日本語 / English column in the table.

この表は**手で書いていません**。`tools/gen_maturity.py` が能力ノート・例の台帳・
門の実体・`tests/` の中身から数えて出します。`tests/test_maturity.py` が
コミット済みの内容と生成物を突き合わせるので、古びると CI が落ちます。

*This ledger is generated, not written. Each row's status is derived from facts in the repository — which operators have tests, which linked examples an actual gate executes, and whether that example is driven by real measured data.*

## はしご(4 段)

| 段 | 意味 | Meaning |
|---|---|---|
| `research-prototype` | 実装はあるが、名指しの op に試験が揃っておらず、走る例も無い | Implemented, but not every named operator is exercised by a test and no linked example is executed by a gate. |
| `verified-synthetic` | 真値を持つ合成データで自動検証済み(名指しの op 全部に試験があるか、走る例がある) | Automatically verified against ground truth that is synthesised or computed in closed form. |
| `validated-public-real-data` | 公開された実写・実測データを使う例が、門で実際に走っている | At least one linked example that runs in CI is driven by real, publicly available measured data. |
| `validated-hardware` | 実機センサ・装置につないで検証済み(★CI に実機が無いのでこの段は決して出ない) | Validated against physical sensors or instruments. Never emitted: there is no hardware in CI. |

★ **`validated-hardware` は決して出ません。** CI に実機センサが無いからです。
段を先に書くのは順序が逆なので、生成器の側で構造的に到達不能にしてあります。

## 能力ごと

| 能力 | Capability | 分類 | 段 | op(名指しの試験/全) | 例(走る門) |
|---|---|---|---|---|---|
| [位置を合わせて重ねる](capabilities/align-and-stack.md) | Align and stack | 組み立てる | `verified-synthetic` | 4/4 | `poc_astro_photometry` synthetic → tests/test_poc_scripts_run.py<br>`poc_registration_basin` synthetic → tests/test_poc_scripts_run.py |
| [配列で方向を測り、距離と速度を分ける](capabilities/beamforming-and-range-doppler.md) | Beamform for direction, separate range from velocity | 波と信号 | `verified-synthetic` | 4/4 | `poc_multibeam_bathymetry` synthetic → tests/test_poc_scripts_run.py<br>`poc_bev_sensor_fusion` synthetic → tests/test_poc_scripts_run.py |
| [領域を切り出して、選んで、数える](capabilities/blob-and-region.md) | Segment regions, select them, and count | 見つける | `validated-public-real-data` | 3/4 | `poc_cell_counting` synthetic → tests/test_poc_scripts_run.py<br>`poc_particle_sizing` synthetic → tests/test_poc_scripts_run.py<br>`poc_real_coin_metrology` real → tests/test_poc_scripts_run.py |
| [色を測る(XYZ / Lab / 色差)](capabilities/colour-and-delta-e.md) | Measure colour (XYZ / Lab / colour difference) | 光と色 | `verified-synthetic` | 4/4 | `poc_white_balance` synthetic → tests/test_poc_scripts_run.py<br>`poc_pigment_unmixing` synthetic → tests/test_poc_scripts_run.py |
| [結果を人が読める図にする](capabilities/figures-and-annotation.md) | Turn results into figures people can read | 見せる | `verified-synthetic` | 3/3 | `poc_colormap_readability` synthetic → tests/test_poc_scripts_run.py<br>`poc_dem_terrain` synthetic → tests/test_poc_scripts_run.py |
| [地球規模の座標に載せる(ECEF と測地座標)](capabilities/geodetic-frames.md) | Put measurements on the Earth (ECEF and geodetic) | 測る | `verified-synthetic` | 2/2 | `poc_geodetic_height_frames` synthetic → tests/test_poc_scripts_run.py<br>`dem_geodesy_tour` synthetic → tests/test_example_scripts_run.py |
| [地の色を知らずに線と領域を描く(反転色)](capabilities/inverted-colour-overlays.md) | Draw lines and regions without knowing the background colour | 見せる | `verified-synthetic` | 3/3 | `annotate_paper_tour` synthetic → tests/test_example_scripts_run.py |
| [光の反射・屈折・干渉を計算する](capabilities/optics-and-materials.md) | Compute reflection, refraction and interference | 光と色 | `verified-synthetic` | 4/4 | `glass_and_mirror_optics` synthetic → tests/test_example_scripts_run.py<br>`appearance_structural_colour` synthetic → tests/test_example_scripts_run.py |
| [小さな点状の目標を見つけて、副画素で位置を出す](capabilities/point-target-detection.md) | Find small point-like targets and locate them below the pixel | 見つける | `verified-synthetic` | 4/4 | `poc_search_sweep_width` synthetic → tests/test_poc_scripts_run.py<br>`poc_astro_photometry` synthetic → tests/test_poc_scripts_run.py |
| [画像から寸法をサブピクセルで測る](capabilities/subpixel-2d-metrology.md) | Measure dimensions from an image, below the pixel | 測る | `verified-synthetic` | 4/4 | `poc_dimensional_inspection` synthetic → tests/test_poc_scripts_run.py<br>`poc_screw_thread_metrology` synthetic → tests/test_poc_scripts_run.py |
| [地形の傾き・水の流れ・見通しを測る](capabilities/terrain-and-visibility.md) | Slope, flow and line of sight on a terrain | 測る | `verified-synthetic` | 4/4 | `poc_dem_terrain` synthetic → tests/test_poc_scripts_run.py<br>`dem_terrain_analysis_tour` synthetic → tests/test_example_scripts_run.py |
| [画像の上に、文字と表を置きたい場所へ置く](capabilities/text-and-tables-on-images.md) | Put text and tables exactly where you want them on an image | 見せる | `verified-synthetic` | 6/6 | `annotate_paper_tour` synthetic → tests/test_example_scripts_run.py |
| [投影から断面を再構成する(CT)](capabilities/tomography-reconstruction.md) | Reconstruct slices from projections (CT) | 形にする | `verified-synthetic` | 3/4 | `poc_ct_fidelity` synthetic → tests/test_poc_scripts_run.py<br>`poc_ct_void_morphology` synthetic → tests/test_poc_scripts_run.py |
| [振動と音から異常を診断する](capabilities/vibration-and-acoustics.md) | Diagnose faults from vibration and sound | 波と信号 | `verified-synthetic` | 5/5 | `poc_bearing_diagnosis` synthetic → tests/test_poc_scripts_run.py<br>`poc_rail_corrugation` synthetic → tests/test_poc_scripts_run.py |
| [シルエットから立体を彫り出す(視体積交差)](capabilities/visual-hull-from-silhouettes.md) | Carve a solid out of silhouettes (visual hull) | 形にする | `verified-synthetic` | 4/4 | `space_carving` synthetic → examples3d.py (suite runs a smoke subset)<br>`poc_livestock_body_volume` synthetic → tests/test_poc_scripts_run.py |
| [3-D スキャンから体積・土量を出す](capabilities/volume-from-3d-scan.md) | Turn a 3-D scan into a volume | 測る | `verified-synthetic` | 3/4 | `poc_stockpile_volume` synthetic → tests/test_poc_scripts_run.py<br>`poc_lidar_terrain_change` synthetic → tests/test_poc_scripts_run.py |

## 例が実際に走っているか

| | 件数 |
|---|---|
| 2-D 台帳の例 | 200 |
| `tests/test_poc_scripts_run.py` が走らせる | 117 |
| `tests/test_example_scripts_run.py` が走らせる | 83 |
| **どの門も走らせていない** | **0** |

走らせない門は、実行時の壊れに盲目です。2026-09-06 に PoC 側で穴が見つかり
(31 本のうち 4 本が exit 1 のまま放置)、**2026-09-09 に同じ穴が 1 つ内側で
再演していた**ことが分かりました —— 門を作ったのに、対象を数え直さなかったので
`poc_*` 以外の 83 件が外に残り、そのうち 2 件が落ちていました。
どちらの門も `PYTHONPATH` を渡さずに走らせます(利用者と同じ条件)。
機械可読版は [`maturity.json`](maturity.json)。
