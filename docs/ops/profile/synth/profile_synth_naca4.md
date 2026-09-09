---
op: profile_synth_naca4
dim: profile
category: synth
in: 
out: pairs
examples: [profile_frame_tour, profile_shape_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# profile_synth_naca4 — PROFILE `synth` op

- **データ種**: `なし` → `pairs`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.profile_synth_naca4(code='2412', n=161, closed_te=False)` (実装を直接呼ぶなら `import profileops; profileops.profile_synth_naca4(code='2412', n=161, closed_te=False)`、台帳から引くなら `opsprofile.get("profile_synth_naca4")`)

## 使い方

NACA 4 桁翼型を閉形式で生成する。返りは ``(N, 2)`` の一筆書き。

``code`` は 4 桁(例 ``"2412"`` = キャンバー 2 %、位置 40 %、厚み 12 %)。
点は前縁を密にするために余弦分布で置く。

``closed_te`` は後縁を閉じる係数を使うかどうか。**既定は歴史的な係数**
(0.1015)で、後縁がわずかに開く。閉じる版は 0.1036。どちらを使ったかで
後縁付近の計測が変わるので、真値として使うなら固定して書き残すこと。

Returns:
    ``(2*n-1, 2)``。後縁 → 上面 → 前縁 → 下面 → 後縁 の順(Selig 流)。

## 詳しい使い方ガイド

- [profile_metrology ファミリ ガイド](../guides/profile_metrology.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [profile_frame_tour](../../../../examples/profile_frame_tour.py) — `py -3.11 examples/profile_frame_tour.py`
- [profile_shape_inspection](../../../../examples/profile_shape_inspection.py) — `py -3.11 examples/profile_shape_inspection.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[profile_perturb](profile_perturb.md) · [profile_chord_frame](../frame/profile_chord_frame.md) · [profile_normalise](../frame/profile_normalise.md) · [profile_resample](../frame/profile_resample.md) · [profile_sides](../measure/profile_sides.md) · [profile_thickness](../measure/profile_thickness.md) · [profile_camber](../measure/profile_camber.md) · [profile_leading_edge_radius](../measure/profile_leading_edge_radius.md)

## 同カテゴリ(`synth`)

[profile_perturb](profile_perturb.md)

---
*Provenance: profileops.py — PROFILE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
