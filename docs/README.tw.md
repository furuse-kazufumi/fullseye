<!-- i18n-source-sha: 14023776078e -->
# Fullseye 文件索引

**Language:** [日本語](README.md) · [English](README.en.md) · [简体中文](README.zh.md) · [繁體中文](README.tw.md) · [한국어](README.ko.md) · [Deutsch](README.de.md)

> **請注意：**目前只有這份索引頁有譯文，它所連結的各篇文件暫時僅有日文版。


![六幕，全部是真實的運算子輸出：邊緣方向 / 連通域篩選 / 次像素量測 / SDF 轉網格 / 點雲分群 / 鏡頭離焦。](articles/assets/fullseye_hero.gif)

*六幕，全部是真實的運算子輸出：邊緣方向 / 連通域篩選 / 次像素量測 / SDF 轉網格 / 點雲分群 / 鏡頭離焦。*

**Fullseye**（開發代號 imgevolve）是一套 HALCON/HDevelop 等級的實用軟體：由 numpy 原生的影像處理運算子函式庫、HDevelop 風格的視覺化管線設計環境（Fullseye Studio），以及負責執行的 runtime（FullseyeEngine）三者組成。運算子約 **932** 個（以 registry 計），其中 **980/2313** 個真實的 HALCON 運算子做到 genuine（真正等效）的實作，涵蓋 48 個類別。

★ **在影像處理函式庫中少見，Fullseye 還內建「虛擬光學設計」** —— 薄/厚透鏡、光線追蹤、Seidel 像差與 PSF/MTF，並以阻尼最小二乘（Levenberg–Marquardt）最佳化透鏡處方本身（`optimize_lens`）。可從**設計成像系統，到用上述運算子檢查其成像，一氣呵成** —— 在半導體與精密計量中是明確的差異化。

> **請從這裡開始 → [GETTING_STARTED.md](GETTING_STARTED.md)（5 分鐘跑起來）**

> **功能一覽 → [CAPABILITIES.en.md](CAPABILITIES.en.md)**（依目的檢索）/ **PoC 提升的穩健性 → [HARDENING.en.md](HARDENING.en.md)**（發現、修復、設門）

---

<!-- poc-index:start -->

## PoC 系列 — 帶真值求解的 151 個實際問題

每一個都具有閉式或合成的真值，並必定附上零點(什麼都不做)。失敗方式分開計數，原因以對照組區分。完整列表: [examples/README.md](../examples/README.md)。

