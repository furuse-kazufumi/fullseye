# Fullseye 文档索引

**Language:** [日本語](README.md) · [English](README.en.md) · [简体中文](README.zh.md) · [繁體中文](README.tw.md) · [한국어](README.ko.md) · [Deutsch](README.de.md)

> **请注意：**目前只有本索引页有译文，它所链接的各篇文档暂时仅有日文版。


![六幕，全部是真实算子输出：边缘方向 / 连通域筛选 / 亚像素测量 / SDF 转网格 / 点云聚类 / 镜头离焦。](articles/assets/fullseye_hero.gif)

*六幕，全部是真实算子输出：边缘方向 / 连通域筛选 / 亚像素测量 / SDF 转网格 / 点云聚类 / 镜头离焦。*

**Fullseye**（工作代号 imgevolve）是一套 HALCON/HDevelop 级别的实用工具：由 numpy 原生的图像处理算子库、HDevelop 风格的可视化流水线设计环境（Fullseye Studio）以及执行运行时（FullseyeEngine）三者组成。算子约 **899** 个（以注册表计数），其中 **979/2313** 个真实 HALCON 算子做到了 genuine（真正等效）实现，覆盖 48 个类别。

> **先从这里开始 → [GETTING_STARTED.md](GETTING_STARTED.md)（5 分钟跑起来）**

> **功能一览 → [CAPABILITIES.en.md](CAPABILITIES.en.md)**（按目的检索）/ **PoC 提升的健壮性 → [HARDENING.en.md](HARDENING.en.md)**（发现、修复、加门）

---

<!-- poc-index:start -->

## PoC 系列 — 带真值求解的 117 个实际问题

每一个都具有闭式或合成的真值，并必定附带零点(什么都不做)。失败模式分开计数，原因用对照组区分。完整列表: [examples/README.md](../examples/README.md)。

