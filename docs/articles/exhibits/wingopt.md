<!-- tools/gen_wingopt_gallery.py が自動生成。記事本体 (docs/articles/*.md) には手を触れていません。 -->

# 光学設計・検査ウィング —— キャプション原稿

再生成: `py -3.11 tools/gen_wingopt_gallery.py`(展示単位なら `--exhibits <name,...>`)。
図に焼かれた数字はすべて `optics` / `visiondesign` / `defectgen` / `visionlab` を実際に呼んだ実測値で、決定的です(`--verify` で SHA-256 一致を確認できます)。

## 検出限界マップ

[![検出限界マップ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingopt_detect_map_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingopt_detect_map.png)

*↑ **検出限界マップ** ―― 欠陥サイズ(横・対数)とコントラスト(縦)の平面で検出率を測ると、**光学限界 32.53 µm(sampling 律速)は縦の直線として動かず**、実際の検出境界(白線 = 実測 50 % 等高線)はその右に寝ています。コントラスト 0.06 では 53 µm(限界の 1.64 倍)必要なのに、0.40 まで上げると 28 µm(0.85 倍)で足ります —— **右側はレンズの問題ではありません**。 使用 op: `render_part`, `system_geometry`, `resolving_power`, `draw_polyline`, `draw_line`。*

<small>クリックで原寸 (1028×488 px / 40 kB)。</small>

## 画素ピッチとサンプリング

![画素ピッチとサンプリング](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_pixel_pitch.gif)

*↑ **画素ピッチとサンプリング** ―― 130 µm の傷を固定して画素ピッチだけを粗くすると、欠陥が **2 画素を割るのはピッチ 13.79 µm** (Nyquist の境界)で、実測の 50 % 検出が保つのはピッチ **15.02 µm** までです。拡大は最近傍なので**見えている四角は本物の画素**で、滑らかに見せるための補間は入れていません。 使用 op: `render_part`, `system_geometry`, `resolving_power`, `draw_polyline`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_pixel_pitch_thumb.jpg`)。40 フレーム / 10 fps / 1000×502 px / 0.58 MB。</small>

---

## 生成物一覧(実測)

| 展示 | 形式 | 画素 | フレーム | サイズ | SHA-256(先頭 16) |
|---|---|---|---|---|---|
| 検出限界マップ | PNG | 1028×488 | 1 | 40 kB | `81b870b0b2bbbd90` |
| 画素ピッチとサンプリング | GIF | 1000×502 | 40 | 577 kB | `54e2158fdb88a94a` |
