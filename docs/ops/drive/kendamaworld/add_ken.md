---
op: add_ken
dim: drive
category: kendamaworld
in: table × table
out: scalar
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# add_ken — DRIVE `kendamaworld` op

- **データ種**: `table × table` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.add_ken(world: 'dict', mesh: 'dict', p, R=None, *, name: 'str' = 'ken') -> 'int'` (実装を直接呼ぶなら `import kendamaworld; kendamaworld.add_ken(world: 'dict', mesh: 'dict', p, R=None, *, name: 'str' = 'ken') -> 'int'`、台帳から引くなら `opsdrive.get("add_ken")`)

## 使い方

けんを姿勢 (p = 皿胴の中心, R) で世界に足す(面ラベル 27/28/30/31 はそのまま)。返り値 = objects の索引。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`kendamaworld`)

[ken_mesh](ken_mesh.md) · [ken_set_pose](ken_set_pose.md) · [string_mesh](string_mesh.md) · [add_string](add_string.md) · [string_set](string_set.md) · [kendama_world](kendama_world.md) · [kendama_rig](kendama_rig.md) · [ken_truth](ken_truth.md)

---
*Provenance: kendamaworld.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
