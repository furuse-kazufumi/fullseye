---
op: cif_read
dim: drive
category: pxrd
in: any
out: table
examples: [poc_pxrd_phase_peel]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# cif_read — DRIVE `pxrd` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.cif_read(cif, name=None, default_b=0.5)` (実装を直接呼ぶなら `import pxrd; pxrd.cif_read(cif, name=None, default_b=0.5)`、台帳から引くなら `opsdrive.get("cif_read")`)

## 使い方

CIF(結晶構造の標準書式)を読んで、単位格子の中の全原子に展開した「相」を返す。

``cif`` はファイルのパスか CIF の本文(文字列。``data_`` か ``_cell_length_a`` を含むなら本文とみなす)。
読むもの: ``_cell_length_a/b/c``・``_cell_angle_alpha/beta/gamma``、対称操作のループ
(``_space_group_symop_operation_xyz`` か ``_symmetry_equiv_pos_as_xyz``、無ければ恒等だけ)、原子のループ
(``_atom_site_fract_x/y/z``、``_atom_site_type_symbol``(無ければラベルの先頭の元素記号)、``_atom_site_occupancy``
(既定 1)、``_atom_site_U_iso_or_equiv`` か ``_atom_site_B_iso_or_equiv``(無ければ ``default_b`` [Å²]))。
数値の不確かさの括弧(``4.76050(5)``)は落とす。対称操作は自前の小さな構文解析で読み、``eval`` しない。

返り値(dict、相): ``name``・``cell``(a, b, c [Å], α, β, γ [deg])・``volume`` [Å³]・``atoms``(展開後の原子の
list: ``type``・``xyz``・``occ``・``B``)・``cell_mass`` [g/mol]・``density`` [g/cm³]・``notes``(中性原子で代用した
イオンなど)・``source``(DOI と COD 番号があれば)。:func:`powder_reflections` と :func:`phase_dictionary` の入力。

Raises ValueError: 格子定数が無い・数値でない、対称操作が読めない、原子が無い、散乱因子の無い元素。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_pxrd_phase_peel](../../../../examples/poc_pxrd_phase_peel.py) — `py -3.11 examples/poc_pxrd_phase_peel.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pxrd`)

[cubic_prototype](cubic_prototype.md) · [powder_reflections](powder_reflections.md) · [scherrer_size](scherrer_size.md) · [debye_ring_image](debye_ring_image.md) · [detector_two_theta](detector_two_theta.md) · [detector_calibrate](detector_calibrate.md) · [azimuthal_integrate](azimuthal_integrate.md) · [diffraction_peaks](diffraction_peaks.md)

---
*Provenance: pxrd.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
