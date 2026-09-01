続いて分野別の展示室です。医学・考古学・生物学・宇宙・古生物学・地質学・気象学・海洋学・植物学 ―― **どの分野の画像にも、同じ op 体系がそのまま刺さる**ことを見てもらうコーナーです。ここから先のキャプション表記は上と同じルール（実データは出典リンク、AI 生成は明記）です。

#### 古生物学

[![アンモナイト化石の螺旋抽出](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_ammonite_real_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_ammonite_real.png)

*↑ アンモナイト化石（[Smithsonian Open Access, CC0](http://n2t.net/ark:/65665/34afa6692-b3f9-408d-90dc-cc53097171b6)）の螺旋を `canny` で抽出。使用 op: `rgb1_to_gray`, `canny`, `overlay_mask`。*

[![ティラノサウルス生体復元の皮膚テクスチャ解析](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_trex_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_trex.png)

*↑ ティラノサウルス生体復元の皮膚テクスチャを `std_filter` / `texture_laws` で解析。素材は **AI 生成（gemini-2.5-flash-image）の模擬データ**（実在の標本ではありません）。*

[![トリケラトプス生体復元の multi-Otsu 分類](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_triceratops_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_triceratops.png)

*↑ トリケラトプス生体復元を multi-Otsu で領域分類。素材は **AI 生成の模擬データ**。使用 op: `xsk2_multiotsu`, `colorize_labels`。*

[![羽毛恐竜の羽毛流れ解析](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_feathered_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_feathered.png)

*↑ 羽毛恐竜の羽毛の流れを Gabor フィルタで解析。素材は **AI 生成の模擬データ**。使用 op: `sk_gabor`, `std_filter`。*

[![アンモナイト断面の対数螺旋 FFT](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_ammonite_section_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_ammonite_section.png)

*↑ アンモナイト断面の対数螺旋を FFT スペクトルで観察。素材は **AI 生成の模擬データ**。使用 op: `cv_clahe`, `cx_fft`, `cx_magnitude`。*

[![三葉虫の体節を浮き彫り強調](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_trilobite_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_trilobite.png)

*↑ 三葉虫の体節を `gray_tophat` で浮き彫り強調。素材は **AI 生成の模擬データ**。*

#### 宇宙

[![カリーナ星雲のフィラメント抽出](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_carina_thumb.jpg?v=2)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_carina.png)

*↑ カリーナ星雲（[NASA/STScI Webb, public domain](https://images.nasa.gov/details/carina_nebula)）のフィラメント構造を、本来は血管強調用の `sk_frangi` で抽出。医学の op が天文に刺さる例。*

[![火星 Nili Patera 砂丘のテクスチャ解析](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_mars_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_mars.png)

*↑ 火星の砂丘（[NASA/JPL-Caltech/Univ. of Arizona, public domain](https://images.nasa.gov/details/PIA18244)）のテクスチャを `std_filter` / `texture_laws` で解析。*

[![ひまわり銀河の FFT スペクトル](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_galaxy_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_galaxy.png)

*↑ 渦巻銀河（[NASA GSFC, public domain](https://images.nasa.gov/details/hubble-sees-a-galactic-sunflower_21136469209_o)）の周波数構造を `cx_fft` で可視化。*

#### 医学（このブロックはすべて AI 生成の模擬データです）

[![胸部X線風画像の強調とエッジ抽出](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_chest_xray_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_chest_xray.png)

*↑ 胸部X線**風**画像を `cv_clahe` + `sobel_amp` で強調・エッジ抽出。**AI 生成の模擬データ**（実在の患者・スキャンではありません）。*

[![H&E 組織切片風画像の multi-Otsu 分類](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_histology_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_histology.png)

*↑ H&E 組織切片**風**画像を multi-Otsu で組織構造分類。**AI 生成の模擬データ**。*

[![脳 MRI 風画像のコントラスト強調](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_brain_mri_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_brain_mri.png)

*↑ 脳 MRI **風**画像を `cv_clahe` + `unsharp` で組織コントラスト強調。**AI 生成の模擬データ**。*

[![血液塗抹風画像の血球計数](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_blood_smear_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_blood_smear.png)

*↑ 血液塗抹**風**画像の血球を分割・計数（検出数 131）。**AI 生成の模擬データ**。使用 op: `segment_objects(otsu)`, `colorize_labels`。*

[![解剖図風イラストの輪郭抽出](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_anatomy_heart_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_anatomy_heart.png)

*↑ 解剖図**風**イラストの輪郭を `canny` で抽出。**AI 生成の模擬データ**。*

#### 生物学

[![神経細胞の樹状突起トレース](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_neuron_thumb.jpg?v=2)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_neuron.png)

*↑ 神経細胞蛍光像の樹状突起を `sk_frangi` でトレース。**AI 生成の模擬データ**。*

[![珪藻の分割と計数](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_diatoms_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_diatoms.png)

*↑ 珪藻顕微鏡像を分割・計数（検出数 123）。**AI 生成の模擬データ**。*

[![深海アンコウの暗部増強](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_deepsea_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_deepsea.png)

*↑ 深海生物の暗部を `cv_clahe` で増強。**AI 生成の模擬データ**。*

[![蝶の翅鱗粉の周期構造解析](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_butterfly_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_butterfly.png)

*↑ 蝶の翅の鱗粉の周期構造を `sk_gabor` で解析。**AI 生成の模擬データ**。*

#### 考古学

[![土器シルエットの楕円フーリエ記述子](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_amphora_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_amphora.png)

*↑ アンフォラ（[メトロポリタン美術館 Open Access, CC0](https://www.metmuseum.org/art/collection/search/254896)）のシルエットを楕円フーリエ記述子（EFD）で形状復元。2 → 8 → 32 高調波と増やすほど輪郭に吸い付いていく ―― 考古学の土器形状分類で実際に使われる手法です。使用 op: `otsu`, `fourierdesc.elliptic_fourier`, `fourierdesc.reconstruct`。*

[![石碑レリーフの浮き彫り強調](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_relief_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_relief.png)

*↑ アッシリアの石碑レリーフ（[メトロポリタン美術館, CC0](https://www.metmuseum.org/art/collection/search/322611)）の彫刻を `gray_tophat` で浮き彫り強調。*

[![洞窟壁画の顔料強調（DStretch 手法）](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_cave_painting_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_cave_painting.png)

*↑ 洞窟壁画の消えかけた顔料を decorrelation stretch（岩絵調査の定番 DStretch と同系の手法）で強調。**AI 生成の模擬データ**。使用 op: `principal_comp`。*

[![楔形文字粘土板の刻印強調](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_cuneiform_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_cuneiform.png)

*↑ 楔形文字粘土板の文字刻印を `gray_tophat` で強調。**AI 生成の模擬データ**。*

#### 地質学・気象学・海洋学・植物学

[![衛星画像の岩相 decorrelation stretch](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_geo_earth_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_geo_earth.png)

*↑ 衛星画像（[NASA JSC, public domain](https://images.nasa.gov/details/SL2-04-018)）の岩相を decorrelation stretch（リモートセンシングの定番）で強調。*

[![鉱物結晶のファセット稜線抽出](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_geo_mineral_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_geo_mineral.png)

*↑ アメジスト結晶のファセット稜線を `canny` で抽出。**AI 生成の模擬データ**。*

[![岩石薄片の鉱物粒子分類](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_geo_thin_section_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_geo_thin_section.png)

*↑ 岩石薄片（偏光顕微鏡風）を multi-Otsu で鉱物粒子に分類。**AI 生成の模擬データ**。*

[![ハリケーンの渦構造の勾配方向ホイール](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_met_hurricane_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_met_hurricane.png)

*↑ ハリケーン（[NASA JSC, public domain](https://images.nasa.gov/details/iss056e162187)）の渦構造を勾配方向ホイール（`sobel_dir` + `colorize_flow`）で可視化。*

[![スーパーセル積乱雲の構造強調](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_met_supercell_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_met_supercell.png)

*↑ スーパーセル積乱雲を `cv_clahe` + `unsharp` で構造強調。**AI 生成の模擬データ**。*

[![サンゴ礁の被覆分類](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_ocean_coral_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_ocean_coral.png)

*↑ サンゴ礁を multi-Otsu で被覆分類（海洋調査風）。**AI 生成の模擬データ**。*

[![シダ葉脈の抽出](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bot_fern_thumb.jpg?v=2)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bot_fern.png)

*↑ シダの葉脈を `sk_frangi` で抽出。**AI 生成の模擬データ**。*

[![花粉 SEM 風画像の分割と計数](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bot_pollen_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bot_pollen.png)

*↑ 花粉 SEM **風**画像を分割・計数（検出数 41）。**AI 生成の模擬データ**。*

この 41 展示のうち、**実データにはすべて出典とライセンス**（詳細な帰属表は[ACADEMIC_ATTRIBUTION.md](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/articles/assets/ACADEMIC_ATTRIBUTION.md)）を、**AI 生成には全点にその旨**を付けました。おまけをひとつ ―― この「多様な実データを流す」作業は、それ自体が**バグ発見器**でもありました。合成データでは表面化しなかった op の不具合が実データで 5 件見つかり、**公開前にすべて修正済み**です（発見の経緯と回帰テストは [docs/KNOWN_ISSUES.md](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/KNOWN_ISSUES.md)）。きれいな展示の裏で、テストにもなっている ―― という一石二鳥でした。

---