| 领域 | PoC 与其结论 |
|---|---|
| metrology (35) | [`poc_asbuilt_wall_deviation`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_asbuilt_wall_deviation.py) As-built wall deviation — the bounding box measures the room's heading, not its size<br>[`poc_battery_electrode_breathing`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_battery_electrode_breathing.py) Measuring electrode breathing in microns — sub-pixel is not enough<br>[`poc_bone_trabecular_thickness`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bone_trabecular_thickness.py) Trabecular Thickness, Separation and Bone Volume Fraction — The Plate Model and the Direct Method Disagree on the Same Image<br>[`poc_bump_coplanarity`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bump_coplanarity.py) Bump coplanarity versus substrate warpage — subtract too much and the real defect goes with it<br>[`poc_cad_scan_deviation`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cad_scan_deviation.py) CAD-to-scan deviation inspection — the fit absorbs the defect and invents a dent<br>[`poc_crack_width`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_crack_width.py) Concrete Crack Width Is Thinner Than a Pixel — Counting Width Versus Integrating Width<br>[`poc_crack_width_timeseries`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_crack_width_timeseries.py) Measuring the Growth, Not the Width — Rephotographing the Same Wall Changes What the Error Is<br>[`poc_datacenter_thermal_field`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_datacenter_thermal_field.py) A 3-D Thermal Field from Sparse Sensors — The Grid's Blind Spot Erases a Rack<br>[`poc_dic_strain`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dic_strain.py) Strain From Speckle Images (DIC)<br>[`poc_dimensional_inspection`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dimensional_inspection.py) Dimensional Inspection of a Machined Part — Bias and Scatter as Two Numbers<br>[`poc_fiber_orientation`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fiber_orientation.py) Fibre Orientation Distribution — Angles Repeat Every 180 Degrees, and a Naive Mean Is 90 Degrees Off<br>[`poc_gear_tooth_metrology`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_gear_tooth_metrology.py) Gear Tooth Metrology — Eccentricity Is Order 1, Teeth Are Order z<br>[`poc_geodetic_height_frames`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_geodetic_height_frames.py) Coordinates Go Wrong by Tens of Metres While Still Looking Plausible<br>[`poc_interferometry_step`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_interferometry_step.py) How Accurately a White-Light Interferometer Measures a Nanometre Step<br>[`poc_livestock_body_volume`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_livestock_body_volume.py) Weighing an Animal from Silhouettes — The Error You Can Buy Down, and the One You Cannot<br>[`poc_metal_grain_size`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_metal_grain_size.py) Metallographic Grain Size — The Planimetric and Intercept Methods Fall Off Different Cliffs<br>[`poc_multibeam_bathymetry`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_multibeam_bathymetry.py) Why the Seafloor Smiles — A Wrong Sound-Speed Profile Breaks Only the Outer Beams<br>[`poc_particle_sizing`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_particle_sizing.py) Particle Size Distribution From Images — Merging and Edge Cuts Pull Opposite Ways and Cancel<br>[`poc_photoelasticity`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_photoelasticity.py) Stress by Photoelasticity — Unwrapping Fails First at the Isotropic Point<br>[`poc_pipe_wall_loss`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pipe_wall_loss.py) Pipe Wall Loss on the Unwrapped Map — The Axis You Choose Eats the Invert Corrosion<br>[`poc_real_coin_metrology`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_coin_metrology.py) Counting and Measuring Real Coins — A Correct Answer Is Not a Safe One<br>[`poc_scan_to_bim_asbuilt`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_scan_to_bim_asbuilt.py) As-built deviation of a room — the compromise pose is handed to the innocent element<br>[`poc_screw_thread_metrology`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_screw_thread_metrology.py) Pitch, Flank Angle and Pitch Diameter From a Thread Silhouette — Tilt Shows Up With Opposite Signs on the Two Flanks<br>[`poc_settlement_significance`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_settlement_significance.py) Did It Settle, or Did We Just Scan It Again — What Changes When You Cut at the Detection Limit<br>[`poc_star_astrometry`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_star_astrometry.py) To What Fraction of a Pixel Can a Star Be Located, and Where Is the Cliff?<br>[`poc_stockpile_volume`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_stockpile_volume.py) Stockpile Inventory — The Answer Is Fixed by the Ground Nobody Measured<br>[`poc_strain_history`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_strain_history.py) Strain History in a Creep Test — Cumulative or Direct?<br>[`poc_structure_4d_deterioration`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_structure_4d_deterioration.py) Re-surveying a structure year by year — when the vantage moves, decay appears to advance<br>[`poc_surface_roughness`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_surface_roughness.py) How Far Sa / Sq / Sz Survive Sampling and Cutoff<br>[`poc_thermal_radiometry`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermal_radiometry.py) A Thermal Image Is Not a Temperature Image — Emissivity, Reflection, and an Uncertainty That Does Not Add<br>[`poc_tree_ring_dendro`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tree_ring_dendro.py) Counting tree rings and extracting the width series — ring count and width correlation fail separately<br>[`poc_water_level`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_water_level.py) River Stage From an Oblique Photo — Ignoring Perspective Bends the Row-Number Error Into an Arc<br>[`poc_weld_bead_profile`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_weld_bead_profile.py) Weld Bead From a Laser-Triangulation Profile — The Sin of Writing 0 Where Nothing Was Measured<br>[`poc_weld_bead_scan_angle`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_weld_bead_scan_angle.py) Light-section scanning of a weld bead — resolution and occlusion share one knob<br>[`poc_wound_area_tracking`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_wound_area_tracking.py) Wound Area Over Time — Calibration Error Enters the Area Squared |
| diagnostics (10) | [`poc_bearing_diagnosis`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bearing_diagnosis.py) Rolling-Bearing Diagnosis — How Deep in Noise Can It Still Be Caught?<br>[`poc_cold_chain_excursion`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cold_chain_excursion.py) The Cold-Chain Temperature Record — Where You Taped the Logger Is the Verdict<br>[`poc_fabric_defect`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fabric_defect.py) Defects Buried in a Periodic Background — What a Pooled ROC Hides<br>[`poc_machine_condition_fusion`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_machine_condition_fusion.py) Fusing thermal, vibration and geometry for machine health — three sensors, one fact<br>[`poc_prnu_camera_fingerprint`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_prnu_camera_fingerprint.py) Camera Fingerprints (PRNU): Which Camera Took This? — The Fingerprint Grows With Frame Count and Dies at the Save Button<br>[`poc_pv_thermal_survey`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pv_thermal_survey.py) Drone Thermography of a PV Plant — You Think You Are Measuring Temperature Difference, but You Are Measuring Wind and Viewing Angle<br>[`poc_solar_el_inspection`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_solar_el_inspection.py) Power loss from solar-cell EL images — dark is not the same as inactive<br>[`poc_solder_fillet_aoi`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_solder_fillet_aoi.py) Solder fillet AOI — three ring lights are a 3-level tilt quantiser, and 70 % of the fillet height sits in the dark<br>[`poc_thermography_ndt`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermography_ndt.py) Depth of a Subsurface Defect by Pulsed Thermography<br>[`poc_weld_radiograph_porosity`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_weld_radiograph_porosity.py) Porosity in Weld Radiographs — Closing With the Share of Images Misgraded by One Class |
| geometry (7) | [`poc_dfm_thickness_overhang`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dfm_thickness_overhang.py) Manufacturability from geometry alone — faces that sit on the threshold flip when you smooth them<br>[`poc_mesh_quality_repair`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_mesh_quality_repair.py) Repair the mesh, then measure — the defect count clears, the quantity does not<br>[`poc_pallet_load_utilization`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pallet_load_utilization.py) Pallet load utilization — one number gives voids and overhang the same value<br>[`poc_panorama_drift`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_panorama_drift.py) Chain the Neighbours Together and You Cannot Get Back Where You Started<br>[`poc_print_warpage_risk`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_print_warpage_risk.py) Warpage lives in the layer history — averaging the area throws the placement away<br>[`poc_symmetry_restoration`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_symmetry_restoration.py) Restoring what is missing by symmetry — the plane you assume is the lie you get<br>[`poc_xyt_event_surface`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_xyt_event_surface.py) The Arrival-Time Surface as an Isosurface in (x, y, t) |
| photometry (6) | [`poc_allsky_cloud_cover`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_allsky_cloud_cover.py) All-Sky Cloud Cover — Counting Pixels Is Biased by Position<br>[`poc_astro_photometry`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_astro_photometry.py) How Many Frames for What Photometric Precision?<br>[`poc_exoplanet_transit`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_exoplanet_transit.py) Exoplanet transit from aperture photometry — depth and duration fail separately<br>[`poc_nuclei_ploidy`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_nuclei_ploidy.py) Ploidy From Integrated Nuclear Intensity — Area Cannot Separate It<br>[`poc_real_sky_photometry`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_sky_photometry.py) Planting Known Stars in a Real Deep Field — Contamination Lies About the Measurement and the Confidence in the Same Direction<br>[`poc_solar_limb_darkening`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_solar_limb_darkening.py) Where Is the Edge of a Limb-Darkened Disc? The 50 % Rule Reads the Radius Small |
| separation (6) | [`poc_colocalization_crosstalk`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_colocalization_crosstalk.py) Colocalization lies under bleed-through — Pearson and Manders break in different places<br>[`poc_pigment_unmixing`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pigment_unmixing.py) Peeling Layers With Many Wavelengths — Underdrawing, Ground, Glaze and Fading, Truth in Hand<br>[`poc_polarization_specular`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_polarization_specular.py) Stripping Specular Reflection With Polarisation — Truth From the Fresnel Equations<br>[`poc_real_stain_unmix`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_stain_unmix.py) Separating a Real Immunostain by Colour — The Watchdog Was Blind to Exactly the Error It Should Catch<br>[`poc_recycling_sorting`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_recycling_sorting.py) Sorting mixed waste by material — what a preprocessor can erase is decided by algebra<br>[`poc_sea_ice_concentration`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_sea_ice_concentration.py) Sea-Ice Concentration — The Answer Depends on How Mixed Pixels Are Counted |
| segmentation (5) | [`poc_cell_counting`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cell_counting.py) Counting Overlapping Cells — Count, Over-Segmentation and Under-Segmentation as Three Numbers<br>[`poc_leaf_disease_area`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_leaf_disease_area.py) Leaf disease severity — colour axes survive the lighting; the grade is decided by the leaf mask and the edge convention<br>[`poc_mri_bias_field`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_mri_bias_field.py) MRI Bias Field and Tissue Area — Grey and White Matter Fail in Opposite Directions, and the Sum Hides It<br>[`poc_timelapse_growth`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_timelapse_growth.py) A Growth Time-Lapse as Space-Time Connected Components<br>[`poc_vegetation_cover`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_vegetation_cover.py) Counting Crop Green — Ground Truth as Per-Pixel Leaf Area Fraction |
| motion (4) | [`poc_particle_tracking`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_particle_tracking.py) Particle Tracking as a (row, column, time) Volume — Mislinks Come in Two Directions<br>[`poc_river_surface_velocity`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_river_surface_velocity.py) River surface velocity from an oblique video (LSPIV) — velocity error and discharge error are different numbers<br>[`poc_traffic_counting`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_traffic_counting.py) Counting in (x, y, t) — Vehicles Passed, Occlusion, and One Constant: L/V<br>[`poc_warehouse_flow`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_warehouse_flow.py) Where the Warehouse Dwell Came From — Count Waiting Without Its Kind and Everything Is Just Congestion |
| registration (4) | [`poc_change_detection_misreg`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_change_detection_misreg.py) Change detection under misregistration — false positives are edge bands, with a cliff<br>[`poc_print_registration`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_print_registration.py) Print Misregistration from the Sheet — A Halftone Is a Lattice, So the Answer Is Not Unique<br>[`poc_registration_basin`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_registration_basin.py) The Convergence Basin of Point-Cloud Registration — How Far Off Can the Initial Pose Be?<br>[`poc_template_tracking`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_template_tracking.py) Template Tracking Drifts Quietly Before It Ever Loses the Target |
| tomography_3d (4) | [`poc_battery_ct_degradation`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_battery_ct_degradation.py) Battery cell degradation by CT — the swelling shows outside, the cause stays inside<br>[`poc_battery_electrode_tortuosity`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_battery_electrode_tortuosity.py) Electrode tortuosity from CT — the rule of thumb only sees porosity<br>[`poc_ct_void_morphology`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_void_morphology.py) Collapsing joint voids into one number — what the number drops is the shape that matters<br>[`poc_die_tilt_tsv_overlay`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_die_tilt_tsv_overlay.py) Die tilt and TSV overlay from one CT — tilt fakes rotation too |
| depth (3) | [`poc_focus_stacking`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_focus_stacking.py) Focus Stacking — The All-in-Focus Image and the Depth Map Are Different Things<br>[`poc_lightfield_depth`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lightfield_depth.py) Depth From a Light Field — A Light Field of Known Depth, Confronted With Its Nulls<br>[`poc_real_stereo_depth`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_stereo_depth.py) Measuring on a Real Stereo Photograph — Three Stumbles Synthesis Never Produces |
| imaging quality (3) | [`poc_colormap_readability`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_colormap_readability.py) Pseudo-colour changes what the reader decides — counting edges that are not there<br>[`poc_moire_screen`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_moire_screen.py) Can Display-Inspection Moire Be Told From Real Non-Uniformity?<br>[`poc_veiling_glare`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_veiling_glare.py) Veiling Glare Breaks Contrast Measurement — MTF Passes While Black Level Fails |
| restoration (3) | [`poc_camera_shake_deblur`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_camera_shake_deblur.py) How Much Camera Shake Can Be Undone — Make the Kernel, Apply It, Invert It, Compare<br>[`poc_dehazing`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dehazing.py) Removing Haze — Ground Truth From the Scattering Model, Transmission and Airlight Scored Apart<br>[`poc_real_deblur_honesty`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_deblur_honesty.py) Deblurring a Real Photograph — Three Rulers, Three Different Winners |
| terrain (3) | [`poc_crop_phenotyping`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_crop_phenotyping.py) Crop leaf area from above — folded by projection before it is ever hidden<br>[`poc_dem_terrain`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dem_terrain.py) Measuring Terrain — Slope, Flow and Insolation Against Closed Forms<br>[`poc_lidar_terrain_change`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lidar_terrain_change.py) Earthwork on a slope — align first and the scar gets shallower |
| calibration (2) | [`poc_camera_calibration`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_camera_calibration.py) A Reprojection Error of 0.05 px Guarantees Nothing<br>[`poc_thermal_drift_metrology`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermal_drift_metrology.py) How Much Camera Thermal Drift Costs a Dimensional Measurement |
| decoding (2) | [`poc_barcode_1d`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_barcode_1d.py) Where a 1-D Barcode Stops Reading — Counting Misreads and Unreadables Separately<br>[`poc_matrix_code_reading`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_matrix_code_reading.py) Reading a Binary Matrix Code — Geometry Always Dies First |
| detection (2) | [`poc_real_defect_floor`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_defect_floor.py) How Faint a Defect Can Still Be Found — Planting a Known Truth in a Real Background<br>[`poc_search_sweep_width`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_search_sweep_width.py) Sweep Width — One Number Measured from Aerial Images Decides Whether the Search Works |
| forensics (2) | [`poc_forensics_roc`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_forensics_roc.py) Forgery Detection as an ROC — Not the One Image Found, but Detection at a Fixed False-Positive Rate<br>[`poc_fresco_craquelure`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fresco_craquelure.py) Craquelure networks — of three indicators, only junction degree breaks under imaging conditions |
| morphology (2) | [`poc_bilateral_asymmetry`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bilateral_asymmetry.py) Measuring Bilateral Asymmetry — The Symmetry Plane Gets Dragged by the Deformation<br>[`poc_vessel_network`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_vessel_network.py) Extracting a Vessel Network — Spurs, Overestimated Radii Near Branches, and a Fragile Exponent |
| perception_templates (2) | [`poc_bev_sensor_fusion`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bev_sensor_fusion.py) Fusing two sensors into a bird's-eye grid — a calibration that passes in pixels turns into metres at range<br>[`poc_safety_clearance`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_safety_clearance.py) Human-machine clearance — swap the body for a point, and the hazard vanishes with it |
| ranging (2) | [`poc_dtof_ranging`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dtof_ranging.py) Ranging by Counting Photons — How Many for How Many Millimetres?<br>[`poc_leak_localization`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_leak_localization.py) Digging Where the Sound Says — A Clean Correlation Still Digs in the Wrong Place |
| shape_descriptors (2) | [`poc_real_texture_invariance`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_texture_invariance.py) Rotating Real Textures — Rotation Invariance Holds Only Where It Is Not Needed<br>[`poc_rotation_invariance_audit`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_rotation_invariance_audit.py) Which Quantities Really Survive a Rotation — Auditing Invariance on a Real Coin |
| signal_processing (2) | [`poc_rail_corrugation`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_rail_corrugation.py) Measuring Rail with a Chord — At the Wavelengths Where the Transfer Function Is Zero, Any Amplitude Reads Zero<br>[`poc_web_roll_periodicity`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_web_roll_periodicity.py) Naming the Damaged Roller from a Period — You Run Out of Evidence Before You Reach the Cliff |
| vibration (2) | [`poc_beam_modal_video`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_beam_modal_video.py) Modal identification from video — frequency survives to the end, damping lies first<br>[`poc_motion_magnification`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_motion_magnification.py) Micro-Vibration of a Structure From Video — Does Motion Magnification Help You Measure? |
| colour (1) | [`poc_white_balance`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_white_balance.py) Colour Constancy (White Balance) — No Method Works, Only Conditions Do |
| rectification (1) | [`poc_document_scan`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_document_scan.py) Straightening a Hand-Held Document Photo — Keystone Correction and Shadow Removal Against Ground Truth |
| tomography (1) | [`poc_ct_fidelity`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_fidelity.py) Where CT Reconstruction Starts to Break as Projections Are Removed |
| super-resolution (1) | [`poc_superresolution_limits`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_superresolution_limits.py) Does Super-Resolution Add Information? Downsample With the Truth in Hand, Restore, Count |

