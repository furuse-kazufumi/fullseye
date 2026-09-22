---
op: volseq_pathline_render
dim: live4d
category: flow
in: volseq
out: rgb
examples: [poc_live4d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# volseq_pathline_render — LIVE4D `flow` op

- **データ種**: `volseq` → `rgb`
- **呼び出し**: `import fullseye as fs; fs.ledger.volseq_pathline_render(volseq, n_seeds: 'int' = 200, yaw: 'float' = 35.0, pitch: 'float' = 25.0, size: 'int' = 256, static_alpha: 'float' = 0.03, win: 'int' = 3, pyr_levels: 'int' = 3, iters: 'int' = 5, reg: 'float' = 0.001, seed: 'int' = 0, trail_sigma: 'float' = 0.7, min_speed: 'float' = 0.1, min_intensity: 'float' = 0.3) -> 'np.ndarray'` (実装を直接呼ぶなら `import live4d; live4d.volseq_pathline_render(volseq, n_seeds: 'int' = 200, yaw: 'float' = 35.0, pitch: 'float' = 25.0, size: 'int' = 256, static_alpha: 'float' = 0.03, win: 'int' = 3, pyr_levels: 'int' = 3, iters: 'int' = 5, reg: 'float' = 0.001, seed: 'int' = 0, trail_sigma: 'float' = 0.7, min_speed: 'float' = 0.1, min_intensity: 'float' = 0.3) -> 'np.ndarray'`、台帳から引くなら `opslive4d.get("volseq_pathline_render")`)

## 使い方

粒子を流れに乗せて描いた**軌跡の立体** ``(size, size, 3)``(``rgb``)—— 動きを 1 枚の静止画で見せる。

隣り合うフレームの変位場(``vol_flow_3d``)で、動いていて(速さ >= ``min_speed``)かつ明るい(最初の
フレームの値域の ``min_intensity`` 以上 = 構造のある)場所から撒いた ``n_seeds`` 個の粒子を変位場の写像どおりに移流し、
軌跡を**時刻の色**(青 = 始め → 赤 = 終わり)で立方体に描いて ``vol_render_transfer`` で任意視点から
合成する。``static_alpha`` > 0 なら最初のフレームの明るさを薄い灰で重ねる(どこを流れたかの手掛かり)。
``trail_sigma`` は軌跡の太さ(voxel)。テクスチャの無い場所の流れは決まらない(開口問題)ので、
種を明るい場所に限る —— 速さだけで選ぶと真っ暗な隅にも種が落ちて立方体が軌跡で埋まる(実測)。

## 詳しい使い方ガイド

- [live4d ファミリ ガイド](../guides/live4d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_live4d](../../../../examples/poc_live4d.py) — `py -3.11 examples/poc_live4d.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

—

## 同カテゴリ(`flow`)

[vol_flow_3d](vol_flow_3d.md) · [volseq_speed](volseq_speed.md) · [volseq_pathline_orbit](volseq_pathline_orbit.md)

---
*Provenance: live4d.py — LIVE4D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
