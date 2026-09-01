<!-- tools/gen_wingopt_gallery.py が自動生成。記事本体 (docs/articles/*.md) には手を触れていません。 -->

# 光学設計・検査ウィング —— キャプション原稿

再生成: `py -3.11 tools/gen_wingopt_gallery.py`(展示単位なら `--exhibits <name,...>`)。
図に焼かれた数字はすべて `optics` / `visiondesign` / `defectgen` / `visionlab` を実際に呼んだ実測値で、決定的です(`--verify` で SHA-256 一致を確認できます)。

## 検出限界マップ

[![検出限界マップ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingopt_detect_map_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingopt_detect_map.png)

*↑ **検出限界マップ** ―― 欠陥サイズ(横・対数)とコントラスト(縦)の平面で検出率を測ると、**光学限界 32.53 µm(sampling 律速)は縦の直線として動かず**、実際の検出境界(白線 = 実測 50 % 等高線)はその右に寝ています。コントラスト 0.03 では 231 µm(限界の 7.10 倍)必要なのに、0.40 まで上げると 33 µm(1.00 倍)で足ります —— **右側はレンズの問題ではありません**。 使用 op: `render_part`, `system_geometry`, `resolving_power`, `draw_polyline`, `draw_line`。*

<small>クリックで原寸 (1028×488 px / 40 kB)。</small>

## 照明を変えると何が見えるか

![照明を変えると何が見えるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_illumination.gif)

*↑ **照明を変えると何が見えるか** ―― 同じ幾何の 120 µm の傷を、明視野風(明るい面に暗い傷)と暗視野風(暗い場に光る傷)で並べ、コントラストを掃きます。50 % 検出に届くのは明視野風が |contrast| **0.050**、暗視野風が **0.020** で、光学限界 32.53 µm は両方とも余裕で超えています —— **差はレンズではなく見せ方**です(これは `defectgen` の appearance モデル = 符号と露光であって、リング照明の光輸送計算ではありません)。 使用 op: `render_part`, `defect_scratch`, `image_formation`, `draw_polyline`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_illumination_thumb.jpg`)。33 フレーム / 10 fps / 1000×502 px / 0.34 MB。</small>

---

## 生成物一覧(実測)

| 展示 | 形式 | 画素 | フレーム | サイズ | SHA-256(先頭 16) |
|---|---|---|---|---|---|
| 検出限界マップ | PNG | 1028×488 | 1 | 40 kB | `dbf3d8317f993d48` |
| 照明を変えると何が見えるか | GIF | 1000×502 | 33 | 342 kB | `5844be54809c2f3f` |
