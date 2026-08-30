<!-- 記事貼り付け用スニペット: 学問分野横断ギャラリー (gen_academic_gallery.py) -->
<!-- 画像はサムネ(720px JPG)。フル解像度は _thumb を外した .png -->

## 古生物学

![paleo_ammonite_real](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_ammonite_real_thumb.jpg)
*アンモナイト化石(Smithsonian CC0)の螺旋を canny で抽出(op: `rgb1_to_gray`, `canny`, `overlay_mask`)。素材: NMNH - Education & Outreach — CC0 (Smithsonian Open Access)([出典](http://n2t.net/ark:/65665/34afa6692-b3f9-408d-90dc-cc53097171b6))*

![paleo_trex](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_trex_thumb.jpg)
*ティラノサウルス生体復元(AI 生成)の皮膚テクスチャを std_filter で解析(op: `rgb1_to_gray`, `std_filter`, `texture_laws`)。素材: **AI 生成(Google gemini-2.5-flash-image)による模擬データ**(実在の標本・スキャンではない)*

![paleo_triceratops](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_triceratops_thumb.jpg)
*トリケラトプス生体復元(AI 生成)を multi-Otsu で領域分類(op: `rgb1_to_gray`, `xsk2_multiotsu`, `colorize_labels`)。素材: **AI 生成(Google gemini-2.5-flash-image)による模擬データ**(実在の標本・スキャンではない)*

![paleo_feathered](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_feathered_thumb.jpg)
*羽毛恐竜生体復元(AI 生成)の羽毛流れを sk_gabor で解析(op: `rgb1_to_gray`, `sk_gabor`, `std_filter`)。素材: **AI 生成(Google gemini-2.5-flash-image)による模擬データ**(実在の標本・スキャンではない)*

![paleo_ammonite_section](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_ammonite_section_thumb.jpg)
*アンモナイト断面(AI 生成)の対数螺旋を FFT スペクトルで観察(op: `rgb1_to_gray`, `cv_clahe`, `cx_fft`, `cx_magnitude`)。素材: **AI 生成(Google gemini-2.5-flash-image)による模擬データ**(実在の標本・スキャンではない)*

![paleo_trilobite](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_trilobite_thumb.jpg)
*三葉虫化石(AI 生成)の体節を gray_tophat で浮き彫り強調(op: `rgb1_to_gray`, `gray_tophat`, `cv_clahe`)。素材: **AI 生成(Google gemini-2.5-flash-image)による模擬データ**(実在の標本・スキャンではない)*

## 宇宙

![space_carina](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_carina_thumb.jpg)
*星雲のフィラメント構造を sk_frangi(血管強調フィルタ)で抽出し、応答上位 10% を着色オーバーレイ表示(op: `rgb1_to_gray`, `cv_clahe`, `cv_median`, `sk_frangi`, `sk_area_opening`, `overlay_mask`)。素材: STScI (Webb) — Public domain (NASA)([出典](https://images.nasa.gov/details/carina_nebula))*

![space_mars](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_mars_thumb.jpg)
*火星 Nili Patera 砂丘のテクスチャを std_filter / texture_laws で解析(op: `rgb1_to_gray`, `std_filter`, `texture_laws`)。素材: NASA/JPL-Caltech/Univ. of Arizona — Public domain (NASA)([出典](https://images.nasa.gov/details/PIA18244))*

![space_galaxy](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_galaxy_thumb.jpg)
*渦巻銀河の周波数構造を cx_fft スペクトルで可視化(op: `rgb1_to_gray`, `cv_clahe`, `cx_fft`, `cx_magnitude`)。素材: GSFC — Public domain (NASA)([出典](https://images.nasa.gov/details/hubble-sees-a-galactic-sunflower_21136469209_o))*

## 医学

![med_chest_xray](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_chest_xray_thumb.jpg)
*胸部X線風画像(AI 生成)を cv_clahe + sobel_amp で強調・エッジ抽出(op: `rgb1_to_gray`, `cv_clahe`, `sobel_amp`)。素材: **AI 生成(Google gemini-2.5-flash-image)による模擬データ**(実在の標本・スキャンではない)*

![med_histology](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_histology_thumb.jpg)
*H&E 組織切片風画像(AI 生成)を multi-Otsu で組織構造分類(op: `rgb1_to_gray`, `xsk2_multiotsu`, `colorize_labels`)。素材: **AI 生成(Google gemini-2.5-flash-image)による模擬データ**(実在の標本・スキャンではない)*

![med_brain_mri](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_brain_mri_thumb.jpg)
*脳 MRI 風画像(AI 生成)を cv_clahe + unsharp で組織コントラスト強調(op: `rgb1_to_gray`, `cv_clahe`, `unsharp`)。素材: **AI 生成(Google gemini-2.5-flash-image)による模擬データ**(実在の標本・スキャンではない)*

![med_blood_smear](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_blood_smear_thumb.jpg)
*血液塗抹風画像(AI 生成)の血球を分割・計数 検出数 = 131(op: `rgb1_to_gray`, `segment_objects(otsu)`, `count_obj`, `colorize_labels`)。素材: **AI 生成(Google gemini-2.5-flash-image)による模擬データ**(実在の標本・スキャンではない)*

![med_anatomy_heart](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_anatomy_heart_thumb.jpg)
*解剖図風イラスト(AI 生成)の輪郭を canny で抽出(op: `rgb1_to_gray`, `canny`, `overlay_mask`)。素材: **AI 生成(Google gemini-2.5-flash-image)による模擬データ**(実在の標本・スキャンではない)*

## 生物学

![bio_neuron](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_neuron_thumb.jpg)
*神経細胞蛍光像(AI 生成)の樹状突起を sk_frangi でトレースし、応答上位 3% を着色オーバーレイ表示(op: `rgb1_to_gray`, `cv_clahe`, `cv_median`, `sk_frangi`, `sk_area_opening`, `overlay_mask`)。素材: **AI 生成(Google gemini-2.5-flash-image)による模擬データ**(実在の標本・スキャンではない)*

![bio_diatoms](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_diatoms_thumb.jpg)
*珪藻顕微鏡像(AI 生成)を分割・計数 検出数 = 123(op: `rgb1_to_gray`, `segment_objects(otsu)`, `count_obj`, `colorize_labels`)。素材: **AI 生成(Google gemini-2.5-flash-image)による模擬データ**(実在の標本・スキャンではない)*

![bio_deepsea](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_deepsea_thumb.jpg)
*深海生物(AI 生成)の暗部を cv_clahe で増強(op: `rgb1_to_gray`, `cv_clahe`, `unsharp`)。素材: **AI 生成(Google gemini-2.5-flash-image)による模擬データ**(実在の標本・スキャンではない)*

![bio_butterfly](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_butterfly_thumb.jpg)
*蝶の翅鱗粉(AI 生成)の周期構造を sk_gabor で解析(op: `rgb1_to_gray`, `sk_gabor`, `std_filter`)。素材: **AI 生成(Google gemini-2.5-flash-image)による模擬データ**(実在の標本・スキャンではない)*

## 考古学

![arch_amphora](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_amphora_thumb.jpg)
*土器シルエットを楕円フーリエ記述子(EFD)で形状復元(2/8/32 高調波)(op: `rgb1_to_gray`, `otsu`, `fill_up`, `segment_objects`, `fourierdesc.elliptic_fourier`, `fourierdesc.reconstruct`)。素材: The Metropolitan Museum of Art — CC0 (The Met Open Access)([出典](https://www.metmuseum.org/art/collection/search/254896))*

![arch_relief](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_relief_thumb.jpg)
*石碑レリーフの彫刻を gray_tophat で浮き彫り強調(op: `rgb1_to_gray`, `gray_tophat`, `cv_clahe`)。素材: The Metropolitan Museum of Art — CC0 (The Met Open Access)([出典](https://www.metmuseum.org/art/collection/search/322611))*

![arch_cave_painting](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_cave_painting_thumb.jpg)
*洞窟壁画(AI 生成)を decorrelation stretch で顔料強調(DStretch 手法)(op: `principal_comp`, `rgb1_to_gray`, `cv_clahe`)。素材: **AI 生成(Google gemini-2.5-flash-image)による模擬データ**(実在の標本・スキャンではない)*

![arch_cuneiform](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_cuneiform_thumb.jpg)
*楔形文字粘土板(AI 生成)を gray_tophat で文字刻印強調(op: `rgb1_to_gray`, `gray_tophat`, `cv_clahe`)。素材: **AI 生成(Google gemini-2.5-flash-image)による模擬データ**(実在の標本・スキャンではない)*

## 地質学

![geo_earth](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_geo_earth_thumb.jpg)
*衛星画像の岩相を decorrelation stretch(リモートセンシング定番)で強調(op: `principal_comp`, `rgb1_to_gray`, `cv_clahe`)。素材: JSC — Public domain (NASA)([出典](https://images.nasa.gov/details/SL2-04-018))*

![geo_mineral](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_geo_mineral_thumb.jpg)
*鉱物結晶のファセット稜線を canny で抽出(op: `rgb1_to_gray`, `canny`, `overlay_mask`)。素材: **AI 生成(Google gemini-2.5-flash-image)による模擬データ**(実在の標本・スキャンではない)*

![geo_thin_section](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_geo_thin_section_thumb.jpg)
*岩石薄片(偏光顕微鏡風)を multi-Otsu で鉱物粒子に分類(op: `rgb1_to_gray`, `xsk2_multiotsu`, `colorize_labels`)。素材: **AI 生成(Google gemini-2.5-flash-image)による模擬データ**(実在の標本・スキャンではない)*

## 気象学

![met_hurricane](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_met_hurricane_thumb.jpg)
*ハリケーンの渦構造を sobel_dir 勾配方向ホイールで可視化(op: `rgb1_to_gray`, `cv_clahe`, `sobel_amp`, `sobel_dir`, `colorize_flow`)。素材: JSC — Public domain (NASA)([出典](https://images.nasa.gov/details/iss056e162187))*

![met_supercell](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_met_supercell_thumb.jpg)
*スーパーセル積乱雲(AI 生成)を cv_clahe + unsharp で構造強調(op: `rgb1_to_gray`, `cv_clahe`, `unsharp`)。素材: **AI 生成(Google gemini-2.5-flash-image)による模擬データ**(実在の標本・スキャンではない)*

## 海洋学

![ocean_coral](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_ocean_coral_thumb.jpg)
*サンゴ礁(AI 生成)を multi-Otsu で被覆分類(海洋調査風)(op: `rgb1_to_gray`, `xsk2_multiotsu`, `colorize_labels`)。素材: **AI 生成(Google gemini-2.5-flash-image)による模擬データ**(実在の標本・スキャンではない)*

## 植物学

![bot_fern](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bot_fern_thumb.jpg)
*シダ葉脈(AI 生成)を sk_frangi で葉脈抽出し、応答上位 8% を着色オーバーレイ表示(op: `rgb1_to_gray`, `cv_clahe`, `cv_median`, `sk_frangi`, `sk_area_opening`, `overlay_mask`)。素材: **AI 生成(Google gemini-2.5-flash-image)による模擬データ**(実在の標本・スキャンではない)*

![bot_pollen](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bot_pollen_thumb.jpg)
*花粉 SEM 風画像(AI 生成)を分割・計数 検出数 = 41(op: `rgb1_to_gray`, `segment_objects(otsu)`, `count_obj`, `colorize_labels`)。素材: **AI 生成(Google gemini-2.5-flash-image)による模擬データ**(実在の標本・スキャンではない)*
