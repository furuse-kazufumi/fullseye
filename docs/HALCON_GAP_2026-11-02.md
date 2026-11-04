# HALCON 2605 の全 2,313 演算子の棚卸し(2026-11-02)

名前の対応だけを整理した台帳で、機能や性能の比較ではない。機械可読版は `docs/halcon_gap_2026-11-02.json`。生成は `tools/gen_halcon_gap.py`。

| 分類 | 件数 |
|---|---:|
| 対応あり(op の公開面) | 519 |
| 対応あり(モジュール関数のみ) | 495 |
| 別名で実装済み(対応付け漏れ) | 47 |
| 未実装で作るべき | 83 |
| 対象外(理由つき) | 1169 |
| 合計 | 2313 |

「モジュール関数のみ」は実装があるが `fs.ledger` と索引からは引けない。`halcon_facade_map.json` の対応は名前と関数の実在だけを検査していて、意味の一致は確かめていない。今回 13 件を読み直すと 5 件は意味が違った(下の節)。

## 章ごとの内訳

| 章 | 全体 | 対応あり | 別名 | 作るべき | 対象外 |
|---|---:|---:|---:|---:|---:|
| 1D Measuring | 20 | 11 | 0 | 3 | 6 |
| 2D Metrology | 30 | 8 | 0 | 0 | 22 |
| 3D Matching | 59 | 15 | 0 | 2 | 42 |
| 3D Object Model | 50 | 40 | 0 | 0 | 10 |
| 3D Reconstruction | 76 | 50 | 0 | 1 | 25 |
| Calibration | 68 | 35 | 2 | 0 | 31 |
| Classification | 99 | 9 | 0 | 13 | 77 |
| Control | 34 | 0 | 12 | 0 | 22 |
| Deep Learning | 81 | 3 | 0 | 0 | 78 |
| Develop | 37 | 0 | 16 | 0 | 21 |
| File | 53 | 0 | 2 | 0 | 51 |
| Filters | 195 | 186 | 1 | 2 | 6 |
| Graphics | 172 | 7 | 5 | 0 | 160 |
| Identification | 27 | 1 | 0 | 3 | 23 |
| Image | 102 | 83 | 1 | 0 | 18 |
| Image Source | 11 | 0 | 0 | 0 | 11 |
| Inspection | 43 | 8 | 1 | 8 | 26 |
| Legacy | 110 | 26 | 0 | 19 | 65 |
| Matching | 95 | 38 | 0 | 7 | 50 |
| Matrix | 57 | 46 | 0 | 0 | 11 |
| Morphology | 40 | 39 | 0 | 0 | 1 |
| OCR | 94 | 7 | 0 | 19 | 68 |
| Object | 16 | 1 | 0 | 0 | 15 |
| Regions | 101 | 100 | 0 | 1 | 0 |
| Segmentation | 50 | 46 | 0 | 4 | 0 |
| System | 140 | 0 | 1 | 0 | 139 |
| Tools | 107 | 93 | 0 | 0 | 14 |
| Transformations | 97 | 85 | 0 | 0 | 12 |
| Tuple | 162 | 0 | 5 | 0 | 157 |
| XLD | 87 | 77 | 1 | 1 | 8 |

## 2026-08 の分類を読み直して変わったこと

2026-08 の報告は未対応の残りを「ほぼ boilerplate」と分類した。名前を 1 つずつ見直すと、次はアルゴリズムの演算だった。

- `points_lepetit` は学習型と書かれていたが、検出そのものは円周の比較で学習が要らない。実装した。
- Legacy 章の `morph_skiz`、`morph_hat`、`opening_seg`、`thickening*`、`hit_or_miss_*` は教科書の形態学。実装した。
- Tools 章の `create_bg_esti` の族はカルマン背景推定、Transformations 章の `get_circle_pose` は閉形式の姿勢、Classification 章の `train_class_gmm` などは標準の学習。実装した。

## 優先度つきの残り

### 優先度 1(12 件)

