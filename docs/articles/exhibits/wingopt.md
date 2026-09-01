<!-- tools/gen_wingopt_gallery.py が自動生成。記事本体 (docs/articles/*.md) には手を触れていません。 -->

# 光学設計・検査ウィング —— キャプション原稿

再生成: `py -3.11 tools/gen_wingopt_gallery.py`(展示単位なら `--exhibits <name,...>`)。
図に焼かれた数字はすべて `optics` / `visiondesign` / `defectgen` / `visionlab` を実際に呼んだ実測値で、決定的です(`--verify` で SHA-256 一致を確認できます)。

## 横分解能 対 被写界深度

![横分解能 対 被写界深度](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_res_vs_dof.gif)

*↑ **横分解能 対 被写界深度** ―― 横分解能と被写界深度は**独立な 2 軸**です。60 µm の欠陥が解像できるのは **f/7.82 まで**、部品の1 mm 公差が収まるのは **f/5.38 から** —— 使える窓は **f/5.38 〜 f/7.82** の帯だけです。これを 1 つの `resolvable` に畳むと「光学限界に未到達」と出てしまい、**読んだ人はレンズを買いに行きます**(直すべきは絞りか公差かフォーカス機構)。 使用 op: `resolving_power`, `depth_of_field`, `system_geometry`, `draw_polyline`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_res_vs_dof_thumb.jpg`)。43 フレーム / 10 fps / 1000×548 px / 0.33 MB。</small>

---

## 生成物一覧(実測)

| 展示 | 形式 | 画素 | フレーム | サイズ | SHA-256(先頭 16) |
|---|---|---|---|---|---|
| 横分解能 対 被写界深度 | GIF | 1000×548 | 43 | 327 kB | `b89bed20b13b8978` |
