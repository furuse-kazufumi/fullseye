<!-- tools/gen_wingopt_gallery.py が自動生成。記事本体 (docs/articles/*.md) には手を触れていません。 -->

# 光学設計・検査ウィング —— キャプション原稿

再生成: `py -3.11 tools/gen_wingopt_gallery.py`(展示単位なら `--exhibits <name,...>`)。
図に焼かれた数字はすべて `optics` / `visiondesign` / `defectgen` / `visionlab` を実際に呼んだ実測値で、決定的です(`--verify` で SHA-256 一致を確認できます)。

## 画素ピッチとサンプリング

![画素ピッチとサンプリング](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_pixel_pitch.gif)

*↑ **画素ピッチとサンプリング** ―― 130 µm の傷を固定して画素ピッチだけを粗くすると、欠陥が **2 画素を割るのはピッチ 13.79 µm** (Nyquist の境界)で、実測の 50 % 検出が保つのはピッチ **13.32 µm** までです。拡大は最近傍なので**見えている四角は本物の画素**で、滑らかに見せるための補間は入れていません。 使用 op: `render_part`, `system_geometry`, `resolving_power`, `draw_polyline`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_pixel_pitch_thumb.jpg`)。40 フレーム / 10 fps / 1000×502 px / 0.70 MB。</small>

---

## 生成物一覧(実測)

| 展示 | 形式 | 画素 | フレーム | サイズ | SHA-256(先頭 16) |
|---|---|---|---|---|---|
| 画素ピッチとサンプリング | GIF | 1000×502 | 40 | 702 kB | `3e2f3fc929289acc` |
