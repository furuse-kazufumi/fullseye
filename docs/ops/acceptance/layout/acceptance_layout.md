---
op: acceptance_layout
dim: acceptance
category: layout
in: 
out: table
gpu: なし
examples: [poc_virtual_acceptance_3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# acceptance_layout — ACCEPTANCE `layout` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.acceptance_layout(volume_mm=(400.0, 300.0, 300.0), center_mm=(0.0, 0.0, 800.0), sphere_diameter_mm=25.0, bar_length_mm=None, plane_size_mm=(300.0, 150.0), plane_tilt_deg=25.0)` (実装を直接呼ぶなら `import acceptance3d; acceptance3d.acceptance_layout(volume_mm=(400.0, 300.0, 300.0), center_mm=(0.0, 0.0, 800.0), sphere_diameter_mm=25.0, bar_length_mm=None, plane_size_mm=(300.0, 150.0), plane_tilt_deg=25.0)`、台帳から引くなら `opsacceptance.get("acceptance_layout")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

測定体積の中に試験体(探針の球 1・ダンベル 7 姿勢・平面 7 姿勢)を置く配置を作る(``table``)。

Place the artefacts in the measuring volume: one probing sphere at the centre, a ball bar in 7
orientations and a flat in 7 orientations. Coordinates are the sensor frame (x right, y down,
z along the optical axis, mm), the volume a box of ``volume_mm`` centred on ``center_mm``.

ダンベルの 7 姿勢 = 空間対角線 4 本 + 面の対角線 3 本(xy・xz・yz)、どれも体積の中心を通る。光軸(z)に
平行な姿勢は手前の球が奥の球を隠すので取らない。平面の 7 姿勢 = 正対 1 + x 軸・y 軸まわりに ±``plane_tilt_deg``
の 4 + 対角の軸まわり ±tilt の 2。★これは **Fullseye の約束** で、VDI/VDE 2634 の図の写しではない
(考え方 = 体積を対角に貫く長さで尺度の誤差を見る、に沿っただけ)。
This 7+7 convention is Fullseye's own, modelled on the guideline's idea (span the volume
diagonally so a scale error shows up); it is not a copy of the normative figure.

``bar_length_mm`` の既定 = 7 方向のうち最も短い「体積を貫く長さ」の 0.8 倍から球の直径を引いた値。

返す ``dict``: ``kind`` = ``"acceptance_layout"``、``volume_mm``、``center_mm``、``sphere_diameter_mm``、
``bar_length_mm``、``probe``(``[{"center", "diameter"}]``)、``bars``(7 個の
``{"name", "center_a", "center_b", "length", "diameter", "direction"}``)、
``planes``(7 個の ``{"name", "center", "normal", "u", "v", "size"}``)。

**Raises** ``ValueError``: 寸法が正でない・非有限、``center_mm`` の z が体積の半分以下(センサの後ろに入る)、
球やダンベルや平面が体積からはみ出す、平面の傾きが [0, 60] 度の外。

## 詳しい使い方ガイド

- [optical_3d_acceptance ファミリ ガイド](../guides/optical_3d_acceptance.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_virtual_acceptance_3d](../../../../examples/poc_virtual_acceptance_3d.py) — `py -3.11 examples/poc_virtual_acceptance_3d.py`

## 型が繋がる次の op(`table` を入力に取れる)

[acceptance_verdict](../evaluate/acceptance_verdict.md) · [acceptance_scan](../simulate/acceptance_scan.md) · [virtual_acceptance_test](../simulate/virtual_acceptance_test.md) · [acceptance_error_budget](../budget/acceptance_error_budget.md)

## 同カテゴリ(`layout`)

—

---
*Provenance: acceptance3d.py — ACCEPTANCE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