| 領域 | PoC 與其結論 |
|---|---|
| metrology (36) | [`poc_aoi_ct_traceability`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_aoi_ct_traceability.py) Matching Full 2-D Inspection to Sampled 3-D Inspection — A Grid Overlaps Itself<br>[`poc_asbuilt_wall_deviation`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_asbuilt_wall_deviation.py) As-built wall deviation — the bounding box measures the room's heading, not its size<br>[`poc_battery_electrode_breathing`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_battery_electrode_breathing.py) Measuring electrode breathing in microns — sub-pixel is not enough<br>[`poc_bone_trabecular_thickness`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bone_trabecular_thickness.py) Trabecular Thickness, Separation and Bone Volume Fraction — The Plate Model and the Direct Method Disagree on the Same Image<br>[`poc_bump_coplanarity`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bump_coplanarity.py) Bump coplanarity versus substrate warpage — subtract too much and the real defect goes with it<br>[`poc_cad_scan_deviation`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cad_scan_deviation.py) CAD-to-scan deviation inspection — the fit absorbs the defect and invents a dent<br>[`poc_crack_width`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_crack_width.py) Concrete Crack Width Is Thinner Than a Pixel — Counting Width Versus Integrating Width<br>[`poc_crack_width_timeseries`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_crack_width_timeseries.py) Measuring the Growth, Not the Width — Rephotographing the Same Wall Changes What the Error Is<br>[`poc_datacenter_thermal_field`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_datacenter_thermal_field.py) A 3-D Thermal Field from Sparse Sensors — The Grid's Blind Spot Erases a Rack<br>[`poc_dic_strain`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dic_strain.py) Strain From Speckle Images (DIC)<br>[`poc_dimensional_inspection`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dimensional_inspection.py) Dimensional Inspection of a Machined Part — Bias and Scatter as Two Numbers<br>[`poc_fiber_orientation`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fiber_orientation.py) Fibre Orientation Distribution — Angles Repeat Every 180 Degrees, and a Naive Mean Is 90 Degrees Off<br>[`poc_gear_tooth_metrology`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_gear_tooth_metrology.py) Gear Tooth Metrology — Eccentricity Is Order 1, Teeth Are Order z<br>[`poc_geodetic_height_frames`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_geodetic_height_frames.py) Coordinates Go Wrong by Tens of Metres While Still Looking Plausible<br>[`poc_interferometry_step`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_interferometry_step.py) How Accurately a White-Light Interferometer Measures a Nanometre Step<br>[`poc_livestock_body_volume`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_livestock_body_volume.py) Weighing an Animal from Silhouettes — The Error You Can Buy Down, and the One You Cannot<br>[`poc_metal_grain_size`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_metal_grain_size.py) Metallographic Grain Size — The Planimetric and Intercept Methods Fall Off Different Cliffs<br>[`poc_multibeam_bathymetry`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_multibeam_bathymetry.py) Why the Seafloor Smiles — A Wrong Sound-Speed Profile Breaks Only the Outer Beams<br>[`poc_particle_sizing`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_particle_sizing.py) Particle Size Distribution From Images — Merging and Edge Cuts Pull Opposite Ways and Cancel<br>[`poc_photoelasticity`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_photoelasticity.py) Stress by Photoelasticity — Unwrapping Fails First at the Isotropic Point<br>[`poc_pipe_wall_loss`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pipe_wall_loss.py) Pipe Wall Loss on the Unwrapped Map — The Axis You Choose Eats the Invert Corrosion<br>[`poc_real_coin_metrology`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_coin_metrology.py) Counting and Measuring Real Coins — A Correct Answer Is Not a Safe One<br>[`poc_scan_to_bim_asbuilt`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_scan_to_bim_asbuilt.py) As-built deviation of a room — the compromise pose is handed to the innocent element<br>[`poc_screw_thread_metrology`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_screw_thread_metrology.py) Pitch, Flank Angle and Pitch Diameter From a Thread Silhouette — Tilt Shows Up With Opposite Signs on the Two Flanks<br>[`poc_settlement_significance`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_settlement_significance.py) Did It Settle, or Did We Just Scan It Again — What Changes When You Cut at the Detection Limit<br>[`poc_star_astrometry`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_star_astrometry.py) To What Fraction of a Pixel Can a Star Be Located, and Where Is the Cliff?<br>[`poc_stockpile_volume`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_stockpile_volume.py) Stockpile Inventory — The Answer Is Fixed by the Ground Nobody Measured<br>[`poc_strain_history`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_strain_history.py) Strain History in a Creep Test — Cumulative or Direct?<br>[`poc_structure_4d_deterioration`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_structure_4d_deterioration.py) Re-surveying a structure year by year — when the vantage moves, decay appears to advance<br>[`poc_surface_roughness`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_surface_roughness.py) How Far Sa / Sq / Sz Survive Sampling and Cutoff<br>[`poc_thermal_radiometry`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermal_radiometry.py) A Thermal Image Is Not a Temperature Image — Emissivity, Reflection, and an Uncertainty That Does Not Add<br>[`poc_tree_ring_dendro`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tree_ring_dendro.py) Counting tree rings and extracting the width series — ring count and width correlation fail separately<br>[`poc_water_level`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_water_level.py) River Stage From an Oblique Photo — Ignoring Perspective Bends the Row-Number Error Into an Arc<br>[`poc_weld_bead_profile`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_weld_bead_profile.py) Weld Bead From a Laser-Triangulation Profile — The Sin of Writing 0 Where Nothing Was Measured<br>[`poc_weld_bead_scan_angle`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_weld_bead_scan_angle.py) Light-section scanning of a weld bead — resolution and occlusion share one knob<br>[`poc_wound_area_tracking`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_wound_area_tracking.py) Wound Area Over Time — Calibration Error Enters the Area Squared |
| analysis (19) | [`poc_attention_identities`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_attention_identities.py) Every Speedup Is the Same Arithmetic Regrouped: Scoring Attention with Identities<br>[`poc_beats_fringes_and_screens`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_beats_fringes_and_screens.py) One Beat — A Two-Slit Fringe and a Print Moire Are the Same Mathematics<br>[`poc_calipers_under_illusion`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_calipers_under_illusion.py) Auditing the Instrument with Illusions - Where a Caliper Fails, and Why<br>[`poc_complex_plane_fields`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_complex_plane_fields.py) Seeing the Complex Plane as an Area — When the Picture Proves the Theorem<br>[`poc_connectome_motor_bottleneck`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_connectome_motor_bottleneck.py) Motor Quantisation — Where the Command Dimension Collapses Between Brain and Muscle (the Fly's Neck and an RL Policy's Joints on One Scale)<br>[`poc_em_branch_territory`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_em_branch_territory.py) Branch Territories — Handing Every Voxel Its Nearest Branch, Not Just Its Distance, Makes Per-Branch Volume and Radius Countable<br>[`poc_endless_zoom_and_turning_solids`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_endless_zoom_and_turning_solids.py) Endless Zooms and Turning Solids: Making the Return Itself the Ground Truth<br>[`poc_four_dimensions_by_three_d_tools`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_four_dimensions_by_three_d_tools.py) Scoring Four-Dimensional Claims with Ordinary Three-Dimensional Operators<br>[`poc_geodetic_benchmarks_real`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_geodetic_benchmarks_real.py) There Are Two Kinds of Height, for Real — Putting a Height-Frame Mix-Up Under a Detector with 523 Published Survey Marks<br>[`poc_gravitational_lens_invariants`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_gravitational_lens_invariants.py) Scoring Gravitational-Lens Images with Ordinary Industrial Measurement Operators<br>[`poc_illusions_and_perpetual_drawing`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_illusions_and_perpetual_drawing.py) Scoring Endlessly Generated Pictures with Identities, Not with the Eye<br>[`poc_measurement_system_analysis`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_measurement_system_analysis.py) How Much of That Number Is Your Measuring - Gauge R&R and Measurement Uncertainty<br>[`poc_microns_brain_wave`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_microns_brain_wave.py) The MICrONS Brain Wave — How Much of the Measured Response Does the Wiring Explain in 1 mm^3 of Visual Cortex<br>[`poc_one_stroke_epicycles`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_one_stroke_epicycles.py) A Photograph as One Line, Drawn by Rotating Circles — Tone, Stipple, Tour, Fourier Series, G-code<br>[`poc_periodic_video_boundary`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_periodic_video_boundary.py) Testing the Periodic Boundary of Temporal Operators with a Seamless Loop<br>[`poc_theorems_as_pictures`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_theorems_as_pictures.py) Theorems as Gates — Apollonian Gaskets, Ford Circles, Geodesic Domes, Phyllotaxis, IFS, Space-Filling Curves<br>[`poc_vanishing_detail_and_morphing_area`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_vanishing_detail_and_morphing_area.py) The Exact Distance at Which Detail Vanishes, and the Area of a Changing Shape<br>[`poc_what_a_picture_cannot_check`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_what_a_picture_cannot_check.py) What a Picture Cannot Check — Scoring Dynamical Systems and Minimal Surfaces by Identity and Definition<br>[`poc_zernike_aberrations`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_zernike_aberrations.py) Scoring an Aberration as a Picture: Zernike Polynomials and the Point Spread Function |
| diagnostics (10) | [`poc_bearing_diagnosis`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bearing_diagnosis.py) Rolling-Bearing Diagnosis — How Deep in Noise Can It Still Be Caught?<br>[`poc_cold_chain_excursion`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cold_chain_excursion.py) The Cold-Chain Temperature Record — Where You Taped the Logger Is the Verdict<br>[`poc_fabric_defect`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fabric_defect.py) Defects Buried in a Periodic Background — What a Pooled ROC Hides<br>[`poc_machine_condition_fusion`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_machine_condition_fusion.py) Fusing thermal, vibration and geometry for machine health — three sensors, one fact<br>[`poc_prnu_camera_fingerprint`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_prnu_camera_fingerprint.py) Camera Fingerprints (PRNU): Which Camera Took This? — The Fingerprint Grows With Frame Count and Dies at the Save Button<br>[`poc_pv_thermal_survey`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pv_thermal_survey.py) Drone Thermography of a PV Plant — You Think You Are Measuring Temperature Difference, but You Are Measuring Wind and Viewing Angle<br>[`poc_solar_el_inspection`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_solar_el_inspection.py) Power loss from solar-cell EL images — dark is not the same as inactive<br>[`poc_solder_fillet_aoi`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_solder_fillet_aoi.py) Solder fillet AOI — three ring lights are a 3-level tilt quantiser, and 70 % of the fillet height sits in the dark<br>[`poc_thermography_ndt`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermography_ndt.py) Depth of a Subsurface Defect by Pulsed Thermography<br>[`poc_weld_radiograph_porosity`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_weld_radiograph_porosity.py) Porosity in Weld Radiographs — Closing With the Share of Images Misgraded by One Class |
| geometry (7) | [`poc_dfm_thickness_overhang`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dfm_thickness_overhang.py) Manufacturability from geometry alone — faces that sit on the threshold flip when you smooth them<br>[`poc_mesh_quality_repair`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_mesh_quality_repair.py) Repair the mesh, then measure — the defect count clears, the quantity does not<br>[`poc_pallet_load_utilization`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pallet_load_utilization.py) Pallet load utilization — one number gives voids and overhang the same value<br>[`poc_panorama_drift`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_panorama_drift.py) Chain the Neighbours Together and You Cannot Get Back Where You Started<br>[`poc_print_warpage_risk`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_print_warpage_risk.py) Warpage lives in the layer history — averaging the area throws the placement away<br>[`poc_symmetry_restoration`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_symmetry_restoration.py) Restoring what is missing by symmetry — the plane you assume is the lie you get<br>[`poc_xyt_event_surface`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_xyt_event_surface.py) The Arrival-Time Surface as an Isosurface in (x, y, t) |
| photometry (6) | [`poc_allsky_cloud_cover`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_allsky_cloud_cover.py) All-Sky Cloud Cover — Counting Pixels Is Biased by Position<br>[`poc_astro_photometry`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_astro_photometry.py) How Many Frames for What Photometric Precision?<br>[`poc_exoplanet_transit`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_exoplanet_transit.py) Exoplanet transit from aperture photometry — depth and duration fail separately<br>[`poc_nuclei_ploidy`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_nuclei_ploidy.py) Ploidy From Integrated Nuclear Intensity — Area Cannot Separate It<br>[`poc_real_sky_photometry`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_sky_photometry.py) Planting Known Stars in a Real Deep Field — Contamination Lies About the Measurement and the Confidence in the Same Direction<br>[`poc_solar_limb_darkening`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_solar_limb_darkening.py) Where Is the Edge of a Limb-Darkened Disc? The 50 % Rule Reads the Radius Small |
| separation (6) | [`poc_colocalization_crosstalk`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_colocalization_crosstalk.py) Colocalization lies under bleed-through — Pearson and Manders break in different places<br>[`poc_pigment_unmixing`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pigment_unmixing.py) Peeling Layers With Many Wavelengths — Underdrawing, Ground, Glaze and Fading, Truth in Hand<br>[`poc_polarization_specular`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_polarization_specular.py) Stripping Specular Reflection With Polarisation — Truth From the Fresnel Equations<br>[`poc_real_stain_unmix`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_stain_unmix.py) Separating a Real Immunostain by Colour — The Watchdog Was Blind to Exactly the Error It Should Catch<br>[`poc_recycling_sorting`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_recycling_sorting.py) Sorting mixed waste by material — what a preprocessor can erase is decided by algebra<br>[`poc_sea_ice_concentration`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_sea_ice_concentration.py) Sea-Ice Concentration — The Answer Depends on How Mixed Pixels Are Counted |
| calibration (5) | [`poc_camera_calibration`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_camera_calibration.py) A Reprojection Error of 0.05 px Guarantees Nothing<br>[`poc_fly_optomotor_steering`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fly_optomotor_steering.py) Holding a Course with a Fly's Optic Lobe Alone — From the Lamina to the Steering, Without Learning<br>[`poc_public_camera_heading`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_public_camera_heading.py) Where Is the Public Camera Looking — The Orientation of a Fixed Camera Whose Only Published Fact Is Its Position, from the Picture Itself<br>[`poc_public_camera_heading_real`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_public_camera_heading_real.py) Where Is the Public Camera Looking, for Real — Hunting the Sun in 807 Road Cameras, Fixing the Heading from One Sunset and Checking It Against the Road<br>[`poc_thermal_drift_metrology`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermal_drift_metrology.py) How Much Camera Thermal Drift Costs a Dimensional Measurement |
| segmentation (5) | [`poc_cell_counting`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cell_counting.py) Counting Overlapping Cells — Count, Over-Segmentation and Under-Segmentation as Three Numbers<br>[`poc_leaf_disease_area`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_leaf_disease_area.py) Leaf disease severity — colour axes survive the lighting; the grade is decided by the leaf mask and the edge convention<br>[`poc_mri_bias_field`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_mri_bias_field.py) MRI Bias Field and Tissue Area — Grey and White Matter Fail in Opposite Directions, and the Sum Hides It<br>[`poc_timelapse_growth`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_timelapse_growth.py) A Growth Time-Lapse as Space-Time Connected Components<br>[`poc_vegetation_cover`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_vegetation_cover.py) Counting Crop Green — Ground Truth as Per-Pixel Leaf Area Fraction |
| motion (4) | [`poc_particle_tracking`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_particle_tracking.py) Particle Tracking as a (row, column, time) Volume — Mislinks Come in Two Directions<br>[`poc_river_surface_velocity`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_river_surface_velocity.py) River surface velocity from an oblique video (LSPIV) — velocity error and discharge error are different numbers<br>[`poc_traffic_counting`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_traffic_counting.py) Counting in (x, y, t) — Vehicles Passed, Occlusion, and One Constant: L/V<br>[`poc_warehouse_flow`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_warehouse_flow.py) Where the Warehouse Dwell Came From — Count Waiting Without Its Kind and Everything Is Just Congestion |
| registration (4) | [`poc_change_detection_misreg`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_change_detection_misreg.py) Change detection under misregistration — false positives are edge bands, with a cliff<br>[`poc_print_registration`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_print_registration.py) Print Misregistration from the Sheet — A Halftone Is a Lattice, So the Answer Is Not Unique<br>[`poc_registration_basin`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_registration_basin.py) The Convergence Basin of Point-Cloud Registration — How Far Off Can the Initial Pose Be?<br>[`poc_template_tracking`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_template_tracking.py) Template Tracking Drifts Quietly Before It Ever Loses the Target |
| tomography_3d (4) | [`poc_battery_ct_degradation`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_battery_ct_degradation.py) Battery cell degradation by CT — the swelling shows outside, the cause stays inside<br>[`poc_battery_electrode_tortuosity`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_battery_electrode_tortuosity.py) Electrode tortuosity from CT — the rule of thumb only sees porosity<br>[`poc_ct_void_morphology`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_void_morphology.py) Collapsing joint voids into one number — what the number drops is the shape that matters<br>[`poc_die_tilt_tsv_overlay`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_die_tilt_tsv_overlay.py) Die tilt and TSV overlay from one CT — tilt fakes rotation too |
| visualization (4) | [`poc_eye_to_brain`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_eye_to_brain.py) What the Compound Eye Sees, and Where the Brain Answers — Trace an Ommatidium and the Response Travels the Wiring<br>[`poc_live4d`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_live4d.py) Living Tissue in 3D+t Without a Generator — Magnify, Flow, Interpolate, Height, All Against Truth<br>[`poc_malecns_activity_wave`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_malecns_activity_wave.py) Watching a Pulse Travel the Wiring on the 3-D Fly Brain — Connectome vs Degree-Preserving Shuffle<br>[`poc_video_cube`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_video_cube.py) A Clip as a Space-Time Cube — What Passed Where, and When, in One Solid |
| depth (3) | [`poc_focus_stacking`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_focus_stacking.py) Focus Stacking — The All-in-Focus Image and the Depth Map Are Different Things<br>[`poc_lightfield_depth`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lightfield_depth.py) Depth From a Light Field — A Light Field of Known Depth, Confronted With Its Nulls<br>[`poc_real_stereo_depth`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_stereo_depth.py) Measuring on a Real Stereo Photograph — Three Stumbles Synthesis Never Produces |
| imaging quality (3) | [`poc_colormap_readability`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_colormap_readability.py) Pseudo-colour changes what the reader decides — counting edges that are not there<br>[`poc_moire_screen`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_moire_screen.py) Can Display-Inspection Moire Be Told From Real Non-Uniformity?<br>[`poc_veiling_glare`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_veiling_glare.py) Veiling Glare Breaks Contrast Measurement — MTF Passes While Black Level Fails |
| restoration (3) | [`poc_camera_shake_deblur`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_camera_shake_deblur.py) How Much Camera Shake Can Be Undone — Make the Kernel, Apply It, Invert It, Compare<br>[`poc_dehazing`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dehazing.py) Removing Haze — Ground Truth From the Scattering Model, Transmission and Airlight Scored Apart<br>[`poc_real_deblur_honesty`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_deblur_honesty.py) Deblurring a Real Photograph — Three Rulers, Three Different Winners |
| terrain (3) | [`poc_crop_phenotyping`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_crop_phenotyping.py) Crop leaf area from above — folded by projection before it is ever hidden<br>[`poc_dem_terrain`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dem_terrain.py) Measuring Terrain — Slope, Flow and Insolation Against Closed Forms<br>[`poc_lidar_terrain_change`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lidar_terrain_change.py) Earthwork on a slope — align first and the scar gets shallower |
| decoding (2) | [`poc_barcode_1d`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_barcode_1d.py) Where a 1-D Barcode Stops Reading — Counting Misreads and Unreadables Separately<br>[`poc_matrix_code_reading`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_matrix_code_reading.py) Reading a Binary Matrix Code — Geometry Always Dies First |
| detection (2) | [`poc_real_defect_floor`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_defect_floor.py) How Faint a Defect Can Still Be Found — Planting a Known Truth in a Real Background<br>[`poc_search_sweep_width`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_search_sweep_width.py) Sweep Width — One Number Measured from Aerial Images Decides Whether the Search Works |
| forensics (2) | [`poc_forensics_roc`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_forensics_roc.py) Forgery Detection as an ROC — Not the One Image Found, but Detection at a Fixed False-Positive Rate<br>[`poc_fresco_craquelure`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fresco_craquelure.py) Craquelure networks — of three indicators, only junction degree breaks under imaging conditions |
| inspection (2) | [`poc_em_second_opinion`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_em_second_opinion.py) A Second Opinion for EM Connectome Proofreading — Membranes Belong Only on Label Boundaries<br>[`poc_print_layer_inspection`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_print_layer_inspection.py) Print Layer Inspection — Closing the Shape → Layer → Path → Image Loop and Catching Planted Defects by the Numbers |
| morphology (2) | [`poc_bilateral_asymmetry`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bilateral_asymmetry.py) Measuring Bilateral Asymmetry — The Symmetry Plane Gets Dragged by the Deformation<br>[`poc_vessel_network`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_vessel_network.py) Extracting a Vessel Network — Spurs, Overestimated Radii Near Branches, and a Fragile Exponent |
| optics (2) | [`poc_compound_eye`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_compound_eye.py) The Fly's Compound Eye Is a Light-Field Sensor — Neural Superposition Pays Only Up to the Knee<br>[`poc_fly_vision`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fly_vision.py) The Fly's Visual Front End as a Chain of Operators — Turning and Walking Through a Synthetic Sky, What Can and Cannot Be Read |
| perception_templates (2) | [`poc_bev_sensor_fusion`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bev_sensor_fusion.py) Fusing two sensors into a bird's-eye grid — a calibration that passes in pixels turns into metres at range<br>[`poc_safety_clearance`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_safety_clearance.py) Human-machine clearance — swap the body for a point, and the hazard vanishes with it |
| ranging (2) | [`poc_dtof_ranging`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dtof_ranging.py) Ranging by Counting Photons — How Many for How Many Millimetres?<br>[`poc_leak_localization`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_leak_localization.py) Digging Where the Sound Says — A Clean Correlation Still Digs in the Wrong Place |
| shape_descriptors (2) | [`poc_real_texture_invariance`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_texture_invariance.py) Rotating Real Textures — Rotation Invariance Holds Only Where It Is Not Needed<br>[`poc_rotation_invariance_audit`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_rotation_invariance_audit.py) Which Quantities Really Survive a Rotation — Auditing Invariance on a Real Coin |
| signal_processing (2) | [`poc_rail_corrugation`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_rail_corrugation.py) Measuring Rail with a Chord — At the Wavelengths Where the Transfer Function Is Zero, Any Amplitude Reads Zero<br>[`poc_web_roll_periodicity`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_web_roll_periodicity.py) Naming the Damaged Roller from a Period — You Run Out of Evidence Before You Reach the Cliff |
| verification (2) | [`poc_glyph_typo_detection`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_glyph_typo_detection.py) Finding and Fixing Wrong Characters Without Recognising Them — the Threshold Comes from Typeface Spread<br>[`poc_larval_connectome_reservoir`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_larval_connectome_reservoir.py) A Larval Connectome as a Reservoir Reads Digits — and the Wiring Is Not What Does It |
| vibration (2) | [`poc_beam_modal_video`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_beam_modal_video.py) Modal identification from video — frequency survives to the end, damping lies first<br>[`poc_motion_magnification`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_motion_magnification.py) Micro-Vibration of a Structure From Video — Does Motion Magnification Help You Measure? |
| colour (1) | [`poc_white_balance`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_white_balance.py) Colour Constancy (White Balance) — No Method Works, Only Conditions Do |
| imgmetrics (1) | [`poc_spc`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_spc.py) Is the Process in Control, and Is It Capable? — Statistical Process Control from Closed-Form Alone |
| rectification (1) | [`poc_document_scan`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_document_scan.py) Straightening a Hand-Held Document Photo — Keystone Correction and Shadow Removal Against Ground Truth |
| tomography (1) | [`poc_ct_fidelity`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_fidelity.py) Where CT Reconstruction Starts to Break as Projections Are Removed |
| super-resolution (1) | [`poc_superresolution_limits`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_superresolution_limits.py) Does Super-Resolution Add Information? Downsample With the Truth in Hand, Restore, Count |

