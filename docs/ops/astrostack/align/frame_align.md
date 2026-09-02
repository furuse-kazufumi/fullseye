---
op: frame_align
dim: astrostack
category: align
in: image2d × image2d
out: matrix
examples: [astro_stacking]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# frame_align — ASTROSTACK `align` op

- **データ種**: `image2d × image2d` → `matrix`
- **呼び出し**: `import astrostack; astrostack.frame_align(reference, frame, model='similarity', threshold_sigma=5.0, max_stars=60, tolerance_px=2.0, max_shift_px=None, ransac_iters=500, seed=0, min_inliers=3)` (または `opsastrostack.get("frame_align")`)

## 使い方

星の対応から ``frame`` → ``reference`` の 2-D 変換を推定する。

工程は 3 段で、**推定の本体はどれも既存 op**:

1. :func:`star_detect` で両方の星を取る。
2. 粗い平行移動を**オフセット投票**で出す(``_vote_translation``)。
   ここで :func:`features.match_keypoints` を使わないのは実測に基づく判断で、
   星野の 9x9 パッチは互いにほとんど同じ形なので Lowe の比検定
   (既定 ratio=0.8)がほぼ全部を捨てる。128x128 に 40 星、真のずれが
   ``(+0.590, -0.540)`` px のフレーム対での実測: ``match_keypoints`` が
   返した対応は **4 件、うち真値から 1 px 以内は 0 件**(= 使えるものが
   1 つも無い)。同じ対で投票法は **26 票 → 26 対応 → 26 内点**、推定誤差
   **0.0155 px**。星野は「特徴が無い」のではなく「特徴が全部同じ」なので、
   記述子ではなく**配置の幾何**を使うのが正しい。
3. 粗い移動で最近傍の対応を作り、
   :func:`mosaic.proj_match_points_ransac` で誤対応を落とし、
   :func:`fit_transform.vector_to_similarity`(``model`` に応じて
   ``vector_to_rigid`` / ``vector_to_hom_mat2d``)で当てはめる。
   RANSAC ループも Umeyama もここには書いていない。

*model* ``"translation"`` は対応の差の中央値だけを使う(星が 1 個でも動く)。
``"rigid"`` = 回転 + 並進、``"similarity"`` = + 等方スケール、
``"affine"`` = 6 自由度。**視野が広くなければ ``"similarity"`` で足りる**
(赤道儀の追尾誤差は回転と並進、大気差はスケールに一次で乗る)。

Returns ``(matrix, info)``:

* ``matrix`` —— ``(3, 3)`` float64。``(row, col, 1)`` に左から掛けると
  ``reference`` の座標になる(``fit_transform`` と同じ規約)。
* ``info`` —— dict。``n_stars_ref`` / ``n_stars_src`` / ``n_pairs`` /
  ``n_inliers`` / ``inlier_ratio`` / ``shift_row`` / ``shift_col`` /
  ``rotation_deg`` / ``scale`` / ``rms_px``(内点の残差 RMS)/ ``model``。

**fail-closed**: 内点が *min_inliers* に満たなければ ``ValueError`` を送出
する。**恒等変換を黙って返さない** —— 位置合わせに失敗したフレームを
「ずれ 0」として合成に混ぜると、例外も警告も無しに二重像ができる。

**Raises** ``ValueError``: 2-D でない / 形が違う / *model* が
:data:`ALIGN_MODELS` にない / どちらかで星が 1 つも見つからない /
対応が作れない / 内点が足りない場合。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [astro_stacking](../../../../examples/astro_stacking.py) — `py -3.11 examples/astro_stacking.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

—

## 同カテゴリ(`align`)

[align_frames](align_frames.md)

---
*Provenance: astrostack.py — ASTROSTACK operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
