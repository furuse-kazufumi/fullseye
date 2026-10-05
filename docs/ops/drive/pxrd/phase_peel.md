---
op: phase_peel
dim: drive
category: pxrd
in: signal × signal × table
out: table
examples: [poc_pxrd_phase_peel]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# phase_peel — DRIVE `pxrd` op

- **データ種**: `signal × signal × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.phase_peel(two_theta, intensity, dictionary, max_phases=None, min_gain=0.05, min_fraction=0.005, background_order=4, sigma=None)` (実装を直接呼ぶなら `import pxrd; pxrd.phase_peel(two_theta, intensity, dictionary, max_phases=None, min_gain=0.05, min_fraction=0.005, background_order=4, sigma=None)`、台帳から引くなら `opsdrive.get("phase_peel")`)

## 使い方

混合物から相を 1 つずつ剥がす(貪欲な前進選択)。

段 0 は背景だけ。各段で、まだ選んでいない相を 1 つずつ足して :func:`phase_fractions` を当て、``rwp`` が最も下がる
相を選ぶ。``rwp`` の相対的な下がり幅が ``min_gain`` 未満、または選んだ相の重量分率が ``min_fraction`` 未満なら止める。
全部の相を一度に当てる :func:`phase_fractions` と違い、「どの順で、どれだけ説明が進んだか」が残る(図の素材)。

返り値(dict): ``order``(選んだ順の名前)・``stages``(各段の ``phases``・``weight_fraction``・``fit``・``residual``・
``rwp``)・``final``(最後の段の :func:`phase_fractions` の結果)。

Raises ValueError: :func:`phase_fractions` と同じ。``min_gain`` が [0, 1) の外。

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