<!-- poc-index:end -->

<!-- ops-index:start -->

## 尋找運算子

共有 **2,193 篇運算子說明**(呼叫方式、型別契約、HALCON 對應、參考文獻、來源)與 **58 篇族群指南**。依維度的入口:

**實測涵蓋**: 演化運算子 932/932、型別台帳 1240/1252、單行門面 `fullseye.<名稱>` 596/1245 —— **門面側僅涵蓋一半**。

**內容實測**: 2198 篇中，附有可執行範例的 **2132** 篇(66 篇沒有)，用法說明 120 字以上的 **2147** 篇(51 篇僅一行)。結構(呼叫形式、型別、可銜接運算子)2198 篇全有。

| 維度 | 運算子數 | 入口 |
|---|---:|---|
| `2d` | 949 | [INDEX](ops/2d/INDEX.md) |
| `3d` | 372 | [INDEX](ops/3d/INDEX.md) |
| `optics` | 131 | [INDEX](ops/optics/INDEX.md) · [guide](ops/optics/guides/optics_imaging.md) |
| `math` | 55 | [INDEX](ops/math/INDEX.md) · [guide](ops/math/guides/math_metrology.md) |
| `annotate` | 51 | [INDEX](ops/annotate/INDEX.md) · [guide](ops/annotate/guides/figure_annotation.md) |
| `gfx2d` | 44 | [INDEX](ops/gfx2d/INDEX.md) |
| `oned` | 42 | [INDEX](ops/oned/INDEX.md) |
| `reprconv` | 42 | [INDEX](ops/reprconv/INDEX.md) |
| `generative` | 30 | [INDEX](ops/generative/INDEX.md) · [guide](ops/generative/guides/generative_art.md) |
| `conngraph` | 28 | [INDEX](ops/conngraph/INDEX.md) · [guide](ops/conngraph/guides/conngraph.md) |
| `piv` | 26 | [INDEX](ops/piv/INDEX.md) · [guide](ops/piv/guides/piv_displacement.md) |
| `dem` | 25 | [INDEX](ops/dem/INDEX.md) · [guide](ops/dem/guides/dem_terrain_analysis.md) |
| `imgmetrics` | 24 | [INDEX](ops/imgmetrics/INDEX.md) · [guide](ops/imgmetrics/guides/image_difference_metrics.md) |
| `printpath` | 23 | [INDEX](ops/printpath/INDEX.md) · [guide](ops/printpath/guides/printpath.md) |
| `acoustics` | 20 | [INDEX](ops/acoustics/INDEX.md) · [guide](ops/acoustics/guides/acoustic_condition_monitoring.md) |
| `quat` | 19 | [INDEX](ops/quat/INDEX.md) · [guide](ops/quat/guides/quaternion_monogenic.md) |
| `lightfield` | 17 | [INDEX](ops/lightfield/INDEX.md) · [guide](ops/lightfield/guides/lightfield_depth.md) |
| `photon` | 17 | [INDEX](ops/photon/INDEX.md) · [guide](ops/photon/guides/photon_timeresolved.md) |
| `tomography` | 17 | [INDEX](ops/tomography/INDEX.md) |
| `flyvision` | 16 | [INDEX](ops/flyvision/INDEX.md) · [guide](ops/flyvision/guides/fly_vision.md) |
| `imgforensics` | 16 | [INDEX](ops/imgforensics/INDEX.md) |
| `shape2d` | 16 | [INDEX](ops/shape2d/INDEX.md) · [guide](ops/shape2d/guides/shape_description_2d.md) |
| `shapestat` | 16 | [INDEX](ops/shapestat/INDEX.md) · [guide](ops/shapestat/guides/shape_statistics.md) |
| `videostream` | 16 | [INDEX](ops/videostream/INDEX.md) · [guide](ops/videostream/guides/video_streaming.md) |
| `astrostack` | 14 | [INDEX](ops/astrostack/INDEX.md) |
| `live4d` | 14 | [INDEX](ops/live4d/INDEX.md) · [guide](ops/live4d/guides/live4d.md) |
| `measure1d` | 14 | [INDEX](ops/measure1d/INDEX.md) · [guide](ops/measure1d/guides/subpixel_measuring.md) |
| `spc` | 14 | [INDEX](ops/spc/INDEX.md) |
| `specular` | 13 | [INDEX](ops/specular/INDEX.md) · [guide](ops/specular/guides/specular_photometric.md) |
| `profile` | 12 | [INDEX](ops/profile/INDEX.md) · [guide](ops/profile/guides/profile_metrology.md) |
| `colortransport` | 11 | [INDEX](ops/colortransport/INDEX.md) |
| `volcolor` | 11 | [INDEX](ops/volcolor/INDEX.md) |
| `blob` | 10 | [INDEX](ops/blob/INDEX.md) · [guide](ops/blob/guides/blob_analysis.md) |
| `llmcore` | 10 | [INDEX](ops/llmcore/INDEX.md) · [guide](ops/llmcore/guides/llmcore.md) |
| `geocam` | 9 | [INDEX](ops/geocam/INDEX.md) · [guide](ops/geocam/guides/geocam.md) |
| `interferometry` | 9 | [INDEX](ops/interferometry/INDEX.md) · [guide](ops/interferometry/guides/coherence_scanning.md) |
| `motionmag` | 9 | [INDEX](ops/motionmag/INDEX.md) · [guide](ops/motionmag/guides/motion_magnification.md) |
| `rangedoppler` | 8 | [INDEX](ops/rangedoppler/INDEX.md) · [guide](ops/rangedoppler/guides/fmcw_range_doppler.md) |
| `emproof` | 7 | [INDEX](ops/emproof/INDEX.md) · [guide](ops/emproof/guides/emproof.md) |
| `roughness` | 6 | [INDEX](ops/roughness/INDEX.md) · [guide](ops/roughness/guides/surface_roughness.md) |
| `videocube` | 6 | [INDEX](ops/videocube/INDEX.md) · [guide](ops/videocube/guides/videocube.md) |
| `cadmap` | 4 | [INDEX](ops/cadmap/INDEX.md) |

