---
op: vol_flow_3d
dim: live4d
category: flow
in: voxel × voxel
out: flow_dense
examples: [poc_live4d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# vol_flow_3d — LIVE4D `flow` op

- **データ種**: `voxel × voxel` → `flow_dense`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_flow_3d(vol_a, vol_b, win: 'int' = 3, pyr_levels: 'int' = 3, iters: 'int' = 5, reg: 'float' = 0.001) -> 'np.ndarray'` (実装を直接呼ぶなら `import live4d; live4d.vol_flow_3d(vol_a, vol_b, win: 'int' = 3, pyr_levels: 'int' = 3, iters: 'int' = 5, reg: 'float' = 0.001) -> 'np.ndarray'`、台帳から引くなら `opslive4d.get("vol_flow_3d")`)

## 使い方

2 つの体積の間の密な変位場 ``(3, Z, Y, X)``(``flow_dense``、成分 dz, dy, dx [voxel])。

``vol_b(x) ≈ vol_a(x − d)``、つまり ``vol_a`` の構造が ``+d`` 動いて ``vol_b`` になる(torch 版
``scene_flow_lk`` と同じ約束)。Lucas–Kanade の 3 次元版を numpy + scipy だけで: ``win`` は窓の半幅
(窓は一辺 2·win + 1)、``pyr_levels`` はピラミッド段数(大変位ほど増やす、各段 1/2)、``iters`` は各段の
warp 反復、``reg`` は構造テンソル対角の正則化(平坦部の 0 除算回避。大きいほど平坦部の流れが 0 に寄る)。
テクスチャの無い平坦部では流れは決まらない(開口問題)—— 信じるのは勾配のある場所だけ。

>>> a = volseq_synth_dividing((16, 24, 24), n_frames=4, split_frame=0, speed=1.0)
>>> d = vol_flow_3d(a[1], a[2]); d.shape
(3, 16, 24, 24)

## 詳しい使い方ガイド

- [live4d ファミリ ガイド](../guides/live4d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_live4d](../../../../examples/poc_live4d.py) — `py -3.11 examples/poc_live4d.py`

## 型が繋がる次の op(`flow_dense` を入力に取れる)

—

## 同カテゴリ(`flow`)

[volseq_speed](volseq_speed.md) · [volseq_pathline_render](volseq_pathline_render.md) · [volseq_pathline_orbit](volseq_pathline_orbit.md)

---
*Provenance: live4d.py — LIVE4D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
