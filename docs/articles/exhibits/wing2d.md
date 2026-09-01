<!-- tools/gen_wing2d_gallery.py が自動生成。記事本体 (docs/articles/*.md)
     には手を入れていません。ここは「紙面の科学館」2D 古典オペレータ・ウィングの
     キャプション原稿です。数値はすべて生成時の実測で、`_wing2d_meta.json` に
     同じ値が入っています。 -->

# 紙面の科学館 —— 2D 古典オペレータ・ウィング（14 の展示）

既存の「科学館ウィング(11 点)」「博物館ウィング(30 点)」と題材が重ならないよう、
**古典的な 2-D オペレータ**だけで組んだ一角です。すべて Fullseye の登録 op の実出力で、
素材は合成か skimage.data(BSD / public domain)。キャプションの数字は**生成時の実測値**で、
`docs/articles/assets/_wing2d_meta.json` に生の配列が入っています。

並べ方は 3 通り: **タイル**(並べて比べるもの)、**フリップブック GIF**(同じ寸法で工程が
進むもの)、**掃引 GIF**(軸ラベルつきのグラフが主役のもの)。1 枚・1 本を 1 展示と数えています。

再生成: `py -3.11 tools/gen_wing2d_gallery.py`(展示名を指定するなら `--subjects <name,...>`)。


## 1. 形態学の 4 兄弟 —— どれが何を消すのか

![形態学の 4 兄弟 —— どれが何を消すのか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing2d_morph_quartet.gif)

*↑ **形態学の 4 兄弟 —— どれが何を消すのか** ―― 幅 2/4/6/8/10 px の棒と幅 2/4/6 px のスリットを刻んだ図形に、4 つの形態学 op を半径 1→4 px で当てた。膨張は面積を 39148→47296 px に増やし、収縮は 33212→25456 px に減らす。開は面積をほぼ保ったまま細い棒だけを落とし (r=1 で 4/6/8/10 px が生き残り、r=4 では 10 px だけ)、閉は細い隙間だけを埋める (r=1 で幅 2 px、r=4 で幅 2/4/6 px のスリットが消える)。使用 op: `threshold`, `erosion_circle`, `dilation_circle`, `opening_circle`, `closing_circle`, `morph_grad`。*

<!-- 静止サムネ: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wing2d_morph_quartet_720.jpg -->

<!-- 生成: tools/gen_wing2d_gallery.py::subject_morph_quartet() / GIF / 8 パネル / Fullseye の描画 op (imagedraw.draw_circle) で作った合成テスト図形 -->

## 2. 周波数フィルタの効き

![周波数フィルタの効き](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing2d_freq_sweep.gif)

*↑ **周波数フィルタの効き** ―― 同じ写真にローパス・ハイパス・バンドパスを当て、遮断周波数を 0.05→0.45 (正規化) で掃引した。ローパスの遮断を 0.05 から 0.45 へ上げると 元画像との PSNR は 22.33→36.13 dB。一方その通過帯に入っているスペクトルエネルギーは遮断 0.05 の時点ですでに 98.27% —— 「エネルギーのほとんどは低周波にあるのに、見た目は高周波が決めている」という画像の癖がそのまま数字に出る。使用 op: `fft_image`, `lowpass`, `highpass`, `bandpass_image`。*

<!-- 静止サムネ: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wing2d_freq_sweep_720.jpg -->

<!-- 生成: tools/gen_wing2d_gallery.py::subject_freq_sweep() / GIF / 6 パネル / skimage.data camera (BSD / public domain) -->

## 3. ノイズ除去の比較 —— median / bilateral / NLM

![ノイズ除去の比較 —— median / bilateral / NLM](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing2d_denoise_compare.gif)

*↑ **ノイズ除去の比較 —— median / bilateral / NLM** ―― 同じ写真に σ=0.020→0.220 の白色ノイズを乗せ、median・bilateral・non-local means を固定パラメータで当てて PSNR を実測した 6 パネル。弱いノイズ (σ=0.020) では bilateral が 30.00 dB で最良だが、強いノイズ (σ=0.220) では median が 23.09 dB で逆転する —— 「どれが一番強いか」はノイズ量と設定次第で、掃引の途中で順位が 2 度入れ替わった。ノイズ画像そのものは 34.04→14.34 dB。使用 op: `add_noise_white`, `median`, `bilateral`, `sk_nlm`, `estimate_noise`。*

<!-- 静止サムネ: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wing2d_denoise_compare_720.jpg -->

<!-- 生成: tools/gen_wing2d_gallery.py::subject_denoise_compare() / GIF / 6 パネル / skimage.data camera (BSD / public domain) + 決定的な白色ノイズ -->

## 4. ヒストグラム整形 —— equalize と clahe

![ヒストグラム整形 —— equalize と clahe](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing2d_hist_shaping.gif)

*↑ **ヒストグラム整形 —— equalize と clahe** ―― 文書画像のコントラストを 1.00→0.16 倍まで潰していき、equalize と clahe で戻せるかを追った。入力の標準偏差は 0.2228→0.0356 まで落ちるが、equalize 後は 0.2931→0.2994、clahe 後は 0.2379→0.2510 にとどまる。ヒストグラムは入力が針のように細くなっても、平坦化した側は幅を保ったままだ。使用 op: `equalize`, `clahe`, `gray_histo_abs`, `entropy_gray`。*

<!-- 静止サムネ: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wing2d_hist_shaping_720.jpg -->

<!-- 生成: tools/gen_wing2d_gallery.py::subject_hist_shaping() / GIF / 6 パネル / skimage.data page (BSD / public domain) -->

## 5. 楕円フーリエ記述子 —— 何次で形が戻るか

![楕円フーリエ記述子 —— 何次で形が戻るか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing2d_fourier_desc.gif)

*↑ **楕円フーリエ記述子 —— 何次で形が戻るか** ―― 1557 点の輪郭を楕円フーリエ記述子に直し、高調波を 1 次から 24 次まで足しながら復元した。1 次 (楕円 1 個) では最近傍 RMS 誤差 25.39 px、15 次で 1 px を切り、24 次では 0.45 px。誤差が大きく落ちるのは 2・4・6 次を足したときで、偶数次を足したときの平均低下 1.955 px に対し奇数次では 0.134 px しか下がらない —— r = 146 + 40sin3θ + 20cos5θ + 12sin9θ という作り方が、閉曲線としては n±1 次(= 偶数次)に現れるためだ。使用 op: `gen_region_polygon_filled`, `gen_contour_region_xld`, `elliptic_fourier`, `reconstruct`。*

<!-- 静止サムネ: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wing2d_fourier_desc_thumb.jpg -->

<!-- 生成: tools/gen_wing2d_gallery.py::subject_fourier_desc() / GIF / 2 パネル / Fullseye の region 生成 op で作った合成の葉形 (r = 146 + 40sin3θ + 20cos5θ + 12sin9θ) -->

## 6. 対応点モーフ —— 単純合成との違い

![対応点モーフ —— 単純合成との違い](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing2d_face_morph.gif)

*↑ **対応点モーフ —— 単純合成との違い** ―― 対応点 11 個 (輪郭の楕円上 8 点 + 両目 + 口) だけを与えて顔 A から顔 B へモーフさせた 6 パネル。対応点を使わない単純合成は途中で二重像になるが、piecewise affine と TPS は輪郭も目も口も対応させたまま連続的に動く。両端は入力を厳密に再現し (α=0 で A と PSNR 99.0 dB、α=1 で B と 99.0 dB = 完全一致の上限値)、2 つのワープ方式の差は α=0.5 で平均 0.00802 にとどまる。使用 op: `morph (imagemorph)`, `warp_piecewise_affine`, `warp_tps_image`, `blend`。*

<!-- 静止サムネ: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wing2d_face_morph_thumb.jpg -->

<!-- 生成: tools/gen_wing2d_gallery.py::subject_face_morph() / GIF / 6 パネル / Pillow で描いた合成の顔 2 枚 (実在の人物ではない) -->

## 7. ブロブ解析 —— 真円度で粒を選り分ける

![ブロブ解析 —— 真円度で粒を選り分ける](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing2d_blob_select.gif)

*↑ **ブロブ解析 —— 真円度で粒を選り分ける** ―― 円 8 個・楕円 1・四角 1・板 2・三角 1 を混ぜた合成シーンを二値化 → 穴埋め → ラベル付けし、blob_count が 13 個と数えた。真円度 (circularity) 0.85 をしきい値にすると採用 8 個 (真円度 0.912〜0.916)、不採用 5 個 (0.416〜0.797) にきれいに割れる —— 特徴空間の散布図でも 2 つの群がしきい値をまたいで重なっていない。使用 op: `threshold`, `fill_up`, `blob_count`, `colorize_labels`, `circularity`, `eccentricity`, `rectangularity`, `area_center`。*

<!-- 静止サムネ: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wing2d_blob_select_thumb.jpg -->

<!-- 生成: tools/gen_wing2d_gallery.py::subject_blob_select() / GIF / 6 パネル / Pillow で描いた合成の粒シーン (決定的) -->

## 8. サブピクセル計測 —— 画素より細かく測る

![サブピクセル計測 —— 画素より細かく測る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing2d_subpixel_edge.gif)

*↑ **サブピクセル計測 —— 画素より細かく測る** ―― ガウスぼけしたエッジの真の位置を 0.05 px 刻みで 1 画素ぶん動かし、`measure_pos` の推定と「勾配が最大の画素」を比べた。サブピクセル推定の誤差は RMS 0.0119 px・最大 0.0170 px、画素単位の推定は RMS 0.282 px・最大 0.50 px。同じ画像・同じエッジで **24 倍**の差が出る —— 画素の格子は、測れる細かさの限界ではない。使用 op: `gen_measure_rectangle2`, `measure_pos (m1_measure_pos)`。*

<!-- 静止サムネ: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wing2d_subpixel_edge_thumb.jpg -->

<!-- 生成: tools/gen_wing2d_gallery.py::subject_subpixel_edge() / GIF / 2 パネル / 解析式で作った合成のガウスぼけステップ (真値は式で与えた x0 そのもの) -->

## 9. 形状マッチング —— 回っていても見つける

![形状マッチング —— 回っていても見つける](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing2d_shape_match.gif)

*↑ **形状マッチング —— 回っていても見つける** ―― 96×96 px のテンプレートから作った形状モデルで、23° ずつ回した部品 (探索格子 5° の倍数を避けた角度) を 16 枚のシーンから探した。5° 刻みで角度も探索させると、角度の誤差は最大 2.0°(探索格子 5° の半分 = 2.5° がそもそもの下限)、位置の誤差は最大 0 px、スコアは最低でも 0.864。1 シーンあたり約 2.5 秒(CPU、72 角度ぶんの探索を含む)。使用 op: `create_shape_model`, `find_shape_model (角度探索つき)`。*

<!-- 静止サムネ: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wing2d_shape_match_thumb.jpg -->

<!-- 生成: tools/gen_wing2d_gallery.py::subject_shape_match() / GIF / 3 パネル / Pillow で描いた合成の六角ナット + 決定的な背景ノイズ -->

## 10. 帳票の傾き補正 → 二値化 → バーを数える

![帳票の傾き補正 → 二値化 → バーを数える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing2d_doc_deskew.gif)

*↑ **帳票の傾き補正 → 二値化 → バーを数える** ―― 合成の帳票を 0→42° と傾けながら、回転角を 0.5° 刻みで振って「行方向プロファイルの分散が最大になる角」を探した。推定誤差は全域で最大 0.0°(11° のときは真値どおり 11.0°)で、補正後の `decode_barcode` はどの傾きでも真値の 8 本を返す。補正しないと 30° を超えたところで 5 本まで取りこぼす —— 前処理を 1 段挟むかどうかで、同じ op の答えが変わる。使用 op: `rotate_image`, `otsu`, `decode_barcode`。*

<!-- 静止サムネ: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wing2d_doc_deskew_thumb.jpg -->

<!-- 生成: tools/gen_wing2d_gallery.py::subject_doc_deskew() / GIF / 6 パネル / Pillow で描いた合成の帳票 (バーコードは本数だけが意味を持つ模擬) -->

## 11. 輪郭の当てはめと残差

![輪郭の当てはめと残差](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing2d_fit_residual.gif)

*↑ **輪郭の当てはめと残差** ―― 縁が 72 px 欠けた円と直線に、輪郭からの当てはめを掛けた 6 コマ。輪郭の全点で当てると半径は真値 210.0 px に対し 206.95 px (誤差 -3.05 px、残差 RMS 12.96 px) —— 欠けの縁が当てはめを引っ張っており、残差 3σ を超える 91 点を落として当て直すと 209.19 px (誤差 -0.81 px、RMS 6.21 px) まで戻る。直線は真値 73.20° に対し 73.21°(誤差 +0.006°)で、「当てはまった値」より「合わなかった場所」の方が情報が多い。使用 op: `threshold`, `opening_circle`, `gen_contour_region_xld`, `sobel_amp`, `fit_circle`, `fit_line`。*

<!-- 静止サムネ: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wing2d_fit_residual_thumb.jpg -->

<!-- 生成: tools/gen_wing2d_gallery.py::subject_fit_residual() / GIF / 6 パネル / Pillow で描いた合成の円 (欠けあり) と直線 + 決定的なガウスノイズ -->

## 12. 色空間ツアー —— どの空間なら分けられるか

[![色空間ツアー —— どの空間なら分けられるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing2d_colour_tour_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing2d_colour_tour.png)

*↑ **色空間ツアー —— どの空間なら分けられるか** ―― 同じ赤で塗った 2 つの円を、左は 0.35 倍・右は 1.0 倍の明るさで照らした合成シーンを 6 チャンネルで見た 9 パネル。1 本のしきい値で赤い 2 円を取り切れるかを IoU で測ると HSV の H (色相)・Lab の a (赤-緑) が 1.000 に届き、Lab の L (明るさ) は最良でも 0.250 —— 明るさを含むチャンネルでは、同じ色が照明で 2 つに割れてしまう。なお HSV の H は cv2 由来で 0..179 を 255 で割った値、つまり度÷510 で返る(純緑 120° が 0.2353 —— 実測して確かめた単位)。使用 op: `trans_from_rgb`, `access_channel`, `rgb1_to_gray`。*

<!-- 生成: tools/gen_wing2d_gallery.py::subject_colour_tour() / PNG / 9 パネル / numpy で合成した色つきシーン (左→右に照明勾配) -->

## 13. テクスチャの見分け —— 特徴量で模様を分ける

[![テクスチャの見分け —— 特徴量で模様を分ける](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing2d_texture_zoo_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing2d_texture_zoo.png)

*↑ **テクスチャの見分け —— 特徴量で模様を分ける** ―― 3 種類の模様を 64×64 px の小片 48 枚に切り分け、GLCM energy・entropy・標準偏差・ノイズ推定・4 方向の Gabor 応答の 8 個を特徴量にして leave-one-out の最近傍重心で分類したところ 47/48 = 97.9% が正解だった。見た目が似ていても、GLCM energy は 0.236 / 0.148 / 0.212 と離れている —— 「模様」は数字にできる。使用 op: `cooc_feature_matrix`, `entropy_gray`, `gray_histo_abs`, `estimate_noise`, `gabor`, `sk_lbp`。*

<!-- 生成: tools/gen_wing2d_gallery.py::subject_texture_zoo() / PNG / 12 パネル / Fullseye の synth で合成したテクスチャ 3 種 (レンガ / 織り目 / 1/f 粒状) -->

## 14. 回し続けると何が失われるか (リサンプリング損失)

[![回し続けると何が失われるか (リサンプリング損失)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing2d_resample_loss_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing2d_resample_loss.png)

*↑ **回し続けると何が失われるか (リサンプリング損失)** ―― 同じ画像に 10° の回転を 36 回かけると、幾何としては一周して元の向きに戻るのに、画素は戻らない。中央部だけで測っても元画像との PSNR は 26.81 dB、中央の「細かさ」(画像 − ローパスの標準偏差) は元の 64.4% まで落ちる(画像全体では 23.98 dB。その差の大半は端の処理 —— rotate_image は reshape=False + mode='reflect' —— によるもので補間の損失ではない)。ついでの実測として `zoom_image_factor` / `zoom_image_size` / `rescale_img` の 3 op は それぞれ別実装で、出力の形も zoom_image_factor=256x256 / zoom_image_size=358x256 / rescale_img=256x256(`zoom_image_size` だけが目標サイズ指定なので形が変わる)。使用 op: `rotate_image`, `gauss_image`, `zoom_image_factor`, `zoom_image_size`, `rescale_img`。*

<!-- 生成: tools/gen_wing2d_gallery.py::subject_resample_loss() / PNG / 8 パネル / skimage.data camera (BSD / public domain) を 1/2 に間引いたもの -->
