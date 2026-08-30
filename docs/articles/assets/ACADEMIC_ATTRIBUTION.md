# Academic gallery — attribution / 出典とライセンス

`academic_*.png` (tools/gen_academic_gallery.py 生成) の全素材の出典。
**「AI 生成」列が Yes の画像は OpenAI 画像生成モデルによる模擬データであり、実在の標本・スキャン・観測ではない。**
実データはすべて public domain / CC0 / CC-BY のみを使用。

| 画像 | 分野 | 素材 | AI 生成 | 出典 / ライセンス | 使用 op |
|---|---|---|---|---|---|
| `academic_arch_amphora.png` | 考古学 | Terracotta amphora (jar) | No | [The Metropolitan Museum of Art](https://www.metmuseum.org/art/collection/search/254896) — CC0 (The Met Open Access) | rgb1_to_gray, otsu, fill_up, segment_objects, fourierdesc.elliptic_fourier, fourierdesc.reconstruct |
| `academic_arch_relief.png` | 考古学 | Relief panel | No | [The Metropolitan Museum of Art](https://www.metmuseum.org/art/collection/search/322611) — CC0 (The Met Open Access) | rgb1_to_gray, gray_tophat, clahe |
| `academic_bio_cells.png` | 生物学 | BBBC001 human HT29 colon-cancer cells (AS_09125_050118150001 | No | [Broad Bioimage Benchmark Collection](https://bbbc.broadinstitute.org/BBBC001) — CC-BY 3.0 (Broad Bioimage Benchmark Collection; Ljosa et al., Nature Methods 2012) | rgb1_to_gray, segment_objects(otsu), count_obj, colorize_labels |
| `academic_paleo_ammonite_real.png` | 古生物学 | Ammonite | No | [NMNH - Education & Outreach](http://n2t.net/ark:/65665/34afa6692-b3f9-408d-90dc-cc53097171b6) — CC0 (Smithsonian Open Access) | rgb1_to_gray, canny, overlay_mask |

生成日: 2026-08-30 / スクリプト: `tools/gen_academic_gallery.py`
