---
op: pod_hitmiss_fit
dim: spc
category: pod
in: table
out: table
gpu: なし
examples: [poc_pod_lighting, poc_sem_wafer_defect_edge_bias, poc_si_wafer_pl_defect_visibility]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# pod_hitmiss_fit — SPC `pod` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.pod_hitmiss_fit(table, size='a', hit='hit', link='logit', log_size=False, level=0.95, n_grid=200)` (実装を直接呼ぶなら `import pod; pod.pod_hitmiss_fit(table, size='a', hit='hit', link='logit', log_size=False, level=0.95, n_grid=200)`、台帳から引くなら `opsspc.get("pod_hitmiss_fit")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

見つけた/見落としたの 2 値データから POD(a) を一般化線形モデルで当てる(``table``)。

``POD(a) = F(β0 + β1 x)``、``x = a`` または ``ln a``、``F`` はリンクの逆
(``logit`` / ``probit`` / ``cloglog``、MIL-HDBK-1823A G.4.1.1)。最尤推定は
ニュートン法(logit では反復重み付き最小二乗と同じ)、共分散は観測情報の逆。

``a_p = (F⁻¹(p) − β0)/β1`` で a50 / a90 を出す(logit なら ``a50 = −β0/β1``)。
a90/95 は 2 通り返す:

  * ``a90_95``(Wald / デルタ法): ``x90 + z_level · se(x90)``、
    ``var(x90) = [vβ0 + 2 x90 c + x90² vβ1]/β1²``。
  * ``a90_95_lr``(尤度比、G.4.2.2): x90 を固定して β1 について最大化した
    **プロファイル対数尤度** ``ℓp(x90)`` が ``ℓmax − χ²₁(2·level − 1)/2`` まで落ちる
    x90(片側なので 95 % なら χ² の 90 % 点 2.7055)。1823A のソフトは
    (μ, σ) の 2 次元の信頼域の包絡線を描くが、ここで返すのは a90 という
    1 つの量に対する境界なので自由度 1 のプロファイルを使う —— **定義が違う**ことを
    明示しておく。尤度が十分に落ちない(データが少なく上限が無い)ときは
    ``None`` と ``lr_status = "unbounded"``。

曲線 ``pod`` / ``pod_lower``(Wald、水平方向)は ``n_grid`` 点。``a90_95_beyond_data``
は Wald の a90/95 が試した最大の大きさを超えた(外挿である)ことの旗。

空の入力(``table`` が 0 行、または空の dict)は ValueError。
拒否(``ValueError``): 空の表・列の欠け、``hit`` が 0/1 以外、全部検出か全部
見落とし(曲線が立たない)、**完全分離**(ある大きさを境に全部見落とし/全部検出 =
最尤推定が無限大へ発散する)、``β1 <= 0`` または標準誤差の ``z_level`` 倍以下、未知の ``link``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_pod_lighting](../../../../examples/poc_pod_lighting.py) — `py -3.11 examples/poc_pod_lighting.py`
- [poc_sem_wafer_defect_edge_bias](../../../../examples/poc_sem_wafer_defect_edge_bias.py) — `py -3.11 examples/poc_sem_wafer_defect_edge_bias.py`
- [poc_si_wafer_pl_defect_visibility](../../../../examples/poc_si_wafer_pl_defect_visibility.py) — `py -3.11 examples/poc_si_wafer_pl_defect_visibility.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md)

## 同カテゴリ(`pod`)

[proportion_interval](proportion_interval.md) · [trials_for_all_success](trials_for_all_success.md) · [pod_ahat_fit](pod_ahat_fit.md) · [pod_from_ahat](pod_from_ahat.md) · [pod_false_call](pod_false_call.md) · [pod_decision_tradeoff](pod_decision_tradeoff.md)

---
*Provenance: pod.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
