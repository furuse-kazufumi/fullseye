---
op: acceptance_scan
dim: acceptance
category: simulate
in: table × table
out: points
gpu: なし
examples: [poc_virtual_acceptance_3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# acceptance_scan — ACCEPTANCE `simulate` op

- **データ種**: `table × table` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.acceptance_scan(sensor, artifact, seed=0)` (実装を直接呼ぶなら `import acceptance3d; acceptance3d.acceptance_scan(sensor, artifact, seed=0)`、台帳から引くなら `opsacceptance.get("acceptance_scan")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

シミュレーションのセンサで 1 つの試験体を撮り、その点群 ``(N, 3)`` を返す(``points``)。

Scan one artefact (probe sphere, ball bar or plane from :func:`acceptance_layout`) with a simulated
sensor and return its points (N, 3) in the sensor frame, mm. For a ball bar the points of both
spheres are concatenated in the order a, b (use :func:`virtual_acceptance_test` for the split).

センサ(``sensor`` の ``kind``):
  * ``"ideal"`` —— 真の視線距離をそのまま返す(雑音なし)。往復の検算用。
  * ``"triangulation"`` —— 奥行き z に正規雑音 ``σ_z = z²·σ_d / (f·b)``(``z = f·b/d`` の誤差伝播、
    ``disparity_sigma_px`` = σ_d、``baseline_mm`` = b)。構造化光・ステレオの雑音則の代表で、縞を描いて
    復号するわけではない(限界)。
  * ``"itof"`` —— 既存の :func:`itof.itof_capture` → :func:`itof.itof_phase_amplitude` で 4 位相の生信号から
    距離を出す(ショット雑音・反射率・背景光・``supersample`` による縁の混合 = フライングピクセル・
    ``multipath_amplitude`` の 2 経路の多重反射)。多重反射は「全画素に一様な第 2 経路
    (余分な経路長 ``multipath_extra_mm``)」の最も粗いモデル。
校正の誤差は逆投影に入る: ``fx_rel_error``・``fy_rel_error``(相対)、``cx_error_px``・``cy_error_px``、
距離の尺度 ``range_scale`` とオフセット ``range_offset_mm``。真値は場面の解析解(光線と球・平面の交点)。

**Raises** ``ValueError``: センサの表に ``kind`` が無い(空の表は既定値で黙って走らせない)・鍵が未知・値が範囲外、試験体が配置の形でない、点が 10 点未満しか写らない。

## 詳しい使い方ガイド

- [optical_3d_acceptance ファミリ ガイド](../guides/optical_3d_acceptance.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_virtual_acceptance_3d](../../../../examples/poc_virtual_acceptance_3d.py) — `py -3.11 examples/poc_virtual_acceptance_3d.py`

## 型が繋がる次の op(`points` を入力に取れる)

[sphere_probing_error](../evaluate/sphere_probing_error.md) · [sphere_spacing_error](../evaluate/sphere_spacing_error.md) · [plane_flatness_error](../evaluate/plane_flatness_error.md)

## 同カテゴリ(`simulate`)

[virtual_acceptance_test](virtual_acceptance_test.md)

---
*Provenance: acceptance3d.py — ACCEPTANCE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