依名稱搜尋請用 `py -3.11 imgevolve.py ops --search edge`;全部運算子的對照表見 [OP_CATALOG.md](OP_CATALOG.md)，跨維度入口見 [ops/INDEX.md](ops/INDEX.md)。

**供 AI 檢索**: 機器可讀索引 [`OP_INDEX.json`](OP_INDEX.json)，用法見 [AI_RAG_GUIDE.md](AI_RAG_GUIDE.md)。

<!-- ops-index:end -->

## 用法（給使用者 —— 先看這四篇）

| 文件 | 內容 |
|---|---|
| **[GETTING_STARTED.md](GETTING_STARTED.md)** | 5 分鐘上手：安裝 → 第一條管線 → 在 Studio／CLI／程式碼中執行 → 看結果 |
| **[INSTALL.md](INSTALL.md)** | 環境建置完整指南：前置條件、`pip install -e .` 與各 extras 的取捨、Windows／Linux 安裝程式、最小組態與嵌入式整合、疑難排解 |
| **[STUDIO_GUIDE.md](STUDIO_GUIDE.md)** | Fullseye Studio 完整指南：三面板、運算子瀏覽器、單步執行、參數旋鈕、Inspector、感知面板、命令面板、快速鍵、匯出 |
| **[ENGINE.md](ENGINE.md)** | FullseyeEngine（設計 → 執行）：全部方法、在 Python 中的用法、CLI `run`、從其他專案呼叫 |

---

## 運算子 / API 參考

| 文件 | 內容 |
|---|---|
| [OPERATORS.md](OPERATORS.md) | 全部 897 個運算子的目錄（48 個類別，依 sort 分組，並列出 HALCON／OpenCV／scikit-image／MATLAB 的對應 API） |
| [EXAMPLES.md](EXAMPLES.md) | 逐個運算子的範例程式碼（附上其他函式庫中的等價呼叫） |
| [OP_INDEX.json](OP_INDEX.json) | 機器可讀的運算子索引（用 `imgevolve.py index` 重新產生） |
| [ADDING_OPS.md](ADDING_OPS.md) | 如何新增運算子（演化、codegen、目錄與索引都會自動跟上） |
| [../examples/README.md](../examples/README.md) | 可直接執行的端對端範例程式集 |

## 感知堆疊（機器人 / 視覺）

| 文件 | 內容 |
|---|---|
| [PERCEPTION.md](PERCEPTION.md) | 感知堆疊單頁速查（stereo／terrain／detect／registration／pose／flow／motion） |
| [PERCEPTION_REALDATA.md](PERCEPTION_REALDATA.md) | 在實拍影片片段上的量測結果（影片 I/O ＋ 誠實列出的實測數值） |

## HALCON 對等性 / 涵蓋率（誠實揭露 honest disclosure）

| 文件 | 內容 |
|---|---|
| [HALCON_PARITY.md](HALCON_PARITY.md) | genuine（真正等效）實作的進度（980/2313）：不是「只有名字一樣」，而是確實做得到同樣的處理 |
| [HALCON_COVERAGE.md](HALCON_COVERAGE.md) | 實際抓取官方參考手冊（v2605）後量出的涵蓋率 |
| [LIB_COVERAGE.md](LIB_COVERAGE.md) | 跨多個函式庫的涵蓋情形（納入 HALCON 以外具特色的運算子） |
| [PARITY_CROSSBACKEND.md](PARITY_CROSSBACKEND.md) | 以多個獨立實作（scipy／cv2／skimage）之間的跨後端一致性，來佐證對等性 |

## 品質 / 來源履歷 / 重現

| 文件 | 內容 |
|---|---|
| [ACCURACY_BENCH.md](ACCURACY_BENCH.md) | 常設精度表：演化出的 champion 對上 null 基準（holdout） |
| [CHAIN_FUZZ.md](CHAIN_FUZZ.md) | 鏈式 fuzzer——把運算子串成鏈條施加擾動的第三層品質保證（擴散 → 收斂 → 最小重現） |
| [EVOLUTION_ENVIRONMENT.md](EVOLUTION_ENVIRONMENT.md) | 演化式演算法開發環境（擴散 → 收縮 → 晉升；counterfactual utility 閘門，以及連接兩個運算子宇宙的橋） |
| [PROVENANCE.md](PROVENANCE.md) | 來源履歷：說明這些實作都是依據公開演算法自行寫成 |
| [REFERENCES.md](REFERENCES.md) | 每個運算子的文獻依據 |
| [REPRODUCE.md](REPRODUCE.md) | 數值重現步驟：由 seed 驅動、結果確定 |
| [STATUS.md](STATUS.md) | 專案目前的位置與後續計畫（plan_ref） |

