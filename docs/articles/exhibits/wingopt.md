<!-- tools/gen_wingopt_gallery.py が自動生成。記事本体 (docs/articles/*.md) には手を触れていません。 -->

# 光学設計・検査ウィング —— キャプション原稿

再生成: `py -3.11 tools/gen_wingopt_gallery.py`(展示単位なら `--exhibits <name,...>`)。
図に焼かれた数字はすべて `optics` / `visiondesign` / `defectgen` / `visionlab` を実際に呼んだ実測値で、決定的です(`--verify` で SHA-256 一致を確認できます)。

## 欠陥ジェネレータの見本帳

[![欠陥ジェネレータの見本帳](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingopt_defect_atlas_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingopt_defect_atlas.png)

*↑ **欠陥ジェネレータの見本帳** ―― 欠陥 5 種(scratch / pits / crack / blob / composite)を同じ系(**16.264 µm/画素**)で撮り、左列が撮れる画像、右列が**画素完全な正解マスク**です。マスクは撮像前の幾何から作るので、撮像でぼけても正解は動かず、**注釈作業が存在しません** —— 各行のマスク面積は実測で 873 / 217 / 692 / 347 / 2243 画素、光学限界は 32.53 µm(sampling 律速)です。 使用 op: `defect_scratch`, `defect_pits`, `defect_crack`, `defect_blob`, `surface_texture`, `composite_defect`, `defect_stats`, `image_formation`。*

<small>クリックで原寸 (554×1562 px / 142 kB)。</small>

---

## 生成物一覧(実測)

| 展示 | 形式 | 画素 | フレーム | サイズ | SHA-256(先頭 16) |
|---|---|---|---|---|---|
| 欠陥ジェネレータの見本帳 | PNG | 554×1562 | 1 | 142 kB | `139bdb29647d2a13` |
