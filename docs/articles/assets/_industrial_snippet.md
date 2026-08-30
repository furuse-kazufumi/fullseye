<!-- gen_industrial_gallery.py が自動生成。記事 md への挿入候補
     (このファイル自体は記事ではない。GALLERY.md も編集しない)。 -->

# 工業用途 + Physical AI ギャラリー — 記事挿入候補

すべて合成データ / シミュレーション上の実処理(モックアップなし)。
検出・計測結果は既知の真値(配置数・描画寸法・配置姿勢)と照合済み。

## 寸法計測 — 1D measuring サブピクセルキャリパー

![寸法計測 — 1D measuring サブピクセルキャリパー](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/industrial_metrology_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/industrial_metrology.png )

測定矩形に沿ってグレープロファイルを取り、微分の極値をサブピクセル補間してエッジ対を抽出。3 段の径を実測し、描画寸法との誤差は最大 0.02px。HALCON の 1D Measuring と同じ流儀。 使用 op: gen_measure_rectangle2 (m1_*), measure_pairs (m1_measure_pairs)。データ: 合成段付きシャフト (描画径 = 真値、0.05 mm/px)。

## ブロブ解析 — 粒子計数とサイズ分布

![ブロブ解析 — 粒子計数とサイズ分布](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/industrial_blobs_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/industrial_blobs.png )

60 粒を配置した合成画像を otsu 二値化し、距離変換 + watershed で接触粒を切り分けて計数 60/60。面積の 20/80 パーセンタイルで小粒(青)・標準(緑)・大粒(橙)に色分け。粉粒体の品質検査の型。 使用 op: otsu, fill_up, distance_transform, watersheds, segment_objects。データ: 合成樹脂ペレット 60 粒 (配置数 = 真値)。

## コード読取りの土台 — 走査線エッジ対によるバー検出

![コード読取りの土台 — 走査線エッジ対によるバー検出](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/industrial_barcode_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/industrial_barcode.png )

実際のバーコードリーダーと同じく走査線のグレープロファイルからバーのエッジ対を検出。45 本のバー全ての両端を ±1.5px 以内で特定し、登録 op decode_barcode(簡易バー計数)とも本数が一致。※フル復号器ではなくバー検出・幅計測の素材。 使用 op: decode_barcode, gen_measure_rectangle2 (m1_*), measure_pairs (m1_measure_pairs)。データ: 合成バーコード (45 本, バー位置 = 真値)。
