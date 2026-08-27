# -*- coding: utf-8 -*-
"""事例: 進化探索で見つけた点群デノイズ・パイプライン。

実問題: レーザースキャナやステレオ深度で得た点群には、表面の細かなノイズと
遠くに飛んだ外れ値(スパイク)が混じる。これを取り除いて「きれいな表面」に
近づけたい。どの処理(外れ値除去・平滑化・ダウンサンプル)をどの順で並べれば
一番きれいになるかを、進化的探索(遺伝的アルゴリズム)に自動で見つけさせる。

honest 規律: 進化が見つけた best パイプラインが「無処理(そのまま)」と
「人が手で組んだ定番パイプライン」を本当に上回るかを chamfer 距離で検証する。
上回らなければ探索の価値はない(beat-the-null)。
"""
import numpy as np
import pipeline_evolve as pe

# --- 合成データ: きれいな球面 + ガウスノイズ + 一様外れ値 ---------------------
# make_denoise_task が「clean 球面(目標)」「noisy+外れ値(入力)」を作り、
# 目標との chamfer 距離を fitness にする(小さいほど良い)。
task = pe.make_denoise_task(seed=0)
print("入力点数(ノイズ+外れ値込み):", len(task.x))
print("目標点数(clean 球面)      :", len(task.target))

# --- 3 者を同一メトリクス(chamfer)で比較 -----------------------------------
# fitness = -chamfer なので chamfer = -fitness。小さいほど良い。
ev = pe.evolve(task, pop=24, gens=12, seed=0)          # 進化探索の best
cd_best = -ev["fitness"]
cd_ident = -pe.evaluate((), task)                       # identity(無処理)
cd_hand = -pe.evaluate(pe.hand_designed_chain(), task)  # 人手の定番(SOR→MLS)

print("\n--- chamfer 距離(小さいほど clean 表面に近い)---")
print(f"identity   (無処理)          : {cd_ident:.6f}")
print(f"hand_designed ({pe.describe(pe.hand_designed_chain())}): {cd_hand:.6f}")
print(f"evolved best ({pe.describe(ev['best'])}): {cd_best:.6f}")
print(f"評価したユニーク chain 数     : {ev['n_evals']}")

# 実測の改善率(誇張しない・数値をそのまま)
imp_vs_ident = (cd_ident - cd_best) / cd_ident * 100.0
imp_vs_hand = (cd_hand - cd_best) / cd_hand * 100.0
print(f"\nidentity 比の改善     : {imp_vs_ident:.1f}%  ({cd_ident:.4f} -> {cd_best:.4f})")
print(f"hand_designed 比の改善: {imp_vs_hand:.2f}% ({cd_hand:.4f} -> {cd_best:.4f})")

# --- GT 検証(数値 assert)---------------------------------------------------
# (1) 進化 best は無処理を大きく改善(chamfer が無処理の 0.6 倍未満)
assert cd_best < 0.6 * cd_ident, (cd_best, cd_ident)
# (2) 進化 best は人手の定番を下回らない(chamfer が hand 以下)
assert cd_best <= cd_hand + 1e-9, (cd_best, cd_hand)
# (3) 進化中の best fitness はエリート保存で悪化しない(単調非減少)
h = ev["history"]
assert all(h[i + 1] >= h[i] - 1e-9 for i in range(len(h) - 1)), h

print("\nOK: 進化 best は identity と hand_designed を chamfer で上回った(beat-the-null 成立)")
