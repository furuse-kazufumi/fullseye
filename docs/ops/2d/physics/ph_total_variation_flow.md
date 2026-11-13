---
op: ph_total_variation_flow
dim: 2d
category: physics
in: image
out: image
gpu: あり(許可リスト)
examples: [find_ops_by_meaning, gallery2d_physics_alife_3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# ph_total_variation_flow — 2D `physics` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "ph_total_variation_flow", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **GPU**: あり(許可リストの機械的 GPU 経路、CuPy)。`device="auto"` は測った大きさ(4,194,304 画素)以上で GPU を選ぶ

![ph_total_variation_flow: input → output](../../_fig/ph_total_variation_flow.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

*出力は viridis 風の疑似カラー(暗い紫 = 小、黄 = 大)。距離・位相・向き・深度のような「量の場」を読むため。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![ph_total_variation_flow: knob a sweep](../../_fig/ph_total_variation_flow.a.jpg)

**つまみ b を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![ph_total_variation_flow: knob b sweep](../../_fig/ph_total_variation_flow.b.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![ph_total_variation_flow: other inputs](../../_fig/ph_total_variation_flow.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

Total-variation (Rudin-Osher-Fatemi) denoising flow (no HALCON operator, "").

Gradient descent of the ROF energy TV(I) + (lam/2)||I - I0||^2:
   I_t = div(grad I / |grad I|) - lam (I - I0).
The TV term (curvature of the level sets) flattens noise while preserving sharp
edges; the fidelity term keeps the result anchored to the noisy input I0 so it
denoises rather than collapsing to a constant. ``a`` sets the step count
(1..80 explicit steps of dt=0.008), ``b`` the fidelity weight lam in [10, 30]
(``b=0`` smooths most, ``b=1`` stays closest to the input).

The steps march towards the ROF minimiser, a fixed point: once the fidelity
has had time to act (lam * steps * dt of a few units, reached by a ~ 0.5 at
b=0) more steps no longer change the answer, so raising ``a`` never turns
a denoiser into a blur. A flat region of perimeter P and area A loses about
(P/A)/lam of its contrast at the fixed point, so small features fade more
than large ones (the usual ROF bias); raise ``b`` for light noise.

Until 2026-11-05 lam was 0.02..0.22: its time constant 1/lam (4.5..50) was far
longer than the whole run (80 * 0.008 = 0.64), so the fidelity did nothing,
the op was a pure TV flow drifting to a constant, and the error against the
clean image grew with ``a`` (noisy square, sigma 0.05: 0.019 at a=0.1, 0.067
at a=1, worse than the noisy input's 0.050; even a clean input lost 0.067).

The curvature term is the mean of the four forward/backward staggerings (forward
gradient + backward divergence and its mirror, per axis), so the flow commutes
with flipping the image. Until 2026-11-05 (adversarial review round 2) only the
forward-gradient / backward-divergence pair was used, and flipping the input
changed the result by up to 0.15.

## 詳しい使い方ガイド

- [gallery2d_physics_alife_3d ファミリ ガイド](../guides/gallery2d_physics_alife_3d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
ph_total_variation_flow 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [find_ops_by_meaning](../../../../examples/find_ops_by_meaning.py) — `py -3.11 examples/find_ops_by_meaning.py`
- [gallery2d_physics_alife_3d](../../../../examples/gallery2d_physics_alife_3d.py) — `py -3.11 examples/gallery2d_physics_alife_3d.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [mean_box_wh](../smoothing/mean_box_wh.md) · [bilateral](../smoothing/bilateral.md) · [kuwahara](../smoothing/kuwahara.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md)

## 同カテゴリ(`physics`)

[ph_perona_malik](ph_perona_malik.md) · [ph_coherence_enhancing_diffusion](ph_coherence_enhancing_diffusion.md) · [ph_reaction_diffusion](ph_reaction_diffusion.md) · [ph_heat_flow](ph_heat_flow.md) · [ph_mean_curvature_motion](ph_mean_curvature_motion.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
