---
op: vol_label_palette
dim: volcolor
category: palette
in: 
out: matrix
examples: [voxel_labels_color]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# vol_label_palette — VOLCOLOR `palette` op

- **データ種**: `なし` → `matrix`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import volcolor; volcolor.vol_label_palette(n_labels, seed: 'int' = 0, background=(0.0, 0.0, 0.0))` (または `opsvolcolor.get("vol_label_palette")`)

## 使い方

ラベル ``0..n_labels`` の RGB パレット ``(n_labels + 1, 3)`` float64。

:func:`imgio.colorize_labels` と**同じ乱数列**である ――
``np.random.default_rng(seed).random((n + 1, 3))`` の行 ``k`` がラベル ``k`` の
色、行 0 は *background*(既定は黒 = 2-D 側と同一)。PCG64 の標本列は逐次
生成なので ``n`` を増やしても先頭行は変わらず、**同じラベル番号・同じ seed なら
2-D の 1 枚でも 3-D のボリュームでも色が一致する**。この一致は
``tests/test_volcolor.py`` が ``np.array_equal`` で固定している。

実測(seed=0、RGB ユークリッド距離、取りうる最大は sqrt(3)=1.732):最近接の
色対の距離は 16 色で 0.1439、64 色で 0.0385、256 色で 0.0274。**色は識別子では
なく目印**であり、区別が要る図には :func:`vol_label_legend` の表を添える。

Raises ``ValueError`` for a negative / non-integer *n_labels*, an *n_labels*
over :data:`MAX_LABELS`, a negative *seed*, or a *background* outside [0, 1].

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [voxel_labels_color](../../../../examples/voxel_labels_color.py) — `py -3.11 examples/voxel_labels_color.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

—

## 同カテゴリ(`palette`)

—

---
*Provenance: volcolor.py — VOLCOLOR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
