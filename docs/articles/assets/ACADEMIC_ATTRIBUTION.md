# Academic gallery — attribution / 出典とライセンス

`academic_*.png` (tools/gen_academic_gallery.py 生成) の全素材の出典。
**「AI 生成」列が Yes の画像は画像生成 AI(モデル名は表に記載)による模擬データであり、実在の標本・スキャン・観測ではない。**
実データはすべて public domain / CC0 / CC-BY のみを使用。

| 画像 | 分野 | 素材 | AI 生成 | 出典 / ライセンス | 使用 op |
|---|---|---|---|---|---|
| `academic_arch_amphora.png` | 考古学 | Terracotta amphora (jar) | No | [The Metropolitan Museum of Art](https://www.metmuseum.org/art/collection/search/254896) — CC0 (The Met Open Access) | rgb1_to_gray, otsu, fill_up, segment_objects, fourierdesc.elliptic_fourier, fourierdesc.reconstruct |
| `academic_arch_cave_painting.png` | 考古学 | AI-generated simulated data (gemini-2.5-flash-image) | **Yes** (gemini-2.5-flash-image) | AI 生成模擬データ(Google gemini-2.5-flash-image)— 実データではない | principal_comp, rgb1_to_gray, cv_clahe |
| `academic_arch_cuneiform.png` | 考古学 | AI-generated simulated data (gemini-2.5-flash-image) | **Yes** (gemini-2.5-flash-image) | AI 生成模擬データ(Google gemini-2.5-flash-image)— 実データではない | rgb1_to_gray, gray_tophat, cv_clahe |
| `academic_arch_relief.png` | 考古学 | Relief panel | No | [The Metropolitan Museum of Art](https://www.metmuseum.org/art/collection/search/322611) — CC0 (The Met Open Access) | rgb1_to_gray, gray_tophat, cv_clahe |
| `academic_bio_butterfly.png` | 生物学 | AI-generated simulated data (gemini-2.5-flash-image) | **Yes** (gemini-2.5-flash-image) | AI 生成模擬データ(Google gemini-2.5-flash-image)— 実データではない | rgb1_to_gray, sk_gabor, std_filter |
| `academic_bio_cells.png` | 生物学 | BBBC001 human HT29 colon-cancer cells (AS_09125_050118150001 | No | [Broad Bioimage Benchmark Collection](https://bbbc.broadinstitute.org/BBBC001) — CC-BY 3.0 (Broad Bioimage Benchmark Collection; Ljosa et al., Nature Methods 2012) | rgb1_to_gray, segment_objects(otsu), count_obj, colorize_labels |
| `academic_bio_deepsea.png` | 生物学 | AI-generated simulated data (gemini-2.5-flash-image) | **Yes** (gemini-2.5-flash-image) | AI 生成模擬データ(Google gemini-2.5-flash-image)— 実データではない | rgb1_to_gray, cv_clahe, unsharp |
| `academic_bio_diatoms.png` | 生物学 | AI-generated simulated data (gemini-2.5-flash-image) | **Yes** (gemini-2.5-flash-image) | AI 生成模擬データ(Google gemini-2.5-flash-image)— 実データではない | rgb1_to_gray, segment_objects(otsu), count_obj, colorize_labels |
| `academic_bio_neuron.png` | 生物学 | AI-generated simulated data (gemini-2.5-flash-image) | **Yes** (gemini-2.5-flash-image) | AI 生成模擬データ(Google gemini-2.5-flash-image)— 実データではない | rgb1_to_gray, cv_clahe, cv_median, sk_frangi, sk_area_opening, overlay_mask |
| `academic_bot_fern.png` | 植物学 | AI-generated simulated data (gemini-2.5-flash-image) | **Yes** (gemini-2.5-flash-image) | AI 生成模擬データ(Google gemini-2.5-flash-image)— 実データではない | rgb1_to_gray, cv_clahe, sk_frangi |
| `academic_bot_pollen.png` | 植物学 | AI-generated simulated data (gemini-2.5-flash-image) | **Yes** (gemini-2.5-flash-image) | AI 生成模擬データ(Google gemini-2.5-flash-image)— 実データではない | rgb1_to_gray, segment_objects(otsu), count_obj, colorize_labels |
| `academic_geo_earth.png` | 地質学 | Lake Powell, Colorado River, Utah and Grand Canyon, Arizona | No | [JSC](https://images.nasa.gov/details/SL2-04-018) — Public domain (NASA) | principal_comp, rgb1_to_gray, cv_clahe |
| `academic_geo_mineral.png` | 地質学 | AI-generated simulated data (gemini-2.5-flash-image) | **Yes** (gemini-2.5-flash-image) | AI 生成模擬データ(Google gemini-2.5-flash-image)— 実データではない | rgb1_to_gray, canny, overlay_mask |
| `academic_geo_thin_section.png` | 地質学 | AI-generated simulated data (gemini-2.5-flash-image) | **Yes** (gemini-2.5-flash-image) | AI 生成模擬データ(Google gemini-2.5-flash-image)— 実データではない | rgb1_to_gray, xsk2_multiotsu, colorize_labels |
| `academic_med_anatomy_heart.png` | 医学 | AI-generated simulated data (gemini-2.5-flash-image) | **Yes** (gemini-2.5-flash-image) | AI 生成模擬データ(Google gemini-2.5-flash-image)— 実データではない | rgb1_to_gray, canny, overlay_mask |
| `academic_med_blood_smear.png` | 医学 | AI-generated simulated data (gemini-2.5-flash-image) | **Yes** (gemini-2.5-flash-image) | AI 生成模擬データ(Google gemini-2.5-flash-image)— 実データではない | rgb1_to_gray, segment_objects(otsu), count_obj, colorize_labels |
| `academic_med_brain_mri.png` | 医学 | AI-generated simulated data (gemini-2.5-flash-image) | **Yes** (gemini-2.5-flash-image) | AI 生成模擬データ(Google gemini-2.5-flash-image)— 実データではない | rgb1_to_gray, cv_clahe, unsharp |
| `academic_med_chest_xray.png` | 医学 | AI-generated simulated data (gemini-2.5-flash-image) | **Yes** (gemini-2.5-flash-image) | AI 生成模擬データ(Google gemini-2.5-flash-image)— 実データではない | rgb1_to_gray, cv_clahe, sobel_amp |
| `academic_med_histology.png` | 医学 | AI-generated simulated data (gemini-2.5-flash-image) | **Yes** (gemini-2.5-flash-image) | AI 生成模擬データ(Google gemini-2.5-flash-image)— 実データではない | rgb1_to_gray, xsk2_multiotsu, colorize_labels |
| `academic_met_hurricane.png` | 気象学 | iss056e162187 | No | [JSC](https://images.nasa.gov/details/iss056e162187) — Public domain (NASA) | rgb1_to_gray, cv_clahe, sobel_amp, sobel_dir, colorize_flow |
| `academic_met_supercell.png` | 気象学 | AI-generated simulated data (gemini-2.5-flash-image) | **Yes** (gemini-2.5-flash-image) | AI 生成模擬データ(Google gemini-2.5-flash-image)— 実データではない | rgb1_to_gray, cv_clahe, unsharp |
| `academic_ocean_coral.png` | 海洋学 | AI-generated simulated data (gemini-2.5-flash-image) | **Yes** (gemini-2.5-flash-image) | AI 生成模擬データ(Google gemini-2.5-flash-image)— 実データではない | rgb1_to_gray, xsk2_multiotsu, colorize_labels |
| `academic_paleo_ammonite_real.png` | 古生物学 | Ammonite | No | [NMNH - Education & Outreach](http://n2t.net/ark:/65665/34afa6692-b3f9-408d-90dc-cc53097171b6) — CC0 (Smithsonian Open Access) | rgb1_to_gray, canny, overlay_mask |
| `academic_paleo_ammonite_section.png` | 古生物学 | AI-generated simulated data (gemini-2.5-flash-image) | **Yes** (gemini-2.5-flash-image) | AI 生成模擬データ(Google gemini-2.5-flash-image)— 実データではない | rgb1_to_gray, cv_clahe, cx_fft, cx_magnitude |
| `academic_paleo_feathered.png` | 古生物学 | AI-generated simulated data (gemini-2.5-flash-image) | **Yes** (gemini-2.5-flash-image) | AI 生成模擬データ(Google gemini-2.5-flash-image)— 実データではない | rgb1_to_gray, sk_gabor, std_filter |
| `academic_paleo_trex.png` | 古生物学 | AI-generated simulated data (gemini-2.5-flash-image) | **Yes** (gemini-2.5-flash-image) | AI 生成模擬データ(Google gemini-2.5-flash-image)— 実データではない | rgb1_to_gray, std_filter, texture_laws |
| `academic_paleo_triceratops.png` | 古生物学 | AI-generated simulated data (gemini-2.5-flash-image) | **Yes** (gemini-2.5-flash-image) | AI 生成模擬データ(Google gemini-2.5-flash-image)— 実データではない | rgb1_to_gray, xsk2_multiotsu, colorize_labels |
| `academic_paleo_trilobite.png` | 古生物学 | AI-generated simulated data (gemini-2.5-flash-image) | **Yes** (gemini-2.5-flash-image) | AI 生成模擬データ(Google gemini-2.5-flash-image)— 実データではない | rgb1_to_gray, gray_tophat, cv_clahe |
| `academic_space_carina.png` | 宇宙 | James Webb Space Telescope NIRCam Image of the “Cosmic Cliff | No | [STScI (Webb)](https://images.nasa.gov/details/carina_nebula) — Public domain (NASA) | rgb1_to_gray, cv_clahe, sk_frangi |
| `academic_space_galaxy.png` | 宇宙 | A galactic sunflower | No | [GSFC](https://images.nasa.gov/details/hubble-sees-a-galactic-sunflower_21136469209_o) — Public domain (NASA) | rgb1_to_gray, cv_clahe, cx_fft, cx_magnitude |
| `academic_space_mars.png` | 宇宙 | The Active Dunes of Nili Patera | No | [NASA/JPL-Caltech/Univ. of Arizona](https://images.nasa.gov/details/PIA18244) — Public domain (NASA) | rgb1_to_gray, std_filter, texture_laws |

生成日: 2026-08-30 / スクリプト: `tools/gen_academic_gallery.py`
