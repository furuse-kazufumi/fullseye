---
op: segment_rigid_motions
dim: 3d
category: motion_segment
in: points × points
out: labels
examples: [motion_seg]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# segment_rigid_motions — 3D `motion_segment` op

- **データ種**: `points × points` → `labels`
- **呼び出し**: `import motion_seg3d; motion_seg3d.segment_rigid_motions(pts0, pts1, thresh, max_bodies: 'int' = 5, min_inliers=None, n_iter: 'int' = 100, k_sample: 'int' = 6, seed: 'int' = 0) -> 'dict'` (または `ops3d.get("segment_rigid_motions")`)

## 使い方

2 点群を運動が一致する剛体ごとに分割する(反復 RANSAC による multi-body 分割)。

まず :func:`estimate_flow` で観測フロー(各 pts0 点 -> pts1 最近傍)を取り、
``target = pts0 + flow`` を対応先として固定する。以後、残り点集合に対して:

  1. 空間的に近い ``k_sample`` 点(seed + その最近傍)を種に Kabsch で剛体仮説を立て、
  2. フロー整合 ``|| (R·s + t) - target(s) || < thresh`` を満たす inlier を数え、
  3. ``n_iter`` 試行で **有意性ゲートを満たす** 最良仮説を選び(inlier 残差中央値が
     ``thresh`` の一定割合未満 = 真の剛体らしく残差が 0 近傍に集中。無相関/ノイズの
     偶然適合は許容球を満たし残差 ≈ 0.6*thresh なので弾かれる)、その inlier で Kabsch
     再フィット(refine)、
  4. inlier 数が ``min_inliers`` 以上 **かつ** refine 後も有意性を保つならそれを 1 剛体
     として確定・除去。満たさなければ body を作らず残余は -1 のまま終了(偽の剛体を捏造
     しない)。

を ``max_bodies`` 個または残り点が閾値を下回るまで繰り返す。どの剛体にも属さない残り点は
``labels = -1``(outlier / 未対応、詐称しない)。近傍種サンプリングは空間的に連続な物体を
まとめて掴むための locality prior で、閾値ではなく相対順位だけを使うためスケール不変。

Args:
    pts0: (N, 3) 時刻 0 の点群。
    pts1: (M, 3) 時刻 1 の点群(N と一致不要)。
    thresh: フロー整合の inlier 距離しきい値。**座標スケール相対**で与えること
        (絶対 epsilon をモジュール内に持たないため、呼び手が座標系に合わせる)。
    max_bodies: 抽出する剛体数の上限(>= 1)。
    min_inliers: 1 剛体と認める最小 inlier 数。None なら ``max(3, round(0.1*N))``。
        outlier の塊を偽の剛体にしないための下限。
    n_iter: 剛体 1 個あたりの RANSAC 試行回数。
    k_sample: 1 仮説を作る種サンプルの点数(seed + 最近傍、>= 3)。
    seed: RANSAC 乱数シード(再現性)。
Returns:
    dict: ``{"labels": (N,) int(各点の剛体 id、0..K-1 / outlier=-1),
    "motions": [(R, t), ...] (id 順の剛体変換、K 個)}``。
Raises:
    ValueError: 形状不正 / 非有限 / pts1 空 / thresh <= 0 / max_bodies < 1 /
        k_sample < 3。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [motion_seg](../../../../examples_3d/motion_seg.py) — `py -3.11 examples_3d/motion_seg.py`

## 型が繋がる次の op(`labels` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [vol_region_props](../regionprops/vol_region_props.md)

## 同カテゴリ(`motion_segment`)

[estimate_flow](estimate_flow.md) · [fit_rigid](fit_rigid.md)

---
*Provenance: motion_seg3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
