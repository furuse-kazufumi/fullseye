---
op: graph_conductance_states
dim: conngraph
category: circuit
in: conn_graph × matrix
out: matrix
examples: [poc_fly_optomotor_steering]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# graph_conductance_states — CONNGRAPH `circuit` op

- **データ種**: `conn_graph × matrix` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_conductance_states(W: 'Any', drive: 'Any', dt_s: 'float' = 0.001, tau_s: 'float' = 0.02, e_rest: 'float' = 0.0, e_exc: 'float' = 1.0, e_inh: 'float' = -1.0, release: 'str' = 'relu', v_half: 'float' = 0.5, slope: 'float' = 4.0, gain: 'float' = 1.0, v0: 'Any' = None) -> 'np.ndarray'` (実装を直接呼ぶなら `import conngraph; conngraph.graph_conductance_states(W: 'Any', drive: 'Any', dt_s: 'float' = 0.001, tau_s: 'float' = 0.02, e_rest: 'float' = 0.0, e_exc: 'float' = 1.0, e_inh: 'float' = -1.0, release: 'str' = 'relu', v_half: 'float' = 0.5, slope: 'float' = 4.0, gain: 'float' = 1.0, v0: 'Any' = None) -> 'np.ndarray'`、台帳から引くなら `opsconngraph.get("graph_conductance_states")`)

## 使い方

配線 ``W`` を**そのまま回路として回した**膜電位の時系列 ``(T, n)``(``matrix``、学習なし)。

ハエの視葉で「掛け算」に見えていた非線形の正体は、樹状突起のコンダクタンス比だった
(Groschner ら 2022: 定常では ``Vm = Σgᵢ Eᵢ / Σgᵢ``)。同じ形の式が、コネクトームを
配線として固定した全脳モデルの標準形でもある(Lappalainen ら 2024:
``τᵢ V̇ᵢ = −Vᵢ + Σ sᵢⱼ + V_rest``)。この op はその**動的な版**を、``conn_graph``
1 枚と外部入力 1 枚だけで回す:

    τ dVᵢ/dt = −(Vᵢ − e_rest) + g⁺ᵢ (e_exc − Vᵢ) + g⁻ᵢ (e_inh − Vᵢ)

``g⁺`` は ``W`` の**正の重み**、``g⁻`` は**負の重み**の絶対値を、前シナプス側の
放出 ``f(V)`` で重みづけて足したもの(``drive`` の正負も同じ向きに足す)。重みは
与えられたまま使う —— **学習も当てはめも一切しない**。時定数が入力で縮む
(実効 τ = ``τ/(1+g⁺+g⁻)``)ので、これは liquid time-constant 型の力学そのものだが、
パラメータは配線と定数だけで、勾配で決めた数は 1 つも無い。

W: ``(n, n)`` の重みつき隣接行列(``W[pre, post]``、正 = 興奮性、負 = 抑制性)。
drive: ``(T, n)`` の外部入力。正はそのノードを ``e_exc`` へ、負は ``e_inh`` へ引く
  コンダクタンスとして入る(電流ではない —— 電流だと下の有界性が壊れる)。
dt_s / tau_s: 刻みと膜時定数[秒]。e_rest / e_exc / e_inh: 静止電位と 2 つの反転電位。
release: 前シナプス放出 ``f(V)``。``"relu"`` は ``gain·max(V, 0)``、``"sigmoid"`` は
  ``gain/(1+exp(−slope(V−v_half)))``。**どちらも非負**で、負のコンダクタンス
  (物理的に存在しない)を作らない —— それが下の有界性の前提。
v_half / slope: シグモイドの半値と傾き。gain: 放出の利得(非負)。
v0: 初期状態 ``(n,)``。既定は全ノード ``e_rest``。

各段は**コンダクタンスを固定した厳密解**で進める(``V ← V∞ + (V − V∞)e^{−dt·g_tot/τ}``)
ので、刻みを粗くしても発散しない。

閉じた式で検査できること:

* **有界性**: 放出が非負である限り、``V∞`` は 3 つの反転電位の**凸結合**なので
  ``[min(e_rest, e_exc, e_inh), max(...)]`` の中にある。各段は ``V`` をその
  ``V∞`` へ指数で寄せるだけなので、**箱の中から始めれば必ず箱の中に留まり、
  箱の外から始めても外へは行かず箱へ向かう**。どんな配線・どんな入力でも
  発散しない、が構造で保証される(``v0`` の既定は ``e_rest`` = 箱の中)。
* **減衰**: 入力も結合も無ければ ``V(t) = e_rest + (V₀ − e_rest)e^{−t/τ}`` ちょうど。
* **定常**: 一定の入力 ``d > 0`` を 1 ノードに入れると ``V∞ = (e_rest + d·e_exc)/(1 + d)``、
  そこへ向かう実効時定数は ``τ/(1 + d)`` ちょうど(入力で時定数が縮む、の数値)。

**ValueError**: 正方でない / 非有限の ``W``、``(T, n)`` でない ``drive``、
非正の ``dt_s`` / ``tau_s``、負の ``gain``、未知の ``release``、長さの合わない ``v0``。

## 詳しい使い方ガイド

- [conngraph ファミリ ガイド](../guides/conngraph.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_fly_optomotor_steering](../../../../examples/poc_fly_optomotor_steering.py) — `py -3.11 examples/poc_fly_optomotor_steering.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[reservoir_states](../reservoir/reservoir_states.md) · [reservoir_encode](../reservoir/reservoir_encode.md) · [ridge_readout](../reservoir/ridge_readout.md) · [ridge_predict](../reservoir/ridge_predict.md) · [graph_activation_latency](../activity/graph_activation_latency.md) · [graph_activity_spread](../activity/graph_activity_spread.md) · [points_activity_video](../activity/points_activity_video.md) · [graph_layer_propagate](../dimension/graph_layer_propagate.md)

## 同カテゴリ(`circuit`)

—

---
*Provenance: conngraph.py — CONNGRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