<!-- poc-index:end -->

<!-- ops-index:start -->

## 查找算子

共有 **1,929 篇算子说明**(调用形式、类型契约、HALCON 对应、参考文献、来源)与 **49 篇族指南**。按维度的入口:

**实测覆盖**: 演化算子 899/899、类型化台账 1009/1021、单行门面 `fullseye.<名称>` 544/1117 —— **门面侧仅覆盖一半**。

**内容实测**: 1934 篇中，附有可运行示例的 **1894** 篇(40 篇没有)，用法说明 120 字以上的 **1915** 篇(19 篇仅一行)。结构(调用形式、类型、可衔接算子)1934 篇全有。

| 维度 | 算子数 | 入口 |
|---|---:|---|
| `2d` | 916 | [INDEX](ops/2d/INDEX.md) |
| `3d` | 357 | [INDEX](ops/3d/INDEX.md) |
| `optics` | 124 | [INDEX](ops/optics/INDEX.md) · [guide](ops/optics/guides/optics_imaging.md) |
| `annotate` | 51 | [INDEX](ops/annotate/INDEX.md) · [guide](ops/annotate/guides/figure_annotation.md) |
| `reprconv` | 42 | [INDEX](ops/reprconv/INDEX.md) |
| `oned` | 39 | [INDEX](ops/oned/INDEX.md) |
| `gfx2d` | 32 | [INDEX](ops/gfx2d/INDEX.md) |
| `math` | 27 | [INDEX](ops/math/INDEX.md) · [guide](ops/math/guides/math_metrology.md) |
| `piv` | 26 | [INDEX](ops/piv/INDEX.md) · [guide](ops/piv/guides/piv_displacement.md) |
| `imgmetrics` | 24 | [INDEX](ops/imgmetrics/INDEX.md) · [guide](ops/imgmetrics/guides/image_difference_metrics.md) |
| `acoustics` | 20 | [INDEX](ops/acoustics/INDEX.md) · [guide](ops/acoustics/guides/acoustic_condition_monitoring.md) |
| `dem` | 19 | [INDEX](ops/dem/INDEX.md) · [guide](ops/dem/guides/dem_terrain_analysis.md) |
| `quat` | 19 | [INDEX](ops/quat/INDEX.md) · [guide](ops/quat/guides/quaternion_monogenic.md) |
| `lightfield` | 17 | [INDEX](ops/lightfield/INDEX.md) · [guide](ops/lightfield/guides/lightfield_depth.md) |
| `photon` | 17 | [INDEX](ops/photon/INDEX.md) · [guide](ops/photon/guides/photon_timeresolved.md) |
| `tomography` | 17 | [INDEX](ops/tomography/INDEX.md) |
| `imgforensics` | 16 | [INDEX](ops/imgforensics/INDEX.md) |
| `shapestat` | 16 | [INDEX](ops/shapestat/INDEX.md) · [guide](ops/shapestat/guides/shape_statistics.md) |
| `videostream` | 16 | [INDEX](ops/videostream/INDEX.md) · [guide](ops/videostream/guides/video_streaming.md) |
| `astrostack` | 14 | [INDEX](ops/astrostack/INDEX.md) |
| `measure1d` | 14 | [INDEX](ops/measure1d/INDEX.md) · [guide](ops/measure1d/guides/subpixel_measuring.md) |
| `shape2d` | 13 | [INDEX](ops/shape2d/INDEX.md) · [guide](ops/shape2d/guides/shape_description_2d.md) |
| `specular` | 13 | [INDEX](ops/specular/INDEX.md) · [guide](ops/specular/guides/specular_photometric.md) |
| `profile` | 12 | [INDEX](ops/profile/INDEX.md) · [guide](ops/profile/guides/profile_metrology.md) |
| `colortransport` | 11 | [INDEX](ops/colortransport/INDEX.md) |
| `volcolor` | 11 | [INDEX](ops/volcolor/INDEX.md) |
| `blob` | 10 | [INDEX](ops/blob/INDEX.md) · [guide](ops/blob/guides/blob_analysis.md) |
| `interferometry` | 9 | [INDEX](ops/interferometry/INDEX.md) · [guide](ops/interferometry/guides/coherence_scanning.md) |
| `motionmag` | 9 | [INDEX](ops/motionmag/INDEX.md) · [guide](ops/motionmag/guides/motion_magnification.md) |
| `rangedoppler` | 8 | [INDEX](ops/rangedoppler/INDEX.md) · [guide](ops/rangedoppler/guides/fmcw_range_doppler.md) |
| `roughness` | 6 | [INDEX](ops/roughness/INDEX.md) · [guide](ops/roughness/guides/surface_roughness.md) |
| `cadmap` | 4 | [INDEX](ops/cadmap/INDEX.md) |

