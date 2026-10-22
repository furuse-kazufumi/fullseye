---
op: convol_image
dim: 2d
category: nary
in: image × image
out: image
halcon: convol_image
examples: [gallery_nary_image_algebra]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# convol_image — 2D `nary` op

- **データ種**: `image × image` → `image`
- **呼び出し**: 入力 2 枚の op なので `fullseye.apply` では呼べない(あれは 1 画像モデル)。`g = fullseye.FullseyeGraph(); g.add("out", "convol_image", ["$in1", "$in2"], a=0.5, b=0.5); g.run({"$in1": img1, "$in2": img2}, terminal="out")` (`$` 始まりが外から渡す入力)
- **HALCON 相当**: `convol_image`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

第 2 入力をフィルタマスクとして畳み込む。HALCON の ``convol_image`` に相当。★HALCON と同じく**相関**(マスクを書いたまま重ねる)で計算する —— scipy の ``convolve`` はマスクを反転するので、非対称なマスクだと画像が逆向きにずれる。マスクは画像より小さくてよく(形の一致は要らない)、絶対値の総和 + 1e-8 で割って正規化する(総和が 0 のマスクで割り算が爆発しないため。出力は相対 1e-8 だけ小さくなる)。端は ``reflect``。``a``, ``b`` は未使用。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery_nary_image_algebra](../../../../examples/gallery_nary_image_algebra.py) — `py -3.11 examples/gallery_nary_image_algebra.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [mean_box_wh](../smoothing/mean_box_wh.md) · [bilateral](../smoothing/bilateral.md) · [kuwahara](../smoothing/kuwahara.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md)

## 同カテゴリ(`nary`)

[add_image](add_image.md) · [sub_image](sub_image.md) · [mult_image](mult_image.md) · [div_image](div_image.md) · [abs_diff_image](abs_diff_image.md) · [max_image](max_image.md) · [min_image](min_image.md) · [bit_and](bit_and.md)

---
*Provenance: imgops_nary.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
