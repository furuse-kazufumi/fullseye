# 3D 計測ウィング ―― 紙面の科学館

本ファイルは `tools/gen_wing3d_gallery.py` が **実行結果から自動生成**しています(手で数値を書き換えないでください)。
図に焼き込んだ数字はすべてその場の計算結果で、素材は合成データのみです(実データ・AI 生成素材は使っていません)。

生成: seed `20260902` 固定 / `py -3.11 tools/gen_wing3d_gallery.py`

---

### 3D 計測ウィング ―― ボクセルと点群を「測る」ための op

[![run-length で 1/71](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing3d_rle_compression_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing3d_rle_compression.png)

*↑ **run-length で 1/71** ―― 256³ の合成部品を run-length で持つと **1/71**(16.78 MB → 0.237 MB、19,764 run)。しかも展開せずに体積 1,610,948 voxel を **241 倍速**、BBox を **24 倍速**で返し、集合演算(球 ∪ 軸 = 1,508,456 voxel)も run のまま解ける。decode の往復は bit 一致。 使用 op: `vol_rle_encode`, `vol_rle_decode`, `vol_rle_volume`, `vol_rle_bbox`, `vol_rle_centroid`, `vol_rle_union`, `vol_rle_intersect`, `vol_rle_difference`。*

![断層を送る ―― `z = 48 / 95` は 38.40 mm のこと](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing3d_slice_zsweep.gif)

*↑ **断層を送る ―― `z = 48 / 95` は 38.40 mm のこと** ―― 合成 CT(96×128×128、spacing (0.8, 0.3, 0.3) mm)を 1 スライスずつ 96 コマ送る。各コマに**添字と物理位置の両方**(`z = 48 / 95` = 38.40 mm)と位置バーを焼いた。1 スライス送りは 0.80 mm、面内 1 画素は 0.30 mm = **0.37 倍**なので、下の折れ線のとおり「添字を 1 つ動かす」は軸ごとに違う距離を意味する ―― 異方性 CT でいちばん踏みやすい段差。 使用 op: `vol_window_level`。*

![3 直交断面(MPR)とクロスヘア](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing3d_mpr_crosshair.gif)

*↑ **3 直交断面(MPR)とクロスヘア** ―― 同じ 1 点を 3 方向から見る MPR。axial(`vol[z]`)・coronal(`vol[:, y, :]`)・sagittal(`vol[:, :, x]`)を横に並べ、らせん状の目印を追いながら 3 本のクロスヘアを同時に動かした。各パネルに**どの軸が横でどの軸が縦か**を書き、`+x` に球・`-y` に横棒・`+z` にリングという非対称なランドマークを入れてある ―― 軸の入れ替わりや左右反転が起きたら、この 3 つの位置がずれて必ず露見する。 使用 op: `(numpy スライス + imagedraw)`。*

![斜めに切ると円が楕円になる(長径は 1/cos で伸びる)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing3d_oblique_slice.gif)

*↑ **斜めに切ると円が楕円になる(長径は 1/cos で伸びる)** ―― 半径 5.00 mm の合成円柱を、切断面を 0° から 80° まで倒しながら切る(`vol_rotate` の逆回し)。短径は角度によらず 10.000 mm のままなのに、長径は **2r / cos θ** に沿って伸び、80° では 29.238 mm = 2.92 倍になる。36 角度(0°〜70°)すべてで理論値との差は最大 0.0000 mm(0.00 画素)。「斜めの断面で測った直径」をそのまま寸法にしてはいけない、という一本。 使用 op: `vol_rotate`。*

---

## 生成物の実測(読み戻して確認した値)

| 展示 | 形式 | ファイル | 実測 |
|---|---|---|---|
| rle | PNG | `wing3d_rle_compression.png` | 1120x720, 52 kB |
| zsweep | GIF+mp4 | `media/wing3d_slice_zsweep.gif` | 96 フレーム, 1120x660, 1.15 MB, 256 色, mp4 0.15 MB |
| mpr | GIF+mp4 | `media/wing3d_mpr_crosshair.gif` | 60 フレーム, 1120x620, 1.18 MB, 256 色, mp4 0.22 MB |
| oblique | GIF+mp4 | `media/wing3d_oblique_slice.gif` | 36 フレーム, 1120x640, 0.90 MB, 256 色, mp4 0.11 MB |
