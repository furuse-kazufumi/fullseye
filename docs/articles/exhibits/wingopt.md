<!-- tools/gen_wingopt_gallery.py が自動生成。記事本体 (docs/articles/*.md) には手を触れていません。 -->

# 光学設計・検査ウィング —— キャプション原稿

再生成: `py -3.11 tools/gen_wingopt_gallery.py`(展示単位なら `--exhibits <name,...>`)。
図に焼かれた数字はすべて `optics` / `visiondesign` / `defectgen` / `visionlab` を実際に呼んだ実測値で、決定的です(`--verify` で SHA-256 一致を確認できます)。

## 照明を変えると何が見えるか

![照明を変えると何が見えるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_illumination.gif)

*↑ **照明を変えると何が見えるか** ―― 同じ幾何の 60 µm の傷を、明視野風(明るい面に暗い傷)と暗視野風(暗い場に光る傷)で並べ、コントラストを掃きます。50 % 検出に届くのは明視野風が |contrast| **0.044**、暗視野風が **0.018** で、光学限界 32.53 µm は両方とも余裕で超えています —— **差はレンズではなく見せ方**です(これは `defectgen` の appearance モデル = 符号と露光であって、リング照明の光輸送計算ではありません)。 使用 op: `render_part`, `defect_scratch`, `image_formation`, `draw_polyline`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_illumination_thumb.jpg`)。33 フレーム / 10 fps / 1000×502 px / 0.29 MB。</small>

---

## 生成物一覧(実測)

| 展示 | 形式 | 画素 | フレーム | サイズ | SHA-256(先頭 16) |
|---|---|---|---|---|---|
| 照明を変えると何が見えるか | GIF | 1000×502 | 33 | 295 kB | `4bca22a65a9b2dc7` |
