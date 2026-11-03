---
op: registration_to_flow2d
dim: matchreg
category: intensityreg
in: table
out: flow2d
gpu: なし
examples: [poc_sheet_deformation_ffd]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# registration_to_flow2d — MATCHREG `intensityreg` op

- **データ種**: `table` → `flow2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.registration_to_flow2d(result)` (実装を直接呼ぶなら `import intensityreg; intensityreg.registration_to_flow2d(result)`、台帳から引くなら `opsmatchreg.get("registration_to_flow2d")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

位置合わせの結果の表から変形場 ``flow2d``((2,H,W) の ``(dy, dx)``)を取り出す。→ flow2d。

向きは :mod:`deformreg` と同じ(動く画像の内容の前向き変位)。``piv_flow_magnitude`` /
``piv_vorticity`` / ``flow_to_rgbimage`` など ``flow2d`` を受ける op へ繋ぐための口。

Args:
    result: :func:`register_ecc` / :func:`register_mi` / :func:`register_ffd` の表。

Returns:
    ``(2, H, W)`` float64 の ndarray(写し)。

Raises:
    ValueError: ``kind="registration"`` の表でない / 場の形が違う。

## 詳しい使い方ガイド

- [matching_registration ファミリ ガイド](../guides/matching_registration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_sheet_deformation_ffd](../../../../examples/poc_sheet_deformation_ffd.py) — `py -3.11 examples/poc_sheet_deformation_ffd.py`

## 型が繋がる次の op(`flow2d` を入力に取れる)

[register_accuracy_map](register_accuracy_map.md)

## 同カテゴリ(`intensityreg`)

[register_ecc](register_ecc.md) · [register_mi](register_mi.md) · [register_ffd](register_ffd.md) · [register_accuracy_map](register_accuracy_map.md) · [register_capture_range](register_capture_range.md)

---
*Provenance: intensityreg.py — MATCHREG operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
