# Fullseye のファイル形式棚卸し

この表は `tools/audit_file_formats.py` が実装モジュール、`docs/OP_INDEX.json`、テストを静的走査して生成する。
拡張子や関数を手で数えた表ではない。`—` は、ソース上で対応する公開関数または検証を確認できなかったことを示す。

| 形式 | 拡張子 | 読む関数 | 書く関数 | 公開 op | 依存 | テスト | 独立の読み手で検証 |
|---|---|---|---|---|---|---|---|
| Zemax glass catalog | `.agf` | `materials.read_glass_catalog_agf` | — | `read_glass_catalog_agf` | stdlib / core | `tests/test_lensfile.py`<br>`tests/test_materials.py` | — |
| XYZ text | `.asc` | `mesh.read_points` | `mesh.write_points` | — | stdlib / core | `tests/test_abi_apply.py`<br>`tests/test_abi_wheel.py`<br>+18 | — |
| AVI video | `.avi` | — | `video.write_video` | — | optional: PIL, cv2, imageio | `tests/test_gen_visionlab_video.py`<br>`tests/test_perf_batch20_2026_10_20.py`<br>+2 | — |
| BMP | `.bmp` | `raster.read_raster` | — | — | optional: cv2, imageio, tifffile | `tests/test_iqatid.py`<br>`tests/test_raster.py`<br>+1 | — |
| CSV | `.csv` | `cutting.cut_force_csv_load`<br>`grind.ae_read_csv` | — | `ae_read_csv`<br>`cut_force_csv_load` | optional: mujoco | `tests/test_cutting.py`<br>`tests/test_doseunif.py`<br>+8 | `csv` |
| DICOM | `.dcm` | `volio.read_volume` | `volio.write_volume` | — | optional: SimpleITK, tifffile | `tests/test_public_api.py`<br>`tests/test_volio.py` | — |
| DICOM | `.dicom` | `volio.read_volume` | `volio.write_volume` | — | optional: SimpleITK, tifffile | `tests/test_public_api.py`<br>`tests/test_volio.py` | — |
| GIF | `.gif` | — | `examplefig.save_gif`<br>`projmap.save_gif`<br>`videocube.video_write_gif` | `video_write_gif` | optional: PIL, imageio, mujoco | `tests/test_docs_index_reachable.py`<br>`tests/test_examplefig_gif.py`<br>+9 | — |
| glTF | `.gltf` | `meshio_opt.read_gltf`<br>`meshio_opt.read_gltf_merged` | — | — | optional: pypcd4 | `tests/test_mesh.py`<br>`tests/test_meshio_opt.py`<br>+1 | — |
| Radiance HDR | `.hdr` | `volio.read_volume` | `specops.write_envi`<br>`volio.write_volume` | — | optional: SimpleITK, tifffile | `tests/test_public_api.py`<br>`tests/test_specops.py`<br>+2 | — |
| IMG | `.img` | `volio.read_volume` | `specops.write_envi`<br>`volio.write_volume` | — | optional: SimpleITK, tifffile | `tests/test_public_api.py`<br>`tests/test_specops.py`<br>+3 | — |
| JPEG | `.jpeg` | `raster.read_raster` | — | — | optional: cv2, imageio, tifffile | `tests/test_docs_index_reachable.py`<br>`tests/test_imgforensics.py`<br>+2 | — |
| JPEG | `.jpg` | `raster.read_raster` | — | — | optional: cv2, imageio, tifffile | `tests/test_docs_index_reachable.py`<br>`tests/test_help_rendering.py`<br>+11 | — |
| JSON | `.json` | `backends_auto.load_specs`<br>`fullseye.jsonio.load_json` | `fullseye.jsonio.save_json` | — | optional: cv2, skimage | `tests/test_accel_bridge.py`<br>`tests/test_accel_match.py`<br>+127 | — |
| LAS | `.las` | `meshio_opt.read_las` | — | — | optional: pypcd4 | `tests/test_backends.py`<br>`tests/test_coherent.py`<br>+6 | — |
| M4V | `.m4v` | — | `video.write_video` | — | optional: PIL, cv2, imageio | `tests/test_gen_visionlab_video.py`<br>`tests/test_perf_batch20_2026_10_20.py`<br>+2 | — |
| MetaImage | `.mha` | `volio.read_volume` | `volio.write_volume` | — | optional: SimpleITK, tifffile | `tests/test_public_api.py`<br>`tests/test_volio.py` | — |
| MetaImage | `.mhd` | `volio.read_volume` | `volio.write_volume` | — | optional: SimpleITK, tifffile | `tests/test_public_api.py`<br>`tests/test_volio.py` | — |
| Matroska video | `.mkv` | — | `video.write_video` | — | optional: PIL, cv2, imageio | `tests/test_gen_visionlab_video.py`<br>`tests/test_perf_batch20_2026_10_20.py`<br>+2 | — |
| MODEL | `.model` | `printpath.read_3mf` | — | `read_3mf` | stdlib / core | `tests/test_ledger_probe_fresh_cwd.py`<br>`tests/test_optdraw.py`<br>+2 | — |
| MOV | `.mov` | — | `video.write_video` | — | optional: PIL, cv2, imageio | `tests/test_anomaly_patch.py`<br>`tests/test_astrostack_median.py`<br>+12 | — |
| MP4 | `.mp4` | — | `video.write_video` | — | optional: PIL, cv2, imageio | `tests/test_docs_index_reachable.py`<br>`tests/test_examplefig_gif.py`<br>+7 | — |
| NHDR | `.nhdr` | `volio.read_volume` | `volio.write_volume` | — | optional: SimpleITK, tifffile | `tests/test_public_api.py`<br>`tests/test_volio.py` | — |
| NIfTI | `.nii` | `volio.read_volume` | `volio.write_volume` | — | optional: SimpleITK, tifffile | `tests/test_public_api.py`<br>`tests/test_volio.py` | — |
| NII.GZ | `.nii.gz` | `volio.read_volume` | `volio.write_volume` | — | optional: SimpleITK, tifffile | `tests/test_public_api.py`<br>`tests/test_volio.py` | — |
| NumPy array | `.npy` | `mesh.read_points`<br>`motionio.read_events`<br>`volio.read_volume` | `mesh.write_points`<br>`studio_display.save_outputs`<br>`volio.write_volume` | `read_events` | optional: SimpleITK, tifffile | `tests/test_capabilities.py`<br>`tests/test_examples3d.py`<br>+20 | — |
| NumPy archive | `.npz` | `mesh.read_points`<br>`motionio.read_events`<br>`volio.read_volume` | `mesh.write_points`<br>`volio.write_volume` | `read_events` | optional: SimpleITK, tifffile | `tests/test_carlabridge.py`<br>`tests/test_itokawa_anim3d.py`<br>+13 | — |
| NRRD | `.nrrd` | `volio.read_volume` | `volio.write_volume` | — | optional: SimpleITK, tifffile | `tests/test_public_api.py`<br>`tests/test_volio.py` | — |
| Wavefront OBJ | `.obj` | `driveworld.read_obj_colored`<br>`mesh.read_mesh`<br>`mesh.read_points` | `mesh.write_mesh` | — | optional: PIL | `tests/test_abi_apply.py`<br>`tests/test_audit_0_7_1_fixes_2026_10_21.py`<br>+12 | — |
| Geomview OFF | `.off` | `mesh.read_mesh`<br>`mesh.read_points` | `mesh.write_mesh` | — | stdlib / core | `tests/test_audit_file_formats.py`<br>`tests/test_drivelateral.py`<br>+7 | — |
| PBM | `.pbm` | — | `imgio.save` | — | optional: PIL, cv2 | `tests/test_acquire.py`<br>`tests/test_acquire_contract.py`<br>+58 | — |
| PCL PCD | `.pcd` | `mesh.read_points`<br>`meshio_opt.read_pcd` | — | — | optional: pypcd4 | `tests/test_mesh.py`<br>`tests/test_meshio_opt.py`<br>+2 | — |
| PFM | `.pfm` | `raster.read_depth`<br>`raster.read_pfm`<br>`raster.read_raster` | `imgio.save`<br>`raster.write_pfm` | — | optional: PIL, cv2, imageio, tifffile | `tests/test_acquire.py`<br>`tests/test_acquire_contract.py`<br>+60 | — |
| PGM | `.pgm` | — | `imgio.save` | — | optional: PIL, cv2 | `tests/test_acquire.py`<br>`tests/test_acquire_contract.py`<br>+58 | — |
| Stanford PLY | `.ply` | `gsplatnp.gs_read_file`<br>`mesh.read_mesh`<br>`mesh.read_points` | `gsplat_train_native.save_gaussians_ply`<br>`imgio.save_ply`<br>`mesh.write_mesh`<br>`mesh.write_points` | `gs_read_file` | 必須: PIL, gsplat, torch<br>optional: PIL, cv2, gsplat | `tests/test_audit_file_formats.py`<br>`tests/test_gsviewer.py`<br>+10 | — |
| PNG | `.png` | `raster.read_depth`<br>`raster.read_raster` | `imgio.save`<br>`studio_display.save_outputs` | — | optional: PIL, cv2, imageio, tifffile | `tests/test_acquire.py`<br>`tests/test_acquire_contract.py`<br>+75 | — |
| PPM | `.ppm` | — | `imgio.save` | — | optional: PIL, cv2 | `tests/test_acquire.py`<br>`tests/test_acquire_contract.py`<br>+58 | — |
| XYZ text | `.pts` | `mesh.read_points` | `mesh.write_points` | — | stdlib / core | `tests/test_mesh.py`<br>`tests/test_review_fixes_phys_2026_10_07.py`<br>+1 | — |
| RAW raster | `.raw` | `volio.read_volume` | `volio.write_volume` | — | optional: SimpleITK, tifffile | `tests/test_gfx2d.py`<br>`tests/test_gsplat_train.py`<br>+6 | — |
| 3D Gaussian splat | `.splat` | `gsplatnp.gs_read_file` | — | `gs_read_file` | stdlib / core | `tests/test_gsviewer.py`<br>`tests/test_opsdrive.py`<br>+1 | — |
| STL | `.stl` | `mesh.read_mesh`<br>`mesh.read_points` | `mesh.write_mesh` | — | stdlib / core | `tests/test_audit_file_formats.py`<br>`tests/test_mesh.py`<br>+4 | — |
| TIFF | `.tif` | `raster.read_depth`<br>`raster.read_raster`<br>`volio.read_volume` | `imgio.save`<br>`volio.write_volume` | — | optional: PIL, SimpleITK, cv2, imageio, tifffile | `tests/test_acquire.py`<br>`tests/test_acquire_contract.py`<br>+59 | — |
| TIFF | `.tiff` | `raster.read_depth`<br>`raster.read_raster`<br>`volio.read_volume` | `imgio.save`<br>`volio.write_volume` | — | optional: PIL, SimpleITK, cv2, imageio, tifffile | `tests/test_acquire.py`<br>`tests/test_acquire_contract.py`<br>+59 | — |
| Text/XYZ | `.txt` | `mesh.read_points` | `mesh.write_points` | — | stdlib / core | `tests/test_acquire_contract.py`<br>`tests/test_anim3d_i18n_builders_2026_10_25.py`<br>+18 | — |
| VOL | `.vol` | `volio.read_volume` | `volio.write_volume` | — | optional: SimpleITK, tifffile | `tests/test_docstring_audit_wave1_2026_10_22.py`<br>`tests/test_live4d.py`<br>+22 | — |
| WAV | `.wav` | `dsp.read_wav` | `dsp.write_wav` | `read_wav`<br>`write_wav` | optional: soundfile | `tests/test_chain_type_contracts.py`<br>`tests/test_docstring_audit_wave1_2026_10_22.py`<br>+17 | — |
| WebM video | `.webm` | — | `video.write_video` | — | optional: PIL, cv2, imageio | `tests/test_gen_visionlab_video.py`<br>`tests/test_perf_batch20_2026_10_20.py`<br>+2 | — |
| Excel workbook | `.xlsx` | — | `fullseye.xlsxio.save_xlsx_report` | — | optional: openpyxl | `tests/test_inspect_batch.py`<br>`tests/test_review_fixes_phys_2026_10_07.py`<br>+1 | — |
| XYZ point cloud | `.xyz` | `mesh.read_points` | `mesh.write_points` | — | stdlib / core | `tests/test_anim3d_raster_gate_2026_10_26.py`<br>`tests/test_mesh.py`<br>+5 | — |

## 集計

形式（拡張子） **49**、読みあり **38**、書きあり **39**、読み書き対 **28**、公開 op あり **9**、テストあり **49**、独立の読み手による検証あり **1**。

集計値も上表から生成しており、文書内に別の手書き件数は持たない。