- `add_texture_inspection_model_image`(Inspection)— テクスチャ検査の学習画像の追加
- `create_data_code_2d_model`(Identification)— 2 次元コードの設定の入口
- `decode_bar_code_rectangle2`(Identification)— 矩形の中の 1 次元コードの復号(既存の decode_barcode の入口違い)
- `evaluate_class_mlp`(Classification)— MLP の出力の確率
- `evaluate_class_svm`(Classification)— SVM の判別値
- `find_data_code_2d`(Identification)— QR / Data Matrix の検出と復号(ISO/IEC 18004, 16022)
- `find_text`(OCR)— 文字領域の検出(textregion の部品で組む)
- `get_thresh_images_variation_model`(Inspection)— 上下しきい値画像の取り出し
- `get_variation_model`(Inspection)— 基準と分散の画像の取り出し
- `prepare_direct_variation_model`(Inspection)— 基準と分散の画像から変動モデルを作る
- `prepare_variation_model`(Inspection)— 変動モデルの上下しきい値画像(varmodel の帯)
- `train_texture_inspection_model`(Inspection)— ガボール特徴の良品分布の学習

### 優先度 2(51 件)

- `add_deformable_surface_model_reference_point`(3D Matching)— 変形面モデルの基準点
- `add_deformable_surface_model_sample`(3D Matching)— 変形面モデルの標本の追加
- `add_samples_image_class_gmm`(Segmentation)— 領域から学習標本を集める
- `add_samples_image_class_knn`(Segmentation)— 同上
- `add_samples_image_class_mlp`(Segmentation)— 同上
- `add_samples_image_class_svm`(Segmentation)— 同上
- `approx_chain`(Legacy)— 直線と円弧への折れ線近似(Rosin と West)
- `approx_chain_simple`(Legacy)— 同上の簡易版(gen_polygons_xld と重なる)
- `cluster_model_components`(Legacy)— 部品の統合
- `create_class_lut_gmm`(Classification)— 分類器から 3 次元 LUT を作る
- `create_class_lut_knn`(Classification)— 同上
- `create_class_lut_mlp`(Classification)— 同上
- `create_class_lut_svm`(Classification)— 同上
- `create_component_model`(Legacy)— 部品の相対配置のモデル
- `create_ocr_class_knn`(OCR)— 同上
- `create_ocr_class_mlp`(OCR)— OCR 分類器の入口
- `create_ocr_class_svm`(OCR)— 同上
- `create_trained_component_model`(Legacy)— 同上
- `do_ocr_multi_class_knn`(OCR)— 同上
- `do_ocr_multi_class_mlp`(OCR)— 字の特徴 + 分類器の OCR
- `do_ocr_multi_class_svm`(OCR)— 同上
- `do_ocr_single_class_knn`(OCR)— 同上
- `do_ocr_single_class_mlp`(OCR)— 同上
- `do_ocr_single_class_svm`(OCR)— 同上
- `do_ocr_word_knn`(OCR)— 同上
- `do_ocr_word_mlp`(OCR)— 語の制約つき OCR
- `do_ocr_word_svm`(OCR)— 同上
- `find_component_model`(Legacy)— 部品の配置の探索
- `gen_initial_components`(Legacy)— 部品の初期分割
- `get_features_ocr_class_knn`(OCR)— 同上
- `get_features_ocr_class_mlp`(OCR)— 字の特徴
- `get_features_ocr_class_svm`(OCR)— 同上
- `get_shape_model_clutter`(Matching)— 形状モデルの雑然さの指標
- `get_support_vector_class_svm`(Classification)— 支持ベクトルの取り出し
- `get_support_vector_num_class_svm`(Classification)— 同上
- `inspect_clustered_components`(Legacy)— 部品の統合の確認
- `interjacent`(Legacy)— 領域の間の点の分類
- `reduce_class_svm`(Classification)— 支持ベクトルの削減
- `reset_fuzzy_measure`(1D Measuring)— 同上の解除
- `select_feature_set_gmm`(Classification)— 特徴選択(前進選択)
- `select_feature_set_knn`(Classification)— 同上
- `select_feature_set_mlp`(Classification)— 同上
- `select_feature_set_svm`(Classification)— 同上
- `set_fuzzy_measure`(1D Measuring)— エッジ強度のファジィ所属関数
- `set_fuzzy_measure_norm_pair`(1D Measuring)— 同上(対の幅で正規化)
- `set_profile_sheet_of_light`(3D Reconstruction)— 光切断のプロファイルの積み上げ
- `set_shape_model_clutter`(Matching)— 同上
- `train_model_components`(Legacy)— 部品の学習
- `trainf_ocr_class_knn`(OCR)— 同上
- `trainf_ocr_class_mlp`(OCR)— 字の学習
- `trainf_ocr_class_svm`(OCR)— 同上

