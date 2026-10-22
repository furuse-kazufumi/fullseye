---
op: sem_electron_mc
dim: generative
category: sem
in: 
out: table
examples: [poc_sem_tem_same_particle, poc_virtual_sem_kv_cd_bse]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# sem_electron_mc — GENERATIVE `sem` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.sem_electron_mc(material='SI', energy_kev: 'float' = 10.0, *, tol: 'float' = 0.01, batch: 'int' = 1000, max_electrons: 'int' = 20000, seed: 'int' = 0, n_tracks: 'int' = 0, depth_bins: 'int' = 60, tilt_deg: 'float' = 0.0) -> 'dict'` (実装を直接呼ぶなら `import sem; sem.sem_electron_mc(material='SI', energy_kev: 'float' = 10.0, *, tol: 'float' = 0.01, batch: 'int' = 1000, max_electrons: 'int' = 20000, seed: 'int' = 0, n_tracks: 'int' = 0, depth_bins: 'int' = 60, tilt_deg: 'float' = 0.0) -> 'dict'`、台帳から引くなら `opsgenerative.get("sem_electron_mc")`)

## 使い方

平らな試料に電子を撃つモンテカルロ: 反射電子係数 η・二次電子収率 δ・相互作用体積。

Joy の単散乱モデル(遮蔽ラザフォード + Joy-Luo の阻止能)で一次電子を 1 個ずつ
追い、``batch`` 個ずつ足して 95 % 信頼区間の半幅が η で ``tol``、δ で ``tol``·max(δ, 1)
を切ったら止める(``max_electrons`` で打ち切り、その時は ``converged`` が False)。

Parameters
----------
material : str
    材料表の名前(``materials.material_electron_properties`` が引ける物。SI / W / AU /
    SILICA / PMMA …)。Z・A・密度・二次電子の 2 定数はそこから取る。
energy_kev : float
    加速電圧 [keV] (0.1〜50)。
tol : float
    信頼区間の半幅の目標。
batch, max_electrons : int
    1 回に足す電子の数と上限。
seed : int
    乱数の種(同じ種なら同じ結果)。
n_tracks : int
    軌跡を返す電子の数(図用)。
depth_bins : int
    深さ分布の区間の数(0〜1.2 R_KO)。
tilt_deg : float
    試料の傾き [度] (0〜80)。ビームが法線から θ 傾いて入る。δ(θ)/δ(0) を sec θ と、
    η(θ) を Arnal ほかの (1 + cos θ)^(−9/√Z) と比べるのに使う。

Returns
-------
dict
    ``eta`` / ``eta_ci95`` / ``se_yield`` / ``se_yield_ci95`` / ``n_electrons`` /
    ``converged`` / ``range_ko_nm``(Kanaya-Okayama)/ ``depth_max_nm``・
    ``depth_p95_nm``・``depth_p50_nm``(電子ごとの最大の深さ)/ ``lateral_p95_nm``
    (沈着エネルギーの 95 % が入る半径)/ ``depth_dose``(``pairs``: 深さ [nm] と
    沈着エネルギーの割合)/ ``bse_energy``(``pairs``: E/E0 と反射電子の割合)/
    ``tracks``(各 (K, 3) [nm]、z は下向きが正)。

Examples
--------
>>> r = sem_electron_mc("SI", 5.0, tol=0.03, batch=400, max_electrons=800)
>>> 0.1 < r["eta"] < 0.3 and r["depth_max_nm"] < r["range_ko_nm"]
True

## 詳しい使い方ガイド

- [generative_art ファミリ ガイド](../guides/generative_art.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_sem_tem_same_particle](../../../../examples/poc_sem_tem_same_particle.py) — `py -3.11 examples/poc_sem_tem_same_particle.py`
- [poc_virtual_sem_kv_cd_bse](../../../../examples/poc_virtual_sem_kv_cd_bse.py) — `py -3.11 examples/poc_virtual_sem_kv_cd_bse.py`

## 型が繋がる次の op(`table` を入力に取れる)

[perpetual_step](../stream/perpetual_step.md) · [perpetual_render](../stream/perpetual_render.md)

## 同カテゴリ(`sem`)

[sem_render](sem_render.md) · [sem_se_universal_curve](sem_se_universal_curve.md) · [sem_yield_curve](sem_yield_curve.md) · [sem_line_profile](sem_line_profile.md) · [sem_cd_measure](sem_cd_measure.md) · [sem_image](sem_image.md) · [sem_se_escape_fraction](sem_se_escape_fraction.md) · [sem_charging_series](sem_charging_series.md)

---
*Provenance: sem.py — GENERATIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
