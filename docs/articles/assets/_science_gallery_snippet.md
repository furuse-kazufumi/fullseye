<!-- gen_science_gallery.py が自動生成。GALLERY.md / 記事 md への
     追記候補 (このファイル自体は記事ではない)。 -->

# 科学ギャラリー追加分 — GALLERY.md 追記セクション + 記事挿入候補

## GALLERY.md 追記セクション (そのまま貼り付け可)

```markdown
## 科学ギャラリー — 子供向けサイエンス画像 (`tools/gen_science_gallery.py`)

生成元: `tools/gen_science_gallery.py` (subject 単位で再生成可能:
`py -3.11 tools/gen_science_gallery.py --subjects <name,...>`)。
すべて fullseye の登録 op / facade の実出力で、モックアップはありません。
シミュレーション由来の画像はキャプションにその旨を明記しています。
サムネ (幅 720px JPG) は同ディレクトリの `*_thumb.jpg`。

### 距離変換の虹の波紋

生成元: `tools/gen_science_gallery.py::subject_distance_ripple()`

![science_distance_ripple](articles/assets/science_distance_ripple.png)

コインの写真を白黒に分け、「ふちから何ピクセル離れているか」を虹色で塗ると、波紋のような等高線が浮かび上がる。 使用 op: otsu, fill_up, distance_transform。データ: skimage.data coins (実写真)。

### フーリエの世界 — 画像を周波数で見る

生成元: `tools/gen_science_gallery.py::subject_fourier_stars()`

![science_fourier_stars](articles/assets/science_fourier_stars.png)

画像をフーリエ変換すると「どんな細かさの模様がどの向きに入っているか」が光の点になって見える。規則正しい織り目は星座のように光る。 ※織り目パネルのみ合成。 使用 op: fft_image。データ: skimage.data camera (実写真) + fullseye synth 織り目 (合成)。

### watershed — コインのぬりえ分割

生成元: `tools/gen_science_gallery.py::subject_watershed_foam()`

![science_watershed_foam](articles/assets/science_watershed_foam.png)

水が低い所へ流れて溜まる様子をまねて領域を分ける watershed 法。写真のコインが 1 枚ずつ別の色に塗り分けられる。 使用 op: otsu, fill_up, distance_transform, watersheds, segment_objects, colorize_labels。データ: skimage.data coins (実写真)。

### エッジの方位磁針

生成元: `tools/gen_science_gallery.py::subject_edge_compass()`

![science_edge_compass](articles/assets/science_edge_compass.png)

輪郭がどちらを向いているかを色相環の色で塗ると、同じ向きの線が同じ色に光り、写真の骨組みが見えてくる。 使用 op: sobel_amp, sobel_dir。データ: skimage.data camera (実写真)。

### 単純ルールから生まれる 6 つの宇宙

生成元: `tools/gen_science_gallery.py::subject_alife_worlds()`

![science_alife_worlds](articles/assets/science_alife_worlds.png)

となりのマスを見て自分の色を決める——それだけのルールを繰り返すと、フラクタル・カオス・結晶・珊瑚もようが勝手に生まれる。 ※シミュレーション画像 (実写ではない)。 使用 op: alife_wolfram1d, alife_sandpile, alife_dla, alife_lenia, alife_cyclic_ca, gauss_filter。データ: 0 と乱数の初期値から反復シミュレーション。

### トリケラトプスのレントゲン写真

生成元: `tools/gen_science_gallery.py::subject_dino_xray()`

![science_dino_xray](articles/assets/science_dino_xray.png)

スミソニアン博物館の骨格標本スキャンをボクセル (3D のピクセル) に詰め、最大値投影 (vol_mip) するとレントゲン写真そっくりになる。 使用 op: voxelize, vol_gaussian, vol_mip。データ: Smithsonian 3D triceratops 骨格標本の実スキャン (CC0)。

### 赤青メガネで飛び出すドラゴン

生成元: `tools/gen_science_gallery.py::subject_dragon_anaglyph()`

![science_dragon_anaglyph](articles/assets/science_dragon_anaglyph.png)

左目用と右目用、少しずらした 2 枚を赤とシアンで重ねたアナグリフ。赤青メガネをかけると龍が画面から浮き上がる。 使用 op: read_mesh, look_at, render_mesh。データ: Stanford dragon 実スキャン。

### トリケラトプス山脈 — 恐竜を地図にする

生成元: `tools/gen_science_gallery.py::subject_dino_terrain()`

![science_dino_terrain](articles/assets/science_dino_terrain.png)

骨格標本の実スキャンを 60 万点の点群にして真上から標高地図を作ると、背骨が山脈、ろっ骨が尾根になる。ロボットが地形を読むのと同じ op。 使用 op: sample_surface, elevation_map, colorize_height。データ: Smithsonian 3D triceratops 骨格標本の実スキャン (CC0)。

### 形が育つ・痩せる (モルフォロジー)

生成元: `tools/gen_science_gallery.py::subject_morph_pulse()`

![science_morph_pulse](articles/assets/science_morph_pulse.gif)

膨張 (dilation) でコインがぷくぷく育って合体し、収縮 (erosion) で痩せていく。工場の画像検査でも使う基本の op。 使用 op: otsu, fill_up, dilation_circle, erosion_circle。データ: skimage.data coins (実写真)。

### 空間がぐにゃり — 3 つの変形アルゴリズム

生成元: `tools/gen_science_gallery.py::subject_wobble_warp()`

![science_wobble_warp](articles/assets/science_wobble_warp.png)

画像の下に見えないゴムのシートがあると思って、数学の異なる 3 つの流儀でつまんで引っぱった結果。 使用 op: deform_tps, deform_ffd, deform_mls。データ: skimage.data camera (実写真)。

### 恐竜の影絵から骨格を取り出す

生成元: `tools/gen_science_gallery.py::subject_dino_skeleton()`

![science_dino_skeleton](articles/assets/science_dino_skeleton.png)

トリケラトプス骨格標本の影絵から、形の中心線 (スケルトン) を1 ピクセル幅で抽出。足・角・しっぽが針金細工のように残る。 使用 op: read_mesh, look_at, render_mesh, dilation_circle, erosion_circle, fill_up, select_shape_std, sk_skeleton, distance_transform。データ: Smithsonian 3D triceratops 骨格標本の実スキャン (CC0)。

```

