---
op: text_box
dim: annotate
category: text
in: image2d × text
out: image2d
examples: [annotate_gallery, annotate_paper_tour, drawlist_deferred, poc_active_contours, poc_agv_fleet, poc_air_hockey_intercept, poc_ball_bounce, poc_beam_modal_video, poc_cad_scan_deviation, poc_camera_calibration, poc_camera_shake_deblur, poc_connectome_across_worms, poc_crack_width_timeseries, poc_ct_void_morphology, poc_dehazing, poc_dem_terrain, poc_diabolo_model_and_vision, poc_dic_strain, poc_driving_crossing, poc_driving_decisions, poc_driving_endless_map, poc_driving_lateral, poc_driving_longitudinal, poc_driving_pass, poc_driving_school, poc_driving_traffic, poc_driving_weather, poc_emva1288_sensor, poc_eye_to_brain, poc_focus_stacking, poc_food_cutting_measure, poc_granular_heap_repose, poc_graph_hierarchy_segmentation, poc_interferometry_step, poc_kendama, poc_leak_localization, poc_lidar_terrain_change, poc_livestock_body_volume, poc_machine_condition_fusion, poc_malecns_activity_wave, poc_measurement_system_analysis, poc_mesh_quality_repair, poc_motion_magnification, poc_multibeam_bathymetry, poc_panorama_drift, poc_particle_tracking, poc_peg_failure_recovery, poc_peg_insertion_tactile, poc_photoelasticity, poc_powder_scoop_pour, poc_print_warpage_risk, poc_pxrd_phase_peel, poc_registration_basin, poc_river_surface_velocity, poc_rotation_invariance_audit, poc_rover_slip_risk_path, poc_segmentation_gauntlet, poc_stockpile_volume, poc_strain_history, poc_structure_4d_deterioration, poc_superresolution_limits, poc_swarm_obstacle_from_flow, poc_table_tennis_bounce, poc_table_tennis_rally_loop, poc_table_tennis_spin, poc_tacscalib_sphere_lut, poc_template_tracking, poc_timelapse_growth, poc_traffic_counting, poc_ttc_rss, poc_world_terrain, poc_wound_area_tracking, poc_xyt_event_surface]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# text_box — ANNOTATE `text` op

