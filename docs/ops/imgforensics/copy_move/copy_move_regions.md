---
op: copy_move_regions
dim: imgforensics
category: copy_move
in: image2d
out: table
examples: [image_forensics_audit]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# copy_move_regions — IMGFORENSICS `copy_move` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import imgforensics; imgforensics.copy_move_regions(image, method: 'str' = 'keypoint', min_matches: 'int' = 4, min_offset: 'float' = 16.0, offset_tol: 'float' = 2.0, ratio: 'float' = 0.6, patch: 'int' = 11, block: 'int' = 8, step: 'int' = 1, n_dct: 'int' = 10, min_variance: 'float' = 0.0001, max_feature_dist: 'float' = 0.02, neighbours: 'int' = 2, ransac_thresh: 'float' = 3.0, ransac_iters: 'int' = 300, seed: 'int' = 0) -> 'list'` (または `opsimgforensics.get("copy_move_regions")`)

## 使い方

1 枚の画像の中の **コピー&ムーブ**(自己複製)領域の対を返す。``table``。

``method="keypoint"``(既定)
    :func:`features.harris_corners` でコーナーを取り、
    :func:`features.describe_patches` で正規化パッチ記述子を作り、
    **自分から ``min_offset`` px 以上離れた**最近傍と Lowe の比率検定で対応を作る
    (:func:`_self_match`)。対応をシフトベクトルで束ね、群ごとに
    :func:`mosaic.proj_match_points_ransac` で幾何整合を確認する。
    相似変換は :func:`fit_transform.vector_to_similarity`(Umeyama)で当てて
    ``similarity`` に入れる。

``method="block"``
    Fridrich, Soukal & Lukáš 2003。``block`` 角の重なりブロックを ``step`` px
    刻みで取り(既定 ``step=1`` —— **これは飾りではない**。下の「歩幅」参照)、
    各ブロックの DCT 低周波 ``n_dct`` 係数を特徴にして辞書順に並べ、
    辞書順で近い ``neighbours`` 件までを候補にし、特徴距離が
    ``max_feature_dist`` 以下のものだけをシフトベクトルで数える。
    回転・拡大には効かないが、角の少ない画像で keypoint 法より拾える。
    分散が ``min_variance`` 未満のブロックは捨てる(**一様な空を空にコピーしても
    同じ特徴になる** = 検出器が必ず作る偽陽性の主因)。

**歩幅 (``step``) を 1 にしてある理由(実測で決めた)**: ブロック法が「同じ特徴」を
見つけられるのは、複製元と複製先が **同じ格子に乗ったとき**だけである。
``step=4`` にすると、シフトが 4 の倍数でない複製(たとえば ``(110, 128)``)は
**原理的に一度も一致しない**。実測で ``step=4`` は真のシフトを 1 件も返さず、
代わりに偽の群を 60 件返した。``step=1`` なら真のシフトが第 1 群に来る。
大きい画像で重いときは ``step`` を上げてよいが、**上げた歩幅の倍数のシフト
しか見つからなくなる**ことを承知の上で上げること。

返りは領域対の list(対応数の多い順)。各要素:

``offset``       シフト ``(dy, dx)``(row, col)。向きは **位置で正規化**してある
                 (辞書順で正になる向き)—— 添字で決めると同じ複製が
                 ``(110, 128)`` にも ``(-110, -128)`` にもなる(実測して直した)
``n_matches``    その群の対応数
``n_inliers``    RANSAC の内点数(``method="block"`` では ``n_matches`` と同じ)
``inlier_ratio`` 内点率
``src_bbox`` / ``dst_bbox``  ``(r0, c0, r1, c1)``
``src_points`` / ``dst_points``  ``(N, 2)`` の (row, col)
``similarity``   Umeyama で当てた ``3x3``(``method="keypoint"`` のみ、なければ ``None``)
``method``       使った方法
``caveats``      この結果が言えないこと

**正解が手元にあるので当てられることを数で固定してある**
(``tests/test_imgforensics.py::test_copy_move_finds_the_known_offset``、
256x256 のテクスチャ画像の ``(40, 32)`` にある 64x64 を ``(150, 160)`` へ複製 =
真のシフト ``(110, 128)``):

============ ================= ============ ========= ==============
method       第 1 群の offset  n_matches    群の数    誤差
============ ================= ============ ========= ==============
keypoint     (110.0, 128.0)    15           1         0 px
block        (110.0, 128.0)    3249         1         0 px
============ ================= ============ ========= ==============

**偽陽性も測ってある**: 改竄していない同じ種類の画像 3 枚では、
keypoint 法・block 法とも群 **0 件**(seed 4/5/6)。

**言えないこと**(すべて同じテストで測ってある):

* 一様な領域(空・壁)は複製しなくても同じ特徴になる。上半分を一様な「空」に
  した(**改竄していない**)画像で、``min_variance=1e-4`` と ``1e-6`` はどちらも
  0 件だが、``min_variance=0`` にすると **264 対の偽の群が 1 件**出る
  (シフト ``(1, -247)`` = 空の中の適当な対応)。
* ``method="keypoint"`` は正規化パッチ記述子なので **回転に効かない**。
  複製を回して貼ると群の数は 0 度 1 件 → **5 度 0 件** → 15 度 0 件 → 30 度 0 件。
  ``similarity`` に回転が入って返ることは実質ない。
* ``method="block"`` も **回転にまったく効かない**(5 度で 0 件)。
* 検出ゼロ = 複製が無い、ではない。再圧縮を挟んだ複製は特徴距離が伸びて
  ``max_feature_dist`` を超える。実測(同じ複製画像を JPEG に通してから検出):

  ========== ============================ ==========================
  品質       keypoint 第 1 群の n_matches  block 第 1 群の n_matches
  ========== ============================ ==========================
  無圧縮     15                           3249
  95         10                           138
  85          7                           10
  75          7                           **0 件(群なし)**
  ========== ============================ ==========================

  シフトはどの品質でも ``(110.0, 128.0)`` のまま正しい。**壊れるのは
  「見つかるかどうか」で、見つかったときの答えではない**。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_forensics_audit](../../../../examples/image_forensics_audit.py) — `py -3.11 examples/image_forensics_audit.py`

## 型が繋がる次の op(`table` を入力に取れる)

[evidence_quantile](../calibration/evidence_quantile.md)

## 同カテゴリ(`copy_move`)

—

---
*Provenance: imgforensics.py — IMGFORENSICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
