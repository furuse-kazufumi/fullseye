---
op: frame_align
dim: astrostack
category: align
in: image2d × image2d
out: matrix
examples: [astro_stacking, poc_exoplanet_transit, poc_print_registration]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# frame_align — ASTROSTACK `align` op

- **データ種**: `image2d × image2d` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.frame_align(reference, frame, model='similarity', threshold_sigma=5.0, max_stars=60, tolerance_px=2.0, max_shift_px=None, ransac_iters=500, seed=0, min_inliers=3)` (実装を直接呼ぶなら `import astrostack; astrostack.frame_align(reference, frame, model='similarity', threshold_sigma=5.0, max_stars=60, tolerance_px=2.0, max_shift_px=None, ransac_iters=500, seed=0, min_inliers=3)`、台帳から引くなら `opsastrostack.get("frame_align")`)
- **台帳経由の戻り値**: `fullseye.ledger.frame_align(...)` は**宣言 out 型 `matrix` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.frame_align.raw(...)`、または `astrostack.frame_align` を直接呼ぶ。
  - 本体の返り: `(matrix, info) -> matrix`

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

★**繰り返し構造には使えない**(2026-09-08、`poc_print_registration` が発見)。
``inlier_ratio`` は「同じ答えに賛成した対応の割合」であって「答えが正しい
確率」ではない。網点・織物・格子のように**同じ形が周期的に並ぶ**画像では、
格子ベクトルぶんずれた対応づけも全員が賛成するので、賛成率は 1.00 のまま
答えだけが格子 1 個ぶん(あるいは何個ぶんも)ずれる。

実測: 256x256 の 133 lpi 相当・15 度の網点を **(0.00, +1.30) px** だけ
ずらした対で、``inlier_ratio`` **1.00** / ``rms_px`` 0.78 を返しながら
推定は **(+54.24, +30.12) px**。星野(128x128、40 星、真値
(+0.59, -0.54))では ``inlier_ratio`` は同じ 1.00 で推定は正しい。
**賛成率では 2 つを区別できない**。

区別できるのは ``vote_margin`` —— 投票の**2 番手の山**の高さを 1 番手で
割った値で、0 なら山は 1 つ、1 に近いほど「同じくらいもっともらしい答えが
他にもある」。同じ 2 例で **網点 0.857 / 星野 0.143**。周期構造を渡す
かもしれない経路では、``inlier_ratio`` ではなくこちらを見ること。
平行移動そのものが要るだけなら :func:`piv_cross_correlate` の相関面を
見るほうが素直で、そちらは山が何本立っているかを自分で数えられる。

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
- [poc_exoplanet_transit](../../../../examples/poc_exoplanet_transit.py) — `py -3.11 examples/poc_exoplanet_transit.py`
- [poc_print_registration](../../../../examples/poc_print_registration.py) — `py -3.11 examples/poc_print_registration.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

—

## 同カテゴリ(`align`)

[align_frames](align_frames.md)

---
*Provenance: astrostack.py — ASTROSTACK operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