- **データ種**: `image2d × text` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.text_box(img, text, xy, color='neutral', text_color=None, box_color=None, box_alpha=0.72, anchor='lt', pad=5, font_size=14, min_font_size=9, max_width=None, font_path=None, line_spacing=1.15, scheme='okabe_ito', min_contrast=2.0, border=0, border_color=None, style=None, wrap=True, bold=False, italic=False)` (実装を直接呼ぶなら `import annotate; annotate.text_box(img, text, xy, color='neutral', text_color=None, box_color=None, box_alpha=0.72, anchor='lt', pad=5, font_size=14, min_font_size=9, max_width=None, font_path=None, line_spacing=1.15, scheme='okabe_ito', min_contrast=2.0, border=0, border_color=None, style=None, wrap=True, bold=False, italic=False)`、台帳から引くなら `opsannotate.get("text_box")`)

## 使い方

下敷き(半透明の板)つきの文字。**はみ出しは黙って切らず例外**。

Parameters
----------
img : ndarray
    ``(H,W)`` か ``(H,W,C)``、float [0,1]。
text : str
    描く文字列。
xy : (x, y)
    アンカーの位置(**x=col, y=row**、row は下向き)。
color : str or sequence
    役割名または RGB。``text_color`` 未指定ならこれが**枠の色**として
    使われ、文字は読みやすい既定色になる。
text_color, box_color : str/sequence or None
    文字色・板の色。None なら既定(明るい文字 × 暗い板)。文字色が None の
    ときは、**実際に下に出る色**に対して明るい既定色が ``min_contrast`` を
    割る場合に限り、暗い文字(板の色)へ自動で切り替える ―― 板なし
    (``box_alpha=0``)で白地に置く目盛り・カラーバー・凡例のラベルが
    白に溶けないため。``text_color`` を明示したときは切り替えない
    (色は図の意味なので勝手に変えず、読めなければ例外にする)。
box_alpha : float
    板の不透明度 [0,1]。``0`` なら板を描かない(目盛りラベル向け)。
anchor : str
    ``'lt','ct','rt','lm','cm','rm','lb','cb','rb'`` の 9 通り。
pad : int
    板の内側余白[px]。
max_width : int or None
    文字の折り返し幅。None なら 1 行のまま。
wrap : bool
    False なら折り返さず 1 行のまま縮めて ``max_width`` に収める。
min_contrast : float
    文字と「実際にその下に出る色」のコントラスト比の下限。下回れば
    **ValueError**(背景と同化した文字は誰も気づけないので通さない)。
    **限界(正直に)**: 比べる相手は板の下の**平均色**なので、
    白と黒が半々に混じった写真の上に ``box_alpha=0`` で置くと、平均は
    中間灰になり検査を通ってしまう(白い部分の上の文字は読めない)。
    地が荒れている場所では ``box_alpha`` を上げて板を効かせること ――
    この検査は「板を忘れた」を捕まえるためのもので、
    「板があっても読めない」まで保証はしない。
border : int
    板の枠線の太さ(0 で枠なし)。色は ``border_color`` か ``color``。
style : dict or None
    枠線を引く :func:`imagedraw.draw_polyline` へ**素通し**する引数。

Returns
-------
ndarray
    同じ shape の新しい配列。

Raises
------
ValueError
    板が画像からはみ出す / 文字が収まらない / コントラスト不足 /
    未知の役割名・アンカー / 負の余白。

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
- [drawlist_deferred](../../../../examples/drawlist_deferred.py) — `py -3.11 examples/drawlist_deferred.py`
- [poc_active_contours](../../../../examples/poc_active_contours.py) — `py -3.11 examples/poc_active_contours.py`
- [poc_agv_fleet](../../../../examples/poc_agv_fleet.py) — `py -3.11 examples/poc_agv_fleet.py`
- [poc_air_hockey_intercept](../../../../examples/poc_air_hockey_intercept.py) — `py -3.11 examples/poc_air_hockey_intercept.py`
- [poc_ball_bounce](../../../../examples/poc_ball_bounce.py) — `py -3.11 examples/poc_ball_bounce.py`
- [poc_beam_modal_video](../../../../examples/poc_beam_modal_video.py) — `py -3.11 examples/poc_beam_modal_video.py`
- [poc_cad_scan_deviation](../../../../examples/poc_cad_scan_deviation.py) — `py -3.11 examples/poc_cad_scan_deviation.py`
- [poc_camera_calibration](../../../../examples/poc_camera_calibration.py) — `py -3.11 examples/poc_camera_calibration.py`
- [poc_camera_shake_deblur](../../../../examples/poc_camera_shake_deblur.py) — `py -3.11 examples/poc_camera_shake_deblur.py`
- [poc_connectome_across_worms](../../../../examples/poc_connectome_across_worms.py) — `py -3.11 examples/poc_connectome_across_worms.py`
- [poc_crack_width_timeseries](../../../../examples/poc_crack_width_timeseries.py) — `py -3.11 examples/poc_crack_width_timeseries.py`
- [poc_ct_void_morphology](../../../../examples/poc_ct_void_morphology.py) — `py -3.11 examples/poc_ct_void_morphology.py`
- [poc_dehazing](../../../../examples/poc_dehazing.py) — `py -3.11 examples/poc_dehazing.py`
- [poc_dem_terrain](../../../../examples/poc_dem_terrain.py) — `py -3.11 examples/poc_dem_terrain.py`
- [poc_diabolo_model_and_vision](../../../../examples/poc_diabolo_model_and_vision.py) — `py -3.11 examples/poc_diabolo_model_and_vision.py`
- [poc_dic_strain](../../../../examples/poc_dic_strain.py) — `py -3.11 examples/poc_dic_strain.py`
- [poc_driving_crossing](../../../../examples/poc_driving_crossing.py) — `py -3.11 examples/poc_driving_crossing.py`
- [poc_driving_decisions](../../../../examples/poc_driving_decisions.py) — `py -3.11 examples/poc_driving_decisions.py`
- [poc_driving_endless_map](../../../../examples/poc_driving_endless_map.py) — `py -3.11 examples/poc_driving_endless_map.py`
- [poc_driving_lateral](../../../../examples/poc_driving_lateral.py) — `py -3.11 examples/poc_driving_lateral.py`
- [poc_driving_longitudinal](../../../../examples/poc_driving_longitudinal.py) — `py -3.11 examples/poc_driving_longitudinal.py`
- [poc_driving_pass](../../../../examples/poc_driving_pass.py) — `py -3.11 examples/poc_driving_pass.py`
- [poc_driving_school](../../../../examples/poc_driving_school.py) — `py -3.11 examples/poc_driving_school.py`
- [poc_driving_traffic](../../../../examples/poc_driving_traffic.py) — `py -3.11 examples/poc_driving_traffic.py`
- [poc_driving_weather](../../../../examples/poc_driving_weather.py) — `py -3.11 examples/poc_driving_weather.py`
- [poc_emva1288_sensor](../../../../examples/poc_emva1288_sensor.py) — `py -3.11 examples/poc_emva1288_sensor.py`
- [poc_eye_to_brain](../../../../examples/poc_eye_to_brain.py) — `py -3.11 examples/poc_eye_to_brain.py`
- [poc_focus_stacking](../../../../examples/poc_focus_stacking.py) — `py -3.11 examples/poc_focus_stacking.py`
- [poc_food_cutting_measure](../../../../examples/poc_food_cutting_measure.py) — `py -3.11 examples/poc_food_cutting_measure.py`
- [poc_granular_heap_repose](../../../../examples/poc_granular_heap_repose.py) — `py -3.11 examples/poc_granular_heap_repose.py`
- [poc_graph_hierarchy_segmentation](../../../../examples/poc_graph_hierarchy_segmentation.py) — `py -3.11 examples/poc_graph_hierarchy_segmentation.py`
- [poc_interferometry_step](../../../../examples/poc_interferometry_step.py) — `py -3.11 examples/poc_interferometry_step.py`
- [poc_kendama](../../../../examples/poc_kendama.py) — `py -3.11 examples/poc_kendama.py`
- [poc_leak_localization](../../../../examples/poc_leak_localization.py) — `py -3.11 examples/poc_leak_localization.py`
- [poc_lidar_terrain_change](../../../../examples/poc_lidar_terrain_change.py) — `py -3.11 examples/poc_lidar_terrain_change.py`
- [poc_livestock_body_volume](../../../../examples/poc_livestock_body_volume.py) — `py -3.11 examples/poc_livestock_body_volume.py`
- [poc_machine_condition_fusion](../../../../examples/poc_machine_condition_fusion.py) — `py -3.11 examples/poc_machine_condition_fusion.py`
- [poc_malecns_activity_wave](../../../../examples/poc_malecns_activity_wave.py) — `py -3.11 examples/poc_malecns_activity_wave.py`
- [poc_measurement_system_analysis](../../../../examples/poc_measurement_system_analysis.py) — `py -3.11 examples/poc_measurement_system_analysis.py`
- [poc_mesh_quality_repair](../../../../examples/poc_mesh_quality_repair.py) — `py -3.11 examples/poc_mesh_quality_repair.py`
- [poc_motion_magnification](../../../../examples/poc_motion_magnification.py) — `py -3.11 examples/poc_motion_magnification.py`
- [poc_multibeam_bathymetry](../../../../examples/poc_multibeam_bathymetry.py) — `py -3.11 examples/poc_multibeam_bathymetry.py`
- [poc_panorama_drift](../../../../examples/poc_panorama_drift.py) — `py -3.11 examples/poc_panorama_drift.py`
- [poc_particle_tracking](../../../../examples/poc_particle_tracking.py) — `py -3.11 examples/poc_particle_tracking.py`
- [poc_peg_failure_recovery](../../../../examples/poc_peg_failure_recovery.py) — `py -3.11 examples/poc_peg_failure_recovery.py`
- [poc_peg_insertion_tactile](../../../../examples/poc_peg_insertion_tactile.py) — `py -3.11 examples/poc_peg_insertion_tactile.py`
- [poc_photoelasticity](../../../../examples/poc_photoelasticity.py) — `py -3.11 examples/poc_photoelasticity.py`
- [poc_powder_scoop_pour](../../../../examples/poc_powder_scoop_pour.py) — `py -3.11 examples/poc_powder_scoop_pour.py`
- [poc_print_warpage_risk](../../../../examples/poc_print_warpage_risk.py) — `py -3.11 examples/poc_print_warpage_risk.py`
- [poc_pxrd_phase_peel](../../../../examples/poc_pxrd_phase_peel.py) — `py -3.11 examples/poc_pxrd_phase_peel.py`
- [poc_registration_basin](../../../../examples/poc_registration_basin.py) — `py -3.11 examples/poc_registration_basin.py`
- [poc_river_surface_velocity](../../../../examples/poc_river_surface_velocity.py) — `py -3.11 examples/poc_river_surface_velocity.py`
- [poc_rotation_invariance_audit](../../../../examples/poc_rotation_invariance_audit.py) — `py -3.11 examples/poc_rotation_invariance_audit.py`
- [poc_rover_slip_risk_path](../../../../examples/poc_rover_slip_risk_path.py) — `py -3.11 examples/poc_rover_slip_risk_path.py`
- [poc_segmentation_gauntlet](../../../../examples/poc_segmentation_gauntlet.py) — `py -3.11 examples/poc_segmentation_gauntlet.py`
- [poc_stockpile_volume](../../../../examples/poc_stockpile_volume.py) — `py -3.11 examples/poc_stockpile_volume.py`
- [poc_strain_history](../../../../examples/poc_strain_history.py) — `py -3.11 examples/poc_strain_history.py`
- [poc_structure_4d_deterioration](../../../../examples/poc_structure_4d_deterioration.py) — `py -3.11 examples/poc_structure_4d_deterioration.py`
- [poc_superresolution_limits](../../../../examples/poc_superresolution_limits.py) — `py -3.11 examples/poc_superresolution_limits.py`
- [poc_swarm_obstacle_from_flow](../../../../examples/poc_swarm_obstacle_from_flow.py) — `py -3.11 examples/poc_swarm_obstacle_from_flow.py`
- [poc_table_tennis_bounce](../../../../examples/poc_table_tennis_bounce.py) — `py -3.11 examples/poc_table_tennis_bounce.py`
- [poc_table_tennis_rally_loop](../../../../examples/poc_table_tennis_rally_loop.py) — `py -3.11 examples/poc_table_tennis_rally_loop.py`
- [poc_table_tennis_spin](../../../../examples/poc_table_tennis_spin.py) — `py -3.11 examples/poc_table_tennis_spin.py`
- [poc_tacscalib_sphere_lut](../../../../examples/poc_tacscalib_sphere_lut.py) — `py -3.11 examples/poc_tacscalib_sphere_lut.py`
- [poc_template_tracking](../../../../examples/poc_template_tracking.py) — `py -3.11 examples/poc_template_tracking.py`
- [poc_timelapse_growth](../../../../examples/poc_timelapse_growth.py) — `py -3.11 examples/poc_timelapse_growth.py`
- [poc_traffic_counting](../../../../examples/poc_traffic_counting.py) — `py -3.11 examples/poc_traffic_counting.py`
- [poc_ttc_rss](../../../../examples/poc_ttc_rss.py) — `py -3.11 examples/poc_ttc_rss.py`
- [poc_world_terrain](../../../../examples/poc_world_terrain.py) — `py -3.11 examples/poc_world_terrain.py`
- [poc_wound_area_tracking](../../../../examples/poc_wound_area_tracking.py) — `py -3.11 examples/poc_wound_area_tracking.py`
- [poc_xyt_event_surface](../../../../examples/poc_xyt_event_surface.py) — `py -3.11 examples/poc_xyt_event_surface.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[arrow](../pointer/arrow.md) · [leader_line](../pointer/leader_line.md) · [label_points](../pointer/label_points.md) · [crosshair](../pointer/crosshair.md) · [legend_box](../furniture/legend_box.md) · [color_bar](../furniture/color_bar.md) · [scale_bar](../furniture/scale_bar.md) · [axes_frame](../plot/axes_frame.md)

## 同カテゴリ(`text`)

[measure_text](measure_text.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
