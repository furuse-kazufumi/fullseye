---
op: deflectometry_rig
dim: specular
category: deflectometry
in: 
out: table
examples: [poc_phase_measuring_deflectometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# deflectometry_rig — SPECULAR `deflectometry` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.deflectometry_rig(incidence_deg=20.0, camera_distance_mm=400.0, screen_distance_mm=300.0, field_mm=40.0, aperture_mm=4.0, screen_size_mm=(520.0, 320.0), screen_pixel_mm=0.27)` (実装を直接呼ぶなら `import deflectometry; deflectometry.deflectometry_rig(incidence_deg=20.0, camera_distance_mm=400.0, screen_distance_mm=300.0, field_mm=40.0, aperture_mm=4.0, screen_size_mm=(520.0, 320.0), screen_pixel_mm=0.27)`、台帳から引くなら `opsspecular.get("deflectometry_rig")`)

## 使い方

デフレクトメトリの装置(カメラ・画面・視野)の幾何を 1 つの表(dict)にする。

入射面は x-z 面。カメラ(ピンホール)は面の中心から ``camera_distance_mm`` = L 離れ、法線から
``incidence_deg`` = θ 傾いた位置 C = L(−sin θ, 0, cos θ) から原点を見る。画面は公称の正反射方向
r0 = (sin θ, 0, cos θ) 上の距離 ``screen_distance_mm`` = d に、r0 と直交して置く。
``field_mm`` は測る面の正方形の一辺(高さ場の格子はこの視野に張る。縦横比は高さ場の形に従う)。
``aperture_mm`` はレンズの開口の直径(ピントのぼけの錯乱円に効く。0 = ピンホール)。
``screen_size_mm`` は画面の (幅 u, 高さ v)、``screen_pixel_mm`` は画面の画素ピッチ
(24 型 WUXGA でおよそ 0.27 mm)。

返り値: dict。スカラーの入力 7 つに加え、ベクトル ``camera``(C)、``screen_center``、
``screen_normal``(面へ向く)、``e_u`` / ``e_v``(画面の座標軸)、``forward`` / ``right`` /
``down``(カメラの光軸と、画像の列・行の方向)。他の op はこの dict を ``rig=`` で受け、
手で書き換えたベクトルはスカラーと食い違うとして拒否する(fail-closed)。

Raises: ``ValueError`` —— 入射角が [0, 80] 度の外、距離・視野・画面の大きさ・画素ピッチが
正でない、開口が負、値が数でない・有限でない、画面の大きさが 2 つの数でない。

## 詳しい使い方ガイド

- [specular_photometric ファミリ ガイド](../guides/specular_photometric.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_phase_measuring_deflectometry](../../../../examples/poc_phase_measuring_deflectometry.py) — `py -3.11 examples/poc_phase_measuring_deflectometry.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`deflectometry`)

[deflectometry_screen_pattern](deflectometry_screen_pattern.md) · [deflectometry_render](deflectometry_render.md) · [deflectometry_phase_to_slope](deflectometry_phase_to_slope.md) · [slope_to_curvature](slope_to_curvature.md) · [deflectometry_sensitivity](deflectometry_sensitivity.md)

---
*Provenance: deflectometry.py — SPECULAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
