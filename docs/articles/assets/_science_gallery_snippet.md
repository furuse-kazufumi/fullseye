<!-- gen_science_gallery.py が自動生成。GALLERY.md / 記事 md への
     追記候補 (このファイル自体は記事ではない)。 -->

# 科学ギャラリー追加分 — GALLERY.md 追記行 + 記事挿入候補

## GALLERY.md 追記行

| 距離変換の虹の波紋 | ![距離変換の虹の波紋](assets/science_distance_ripple_thumb.jpg) | otsu, fill_up, distance_transform | skimage.data coins (実写真) |
| フーリエの世界 — 画像を周波数で見る | ![フーリエの世界 — 画像を周波数で見る](assets/science_fourier_stars_thumb.jpg) | fft_image | skimage.data camera (実写真) + fullseye synth 織り目 (合成) |
| エッジの方位磁針 | ![エッジの方位磁針](assets/science_edge_compass_thumb.jpg) | sobel_amp, sobel_dir | skimage.data camera (実写真) |
| watershed — コインのなわばり地図 | ![watershed — コインのなわばり地図](assets/science_watershed_foam_thumb.jpg) | otsu, fill_up, distance_transform, watersheds, segment_objects, colorize_labels | skimage.data coins (実写真) |

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

### watershed — コインのなわばり地図

![watershed — コインのなわばり地図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_watershed_foam_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_watershed_foam.png )

水が低いところへ流れて溜まるように領域を分ける watershed 法。どのコインに一番近いかで平面が泡のように分割される。 使用 op: otsu, fill_up, distance_transform, watersheds, segment_objects, colorize_labels。データ: skimage.data coins (実写真)。
