<!-- tools/gen_wingopt_gallery.py が自動生成。記事本体 (docs/articles/*.md) には手を触れていません。 -->

# 光学設計・検査ウィング —— キャプション原稿

再生成: `py -3.11 tools/gen_wingopt_gallery.py`(展示単位なら `--exhibits <name,...>`)。
図に焼かれた数字はすべて `optics` / `visiondesign` / `defectgen` / `visionlab` を実際に呼んだ実測値で、決定的です(`--verify` で SHA-256 一致を確認できます)。

## 設計から判定までの一本道

![設計から判定までの一本道](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_pipeline_flow.gif)

*↑ **設計から判定までの一本道** ―― 「設計 → 限界 → 仮想の部品 → 撮像 → 検査 → 判定」の 6 工程を、1 コマずつ止めて読めるコマ送りにしました。系が決まると **16.264 µm/画素**が確定し、そこから光学限界 **32.53 µm**(sampling 律速)が出て、120 µm の傷は 7.38 画素になり、最後に IoU **0.3790** で 検出と判定される —— **正解マスクは撮像でぼけても動かない**ので、この採点が成立します(判定は `marginal`)。 使用 op: `system_geometry`, `resolving_power`, `system_feasibility`, `surface_texture`, `defect_scratch`, `composite_defect`, `defect_stats`, `image_formation`, `draw_polyline`, `draw_circle`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_pipeline_flow_thumb.jpg`)。6 フレーム / 700 ms/コマ / 940×514 px / 0.20 MB。</small>

## 欠陥ジェネレータの見本帳

[![欠陥ジェネレータの見本帳](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingopt_defect_atlas_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingopt_defect_atlas.png)

*↑ **欠陥ジェネレータの見本帳** ―― 欠陥 5 種(scratch / pits / crack / blob / composite)を同じ系(**16.264 µm/画素**)で撮り、左列が撮れる画像、右列が**画素完全な正解マスク**です。マスクは撮像前の幾何から作るので、撮像でぼけても正解は動かず、**注釈作業が存在しません** —— 各行のマスク面積は実測で 682 / 949 / 441 / 2318 / 1749 画素、光学限界は 32.53 µm(sampling 律速)です。 使用 op: `defect_scratch`, `defect_pits`, `defect_crack`, `defect_blob`, `surface_texture`, `composite_defect`, `defect_stats`, `image_formation`。*

<small>クリックで原寸 (998×882 px / 146 kB)。</small>

---

## 生成物一覧(実測)

| 展示 | 形式 | 画素 | フレーム | サイズ | SHA-256(先頭 16) |
|---|---|---|---|---|---|
| 設計から判定までの一本道 | GIF | 940×514 | 6 | 198 kB | `0cc45944f44d336f` |
| 欠陥ジェネレータの見本帳 | PNG | 998×882 | 1 | 146 kB | `c732c5100726f75c` |
