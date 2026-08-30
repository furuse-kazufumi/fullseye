<!-- gen_science_gallery.py が自動生成。GALLERY.md / 記事 md への
     追記候補 (このファイル自体は記事ではない)。 -->

# 科学ギャラリー追加分 — GALLERY.md 追記行 + 記事挿入候補

## GALLERY.md 追記行

| 距離変換の虹の波紋 | ![距離変換の虹の波紋](assets/science_distance_ripple_thumb.jpg) | otsu, fill_up, distance_transform | skimage.data coins (実写真) |
| フーリエの世界 — 画像を周波数で見る | ![フーリエの世界 — 画像を周波数で見る](assets/science_fourier_stars_thumb.jpg) | fft_image | skimage.data camera (実写真) + fullseye synth 織り目 (合成) |
| エッジの方位磁針 | ![エッジの方位磁針](assets/science_edge_compass_thumb.jpg) | sobel_amp, sobel_dir | skimage.data camera (実写真) |
| watershed — コインのぬりえ分割 | ![watershed — コインのぬりえ分割](assets/science_watershed_foam_thumb.jpg) | otsu, fill_up, distance_transform, watersheds, segment_objects, colorize_labels | skimage.data coins (実写真) |
| 人工生命の 6 つの宇宙 | ![人工生命の 6 つの宇宙](assets/science_alife_worlds_thumb.jpg) | alife_gray_scott, alife_turing, alife_lenia, alife_dla, alife_sandpile, alife_wolfram1d | 乱数ノイズ / 1 点から成長 (シミュレーション) |
| 空間がぐにゃり — 3 つの変形アルゴリズム | ![空間がぐにゃり — 3 つの変形アルゴリズム](assets/science_wobble_warp_thumb.jpg) | deform_tps, deform_ffd, deform_mls | skimage.data camera (実写真) |
| 樹枝状結晶とその骨格 | ![樹枝状結晶とその骨格](assets/science_dla_skeleton_thumb.jpg) | alife_dla, dilation_circle, sk_skeleton, distance_transform | 乱数から DLA 成長 (シミュレーション) |

## 記事挿入候補 (raw GitHub URL)

### 距離変換の虹の波紋

![距離変換の虹の波紋](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_distance_ripple_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_distance_ripple.png )

コインの写真を白黒に分け、「ふちから何ピクセル離れているか」を虹色で塗ると、波紋のような等高線が浮かび上がる。 使用 op: otsu, fill_up, distance_transform。データ: skimage.data coins (実写真)。

### フーリエの世界 — 画像を周波数で見る

![フーリエの世界 — 画像を周波数で見る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_fourier_stars_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_fourier_stars.png )

画像をフーリエ変換すると「どんな細かさの模様がどの向きに入っているか」が光の点になって見える。規則正しい織り目は星座のように光る。※織り目パネルのみ合成。 使用 op: fft_image。データ: skimage.data camera (実写真) + fullseye synth 織り目 (合成)。

### エッジの方位磁針

![エッジの方位磁針](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_edge_compass_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_edge_compass.png )

輪郭がどちらを向いているかを色相環の色で塗ると、同じ向きの線が同じ色に光り、写真の骨組みが見えてくる。 使用 op: sobel_amp, sobel_dir。データ: skimage.data camera (実写真)。

### watershed — コインのぬりえ分割

![watershed — コインのぬりえ分割](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_watershed_foam_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_watershed_foam.png )

水が低い所へ流れて溜まる様子をまねて領域を分ける watershed 法。写真のコインが 1 枚ずつ別の色に塗り分けられる。 使用 op: otsu, fill_up, distance_transform, watersheds, segment_objects, colorize_labels。データ: skimage.data coins (実写真)。

### 人工生命の 6 つの宇宙

![人工生命の 6 つの宇宙](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_alife_worlds_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_alife_worlds.png )

単純なルールを繰り返すだけで、ヒョウ柄・生き物・結晶・雪崩・フラクタルが勝手に生まれる。全部 fullseye の op 1 回ずつ。※シミュレーション画像 (実写ではない)。 使用 op: alife_gray_scott, alife_turing, alife_lenia, alife_dla, alife_sandpile, alife_wolfram1d。データ: 乱数ノイズ / 1 点から成長 (シミュレーション)。

### 空間がぐにゃり — 3 つの変形アルゴリズム

![空間がぐにゃり — 3 つの変形アルゴリズム](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_wobble_warp_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_wobble_warp.png )

画像の下に見えないゴムのシートがあると思って、数学の異なる 3 つの流儀でつまんで引っぱった結果。 使用 op: deform_tps, deform_ffd, deform_mls。データ: skimage.data camera (実写真)。

### 樹枝状結晶とその骨格

![樹枝状結晶とその骨格](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dla_skeleton_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dla_skeleton.png )

粒子がふらふら漂って張り付くだけで雪の結晶のような枝が育つ (DLA)。スケルトン化するとその「骨」が 1 ピクセル幅で取り出せる。※シミュレーション画像 (実写ではない)。 使用 op: alife_dla, dilation_circle, sk_skeleton, distance_transform。データ: 乱数から DLA 成長 (シミュレーション)。