按名称检索用 `py -3.11 imgevolve.py ops --search edge`;全部算子的对照表见 [OP_CATALOG.md](OP_CATALOG.md)，跨维度入口见 [ops/INDEX.md](ops/INDEX.md)。

**供 AI 检索**: 机器可读索引 [`OP_INDEX.json`](OP_INDEX.json)，用法见 [AI_RAG_GUIDE.md](AI_RAG_GUIDE.md)。

<!-- ops-index:end -->

## 用法（面向使用者 —— 先看这四篇）

| 文档 | 内容 |
|---|---|
| **[GETTING_STARTED.md](GETTING_STARTED.md)** | 5 分钟上手：安装 → 第一条流水线 → 在 Studio／CLI／代码中运行 → 查看结果 |
| **[INSTALL.md](INSTALL.md)** | 环境搭建完整指南：前置条件、`pip install -e .` 与各 extras 的取舍、Windows／Linux 安装器、最小配置与嵌入式集成、疑难排查 |
| **[STUDIO_GUIDE.md](STUDIO_GUIDE.md)** | Fullseye Studio 完整指南：三面板、算子浏览器、单步执行、参数旋钮、Inspector、感知面板、命令面板、快捷键、导出 |
| **[ENGINE.md](ENGINE.md)** | FullseyeEngine（设计 → 执行）：全部方法、在 Python 中的用法、CLI `run`、从其他项目中调用 |