## 發行說明 / 設計

| 文件 | 內容 |
|---|---|
| [V13.md](V13.md) | v13 ＝ 走向實用 ＋ 跨專案 packaging ＋ 感知堆疊 |
| [V14.md](V14.md) | v14 ＝ 感知堆疊完成（運動 ＋ 強化） |
| [STUDIO_UX.md](STUDIO_UX.md) | Fullseye Studio 在 UX／設計上的改良意圖與來龍去脈 |

---

## 快速指令

```powershell
py -3.11 -m pip install -e ".[opencv,gui]"     # 安裝（影像 I/O + Studio）
py -3.11 studio.py                              # 啟動 Fullseye Studio（= fullseye-studio）
py -3.11 imgevolve.py ops --search edge         # 搜尋運算子（= fullseye ops --search edge）
py -3.11 imgevolve.py apply gauss_filter in.png out.png --a 0.6
py -3.11 imgevolve.py run pipeline.json in.png --out result.png
py -3.11 imgevolve.py coverage                  # 誠實的涵蓋數字
```

在 Python 中：

```python
import fullseye, numpy as np
out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])
eng = fullseye.FullseyeEngine.load("pipeline.json"); result = eng.run(frame)
```

---

![經典 2-D 視覺運算子的真實輸出](articles/assets/vision_ops_montage.png)

*經典 2-D 視覺運算子的真實輸出*

![Physical AI 與感測器模擬的真實輸出](articles/assets/physical_ai_montage.png)

*Physical AI 與感測器模擬的真實輸出*

<!-- docmap:start -->

## 文件地圖 — 共 213 篇

完整地圖，確保**沒有任何文件無法從索引到達**(`docs/ops/` 下的 2,193 篇運算子說明與 58 篇族群指南從上面的「尋找運算子」進入; 文章見 [articles/](articles/README.md))。**內文多為日文。**

**Getting started**(12)

| 文件 | 內容 |
|---|---|
| [`GETTING_STARTED.md`](GETTING_STARTED.md) | はじめかた（5分で動かす） _(ja)_ |
| [`INSTALL.md`](INSTALL.md) | インストール / 環境構築 完全ガイド _(ja)_ |
| [`STUDIO_GUIDE.md`](STUDIO_GUIDE.md) | Fullseye Studio 完全ガイド _(ja)_ |
| [`STUDIO_UX.md`](STUDIO_UX.md) | Fullseye Studio — UX & design pass (v15) |
| [`EXAMPLES.md`](EXAMPLES.md) | imgevolve — sample code (cross-library recipes) |
| [`EXAMPLES_3D.md`](EXAMPLES_3D.md) | Fullseye 3-D ビジョン — 事例ギャラリー(EXAMPLES_3D) _(ja)_ |
| [`GALLERY.md`](GALLERY.md) | Fullseye ギャラリー / Gallery _(ja)_ |
| [`REPRODUCE.md`](REPRODUCE.md) | Reproducing the numbers |
| [`CONSUMER_APPLICATIONS.md`](CONSUMER_APPLICATIONS.md) | Fullseye — per-project applications (honest, 2026-08-15) |
| [`3DGS_USAGE.md`](3DGS_USAGE.md) | Fullseye 3DGS ― 使い方(1コマンド) _(ja)_ |
| [`TERRAIN_WALK.md`](TERRAIN_WALK.md) | 地形の上を歩かせる(sim-native, GPU 不要) _(ja)_ |
| [`GSPLAT_NATIVE_WINDOWS.md`](GSPLAT_NATIVE_WINDOWS.md) | gsplat native を Windows(RTX 5090 / torch cu128)でビルドする — 実証済み手順 _(ja)_ |

**Operator reference**(9)

| 文件 | 內容 |
|---|---|
| [`OPERATORS.md`](OPERATORS.md) | imgevolve — cross-library operator catalog |
| [`OP_CATALOG.md`](OP_CATALOG.md) | Fullseye Operator Catalog — AI capability ledger |
| [`OP_COMBINATION_MATRIX.md`](OP_COMBINATION_MATRIX.md) | fullseye 3D op × op 組み合わせマトリクス(実現性 × 差別化で優先度化) _(ja)_ |
| [`CONVERSION_MATRIX.md`](CONVERSION_MATRIX.md) | 型変換の行列 ―― 穴と不具合の点検 _(ja)_ |
| [`CONNECTIVITY.md`](CONNECTIVITY.md) | Fullseye connectivity — devices, cameras & industrial protocols |
| [`MATCH_3D_MATRIX.md`](MATCH_3D_MATRIX.md) | fullseye 3D ビジョン・ツールキット(Physical AI 向け、HALCON/OpenCV 差別化) _(ja)_ |
| [`GENERAL_ALGORITHMS.md`](GENERAL_ALGORITHMS.md) | 汎用アルゴリズムを実装可能にする — algo-c 対応ロードマップ _(ja)_ |
| [`ADDING_OPS.md`](ADDING_OPS.md) | Adding an operator |
| [`WAVE0_STABLE_SLOTS.md`](WAVE0_STABLE_SLOTS.md) | Wave-0: stable op slots + name-pinned champions |

**Retrieval for AI assistants**(1)

| 文件 | 內容 |
|---|---|
| [`AI_RAG_GUIDE.md`](AI_RAG_GUIDE.md) | Fullseye を AI アシスタントの RAG にする手順(Claude Code 向け) _(ja)_ |

**Literature layer (manufacturing knowledge → ops)**(5)

| 文件 | 內容 |
|---|---|
| [`literature/INDEX.md`](literature/INDEX.md) | 文献層 —— RAD コーパスからの、op に繋がる来歴つき要約 _(ja)_ |
| [`literature/mech_design.md`](literature/mech_design.md) | 文献層: メカ設計(機械設計) _(ja)_ |
| [`literature/mechatronics_parts.md`](literature/mechatronics_parts.md) | 文献層: メカトロ部品(アクチュエータ・センサ・電気部品) _(ja)_ |
| [`literature/manufacturing_processes.md`](literature/manufacturing_processes.md) | 文献層: 製造工程(あらゆる製造技術の開発に) _(ja)_ |
| [`literature/OSS_LANDSCAPE.md`](literature/OSS_LANDSCAPE.md) | 既存 OSS の地図 —— すでにある道具と、Fullseye との繋ぎ方 _(ja)_ |

**Perception and sensors**(7)

| 文件 | 內容 |
|---|---|
| [`PERCEPTION.md`](PERCEPTION.md) | Fullseye perception stack — one-page reference |
| [`PERCEPTION_PHYSICAL_AI.md`](PERCEPTION_PHYSICAL_AI.md) | Physical-AI perception pipeline (fullseye / imgevolve, v18.3, 2026-08-15) |
| [`PERCEPTION_REALDATA.md`](PERCEPTION_REALDATA.md) | v15 — perception stack on real footage (video I/O + honest field measurements) |
| [`SENSOR_PLAYBOOK.md`](SENSOR_PLAYBOOK.md) | Fullseye Sensor Playbook — センサー種別ごとの推奨 op パイプライン _(ja)_ |
| [`HIGHSPEED_VISION.md`](HIGHSPEED_VISION.md) | 高速ビジョン(1ms 視覚フィードバック)を物理シミュ上でやる — 計画 _(ja)_ |
| [`SAMPLE_IMAGE_REFERENCES.md`](SAMPLE_IMAGE_REFERENCES.md) | Sample images — provenance, source papers & public repositories |
| [`BBB_SENSING.md`](BBB_SENSING.md) | BBB sensing — 複眼光場 × コネクトーム(研究方向) _(ja)_ |

**HALCON correspondence**(6)

| 文件 | 內容 |
|---|---|
| [`HALCON_PARITY.md`](HALCON_PARITY.md) | HALCON parity — what imgevolve genuinely DOES (not just names) |
| [`HALCON_COVERAGE.md`](HALCON_COVERAGE.md) | HALCON operator coverage (measured vs the real reference) |
| [`HALCON_COVERAGE_HONEST.md`](HALCON_COVERAGE_HONEST.md) | HALCON カバレッジ — honest な分母(2026-08-18 更新) _(ja)_ |
| [`HDEVELOP_FIDELITY.md`](HDEVELOP_FIDELITY.md) | Fullseye Studio — HDevelop 忠実化スペック(北極星) _(ja)_ |
| [`HDEVELOP_DEV_OPS.md`](HDEVELOP_DEV_OPS.md) | HDevelop `dev_*` operator family — the UI/display control surface (Studio 北極星) _(ja)_ |
| [`LIB_COVERAGE.md`](LIB_COVERAGE.md) | Multi-library coverage (imgevolve is not HALCON-only) |

**Fullseye Script**(3)

| 文件 | 內容 |
|---|---|
| [`FSCRIPT_DECISION.md`](FSCRIPT_DECISION.md) | Fullseye Script / Runtime — 要件定義と基本設計(確定案) _(ja)_ |
| [`FSCRIPT_LANGUAGE.md`](FSCRIPT_LANGUAGE.md) | Fullseye Script — 言語 / ランタイム / ウォッチ IDE 設計仕様(北極星) _(ja)_ |
| [`FSCRIPT_MEASUREMENTS.md`](FSCRIPT_MEASUREMENTS.md) | Fullseye Runtime — 実測記録 (2026-08-15) _(ja)_ |

**Quality and honesty**(11)

