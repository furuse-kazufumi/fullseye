<!-- tools/gen_wingopt_gallery.py が自動生成。記事本体 (docs/articles/*.md) には手を触れていません。 -->

# 光学設計・検査ウィング —— キャプション原稿

再生成: `py -3.11 tools/gen_wingopt_gallery.py`(展示単位なら `--exhibits <name,...>`)。
図に焼かれた数字はすべて `optics` / `visiondesign` / `defectgen` / `visionlab` を実際に呼んだ実測値で、決定的です(`--verify` で SHA-256 一致を確認できます)。

## 律速の入れ替わり

![律速の入れ替わり](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_limit_crossover.gif)

*↑ **律速の入れ替わり** ―― 作動距離を 120 → 320 mm と掃くと、**回折律速と標本化律速が入れ替わります**。閉形式で解いた交点は **WD 157.64 mm**、そこでは 2 本の限界がどちらも **24.18 µm** で一致します(倍率 0.28539)。記事本文の 44 段掃引が入れ替わりを最初に報告するのは 160.5 mm —— その差は物理ではなく**格子の粗さ**です。 使用 op: `system_geometry`, `resolving_power`, `thin_lens`, `draw_polyline`, `draw_line`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_limit_crossover_thumb.jpg`)。42 フレーム / 10 fps / 1000×474 px / 0.46 MB。</small>

---

## 生成物一覧(実測)

| 展示 | 形式 | 画素 | フレーム | サイズ | SHA-256(先頭 16) |
|---|---|---|---|---|---|
| 律速の入れ替わり | GIF | 1000×474 | 42 | 459 kB | `353cbabaa24686ab` |
