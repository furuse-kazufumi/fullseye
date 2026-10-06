---
op: swing_up_plan
dim: drive
category: kendama
in: table
out: any
examples: [poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# swing_up_plan — DRIVE `kendama` op

- **データ種**: `table` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.swing_up_plan(kp: 'dict', *, lift: 'float' = 0.265, T_lift: 'float' = 0.15, kind: 'str' = 'bang', origin=(0.0, 0.0, 0.0), dodge=(0.0, 0.0, 0.0))` (実装を直接呼ぶなら `import kendama; kendama.swing_up_plan(kp: 'dict', *, lift: 'float' = 0.265, T_lift: 'float' = 0.15, kind: 'str' = 'bang', origin=(0.0, 0.0, 0.0), dodge=(0.0, 0.0, 0.0))`、台帳から引くなら `opsdrive.get("swing_up_plan")`)

## 使い方

手元(皿胴の中心。ひもの支点と大皿はそこから kp の offset だけずれて一緒に動く)の開ループ軌道: ``origin`` から真上へ ``lift`` だけ ``T_lift`` 秒で持ち上げ、以後静止。
返り値は t → (3,) の関数(t ≤ 0 で origin、t ≥ T_lift で origin + lift·ẑ で静止)。

``kind="bang"``: 加速 a = 4·lift/T² を T/2、減速 −a を T/2(速度三角形)。``kind="trap"``: 加速・等速・減速を T/3 ずつ
(速度台形、a = 9·lift/(2T²))。玉が昇るには減速の加速度が g を超える必要がある(:func:`swing_up_apex` が閉形式で答える)。
既定 lift = 0.265 m、T = 0.15 s(a = 47 m/s² ≈ 4.8 g、手元の最高速 3.5 m/s)で玉の頂点は大皿の縁の 4.9 cm 上
(ひもの有効長 0.42 m、大皿の縁は手元の 35 mm 上: :func:`swing_up_apex`)。

``dodge`` (3,)(水平): 減速に入って玉が離れた後(bang: T/2 → T、trap: 2T/3 → T)に手元を横へ ``dodge`` だけ逃がす
(S 字の bang-bang)。玉は皿胴の糸穴の真下から真っ直ぐ昇るので、逃がさないと皿胴・小皿を突き抜ける(物理は玉とけん玉の衝突を
解かない —— :func:`kendamaworld.kendama_clearance` で数える)。逃がした分は :func:`catch_plan_ballistic` の ``clearance`` が
玉が大皿の縁より上に出てから戻す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_kendama](../../../../examples/poc_kendama.py) — `py -3.11 examples/poc_kendama.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`kendama`)

[kendama_params](kendama_params.md) · [elliptic_k_agm](elliptic_k_agm.md) · [pendulum_period_exact](pendulum_period_exact.md) · [pendulum_launch_speed](pendulum_launch_speed.md) · [pendulum_rod_simulate](pendulum_rod_simulate.md) · [tether_tension_fixed](tether_tension_fixed.md) · [tether_slack_angle](tether_slack_angle.md) · [swing_up_apex](swing_up_apex.md)

---
*Provenance: kendama.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