## 記事挿入候補 (raw GitHub URL)

### 距離変換の虹の波紋

![距離変換の虹の波紋](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_distance_ripple_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_distance_ripple.png )

コインの写真を白黒に分け、「ふちから何ピクセル離れているか」を虹色で塗ると、波紋のような等高線が浮かび上がる。 使用 op: otsu, fill_up, distance_transform。データ: skimage.data coins (実写真)。

### フーリエの世界 — 画像を周波数で見る

![フーリエの世界 — 画像を周波数で見る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_fourier_stars_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_fourier_stars.png )

画像をフーリエ変換すると「どんな細かさの模様がどの向きに入っているか」が光の点になって見える。規則正しい織り目は星座のように光る。※織り目パネルのみ合成。 使用 op: fft_image。データ: skimage.data camera (実写真) + fullseye synth 織り目 (合成)。

### watershed — コインのぬりえ分割

![watershed — コインのぬりえ分割](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_watershed_foam_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_watershed_foam.png )

水が低い所へ流れて溜まる様子をまねて領域を分ける watershed 法。写真のコインが 1 枚ずつ別の色に塗り分けられる。 使用 op: otsu, fill_up, distance_transform, watersheds, segment_objects, colorize_labels。データ: skimage.data coins (実写真)。

### エッジの方位磁針

![エッジの方位磁針](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_edge_compass_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_edge_compass.png )

輪郭がどちらを向いているかを色相環の色で塗ると、同じ向きの線が同じ色に光り、写真の骨組みが見えてくる。 使用 op: sobel_amp, sobel_dir。データ: skimage.data camera (実写真)。

### 単純ルールから生まれる 6 つの宇宙

![単純ルールから生まれる 6 つの宇宙](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_alife_worlds_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_alife_worlds.png )

となりのマスを見て自分の色を決める——それだけのルールを繰り返すと、フラクタル・カオス・結晶・珊瑚もようが勝手に生まれる。※シミュレーション画像 (実写ではない)。 使用 op: alife_wolfram1d, alife_sandpile, alife_dla, alife_lenia, alife_cyclic_ca, gauss_filter。データ: 0 と乱数の初期値から反復シミュレーション。

### トリケラトプスのレントゲン写真

![トリケラトプスのレントゲン写真](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_xray_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_xray.png )

スミソニアン博物館の骨格標本スキャンをボクセル (3D のピクセル) に詰め、最大値投影 (vol_mip) するとレントゲン写真そっくりになる。 使用 op: voxelize, vol_gaussian, vol_mip。データ: Smithsonian 3D triceratops 骨格標本の実スキャン (CC0)。

### 赤青メガネで飛び出すドラゴン

![赤青メガネで飛び出すドラゴン](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dragon_anaglyph_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dragon_anaglyph.png )

左目用と右目用、少しずらした 2 枚を赤とシアンで重ねたアナグリフ。赤青メガネをかけると龍が画面から浮き上がる。 使用 op: read_mesh, look_at, render_mesh。データ: Stanford dragon 実スキャン。

### トリケラトプス山脈 — 恐竜を地図にする

![トリケラトプス山脈 — 恐竜を地図にする](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_terrain_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_terrain.png )

骨格標本の実スキャンを 60 万点の点群にして真上から標高地図を作ると、背骨が山脈、ろっ骨が尾根になる。ロボットが地形を読むのと同じ op。 使用 op: sample_surface, elevation_map, colorize_height。データ: Smithsonian 3D triceratops 骨格標本の実スキャン (CC0)。

### 形が育つ・痩せる (モルフォロジー)

![形が育つ・痩せる (モルフォロジー)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_morph_pulse.gif)

膨張 (dilation) でコインがぷくぷく育って合体し、収縮 (erosion) で痩せていく。工場の画像検査でも使う基本の op。 使用 op: otsu, fill_up, dilation_circle, erosion_circle。データ: skimage.data coins (実写真)。

### 空間がぐにゃり — 3 つの変形アルゴリズム

![空間がぐにゃり — 3 つの変形アルゴリズム](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_wobble_warp_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_wobble_warp.png )

画像の下に見えないゴムのシートがあると思って、数学の異なる 3 つの流儀でつまんで引っぱった結果。 使用 op: deform_tps, deform_ffd, deform_mls。データ: skimage.data camera (実写真)。

### 恐竜の影絵から骨格を取り出す

![恐竜の影絵から骨格を取り出す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_skeleton_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_skeleton.png )

トリケラトプス骨格標本の影絵から、形の中心線 (スケルトン) を1 ピクセル幅で抽出。足・角・しっぽが針金細工のように残る。 使用 op: read_mesh, look_at, render_mesh, dilation_circle, erosion_circle, fill_up, select_shape_std, sk_skeleton, distance_transform。データ: Smithsonian 3D triceratops 骨格標本の実スキャン (CC0)。
