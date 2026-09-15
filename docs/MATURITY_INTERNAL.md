# 内部用にとどめる実装(公開しない理由の台帳)

**Language:** 日本語

[成熟度台帳](MATURITY.md) は「公開している能力が、どこまで検証されているか」を
数えて出す生成物です。この文書はその**裏側** —— **実装は在るが、公開経路
(`fullseye.<名前>` / `fullseye.ledger` / op レジストリ)に載せないと決めたもの**を、
理由つきで並べます。

なぜ要るか: 載せない判断を書き残さないと、次に棚卸しした人が同じ調査を
やり直すか、あるいは「見落としだ」と判断して**名乗りと中身が食い違う op を
公開してしまう**。実装を消すのではなく、**隠さず並べて、埋まった順に外す**
——「出すべきなのに出ていない」ものの器が
`tests/test_public_reachability.py` の `_PENDING_EXPOSURE` で、
こちらは「**出さないと決めた**もの」の器です。

★この表は手で書きます(生成物ではありません)。行を足すときは
**実測した事実**を根拠に書くこと。

---

## 1. 名乗りと中身が食い違うもの(契約が未確定)

出すと利用者が**例外ではなく、もっともらしく間違った結果**を受け取る側です。

| 実装 | 名乗り | 実際にやっていること | 判断 |
|---|---|---|---|
| `mosaic.proj_match_points_distortion_ransac` | 歪み込みの点対応 RANSAC | 歪みなし RANSAC を呼び、`kappa` に **定数 0.0** を入れて返すだけ。歪みは 1 度も推定しない | 内部用 |
| `mosaic.proj_match_points_distortion_ransac_guided` | 同上(誘導つき) | 同上 | 内部用 |
| `mosaic.gen_spherical_mosaic` | 球面パノラマ座標で合成 | `gen_projective_mosaic` を**そのまま**返す(平面射影のまま。球面投影は 1 行も無い) | 内部用 |
| `mosaic.bundle_adjust_mosaic` | 全画像対からバンドル調整 | 画像 0 との**対ごとの RANSAC** を並べるだけ。全体最適化(バンドル調整)はしていない | 内部用 |
| `mosaic.gen_bundle_adjusted_mosaic` | バンドル調整した合成 | 上を呼ぶので同じ | 内部用 |
| `mosaic.gen_cube_map_mosaic` | キューブマップ合成 | 6 枚を 3x4 のタイルに**並べるだけ**(面の向きも投影も扱わない) | 内部用 |
| `caltab.binocular_calibration` | 左右を校正しステレオ相対姿勢を推定 | 左右を個別に Zhang 校正し、相対姿勢の代わりに `{"note": "…(簡易)"}` という**文字列**を返す。相対姿勢そのものは返らない | 内部用 |

**共通の理由**: どれも「できます」と読める名前を持ちながら、その計算をしていません。
名前だけを見て連鎖を組む利用者(と LLM)にとって、これは静かに間違う入口になります。
実装を直して名乗りに追いつかせたときに、この表から行を消して公開します。

## 2. 同名で規約が違うもの(混ぜると静かに嘘をつく)

| 実装 | 衝突相手 | 違い | 判断 |
|---|---|---|---|
| `calib.vector_to_hom_mat2d` | `fit_transform.vector_to_hom_mat2d` | 前者は **(x, y)** の DLT 射影変換、後者は **(row, col)** のアフィン最小二乗。**同じ名前・違う座標規約・違うモデル** | 両方とも台帳に載せない |

台帳は 1 名前 1 実装です。どちらを載せても、もう片方を期待した呼び手は
**2 座標が入れ替わった行列**を受け取ります —— 例外は出ず、再投影誤差も小さいまま
出うるので気づけません([[feedback_split_types_when_mixing_lies_silently]] の型)。

射影変換が要るなら `hom_vector_to_proj_hom_mat2d` を使ってください
(Hartley 正規化つき DLT で、`(row, col)` 契約が `tests/test_fit_transform.py` で
固定されています)。

## 3. 別名(同じ実装を 2 つの名前で出さない)

| 別名 | 本体 |
|---|---|
| `calib.calibrate_cameras` | `calib.camera_calibration` |
| `calib.calibrate_hand_eye` | `calib.hand_eye_calibration` |
| `caltab.find_calib_object` | `caltab.find_caltab` |

HALCON 互換の呼び名としてモジュールには残しますが、台帳に 2 つ出すと
利用者がどちらを呼ぶか決められません(2-D レジストリ側で
`tests/test_op_discovery.py` が敷いているのと同じ規律)。
HALCON 名で引きたい場合は `fullseye.vision_ops` から届きます。

## 4. 保留(honest だが、置き場が無い)

| 実装 | 状態 | なぜ今は出さないか |
|---|---|---|
| `filters_freq.phase_correlation_fft` | **実装は正しい**(位相相関で並進を推定。FFT・正規化・ピーク探索とも素直) | 属する族が無い。`filters_freq` は HALCON facade の 18 関数を持つモジュールで、そのうち 1 本だけを台帳に上げると「なぜこれだけ?」になる。周波数領域の位置合わせ族(相互相関・位相相関・対数極座標)を立てるときに、まとめて出すのが正しい順序。1 op の族を作るのは語彙を増やすだけで連鎖を増やさない |
| `mosaic.proj_match_points_ransac` ほか honest な 4 本 | 実装は正しい | 同じモジュールの 6 本が上の 1. に該当するため、族として出すと**同じ名前空間に「やる」と「やらない」が混ざる**。mosaic を族として出すのは、1. の実装を直してから |

---

*この表の行は、直したら消してください。消し忘れないように、
`docs/capabilities/` の能力ノートからはここを参照しません
(参照すると「内部用」が能力の説明に混ざります)。*

Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0.
