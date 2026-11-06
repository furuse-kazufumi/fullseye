---
op: features_sift
dim: matchreg
category: featmatch
in: image2d
out: table
gpu: なし
examples: [poc_part_locate_features]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# features_sift — MATCHREG `featmatch` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.features_sift(image, n_octaves=None, n_scales=3, sigma=1.6, contrast_threshold=0.04, edge_threshold=10.0, max_features=2000, double_image=True)` (実装を直接呼ぶなら `import featmatch; featmatch.features_sift(image, n_octaves=None, n_scales=3, sigma=1.6, contrast_threshold=0.04, edge_threshold=10.0, max_features=2000, double_image=True)`、台帳から引くなら `opsmatchreg.get("features_sift")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

SIFT の特徴点と 128 次元の記述子(DoG の極値、Lowe 2004)。→ table(``kind="features"``)。

DoG(ガウスの差)のスケール空間で 3×3×3 の極値を探し、2 次の当てはめで副画素・副スケールへ
詰め、低コントラスト(``|D| * n_scales < contrast_threshold``、画像は [0, 1] の尺度)と稜線
(ヘッセ行列の固有値比が ``edge_threshold`` 超)を捨てる。向きは勾配の 36 ビンの山(最大の
0.8 倍以上の山ごとに 1 点、同じ位置に複数の向きが出る)、記述子は 4×4 のマス × 8 方向。

座標の約束: ``xy`` は原画像の **(x, y)** 画素(画素の中心が整数)。``double_image=True`` の
拡大は標本点 ``i/2`` の双線形なので、拡大後の座標の半分がちょうど原画像の座標になる
(OpenCV の拡大は画素中心の扱いが違い、点が約 0.25 px ずれる —— 位置を直接比べるときの注意)。

実測(256×256 の :func:`synthetic_scene`、``tests/test_featmatch.py`` が固定): 90 度回転の対で
ホモグラフィの 4 隅誤差 < 0.5 px、0.5 倍の縮小で < 1.5 px、OpenCV の SIFT(5.0)と同じ対で
4 隅誤差が同じ桁。

限界: 記述子の組み立てはキーポイントごとの Python ループ(2000 点で数秒)。アフィン不変では
ない(強い遠近では壊れる。:func:`features_accuracy_table` で条件ごとに測れる)。

Args:
    image: 2-D の濃淡画像(値の尺度は [0, 1] を想定。コントラストのしきい値がこの尺度)。
    n_octaves: オクターブ数。``None`` なら ``log2(min(H, W)) - 3``(最低 1)。
    n_scales: 1 オクターブあたりの尺度の数(Lowe の s、既定 3)。
    sigma: 土台の σ(既定 1.6)。原画像は σ=0.5 のぼけを持つと仮定する。
    contrast_threshold: 低コントラストを捨てるしきい値(既定 0.04)。
    edge_threshold: 稜線を捨てる固有値比 r(既定 10)。
    max_features: 応答の強い順に残す上限。
    double_image: 最初に 2 倍へ拡大するか(既定 True、小さな特徴が拾える)。

Returns:
    dict(``kind="features"``, ``detector="sift"``)。``xy`` (N,2) / ``scale`` (N,) [px] /
    ``angle`` (N,) [度] / ``response`` (N,) / ``octave`` (N,) / ``descriptors`` (N,128) float32 /
    ``descriptor_kind="float"`` / ``image_shape``。

Raises:
    ValueError: 2-D でない / 16 px 未満 / 非有限 / 定数画像 / 引数が値域外。

## 詳しい使い方ガイド

- [matching_registration ファミリ ガイド](../guides/matching_registration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_part_locate_features](../../../../examples/poc_part_locate_features.py) — `py -3.11 examples/poc_part_locate_features.py`

## 型が繋がる次の op(`table` を入力に取れる)

[features_match](features_match.md) · [ransac_homography](ransac_homography.md) · [ransac_fundamental](ransac_fundamental.md) · [registration_to_flow2d](../intensityreg/registration_to_flow2d.md)

## 同カテゴリ(`featmatch`)

[features_orb](features_orb.md) · [features_match](features_match.md) · [ransac_homography](ransac_homography.md) · [ransac_fundamental](ransac_fundamental.md) · [features_accuracy_table](features_accuracy_table.md)

---
*Provenance: featmatch.py — MATCHREG operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
