---
op: cubic_prototype
dim: drive
category: pxrd
in: any × scalar × any
out: table
examples: [poc_pxrd_phase_peel]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# cubic_prototype — DRIVE `pxrd` op

- **データ種**: `any × scalar × any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.cubic_prototype(kind, a, species, b_iso=0.5, name=None)` (実装を直接呼ぶなら `import pxrd; pxrd.cubic_prototype(kind, a, species, b_iso=0.5, name=None)`、台帳から引くなら `opsdrive.get("cubic_prototype")`)

## 使い方

立方晶の原型(``sc``・``bcc``・``fcc``・``diamond``・``rocksalt``・``cscl``・``zincblende``・``fluorite``)から相を作る。

CIF が無いときの相の作り方(教科書の座標だけ)。``species`` は副格子ごとの散乱体の名前の list(rocksalt は
``["Na", "Cl"]``、fluorite は ``["Ca", "F"]`` の順 = 陽イオン、陰イオン)。``a`` [Å]、``b_iso`` [Å²] は全原子共通。
返り値は :func:`cif_read` と同じ形の相。

Raises ValueError: 原型の名前の綴り違い、副格子の数と ``species`` の数の不一致、未知の元素、``a <= 0``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_pxrd_phase_peel](../../../../examples/poc_pxrd_phase_peel.py) — `py -3.11 examples/poc_pxrd_phase_peel.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pxrd`)

[cif_read](cif_read.md) · [powder_reflections](powder_reflections.md) · [scherrer_size](scherrer_size.md) · [debye_ring_image](debye_ring_image.md) · [detector_two_theta](detector_two_theta.md) · [detector_calibrate](detector_calibrate.md) · [azimuthal_integrate](azimuthal_integrate.md) · [diffraction_peaks](diffraction_peaks.md)

---
*Provenance: pxrd.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
