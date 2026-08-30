<!-- 記事貼り付け用スニペット: 学問分野横断ギャラリー (gen_academic_gallery.py) -->
<!-- 画像はサムネ(720px JPG)。フル解像度は _thumb を外した .png -->

## 古生物学

![paleo_ammonite_real](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_ammonite_real_thumb.jpg)
*アンモナイト化石(Smithsonian CC0)の螺旋を canny で抽出(op: `rgb1_to_gray`, `canny`, `overlay_mask`)。素材: NMNH - Education & Outreach — CC0 (Smithsonian Open Access)([出典](http://n2t.net/ark:/65665/34afa6692-b3f9-408d-90dc-cc53097171b6))*

## 宇宙

![space_carina](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_carina_thumb.jpg)
*星雲のフィラメント構造を sk_frangi(血管強調フィルタ)で抽出(op: `rgb1_to_gray`, `clahe`, `sk_frangi`)。素材: STScI (Webb) — Public domain (NASA)([出典](https://images.nasa.gov/details/carina_nebula))*

![space_mars](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_mars_thumb.jpg)
*火星表面の岩石テクスチャを std_filter / texture_laws で解析(op: `rgb1_to_gray`, `std_filter`, `texture_laws`)。素材: NASA/JPL-Caltech — Public domain (NASA)([出典](https://images.nasa.gov/details/PIA14760))*

![space_galaxy](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_galaxy_thumb.jpg)
*渦巻銀河の周波数構造を cx_fft スペクトルで可視化(op: `rgb1_to_gray`, `clahe`, `cx_fft`, `cx_magnitude`)。素材: GSFC — Public domain (NASA)([出典](https://images.nasa.gov/details/hubble-sees-a-galactic-sunflower_21136469209_o))*

## 生物学

![bio_cells](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_cells_thumb.jpg)
*HT29 細胞蛍光顕微鏡像(BBBC001)を otsu 分割 -> ラベル彩色 -> count_obj で計数 検出数 = 327(count_obj = 342)(op: `rgb1_to_gray`, `segment_objects(otsu)`, `count_obj`, `colorize_labels`)。素材: Broad Bioimage Benchmark Collection — CC-BY 3.0 (Broad Bioimage Benchmark Collection; Ljosa et al., Nature Methods 2012)([出典](https://bbbc.broadinstitute.org/BBBC001))*

## 考古学

![arch_amphora](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_amphora_thumb.jpg)
*土器シルエットを楕円フーリエ記述子(EFD)で形状復元(2/8/32 高調波)(op: `rgb1_to_gray`, `otsu`, `fill_up`, `segment_objects`, `fourierdesc.elliptic_fourier`, `fourierdesc.reconstruct`)。素材: The Metropolitan Museum of Art — CC0 (The Met Open Access)([出典](https://www.metmuseum.org/art/collection/search/254896))*

![arch_relief](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_relief_thumb.jpg)
*石碑レリーフの彫刻を gray_tophat で浮き彫り強調(op: `rgb1_to_gray`, `gray_tophat`, `clahe`)。素材: The Metropolitan Museum of Art — CC0 (The Met Open Access)([出典](https://www.metmuseum.org/art/collection/search/322611))*

## 気象学

![met_hurricane](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_met_hurricane_thumb.jpg)
*ハリケーンの渦構造を sobel_dir 勾配方向ホイールで可視化(op: `rgb1_to_gray`, `sobel_amp`, `sobel_dir`, `colorize_flow`)。素材: JSC — Public domain (NASA)([出典](https://images.nasa.gov/details/iss005e15375))*
