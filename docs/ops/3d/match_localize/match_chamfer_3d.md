---
op: match_chamfer_3d
dim: 3d
category: match_localize
in: voxel × voxel
out: position
gpu: true
examples: [matching_localize]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# match_chamfer_3d — 3D `match_localize` op

- **データ種**: `voxel × voxel` → `position`
- **呼び出し**: `import fullseye as fs; fs.ledger.match_chamfer_3d(scene, template, device='cpu', thr=0.3, edt='scipy')` (実装を直接呼ぶなら `import match3d; match3d.match_chamfer_3d(scene, template, device='cpu', thr=0.3, edt='scipy')`、台帳から引くなら `ops3d.get("match_chamfer_3d")`)
- **台帳経由の戻り値**: `fullseye.ledger.match_chamfer_3d(...)` は**宣言 out 型 `position` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.match_chamfer_3d.raw(...)`、または `match3d.match_chamfer_3d` を直接呼ぶ。
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

chamfer / 距離場マッチング(部分・遮蔽に頑健)。voxel × chamfer 列。

シーンのエッジの EDT(各 voxel から最近エッジまでの距離)に、テンプレのエッジ点を載せて
距離和を最小化。score(pos)=Σ_{template edge} DT_scene(pos+edge)/n。**低いほど良い一致**。
エッジ点の一部が欠けても効く(NCC より遮蔽に強い)。相関(conv3d)は常に GPU。距離場は
edt="scipy"(CPU、既定)か edt="jfa"(`edt_jfa`、全 GPU で CPU 往復なし。scipy と厳密一致)。
返り値 [chamfer 距離, d, h, w]。

手順: 両 volume で ``|∇| > thr·max|∇|`` の voxel をエッジにする(``thr`` は各 volume の最大
勾配に対する **相対比**、勾配は ``sobel3d``)。scene エッジの距離変換 DT を作り、テンプレの
エッジ 2 値 volume をカーネルに conv3d した値をエッジ数 ``n`` で割る。
返り値 ``[距離, z, y, x]`` の距離は「テンプレのエッジ 1 voxel あたり、最寄り scene エッジまでの
平均距離(voxel 単位)」で 0 が完全一致。位置は **テンプレ中心 (T//2)** の scene 座標で
**整数**(subvoxel 精緻化は無い。要るなら ``refine_translation_lk`` へ。corner 規約なので
T//2 を引く)。テンプレが完全に収まらない位置は最大値+1 で埋めて除外する。
テンプレにエッジが無い(``thr`` が高すぎる等)と score が全 0 になり index (0,0,0) が返る。
scene にエッジが無い場合の距離場は意味を持たない(``thr`` を下げる)。
``edt="jfa"`` は ``edt_jfa`` を使い ``device`` 上で完結、それ以外は scipy(CPU)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [matching_localize](../../../../examples_3d/matching_localize.py) — `py -3.11 examples_3d/matching_localize.py`

## 型が繋がる次の op(`position` を入力に取れる)

[refine_peak_newton](../refine/refine_peak_newton.md) · [refine_translation_lk](../refine/refine_translation_lk.md) · [refine_lm](../refine/refine_lm.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`match_localize`)

[match_shape_3d](match_shape_3d.md) · [match_curvature_3d](match_curvature_3d.md) · [match_hough_3d](match_hough_3d.md) · [match_mip_2d](match_mip_2d.md) · [match_points_ncc](match_points_ncc.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
