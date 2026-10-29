---
op: fringe_ftp_phase
dim: 3d
category: structured_light
in: image2d
out: depth
examples: [ftp_and_focus_depth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# fringe_ftp_phase — 3D `structured_light` op

- **データ種**: `image2d` → `depth`
- **呼び出し**: `import fullseye as fs; fs.ledger.fringe_ftp_phase(image, carrier_axis='x', carrier_period=None, bandwidth=0.35, k=1.0, min_modulation=0.05, return_info=False)` (実装を直接呼ぶなら `import fringe; fringe.fringe_ftp_phase(image, carrier_axis='x', carrier_period=None, bandwidth=0.35, k=1.0, min_modulation=0.05, return_info=False)`、台帳から引くなら `ops3d.get("fringe_ftp_phase")`)
- **台帳経由の戻り値**: `fullseye.ledger.fringe_ftp_phase(...)` は**宣言 out 型 `depth` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.fringe_ftp_phase.raw(...)`、または `fringe.fringe_ftp_phase` を直接呼ぶ。

## 使い方

縞 1 枚から高さ・位相を Takeda の Fourier transform profilometry で復元する。

2-D FFT の直流から離れた片側一次スペクトルを窓で抜き、複素解析信号へ戻して
位相を展開し、搬送波の線形ランプを除く。``carrier_axis`` は位相が増える方向
(``"x"``=列、``"y"``=行)。``carrier_period`` は画素単位で、省略時は指定軸の
正周波数側にある最大ピークから推定する。``bandwidth`` は搬送周波数に対する
Gaussian 窓の標準偏差の比(0 < bandwidth < 1)。``k`` は rad から高さへの係数。

返り値は通常 ``height``。``return_info=True`` なら ``(height, info)`` となり、
``info`` は搬送波を除いた ``phase``、実際に使った
``carrier_period``、``carrier_frequency``、``estimated_carrier``、解析信号の
``modulation`` を持つ。高さは既存の ``phase_to_height(phase, 0, k)`` で作る。

業務上の言い方では「縞 1 枚から高さ」「1枚の縞画像から位相」を求める op。

1 枚で済む代わりに、対象位相の空間帯域が搬送波と直流/反対側サイドバンドの間に
収まる必要がある。急な高さ、段差、オクルージョンでは帯域重なりと Itoh 条件違反で
誤る。3 枚以上を撮れて広い帯域や低い搬送波を扱うなら ``decode_fringe`` の位相
シフト法を使う。一定画像や、抽出した変調振幅が画像の動的範囲に対して小さすぎる
画像は丸め誤差から位相を作らず ``ValueError`` にする。

出典: M. Takeda, H. Ina and S. Kobayashi, “Fourier-transform method of
fringe-pattern analysis for computer-based topography and interferometry,”
J. Opt. Soc. Am. 72(1), 156–160 (1982), doi:10.1364/JOSA.72.000156.

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ftp_and_focus_depth](../../../../examples_3d/ftp_and_focus_depth.py) — `py -3.11 examples_3d/ftp_and_focus_depth.py`

## 型が繋がる次の op(`depth` を入力に取れる)

[depth_to_points](../transform/depth_to_points.md) · [tsdf_from_depth](../transform/tsdf_from_depth.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [depth_to_organized_points](../range_image/depth_to_organized_points.md) · [normals_from_depth](../range_image/normals_from_depth.md) · [occlusion_edges](../range_image/occlusion_edges.md) · [bearing_angle_image](../range_image/bearing_angle_image.md)

## 同カテゴリ(`structured_light`)

[wrapped_phase](wrapped_phase.md) · [unwrap_phase_2d](unwrap_phase_2d.md) · [graycode_decode](graycode_decode.md) · [decode_fringe](decode_fringe.md) · [depth_from_focus](depth_from_focus.md) · [synthesize_fringes](synthesize_fringes.md) · [absolute_phase](absolute_phase.md) · [triangulate_column](triangulate_column.md)

---
*Provenance: fringe.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
