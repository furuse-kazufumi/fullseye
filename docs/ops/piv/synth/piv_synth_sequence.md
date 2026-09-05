---
op: piv_synth_sequence
dim: piv
category: synth
in: 
out: images
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# piv_synth_sequence — PIV `synth` op

- **データ種**: `なし` → `images`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import pivops; pivops.piv_synth_sequence(shape, displacement, n_frames=8, density=0.02, diameter_px=2.5, seed=0, noise_sigma=0.0, intensity=(0.6, 1.0), background=0.0, jitter=0.0)` (または `opspiv.get("piv_synth_sequence")`)

## 使い方

同じ粒子を繰り返し動かした画像列。返りは ``(frames, truth)``。

:func:`piv_synth_pair` が 2 枚なのに対し、こちらは **1 つの流れを追い続けた
列**を作る。アンサンブル相関と時間統計はこれでないと確かめられない ——
独立な対を並べたものを列と呼ぶと、隣り合う 2 枚に対応関係が無く、
統計が無意味になる(実測: 平均 0.73 px に対して変動の RMS が 4.05 px という、
流れではなく作り方を測った数字が出た)。

Args:
    shape: ``(H, W)``。
    displacement: 1 コマあたりの変位(:func:`piv_synth_pair` と同じ形式)。
    n_frames: コマ数(2 以上)。
    jitter: コマごとに**場全体へ**加える乱れの標準偏差 [px]。0 なら定常流。
        時間統計(変動・レイノルズ応力)を試すにはここを 0 より大きくする。

        ★ 粒子ごとに独立な乱れではなく**コマごとに一つ**の乱れにしてある。
        粒子ごとに振ると、窓の中で平均されて N の平方根ぶん小さくなり、
        仕込んだ値と測った値が合わない(実測: 仕込み 0.3 に対して 0.15)。
        それは PIV の性質であって間違いではないが、**時間統計の検証には
        使えない**ので、ここは非定常な流れそのものを模す形にした。
    density / diameter_px / seed / noise_sigma / intensity / background:
        :func:`piv_synth_pair` と同じ。
Returns:
    ``(frames: list of (H, W), truth: (2, H, W))``。``truth`` は
    **1 コマあたり**の平均変位。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`images` を入力に取れる)

[piv_ensemble_correlate](../estimate/piv_ensemble_correlate.md) · [piv_time_statistics](../assess/piv_time_statistics.md)

## 同カテゴリ(`synth`)

[piv_synth_particles](piv_synth_particles.md) · [piv_synth_pair](piv_synth_pair.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