### 優先度 3(20 件)

- `combine_roads_xld`(XLD)— 航空写真の道路の線と縁の統合
- `do_ocv_simple`(Inspection)— 同上
- `expand_line`(Legacy)— 線の周りの領域の成長
- `fitting`(Legacy)— 旧来の形態学の適合
- `gen_struct_elements`(Legacy)— 旧来の構造要素の生成
- `get_region_index`(Regions)— 座標の入る領域の番号
- `hamming_change_region`(Legacy)— 領域のハミング変更
- `info_edges`(Filters)— フィルタ係数の情報
- `info_smooth`(Filters)— 平滑の窓幅の情報
- `intersection_ll`(Legacy)— 線分の交点
- `partition_lines`(Legacy)— 線分の属性での分割
- `select_lines`(Legacy)— 線分の属性での選択
- `select_lines_longest`(Legacy)— 最長の線分の選択
- `set_local_deformable_model_metric`(Matching)— 変形モデルの距離の指定
- `set_planar_calib_deformable_model_metric`(Matching)— 同上
- `set_planar_uncalib_deformable_model_metric`(Matching)— 同上
- `set_shape_model_metric`(Matching)— 形状モデルの極性の指定
- `train_generic_shape_model`(Matching)— 汎用形状モデルの学習
- `traind_ocv_proj`(Inspection)— 射影による文字の検証
- `union_straight_contours_histo_xld`(Legacy)— 向きのヒストグラムによる直線の統合

## 対象外の理由

| 符号 | 件数 | 理由 |
|---|---:|---|
| `acquisition_device` | 22 | 取り込み機器の操作。acquire.Camera が担う |
| `dl_wrapper` | 112 | 深層学習の枠組みの包み。古典の視覚アルゴリズムの対象外 |
| `file_io` | 51 | ファイルの低水準操作。Python の標準の入出力が担う |
| `gui_window` | 168 | ウィンドウ表示と対話の描画。出力の描画は別の op が担う |
| `handle_lifecycle` | 58 | ハンドルの破棄と複製。Python のオブジェクトでは要らない |
| `ide_environment` | 27 | HDevelop の環境の操作 |
| `language_control` | 23 | 制御構文。Python と FScript の構文が担う |
| `language_data` | 159 | tuple と dict の言語機能。Python と numpy がそのまま担う |
| `legacy_ocr` | 18 | 旧 OCR の学習ファイルと語彙の口。同じ働きは別の入口にある |
| `model_constructor` | 18 | ハンドルへ標本を積む口。配列を 1 度に渡す形で不要 |
| `model_file_io` | 92 | モデルのファイル入出力。dict を保存すれば足りる |
| `model_parameter_getter_setter` | 187 | ハンドルの引数の取得と設定。dict の鍵を読み書きすれば足りる |
| `model_serialization` | 78 | モデルの直列化。dict を保存すれば足りる |
| `object_container` | 15 | HObject の入れ物の操作。numpy の配列とリストが担う |
| `system_runtime` | 141 | プロセス・スレッド・通信など実行環境の操作 |

## 意味が違っていた対応(2026-11-02 に直した)

| 名前 | 以前の実体 | 直したこと |
|---|---|---|
| `map_image` | 灰色値の LUT | 幾何の写像の適用(`mvimage.map_image`)。LUT の関数は消した |
| `image_to_world_plane` | 点の写像(校正族の op) | 画像の平行化を `rectify_to_world_plane` として足した |
| `change_radial_distortion_image` | 多項式の歪み、カメラの引数なし | 除算モデルで 2 つのカメラの間を変換 |
| `gray_projections` | 行と列の和 | 行と列の平均 |
| `find_ncc_models` | 1 モデルの複数検出 | 複数モデルの同時探索(1 モデルの呼び方も残す) |

比較に使った情報は演算子名と引数の形だけで、HALCON の出力とは比べていない。
