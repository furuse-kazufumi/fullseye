[![距離変換の虹の波紋](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_distance_ripple_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_distance_ripple.png)

*↑ **距離変換の虹の波紋** ―― コイン写真を白黒に分け、「ふちから何ピクセル離れているか」を虹色で塗ると波紋のような等高線が浮かぶ。使用 op: `otsu`, `fill_up`, `distance_transform`。*

[![フーリエの世界](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_fourier_stars_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_fourier_stars.png)

*↑ **フーリエの世界** ―― 画像を周波数で見ると「どんな細かさの模様がどの向きにあるか」が光の点になる。規則正しい織り目は星座のように光る（織り目パネルのみ合成）。使用 op: `fft_image`。*

[![watershed ―― コインのぬりえ分割](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_watershed_foam_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_watershed_foam.png)

*↑ **watershed のぬりえ分割** ―― 水が低い所へ流れて溜まる様子をまねて、コインを 1 枚ずつ別の色に。使用 op: `otsu`, `distance_transform`, `watersheds`, `colorize_labels`。*

[![エッジの方位磁針](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_edge_compass_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_edge_compass.png)

*↑ **エッジの方位磁針** ―― 輪郭の向きを色相環の色で塗ると、同じ向きの線が同じ色に光る。使用 op: `sobel_amp`, `sobel_dir`。*

[![単純ルールから生まれる 6 つの宇宙](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_alife_worlds_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_alife_worlds.png)

*↑ **単純ルールから生まれる 6 つの宇宙** ―― 「となりのマスを見て自分の色を決める」だけのルールから、フラクタル・カオス・砂山マンダラ・樹枝・珊瑚もようが生まれる（シミュレーション画像）。使用 op: `alife_wolfram1d`, `alife_sandpile`, `alife_dla`, `alife_lenia`, `alife_cyclic_ca`。*

[![トリケラトプスのレントゲン写真](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_xray_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_xray.png)

*↑ **トリケラトプスのレントゲン写真** ―― Smithsonian の骨格標本実スキャン（CC0）をボクセルに詰めて最大値投影（MIP）すると、レントゲン写真そっくりになる。肋骨も角も写る。使用 op: `voxelize`, `vol_gaussian`, `vol_mip`。*

[![赤青メガネで飛び出すドラゴン](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dragon_anaglyph_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dragon_anaglyph.png)

*↑ **赤青メガネで飛び出すドラゴン** ―― Stanford dragon 実スキャンを 2 視点からレンダして赤シアンで重ねたアナグリフ。赤青メガネで浮き上がります。使用 op: `read_mesh`, `look_at`, `render_mesh`。*

[![トリケラトプス山脈](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_terrain_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_terrain.png)

*↑ **トリケラトプス山脈** ―― 骨格標本を 60 万点の点群にして真上から標高地図を作ると、背骨が山脈、肋骨が尾根になる。ロボットが地形を読むのと同じ op です。使用 op: `sample_surface`, `elevation_map`, `colorize_height`。*

![形が育つ・痩せる（モルフォロジー）](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_morph_pulse.gif)

*↑ **形が育つ・痩せる** ―― 膨張（dilation）でコインがぷくぷく育って合体し、収縮（erosion）で痩せる。工場の画像検査でも使う基本の op です。使用 op: `dilation_circle`, `erosion_circle`。*

[![空間がぐにゃり ―― 3 つの変形アルゴリズム](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_wobble_warp_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_wobble_warp.png)

*↑ **空間がぐにゃり** ―― 画像の下に見えないゴムのシートがあると思って、TPS / FFD / MLS という 3 つの流儀でつまんで引っぱった結果。使用 op: `deform_tps`, `deform_ffd`, `deform_mls`。*

[![恐竜の影絵から骨格を取り出す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_skeleton_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_skeleton.png)

*↑ **恐竜の影絵から骨格を取り出す** ―― トリケラトプス骨格標本の影絵から中心線（スケルトン）を 1 ピクセル幅で抽出。足・角・しっぽが針金細工のように残る。使用 op: `sk_skeleton`, `distance_transform` ほか。*
