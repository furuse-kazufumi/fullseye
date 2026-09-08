---
id: inverted-colour-overlays
title: 地の色を知らずに線と領域を描く(反転色)
title_en: Draw lines and regions without knowing the background colour
category: 見せる
ops: [annotate_invert, annotate_invert_path, annotate_invert_visibility]
examples: [annotate_paper_tour]
version: 0.1.11
---

# 地の色を知らずに線と領域を描く(反転色)

## できること

検査画像に測定線や ROI を重ねるとき、**地が明るいか暗いか分からない**のが普通です。白で描けば白飛びの上で消え、黒で描けば影の上で消えます。反転色は「その場の色をひっくり返して描く」ことでこれを避ける古典手で、`annotate_invert_path` が折れ線(アンチエイリアス・破線可)、`annotate_invert` が領域を、`draw="fill"` で中身ごと、`draw="margin"` で輪郭だけ反転します(HALCON の `set_draw` と同じ語)。

ただし反転色には**たった 1 つの、しかし致命的な弱点**があります —— 中間調では反転しても同じ色になる。`annotate_invert_visibility` は描く前にそれを測り、描く 2 つの op は測ってから警告(あるいは `on_invisible="raise"` で拒否)します。

## What it does

Draw a polyline or a region in the inverse of whatever is underneath, so the overlay stays visible without knowing the background. `draw="margin"` outlines instead of filling. The one real failure mode — mid-grey, where the complement equals the original — is measured rather than assumed: `annotate_invert_visibility` reports the per-pixel WCAG contrast, and the drawing ops warn (or refuse) when the mark would be invisible.

## 向くところ / 向かないところ

**向く**: 明暗が入り混じる検査画像の上の測定線・ROI・当たり判定の可視化。地の統計を取らずに 1 行で重ねられます。

**向かない**: ★**中間調では消えます**。8bit グレーで補色とのコントラスト比が 1.5 を割るのは `v ∈ [113, 142]` の 30/256 階調(全体の 11.7 %)で、`v=128` では比 **1.014** —— 比 1.0 が「同じ色」なので実質不可視です。明→暗の傾斜の上に線を引くと、消える列は `x = (1-v)(W-1)` の予測どおりに現れます(`annotate_paper_tour` が閉形式と画素で照合)。逃げ道は `mode="contrast"`(画素ごとに白か黒へ倒す)で、**どんな地でもコントラスト比 4.58 以上**が保証されますが、地の模様は失われます。★見え方は「反転色」ではなく**実際に置かれた色**で決まるので、`alpha` を落とすと答えが変わります(黒地に `alpha=0.5` の補色は中間調になりますが、黒の上では十分見えます)。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

img = np.tile(np.linspace(1.0, 0.0, 64), (32, 1))       # 左が明るい傾斜
rep = fs.annotate_invert_visibility(img, np.ones(img.shape, bool))
print('最悪のコントラスト比', round(rep['min_contrast'], 3))   # 中間調で 1 に近づく
safe = fs.annotate_invert_path(img, [(4.0, 16.0), (59.0, 16.0)],
                               width=2.0, mode='contrast')
print('逃げ道で描いた図', np.asarray(safe).shape)
```

## 裏づけ

- op: `annotate_invert` / `annotate_invert_path` / `annotate_invert_visibility`
- 例: [`annotate_paper_tour`](../../examples/annotate_paper_tour.py)(節 6 が崖の位置を閉形式で当てる)
- 試験: `tests/test_annotate_invert.py`(全 256 階調で `mode="contrast"` の 4.58 保証を確認)
