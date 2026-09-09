---
op: normals_from_depth
dim: 3d
category: range_image
in: depth
out: normalmap
examples: [range_image]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# normals_from_depth — 3D `range_image` op

- **データ種**: `depth` → `normalmap`
- **呼び出し**: `import fullseye as fs; fs.ledger.normals_from_depth(depth, fx=None, fy=None, cx=None, cy=None, orient_to_camera=True, spacing=None)` (実装を直接呼ぶなら `import range_image; range_image.normals_from_depth(depth, fx=None, fy=None, cx=None, cy=None, orient_to_camera=True, spacing=None)`、台帳から引くなら `ops3d.get("normals_from_depth")`)

## 使い方

organized 深度 → 向き付き単位法線 (H,W,3)。隣接画素の 3D 点の外積(格子構造を利用、O(HW))。

fx,fy 指定で透視、未指定で正射。orient_to_camera=True で法線をカメラ(原点)向きに符号統一。

★**同名の別関数が 1 行ファサードにある**。``fullseye.normals_from_depth`` は
``(depth, K, smooth=0)`` の**透視版で K が必須**、こちら(``fullseye.ledger``
経由 = ``range_image``)は K を取らない正射版。片方の呼び方を覚えると、もう
片方で ``TypeError`` になる(2026-09-08 実測)。

★``spacing=(dy, dx)`` は**正射モードでの画素の実寸**。既定 ``None`` は
「1 画素 = 1 単位」で、**異方な格子(例: 列 0.05 mm × 行 0.5 mm)をそのまま
渡すと傾きが黙ってずれる** —— 実測で x 成分が 20 倍(= 1/dx 倍)外れ、例外も
警告も出なかった。実寸が分かっているなら必ず渡すこと。透視モード
(``fx``/``fy`` 指定)では焦点距離が実寸を決めるので無視される。
★``spacing`` を渡すときは **``orient_to_camera=False``** にすること。正射での
「カメラ」は原点(左上・深度 0)という便宜的なもので、実寸を入れると面に対する
その位置が変わり、**符号が反転しうる**(実測: 傾き 0.1 の平面で
``orient_to_camera=False`` なら真値 x=-0.0995 と一致、``True`` では +0.0995)。
向きが要るなら、視線が定義できる座標系で後段で揃える。

法線は隣接画素の外積で出すため両軸に近傍が要る。H<2 or W<2 は第2の接線方向が無く
法線が定義できない(その軸の勾配を 0 とみなすと cross(dPx,0)=[0,0,0] の縮退法線を
静かに返してしまう)。fail-closed で明示的に ValueError 拒否する。

計算は ``depth_to_organized_points`` で 3-D 点 ``P`` を作り、``np.gradient`` の列方向
差分 ``dPx`` と行方向差分 ``dPy`` の外積 ``dPx × dPy`` を単位長にする(端は片側差分)。
``orient_to_camera=True`` では ``n·(-P) < 0`` の画素を反転し、法線が原点(カメラ)を向く
よう揃える。正射モード(``fx`` か ``fy`` が None)では ``P=(u,v,d)`` なので原点は画像
左上の深度 0 の位置になり、「カメラ向き」の意味が透視モードと異なる点に注意。``cx``・
``cy`` 省略時は画像中心。深度の段差(遮蔽エッジ)をまたぐ画素では外積が段差の向きを
拾って法線が壊れるので、``occlusion_edges`` で境界画素を除いてから使う。深度 0 / NaN の
画素は検証せず、法線も不定になる。返り値は float32 の ``(H,W,3)``。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)
- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [range_image](../../../../examples_3d/range_image.py) — `py -3.11 examples_3d/range_image.py`

## 型が繋がる次の op(`normalmap` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [render_shaded](../render/render_shaded.md) · [phong_shade](../render/phong_shade.md) · [matcap_shade](../render/matcap_shade.md) · [brdf_lommel_seeliger](../render/brdf_lommel_seeliger.md) · [brdf_hapke](../render/brdf_hapke.md) · [bump_normals_fbm](../terrain/bump_normals_fbm.md) · [integrate_normals](../photometric/integrate_normals.md)

## 同カテゴリ(`range_image`)

[depth_to_organized_points](depth_to_organized_points.md) · [occlusion_edges](occlusion_edges.md) · [bearing_angle_image](bearing_angle_image.md)

---
*Provenance: range_image.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
