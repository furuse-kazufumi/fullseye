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

60 粒(うち 6 組は実際に接触)を配置した合成画像を otsu 二値化し、距離変換ピークを種にしたマーカー式 watershed で接触粒を切り分けて計数 60/60。面積の 20/80 パーセンタイルで小粒(青)・標準(緑)・大粒(橙)に色分け。粉粒体の品質検査の型。 使用 op: otsu, fill_up, xcv_watershed_markers, segment_objects。データ: 合成樹脂ペレット 60 粒・うち 6 組は接触 (配置数 = 真値)。

## コード読取りの土台 — 走査線エッジ対によるバー検出

![コード読取りの土台 — 走査線エッジ対によるバー検出](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/industrial_barcode_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/industrial_barcode.png )

実際のバーコードリーダーと同じく走査線のグレープロファイルからバーのエッジ対を検出。45 本のバー全ての両端を ±1.5px 以内で特定し、登録 op decode_barcode(簡易バー計数)とも本数が一致。※フル復号器ではなくバー検出・幅計測の素材。 使用 op: decode_barcode, gen_measure_rectangle2 (m1_*), measure_pairs (m1_measure_pairs)。データ: 合成バーコード (45 本, バー位置 = 真値)。

## 表面欠陥検査 — 背景差分 + blob 解析 + 種別分類

![表面欠陥検査 — 背景差分 + blob 解析 + 種別分類](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/industrial_defect_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/industrial_defect.png )

合成した金属面に入れた傷 3・打痕 2・錆色異物 1 を、median フィルタで地合いを推定して差分を取り、blob 解析で 6/6 件検出。さらに形状 (離心率) と色 (赤み) だけで傷/打痕/異物に分類し、種別ラベル + 色分け枠 + 拡大インセットで表示する外観検査パイプライン。 使用 op: median_image, dilation_circle, segment_objects。データ: 合成ヘアライン金属面 + 描き込み欠陥 6 件 (真値既知)。

## 位置決め — 回転探索つき shape matching

![位置決め — 回転探索つき shape matching](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/industrial_align_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/industrial_align.png )

エッジ勾配ベースの形状モデルをピラミッド探索で照合し、回転したワーク 3 個の位置と角度を検出。円板や長方形の別部品には反応しない。ばら積みピッキングや組立の前段になる位置決め。 使用 op: create_shape_model, find_shape_model (angles 探索)。データ: 合成ブラケット 3 個 (配置姿勢 = 真値) + 紛らわしい別部品。

## 焦点合成 — ボケた 7 枚から全焦点 1 枚を作る

![焦点合成 — ボケた 7 枚から全焦点 1 枚を作る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/phai_focus_stack_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/phai_focus_stack.png )

手前・中間・奥にピントを振った 7 枚を撮り、各画素で最もシャープな 1 枚を選んで合成すると、全体にピントの合った 1 枚になる。顕微鏡検査や基板検査で使う焦点合成と同じ仕組み。鮮鋭度スコアは単写比 1.27 倍。 使用 op: focus_stack suite (ラプラシアン鮮鋭度で最良フォーカスを選択)。データ: MuJoCo レンダ + 被写界深度シミュレーション (7 焦点)。

## LIDAR 点群 → 地面除去 → クラスタリング

![LIDAR 点群 → 地面除去 → クラスタリング](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/phai_lidar_clusters_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/phai_lidar_clusters.png )

リング型 LIDAR を模して 2 万本超のレイを実際に飛ばし、返ってきた点群から RANSAC で地面を除去、ユークリッド距離でクラスタリングすると物体 6 個が 6 クラスタに分かれる。各クラスタに OBB(有向バウンディングボックス)を当てて鳥瞰表示。自律移動ロボットの障害物認識の型。 使用 op: remove_ground, euclidean_clusters, obb, (mj_ray 実レイキャスト)。データ: MuJoCo シーンへの実レイキャスト (48ch × 480 方位, 物体 6 個 = 真値)。

## bin picking — 深度セグメントと把持候補の採点

![bin picking — 深度セグメントと把持候補の採点](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/phai_binpick_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/phai_binpick.png )

部品 10 個を物理シミュレーションで箱に落とし、真上の深度カメラで観測。深度しきい値でセグメントした各部品を「周囲クリアランス + 高さ」で採点し、把持ジョーの向きは長方形フィットの長軸から決める。緑が最優先候補。実機ビンピッキングの前段そのもの。 使用 op: segment_objects, fit_rectangle2, colorize_depth, (scipy distance_transform_edt)。データ: MuJoCo 物理シミュレーション (部品 10 個を実際に落下・堆積)。

## ステレオ視差 → 3D 復元 → 鳥瞰障害物マップ

![ステレオ視差 → 3D 復元 → 鳥瞰障害物マップ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/phai_stereo_obstacles_thumb.jpg)

(フル解像度: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/phai_stereo_obstacles.png )

2 台のカメラ画像のズレ(視差)をブロックマッチングで求め、Z = f·b/d で奥行きに変換して 3D 点群へ。高さ 12cm 超の点をクラスタリングすると 4 物体が 4 クラスタに分かれ、鳥瞰の障害物マップができる。移動ロボットの視覚の定番パイプライン。 使用 op: disparity_subpixel (stereo), disparity_confidence (stereo), colorize_disparity, euclidean_clusters, fit_rectangle2。データ: MuJoCo レンダのステレオペア (基線 12cm, 物体 4 個 = 真値)。

## bin picking 実動作 — 探索・把持・搬出のフルサイクル

動画 (GitHub blob ページでインライン再生): https://github.com/furuse-kazufumi/fullseye/blob/master/docs/articles/assets/media/phai_bin_pick.mp4
(raw 直リンク: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/phai_bin_pick.mp4 / 静止サムネ: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/phai_bin_pick_still_thumb.jpg )

箱に落とした部品 8 個から把持候補を採点して選び、6 自由度 IK で真上から掴んで搬出する実動作。接着なしの素の物理で、箱の外に出た部品だけを成功と数えて 3 個成功。 使用 op: bin_pick suite (6-DOF IK + 把持候補採点 + MuJoCo 物理)。データ: MuJoCo 物理シミュレーション (Franka Panda + 部品 8 個、3 個の搬出成功を実測)。
