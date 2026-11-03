---
op: virtual_acceptance_test
dim: acceptance
category: simulate
in: table
out: table
gpu: なし
examples: [poc_virtual_acceptance_3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# virtual_acceptance_test — ACCEPTANCE `simulate` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.virtual_acceptance_test(sensor, layout=None, mpe=None, exclude_fraction=0.003, seed=0)` (実装を直接呼ぶなら `import acceptance3d; acceptance3d.virtual_acceptance_test(sensor, layout=None, mpe=None, exclude_fraction=0.003, seed=0)`、台帳から引くなら `opsacceptance.get("virtual_acceptance_test")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

シミュレーションのセンサで試験体の全配置を撮り、PF・PS・SD・F と合否を返す(``table``)。

Run the whole virtual acceptance test: scan the probing sphere, the ball bar in its 7 positions and the
flat in its 7 positions with the simulated ``sensor`` (see :func:`acceptance_scan`), evaluate them with
the same ops a real point cloud would go through, and (if ``mpe`` is given) the verdict.

返す ``dict``: ``pf``・``ps``(探針の球の位置ごと)、``sd``(ダンベル 7 姿勢)、``f``(平面 7 姿勢)、
``probe``・``bars``・``planes``(各評価 op の返り)、``verdict``(``mpe`` があれば :func:`acceptance_verdict`)、
``layout``、``sensor``(既定値で埋めた写し)。ダンベルの 2 球は場面の番号で分ける(実機では作業者が
範囲を切る作業にあたる)。

**Raises** ``ValueError``: センサや配置が不正、どれかの試験体が 10 点未満しか写らない。

## 詳しい使い方ガイド

- [optical_3d_acceptance ファミリ ガイド](../guides/optical_3d_acceptance.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_virtual_acceptance_3d](../../../../examples/poc_virtual_acceptance_3d.py) — `py -3.11 examples/poc_virtual_acceptance_3d.py`

## 型が繋がる次の op(`table` を入力に取れる)

[acceptance_verdict](../evaluate/acceptance_verdict.md) · [acceptance_scan](acceptance_scan.md) · [acceptance_error_budget](../budget/acceptance_error_budget.md)

## 同カテゴリ(`simulate`)

[acceptance_scan](acceptance_scan.md)

---
*Provenance: acceptance3d.py — ACCEPTANCE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
