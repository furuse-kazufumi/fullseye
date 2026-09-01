<!-- tools/gen_wingopt_gallery.py が自動生成。記事本体 (docs/articles/*.md) には手を触れていません。 -->

# 光学設計・検査ウィング —— キャプション原稿

再生成: `py -3.11 tools/gen_wingopt_gallery.py`(展示単位なら `--exhibits <name,...>`)。
図に焼かれた数字はすべて `optics` / `visiondesign` / `defectgen` / `visionlab` を実際に呼んだ実測値で、決定的です(`--verify` で SHA-256 一致を確認できます)。

## 検出限界マップ

[![検出限界マップ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingopt_detect_map_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingopt_detect_map.png)

*↑ **検出限界マップ** ―― 欠陥サイズ(横・対数)とコントラスト(縦)の平面で検出率を測ると、**光学限界 32.53 µm(sampling 律速)は縦の直線として動かず**、実際の検出境界(白線 = 実測 50 % 等高線)はコントラストだけで 53.2 → 27.7 µm と動きます。コントラスト 0.06 では 53 µm(限界の 1.64 倍)必要なのに、0.40 まで上げると 28 µm(0.85 倍)で足ります —— 13 段のうち 4 段は境界が限界より**左**に出ます(ここの検出は IoU ≥ 0.1 の当たり判定であって、2 画素に分かれて見えること = 解像ではありません)。**右側はレンズの問題ではありません**。 使用 op: `render_part`, `system_geometry`, `resolving_power`, `draw_polyline`, `draw_line`。*

<small>クリックで原寸 (1028×488 px / 40 kB)。</small>

---

## 生成物一覧(実測)

| 展示 | 形式 | 画素 | フレーム | サイズ | SHA-256(先頭 16) |
|---|---|---|---|---|---|
| 検出限界マップ | PNG | 1028×488 | 1 | 40 kB | `81b870b0b2bbbd90` |