---

## 算子 / API 参考

| 文档 | 内容 |
|---|---|
| [OPERATORS.md](OPERATORS.md) | 全部 897 个算子的目录（48 个类别，按 sort 分组，并列出 HALCON／OpenCV／scikit-image／MATLAB 的对应 API） |
| [EXAMPLES.md](EXAMPLES.md) | 逐个算子的示例代码（附其他库中的等价调用） |
| [OP_INDEX.json](OP_INDEX.json) | 机器可读的算子索引（用 `imgevolve.py index` 重新生成） |
| [ADDING_OPS.md](ADDING_OPS.md) | 如何新增算子（演化、codegen、目录与索引都会自动跟进） |
| [../examples/README.md](../examples/README.md) | 可直接运行的端到端示例脚本集 |

## 感知栈（机器人 / 视觉）

| 文档 | 内容 |
|---|---|
| [PERCEPTION.md](PERCEPTION.md) | 感知栈单页速查（stereo／terrain／detect／registration／pose／flow／motion） |
| [PERCEPTION_REALDATA.md](PERCEPTION_REALDATA.md) | 在实拍视频片段上的测量结果（视频 I/O ＋ 诚实给出的实测数值） |

## HALCON 对等性 / 覆盖率（诚实披露 honest disclosure）

| 文档 | 内容 |
|---|---|
| [HALCON_PARITY.md](HALCON_PARITY.md) | genuine（真正等效）实现的进展（979/2313）：不是“只有名字相同”，而是确实能做同样的处理 |
| [HALCON_COVERAGE.md](HALCON_COVERAGE.md) | 通过真实抓取官方参考手册（v2605）得到的覆盖率测量 |
| [LIB_COVERAGE.md](LIB_COVERAGE.md) | 跨多个库的覆盖情况（吸收 HALCON 之外具有特色的算子） |
| [PARITY_CROSSBACKEND.md](PARITY_CROSSBACKEND.md) | 以多个独立实现（scipy／cv2／skimage）之间的跨后端一致性来证明对等性 |

