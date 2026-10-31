---
op: trials_for_all_success
dim: spc
category: pod
in: 
out: scalar
examples: [proportion_interval_audit]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# trials_for_all_success — SPC `pod` op

- **データ種**: `なし` → `scalar`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.trials_for_all_success(p_min, *, confidence=0.95)` (実装を直接呼ぶなら `import pod; pod.trials_for_all_success(p_min, *, confidence=0.95)`、台帳から引くなら `opsspc.get("trials_for_all_success")`)

## 使い方

全数成功で ``p >= p_min`` を片側 ``confidence`` で示す最小試行数(``scalar``)。

返り値は整数で、Clopper--Pearson の全数成功時の閉形式
``(1-confidence)**(1/n) >= p_min`` に基づく。たとえば POD >= 0.90 を
95 % 信頼で示すには 29/29 が必要である。誤警報率 ``p <= p_max`` を
0 件で示す件数は ``trials_for_all_success(1-p_max, confidence=...)`` と同じ。

拒否(``ValueError``): ``p_min`` または ``confidence`` が有限な (0, 1) 外。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [proportion_interval_audit](../../../../examples/proportion_interval_audit.py) — `py -3.11 examples/proportion_interval_audit.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`pod`)

[proportion_interval](proportion_interval.md) · [pod_ahat_fit](pod_ahat_fit.md) · [pod_from_ahat](pod_from_ahat.md) · [pod_hitmiss_fit](pod_hitmiss_fit.md) · [pod_false_call](pod_false_call.md) · [pod_decision_tradeoff](pod_decision_tradeoff.md)

---
*Provenance: pod.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
