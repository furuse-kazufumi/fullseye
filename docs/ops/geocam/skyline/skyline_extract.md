---
op: skyline_extract
dim: geocam
category: skyline
in: image2d
out: signal
examples: [poc_public_camera_heading]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# skyline_extract — GEOCAM `skyline` op

- **データ種**: `image2d` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.skyline_extract(image, sky_is_bright=True, smooth=1.5, max_jump=3, jump_penalty=0.5)` (実装を直接呼ぶなら `import geocam; geocam.skyline_extract(image, sky_is_bright=True, smooth=1.5, max_jump=3, jump_penalty=0.5)`、台帳から引くなら `opsgeocam.get("skyline_extract")`)

## 使い方

写真から**列ごとの空と地形の境界の行**を動的計画法で 1 本抜く → signal (W,)。

Lie・Lin・Hsu 2005(*Pattern Recognition*: 航法のための頑健なスカイライン抽出)と同じ考え:
垂直方向の明るさの変化(空が上で明るければ ``I[v−1] − I[v+1]`` が正)を「境界らしさ」にし、
隣の列から行が ``max_jump`` 以上飛ばない連続な経路のうちコストが最小のものを選ぶ
(``jump_penalty`` × 行の飛び)。雲や建物の縦の縁で局所的に強い応答が出ても、経路の
連続性が本物の稜線を残す。

Args:
    image: (H, W) float。RGB なら先に灰色にする。
    sky_is_bright: 空が地形より明るい(昼)。夜景・逆光で反転するなら False。
    smooth: 縦方向の Gaussian σ [画素] (雑音)。0 で無効。
    max_jump: 隣の列で許す行の飛び [画素]。
    jump_penalty: 飛び 1 画素あたりのコスト(境界らしさは 0〜1 に正規化してある)。
Returns:
    signal (W,) float: 列ごとの境界の行(0 が最上段)。**空しか写っていない・地形しか
    写っていない**画像では境界の応答が弱く、経路の平均コストが 0 に近いので ValueError
    で止める(黙って雑音の線を返さない)。

## 詳しい使い方ガイド

- [geocam ファミリ ガイド](../guides/geocam.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_public_camera_heading](../../../../examples/poc_public_camera_heading.py) — `py -3.11 examples/poc_public_camera_heading.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[sun_position](../sun/sun_position.md) · [camera_orientation_from_sun](../sun/camera_orientation_from_sun.md) · [camera_orientation_from_sun_candidates](../sun/camera_orientation_from_sun_candidates.md) · [camera_orientation_from_skyline](../orientation/camera_orientation_from_skyline.md)

## 同カテゴリ(`skyline`)

[dem_skyline](dem_skyline.md) · [render_skyline_view](render_skyline_view.md)

---
*Provenance: geocam.py — GEOCAM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