## 质量 / 溯源 / 复现

| 文档 | 内容 |
|---|---|
| [ACCURACY_BENCH.md](ACCURACY_BENCH.md) | 常设精度表：演化得到的 champion 对比 null 基线（holdout） |
| [CHAIN_FUZZ.md](CHAIN_FUZZ.md) | 链式 fuzzer——把算子串成链条施加扰动的第三层质量保障（扩散 → 收敛 → 最小复现） |
| [EVOLUTION_ENVIRONMENT.md](EVOLUTION_ENVIRONMENT.md) | 演化式算法开发环境（扩散 → 收缩 → 晋级；counterfactual utility 闸门，以及连接两个算子宇宙的桥） |
| [PROVENANCE.md](PROVENANCE.md) | 溯源：说明这些实现都是依据公开算法自行编写而成 |
| [REFERENCES.md](REFERENCES.md) | 每个算子的文献依据 |
| [REPRODUCE.md](REPRODUCE.md) | 数值复现步骤：由 seed 驱动、结果确定 |
| [STATUS.md](STATUS.md) | 项目当前所处的位置与后续计划（plan_ref） |

## 发行说明 / 设计

| 文档 | 内容 |
|---|---|
| [V13.md](V13.md) | v13 ＝ 走向实用 ＋ 跨项目 packaging ＋ 感知栈 |
| [V14.md](V14.md) | v14 ＝ 感知栈完成（运动 ＋ 健壮化） |
| [STUDIO_UX.md](STUDIO_UX.md) | Fullseye Studio 在 UX／设计上的改进意图与来龙去脉 |

---

## 快捷命令

```powershell
py -3.11 -m pip install -e ".[opencv,gui]"     # 安装（图像 I/O + Studio）
py -3.11 studio.py                              # 启动 Fullseye Studio（= fullseye-studio）
py -3.11 imgevolve.py ops --search edge         # 搜索算子（= fullseye ops --search edge）
py -3.11 imgevolve.py apply gauss_filter in.png out.png --a 0.6
py -3.11 imgevolve.py run pipeline.json in.png --out result.png
py -3.11 imgevolve.py coverage                  # 诚实的覆盖数字
```

在 Python 中：

```python
import fullseye, numpy as np
out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])
eng = fullseye.FullseyeEngine.load("pipeline.json"); result = eng.run(frame)
```

---

![经典 2-D 视觉算子的真实输出](articles/assets/vision_ops_montage.png)

*经典 2-D 视觉算子的真实输出*

![Physical AI 与传感器仿真的真实输出](articles/assets/physical_ai_montage.png)

*Physical AI 与传感器仿真的真实输出*

<!-- docmap:start -->

## 文档地图 — 共 107 篇

完整地图，确保**没有任何文档无法从索引到达**(`docs/ops/` 下的 1,929 篇算子说明与 49 篇族群指南从上面的「查找算子」进入; 文章见 [articles/](articles/README.md))。**正文多为日语。**

**Getting started**(12)

| 文档 | 内容 |
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

| 文档 | 内容 |
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

| 文档 | 内容 |
|---|---|
| [`AI_RAG_GUIDE.md`](AI_RAG_GUIDE.md) | Fullseye を AI アシスタントの RAG にする手順(Claude Code 向け) _(ja)_ |

**Perception and sensors**(6)

