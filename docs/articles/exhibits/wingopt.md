<!-- tools/gen_wingopt_gallery.py が自動生成。記事本体 (docs/articles/*.md) には手を触れていません。 -->

# 光学設計・検査ウィング —— キャプション原稿

再生成: `py -3.11 tools/gen_wingopt_gallery.py`(展示単位なら `--exhibits <name,...>`)。
図に焼かれた数字はすべて `optics` / `visiondesign` / `defectgen` / `visionlab` を実際に呼んだ実測値で、決定的です(`--verify` で SHA-256 一致を確認できます)。

## cos⁴ 則の周辺光量落ち

![cos⁴ 則の周辺光量落ち](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_cos4_falloff.gif)

*↑ **cos⁴ 則の周辺光量落ち** ―― 焦点距離を 42 → 8 mm と短くすると半画角が 5.91° → 33.45° へ広がり、視野の角の明るさが **0.9789 → 0.4846**(中心比)まで落ちます。右の曲線は `relative_illumination` の出力そのもので、左のマップは同じ cos⁴ をセンサ座標で評価したもの —— **独立な 2 経路の角の値が最大でも 0.0e+00 しか違いません**(片方が壊れたら気付ける作りにしてあります)。 使用 op: `relative_illumination`, `thin_lens`, `system_feasibility`, `draw_polyline`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_cos4_falloff_thumb.jpg`)。36 フレーム / 10 fps / 1000×468 px / 1.64 MB。</small>

## 回折限界の MTF

![回折限界の MTF](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_mtf.gif)

*↑ **回折限界の MTF** ―― F 値を f/1.4 から f/22.0 まで絞ると、カットオフ周波数 1/(λN) が **1299 → 83 cyc/mm** へ下がります。左のバーは飾りではなく、**右の曲線から読んだコントラストをそのまま振幅にして描いた**もので、200 cyc/mm のバーは f/1.4 では 0.805 だったのが f/22.0 では 0.000 —— 完全に消えます。 使用 op: `mtf_diffraction`, `draw_polyline`, `draw_markers`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_mtf_thumb.jpg`)。34 フレーム / 10 fps / 1000×520 px / 0.77 MB。</small>

## 被写界深度と錯乱円

![被写界深度と錯乱円](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_dof_coc.gif)

*↑ **被写界深度と錯乱円** ―― 被写界深度は**レンズの性質ではなく、許容錯乱円という「こちらの決め事」**です。錯乱円を 1 画素から 10 画素へ広げると深度は **0.7435 mm → 7.4377 mm**(比 10.0034)と、ほぼ厳密に比例して伸びます。記事のライトフィールドの利得表(6×6 で 6.0016 倍)は**この直線を 2 回読んだだけ**で、要求公差 1 mm が収まるのは錯乱円 1.345 画素からです。 使用 op: `depth_of_field`, `draw_polyline`, `draw_line`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_dof_coc_thumb.jpg`)。37 フレーム / 10 fps / 1000×516 px / 0.43 MB。</small>

## 横分解能 対 被写界深度

![横分解能 対 被写界深度](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingopt_res_vs_dof.gif)

*↑ **横分解能 対 被写界深度** ―― 横分解能と被写界深度は**独立な 2 軸**です。60 µm の欠陥が解像できるのは **f/7.82 まで**、部品の1 mm 公差が収まるのは **f/5.38 から** —— 使える窓は **f/5.38 〜 f/7.82** の帯だけです。これを 1 つの `resolvable` に畳むと「光学限界に未到達」と出てしまい、**読んだ人はレンズを買いに行きます**(直すべきは絞りか公差かフォーカス機構)。 使用 op: `resolving_power`, `depth_of_field`, `system_geometry`, `draw_polyline`。*

<small>静止フレームでも読めます(静止サムネ: `https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/wingopt_res_vs_dof_thumb.jpg`)。43 フレーム / 10 fps / 1000×498 px / 0.33 MB。</small>

---

## 生成物一覧(実測)

| 展示 | 形式 | 画素 | フレーム | サイズ | SHA-256(先頭 16) |
|---|---|---|---|---|---|
| cos⁴ 則の周辺光量落ち | GIF | 1000×468 | 36 | 1641 kB | `9fb7255a6f624b3f` |
| 回折限界の MTF | GIF | 1000×520 | 34 | 773 kB | `42b1aaa19184dbd0` |
| 被写界深度と錯乱円 | GIF | 1000×516 | 37 | 428 kB | `e2c935899e737d3c` |
| 横分解能 対 被写界深度 | GIF | 1000×498 | 43 | 328 kB | `4c230e35bf63a22f` |
