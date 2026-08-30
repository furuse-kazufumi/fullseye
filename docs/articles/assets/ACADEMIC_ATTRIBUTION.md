# Academic gallery — attribution / 出典とライセンス

`academic_*.png` (tools/gen_academic_gallery.py 生成) の全素材の出典。
**「AI 生成」列が Yes の画像は OpenAI 画像生成モデルによる模擬データであり、実在の標本・スキャン・観測ではない。**
実データはすべて public domain / CC0 / CC-BY のみを使用。

| 画像 | 分野 | 素材 | AI 生成 | 出典 / ライセンス | 使用 op |
|---|---|---|---|---|---|
| `academic_arch_amphora.png` | 考古学 | Terracotta amphora (jar) | No | [The Metropolitan Museum of Art](https://www.metmuseum.org/art/collection/search/254896) — CC0 (The Met Open Access) | rgb1_to_gray, otsu, fill_up, segment_objects, fourierdesc.elliptic_fourier, fourierdesc.reconstruct |
| `academic_arch_relief.png` | 考古学 | Relief panel | No | [The Metropolitan Museum of Art](https://www.metmuseum.org/art/collection/search/322611) — CC0 (The Met Open Access) | rgb1_to_gray, gray_tophat, cv_clahe |
| `academic_bio_cells.png` | 生物学 | BBBC001 human HT29 colon-cancer cells (AS_09125_050118150001 | No | [Broad Bioimage Benchmark Collection](https://bbbc.broadinstitute.org/BBBC001) — CC-BY 3.0 (Broad Bioimage Benchmark Collection; Ljosa et al., Nature Methods 2012) | rgb1_to_gray, segment_objects(otsu), count_obj, colorize_labels |
| `academic_geo_earth.png` | 地質学 | Lake Powell, Colorado River, Utah and Grand Canyon, Arizona | No | [JSC](https://images.nasa.gov/details/SL2-04-018) — Public domain (NASA) | principal_comp, rgb1_to_gray, cv_clahe |
| `academic_met_hurricane.png` | 気象学 | iss056e162187 | No | [JSC](https://images.nasa.gov/details/iss056e162187) — Public domain (NASA) | rgb1_to_gray, cv_clahe, sobel_amp, sobel_dir, colorize_flow |
| `academic_paleo_ammonite_real.png` | 古生物学 | Ammonite | No | [NMNH - Education & Outreach](http://n2t.net/ark:/65665/34afa6692-b3f9-408d-90dc-cc53097171b6) — CC0 (Smithsonian Open Access) | rgb1_to_gray, canny, overlay_mask |
| `academic_space_carina.png` | 宇宙 | James Webb Space Telescope NIRCam Image of the “Cosmic Cliff | No | [STScI (Webb)](https://images.nasa.gov/details/carina_nebula) — Public domain (NASA) | rgb1_to_gray, cv_clahe, sk_frangi |
| `academic_space_galaxy.png` | 宇宙 | A galactic sunflower | No | [GSFC](https://images.nasa.gov/details/hubble-sees-a-galactic-sunflower_21136469209_o) — Public domain (NASA) | rgb1_to_gray, cv_clahe, cx_fft, cx_magnitude |
| `academic_space_mars.png` | 宇宙 | The Active Dunes of Nili Patera | No | [NASA/JPL-Caltech/Univ. of Arizona](https://images.nasa.gov/details/PIA18244) — Public domain (NASA) | rgb1_to_gray, std_filter, texture_laws |

生成日: 2026-08-30 / スクリプト: `tools/gen_academic_gallery.py`
