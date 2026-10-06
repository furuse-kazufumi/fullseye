---
op: phase_dictionary
dim: drive
category: pxrd
in: any × signal × scalar
out: table
examples: [poc_pxrd_phase_peel]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# phase_dictionary — DRIVE `pxrd` op

- **データ種**: `any × signal × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.phase_dictionary(phases, two_theta, wavelength, size=inf, K=0.9, instrumental_fwhm=0.02, lorentz='powder', eta=0.0)` (実装を直接呼ぶなら `import pxrd; pxrd.phase_dictionary(phases, two_theta, wavelength, size=inf, K=0.9, instrumental_fwhm=0.02, lorentz='powder', eta=0.0)`、台帳から引くなら `opsdrive.get("phase_dictionary")`)

## 使い方

相の参照パターンの辞書: 2θ の格子の上に、体積分率 1 あたりの 1-D 強度を相ごとに並べる。

1 行 = ``(1/V²) Σ m|F|² L(2θ) × 形``(形は Scherrer の ``size`` [Å] と装置の FWHM をガウスで足した幅の pseudo-Voigt、
``eta`` は Lorentz の割合)。``instrumental_fwhm`` は数 [deg] か ``(2θ の列, FWHM の列)`` の表 —— 平らな検出器では画素の
張る角が ``cos² 2θ`` で縮むので装置の幅は 2θ で変わる。広がりの無い標準(Si)の像を同じ幾何で積分し、
:func:`diffraction_peaks` の FWHM を表にして渡すのが筋(PoC の手順)。:func:`azimuthal_integrate` を偏光・立体角の補正つきで回したプロファイルと同じ量に揃う。
幅が合っていないと NNLS の倍率が偏る —— :func:`diffraction_peaks` の FWHM と :func:`scherrer_size` で ``size`` を
先に見積もるのが筋。

返り値(dict): ``names``・``two_theta``・``matrix``((P, n))・``density`` [g/cm³]・``phases``(元の相、格子の追い込みで
描き直すため)・``params``(波長・幅・Lorentz)。

Raises ValueError: 相が空・相の形でない、名前の重複、格子が増えない、幅の値が不正。

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
