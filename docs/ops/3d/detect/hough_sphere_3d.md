---
op: hough_sphere_3d
dim: 3d
category: detect
in: voxel
out: primitive
gpu: true
examples: [detect_primitives_3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# hough_sphere_3d — 3D `detect` op

- **データ種**: `voxel` → `primitive`
- **呼び出し**: `import fullseye as fs; fs.ledger.hough_sphere_3d(vol, device='cpu', radii=None, mc=0.0, iso=0.5, subvoxel=True)` (実装を直接呼ぶなら `import match3d; match3d.hough_sphere_3d(vol, device='cpu', radii=None, mc=0.0, iso=0.5, subvoxel=True)`、台帳から引くなら `ops3d.get("hough_sphere_3d")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

球検出(2D Hough 円の 3D リフト)。中心 = p + sgn·r·n を半径 r ごとに投票。

薄い境界面の各 voxel が法線 n に沿って中心へ投票(符号は明/暗どちらの球でも拾えるよう両方試す)。
半径ごとの中心ピーク投票の最大 = 検出球。votes-vs-radius を放物線補間で sub-voxel 半径。
産業: ボール・球状部品・点群中の球面。返り値 (votes, radius, center(3,))。

手順: ``(vol > iso)`` の 1 voxel 厚の境界面 voxel ``p`` とその単位法線 ``n``(``sobel3d``、
``mc`` は生出力への閾値)から、半径 ``r`` ごとに ``c = round(p ± r·n)`` へ投票し(± は明球・
暗球の両方を試し、多い方を採る)、volume 内に落ちた票の最大値をその r のスコアにする。全 r で
最大のものが検出球。
- ``radii``: 試す半径(voxel 単位)の列。None なら ``range(4, 16)``(4〜15)。``subvoxel=True``
は最良 r の **両隣 r±1 が radii に含まれるとき**だけ votes の放物線補間で半径を ±1 以内に
精緻化する(端の r や飛び飛びの radii では整数のまま)。
- 返り値 ``(votes, radius, center)``: votes は票数(境界 voxel 数が上限)、radius は float、
center は **整数 (z,y,x) の tuple**(中心は精緻化しない)。
- 境界 voxel が 10 未満なら **None**。``radii`` が空だと TypeError で落ちる。
- 1 個しか返さない。複数球は検出した球の voxel を消して再実行するか、点群なら
``ransac_sphere`` / ``fit_sphere_3d``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [detect_primitives_3d](../../../../examples_3d/detect_primitives_3d.py) — `py -3.11 examples_3d/detect_primitives_3d.py`

## 型が繋がる次の op(`primitive` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [angle_between_lines](../geometry/angle_between_lines.md) · [angle_between_planes](../geometry/angle_between_planes.md) · [angle_line_plane](../geometry/angle_line_plane.md) · [distance_point_plane](../geometry/distance_point_plane.md) · [distance_point_line](../geometry/distance_point_line.md) · [distance_line_line](../geometry/distance_line_line.md) · [intersect_line_plane](../geometry/intersect_line_plane.md)

## 同カテゴリ(`detect`)

[hough_plane_3d](hough_plane_3d.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
