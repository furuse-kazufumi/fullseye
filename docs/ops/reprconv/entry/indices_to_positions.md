---
op: indices_to_positions
dim: reprconv
category: entry
in: indices
out: positions
gpu: なし
examples: [type_connectivity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# indices_to_positions — REPRCONV `entry` op

- **データ種**: `indices` → `positions`
- **呼び出し**: `import fullseye as fs; fs.ledger.indices_to_positions(indices, spacing=1.0, origin=0.0)` (実装を直接呼ぶなら `import reprconv; reprconv.indices_to_positions(indices, spacing=1.0, origin=0.0)`、台帳から引くなら `opsreprconv.get("indices_to_positions")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

添字 ``indices`` → 事象の位置 ``positions``(物理単位)。``positions`` 型の入口。

``x = origin + spacing * i``。``find_peaks`` / ``zero_crossings_funct_1d`` などが返す
**標本番号**を、``point_spectrum`` が受ける**位置の列**(欠陥が流れ方向のどこにあったか、
いつ数えたか)にする。``positions`` を ``signal`` と分けてあるのは、等間隔標本の列を
事象の位置として(またはその逆に)渡すと、例外なしに別物のスペクトルが出るため
(``point_spectrum`` の docstring)。順序は入力のまま(並べ替えない)。

空の添字は ValueError(この repo の空入力の方針 A: 黙って空を返さず、何が空かを名指しで拒否)。

Args:
    indices: 1-D の整数(整数値の float も可。非整数・非有限・空は拒否)。
    spacing: 標本間隔(位置の単位 / 標本)。有限で 0 でないこと。
    origin: 添字 0 の位置。有限。
Returns:
    (k,) float64。
Raises:
    ValueError: 1-D でない / 整数でない / 非有限 / 空 / spacing が 0 か非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [type_connectivity_tour](../../../../examples/type_connectivity_tour.py) — `py -3.11 examples/type_connectivity_tour.py`

## 型が繋がる次の op(`positions` を入力に取れる)

—

## 同カテゴリ(`entry`)

[synapse_table_from_table](synapse_table_from_table.md) · [jones_state](jones_state.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
