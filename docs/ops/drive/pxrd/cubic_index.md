---
op: cubic_index
dim: drive
category: pxrd
in: signal × scalar
out: table
examples: [poc_pxrd_phase_peel]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# cubic_index — DRIVE `pxrd` op

- **データ種**: `signal × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.cubic_index(two_theta, wavelength, lattices=('P', 'I', 'F', 'diamond'), tolerance=0.05, n_first=6, max_unindexed=0)` (実装を直接呼ぶなら `import pxrd; pxrd.cubic_index(two_theta, wavelength, lattices=('P', 'I', 'F', 'diamond'), tolerance=0.05, n_first=6, max_unindexed=0)`、台帳から引くなら `opsdrive.get("cubic_index")`)

## 使い方

立方晶として山に指数を付け、格子(P / I / F / diamond)と格子定数 a [Å] を決める。

``1/d² = N / a²`` なので、1 本目の山に許される N の小さい方から ``n_first`` 個を当てて a を仮に決め、全部の山を
最も近い許される N に割り当て、``a`` を最小二乗で追い込み(割り当て → 追い込みを 2 回)、計算と観測の 2θ の差が
``tolerance`` [deg] 以内の候補だけを残す(外れる山が ``max_unindexed`` 本までなら、それを除いて残す —— 不純物や
偽の山が 1 本混じっただけで全部を捨てないため。除いた山は ``unindexed`` に返す)。候補どうしは de Wolff の M 型の性能指数
``M = Q_last / (2 ε̄ N_calc)``(``Q = 1/d²``、``ε̄`` = |ΔQ| の平均、``N_calc`` = 最後の観測線までに許される計算線の数)
で比べる —— P は何にでも合うが計算線が多いぶん M が下がる。外した山がある候補は ``(指数の付いた割合)⁴`` で割り引く
(経験的な重み。強い山を捨てて計算線の少ない格子に逃げるのを防ぐ)。

返り値(dict): ``lattice``・``a``・``a_sigma``(残差からの標準誤差)・``two_theta``(指数の付いた山)・``hkl``((n, 3))・
``N``・``residual_deg``(観測 − 計算)・``fom``・``missing``(範囲内で許されるのに観測に無い N の list)・``unindexed``
(外した山)・``candidates``(全候補の要約)。
当てはまる候補が無ければ ``lattice = None``(立方晶でない・山の取り違え)。

Raises ValueError: 山が 2 本未満・非有限・(0, 180) の外、波長が非正、格子の綴り違い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_pxrd_phase_peel](../../../../examples/poc_pxrd_phase_peel.py) — `py -3.11 examples/poc_pxrd_phase_peel.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pxrd`)

[cif_read](cif_read.md) · [cubic_prototype](cubic_prototype.md) · [powder_reflections](powder_reflections.md) · [scherrer_size](scherrer_size.md) · [debye_ring_image](debye_ring_image.md) · [detector_two_theta](detector_two_theta.md) · [detector_calibrate](detector_calibrate.md) · [azimuthal_integrate](azimuthal_integrate.md)

---
*Provenance: pxrd.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