| 文档 | 内容 |
|---|---|
| [`PERCEPTION.md`](PERCEPTION.md) | Fullseye perception stack — one-page reference |
| [`PERCEPTION_PHYSICAL_AI.md`](PERCEPTION_PHYSICAL_AI.md) | Physical-AI perception pipeline (fullseye / imgevolve, v18.3, 2026-08-15) |
| [`PERCEPTION_REALDATA.md`](PERCEPTION_REALDATA.md) | v15 — perception stack on real footage (video I/O + honest field measurements) |
| [`SENSOR_PLAYBOOK.md`](SENSOR_PLAYBOOK.md) | Fullseye Sensor Playbook — センサー種別ごとの推奨 op パイプライン _(ja)_ |
| [`HIGHSPEED_VISION.md`](HIGHSPEED_VISION.md) | 高速ビジョン(1ms 視覚フィードバック)を物理シミュ上でやる — 計画 _(ja)_ |
| [`SAMPLE_IMAGE_REFERENCES.md`](SAMPLE_IMAGE_REFERENCES.md) | Sample images — provenance, source papers & public repositories |

**HALCON correspondence**(6)

| 文档 | 内容 |
|---|---|
| [`HALCON_PARITY.md`](HALCON_PARITY.md) | HALCON parity — what imgevolve genuinely DOES (not just names) |
| [`HALCON_COVERAGE.md`](HALCON_COVERAGE.md) | HALCON operator coverage (measured vs the real reference) |
| [`HALCON_COVERAGE_HONEST.md`](HALCON_COVERAGE_HONEST.md) | HALCON カバレッジ — honest な分母(2026-08-18 更新) _(ja)_ |
| [`HDEVELOP_FIDELITY.md`](HDEVELOP_FIDELITY.md) | Fullseye Studio — HDevelop 忠実化スペック(北極星) _(ja)_ |
| [`HDEVELOP_DEV_OPS.md`](HDEVELOP_DEV_OPS.md) | HDevelop `dev_*` operator family — the UI/display control surface (Studio 北極星) |
| [`LIB_COVERAGE.md`](LIB_COVERAGE.md) | Multi-library coverage (imgevolve is not HALCON-only) |

**Fullseye Script**(3)

| 文档 | 内容 |
|---|---|
| [`FSCRIPT_DECISION.md`](FSCRIPT_DECISION.md) | Fullseye Script / Runtime — 要件定義と基本設計(確定案) _(ja)_ |
| [`FSCRIPT_LANGUAGE.md`](FSCRIPT_LANGUAGE.md) | Fullseye Script — 言語 / ランタイム / ウォッチ IDE 設計仕様(北極星) _(ja)_ |
| [`FSCRIPT_MEASUREMENTS.md`](FSCRIPT_MEASUREMENTS.md) | Fullseye Runtime — 実測記録 (2026-08-15) |

**Quality and honesty**(11)

| 文档 | 内容 |
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

| 文档 | 内容 |
|---|---|
| [`GPU_ACCEL_PLAN.md`](GPU_ACCEL_PLAN.md) | op の GPU 化ロードマップ(E2E の本丸) _(ja)_ |
| [`GPU_OPTIMIZATION_PATTERNS.md`](GPU_OPTIMIZATION_PATTERNS.md) | GPU 最適化デザインパターン・カタログ(RTX 5090 / Blackwell sm_120 向け) _(ja)_ |
| [`design/FAST_TWINS.md`](design/FAST_TWINS.md) | CPU 高速 twin(`fast.py`)— 実装記録と実測(2026-09-03) _(ja)_ |
| [`design/PERF_MEMORY_VIDEO_SURVEY.md`](design/PERF_MEMORY_VIDEO_SURVEY.md) | op の高速化・省メモリ化・動画処理 — 実測にもとづく調査報告(2026-09-03) _(ja)_ |

**Design and architecture**(7)

| 文档 | 内容 |
|---|---|
| [`ENGINE.md`](ENGINE.md) | FullseyeEngine — 設計したパイプラインを実行するランタイム _(ja)_ |
| [`EVOLUTION_ENVIRONMENT.md`](EVOLUTION_ENVIRONMENT.md) | 進化型アルゴリズム開発環境 — 拡散・収縮・昇格 _(ja)_ |
| [`INTEGRATION.md`](INTEGRATION.md) | Depending on Fullseye from another project (stability contract) |
| [`UNIFIED_API_REQUIREMENTS.md`](UNIFIED_API_REQUIREMENTS.md) | Fullseye 統一インターフェース — 要件定義書 (v0.1, 2026-08-18) _(ja)_ |
| [`design/TRIZ_DESIGN_PATTERN_MATRIX.md`](design/TRIZ_DESIGN_PATTERN_MATRIX.md) | TRIZ 40 発明原理 × ソフトウェア設計パターン × コンテナ型 — 構造選択マトリクス(fullseye) _(ja)_ |
| [`EVIS_VISION_OSS_GAP.md`](EVIS_VISION_OSS_GAP.md) | evis の視覚部品 — OSS/ROS2 ギャップ分析 (2026-08-17) _(ja)_ |
| [`INDUSTRY_SIGNALS.md`](INDUSTRY_SIGNALS.md) | 業界シグナル — 展示会・アワードを op 発想の恒常的な入力にする _(ja)_ |

**Working notes and plans (historical; numbers are as of their date)**(12)

| 文档 | 内容 |
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

