<!-- 記事貼り付け用スニペット: 学問分野横断ギャラリー (gen_academic_gallery.py) -->
<!-- 画像はサムネ(720px JPG)。フル解像度は _thumb を外した .png -->

## 古生物学

![paleo_ammonite_real](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_ammonite_real_thumb.jpg)
*アンモナイト化石(Smithsonian CC0)の螺旋を canny で抽出(op: `rgb1_to_gray`, `canny`, `overlay_mask`)。素材: NMNH - Education & Outreach — CC0 (Smithsonian Open Access)([出典](http://n2t.net/ark:/65665/34afa6692-b3f9-408d-90dc-cc53097171b6))*

## 生物学

![bio_cells](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_cells_thumb.jpg)
*HT29 細胞蛍光顕微鏡像(BBBC001)を otsu 分割 -> ラベル彩色 -> count_obj で計数 検出数 = 327(count_obj = 342)(op: `rgb1_to_gray`, `segment_objects(otsu)`, `count_obj`, `colorize_labels`)。素材: Broad Bioimage Benchmark Collection — CC-BY 3.0 (Broad Bioimage Benchmark Collection; Ljosa et al., Nature Methods 2012)([出典](https://bbbc.broadinstitute.org/BBBC001))*

## 考古学

![arch_amphora](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_amphora_thumb.jpg)
*土器シルエットを楕円フーリエ記述子(EFD)で形状復元(2/8/32 高調波)(op: `rgb1_to_gray`, `otsu`, `fill_up`, `segment_objects`, `fourierdesc.elliptic_fourier`, `fourierdesc.reconstruct`)。素材: The Metropolitan Museum of Art — CC0 (The Met Open Access)([出典](https://www.metmuseum.org/art/collection/search/254896))*

![arch_relief](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_relief_thumb.jpg)
*石碑レリーフの彫刻を gray_tophat で浮き彫り強調(op: `rgb1_to_gray`, `gray_tophat`, `clahe`)。素材: The Metropolitan Museum of Art — CC0 (The Met Open Access)([出典](https://www.metmuseum.org/art/collection/search/322611))*
