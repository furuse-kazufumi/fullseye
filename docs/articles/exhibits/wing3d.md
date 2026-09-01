# 3D 計測ウィング ―― 紙面の科学館

本ファイルは `tools/gen_wing3d_gallery.py` が **実行結果から自動生成**しています(手で数値を書き換えないでください)。
図に焼き込んだ数字はすべてその場の計算結果で、素材は合成データのみです(実データ・AI 生成素材は使っていません)。

生成: seed `20260902` 固定 / `py -3.11 tools/gen_wing3d_gallery.py`

---

### 3D 計測ウィング ―― ボクセルと点群を「測る」ための op

[![run-length で 1/71](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing3d_rle_compression_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing3d_rle_compression.png)

*↑ **run-length で 1/71** ―― 256³ の合成部品を run-length で持つと **1/71**(16.78 MB → 0.237 MB、19,764 run)。しかも展開せずに体積 1,610,948 voxel を **241 倍速**、BBox を **24 倍速**で返し、集合演算(球 ∪ 軸 = 1,508,456 voxel)も run のまま解ける。decode の往復は bit 一致。 使用 op: `vol_rle_encode`, `vol_rle_decode`, `vol_rle_volume`, `vol_rle_bbox`, `vol_rle_centroid`, `vol_rle_union`, `vol_rle_intersect`, `vol_rle_difference`。*

![斜めに切ると円が楕円になる(長径は 1/cos で伸びる)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wing3d_oblique_slice.gif)

*↑ **斜めに切ると円が楕円になる(長径は 1/cos で伸びる)** ―― 半径 5.00 mm の合成円柱を、切断面を 0° から 80° まで倒しながら切る(`vol_rotate` の逆回し)。短径は角度によらず 10.000 mm のままなのに、長径は **2r / cos θ** に沿って伸び、80° では 29.238 mm = 2.92 倍になる。36 角度(0°〜70°)すべてで理論値との差は最大 0.0000 mm(0.00 画素)。「斜めの断面で測った直径」をそのまま寸法にしてはいけない、という一本。 使用 op: `vol_rotate`。*

---

## 生成物の実測(読み戻して確認した値)

| 展示 | 形式 | ファイル | 実測 |
|---|---|---|---|
| rle | PNG | `wing3d_rle_compression.png` | 1120x720, 52 kB |
| oblique | GIF+mp4 | `media/wing3d_oblique_slice.gif` | 36 フレーム, 1120x640, 0.90 MB, 256 色, mp4 0.11 MB |