**Other**(36)

| 文档 | 内容 |
|---|---|
| [`CAPABILITIES.en.md`](CAPABILITIES.en.md) | What Fullseye can do |
| [`CAPABILITIES.md`](CAPABILITIES.md) | Fullseye でできること _(ja)_ |
| [`DESIGN_NOTES.de.md`](DESIGN_NOTES.de.md) | Fullseye-Entwurfsnotizen (aus den ★-Kommentaren im Quellcode erzeugt) |
| [`DESIGN_NOTES.en.md`](DESIGN_NOTES.en.md) | Fullseye design notes (generated from the ★ comments in the source) |
| [`DESIGN_NOTES.ko.md`](DESIGN_NOTES.ko.md) | Fullseye 설계 판단 모음(소스의 ★ 주석에서 생성) |
| [`DESIGN_NOTES.md`](DESIGN_NOTES.md) | Fullseye 設計判断集(ソース中の ★ コメントから生成) _(ja)_ |
| [`DESIGN_NOTES.tw.md`](DESIGN_NOTES.tw.md) | Fullseye 設計判斷集（由原始碼中的 ★ 註解產生） |
| [`DESIGN_NOTES.zh.md`](DESIGN_NOTES.zh.md) | Fullseye 设计判断集（由源码中的 ★ 注释生成） |
| [`HARDENING.en.md`](HARDENING.en.md) | What the PoCs hardened — found, fixed, and gated |
| [`HARDENING.md`](HARDENING.md) | PoC が上げた堅牢性 —— 見つけて直した記録 _(ja)_ |
| [`I18N_PLAN.md`](I18N_PLAN.md) | 完全な多言語化 — 計画と現在地 _(ja)_ |
| [`MATURITY.md`](MATURITY.md) | 成熟度台帳(Maturity) |
| [`capabilities/align-and-stack.md`](capabilities/align-and-stack.md) | id: align-and-stack |
| [`capabilities/beamforming-and-range-doppler.md`](capabilities/beamforming-and-range-doppler.md) | id: beamforming-and-range-doppler |
| [`capabilities/blob-and-region.md`](capabilities/blob-and-region.md) | id: blob-and-region |
| [`capabilities/colour-and-delta-e.md`](capabilities/colour-and-delta-e.md) | id: colour-and-delta-e |
| [`capabilities/figures-and-annotation.md`](capabilities/figures-and-annotation.md) | id: figures-and-annotation |
| [`capabilities/geodetic-frames.md`](capabilities/geodetic-frames.md) | id: geodetic-frames |
| [`capabilities/inverted-colour-overlays.md`](capabilities/inverted-colour-overlays.md) | id: inverted-colour-overlays |
| [`capabilities/optics-and-materials.md`](capabilities/optics-and-materials.md) | id: optics-and-materials |
| [`capabilities/point-target-detection.md`](capabilities/point-target-detection.md) | id: point-target-detection |
| [`capabilities/subpixel-2d-metrology.md`](capabilities/subpixel-2d-metrology.md) | id: subpixel-2d-metrology |
| [`capabilities/terrain-and-visibility.md`](capabilities/terrain-and-visibility.md) | id: terrain-and-visibility |
| [`capabilities/text-and-tables-on-images.md`](capabilities/text-and-tables-on-images.md) | id: text-and-tables-on-images |
| [`capabilities/tomography-reconstruction.md`](capabilities/tomography-reconstruction.md) | id: tomography-reconstruction |
| [`capabilities/vibration-and-acoustics.md`](capabilities/vibration-and-acoustics.md) | id: vibration-and-acoustics |
| [`capabilities/visual-hull-from-silhouettes.md`](capabilities/visual-hull-from-silhouettes.md) | id: visual-hull-from-silhouettes |
| [`capabilities/volume-from-3d-scan.md`](capabilities/volume-from-3d-scan.md) | id: volume-from-3d-scan |
| [`hardening/carve-look-at-unreachable-and-silent.md`](hardening/carve-look-at-unreachable-and-silent.md) | id: carve-look-at-unreachable-and-silent |
| [`hardening/dem-viewshed-self-occlusion.md`](hardening/dem-viewshed-self-occlusion.md) | id: dem-viewshed-self-occlusion |
| [`hardening/ecef-to-geodetic-returned-latitude-180.md`](hardening/ecef-to-geodetic-returned-latitude-180.md) | id: ecef-to-geodetic-returned-latitude-180 |
| [`hardening/frame-align-inlier-ratio-is-not-confidence.md`](hardening/frame-align-inlier-ratio-is-not-confidence.md) | id: frame-align-inlier-ratio-is-not-confidence |
| [`hardening/moment-invariants-two-families-same-name.md`](hardening/moment-invariants-two-families-same-name.md) | id: moment-invariants-two-families-same-name |
| [`hardening/noise-sigma-mad-collapses-on-quantised-data.md`](hardening/noise-sigma-mad-collapses-on-quantised-data.md) | id: noise-sigma-mad-collapses-on-quantised-data |
| [`hardening/op-find-blind-to-japanese-queries.md`](hardening/op-find-blind-to-japanese-queries.md) | id: op-find-blind-to-japanese-queries |
| [`hardening/refract-one-way-reference.md`](hardening/refract-one-way-reference.md) | id: refract-one-way-reference |

<!-- docmap:end -->