| 文件 | 內容 |
|---|---|
| [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md) | Known Issues — 実データ横断テストで発見(2026-08-30) _(ja)_ |
| [`STATUS.md`](STATUS.md) | imgevolve — status / plan (plan_ref) |
| [`ACCURACY_BENCH.md`](ACCURACY_BENCH.md) | Accuracy benchmark — champion vs null (holdout) |
| [`BENCH_VS_OPENCV.md`](BENCH_VS_OPENCV.md) | imgevolve GPU op vs OpenCV(CPU)処理速度ベンチ _(ja)_ |
| [`PARITY_CROSSBACKEND.md`](PARITY_CROSSBACKEND.md) | Cross-backend parity — independent implementations agree at the tested points |
| [`CHAIN_FUZZ.md`](CHAIN_FUZZ.md) | 連鎖ファザー(chain fuzz)— op を鎖にして揺さぶる第三の品質保証層 _(ja)_ |
| [`PROVENANCE.md`](PROVENANCE.md) | Provenance |
| [`REFERENCES.md`](REFERENCES.md) | imgevolve — operator research provenance |
| [`AUDIT_2026_08_12.md`](AUDIT_2026_08_12.md) | imgevolve implementation audit — 2026-08-12 |
| [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) | リリース手順書 — 同じ間違いを繰り返さないための門 _(ja)_ |
| [`I18N.md`](I18N.md) | Fullseye の多言語対応 — 全体設計 / Internationalisation design _(ja)_ |

**Performance and GPU**(4)

| 文件 | 內容 |
|---|---|
| [`GPU_ACCEL_PLAN.md`](GPU_ACCEL_PLAN.md) | op の GPU 化ロードマップ(E2E の本丸) _(ja)_ |
| [`GPU_OPTIMIZATION_PATTERNS.md`](GPU_OPTIMIZATION_PATTERNS.md) | GPU 最適化デザインパターン・カタログ(RTX 5090 / Blackwell sm_120 向け) _(ja)_ |
| [`design/FAST_TWINS.md`](design/FAST_TWINS.md) | CPU 高速 twin(`fast.py`)— 実装記録と実測(2026-09-03) _(ja)_ |
| [`design/PERF_MEMORY_VIDEO_SURVEY.md`](design/PERF_MEMORY_VIDEO_SURVEY.md) | op の高速化・省メモリ化・動画処理 — 実測にもとづく調査報告(2026-09-03) _(ja)_ |

**Design and architecture**(7)

| 文件 | 內容 |
|---|---|
| [`ENGINE.md`](ENGINE.md) | FullseyeEngine — 設計したパイプラインを実行するランタイム _(ja)_ |
| [`EVOLUTION_ENVIRONMENT.md`](EVOLUTION_ENVIRONMENT.md) | 進化型アルゴリズム開発環境 — 拡散・収縮・昇格 _(ja)_ |
| [`INTEGRATION.md`](INTEGRATION.md) | Depending on Fullseye from another project (stability contract) |
| [`UNIFIED_API_REQUIREMENTS.md`](UNIFIED_API_REQUIREMENTS.md) | Fullseye 統一インターフェース — 要件定義書 (v0.1, 2026-08-18) _(ja)_ |
| [`design/TRIZ_DESIGN_PATTERN_MATRIX.md`](design/TRIZ_DESIGN_PATTERN_MATRIX.md) | TRIZ 40 発明原理 × ソフトウェア設計パターン × コンテナ型 — 構造選択マトリクス(fullseye) _(ja)_ |
| [`EVIS_VISION_OSS_GAP.md`](EVIS_VISION_OSS_GAP.md) | evis の視覚部品 — OSS/ROS2 ギャップ分析 (2026-08-17) _(ja)_ |
| [`INDUSTRY_SIGNALS.md`](INDUSTRY_SIGNALS.md) | 業界シグナル — 展示会・アワードを op 発想の恒常的な入力にする _(ja)_ |

**Working notes and plans (historical; numbers are as of their date)**(12)

| 文件 | 內容 |
|---|---|
| [`V13.md`](V13.md) | v13 — production hardening, cross-project packaging, perception stack |
| [`V14.md`](V14.md) | v14 — perception-stack completion: motion + robustness |
| [`SESSION_SUMMARY.md`](SESSION_SUMMARY.md) | Session Summary (auto-generated) |
| [`SESSION_2026_08_14.md`](SESSION_2026_08_14.md) | Session 2026-08-14 — Data-format expansion + Studio UI review |
| [`STUDIO_REVIEW_2026_08_14.md`](STUDIO_REVIEW_2026_08_14.md) | Fullseye Studio — verified UI review (2026-08-14) |
| [`NEXT_SESSION.md`](NEXT_SESSION.md) | 次セッション引き継ぎ — 高速化・省メモリ・動画 + 解像度管理 + 図注(2026-09-03 午前〜) _(ja)_ |
| [`NEXT_OPS_PLAN_2026-08-31.md`](NEXT_OPS_PLAN_2026-08-31.md) | 次期 op 拡張計画(2026-08-31 調査、v0.1.4 リリース直後) _(ja)_ |
| [`PLAN_0_1_9.md`](PLAN_0_1_9.md) | 0.1.9 → 0.1.10 の作業計画 _(ja)_ |
| [`ARTICLE_INTEGRATION_TODO.md`](ARTICLE_INTEGRATION_TODO.md) | 記事への反映待ち(2026-09-02、可視化ウィング作業から) _(ja)_ |
| [`ARTICLE_RESTRUCTURE_PLAN.md`](ARTICLE_RESTRUCTURE_PLAN.md) | Qiita 記事の章構成 組み替え計画(2026-09-02 起票 / **同日 実施済み** = commit 32e47171) _(ja)_ |
| [`ARTICLE_GPU_SHAPEMATCH.md`](ARTICLE_GPU_SHAPEMATCH.md) | 記事材料: 形状マッチングを GPU に載せる —— 勾配方向スコアの conv2d 定式化 _(ja)_ |
| [`FULLSEYE_OP_ARTICLE_SPEC.md`](FULLSEYE_OP_ARTICLE_SPEC.md) | Fullseye op カタログ画像・専用記事 仕様書(第 2 陣企画書) _(ja)_ |

**Other**(136)

