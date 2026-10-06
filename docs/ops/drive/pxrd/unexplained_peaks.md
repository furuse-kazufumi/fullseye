---
op: unexplained_peaks
dim: drive
category: pxrd
in: table
out: table
examples: [poc_pxrd_phase_peel]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# unexplained_peaks — DRIVE `pxrd` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.unexplained_peaks(fit_result, intensity=None, min_snr=6.0, index=True, noise=None, known_ratio=0.25, model_error=0.1)` (実装を直接呼ぶなら `import pxrd; pxrd.unexplained_peaks(fit_result, intensity=None, min_snr=6.0, index=True, noise=None, known_ratio=0.25, model_error=0.1)`、台帳から引くなら `opsdrive.get("unexplained_peaks")`)

## 使い方

相分率の当てはめの残差から、辞書のどの相でも説明できない山を取り出す(未知相の手がかり)。

残差(``fit_result`` の ``residual``、または ``intensity − fit``)に :func:`diffraction_peaks` をかけ、正の山だけを
残す。既知相の強い線の上に乗った残差の山(高さが、その位置の既知相の模型の ``known_ratio`` 倍未満)は幅や形の
合わなさの名残りである見込みが高いので ``near_known=True`` の印を付け、指数付けからは外す(消さずに返す)。残りが
3 本以上あれば :func:`cubic_index` で立方晶として指数付けを試みる(``index=True``、外れ 1/3 まで許す)。既知相の格子が
ずれていると残差に「正と負の対」が出て偽の山になる —— その場合は :func:`phase_fractions` の ``lattice_tolerance`` を先に使う。
``noise`` には :func:`azimuthal_integrate` の ``sigma`` を渡すのが筋(無ければ残差の MAD から見積もる)。山の判定に使う
雑音は ``sqrt(noise² + (model_error × 既知相の模型)²)`` —— 計数が多いと Poisson の σ は小さく、強い既知線の形の
わずかな合わなさ(画素の箱形の広がりをガウスで近似した名残り。合成像で rwp 2〜4 %)が何千 σ の「山」に見えるので、
模型そのものの相対誤差を雑音の床に入れる。

返り値(dict): ``two_theta``・``d`` [Å]・``height``・``fwhm``・``snr``・``near_known``(bool)・``index``
(:func:`cubic_index` の結果か None)。

Raises ValueError: ``fit_result`` が :func:`phase_fractions` の形でない、長さの不一致。

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
