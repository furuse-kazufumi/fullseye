<!-- tools/gen_wingopt_gallery.py が自動生成。記事本体 (docs/articles/*.md) には手を触れていません。 -->

# 光学設計・検査ウィング —— キャプション原稿

再生成: `py -3.11 tools/gen_wingopt_gallery.py`(展示単位なら `--exhibits <name,...>`)。
図に焼かれた数字はすべて `optics` / `visiondesign` / `defectgen` / `visionlab` を実際に呼んだ実測値で、決定的です(`--verify` で SHA-256 一致を確認できます)。

## 被写界深度と錯乱円

![被写界深度と錯乱円](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_dof_coc.gif)

*↑ **被写界深度と錯乱円** ―― 被写界深度は**レンズの性質ではなく、許容錯乱円という「こちらの決め事」**です。錯乱円を 1 画素から 10 画素へ広げると深度は **0.7435 mm → 7.4377 mm**(比 10.0034)と、ほぼ厳密に比例して伸びます。記事のライトフィールドの利得表(6×6 で 6.0016 倍)は**この直線を 2 回読んだだけ**で、要求公差 1 mm が収まるのは錯乱円 1.345 画素からです。 使用 op: `depth_of_field`, `draw_polyline`, `draw_line`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_dof_coc_thumb.jpg`)。37 フレーム / 10 fps / 1000×496 px / 0.44 MB。</small>

---

## 生成物一覧(実測)

| 展示 | 形式 | 画素 | フレーム | サイズ | SHA-256(先頭 16) |
|---|---|---|---|---|---|
| 被写界深度と錯乱円 | GIF | 1000×496 | 37 | 439 kB | `0f2b9c69b1bb6dc5` |
