# Fullseye のファイル形式棚卸し

この表は `tools/audit_file_formats.py` が実装モジュール、`docs/OP_INDEX.json`、テストを静的走査して生成する。
拡張子や関数を手で数えた表ではない。`—` は、ソース上で対応する公開関数または検証を確認できなかったことを示す。

| 形式 | 拡張子 | 読む関数 | 書く関数 | 公開 op | 依存 | テスト | 独立の読み手で検証 |
|---|---|---|---|---|---|---|---|
| Zemax glass catalog | `.agf` | `materials.read_glass_catalog_agf` | — | `read_glass_catalog_agf` | stdlib / core | `tests/test_lensfile.py`<br>`tests/test_materials.py` | — |
| XYZ text | `.asc` | `mesh.read_points` | `mesh.write_points` | — | stdlib / core | `tests/test_abi_apply.py`<br>`tests/test_abi_wheel.py`<br>+18 | — |
| AVI video | `.avi` | — | `video.write_video` | — | optional: PIL, imageio | `tests/test_gen_visionlab_video.py`<br>`tests/test_perf_batch20_2026_10_20.py`<br>+2 | — |
| BMP | `.bmp` | `raster.read_raster` | — | — | optional: cv2, imageio, tifffile | `tests/test_iqatid.py`<br>`tests/test_raster.py`<br>+1 | — |
| CSV | `.csv` | `cutting.cut_force_csv_load`<br>`fileio.table_read_csv`<br>`grind.ae_read_csv` | `fileio.table_write_csv` | `ae_read_csv`<br>`cut_force_csv_load`<br>`table_read_csv`<br>`table_write_csv` | stdlib / core | `tests/test_audit_file_formats.py`<br>`tests/test_cutting.py`<br>+10 | `csv`<br>`pandas` |
| DICOM | `.dcm` | `volio.read_volume` | `volio.write_volume` | — | optional: SimpleITK, tifffile | `tests/test_public_api.py`<br>`tests/test_volio.py` | — |
| DICOM | `.dicom` | `volio.read_volume` | `volio.write_volume` | — | optional: SimpleITK, tifffile | `tests/test_public_api.py`<br>`tests/test_volio.py` | — |
| ASTM E57 | `.e57` | `fileio.e57_read` | `fileio.e57_write` | `e57_read`<br>`e57_write` | optional: pye57 | `tests/test_audit_file_formats.py`<br>`tests/test_fileio_e57.py` | `pye57` |
| FITS | `.fits` | `fileio.astro_fits_read` | `fileio.astro_fits_write` | `astro_fits_read`<br>`astro_fits_write` | stdlib / core | `tests/test_fileio_scientific.py`<br>`tests/test_kendama_combo.py` | `astropy` |
| GIF | `.gif` | — | `examplefig.save_gif`<br>`projmap.save_gif`<br>`videocube.video_write_gif` | `video_write_gif` | optional: PIL, fullseye, mujoco | `tests/test_docs_index_reachable.py`<br>`tests/test_examplefig_gif.py`<br>+9 | — |
| glTF | `.gltf` | `meshio_opt.read_gltf`<br>`meshio_opt.read_gltf_merged` | — | — | stdlib / core | `tests/test_mesh.py`<br>`tests/test_meshio_opt.py`<br>+1 | — |
| Radiance HDR | `.hdr` | `volio.read_volume` | `specops.write_envi`<br>`volio.write_volume` | — | optional: SimpleITK, tifffile | `tests/test_public_api.py`<br>`tests/test_specops.py`<br>+2 | — |
| IMG | `.img` | `volio.read_volume` | `specops.write_envi`<br>`volio.write_volume` | — | optional: SimpleITK, tifffile | `tests/test_public_api.py`<br>`tests/test_specops.py`<br>+3 | — |
| JPEG | `.jpeg` | `raster.read_raster` | — | — | optional: cv2, imageio, tifffile | `tests/test_docs_index_reachable.py`<br>`tests/test_imgforensics.py`<br>+2 | — |
| JPEG | `.jpg` | `raster.read_raster` | — | — | optional: cv2, imageio, tifffile | `tests/test_docs_index_reachable.py`<br>`tests/test_help_rendering.py`<br>+11 | — |
| JSON | `.json` | `backends_auto.load_specs`<br>`fullseye.jsonio.load_json` | `fullseye.jsonio.save_json` | — | optional: cv2, skimage | `tests/test_accel_bridge.py`<br>`tests/test_accel_match.py`<br>+130 | — |
| LAS | `.las` | `meshio_opt.read_las` | — | — | stdlib / core | `tests/test_backends.py`<br>`tests/test_coherent.py`<br>+6 | — |
| M4V | `.m4v` | — | `video.write_video` | — | optional: PIL, imageio | `tests/test_gen_visionlab_video.py`<br>`tests/test_perf_batch20_2026_10_20.py`<br>+2 | — |
| MetaImage | `.mha` | `volio.read_volume` | `volio.write_volume` | — | optional: SimpleITK, tifffile | `tests/test_public_api.py`<br>`tests/test_volio.py` | — |
| MetaImage | `.mhd` | `volio.read_volume` | `volio.write_volume` | — | optional: SimpleITK, tifffile | `tests/test_public_api.py`<br>`tests/test_volio.py` | — |
| Matroska video | `.mkv` | — | `video.write_video` | — | optional: PIL, imageio | `tests/test_gen_visionlab_video.py`<br>`tests/test_perf_batch20_2026_10_20.py`<br>+2 | — |
| MODEL | `.model` | `printpath.read_3mf` | — | `read_3mf` | stdlib / core | `tests/test_ledger_probe_fresh_cwd.py`<br>`tests/test_optdraw.py`<br>+2 | — |
| MOV | `.mov` | — | `video.write_video` | — | optional: PIL, imageio | `tests/test_anomaly_patch.py`<br>`tests/test_astrostack_median.py`<br>+12 | — |
| MP4 | `.mp4` | — | `video.write_video` | — | optional: PIL, imageio | `tests/test_docs_index_reachable.py`<br>`tests/test_examplefig_gif.py`<br>+7 | — |
| MRC | `.mrc` | `fileio.em_mrc_read` | `fileio.em_mrc_write` | `em_mrc_read`<br>`em_mrc_write` | stdlib / core | `tests/test_fileio_scientific.py` | `mrcfile` |
| NHDR | `.nhdr` | `volio.read_volume` | `volio.write_volume` | — | optional: SimpleITK, tifffile | `tests/test_public_api.py`<br>`tests/test_volio.py` | — |
| NIfTI | `.nii` | `fileio.nifti_read`<br>`volio.read_volume` | `fileio.nifti_write`<br>`volio.write_volume` | `nifti_read`<br>`nifti_write` | optional: SimpleITK, tifffile | `tests/test_fileio_scientific.py`<br>`tests/test_public_api.py`<br>+1 | `nibabel` |
| NIfTI | `.nii.gz` | `fileio.nifti_read`<br>`volio.read_volume` | `fileio.nifti_write`<br>`volio.write_volume` | `nifti_read`<br>`nifti_write` | optional: SimpleITK, tifffile | `tests/test_fileio_scientific.py`<br>`tests/test_public_api.py`<br>+1 | `nibabel` |
| NumPy array | `.npy` | `mesh.read_points`<br>`motionio.read_events`<br>`volio.read_volume` | `mesh.write_points`<br>`studio_display.save_outputs`<br>`volio.write_volume` | `read_events` | optional: SimpleITK, tifffile | `tests/test_capabilities.py`<br>`tests/test_examples3d.py`<br>+20 | — |
| NumPy archive | `.npz` | `mesh.read_points`<br>`motionio.read_events`<br>`volio.read_volume` | `mesh.write_points`<br>`volio.write_volume` | `read_events` | optional: SimpleITK, tifffile | `tests/test_carlabridge.py`<br>`tests/test_itokawa_anim3d.py`<br>+13 | — |
| NRRD | `.nrrd` | `fileio.nrrd_read`<br>`volio.read_volume` | `fileio.nrrd_write`<br>`volio.write_volume` | `nrrd_read`<br>`nrrd_write` | optional: SimpleITK, tifffile | `tests/test_fileio_scientific.py`<br>`tests/test_public_api.py`<br>+1 | `nrrd` |
| Wavefront OBJ | `.obj` | `driveworld.read_obj_colored`<br>`fileio.mesh_read_obj`<br>`mesh.read_mesh`<br>`mesh.read_points` | `fileio.mesh_write_obj`<br>`mesh.write_mesh` | `mesh_read_obj`<br>`mesh_write_obj` | stdlib / core | `tests/test_abi_apply.py`<br>`tests/test_audit_0_7_1_fixes_2026_10_21.py`<br>+13 | `trimesh` |
| Geomview OFF | `.off` | `fileio.mesh_read_off`<br>`mesh.read_mesh`<br>`mesh.read_points` | `fileio.mesh_write_off`<br>`mesh.write_mesh` | `mesh_read_off`<br>`mesh_write_off` | stdlib / core | `tests/test_audit_file_formats.py`<br>`tests/test_drivelateral.py`<br>+8 | `trimesh` |
| PBM | `.pbm` | — | `imgio.save` | — | optional: PIL, cv2 | `tests/test_acquire.py`<br>`tests/test_acquire_contract.py`<br>+59 | — |
| PCL PCD | `.pcd` | `mesh.read_points`<br>`meshio_opt.read_pcd` | — | — | optional: pypcd4 | `tests/test_mesh.py`<br>`tests/test_meshio_opt.py`<br>+2 | — |
| PFM | `.pfm` | `raster.read_depth`<br>`raster.read_pfm`<br>`raster.read_raster` | `imgio.save`<br>`raster.write_pfm` | — | optional: PIL, cv2, imageio, tifffile | `tests/test_acquire.py`<br>`tests/test_acquire_contract.py`<br>+61 | — |
| PGM | `.pgm` | — | `imgio.save` | — | optional: PIL, cv2 | `tests/test_acquire.py`<br>`tests/test_acquire_contract.py`<br>+59 | — |
| Stanford PLY | `.ply` | `fileio.mesh_read_ply`<br>`gsplatnp.gs_read_file`<br>`mesh.read_mesh`<br>`mesh.read_points` | `fileio.mesh_write_ply`<br>`gsplat_train_native.save_gaussians_ply`<br>`imgio.save_ply`<br>`mesh.write_mesh`<br>+1 | `gs_read_file`<br>`mesh_read_ply`<br>`mesh_write_ply` | 必須: PIL, gsplat, torch<br>optional: numpy | `tests/test_audit_file_formats.py`<br>`tests/test_fileio_mesh.py`<br>+12 | `plyfile`<br>`trimesh` |
| PNG | `.png` | `raster.read_depth`<br>`raster.read_raster` | `imgio.save`<br>`studio_display.save_outputs` | — | optional: PIL, cv2, imageio, tifffile | `tests/test_acquire.py`<br>`tests/test_acquire_contract.py`<br>+76 | — |
| PPM | `.ppm` | — | `imgio.save` | — | optional: PIL, cv2 | `tests/test_acquire.py`<br>`tests/test_acquire_contract.py`<br>+59 | — |
| XYZ text | `.pts` | `mesh.read_points` | `mesh.write_points` | — | stdlib / core | `tests/test_mesh.py`<br>`tests/test_review_fixes_phys_2026_10_07.py`<br>+1 | — |
| RAW raster | `.raw` | `volio.read_volume` | `volio.write_volume` | — | optional: SimpleITK, tifffile | `tests/test_gfx2d.py`<br>`tests/test_gsplat_train.py`<br>+6 | — |
| 3D Gaussian splat | `.splat` | `gsplatnp.gs_read_file` | — | `gs_read_file` | stdlib / core | `tests/test_gsviewer.py`<br>`tests/test_opsdrive.py`<br>+1 | — |
| STL | `.stl` | `fileio.mesh_read_stl`<br>`mesh.read_mesh`<br>`mesh.read_points` | `fileio.mesh_write_stl`<br>`mesh.write_mesh` | `mesh_read_stl`<br>`mesh_write_stl` | stdlib / core | `tests/test_audit_file_formats.py`<br>`tests/test_fileio_mesh.py`<br>+5 | `stl`<br>`trimesh` |
| TIFF | `.tif` | `raster.read_depth`<br>`raster.read_raster`<br>`volio.read_volume` | `imgio.save`<br>`volio.write_volume` | — | optional: PIL, SimpleITK, cv2, imageio, tifffile | `tests/test_acquire.py`<br>`tests/test_acquire_contract.py`<br>+60 | — |
| TIFF | `.tiff` | `raster.read_depth`<br>`raster.read_raster`<br>`volio.read_volume` | `imgio.save`<br>`volio.write_volume` | — | optional: PIL, SimpleITK, cv2, imageio, tifffile | `tests/test_acquire.py`<br>`tests/test_acquire_contract.py`<br>+60 | — |
| Text/XYZ | `.txt` | `mesh.read_points` | `mesh.write_points` | — | stdlib / core | `tests/test_acquire_contract.py`<br>`tests/test_anim3d_i18n_builders_2026_10_25.py`<br>+18 | — |
| VOL | `.vol` | `volio.read_volume` | `volio.write_volume` | — | optional: SimpleITK, tifffile | `tests/test_docstring_audit_wave1_2026_10_22.py`<br>`tests/test_fileio_mesh.py`<br>+23 | — |
| WAV | `.wav` | `dsp.read_wav` | `dsp.write_wav` | `read_wav`<br>`write_wav` | stdlib / core | `tests/test_chain_type_contracts.py`<br>`tests/test_docstring_audit_wave1_2026_10_22.py`<br>+17 | — |
| WebM video | `.webm` | — | `video.write_video` | — | optional: PIL, imageio | `tests/test_gen_visionlab_video.py`<br>`tests/test_perf_batch20_2026_10_20.py`<br>+2 | — |
| Excel workbook | `.xlsx` | — | `fullseye.xlsxio.save_xlsx_report` | — | optional: openpyxl | `tests/test_inspect_batch.py`<br>`tests/test_review_fixes_phys_2026_10_07.py`<br>+1 | — |
| XYZ point cloud | `.xyz` | `fileio.points_read_xyz`<br>`mesh.read_points` | `fileio.points_write_xyz`<br>`mesh.write_points` | `points_read_xyz`<br>`points_write_xyz` | stdlib / core | `tests/test_anim3d_raster_gate_2026_10_26.py`<br>`tests/test_audit_file_formats.py`<br>+7 | — |

## 集計

形式（拡張子） **52**、読みあり **41**、書きあり **43**、読み書き対 **32**、公開 op あり **19**、テストあり **52**、独立の読み手による検証あり **11**。

集計値も上表から生成しており、文書内に別の手書き件数は持たない。
