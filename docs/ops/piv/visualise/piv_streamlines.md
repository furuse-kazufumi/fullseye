---
op: piv_streamlines
dim: piv
category: visualise
in: flow2d
out: table
examples: [piv_field_analysis_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# piv_streamlines — PIV `visualise` op

- **データ種**: `flow2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.piv_streamlines(flow, seeds=None, separation=None, step=0.25, max_length=None, min_speed=0.001, test_ratio=0.5)` (実装を直接呼ぶなら `import pivops; pivops.piv_streamlines(flow, seeds=None, separation=None, step=0.25, max_length=None, min_speed=0.001, test_ratio=0.5)`、台帳から引くなら `opspiv.get("piv_streamlines")`)

## 使い方

流線を RK4 でたどる(MATLAB の ``stream2`` / ``streamslice`` に当たる)。

``seeds`` を省くと **Jobard–Lefer(1997)の等間隔配置**で種を自動で置く。
流線どうしが ``separation`` 程度の間隔で並び、``test_ratio * separation``
より近づいた所で打ち切る。矢印図は密にすると潰れ、種を手で置くと空白が
残るが、この配置は**空白も重なりも作らない**(下の 2 つの性質を門にしている)。

* 別々の流線の標本点どうしは ``test_ratio * separation`` より近づかない。
* 速さが ``min_speed`` 以上の格子点はどれも、どこかの流線から
  ``separation`` 以内にある(取りこぼしの無さ)。

座標は flow の格子(行 0 が上、``(row, col)``)。向きの場は速さで割って
**弧長で進む**ので、1 歩は ``step`` 格子。速さは流線上の各点で別に返す。

Args:
    flow: ``(2, h, w)``(``dy, dx``)。
    seeds: ``(n, 2)`` の ``(row, col)``。``None`` で自動配置。
    separation: 流線の間隔 [格子]。``None`` で ``max(h, w) / 25``(2 以上)。
    step: RK4 の 1 歩 [格子]。
    max_length: 片方向の最大の長さ [格子]。``None`` で ``4 * (h + w)``。
    min_speed: これより遅い所で止める(**最大の速さに対する比**)。
    test_ratio: 打ち切りの距離を ``separation`` の何倍にするか(0 < x ≤ 1)。
Returns:
    dict(table): ``paths``(``(m_i, 2)`` の list、上流 → 下流の順)、
    ``speed``(各点の速さの list)、``seeds``、``stop``(``(後ろ, 前)`` の
    理由の組の list)、``n``、``separation``、``d_test``、``step``、
    ``stop_counts``(理由ごとの数)。
Raises:
    ValueError: flow の形・非有限、パラメータ範囲外、種が格子の外。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [piv_field_analysis_tour](../../../../examples/piv_field_analysis_tour.py) — `py -3.11 examples/piv_field_analysis_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`visualise`)

[piv_flow_to_rgbimage](piv_flow_to_rgbimage.md) · [piv_line_integral_convolution](piv_line_integral_convolution.md) · [piv_quiver](piv_quiver.md) · [piv_streamline_image](piv_streamline_image.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
