---
op: profile_align
dim: profile
category: compare
in: pairs × pairs
out: pairs
examples: [profile_frame_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# profile_align — PROFILE `compare` op

- **データ種**: `pairs × pairs` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.profile_align(measured, reference, mode='chord')` (実装を直接呼ぶなら `import profileops; profileops.profile_align(measured, reference, mode='chord')`、台帳から引くなら `opsprofile.get("profile_align")`)
- **台帳経由の戻り値**: `fullseye.ledger.profile_align(...)` は**宣言 out 型 `pairs` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.profile_align.raw(...)`、または `profileops.profile_align` を直接呼ぶ。
  - 本体の返り: `(aligned, info) -> pairs`

## 使い方

測った輪郭を設計輪郭へ合わせる。返りは ``(aligned, info)``。

``mode`` は :data:`ALIGN_MODES`。**相似(スケール推定)は提供しない** ——
大きさの誤差そのものを吸収してしまうため(モジュール docstring の実測表)。

Returns:
    ``(aligned (N, 2), info)``。``info`` は ``mode`` / ``angle_deg`` /
    ``translation`` / ``scale``(常に 1.0。**推定していないことの明示**)。

## 詳しい使い方ガイド

- [profile_metrology ファミリ ガイド](../guides/profile_metrology.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [profile_frame_tour](../../../../examples/profile_frame_tour.py) — `py -3.11 examples/profile_frame_tour.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[profile_perturb](../synth/profile_perturb.md) · [profile_chord_frame](../frame/profile_chord_frame.md) · [profile_normalise](../frame/profile_normalise.md) · [profile_resample](../frame/profile_resample.md) · [profile_sides](../measure/profile_sides.md) · [profile_thickness](../measure/profile_thickness.md) · [profile_camber](../measure/profile_camber.md) · [profile_leading_edge_radius](../measure/profile_leading_edge_radius.md)

## 同カテゴリ(`compare`)

[profile_deviation](profile_deviation.md)

---
*Provenance: profileops.py — PROFILE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
