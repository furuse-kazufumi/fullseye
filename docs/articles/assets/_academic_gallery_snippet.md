<!-- 記事貼り付け用スニペット: 学問分野横断ギャラリー (gen_academic_gallery.py) -->
<!-- 画像はサムネ(720px JPG)。フル解像度は _thumb を外した .png -->

## 宇宙

![space_carina](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_carina_thumb.jpg)
*星雲のフィラメント構造を sk_frangi(血管強調フィルタ)で抽出(op: `rgb1_to_gray`, `cv_clahe`, `sk_frangi`)。素材: STScI (Webb) — Public domain (NASA)([出典](https://images.nasa.gov/details/carina_nebula))*

![space_mars](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_mars_thumb.jpg)
*火星表面の岩石テクスチャを std_filter / texture_laws で解析(op: `rgb1_to_gray`, `std_filter`, `texture_laws`)。素材: NASA/JPL-Caltech — Public domain (NASA)([出典](https://images.nasa.gov/details/PIA14760))*

![space_galaxy](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_galaxy_thumb.jpg)
*渦巻銀河の周波数構造を cx_fft スペクトルで可視化(op: `rgb1_to_gray`, `cv_clahe`, `cx_fft`, `cx_magnitude`)。素材: GSFC — Public domain (NASA)([出典](https://images.nasa.gov/details/hubble-sees-a-galactic-sunflower_21136469209_o))*

## 地質学

![geo_earth](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_geo_earth_thumb.jpg)
*衛星画像の岩相を decorrelation stretch(リモートセンシング定番)で強調(op: `principal_comp`, `rgb1_to_gray`, `cv_clahe`)。素材: JSC — Public domain (NASA)([出典](https://images.nasa.gov/details/SL2-04-018))*

## 気象学

![met_hurricane](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_met_hurricane_thumb.jpg)
*ハリケーンの渦構造を sobel_dir 勾配方向ホイールで可視化(op: `rgb1_to_gray`, `cv_clahe`, `sobel_amp`, `sobel_dir`, `colorize_flow`)。素材: JSC — Public domain (NASA)([出典](https://images.nasa.gov/details/iss056e162187))*
