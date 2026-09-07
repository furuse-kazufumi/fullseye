---
op: shot_descriptor
dim: 3d
category: feature_register
in: points × normals
out: descriptor
examples: [feature_register]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# shot_descriptor — 3D `feature_register` op

- **データ種**: `points × normals` → `descriptor`
- **呼び出し**: `import fullseye as fs; fs.ledger.shot_descriptor(points, normals, kp_idx, tree, radius, n_azim=8, n_elev=2, n_rad=2, n_cos=11)` (実装を直接呼ぶなら `import feat_shot; feat_shot.shot_descriptor(points, normals, kp_idx, tree, radius, n_azim=8, n_elev=2, n_rad=2, n_cos=11)`、台帳から引くなら `ops3d.get("shot_descriptor")`)

## 使い方

SHOT 記述子(Tombari 2010)。各キーポイントに LRF を張り、球状支持を

径2×仰角2×方位8=32 空間セルに分割、各セルで「LRF z 軸と近傍点法線の
cos角」を n_cos=11 ビンのヒストグラムに quadrilinear 補間で蓄積 → 32×11=352
次元を L2 正規化。返り値 (Kp,352)。LRF 不能な点は零ベクトル。

Raises ValueError: normals の行数が points と一致しない場合(別点群の法線を
混ぜると近傍 index が範囲を越え生 IndexError になる — compute_fpfh と同クラス)。

引数: ``points`` (N,3)、``normals`` (N,3) 単位法線、``kp_idx`` はキーポイントの点
インデックス(``iss_keypoints`` の出力)、``tree`` は ``points`` から作った
``scipy.spatial.cKDTree``(呼び出し側で用意する)、``radius`` は支持半径(LRF 推定と
近傍集めの両方に使う)。``n_azim``・``n_elev``・``n_rad``・``n_cos`` を変えると次元は
``n_azim*n_elev*n_rad*n_cos`` になる。
手順: LRF は距離重み ``max(radius-d, 0)`` 付き共分散の固有ベクトル(x=最大、z=最小
固有値)を近傍多数派の符号に揃えて右手系化する。近傍が 5 点未満、または LRF が縮退した
キーポイントは零ベクトルのまま(マッチング側で除外される)。各近傍点は径・仰角
(``arccos(qz/r)/π``)・法線 cos 角をビン中心 0.5 基準で線形補間、方位は円環で wrap
して蓄積し、最後に行ごと L2 正規化する。返り値は float64 ``(len(kp_idx), 次元)``。
2 雲を比較するときは両側で同じ ``radius`` と同じ法線符号則を使うこと(法線の向きが
反転すると cos 角ヒストグラムが裏返る)。``register_shot`` がこの関数を両雲に適用し、
マッチングと RANSAC まで行う。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blas_threads_and_memory](../../math/guides/blas_threads_and_memory.md) — 行列分解が遅い理由の知識 — BLAS スレッド・キャッシュ・メモリ配置

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [feature_register](../../../../examples_3d/feature_register.py) — `py -3.11 examples_3d/feature_register.py`

## 型が繋がる次の op(`descriptor` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [shape_distance](../shape_descriptor/shape_distance.md)

## 同カテゴリ(`feature_register`)

[harris3d_keypoints](harris3d_keypoints.md) · [iss_keypoints](iss_keypoints.md) · [compute_fpfh](compute_fpfh.md) · [register_spin](register_spin.md) · [register_fpfh](register_fpfh.md) · [register_shot](register_shot.md)

---
*Provenance: feat_shot.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