| 文件 | 內容 |
|---|---|
| [`3DGS_USAGE.de.md`](3DGS_USAGE.de.md) | Fullseye 3DGS – Anwendung (ein einziger Befehl) |
| [`3DGS_USAGE.en.md`](3DGS_USAGE.en.md) | Fullseye 3DGS — how to use it (one command) |
| [`3DGS_USAGE.ko.md`](3DGS_USAGE.ko.md) | Fullseye 3DGS — 사용법(명령어 한 줄) |
| [`3DGS_USAGE.tw.md`](3DGS_USAGE.tw.md) | Fullseye 3DGS —— 使用方法（一行指令） _(ja)_ |
| [`3DGS_USAGE.zh.md`](3DGS_USAGE.zh.md) | Fullseye 3DGS —— 使用方法（单条命令） _(ja)_ |
| [`AI_RAG_GUIDE.de.md`](AI_RAG_GUIDE.de.md) | Fullseye als RAG eines KI-Assistenten nutzen (für Claude Code) |
| [`AI_RAG_GUIDE.en.md`](AI_RAG_GUIDE.en.md) | Using Fullseye as an AI assistant's RAG (for Claude Code) |
| [`AI_RAG_GUIDE.ko.md`](AI_RAG_GUIDE.ko.md) | Fullseye를 AI 어시스턴트의 RAG로 사용하는 방법(Claude Code용) |
| [`AI_RAG_GUIDE.tw.md`](AI_RAG_GUIDE.tw.md) | 將 Fullseye 用作 AI 助理 RAG 的方法（針對 Claude Code） _(ja)_ |
| [`AI_RAG_GUIDE.zh.md`](AI_RAG_GUIDE.zh.md) | 将 Fullseye 用作 AI 助手 RAG 的方法（面向 Claude Code） _(ja)_ |
| [`BENCH_VS_OPENCV.en.md`](BENCH_VS_OPENCV.en.md) | imgevolve GPU op vs OpenCV (CPU) throughput benchmark |
| [`CAPABILITIES.en.md`](CAPABILITIES.en.md) | What Fullseye can do |
| [`CAPABILITIES.md`](CAPABILITIES.md) | Fullseye でできること _(ja)_ |
| [`CHAIN_FUZZ.en.md`](CHAIN_FUZZ.en.md) | Chain Fuzzer (chain fuzz) — a third quality-assurance layer that shakes ops by wiring them into chains |
| [`DESIGN_NOTES.de.md`](DESIGN_NOTES.de.md) | Fullseye-Entwurfsnotizen (aus den ★-Kommentaren im Quellcode erzeugt) |
| [`DESIGN_NOTES.en.md`](DESIGN_NOTES.en.md) | Fullseye design notes (generated from the ★ comments in the source) |
| [`DESIGN_NOTES.ko.md`](DESIGN_NOTES.ko.md) | Fullseye 설계 판단 모음(소스의 ★ 주석에서 생성) |
| [`DESIGN_NOTES.md`](DESIGN_NOTES.md) | Fullseye 設計判断集(ソース中の ★ コメントから生成) _(ja)_ |
| [`DESIGN_NOTES.tw.md`](DESIGN_NOTES.tw.md) | Fullseye 設計判斷集（由原始碼中的 ★ 註解產生） _(ja)_ |
| [`DESIGN_NOTES.zh.md`](DESIGN_NOTES.zh.md) | Fullseye 设计判断集（由源码中的 ★ 注释生成） _(ja)_ |
| [`ENGINE.de.md`](ENGINE.de.md) | FullseyeEngine — Laufzeitumgebung zur Ausführung entworfener Pipelines |
| [`ENGINE.en.md`](ENGINE.en.md) | FullseyeEngine — the runtime that executes a pipeline you designed |
| [`ENGINE.ko.md`](ENGINE.ko.md) | FullseyeEngine — 설계한 파이프라인을 실행하는 런타임 |
| [`ENGINE.tw.md`](ENGINE.tw.md) | FullseyeEngine — 執行已設計管線的執行環境 _(ja)_ |
| [`ENGINE.zh.md`](ENGINE.zh.md) | FullseyeEngine — 运行已设计管道的运行时 _(ja)_ |
| [`EVIS_VISION_OSS_GAP.en.md`](EVIS_VISION_OSS_GAP.en.md) | evis Vision Components — OSS/ROS2 Gap Analysis (2026-08-17) |
| [`EVOLUTION_ENVIRONMENT.en.md`](EVOLUTION_ENVIRONMENT.en.md) | Evolutionary Algorithm Development Environment — Expand, Contract, Promote |
| [`FSCRIPT_LANGUAGE.en.md`](FSCRIPT_LANGUAGE.en.md) | Fullseye Script — Language / Runtime / Watch IDE Design Specification (North Star) |
| [`GALLERY.en.md`](GALLERY.en.md) | Fullseye Gallery |
| [`GENERAL_ALGORITHMS.de.md`](GENERAL_ALGORITHMS.de.md) | Allgemeine Algorithmen implementierbar machen — algo-c Kompatibilitäts-Roadmap |
| [`GENERAL_ALGORITHMS.en.md`](GENERAL_ALGORITHMS.en.md) | Making general algorithms implementable — the algo-c support roadmap |
| [`GENERAL_ALGORITHMS.ko.md`](GENERAL_ALGORITHMS.ko.md) | 범용 알고리즘을 구현 가능하게 만들기 — algo-c 대응 로드맵 |
| [`GENERAL_ALGORITHMS.tw.md`](GENERAL_ALGORITHMS.tw.md) | 讓通用演算法也能實作 — algo-c 對應路線圖 _(ja)_ |
| [`GENERAL_ALGORITHMS.zh.md`](GENERAL_ALGORITHMS.zh.md) | 让通用算法也能实现 — algo-c 对应路线图 _(ja)_ |
| [`GETTING_STARTED.de.md`](GETTING_STARTED.de.md) | Erste Schritte (in 5 Minuten startklar) |
| [`GETTING_STARTED.en.md`](GETTING_STARTED.en.md) | Getting started (running in 5 minutes) |
| [`GETTING_STARTED.ko.md`](GETTING_STARTED.ko.md) | 시작하기 (5분 만에 실행하기) |
| [`GETTING_STARTED.tw.md`](GETTING_STARTED.tw.md) | 快速上手（5 分鐘跑起來） _(ja)_ |
| [`GETTING_STARTED.zh.md`](GETTING_STARTED.zh.md) | 快速上手（5 分钟运行起来） _(ja)_ |
| [`GPU_OPTIMIZATION_PATTERNS.en.md`](GPU_OPTIMIZATION_PATTERNS.en.md) | GPU Optimization Design-Pattern Catalog (for RTX 5090 / Blackwell sm_120) |
| [`GSPLAT_NATIVE_WINDOWS.en.md`](GSPLAT_NATIVE_WINDOWS.en.md) | Building native gsplat on Windows (RTX 5090 / torch cu128) — a proven procedure |
| [`HALCON_COVERAGE_HONEST.en.md`](HALCON_COVERAGE_HONEST.en.md) | HALCON Coverage — the honest denominator (updated 2026-08-18) |
| [`HARDENING.en.md`](HARDENING.en.md) | What the PoCs hardened — found, fixed, and gated |
| [`HARDENING.md`](HARDENING.md) | PoC が上げた堅牢性 —— 見つけて直した記録 _(ja)_ |
| [`HDEVELOP_DEV_OPS.en.md`](HDEVELOP_DEV_OPS.en.md) | HDevelop `dev_*` operator family — the UI/display control surface (Studio north star) |
| [`HDEVELOP_FIDELITY.en.md`](HDEVELOP_FIDELITY.en.md) | Fullseye Studio — HDevelop Fidelity Spec (North Star) |
| [`I18N_PLAN.md`](I18N_PLAN.md) | 完全な多言語化 — 計画と現在地 _(ja)_ |
| [`INSTALL.de.md`](INSTALL.de.md) | Installations- und Einrichtungshandbuch |
| [`INSTALL.en.md`](INSTALL.en.md) | Installation / Environment Setup — Complete Guide |
| [`INSTALL.ko.md`](INSTALL.ko.md) | 설치 / 환경 구축 완전 가이드 |
| [`INSTALL.tw.md`](INSTALL.tw.md) | 安裝 / 環境建置完整指南 _(ja)_ |
| [`INSTALL.zh.md`](INSTALL.zh.md) | 安装 / 环境搭建完全指南 _(ja)_ |
| [`MATCH_3D_MATRIX.en.md`](MATCH_3D_MATRIX.en.md) | fullseye 3D Vision Toolkit (for Physical AI, differentiating from HALCON/OpenCV) |
| [`MATURITY.md`](MATURITY.md) | 成熟度台帳(Maturity) _(ja)_ |
| [`MCP.md`](MCP.md) | Fullseye を MCP(Model Context Protocol)から使う _(ja)_ |
| [`OP_COMBINATION_MATRIX.en.md`](OP_COMBINATION_MATRIX.en.md) | fullseye 3D op × op Combination Matrix (prioritized by feasibility × differentiation) |
| [`SAMPLE_IMAGE_REFERENCES.en.md`](SAMPLE_IMAGE_REFERENCES.en.md) | Sample images — provenance, source papers & public repositories |
| [`STUDIO_GUIDE.de.md`](STUDIO_GUIDE.de.md) | Vollständiger Leitfaden zu Fullseye Studio |
| [`STUDIO_GUIDE.en.md`](STUDIO_GUIDE.en.md) | The complete guide to Fullseye Studio |
| [`STUDIO_GUIDE.ko.md`](STUDIO_GUIDE.ko.md) | Fullseye Studio 완전 가이드 |
| [`STUDIO_GUIDE.tw.md`](STUDIO_GUIDE.tw.md) | Fullseye Studio 完全指南 _(ja)_ |
| [`STUDIO_GUIDE.zh.md`](STUDIO_GUIDE.zh.md) | Fullseye Studio 完全指南 _(ja)_ |
| [`TERRAIN_WALK.en.md`](TERRAIN_WALK.en.md) | Walking a Character Over Terrain (sim-native, no GPU required) |
| [`UNIFIED_API_REQUIREMENTS.en.md`](UNIFIED_API_REQUIREMENTS.en.md) | Fullseye Unified Interface — Requirements Specification (v0.1, 2026-08-18) |
| [`capabilities/align-and-stack.md`](capabilities/align-and-stack.md) | id: align-and-stack |
| [`capabilities/beamforming-and-range-doppler.md`](capabilities/beamforming-and-range-doppler.md) | id: beamforming-and-range-doppler |
| [`capabilities/beats-fringes-and-screens.md`](capabilities/beats-fringes-and-screens.md) | id: beats-fringes-and-screens |
| [`capabilities/blob-and-region.md`](capabilities/blob-and-region.md) | id: blob-and-region |
| [`capabilities/camera-intrinsics-calibration.md`](capabilities/camera-intrinsics-calibration.md) | id: camera-intrinsics-calibration |
| [`capabilities/colour-and-delta-e.md`](capabilities/colour-and-delta-e.md) | id: colour-and-delta-e |
| [`capabilities/complex-plane-fields.md`](capabilities/complex-plane-fields.md) | id: complex-plane-fields |
| [`capabilities/estimate-lens-distortion.md`](capabilities/estimate-lens-distortion.md) | id: estimate-lens-distortion |
| [`capabilities/figures-and-annotation.md`](capabilities/figures-and-annotation.md) | id: figures-and-annotation |
| [`capabilities/fix-text-in-images.md`](capabilities/fix-text-in-images.md) | id: fix-text-in-images |
| [`capabilities/geodetic-frames.md`](capabilities/geodetic-frames.md) | id: geodetic-frames |
| [`capabilities/golden-compare.md`](capabilities/golden-compare.md) | id: golden-compare |
| [`capabilities/inspection-fixture.md`](capabilities/inspection-fixture.md) | id: inspection-fixture |
| [`capabilities/inspection-workflow.md`](capabilities/inspection-workflow.md) | id: inspection-workflow |
| [`capabilities/inverted-colour-overlays.md`](capabilities/inverted-colour-overlays.md) | id: inverted-colour-overlays |
| [`capabilities/lens-distortion-correction.md`](capabilities/lens-distortion-correction.md) | id: lens-distortion-correction |
| [`capabilities/measurement-system-and-uncertainty.md`](capabilities/measurement-system-and-uncertainty.md) | id: measurement-system-and-uncertainty |
| [`capabilities/one-stroke-drawing.md`](capabilities/one-stroke-drawing.md) | id: one-stroke-drawing |
| [`capabilities/optics-and-materials.md`](capabilities/optics-and-materials.md) | id: optics-and-materials |
| [`capabilities/pictures-that-carry-their-own-truth.md`](capabilities/pictures-that-carry-their-own-truth.md) | id: pictures-that-carry-their-own-truth |
| [`capabilities/point-target-detection.md`](capabilities/point-target-detection.md) | id: point-target-detection |
| [`capabilities/polarization-imaging.md`](capabilities/polarization-imaging.md) | id: polarization-imaging |
| [`capabilities/raw-to-display-isp.md`](capabilities/raw-to-display-isp.md) | id: raw-to-display-isp |
| [`capabilities/subpixel-2d-metrology.md`](capabilities/subpixel-2d-metrology.md) | id: subpixel-2d-metrology |
| [`capabilities/terrain-and-visibility.md`](capabilities/terrain-and-visibility.md) | id: terrain-and-visibility |
| [`capabilities/text-and-tables-on-images.md`](capabilities/text-and-tables-on-images.md) | id: text-and-tables-on-images |
| [`capabilities/theorems-as-pictures.md`](capabilities/theorems-as-pictures.md) | id: theorems-as-pictures |
| [`capabilities/tomography-reconstruction.md`](capabilities/tomography-reconstruction.md) | id: tomography-reconstruction |
| [`capabilities/typed-results-as-json.md`](capabilities/typed-results-as-json.md) | id: typed-results-as-json |
| [`capabilities/typed-results-as-markdown.md`](capabilities/typed-results-as-markdown.md) | id: typed-results-as-markdown |
| [`capabilities/vibration-and-acoustics.md`](capabilities/vibration-and-acoustics.md) | id: vibration-and-acoustics |
| [`capabilities/visual-hull-from-silhouettes.md`](capabilities/visual-hull-from-silhouettes.md) | id: visual-hull-from-silhouettes |
| [`capabilities/volume-from-3d-scan.md`](capabilities/volume-from-3d-scan.md) | id: volume-from-3d-scan |
| [`capabilities/what-a-picture-cannot-check.md`](capabilities/what-a-picture-cannot-check.md) | id: what-a-picture-cannot-check |
| [`capabilities/xlsx-report.md`](capabilities/xlsx-report.md) | id: xlsx-report |
| [`hardening/carve-look-at-unreachable-and-silent.md`](hardening/carve-look-at-unreachable-and-silent.md) | id: carve-look-at-unreachable-and-silent |
| [`hardening/cli-help-and-subcommands-broke-in-the-wheel.md`](hardening/cli-help-and-subcommands-broke-in-the-wheel.md) | id: cli-help-and-subcommands-broke-in-the-wheel |
| [`hardening/compactness-saturated-at-one.md`](hardening/compactness-saturated-at-one.md) | id: compactness-saturated-at-one |
| [`hardening/dem-viewshed-self-occlusion.md`](hardening/dem-viewshed-self-occlusion.md) | id: dem-viewshed-self-occlusion |
| [`hardening/dimensional-features-were-normalised.md`](hardening/dimensional-features-were-normalised.md) | id: dimensional-features-were-normalised |
| [`hardening/ecef-to-geodetic-returned-latitude-180.md`](hardening/ecef-to-geodetic-returned-latitude-180.md) | id: ecef-to-geodetic-returned-latitude-180 |
| [`hardening/empty-and-tiny-inputs-raised-raw-library-errors.md`](hardening/empty-and-tiny-inputs-raised-raw-library-errors.md) | id: empty-and-tiny-inputs-raised-raw-library-errors |
| [`hardening/empty-name-resolved-and-narrow-floats-not-upcast.md`](hardening/empty-name-resolved-and-narrow-floats-not-upcast.md) | id: empty-name-resolved-and-narrow-floats-not-upcast |
| [`hardening/engine-load-on-an-instance-was-silently-ignored.md`](hardening/engine-load-on-an-instance-was-silently-ignored.md) | id: engine-load-on-an-instance-was-silently-ignored |
| [`hardening/features-saturated-at-one.md`](hardening/features-saturated-at-one.md) | id: features-saturated-at-one |
| [`hardening/frame-align-inlier-ratio-is-not-confidence.md`](hardening/frame-align-inlier-ratio-is-not-confidence.md) | id: frame-align-inlier-ratio-is-not-confidence |
| [`hardening/functional-gate-did-not-know-the-match-sort.md`](hardening/functional-gate-did-not-know-the-match-sort.md) | id: functional-gate-did-not-know-the-match-sort |
| [`hardening/halcon-named-shape-factors.md`](hardening/halcon-named-shape-factors.md) | id: halcon-named-shape-factors |
| [`hardening/image-io-dropped-write-failures-and-crushed-16-bit.md`](hardening/image-io-dropped-write-failures-and-crushed-16-bit.md) | id: image-io-dropped-write-failures-and-crushed-16-bit |
| [`hardening/inputs-without-a-conversion-were-not-refused.md`](hardening/inputs-without-a-conversion-were-not-refused.md) | id: inputs-without-a-conversion-were-not-refused |
| [`hardening/itk-threshold-ops-returned-the-dark-side.md`](hardening/itk-threshold-ops-returned-the-dark-side.md) | id: itk-threshold-ops-returned-the-dark-side |
| [`hardening/ledger-evicted-silently-and-studio-help-aborted.md`](hardening/ledger-evicted-silently-and-studio-help-aborted.md) | id: ledger-evicted-silently-and-studio-help-aborted |
| [`hardening/ledger-lookups-returned-empty-for-unknown-names.md`](hardening/ledger-lookups-returned-empty-for-unknown-names.md) | id: ledger-lookups-returned-empty-for-unknown-names |
| [`hardening/mcp-facade-layer-listed-classes-as-ops.md`](hardening/mcp-facade-layer-listed-classes-as-ops.md) | id: mcp-facade-layer-listed-classes-as-ops |
| [`hardening/moment-invariants-two-families-same-name.md`](hardening/moment-invariants-two-families-same-name.md) | id: moment-invariants-two-families-same-name |
| [`hardening/nary-ops-unlisted-and-knobs-unstated.md`](hardening/nary-ops-unlisted-and-knobs-unstated.md) | id: nary-ops-unlisted-and-knobs-unstated |
| [`hardening/no-gate-knew-what-dimension-a-feature-has.md`](hardening/no-gate-knew-what-dimension-a-feature-has.md) | id: no-gate-knew-what-dimension-a-feature-has |
| [`hardening/noise-sigma-mad-collapses-on-quantised-data.md`](hardening/noise-sigma-mad-collapses-on-quantised-data.md) | id: noise-sigma-mad-collapses-on-quantised-data |
| [`hardening/nonfinite-output-was-sanitized-silently.md`](hardening/nonfinite-output-was-sanitized-silently.md) | id: nonfinite-output-was-sanitized-silently |
| [`hardening/op-find-blind-to-japanese-queries.md`](hardening/op-find-blind-to-japanese-queries.md) | id: op-find-blind-to-japanese-queries |
| [`hardening/otsu-threshold-at-the-bin-midpoint.md`](hardening/otsu-threshold-at-the-bin-midpoint.md) | id: otsu-threshold-at-the-bin-midpoint |
| [`hardening/pfm-default-wrote-8-bit-values-into-a-float-format.md`](hardening/pfm-default-wrote-8-bit-values-into-a-float-format.md) | id: pfm-default-wrote-8-bit-values-into-a-float-format |
| [`hardening/pose-helpers-could-not-take-their-own-matrix.md`](hardening/pose-helpers-could-not-take-their-own-matrix.md) | id: pose-helpers-could-not-take-their-own-matrix |
| [`hardening/refract-one-way-reference.md`](hardening/refract-one-way-reference.md) | id: refract-one-way-reference |
| [`hardening/run-pipeline-stage-forms-fail-obscurely.md`](hardening/run-pipeline-stage-forms-fail-obscurely.md) | id: run-pipeline-stage-forms-fail-obscurely |
| [`hardening/stage-forms-read-differently-by-four-entry-points.md`](hardening/stage-forms-read-differently-by-four-entry-points.md) | id: stage-forms-read-differently-by-four-entry-points |
| [`hardening/strict-mode-only-covered-some-of-the-guards.md`](hardening/strict-mode-only-covered-some-of-the-guards.md) | id: strict-mode-only-covered-some-of-the-guards |
| [`hardening/studio-run-key-ignored-unapplied-edits.md`](hardening/studio-run-key-ignored-unapplied-edits.md) | id: studio-run-key-ignored-unapplied-edits |
| [`hardening/table-sort-mixes-rows-and-spec-dicts.md`](hardening/table-sort-mixes-rows-and-spec-dicts.md) | id: table-sort-mixes-rows-and-spec-dicts |
| [`hardening/unknown-operator-hides-missing-backend.md`](hardening/unknown-operator-hides-missing-backend.md) | id: unknown-operator-hides-missing-backend |
| [`hardening/wrappers-were-scalars-and-hints-were-raw-type-errors.md`](hardening/wrappers-were-scalars-and-hints-were-raw-type-errors.md) | id: wrappers-were-scalars-and-hints-were-raw-type-errors |
| [`literature/oss_landscape_notes.md`](literature/oss_landscape_notes.md) | OSS landscape notes (verified 2026-09-21) |

<!-- docmap:end -->
