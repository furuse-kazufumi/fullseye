# 小惑星イトカワの形状モデル(CC0 1.0、形式の変換あり)

`tools/build_itokawa_anim3d.py`(イトカワの重力を動く 3-D で学ぶ教材)と `tests/test_itokawa_anim3d.py` が読む、
小惑星 (25143) イトカワの三角形メッシュ。

## 出典

- データ: R. Gaskell, J. Saito, M. Ishiguro, T. Kubota, T. Hashimoto, N. Hirata, S. Abe, O. Barnouin-Jha,
  D. Scheeres, "Gaskell Itokawa Shape Model V1.1", urn:nasa:pds:gaskell.ast-itokawa.shape-model::1.1,
  NASA Planetary Data System (2021), doi:10.26033/3b2j-yy57(PDS3 版 HAY-A-AMICA-5-ITOKAWASHAPE-V1.0 から
  2020 年に PDS4 へ移したもの。データの中身は同じ)。NASA PDS Small Bodies Node が公開。
- 形の作り方: Hayabusa(JAXA)の AMICA の画像 775 枚(2005-09-11〜11-12)から R. Gaskell が作った形
  (Gaskell et al., AIAA paper 2006-6660)。
- 取得: 2026-10-25、PDS4 bundle の `data/vertex/ver64q.tab`(4 段の解像度のうち最も粗い Q = 64)。
  SHA-256 `b472418ab40e7b7e8b29f085fa1d334038f69a2b3dd936a4e591a77ed3610c28`。

## 利用条件

NASA PDS Small Bodies Node の書誌の頁(上の bundle)に、ライセンスとして
**Creative Commons CC0 1.0 Universal(パブリックドメインへの献呈)** <https://creativecommons.org/publicdomain/zero/1.0/>
が示されている。引用の表記は上の「データ」の行(頁に示された citation)。CC0 は表示を求めないが、
出典と改変はここに書く。

## 中身(一次情報で確かめた値)

| 項目 | 値 | どこで確かめたか |
|---|---|---|
| 頂点数・面数 | 25,350 頂点・49,152 三角形 | `ver64q.tab` の 1 行目と PDS4 ラベル `ver64q.xml` の records |
| 単位 | km | PDS3 ラベル `ver64q.lbl` の `UNIT = "KILOMETER"` |
| 座標系 | 右手系の body-fixed。z 軸 = 自転の極、x 軸 = 経度 0('black rock'、南緯 3.357°) | bundle の説明 `bundle_description.txt` |
| 極と自転 | 赤経 90.02564°・赤緯 −67.02704°、W = 129.73 + 712.14376110 d(度/日) | 同上(周期 360/712.14376110 日 = 12.1324 時間) |

## 改変

- `gaskell_q64.npz`: `vertices_cm`(int32、座標 [cm]。原本は km の小数 5 桁 = 1 cm 刻みなので値は変えていない)、
  `faces`(int32、頂点番号を 1 始まりから 0 始まりに)、`source_sha256`(原本の SHA-256)。
- 作り方: `py -3.11 -I tools/import_itokawa_shape.py <取得した ver64q.tab>`(原本は repo の外。数として読み、件数・
  範囲・閉じていること・外向きの巻きを検査してから書く)。
- 原本の注意書きどおり、立方体の辺と角に重複した頂点があり、面からは使われない(閉じた曲面であることは変わらない)。
