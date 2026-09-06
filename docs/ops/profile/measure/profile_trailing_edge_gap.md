---
op: profile_trailing_edge_gap
dim: profile
category: measure
in: pairs
out: measurement
examples: [profile_shape_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# profile_trailing_edge_gap — PROFILE `measure` op

- **データ種**: `pairs` → `measurement`
- **呼び出し**: `import profileops; profileops.profile_trailing_edge_gap(contour, n=201)` (または `opsprofile.get("profile_trailing_edge_gap")`)

## 使い方

後縁の開き(翼弦比)。上面と下面の後縁端の距離。

NACA 4 桁の既定係数(-0.1015)は後縁を**わずかに開く**ので、0 にならないのが
正しい。閉じる係数(-0.1036)なら 0 に近づく。

手順: ``profile_sides(contour, n)``(弦長 1 に正規化し、弦を ``n`` 等分した各
位置で上面・下面を線形補間)を取り、**``x = 1`` 側から見て上下両方が取れた
最初の位置**の ``upper - lower`` を返す。単位は弦長比(無次元)。

- ``contour``: ``(N, 2)`` の **(x, y)**、8 点以上、有限、**閉じた断面**であること
  (端点間の隙間が全体の 20 % を超えると「閉じていない」として ``ValueError``)。
- ``n``: 弦の分割数、5 以上(既定 201)。**粗いと後縁から手前の位置で測る**ことに
  なり、テーパした後縁では実際の隙間より大きく出る。細かいほど後縁に寄る。
- 返り値: float(弦長比)。実測(``n=201``): ``profile_synth_naca4("2412")`` で
  0.0039、``closed_te=True`` でも 0.0015 ―― 閉じた後縁でも 0 にならないのは、
  上下両方が取れる最後の位置が後縁のわずかに手前で、そこにはまだ厚みが
  あるため。符号は上面の ``y`` が下面より大きい限り正。
- 失敗: ``ValueError``(形、閉じていない、上下が取れる位置が 1 つも無い、
  上下面が一致して厚み 0)。

``profile_thickness`` の末尾の値と同じ量を「後縁の 1 点だけ」で返すもの。
``profile_synth_naca4(closed_te=True)`` で作った真値と比べれば検算になる。

## 詳しい使い方ガイド

- [profile_metrology ファミリ ガイド](../guides/profile_metrology.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [profile_shape_inspection](../../../../examples/profile_shape_inspection.py) — `py -3.11 examples/profile_shape_inspection.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`measure`)

[profile_sides](profile_sides.md) · [profile_thickness](profile_thickness.md) · [profile_camber](profile_camber.md) · [profile_leading_edge_radius](profile_leading_edge_radius.md)

---
*Provenance: profileops.py — PROFILE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
