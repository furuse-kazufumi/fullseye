---
op: ticks
dim: annotate
category: plot
in: image2d × axes
out: image2d
examples: [annotate_gallery, annotate_paper_tour, poc_beam_modal_video, poc_camera_calibration, poc_camera_shake_deblur, poc_crack_width_timeseries, poc_dehazing, poc_dic_strain, poc_driving_decisions, poc_driving_traffic, poc_focus_stacking, poc_interferometry_step, poc_measurement_system_analysis, poc_motion_magnification, poc_panorama_drift, poc_particle_tracking, poc_photoelasticity, poc_pxrd_phase_peel, poc_registration_basin, poc_river_surface_velocity, poc_strain_history, poc_structure_4d_deterioration, poc_superresolution_limits, poc_template_tracking, poc_timelapse_growth, poc_traffic_counting, poc_wound_area_tracking, poc_xyt_event_surface]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# ticks — ANNOTATE `plot` op

- **データ種**: `image2d × axes` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.ticks(img, axes, xticks=None, yticks=None, color='neutral', width=1, tick_len=5, label=True, label_fmt='{:g}', font_size=11, font_path=None, scheme='okabe_ito', text_color=None, style=None)` (実装を直接呼ぶなら `import annotate; annotate.ticks(img, axes, xticks=None, yticks=None, color='neutral', width=1, tick_len=5, label=True, label_fmt='{:g}', font_size=11, font_path=None, scheme='okabe_ito', text_color=None, style=None)`、台帳から引くなら `opsannotate.get("ticks")`)

## 使い方

目盛りとその数値。**位置は閉形式**(:func:`data_to_pixel` そのもの)。

目盛りは枠の**外側**へ ``tick_len`` px 出す。ラベルは目盛りの外側に置くので、
軸の周りに余白が無ければ :func:`text_box` の境界検査が例外にする
(= 図の外に文字が消える事故が起きない)。

Raises
------
ValueError
    tick_len が負、ラベルが画像に収まらない。

## 詳しい使い方ガイド

- [figure_annotation ファミリ ガイド](../guides/figure_annotation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [dataset_conventions](../guides/dataset_conventions.md) — 学習データセット規約の知識 — COCO / YOLO / VOC と外観検査での落とし穴

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [annotate_gallery](../../../../examples/annotate_gallery.py) — `py -3.11 examples/annotate_gallery.py`
- [annotate_paper_tour](../../../../examples/annotate_paper_tour.py) — `py -3.11 examples/annotate_paper_tour.py`
- [poc_beam_modal_video](../../../../examples/poc_beam_modal_video.py) — `py -3.11 examples/poc_beam_modal_video.py`
- [poc_camera_calibration](../../../../examples/poc_camera_calibration.py) — `py -3.11 examples/poc_camera_calibration.py`
- [poc_camera_shake_deblur](../../../../examples/poc_camera_shake_deblur.py) — `py -3.11 examples/poc_camera_shake_deblur.py`
- [poc_crack_width_timeseries](../../../../examples/poc_crack_width_timeseries.py) — `py -3.11 examples/poc_crack_width_timeseries.py`
- [poc_dehazing](../../../../examples/poc_dehazing.py) — `py -3.11 examples/poc_dehazing.py`
- [poc_dic_strain](../../../../examples/poc_dic_strain.py) — `py -3.11 examples/poc_dic_strain.py`
- [poc_driving_decisions](../../../../examples/poc_driving_decisions.py) — `py -3.11 examples/poc_driving_decisions.py`
- [poc_driving_traffic](../../../../examples/poc_driving_traffic.py) — `py -3.11 examples/poc_driving_traffic.py`
- [poc_focus_stacking](../../../../examples/poc_focus_stacking.py) — `py -3.11 examples/poc_focus_stacking.py`
- [poc_interferometry_step](../../../../examples/poc_interferometry_step.py) — `py -3.11 examples/poc_interferometry_step.py`
- [poc_measurement_system_analysis](../../../../examples/poc_measurement_system_analysis.py) — `py -3.11 examples/poc_measurement_system_analysis.py`
- [poc_motion_magnification](../../../../examples/poc_motion_magnification.py) — `py -3.11 examples/poc_motion_magnification.py`
- [poc_panorama_drift](../../../../examples/poc_panorama_drift.py) — `py -3.11 examples/poc_panorama_drift.py`
- [poc_particle_tracking](../../../../examples/poc_particle_tracking.py) — `py -3.11 examples/poc_particle_tracking.py`
- [poc_photoelasticity](../../../../examples/poc_photoelasticity.py) — `py -3.11 examples/poc_photoelasticity.py`
- [poc_pxrd_phase_peel](../../../../examples/poc_pxrd_phase_peel.py) — `py -3.11 examples/poc_pxrd_phase_peel.py`
- [poc_registration_basin](../../../../examples/poc_registration_basin.py) — `py -3.11 examples/poc_registration_basin.py`
- [poc_river_surface_velocity](../../../../examples/poc_river_surface_velocity.py) — `py -3.11 examples/poc_river_surface_velocity.py`
- [poc_strain_history](../../../../examples/poc_strain_history.py) — `py -3.11 examples/poc_strain_history.py`
- [poc_structure_4d_deterioration](../../../../examples/poc_structure_4d_deterioration.py) — `py -3.11 examples/poc_structure_4d_deterioration.py`
- [poc_superresolution_limits](../../../../examples/poc_superresolution_limits.py) — `py -3.11 examples/poc_superresolution_limits.py`
- [poc_template_tracking](../../../../examples/poc_template_tracking.py) — `py -3.11 examples/poc_template_tracking.py`
- [poc_timelapse_growth](../../../../examples/poc_timelapse_growth.py) — `py -3.11 examples/poc_timelapse_growth.py`
- [poc_traffic_counting](../../../../examples/poc_traffic_counting.py) — `py -3.11 examples/poc_traffic_counting.py`
- [poc_wound_area_tracking](../../../../examples/poc_wound_area_tracking.py) — `py -3.11 examples/poc_wound_area_tracking.py`
- [poc_xyt_event_surface](../../../../examples/poc_xyt_event_surface.py) — `py -3.11 examples/poc_xyt_event_surface.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[text_box](../text/text_box.md) · [arrow](../pointer/arrow.md) · [leader_line](../pointer/leader_line.md) · [label_points](../pointer/label_points.md) · [crosshair](../pointer/crosshair.md) · [legend_box](../furniture/legend_box.md) · [color_bar](../furniture/color_bar.md) · [scale_bar](../furniture/scale_bar.md)

## 同カテゴリ(`plot`)

[axes_transform](axes_transform.md) · [data_to_pixel](data_to_pixel.md) · [nice_ticks](nice_ticks.md) · [axes_frame](axes_frame.md) · [grid_lines](grid_lines.md) · [plot_series](plot_series.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
