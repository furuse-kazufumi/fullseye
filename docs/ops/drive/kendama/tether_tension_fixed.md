---
op: tether_tension_fixed
dim: drive
category: kendama
in: 
out: scalar
examples: [poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# tether_tension_fixed — DRIVE `kendama` op

- **データ種**: `なし` → `scalar`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.tether_tension_fixed(v: 'float', theta: 'float', L: 'float', mass: 'float', g: 'float' = 9.81) -> 'float'` (実装を直接呼ぶなら `import kendama; kendama.tether_tension_fixed(v: 'float', theta: 'float', L: 'float', mass: 'float', g: 'float' = 9.81) -> 'float'`、台帳から引くなら `opsdrive.get("tether_tension_fixed")`)

## 使い方

手元固定・伸びないひもの張力 T = m(v²/L + g cos θ)(v = 速さ、θ = 真下からの角)。負なら「ひもは押せない」= 弛む。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_kendama](../../../../examples/poc_kendama.py) — `py -3.11 examples/poc_kendama.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`kendama`)

[kendama_params](kendama_params.md) · [elliptic_k_agm](elliptic_k_agm.md) · [pendulum_period_exact](pendulum_period_exact.md) · [pendulum_launch_speed](pendulum_launch_speed.md) · [pendulum_rod_simulate](pendulum_rod_simulate.md) · [tether_slack_angle](tether_slack_angle.md) · [swing_up_plan](swing_up_plan.md) · [swing_up_apex](swing_up_apex.md)

---
*Provenance: kendama.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
