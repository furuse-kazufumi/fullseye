---
op: find_marks_and_pose
dim: calib
category: calibrate
in: image2d
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.0  # fullseye lib version this note was generated for
---

# find_marks_and_pose — CALIB `calibrate` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.find_marks_and_pose(image, cam_par, caltab, thresh=0.5, max_reproj_rms=3.0)` (実装を直接呼ぶなら `import caltab; caltab.find_marks_and_pose(image, cam_par, caltab, thresh=0.5, max_reproj_rms=3.0)`、台帳から引くなら `opscalib.get("find_marks_and_pose")`)

## 使い方

マーク検出 + 校正板の姿勢推定(平面ホモグラフィ → pose)(find_marks_and_pose)。

対応づけは行優先ソートではなく **ホモグラフィ誘導**: 検出マークと理想格子の 4 隅
(row±col の極値)から初期 H を作り、理想点を投影して最近傍マークを 1 対 1 に
割り当て、全対応で H を再推定(2 反復)。板の面内回転が ±45° 未満なら傾き
(rx, ry)の大きさに関係なく正しく対応する(2026-09-02 以前は少しの傾きで
行が交錯し、深度が数百 mm ずれても無警告だった)。

fail-closed: マークが 4 個未満/対応が 4 組未満/再投影 RMS が
``max_reproj_rms`` [px] を超えるときは ``ValueError``(``None`` で無効化可)。
戻り値: ``marks`` (M,2) 対応づいた検出マーク(``ideal_index`` の順)、``pose`` 4x4、
``homography`` (x,y)→(col,row)、``reproj_rms`` [px]、``residuals`` (M,)、``n_marks``。
world は ``caltab["points"]`` の (y, x) をそのまま (x, y, 0) とする。

## 詳しい使い方ガイド

- [camera_calibration ファミリ ガイド](../guides/camera_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[sim_caltab](../target/sim_caltab.md) · [disp_caltab](../target/disp_caltab.md)

## 同カテゴリ(`calibrate`)

[camera_calibration](camera_calibration.md) · [hand_eye_calibration](hand_eye_calibration.md)

---
*Provenance: caltab.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
