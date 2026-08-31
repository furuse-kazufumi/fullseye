# Fullseye Operator Catalog — AI capability ledger

Fullseye は説明可能な古典/幾何ビジョンの Physical-AI ツールキット。この台帳は **用途を伝えれば、どの op をどう組み合わせればよいかを AI が提案する**ための一覧です。

## この台帳の使い方(assistant 向け)

1. ユーザーの**用途(入力データ・欲しい出力)**を特定する。
2. まず **Worked examples**(用途→op の実例)から最も近いものを探し、その op 連鎖を土台にする。
3. 連鎖は **in → out のデータ種**が繋がるように組む(例: `image → region → feature`、`points → voxel → mesh`)。2D パイプライン op は 1 画像+2 スカラつまみのモデル、点群/体積の 3D op と 2 画像を取る op(morph 等)は関数として呼ぶ。
4. 各 op の**前提と失敗条件**(退化入力・必要点数など)を必ず確認し、fail-closed に扱う。
5. 提案には**具体的な op 名**と、可能なら該当する worked example / References を添える。
6. 実装が不確かなら、対応する `examples*/` を実行して ground-truth 出力で確かめる。

## Worked examples(用途 → 使う op の実例=推奨組合せの手本)

### 2-D 画像/信号/幾何(18 例)

**morphing**
- **2人の顔の中間を作る(対応点駆動モーフ)** — 作業者が与えた対応点(目・鼻・口)で特徴を中間形状へワープしてからディゾルブし、単純αブレンドの二重像(ゴースト)を避けて『本物の中間顔』を作る。区分アフィン/TPS。 `py -3.11 examples/image_morph.py`

**shape_descriptors**
- **輪郭の楕円フーリエ記述子(平滑化・不変マッチング)** — 閉輪郭をフーリエ級数で表し、高調波打ち切りで平滑化、回転/拡大/移動/始点に不変な記述子で形状検索する(EFD, Kuhl-Giardina)。 `py -3.11 examples/contour_fourier.py`

**drawing**
- **画像にマーカー/線/円/輪郭を直接描く(ラスタ描画)** — 作業者が指定した対応点を画像そのものに焼き込むラスタ描画op(imagedraw)。描いた既知シーンを検出器が回収し結果を描き返す(描画→検出→注釈)。 `py -3.11 examples/draw_annotate.py`

**signal_processing**
- **点列の多項式近似・フーリエ・ローパス/ハイパス** — 計測1D列をトレンド抽出(多項式)・周波数分析(FFT)・平滑化(ローパス)・細部抽出(ハイパス)する(signal1d)。各処理に beat-the-null のGT付き。 `py -3.11 examples/signal_filter.py`

**interpolation**
- **スプライン補間(開/閉曲線・2D/3D・時間変形)** — 疎な点列を滑らかに補間・再サンプル。輪郭は閉曲線(滑らかに閉じる)、軌跡は開曲線、3D空間曲線も同API。座標を時間で補間すれば時間軸の変形も表せる。 `py -3.11 examples/spline_curve.py`

**family_coverage**
- **平滑化・ランク・復元フィルタ族を総なめ** — gaussian/median/bilateral/rank/restoration など平滑化フィルタ族の全 op を実行し、有限性・out_sort・決定性を機械検証(代表 op は beat-the-null GT)。 `py -3.11 examples/gallery2d_smoothing_rank.py`
- **エッジ・微分・コーナー演算子族を総なめ** — sobel/laplace/canny/harris などエッジ・勾配・コーナー検出族の全 op を GT 検証。 `py -3.11 examples/gallery2d_edges.py`
- **モルフォロジー(形態学)op 族を総なめ** — 収縮/膨張/開閉/tophat/skeleton などグレー・二値形態学の全 op を GT 検証。 `py -3.11 examples/gallery2d_morphology.py`
- **領域(region)op 族を総なめ** — 穴埋め/最大成分/距離変換/外接内接/RLE など region・region-morphology・region-transform を GT 検証。 `py -3.11 examples/gallery2d_region.py`
- **セグメンテーション演算子族を総なめ** — otsu/dyn_threshold/watershed/local_max などしきい値・領域分割族の全 op を GT 検証。 `py -3.11 examples/gallery2d_segmentation.py`
- **特徴抽出・テクスチャ・形状記述子族を総なめ** — 特徴点/テクスチャ/形状記述/自己相似の全 op を有限性・決定性で GT 検証。 `py -3.11 examples/gallery2d_features.py`
- **2-D 幾何オペレータ族を総なめ** — アフィン/射影/回転/リサンプル/座標変換など幾何変換族の全 op を GT 検証。 `py -3.11 examples/gallery2d_geometry.py`
- **濃淡・階調変換・算術・定義域 op 族を総なめ** — gamma/contrast/算術演算/domain(定義域)など濃淡・階調族の全 op を GT 検証。 `py -3.11 examples/gallery2d_gray_arith.py`
- **輪郭・1次元計測・テンプレート照合族を総なめ** — 輪郭抽出/subpix/1D 計測/テンプレートマッチ族の全 op を GT 検証。 `py -3.11 examples/gallery2d_contour_measure.py`
- **テクスチャ・周波数・分解 op 族を総なめ** — FFT/gabor/wavelet/分解(decomposition)などテクスチャ・周波数族の全 op を GT 検証。 `py -3.11 examples/gallery2d_texture_freq.py`
- **色・芸術・拡張(sim2real)op 族を総なめ** — 色空間変換/芸術効果/augmentation など色・拡張族の全 op を GT 検証。 `py -3.11 examples/gallery2d_color_artistic.py`
- **HALCON 拡充 tier(hx_ 一族)を総なめ** — HALCON 互換の拡充 op(``hx_`` prefix, category=halcon_ext)の全 op を GT 検証。 `py -3.11 examples/gallery2d_halcon_ext.py`
- **物理PDE・人工生命・トモグラフィ・3Dボリューム op 族を総なめ** — 拡散/反応拡散/CA/tomography/volume など物理・人工生命・3D 族の全 op を GT 検証。 `py -3.11 examples/gallery2d_physics_alife_3d.py`

### 3-D 点群/体積/曲面(112 例)

**registration**
- **CADモデルをノイズ入り3Dスキャンに位置合わせ** — 初期姿勢なしで CAD 設計形状を実物スキャン点群に合わせ、置かれた向きと位置を復元する(FPFH+RANSACで粗く→ICPでセンサノイズ床まで)。 `py -3.11 examples_3d/cad_to_scan.py`
- **手法を自動選択する点群登録** — 2点群の近さを見て、近ければ ICP・大きく離れていれば FPFH+ICP を自動選択する(手法指定不要)。 `py -3.11 examples_3d/auto_register.py`
- **登録品質の評価(recall/RMSE/inlier)** — 登録結果が成功か失敗かを inlier率・RMSE・recall で定量化。対応ゼロでは NaN を返し捏造しない。 `py -3.11 examples_3d/reg_eval.py`
- **2視点からの相対カメラ姿勢(SfM初期化)** — 2枚の画像の対応点から基礎/基本行列を解き、相対カメラ姿勢と3D点を復元する(単眼SfM/VOの初手)。 `py -3.11 examples_3d/two_view_pose.py`
- **N視点バンドル調整による精緻化** — 全カメラ姿勢と3D構造を再投影誤差最小で同時最適化し、摂動から機械精度へ回復する。 `py -3.11 examples_3d/bundle_adjust.py`
- **ループ閉じ込みのポーズグラフSLAMバックエンド** — ノイズ入りオドメトリ+ループ閉じ辺を最適化し、蓄積したドリフトを低減する。 `py -3.11 examples_3d/pose_graph_slam.py`
- **3D 幾何変換 — rotate 90°x4 恒等・resize の物理体積保存・affine 厳密シフト** — vol_rotate は np.rot90 と bit 一致で回転方向規約を機械固定、vol_resize は spacing 再計算で物理体積 230.4 mm^3 厳密保存、vol_affine は pull 規約(out[o]=vol[M@o+offset])を voxel 単位で検証。 `py -3.11 examples_3d/vol_geometry_transform.py`
- **小惑星の姿勢を主成分で正準化** — 不明な向きで届いた小惑星形状を、慣性主軸で形状固有の正準姿勢へ整える(カタログ化・比較用)。 `py -3.11 examples_3d/itokawa_pose_canonical.py`
- **未知姿勢で置かれた小惑星スキャンの位置合わせ** — 未知の探査機姿勢で撮った小惑星スキャンを ICP で基準形状に戻す。不規則形状は球と違い登録できる。 `py -3.11 examples_3d/itokawa_self_register.py`
- **平面主体スキャンのGICP位置合わせ** — 床+直交2壁のコーナーを既知変換で動かし gicp(共分散重みマハラノビス)で復元。回転<1度、平面が滑る状況で点対点ICPを約6.5倍上回る。 `py -3.11 examples_3d/gicp_register.py`
- **疎特徴による3D点群レジストレーション(Harris/ISS + SHOT/Spin/FPFH)** — 初期推定なしで57度回転した2点群を合わせる「疎特徴レジストレーション」道具箱の6opを1本で通し、各段を実測の真値で検証する。harris3d_keypointsは立方体密度場の解析的な8頂点(唯一の3Dコーナー)を狙い、上位8検出が8頂点と1対1対応(平均1.73voxel、無作為null 9.16を判別的に下回る)。iss_keypointsは回転不変性を真値とし、同一点群を既知(R,t)で回した雲でも選ばれる163点のindex配列が完全一致。sh… `py -3.11 examples_3d/feature_register.py`
- **部分重なりスキャンの登録(FPFH+ICP)** — 非対称ブロブを別方向2視点で部分スキャン(幾何重なり56%)。scan Bに55度回転+並進を掛け、register_pointclouds(FPFH+RANSAC→ICP)でAへ登録。回転誤差0.86度<4・RMSE0.150が床0.148水準。PCA主軸103度/単位行列ICP58度のnullを桁違いに下回る。 `py -3.11 examples_3d/partial_overlap_icp.py`

**metrology**
- **平面度メトロロジー(基準面からの偏差)** — 点群に平面を当て、基準面からの偏差=平面度を測る。既知の膨らみ高さと一致することで検証。 `py -3.11 examples_3d/plane_flatness.py`
- **真球度/丸さ検査** — 点群に球を当て、真球からの偏差=真球度を測る。完全な球ほど偏差が小さいことを確認。 `py -3.11 examples_3d/roundness.py`
- **30%外れ値下での頑健プリミティブ適合** — 平面/球/円柱を RANSAC で当て、外れ値30%が混じってもパラメータを正しく復元する。 `py -3.11 examples_3d/ransac_prim.py`
- **domain(処理領域)と boundary(境界殻)でメモリを絞って計測** — vol_reduce_domain で治具を消し vol_crop_domain でメモリ 1/34(実測)、vol_boundary の殻 19% を vol_boundary_points で物理mm点群化して fit_sphere3 が中心誤差 0.000mm、vol_uncrop は元フレームへ bit 一致で貼り戻し。 `py -3.11 examples_3d/roi_domain_boundary.py`
- **RLE 領域 — HALCON region の効率の正体を voxel 界へ** — vol_rle_encode が 192^3 部品マスクを dense bool の 1/73(実測)に、volume/bbox/centroid は run 直接演算で dense と厳密一致かつ 93x 速(実測)、和/積/差の集合演算 3.1ms(run のみ)、vol_rle_components の成分分解、vol_tiled_map は gaussian 全量計算と最大差 0、往復 bit 一致、改竄 RLE は fail-closed 拒否。 `py -3.11 examples_3d/rle_region_efficiency.py`
- **virtual probe — パイプ壁厚をプローブ 1 本で計測** — vol_profile_line(異方 spacing の物理距離厳密)→ vol_edge_probe(サブボクセル 4 エッジ、極性 +,-,+,-)→ vol_wall_thickness が壁厚 2.042/2.042 mm(真値 2.000、誤差 0.042mm=0.085voxel)。measure1d の 3D 版。 `py -3.11 examples_3d/wall_thickness_probe.py`
- **曲座標展開: 極/円筒/Zernike/LiDAR円筒投影で回転体の m 回対称を一貫復元** — 回転体(3枚羽根=m=3回対称)の検査を、中心を原点にした曲座標へ展開する4つのopで横断検証する事例。fit_zernikeは既知の波面係数(piston/tilt/defocus/astigmatism)で合成した円板を極座標直交基底(n,m)へ分解し、各係数を誤差5e-5で復元(非点収差=m=2角モードが立つ)。polar_unwrapは2D画像の円板を(θ×r)へ展開しθ軸FFTでm=3を検出(power@m=179で他ビンを圧倒)、回転対称画像は… `py -3.11 examples_3d/curvilinear_proj.py`
- **幾何メトロロジー: 直線/平面/球/円の当てはめ→角度・距離・交線計測** — 1 個の機械加工ブロック(2 面が稜線で交わり、面上に球と円穴が乗る)を舞台に、当てはめ op(fit_line_3d/fit_plane_3d/fit_sphere_3d/fit_circle_3d/ransac_line)の出力を計測 op(angle_3points/angle_between_lines/angle_between_planes/angle_line_plane/distance_point_plane/distance_point… `py -3.11 examples_3d/geometry_metrology.py`
- **3-D プリミティブ当てはめ(直線/平面/球/円/最小包含球)** — 点群から直線・平面・球・円を最小二乗で当て、中心/半径/向き/残差を (depth,row,col) で復元(機械精度)。各残差は『わざと外した』null を桁違いに下回る。measure3d.fit_line3/fit_plane3/fit_sphere3/fit_circle3/smallest_sphere3。2-D fit_line/fit_circle の 3-D 版。 `py -3.11 examples_3d/primitive_fitting_3d.py`
- **最大内接ボックス(inner_rectangle1 の 3-D 版)** — 空洞のある部品(二値ボクセル)に内接する最大の軸平行ボックス=「保証できる最大の中実ブロック」を厳密に求める(総当たりと完全一致)。深さ区間の論理積×2-D最大内接長方形。空洞をまたぐ前景bbox(非中実)を判別的に下回る。regionprops3d.inner_box3。 `py -3.11 examples_3d/inner_box_inspection.py`
- **最小体積の有向境界箱(OBB=smallest_rectangle2 の 3-D 版)** — 傾いた直方体の実寸を最小体積 OBB で復元(半径 (5,2,1)・中心・体積 80 を機械精度)。軸平行 AABB は回転で ~1.8 倍に膨張し、PCA 箱(pcseg.obb)は非対称形状で最小にならない — min-volume OBB(凸包面×回転キャリパー, measure3d.smallest_box3)が両者を判別的に下回る。把持/梱包の寸法検査。 `py -3.11 examples_3d/oriented_bounding_box.py`
- **点群のバウンディング(凸包/OBB/AABB/最小包含球)** — 生点群から凸包・向き付き箱(OBB)・軸整列箱(AABB)・最小包含球を起こす。新規 min_enclosing_sphere は素朴球 r=9.95→5.63(比0.57・全点内包)、OBB体積は回転箱で AABB の0.20倍。把持/衝突/寸法検査の基本メトロロジー。 `py -3.11 examples_3d/hull_bounds.py`
- **平歯車の歯数をSDFジオメトリから逆計測** — sdf_opsのCSGで平歯車を手続き生成し、歯先帯r=0.44の占有を角度サンプルしてラン計数で歯数N=12→12/20→20を厳密復元(0.2度ジッタでも不変)。歯なし円板null=0本・誤半径 内1/外0本で判別的。 `py -3.11 examples_3d/gear_metrology.py`
- **円筒軸メトロロジー(30%外れ値ロバスト)** — 汚れた産業スキャン(30%グロス外れ値・2000点)からパイプの軸方向と半径を計測。fit_cylinder_ransacで半径誤差1.27%・軸誤差0.78°・面残差0.00165m。非ロバスト全点フィット(半径誤差101%)と誤プリミティブ平面RANSAC(残差0.058m)を5倍超マージンで判別的に上回る。 `py -3.11 examples_3d/cylinder_axis_metrology.py`

**segmentation**
- **CT windowing — 窓の選択が「見える構造」を入れ替える** — vol_window_level の軟部窓は軟部 Δ0.50 が立ち骨は飽和、骨窓は骨が立ち軟部は背景と同化(実測)。vol_equalize(mask domain LUT)/ vol_gamma(γ=2 で 0.5→0.25 厳密)/ vol_stretch(パーセンタイル厳密写像)も検証。 `py -3.11 examples_3d/gray_window_level.py`
- **ビンピッキング: 台平面除去→物体クラスタリング** — 地面平面を plane_segmentation で剥がし、残りを euclidean_cluster で3物体に分離。クラスタ数・重心が真値一致、全点1クラスタ扱いの零点を上回る。 `py -3.11 examples_3d/object_segmentation.py`
- **3Dボリュームの連結成分ラベリングと塊ごとの計測(個数/体積/重心)** — 複数ブロブを連結成分で分離し、体積誤差0voxel・重心誤差0.0で計測。largest_componentで最大塊、filter_by_volumeで小塊除去。全前景を1領域とする零点(重心ズレ13.5voxel)を上回る。 `py -3.11 examples_3d/region_props_3d.py`
- **センサ幾何と領域処理パイプライン(角シーンの denoise→傾き→面分割→計画格子)** — 深度センサが捉えた「2つの傾いた面が稜線で出会う角」の1シーンを、実際の知覚パイプラインの順に8opで連結処理する例。清浄ガイドで joint_bilateral して段差を残しつつノイズを削り(RMS 0.112→0.019、素のGaussianぼかしnullは稜線段差を-5.8→-1.16に潰すが本opは-5.79を保存)、bearing_angle_image で各面の傾きを degrees(atan(s)) と厳密一致で数値化(左26.565°/右… `py -3.11 examples_3d/sensor_seg.py`
- **接触物体の分離(距離変換ベース3D watershed)** — 接触して1連結成分に融合した2球をwatershedで2個に分離。重心を真値へ最大0.31voxel・体積誤差<5%。連結成分(null)はcount=1に融合し重心が10voxelずれる — 個数でも重心でも上回る。CT/粉体/細胞の計数。 `py -3.11 examples_3d/watershed3d.py`
- **分子の接触原子カウント(距離変換+マーカ分水嶺)** — シクロヘキサンC6椅子型を6原子球の和集合(41万voxel・1連結成分)にボクセル化。距離変換+マーカ分水嶺で接触原子を6個に分離・重心を真値へ最大0.52voxel。素朴な連結成分null=1個に融合(43voxelずれ)を個数6vs1で上回る。 `py -3.11 examples_3d/molecule_atom_count.py`
- **屋外LiDARシーンの地面除去→物体分割** — 傾斜地面(~5.4度)上の4物体(球/箱/円柱/円錐)のLiDAR点群5316点を、fit_plane_ransac+height_above_planeで地面除去→euclidean_clustersで分割。検出4==K=4・重心を真物体へ全単射(最大0.128m)。地面除去なしnullは全物体癒着で1クラスタ。 `py -3.11 examples_3d/lidar_scene_segmentation.py`

**reconstruction**
- **顕微鏡スタック復元 — 3D FFT フィルタ + Richardson-Lucy** — vol_fft_lowpass+highpass=入力の恒等式、照明ドリフト成分を 1/17 に抑制(線形性で分離計測、ガウス伝達のトレードオフごと開示)、vol_richardson_lucy 50 回で RMSE 0.68x(漸進と正直に主張)+前方一貫性 0.021x+総強度保存。 `py -3.11 examples_3d/deconv_fft_restore.py`
- **進化探索で見つけた点群デノイズ・パイプライン** — 外れ値除去・平滑化・間引きの順番を遺伝的アルゴリズムに探させ、無処理と人手の定番を上回る。 `py -3.11 examples_3d/denoise_evolution.py`
- **複数深度フレームをTSDFで融合し表面抽出** — 複数視点の深度観測を TSDF に融合し、単一観測よりノイズに頑健な表面を得る。 `py -3.11 examples_3d/tsdf_fusion_demo.py`
- **複数断層の2D輪郭を積層して3D曲面(メッシュ)に** — 各スライスの閉輪郭を塗って voxel 積層→marching cubes で曲面メッシュ化。頂点は球面に乗り体積も一致(断面一定=円柱仮定は1.5倍過大)。輪郭→領域→voxel→メッシュの表現変換。 `py -3.11 examples_3d/contours_to_surface.py`
- **等高線(標高付き輪郭)から地形の高さ場(DEM)を復元** — 等高線点(x,y,標高)を fit_poly_surface でサーフェス当てはめし DEM 格子へ展開。線の間も内挿し全域RMSEが最近傍等高線の階段近似を桁違いに下回る(GIS/測量)。 `py -3.11 examples_3d/contours_to_terrain.py`
- **多視点シルエットから visual hull を彫る** — 既知形状を複数の既知視点で synthesize_silhouette→carve し visual_hull を得る(recall 1.0)。1視点は柱状に過大、多視点で真形状へ収束。 `py -3.11 examples_3d/space_carving.py`
- **評価指標4種の真値検証(F-score/RMSE対応/法線一致/voxel IoU)** — 単位球点群(放射法線)と占有ボクセルを正解として合成し、metrics3d の 4 評価指標を解析真値と 1e-9 で照合する。fscore は 120 点厳密コピー+60 外れ点の再構成で precision=120/180・recall=120/150 を厳密に作り込み f=0.72727 を検証(完全コピー=1.0、無作為点 null≈0)。rmse_correspondence は恒等=0・既知オフセット |v|=0.1 の残差を厳密照合し、対応数… `py -3.11 examples_3d/metrics_eval.py`
- **2視点SfMから表面再構成まで一つの球で通す** — 中心[0,0,6]・半径1.5の単一の球を題材に、2視点SfMから表面再構成・観測合成までを6つのopで鎖状に接続し、すべて既知真値と照合する(ノイズ無し合成)。essential_8pointは球面上の対応点+Kから本質行列Eを復元し、真のE=[t]×Rと符号/スケールを除き|cos|=1.000000で一致・正規化エピポーラ残差1.1e-15を確認(直交並進+40度回転の誤E nullは|cos|=0.002・残差0.35)。triangulateは真… `py -3.11 examples_3d/sfm_recon.py`
- **トーラス点群のalpha shape再構成で穴(genus1)を保持** — 中実トーラス(主R1.0/管r0.35)9000点をestimate_alpha+alpha_shape_meshで再構成。z軸穴プローブ41点の内包率がalpha=0.000(穴を保持)、凸包null=1.000(穴を充填・厳密Delaunayでも1.000)。オイラー標数χ_alpha=0(トーラス)対χ_hull=2(球)でも判別的。 `py -3.11 examples_3d/alpha_shape_topology.py`
- **Poisson軽量表面再構成(向き付き点群→水密メッシュ)** — でこぼこ閉曲面(外向き法線を勾配で厳密算出)の向き付き点群6000点をrecon3d.poisson_liteで水密メッシュ(V11788/F23572)へ。真曲面との正規化chamfer0.01006が外接球null(0.081=8倍)・乱数法線null(0.041=4倍)より桁違いに小さい。 `py -3.11 examples_3d/poisson_surface_recon.py`

**depth**
- **2視点プレーンスイープ・ステレオ深度** — 既知カメラの2画像から、深度平面を掃引して photo-consistency 最小の深度を画素ごとに選ぶ。 `py -3.11 examples_3d/plane_sweep_depth.py`
- **エッジ保存の深度デノイズ+穴埋め** — 段差を跨がずにノイズを平滑化し、浅い穴を調和補間で埋める(深い穴はNaNのまま残す)。 `py -3.11 examples_3d/depth_denoise.py`
- **骨格CTからX線ラジオグラフ(DRR)を合成** — 手骨のCT密度ボリュームを厚み方向に積算し、2次元の手のX線像(DRR)を合成する。 `py -3.11 examples_3d/ct_hand_radiograph.py`
- **低線量スパースビューCT再構成(radon→SART)** — 指の断面をX線投影し、SART(反復)とFBPで再構成する。低線量ゆえの控えめな品質を正直に評価。 `py -3.11 examples_3d/ct_sparse_view_recon.py`
- **ステレオ視差からの多深度パッチ奥行き復元** — 校正済みステレオ対(f*B=96)に近8/中16/遠32mの3テクスチャパッチを視差12/6/3pxで合成し、disparity_map→depth_from_disparityで復元。パッチ内部の相対誤差0.00%・near>mid>far順序も正。最良定数null63.9%・視差ゼロnull(∞)を判別的に上回る。 `py -3.11 examples_3d/stereo_depth_scene.py`

**modeling**
- **SDFのCSG合成(和/差)でソリッドを作りメッシュ化** — 符号付き距離場の集合演算(球∪箱−小球)で陰関数ソリッドを作り、等値面をメッシュへ。 `py -3.11 examples_3d/sdf_csg.py`
- **CTボリュームから骨をセグメンテーションし、接触骨を分離して計数・体積計測** — 骨を閾値化し、関節で繋がる指骨を収縮で分離してから連結成分で数え、体積を測る(閾値内外の密度コントラストで検証)。 `py -3.11 examples_3d/ct_bone_segmentation.py`
- **CTボリュームから骨表面メッシュを抽出(marching cubes)** — CTボリュームに marching cubes をかけ、骨表面を三角メッシュ化する(3Dプリント/FEA向け)。 `py -3.11 examples_3d/ct_surface_extraction.py`
- **3Dモルフォロジ(opening/closing/gradient/top-hat)で体積を整える** — closingで空洞8→0(本体は不変)、openingでトゲ3→0、gradientは境界殻のみ、top-hatはトゲだけ抽出。素のdilate/erodeが本体まで膨張/収縮する差で判別。 `py -3.11 examples_3d/morphology_3d.py`
- **手続き的に手全体の骨格を組む(27骨のカプセルSDF→メッシュ)** — 手根骨8+中手骨5+指骨14をカプセルSDFで解剖学配置しmarching cubesでメッシュ化。指先バンドの連結成分=四指(>=4)・細長さ4.66で「手」と判別。同体積の球null(指1本)を上回る。教材/デモ/合成データの自前生成。 `py -3.11 examples_3d/procedural_hand.py`

**features**
- **主曲率・形状指数による把持アフォーダンス** — 点群の主曲率と形状指数から、球・円柱・鞍点を識別する(把持面の当たり判定)。 `py -3.11 examples_3d/curvature_grasp.py`
- **反射・回転対称性の検出** — 点群の反射面と回転対称の位数を chamfer 採点で検出する。 `py -3.11 examples_3d/symmetry.py`
- **大域記述子(D2/A3)による形状検索** — 距離分布 D2・角分布 A3 の大域記述子で、回転しても同形状は近く・異形状は遠く照合する。 `py -3.11 examples_3d/shape_retrieval.py`
- **小惑星表面の曲率解析(尾根・クレーターの検出)** — 表面の主曲率・曲率度・形状指数を求め、平坦部と尾根/窪みを仕分ける(値が実在表面の幾何であることを近傍相関で確認)。 `py -3.11 examples_3d/itokawa_curvature.py`
- **chamfer距離による形状照合** — chamfer 距離で「同一の天体か別物か」を数値判定する(自身の回転コピーは近く・同大の球は遠い)。 `py -3.11 examples_3d/itokawa_shape_match.py`
- **対称性検出(正直な結果:小惑星は非対称)** — 反射対称スコアを小惑星と対称な楕円体で比較。ラブルパイル小惑星は非対称=検出器が正しく低スコアを返す。 `py -3.11 examples_3d/itokawa_symmetry_honest.py`
- **点群に大域整合した外向き法線を付与(PCA推定→MST向き伝播)** — 符号未定のPCA法線を Hoppe MST で外向きに揃える。球面サンプルで生法線の外向き一致0.50(コイン投げ)を向き付け1.00へ改善、接平面精度1.00。退化入力は捏造せず拒否。 `py -3.11 examples_3d/oriented_normals.py`
- **球面調和記述子による回転不変な3D形状検索** — 向き未知の形状(球/箱/円柱の回転コピー)を SH 帯域エネルギー記述子で照合。検索3/3正解・分離マージン>0で、回転で全マスが入れ替わる素ボクセル占有の1/3を上回る。 `py -3.11 examples_3d/shape_descriptor.py`
- **3Dボリュームのエッジ検出(canny3d: NMS+ヒステリシス)** — なだらかな内部を持つ中実ボールの外周だけを1ボクセルに細線化。オンシェル率1.000・内部誤検出0で、生勾配の固定しきい値null(0.464・誤検出4012)を+0.536上回る。 `py -3.11 examples_3d/edges_3d.py`
- **3-D 微分特徴の抽出と検証(勾配・Hessian・曲率・距離場・black-hat)** — 球状ソリッド部品を題材に、3-D スカラー場から 5 種の微分/形態特徴を抽出し、それぞれ解析的な真値で裏取りする。(1) 既知の 2 次多項式場で sobel3d が勾配を(分離 conv 利得 32 で割ると)機械精度 ~1.9e-5、hessian3d が 6 独立成分を ~6.3e-5 で解析勾配・解析 Hessian を厳密復元。定数場で勾配≈0・線形場で Hessian≈0 の null も確認。(2) curvature_maps が球殻=cap(S≈+1)/円柱=ridge(S≈+0.5)を判別分離し、curvedness は 1/r を絶対値で復元(c·r≈1.0、2026-08-30 の利得補正後は真の 1/voxel 単位)… `py -3.11 examples_3d/diff_features.py`
- **実メッシュ曲率が詳細形状を判別(Stanford Dragon)** — DL実データStanford Dragon(87万面)をread_mesh→vertex_curvature(cotangent Laplace-Beltrami)。正規化曲率はmedian9.2・MAD6.2・|Hn|>2が88%と広く分布し、同スケールの滑球null(median1.00・0%)をMAD比1.4e7倍で判別。未取得時はSKIPしexit0。 `py -3.11 examples_3d/dl_mesh_curvature.py`
- **FPFH記述子で部分ビュー間の点対応を張る** — 同一物体の2部分ビュー(58度回転+並進・重なり1514点)で法線推定→FPFH記述子(33次元)を計算し記述子最近傍で対応。幾何正答率0.633がランダム対応0.0034・記述子シャッフル0.0020(チャンス率)を約185倍上回る。register全体でなく記述子マッチ品質を直接測る。 `py -3.11 examples_3d/fpfh_correspondence.py`

**motion**
- **動的シーンの剛体運動セグメンテーション** — 2時刻の点群から、別々に動く剛体ごとに分割する。無相関ノイズでは剛体を捏造しない。 `py -3.11 examples_3d/motion_seg.py`
- **剛体シーンフロー(既知R,tと密フィールドの復元)** — 点群を既知剛体変換で動かし rigid_flow で復元(回転<1度・並進<1voxel)。smooth_flow が生NN流のEPEを約半分に、residual_flow は剛体部でノイズ床。 `py -3.11 examples_3d/scene_flow_rigid.py`

**pose_estimation**
- **外れ値ありの3D-2D対応からカメラ6自由度姿勢を推定(PnP+RANSAC)** — 既知寸法の箱の3D-2D対応(30%外れ値・0.5px雑音)から pnp_ransac で姿勢復元。回転<2度・並進<2%で、恒等姿勢や素のDLTを明確に上回る。 `py -3.11 examples_3d/pose_estimation.py`
- **誤対応4割下のカメラ姿勢推定(PnP+RANSAC)** — 200点の3D-2D対応の40%が誤対応でもpnp_ransacが姿勢復元: 回転誤差0.11度・inlier再投影0.66px・inlier適合率100%。同じ汚染データの素dlt_pose(RANSACなし)は33.7度に破綻し319倍判別的に上回る。 `py -3.11 examples_3d/pnp_pose_outliers.py`

**mapping**
- **占有格子+ESDFで連続クリアランスを問い合わせ** — 部屋点群から occupancy_grid→esdf を作り、自由空間点で最近接障害物までの連続距離を query_distance。占有0/1のみの零点を約39倍上回る(衝突回避マージン判定)。 `py -3.11 examples_3d/occupancy_esdf.py`
- **地形の走行可能性マッピング(段差検出)** — 平坦+緩スロープ+急段差(0.5m壁)の点群→標高マップ→走行可能性マップ。平坦/緩は走行可能率1.00・段差は非走行可能率1.00。段差検出 実op1.00 vs 全可null/巨大max_step null 0.00、GT精度1.00 vs 0.83。 `py -3.11 examples_3d/terrain_traversability.py`

**shape_fitting**
- **点群から角丸ブロックをスーパー楕円体で当てはめ** — 既知スーパー楕円体からの雑音点群を fit_superquadric で復元(半径5%以内・内外分類>95%)。球1個を当てた残差を大きく下回る(把持点判定向け)。 `py -3.11 examples_3d/superquadric_fit.py`
- **3D Houghで平面・球のプリミティブを検出** — 投票ベースの hough_plane_3d/hough_sphere_3d で平面(法線誤差0.55度)・球(中心誤差0voxel)を復元。素朴PCA(80度)や重心(22voxel)の零点を明確に上回る。 `py -3.11 examples_3d/detect_primitives_3d.py`
- **プリミティブ当てはめ拡張(円錐/トーラス/楕円体)** — 点群に円錐(半角誤差0.008°)・トーラス(R,r誤差~3e-4)・楕円体(半径相対誤差<0.2%)を当てはめ。誤モデル(球/平面)の残差をそれぞれ38x/64x/50x下回る。漏斗/配管/細胞・慣性の寸法検査。 `py -3.11 examples_3d/fit_primitives_ext.py`

**shape_descriptors**
- **3Dモーメント不変量(剛体+一様スケールに不変)** — 点群に既知の平行移動・回転・一様スケールを掛けても moment_invariants はほぼ不変で、別形状とは明確に区別。生モーメントは同変換で大きく変動。 `py -3.11 examples_3d/moment_invariants.py`
- **大域形状記述子と姿勢照合** — 3D 部品を姿勢に依らず「形」で同定し、次に実際の姿勢を復元する一連の流れを、大域形状記述子(D2 距離分布・A3 角度分布・PCA 広がり比 extent・主慣性モーメント)と姿勢照合(PCA 主軸整列・FFT 位相相関・log-polar/Fourier-Mellin)で示す。記述子側は厳密な数学則で検証: extent_signature と principal_moments は同一共分散の別表現なので、principal_moments から共分… `py -3.11 examples_3d/shape_desc_pose.py`
- **球面調和記述子による回転不変な3D形状検索** — 球/立方体/トーラス/円柱/円錐の5クラスをボクセル化しsh_descriptor化。一様ランダム3D回転したクエリをmatch_sh_descriptorで検索→30/30=100%正解・分離マージン0.312。非回転不変null(軸周辺分布)は回転で100%→37%に崩れSHが+63pt上回る。 `py -3.11 examples_3d/sh_descriptor_retrieval.py`

**shape_analysis**
- **CT の管・粒・肉厚を Hessian 特徴と物理量で計測** — vol_frangi/sato(管状度)と vol_hessian_blobness(粒状度)が相互否定対照で逆転、vol_local_maxima がピーク座標一致、vol_label の 26/6 連結規約、vol_region_props/vol_distance_transform が spacing 物理量(mm^3/mm)で手計算一致。 `py -3.11 examples_3d/vessel_metrology.py`
- **中軸骨格と位相署名で形状を区別** — 中実円柱の芯を skeletonize_vol/medial_axis_points で抽出(既知中心軸上)、topology_signature+medial_match でトーラス(genus1)を球/円柱と区別。ランダム署名の零点を上回る。 `py -3.11 examples_3d/medial_topology.py`
- **曲面上の測地距離と最遠点サンプリング** — 球面点群で kNN グラフ上の geodesic_distances が大円距離と一致(誤差1.7%)、farthest_point_sampling で均等な代表点。直線ユークリッド距離は曲面上で系統的に過小。 `py -3.11 examples_3d/geodesic_distance.py`
- **3D空間曲線の微分幾何(曲率κ・捩率τ・弧長・Frenet標構)** — 順序付き点列からκ/τ/弧長とFrenet標構を求め、ヘリックスの解析解と相対誤差<0.01%で一致。直線(κ=0)・平面円(τ=0)の零点を判別的に上回り、変速でもGram-Schmidt射影の正しさを確認。 `py -3.11 examples_3d/space_curve.py`
- **円柱点群の前処理と測地距離・中心軸復元(SOR/radius/MLS + kNN/測地/距離リッジ)** — 円柱(半径R=1, 高さ2)を「側面点群」と「中身入りvoxel」の2通りで合成し、6つのopを鎖にして数値的真値で検証する。側面点群(面2400点+遠方の飛び点40点)に対し statistical_outlier_removal と radius_outlier_removal がいずれも飛び点40/40を除去し面の点2400を1つも誤除去せず(SOR→radius合成で面のみ2400点が残存)。mls_smooth が各点の軸までの距離の真値Rからの… `py -3.11 examples_3d/pcl_geodesic.py`
- **点群の鏡映対称面の復元** — 既知平面で鏡映対称な点群から初期推定なしにdetect_reflection_symmetryが対称面を復元: 法線誤差0.0度・鏡映残差1.5e-11。非対称null(残差1.14)は約7.8e10倍大きく、でたらめ平面(最良1.27)も桁違いで判別的。 `py -3.11 examples_3d/reflection_symmetry.py`
- **トーラス結び目の弧長・捩率計測(非平面曲線)** — (2,3)トーラス結び目を密ポリラインで生成しcurve3dのarc_length/curvature_torsionを検証。弧長は台形積分と相対7.6e-7一致・中央|τ|0.283は同長の平面円(捩率6e-10)の5.1e8倍で非平面を判別。円のκ=1/rも誤差7e-13で正確。 `py -3.11 examples_3d/torus_knot_curve.py`
- **恐竜骨格の左右対称面(矢状面)の復元** — スミソニアン三角竜骨格(CC0,10万頂点→4090点stride)をdetect_reflection_symmetryに渡し矢状面を残差2.48で復元(最薄主軸=左右方向に一致)。他2主平面4.28/4.30と区別、片側20%破壊で15.87(6.4倍)へ悪化=左右対称を判別的に検出。未取得時はSKIPしexit0。 `py -3.11 examples_3d/dl_mesh_symmetry.py`
- **回転対称位数の復元(6枚歯スパーギア)** — 歯数6の平歯車リム2160点を生成。detect_rotational_symmetryで対称軸z(|z|=1.000)、約数構造(rotational_symmetry_score)から位数N=6を復元。約数{2,3,6}残差~1e-11・非約数{4,5,7,9,12}>0.5、位数6残差4.3e-11が無対称ランダム1.52の3.5e10倍。 `py -3.11 examples_3d/rotational_symmetry_fold.py`
- **ガウス曲率の符号で表面をドーム/鞍点に分類** — トーラス(R1.0/r0.35)密点群にgaussian_curvatureを当て、外周(楕円K>0)/内周(双曲K<0)を符号で分離精度1.000で分類(解析真値K=cos v/(r(R+r cos v))と一致)。このR,rは外周も内周もH>0なので平均曲率符号null=0.500(分離不能)を判別的に上回る。把持点選び/欠陥判定。 `py -3.11 examples_3d/curvature_shape_index.py`

**range_sensing**
- **360度点群⇄距離画像の往復(球面投影)** — project_spherical→unproject_spherical の往復で形状を保存(誤差<voxel)。奥行きを潰す平面正射影より55倍良い。 `py -3.11 examples_3d/lidar_projection.py`
- **深度画像から法線・遮蔽エッジを読む** — organized 深度から法線(平面で0度誤差)と手前/奥の段差エッジを検出。一次勾配しきい値は平面の傾きを誤検出、二次差分の occlusion_edges は誤検出0。 `py -3.11 examples_3d/range_image.py`

**shape_from_shading**
- **複数光源の陰影から法線・高さを復元(フォトメトリックステレオ)** — 既知光源方向の陰影群から photometric_stereo で法線(誤差0.88度)、integrate_normals で高さ(相関1.0)。単一輝度=高さの素朴推定を大きく上回る。 `py -3.11 examples_3d/photometric_stereo.py`

**structured_light**
- **位相シフト縞投影で高さを復元** — 縞合成→wrapped_phase→unwrap_phase_2d→decode で高さ(RMSE 0.63%)。位相アンラップ無しは2π跳びで88%誤る。 `py -3.11 examples_3d/structured_light.py`
- **Gray code 構造化光の絶対デコード** — 物体で湾曲した投影機コラム番号(0..127)をGray codeビット面7枚からgraycode_decodeで絶対復号。全12288画素で整数厳密一致(100%)。極性反転(0%)/面順取り違え(13%)/最頻値決め打ち(2%)のnullを判別的に上回る。撮影ノイズ42%まで厳密。 `py -3.11 examples_3d/graycode_structured_light.py`

**deformable_registration**
- **TPSベースの非剛体位置合わせ** — 既知TPS曲げ変形をかけた標的へ register_nonrigid で位置合わせし残差をノイズ床へ。剛体ICPは曲げを吸収できず残差が大きい(制御点で tps_warp が厳密に写ることも確認)。 `py -3.11 examples_3d/nonrigid_deform.py`

**augmentation**
- **点群データ拡張(回転/スケール/ドロップアウト/ジッタ)** — 学習用の点群拡張4種を指定パラメータどおり適用(回転=距離不変・向き変化、scale倍率、dropout点数、jitter std)。恒等nullを判別的に上回り、連鎖でも複合性質を保つ。 `py -3.11 examples_3d/augment_pointcloud.py`

**freeform_geometry**
- **B スプライン自由曲線・自由曲面の復元と計測** — 直線・平面・円のような大域基底では表せない「くねる曲線」「うねる曲面」を区分多項式(B スプライン)で復元し、再サンプル・平滑・残差計測まで 1 本に通す事例。曲面側は既知の f(x,y)=0.7 sin(1.6x)cos(1.3y)+0.3xy を散布 600 点から fit_bspline_surface で双三次フィットし、学習外の内部格子で eval_bspline_surface した値が解析真値と RMS 1.5e-3(大域平均 null 0.… `py -3.11 examples_3d/bspline_freeform.py`

**match_localize**
- **3-D テンプレート定位(NCC/形状/chamfer/Hough/MIP/曲率)** — 同一の合成シーン(滑らかな充実球=ターゲット と、球と同一ピーク濃度の立方体=おとり を離して配置)に対し、match3d の 6 定位手法を全て当てて、球テンプレートの中心を真値±2 voxel(実測の 6 手法合議 spread は 0.87vox)で復元できることを検証する事例。球は表面点群(match_points_ncc 用)と解析的 smooth 占有場(voxel 5 手法用)を同一幾何から生成し(bounds=(0,N-1) で world… `py -3.11 examples_3d/matching_localize.py`

**scene_flow**
- **動く物体のシーンフローを点群・ボクセル・画像平面の3表現で復元** — 2時刻の同一物体を3つの見え方から観測し、既知の真値(剛体運動 R_gt=2度・t_gt<0.3、ボクセル並進 shift=[1.5,-2,1]、画素並進)を握って合成し、5つの op を鎖でつないで運動を復元・検証する。表現1(点群): estimate_flow が小運動で最近傍対応恒等(実測 1.000)となりフローが真の変位と機械精度一致(誤差 0.0)、その対応から fit_rigid が Kabsch で (R,t) を復元(回転誤差 1.7e… `py -3.11 examples_3d/motion_scene.py`

**pose_refinement**
- **姿勢・ピーク精緻化(Newton/LM/LK/回転GN/点-面ICP)** — 粗いマッチ(整数ボクセル/±3度級)を連続座標・連続角へ締め上げる 5 種の精緻化器を、既知真値の合成データで一括検証する。帯域制限した滑らかな解析場 F を整数格子(scene)と既知の分数オフセット格子(template)からサンプルし、「同一の真の並進」を refine_peak_newton(相関スコア山の整数ピーク→サブボクセル)・refine_translation_lk(逆合成 LK, corner 規約)・refine_lm(LM, cen… `py -3.11 examples_3d/refinement.py`

**representation**
- **3-D データ表現の相互変換ハブ(点群↔ボクセル↔メッシュ↔SDF↔深度↔TSDF)** — 半径・中心が既知の球(と、登録用に非対称な段付きブロック)を共通の被写体に、fullseye の 3-D 表現変換 op を 1 本の鎖に繋いで「表現を変えても物体の幾何が保たれる」ことを解析真値で検証する事例。depth→depth_to_points で球面点を厳密復元(median|d-R|=6.7e-16)、mesh_to_voxel と gaussians_to_voxel が同一格子上に同じ殻を作り occupancy IoU=0.454(ずら… `py -3.11 examples_3d/transforms_repr.py`

**mesh_process**
- **三角形メッシュの平滑化(Laplacian/Taubin・非収縮)** — ノイズメッシュを接続グラフ上で平滑化。RMS 0.627→Laplacian 0.306/Taubin 0.215。Taubin は平均半径ズレ0.025で Laplacian 0.298 の約1/12=非収縮。marching cubes/スキャン後処理向け。 `py -3.11 examples_3d/mesh_smooth.py`
- **メッシュ簡略化(QEM edge-collapse)で目標面数へ軽量化** — 球1280面→384面(目標厳密)、頂点は球面上・watertight維持・対称Hausdorff 3.3%R。同数までランダム間引くnullは穴792本・Hausdorff 21.3%Rで6.4倍劣る。スキャン/CADの軽量化。 `py -3.11 examples_3d/mesh_decimate.py`
- **メッシュの法線・表面積・平均曲率(接続情報から)** — 面/頂点法線・表面積・cotangent平均曲率を面の巻き順とラプラシアンから測る。球(R2.5)で面積誤差0.12%・曲率0.4000(1/R)・法線外向き率1.00。面積null(49.7%誤差)・平面曲率nullを判別的に上回る。 `py -3.11 examples_3d/mesh_props.py`
- **DL実データメッシュの多段LOD間引き(QEM)** — DL版Stanford Bunny(6.9万面)をQEMで50/25/10%へ間引き。面数34725→17361→6944と単調減少・Hausdorff/diag<=0.020・Chamfer/diag<=0.0024(1/10面でも平均誤差一定)。同面数ランダムドロップ(0.0034)に平均誤差で勝ち、片側クロップnullはHausdorff0.59=30倍で帯外。未取得時はSKIPしexit0。 `py -3.11 examples_3d/mesh_lod_download.py`

**decimation**
- **点群の間引き(voxel grid / farthest-point)で密度を均す** — 6万点の密度ムラ点群をvoxel格子(重心集約, カバレッジ0.134<=理論0.260)とFPS(0.097)で間引き。同数のランダム間引き(0.310, 穴あり)を判別的に上回る。LiDAR/深度カメラの前処理でICP・特徴計算を軽くする。 `py -3.11 examples_3d/pointcloud_downsampling.py`
- **ボリューム(3D CT)の間引き — max/mean プールの使い分け** — 260^3=1758万ボクセル(Frangi上限超過で拒否)を4倍間引きして上限内へ。既知8欠陥をmaxプールは8/8保持・meanプールは0/8にwashout。微小欠陥検出にはmaxが正しいことを計数で判別的に示す。工業CT/ラミノグラフィの前処理。 `py -3.11 examples_3d/volume_downsampling.py`

**optics**
- **スネル屈折とフレネル反射(解析GT検証)** — match3dの光線光学opを閉じた式で検証。Snell残差1e-16・屈折角一致3.9e-14度、Fresnel垂直入射0.040=解析値・grazing→1・臨界角超で全反射(NaN/None/1.0)。無屈折null(屈折角が平均20.5度ずれ)を判別的に棄却。 `py -3.11 examples_3d/snell_refraction.py`

**rendering**
- **レンダリング品質: アンビエントオクルージョン(接触影・凹部の環境影)** — 物体空間AOで半球到達性を[0,1]化。平面に載る球で頂上AO1.00/接触部0.06(高さとSpearman1.00)、溝は深さに単調低下。一様AO=1(null)は凹凸を判別不能。拡散のみのLambertianに乗算し立体感を出す。 `py -3.11 examples_3d/render_ao.py`
- **レンダリング品質: キャスト/ソフトシャドウ(接地影)** — shadow mappingで接地影。球を床に載せ解析GTだ円とIoU 0.978。影なし(従来陰影)はIoU 0.00(接地影を全く当てられない)を判別的に上回る。半影は光源角サイズで単調に拡大。 `py -3.11 examples_3d/render_shadow.py`
- **レンダリング品質: matcap/Phong鏡面シェーディング** — 拡散のみに鏡面を追加。Phongハイライトのピークが反射方向N=norm(L+V)と0.63px一致。Lambertianの最輝点は反射方向を54px外す(nullを約85倍上回る)。matcapはlit-sphere転写で素材感を持ち込む。 `py -3.11 examples_3d/render_shade.py`
- **レンダリング品質: スーパーサンプリング(SSAA)でジャギー除去** — ss倍レンダ→面積平均縮小。傾き22°エッジでエイリアスエネルギー0.275→0.164(0.59倍)・中間輝度画素0%→0.95%、ss=1..6で単調減少。z-bufferの階段状シルエットを滑らかに。 `py -3.11 examples_3d/render_ssaa.py`
- **レンダリング品質: トーンマップ(HDR→LDR)で白飛び救済** — 鏡面HDR(max5.41)をReinhard/ACESで[0,1]へ。全域Spearman1.00で単調、素朴クリップがハイライト域を1段に潰す(分散0)のに対し順位相関1.0・194段の階調を保持。 `py -3.11 examples_3d/render_tonemap.py`
- **レンダリング品質: hero レンダラ render_beauty(全層合成の映える静止3D)** — ラスタライズ/Phong鏡面/AO/接地影/SSAA/トーンマップを1本に合成。sphere-on-groundで各層を実測: AOは接触凹部を0.07→0.02と選択的に暗化(露出頂部0.01は不変)、鏡面は小面積ハイライト(frac0.018)、接地影はwith-mesh993px vs null0px、reinhardは単調(clip34段潰しを回避)、SSAAはedge0.040→0.026。sdf_ops生成メッシュでhero画像を出力。 `py -3.11 examples_3d/render_beauty.py`

## スタンドアロン幾何/数学モジュール(関数 API)

1画像パイプラインに乗らない op(2画像・点列・可変引数)。関数として呼ぶ。

### `imagemorph` — imagemorph — 対応点(ランドマーク)駆動の2D画像ワープとモーフ。

- `warp_piecewise_affine(img, src_pts, dst_pts, order=1)` — img の src_pts にある内容を dst_pts へ動かす区分アフィンワープ。
- `warp_tps_image(img, src_pts, dst_pts, lam=0.0, order=1)` — 薄板スプラインで img の src_pts を dst_pts へ動かす滑らかなワープ。
- `blend(a, b, alpha)` — クロスディゾルブ (1-alpha)·a + alpha·b(a,b は同 shape・[0,1])。
- `morph(imgA, imgB, ptsA, ptsB, alpha, method='affine', lam=0.0, with_corners=True)` — 2 枚の画像 A, B を対応点でモーフし、比率 alpha の中間画像を作る。
- `morph_sequence(imgA, imgB, ptsA, ptsB, n=7, method='affine', lam=0.0, with_corners=True)` — alpha を 0→1 に n 段で振ったモーフ列(A から B へ滑らかに変わる各フレーム)。
- `add_frame_corners(pts, shape)` — 点群に画像の四隅(+辺の中点)を固定点として足す。

### `fourierdesc` — fourierdesc — 閉輪郭の楕円フーリエ記述子(EFD)と複素フーリエ平滑化。

- `elliptic_fourier(points, n_harmonics=10)` — 閉輪郭の楕円フーリエ係数を Kuhl–Giardina 閉形式で求める。
- `reconstruct(model, n_points=300, n_harmonics=None)` — EFD 係数から輪郭を再構成する((M,2))。
- `normalize(model, size_invariant=True)` — EFD 係数を「正準ポーズ」の係数へ変換する(第1高調波を基準に整列)。
- `invariants(model, scale_invariant=True)` — 回転・平行移動・始点・(任意で)スケールに不変な形状記述子((N,2))。
- `descriptor_distance(m1, m2, n_harmonics=None, scale_invariant=True)` — 2 つの形状間の距離(小さいほど似た形)。回転/平行移動/始点/(任意で)スケール不変。
- `fourier_smooth(points, keep)` — 輪郭を複素 FFT で帯域制限して平滑化する。
- `from_xld(contour, i=0)` — XLD 輪郭 dict(``{"shape", "cs":[Nx2,...]}``)から i 番目の輪郭を取り出す。

### `imagedraw` — imagedraw — 画像配列に直接マーカー/線/円/輪郭を焼き込むラスタ描画op(numpy)。

- `draw_line(img, p0, p1, color=1.0, width=1)` — (x,y)=p0 から p1 へ太さ width の直線を描く。
- `draw_polyline(img, points, color=1.0, width=1, closed=False)` — 点列 (N,2) を結ぶ折れ線を描く(closed=True で始点に戻る=多角形)。
- `draw_circle(img, center, radius, color=1.0, width=1, fill=False)` — 中心 (x,y)・半径 radius の円(fill=True で塗り潰し)。
- `draw_markers(img, points, color=1.0, size=4, shape='cross', width=1)` — 点列 (N,2) の各点にマーカーを描く。shape='cross'|'square'|'dot'。
- `draw_contour(img, contour, color=1.0, width=1)` — XLD 輪郭 ``{cs:[Nx2 (row,col),...]}`` または (N,2) 配列を閉じて描く。

### `signal1d` — signal1d — 点列(1D 信号)の多項式近似・フーリエ変換・ローパス/ハイパス(簡単API)。

- `poly_fit(x, y, degree)` — 点列 (x, y) を次数 degree の多項式で最小二乗近似し、係数を返す(最高次から)。
- `poly_eval(coef, x)` — 多項式係数 coef(最高次から)を点 x で評価する。
- `fft_spectrum(y, sample_spacing=1.0)` — 点列 y の片側振幅スペクトルを返す ``(freqs, magnitude)``。
- `lowpass(y, cutoff=0.2)` — 点列 y をローパス(高周波=ノイズ/細部を落として平滑化)。cutoff=ナイキスト割合。
- `highpass(y, cutoff=0.2)` — 点列 y をハイパス(トレンド=低周波を除き、細部・エッジ・変動だけ残す)。
- `bandpass(y, low=0.1, high=0.4)` — 点列 y のバンドパス(low..high の中間帯だけ通す)。low<high(ナイキスト割合)。
- `smooth(y, window=5)` — 移動平均による平滑化(window は奇数の窓幅、端はエッジ複製)。
- `spline_fit(x, y, smooth=0.0)` — 点列 (x, y) を3次スプラインで補間/平滑化し、評価可能な spline object を返す。
- `spline_eval(spline, x)` — spline object を点 x で評価する。
- `spline_resample(x, y, n, smooth=0.0)` — 点列を n 点に等間隔で滑らかに再サンプルし ``(x_new, y_new)`` を返す。
- `spline_curve_fit(points, closed=False, smooth=0.0)` — 点列を **弧長パラメトリック3次スプライン** で当てはめる(2D 輪郭 / 3D 空間曲線)。
- `spline_curve_eval(model, t)` — 曲線スプライン model をパラメータ t∈[0,1] で評価し (M,D) 点を返す(D=2 or 3)。
- `spline_curve_resample(points, n, closed=False, smooth=0.0)` — 曲線点列を n 点に滑らかに再サンプルして (n,D) を返す(2D/3D、閉曲線はシーム非重複)。

## 3-D operators(ops3d)by category
_計 310 ops / 63 categories。_


### augment(6)
- `jitter` (`points → points`) — 各点に等方ガウスノイズ ``N(0, sigma)`` を付加(センサ位置ノイズの模倣)。 · 例: `augment_pointcloud`
- `random_rotation` (`points → points`) — ランダム回転を適用し ``(rotated, R)`` を返す(視点変化の模倣)。 · 例: `augment_pointcloud`, `sh_descriptor_retrieval`, `shape_retrieval`
- `random_scale` (`points → points`) — 一様スケール ``s ~ U(lo, hi)`` を原点まわりに適用し ``(scaled, s)`` を返す。 · 例: `augment_pointcloud`
- `random_dropout` (`points → points`) — 点の ``ratio`` 割合をランダム除去し ``(kept, kept_idx)`` を返す(欠損の模倣)。 · 例: `augment_pointcloud`
- `elastic_deform` (`points → points`) — 滑らかな乱数変位場で弾性変形(相関距離 ``sigma``, RMS 振幅 ``alpha``)。 · 例: `sensor_seg`
- `cutout` (`points → points`) — 空間的な軸平行ボックス領域を除去し ``(kept, kept_idx)`` を返す(局所欠損の模倣)。 · 例: `sensor_seg`

### boundary(2)
- `vol_boundary` (`voxel → voxel`) — Boundary shell of a binary volume (the 3-D ``region_boundary``). · 例: `roi_domain_boundary`
- `vol_boundary_points` (`voxel → points`) — Boundary shell as an ``(N, 3)`` point cloud in ``(z, y, x)`` order. · 例: `roi_domain_boundary`

### bounds(4)
- `convex_hull` (`points → mesh`) — Convex hull of a point set -> ``(V, F)`` with outward-oriented triangles. · 例: `hull_bounds`
- `aabb` (`points → primitive`) — Axis-aligned bounding box. Returns ``(min (3,), max (3,))``. · 例: `hull_bounds`
- `obb` (`points → primitive`) — Oriented bounding box by PCA. · 例: `hull_bounds`
- `min_enclosing_sphere` (`points → primitive`) — 点群 (N,3) → 全点を含む(近似)最小包含球 {center(3), radius}。 · 例: `hull_bounds`

### bundle_adjust(3)
- `bundle_adjust` (`pose, points → pose`) — 再投影誤差最小でカメラ姿勢と 3D 点を同時最適化。→ dict{cameras, points, rmse, cost}。 · 例: `bundle_adjust`
- `mean_reprojection_error` (`pose, points → measurement`) — 再投影 RMS 誤差(ピクセル)。 · 例: `bundle_adjust`
- `project` (`points → image2d`) — 3D 点 (n,3) をカメラ (rvec,t,K) で 2D (n,2) に射影(透視除算)。 · 例: `bundle_adjust`

### curvature(5)
- `principal_curvatures` (`points → curvature`) — 各点の主曲率 (k1>=k2)。→ (k1 (N,), k2 (N,))。 · 例: `curvature_grasp`, `itokawa_curvature`
- `mean_curvature` (`points → signal`) — 平均曲率 H=(k1+k2)/2。→ (N,)。向きに依存する量。 · 例: `curvature_shape_index`
- `gaussian_curvature` (`points → signal`) — ガウス曲率 K=k1·k2(法線の反転に不変)。→ (N,)。 · 例: `curvature_grasp`, `curvature_shape_index`
- `shape_index` (`points → descriptor`) — Koenderink の shape index s∈[-1,1] (凸球+1・円柱+0.5・鞍点0・凹球-1)。→ (N,)。 · 例: `curvature_grasp`, `itokawa_curvature`
- `estimate_normals` (`points → normals`) — 外向き(近傍重心から離れる)に統一した点群法線。→ (N,3)。 · 例: `cylinder_axis_metrology`, `feature_register`, `oriented_normals`

### curve(5)
- `curvature_torsion` (`points → pairs`) — 各点の曲率 κ と捩率 τ(再パラメータ化不変な閉形式)。→ (kappa (N,), tau (N,))。 · 例: `space_curve`, `torus_knot_curve`
- `frenet_frame` (`points → frame`) — Frenet 標構(接線 T, 主法線 N, 陪法線 B)を各点で。→ (T, N, B) 各 (Npts,3) 単位ベクトル。 · 例: `space_curve`, `torus_knot_curve`
- `arc_length` (`points → measurement`) — 曲線の累積弧長と全長。→ (cumulative (N,), total float)。 · 例: `space_curve`, `torus_knot_curve`
- `resample_uniform` (`points → points`) — 弧長で等間隔に n 点へ再サンプル(線形補間)。→ (n,3)。 · 例: `bspline_freeform`
- `fit_spline_curve` (`points → points`) — 順序付き 3D 点列を B スプラインで平滑し再サンプル。→ (M,3)。ノイズのある軌跡/エッジの平滑化。 · 例: `bspline_freeform`

### curvilinear(3)
- `polar_unwrap` (`image2d → image2d`) — 画像の円環/円板を (θ×r) 矩形へアンラップ(工業: ラベル/リング/回転体の検査)。 · 例: `curvilinear_proj`
- `cylinder_unwrap` (`voxel → voxel`) — voxel の円筒面を (height×θ×r) へアンラップ(円筒部品/配管の内外面検査)。軸=z(D 軸)。 · 例: `curvilinear_proj`
- `fit_zernike` (`image2d → descriptor`) — 円板画像 → Zernike 係数(光学/波面計測の**極座標曲面近似**)。返り値 {(n,m): coef}。 · 例: `curvilinear_proj`

### deform(4)
- `tps_fit` (`points, points → deformation`) — 3D Thin-Plate-Spline を制御点対応から当てはめる。 · 例: `nonrigid_deform`
- `tps_warp` (`deformation, points → points`) — TPS モデルで点群を変形する。 · 例: `nonrigid_deform`
- `register_nonrigid` (`points, points → points`) — 非剛体 ICP で ``src`` を ``dst`` へ寄せる。 · 例: `nonrigid_deform`
- `register_cpd_rigid` (`points, points → pose`) — Coherent Point Drift(CPD)剛体版で回転+並進を EM 推定する。 · 例: `motion_scene`

### depth_denoise(3)
- `bilateral_filter_depth` (`depth → depth`) — 深度画像の bilateral filter(段差保存デノイズ)。→ float64 (H,W)。 · 例: `depth_denoise`
- `joint_bilateral` (`depth, image2d → depth`) — joint / cross bilateral: 平滑対象は depth、range 重みは guide の差で作る。→ float64 (H,W)。 · 例: `sensor_seg`
- `fill_holes` (`depth → depth`) — 無効画素(穴)を近傍有効画素から調和(ラプラス)緩和で補間。→ float64 (H,W)。 · 例: `depth_denoise`

### describe(2)
- `sh_descriptor` (`voxel → descriptor`) — 球面調和記述子。同心球 shell の SH 帯域エネルギー ‖f_l(r)‖ を (半径 × 周波数) で返す。 · 例: `sh_descriptor_retrieval`, `shape_descriptor`
- `match_sh_descriptor` (`voxel, voxel → measurement`) — SH 記述子同士のコサイン類似度(回転不変な形状照合)。1 に近いほど同形状。voxel × SH 列。 · 例: `sh_descriptor_retrieval`, `shape_descriptor`

### detect(2)
- `hough_plane_3d` (`voxel → primitive`) — 平面検出(2D Hough 直線の 3D リフト)。勾配=法線を使い (法線 n, 距離 d) 空間へ投票。 · 例: `detect_primitives_3d`
- `hough_sphere_3d` (`voxel → primitive`) — 球検出(2D Hough 円の 3D リフト)。中心 = p + sgn·r·n を半径 r ごとに投票。 · 例: `detect_primitives_3d`

### domain(5)
- `vol_reduce_domain` (`voxel, voxel → voxel`) — Restrict a volume to a *domain* mask (HALCON ``reduce_domain``, voxel-wise). · 例: `roi_domain_boundary`
- `vol_bounding_box` (`voxel → primitive`) — Tight axis-aligned bounding box of a mask's foreground, in voxel indices. · 例: `rle_region_efficiency`, `roi_domain_boundary`
- `vol_crop_domain` (`voxel → voxel`) — Crop a volume to the tight bounding box of a domain (HALCON ``crop_domain``). · 例: `roi_domain_boundary`
- `vol_uncrop` (`voxel → voxel`) — Paste a cropped sub-volume back into the full frame (inverse of · 例: `roi_domain_boundary`
- `vol_tiled_map` (`voxel → voxel`) — Apply a shape-preserving volume operator in overlapping z-slabs, so peak · 例: `rle_region_efficiency`

### edges(5)
- `gradient3d` (`voxel → gradient`) — ガウス平滑後の中心差分勾配を計算する。 · 例: `edges_3d`
- `canny3d` (`voxel → voxel`) — 3D Canny エッジ検出(非最大抑制 + ヒステリシス)。 · 例: `edges_3d`
- `log_zero_crossings` (`voxel → voxel`) — Laplacian-of-Gaussian のゼロ交差エッジ。 · 例: `edges_3d`
- `link_edges` (`voxel → voxel`) — エッジ mask を 26 近傍で連結成分ラベリングする。 · 例: `sensor_seg`
- `edge_points` (`voxel → points`) — エッジ mask を (M,3) の座標点群にする(下流の chamfer / Hough 用)。 · 例: `edges_3d`

### feature(9)
- `sobel3d` (`voxel → gradient`) — 3D 勾配 (gz,gy,gx)。導関数[-1,0,1]×平滑[1,2,1] の分離 conv3d。 · 例: `diff_features`
- `hessian3d` (`voxel → hessian`) — 3D Hessian の 6 独立成分 (fzz,fyy,fxx,fzy,fzx,fyx)。分離 conv3d(2 階/1 階×平滑)。 · 例: `diff_features`
- `curvature_maps` (`voxel → curvature`) — level-set の主曲率 → shape index S(Koenderink)と curvedness。閉形式(Kindlmann 2003)。 · 例: `diff_features`
- `edt_jfa` (`voxel → sdf`) — 3D ユークリッド距離変換 = Jump Flooding Algorithm(GPU)。各 voxel → 最近 seed 距離。 · 例: `diff_features`
- `vol_frangi` (`voxel → voxel`) — 3-D Frangi vesselness — multiscale tubular-structure enhancement. · 例: `vessel_metrology`, `volume_downsampling`
- `vol_sato` (`voxel → voxel`) — 3-D Sato tubeness — the simpler two-eigenvalue line filter. · 例: `vessel_metrology`
- `vol_hessian_blobness` (`voxel → voxel`) — Blob-like (spherical) response from the Hessian eigenvalues at one *scale*. · 例: `vessel_metrology`
- `vol_gradient_magnitude` (`voxel → voxel`) — 3-D Sobel gradient magnitude ``sqrt(gz**2 + gy**2 + gx**2)``. · 例: `vessel_metrology`
- `vol_local_maxima` (`voxel → points`) — 3-D local-maxima (peak) detection. · 例: `molecule_atom_count`, `vessel_metrology`

### feature_register(7)
- `harris3d_keypoints` (`voxel → keypoints`) — 3D Harris キーポイント検出(2D Harris コーナー検出の 3D 版)。 · 例: `feature_register`
- `iss_keypoints` (`points → indices`) — ISS(Intrinsic Shape Signatures、3D Harris 相当)キーポイント検出。 · 例: `feature_register`
- `compute_fpfh` (`points, normals → descriptor`) — FPFH 記述子 (N, 3*n_bins) を計算(Rusu 2009)。 · 例: `fpfh_correspondence`
- `shot_descriptor` (`points, normals → descriptor`) — SHOT 記述子(Tombari 2010)。各キーポイントに LRF を張り、球状支持を · 例: `feature_register`
- `register_spin` (`points, points → pose`) — Spin Image 記述子 + RANSAC による初期推定なし疎特徴剛体位置合わせ。 · 例: `feature_register`
- `register_fpfh` (`points, points → pose`) — FPFH 記述子 + RANSAC で **初期推定なし** の剛体位置合わせ (R,t) を推定する。 · 例: `feature_register`
- `register_shot` (`points, points → pose`) — SHOT 記述子による疎特徴マッチング + RANSAC 剛体姿勢推定(全パイプライン)。 · 例: `feature_register`

### freeform(5)
- `fit_bspline_surface` (`points → surface`) — 散布 (x, y, z) に双三次(既定)B スプライン曲面を最小二乗フィット(bisplrep)。 · 例: `bspline_freeform`
- `eval_bspline_surface` (`surface → image2d`) — フィット済み曲面 tck を評価(bisplev)。散布点(既定)または格子の 2 モード。 · 例: `bspline_freeform`
- `surface_residual` (`points, surface → measurement`) — 散布データと曲面 tck の残差統計を返す(形状誤差=フィットからの逸脱)。 · 例: `bspline_freeform`
- `fit_bspline_curve` (`points → surface`) — 順序付き点列(M,D)に B スプライン曲線をフィット(splprep, パラメトリック)。 · 例: `bspline_freeform`
- `eval_bspline_curve` (`surface → points`) — 曲線 tck をパラメータ u∈[0,1] 上 n 点で等間隔評価(splev)。 · 例: `bspline_freeform`

### frequency(3)
- `vol_fft_lowpass` (`voxel → voxel`) — Gaussian low-pass: keeps structure coarser than ``1/cutoff`` (voxels, or · 例: `deconv_fft_restore`
- `vol_fft_highpass` (`voxel → voxel`) — Gaussian high-pass — the exact complement ``1 - lowpass`` (the two sum · 例: `deconv_fft_restore`
- `vol_fft_bandpass` (`voxel → voxel`) — Gaussian band-pass ``lowpass(high) - lowpass(low)``: keeps structure · 例: `deconv_fft_restore`

### fusion(2)
- `register_cross` (`any, any → pose`) — 異種構造間の剛体登録。両者を点群へ変換 → 登録器(fpfh=大回転/icp=要 coarse init)。 · 例: `transforms_repr`
- `fuse_to_voxel` (`any → voxel`) — 複数構造を共通密度 voxel へ融合(TRIZ 統合)。items=[(data,kind,params_dict), ...]。 · 例: `transforms_repr`

### geodesic(4)
- `geodesic_distances` (`points → measurement`) — source から全点への測地距離(kNN グラフ上 Dijkstra)。→ (N,) float(不達は inf)。 · 例: `geodesic_distance`
- `geodesic_mesh` (`mesh → measurement`) — 三角メッシュのエッジグラフ上 Dijkstra で source から各頂点への測地距離。→ (V,) float。 · 例: `pcl_geodesic`
- `farthest_point_sampling` (`points → indices`) — 測地距離での最遠点サンプリング(均等間引き)。→ 選択インデックス列 (n,) int。 · 例: `geodesic_distance`, `pointcloud_downsampling`
- `knn_graph` (`points → graph`) — 各点の k 近傍インデックスと Euclid 距離(自己を除く)。→ (idx (N,k) int, dist (N,k) float)。 · 例: `pcl_geodesic`

### geom_transform(3)
- `vol_resize` (`voxel → voxel`) — Resample a volume to a new grid (``scipy.ndimage.zoom``, cell semantics). · 例: `vol_geometry_transform`
- `vol_rotate` (`voxel → voxel`) — Rotate a volume in the plane of an axis pair (``scipy.ndimage.rotate``). · 例: `vol_geometry_transform`
- `vol_affine` (`voxel → voxel`) — General affine resampling (``scipy.ndimage.affine_transform``). · 例: `vol_geometry_transform`

### geometry(23)
- `line_from_2points` (`points → primitive`) — 2 点 → 直線(通過点, 単位方向)。2 座標で線が定まる(2D/3D 共通)。 · 例: `geometry_metrology`
- `plane_from_3points` (`points → primitive`) — 3 点 → 平面(通過点, 単位法線)。3 座標で面が定まる(2D/3D 共通)。 · 例: `geometry_metrology`
- `angle_3points` (`points → measurement`) — 3 点のなす角(頂点 b、度)。∠ABC。 · 例: `geometry_metrology`
- `angle_between_lines` (`primitive → measurement`) — 2 直線方向のなす鋭角(度)。 · 例: `geometry_metrology`
- `angle_between_planes` (`primitive → measurement`) — 2 平面の二面角(法線 n1,n2、度)。 · 例: `geometry_metrology`
- `angle_line_plane` (`primitive → measurement`) — 直線(方向 d)と平面(法線 n)のなす角(度)。 · 例: `geometry_metrology`
- `distance_point_plane` (`points, primitive → measurement`) — 点-平面距離(符号なし)。 · 例: `geometry_metrology`
- `distance_point_line` (`points, primitive → measurement`) — 点-直線距離。 · 例: `geometry_metrology`
- `distance_line_line` (`primitive → measurement`) — 2 直線間距離(ねじれの位置=skew も可)。平行なら点-線距離に退避。 · 例: `geometry_metrology`
- `intersect_line_plane` (`primitive → position`) — 直線 ∩ 平面 → 点(平行なら None)。 · 例: `geometry_metrology`
- `intersect_planes` (`primitive → primitive`) — 平面 ∩ 平面 → 直線(通過点, 方向)。平行なら None。 · 例: `geometry_metrology`
- `fit_line_3d` (`points → primitive`) — 点群 → 最小二乗直線(通過点=重心, 方向=最大主軸)。返り値 (point, direction)。 · 例: `geometry_metrology`
- `fit_plane_3d` (`points → primitive`) — 点群 → 最小二乗平面(通過点=重心, 法線=最小主軸, 残差 RMS)。返り値 (point, normal, resid)。 · 例: `geometry_metrology`
- `fit_sphere_3d` (`points → primitive`) — 点群 → 最小二乗球(代数フィット)。返り値 (center, radius)。配管/ボール計測に。 · 例: `geometry_metrology`
- `fit_circle_3d` (`points → primitive`) — 点群 → 3D 円(平面フィット → 面内で 2D 円フィット)。返り値 (center, radius, normal)。 · 例: `geometry_metrology`
- `fit_line3` (`points → primitive`) — Total-least-squares 3-D line fit to ``(depth, row, col)`` points — the · 例: `primitive_fitting_3d`
- `fit_plane3` (`points → primitive`) — Least-squares 3-D plane fit to ``(depth, row, col)`` points — the plane · 例: `primitive_fitting_3d`
- `fit_sphere3` (`points → primitive`) — Algebraic (Kåsa) least-squares sphere fit to ``(depth, row, col)`` points: · 例: `primitive_fitting_3d`, `roi_domain_boundary`
- `fit_circle3` (`points → primitive`) — 3-D circle fit to ``(depth, row, col)`` points: fit the supporting plane, · 例: `primitive_fitting_3d`
- `smallest_box3_axis` (`points → primitive`) — Axis-aligned bounding box (the 3-D ``smallest_rectangle1``). Returns the · 例: `oriented_bounding_box`
- `fit_box3` (`points → primitive`) — Oriented box fit by PCA (fast, noise-tolerant; the same construction as · 例: `oriented_bounding_box`
- `smallest_box3` (`points → primitive`) — Near-minimum-volume oriented bounding box (the 3-D ``smallest_rectangle2``). · 例: `oriented_bounding_box`
- `smallest_sphere3` (`points → primitive`) — Minimum enclosing sphere of ``(depth, row, col)`` points (Welzl's exact · 例: `primitive_fitting_3d`

### gicp(2)
- `gicp` (`points, points → pose`) — Generalized-ICP(共分散重みマハラノビス ICP)で剛体変換 (R,t) を推定する。 · 例: `gicp_register`
- `estimate_covariances` (`points → descriptor`) — 各点の局所共分散を固有値 (ε,1,1) に置換した plane-to-plane 共分散 (N,3,3)。 · 例: `gicp_register`

### gray(4)
- `vol_window_level` (`voxel → voxel`) — CT window/level (HU windowing) — the radiologist's daily linear remap. · 例: `gray_window_level`
- `vol_equalize` (`voxel → voxel`) — Histogram equalisation of a volume (HALCON ``equ_histo_image``). · 例: `gray_window_level`
- `vol_gamma` (`voxel → voxel`) — Gamma (power-law) correction on the volume's own range (HALCON ``pow_image``). · 例: `gray_window_level`
- `vol_stretch` (`voxel → voxel`) — Percentile contrast stretch to ``[0, 1]`` (robust ``scale_image_max``). · 例: `gray_window_level`

### lidar_projection(3)
- `project_spherical` (`points → image2d`) — 回転式 LiDAR の球面レンジ画像へ投影 (v_res, h_res)。空セル=0, 近い点優先(最小 range)。 · 例: `lidar_projection`
- `unproject_spherical` (`image2d → points`) — 球面レンジ画像 → 3D 点 (M, 3)。range>0 のセルのみをビン中心角で逆投影。 · 例: `lidar_projection`
- `project_cylindrical` (`points → image2d`) — 円柱レンジ画像へ投影 (z_bins, h_res)。方位角(列)× z(行)、画素=水平半径 ρ=hypot(x,y)。 · 例: `curvilinear_proj`

### match_localize(6)
- `match_shape_3d` (`voxel, voxel → position`) — 3D 形状ベース(勾配方向)マッチング = 2D shapematch_gpu の voxel 版(「輪郭マッチング」)。 · 例: `matching_localize`
- `match_chamfer_3d` (`voxel, voxel → position`) — chamfer / 距離場マッチング(部分・遮蔽に頑健)。voxel × chamfer 列。 · 例: `matching_localize`
- `match_curvature_3d` (`voxel, voxel → position`) — 曲率(shape index)マッチング。voxel × 曲率列(線→面リフトの本丸)。 · 例: `matching_localize`
- `match_hough_3d` (`voxel, voxel → position`) — generalized Hough 3D(Ballard R-table 投票)。voxel × Hough 列。 · 例: `matching_localize`
- `match_mip_2d` (`voxel, voxel → position`) — MIP 投影 → 2D NCC(構造=voxel → 2D × 手法=NCC、変換=直交 MIP)。 · 例: `matching_localize`
- `match_points_ncc` (`points, points → position`) — 点群同士マッチング(構造=point cloud × 手法=NCC、変換=splat)。model を scene 内で定位。 · 例: `matching_localize`

### match_pose(4)
- `match_phase_3d` (`voxel, voxel → shift`) — 3D 位相相関(FFT)。b を a に合わせる整数シフト (dz,dy,dx) を返す。 · 例: `shape_desc_pose`
- `match_pca` (`points, points → pose`) — PCA 姿勢マッチング(構造=point cloud × 手法=主軸整列)。 · 例: `shape_desc_pose`
- `moment_axes` (`points → axes`) — 点群/重み付き点の **重心 + 主軸**(慣性テンソルの固有ベクトル)。姿勢推定の基礎。 · 例: `itokawa_pose_canonical`
- `match_logpolar_z` (`voxel, voxel → rot_scale`) — log-polar × 位相相関(Fourier-Mellin)で **z 軸回転 + 等方スケール**を復元。 · 例: `shape_desc_pose`

### medial(10)
- `distance_ridge` (`voxel → voxel`) — EDT のリッジ(距離場の局所極大)を medial として抽出。返り値 (ridge_mask, edt)。 · 例: `pcl_geodesic`
- `skeletonize_vol` (`voxel → voxel`) — 3D バイナリ voxel を細線化して 1 voxel 幅の骨格に。skimage の Lee(1994)法ラッパ。 · 例: `medial_topology`
- `medial_axis_points` (`voxel → points`) — medial voxel の座標と局所半径(= その点の EDT 値)を点群化。返り値 (points, radius)。 · 例: `medial_topology`
- `topology_signature` (`voxel → descriptor`) — 骨格の 26 近傍次数から位相記述子を作る。端点/分岐点/通常点/孤立点の個数を返す。 · 例: `medial_topology`
- `medial_match` (`voxel, voxel → measurement`) — 2 つの voxel 形状の medial(位相 + 半径分布)による粗照合スコア。返り値 [0,1]。 · 例: `medial_topology`
- `skeleton_junctions3d` (`voxel → voxel`) — 3D 骨格の分岐点(joint、26 近傍に骨格 voxel が 3 個以上)を voxel マスクで返す。 · 例: `medial_topology`
- `skeleton_endpoints3d` (`voxel → voxel`) — 3D 骨格の端点(26 近傍に骨格 voxel が 1 個以下)を voxel マスクで返す。 · 例: `medial_topology`
- `skeleton_prune3d` (`voxel → voxel`) — 3D 骨格のヒゲ(短い枝)を刈る。端点除去を length 回反復 = 枝長 <=length を除去。 · 例: `medial_topology`
- `skeleton_branches3d` (`voxel → voxel`) — 3D 骨格を分岐点で切って枝(線分)に分割する。2D の `r2_split_skeleton_lines` の 3D 版。 · 例: `medial_topology`
- `vol_distance_transform` (`voxel → voxel`) — Exact Euclidean distance transform of a binary volume. · 例: `molecule_atom_count`, `vessel_metrology`

### mesh_process(7)
- `laplacian_smooth` (`mesh → mesh`) — umbrella Laplacian による三角形メッシュ平滑化。→ (verts, faces)。 · 例: `mesh_smooth`
- `taubin_smooth` (`mesh → mesh`) — Taubin λ|μ フィルタによる **非収縮** 平滑化。→ (verts, faces)。 · 例: `mesh_smooth`
- `decimate_qem` (`mesh → mesh`) — Quadric-error-metric edge-collapse decimation toward *target_faces*. · 例: `mesh_decimate`, `mesh_lod_download`
- `face_normals` (`mesh → normals`) — 三角形メッシュの**面法線**(各三角形の単位法線ベクトル)。→ (M,3)。 · 例: `mesh_props`
- `vertex_normals` (`mesh → normals`) — 三角形メッシュの**頂点法線**(面積重み付きで集約した単位法線)。→ (N,3)。 · 例: `mesh_props`
- `mesh_area` (`mesh → measurement`) — 三角形メッシュの**表面積**(全三角形面積の総和)。→ float。 · 例: `dl_mesh_curvature`, `mesh_props`
- `vertex_curvature` (`mesh → curvature`) — 三角形メッシュの各頂点の**平均曲率の大きさ**(mean curvature magnitude)。→ (N,)。 · 例: `dl_mesh_curvature`, `mesh_props`

### metrics(7)
- `chamfer_distance` (`points, points → measurement`) — 対称 Chamfer 距離 = 0.5*(mean_a min_b + mean_b min_a)。→ scalar。小さいほど一致。 · 例: `itokawa_pose_canonical`, `itokawa_shape_match`, `mesh_lod_download`, `poisson_surface_recon`
- `hausdorff_distance` (`points, points → measurement`) — 対称 Hausdorff 距離 = max(max_a min_b, max_b min_a)。→ scalar。最悪ケースの乖離。 · 例: `mesh_lod_download`, `pointcloud_downsampling`, `poisson_surface_recon`
- `fscore` (`points, points → measurement`) — F-score @ tau = precision と recall の調和平均。→ (f, precision, recall)。再構成の標準指標。 · 例: `metrics_eval`
- `rmse_correspondence` (`points, points → measurement`) — 対応既知(同 index)の RMSE = sqrt(mean |a_i - b_i|^2)。→ scalar。登録残差の評価。 · 例: `metrics_eval`
- `normal_consistency` (`points, normals → measurement`) — 最近傍対応での法線一致度 = mean|cos(na, nb)|(向き無視)。→ [0,1]。1=完全一致。 · 例: `metrics_eval`
- `voxel_iou` (`voxel, voxel → measurement`) — voxel 占有の IoU(intersection over union)。→ [0,1]。体積一致度。 · 例: `metrics_eval`
- `pose_error` (`pose, pose → measurement`) — 姿勢誤差 = (回転角[度], 並進ノルム)。登録結果の GT 比較。→ (rot_deg, trans_err)。 · 例: `itokawa_self_register`

### moment_invariant(4)
- `moment_invariants` (`points → descriptor`) — 並進+回転+スケール不変な形状特徴ベクトル(Sadjadi–Hall 流 + 高次半径分布)。 · 例: `moment_invariants`
- `principal_moments` (`points → descriptor`) — 慣性テンソルの固有値(主慣性モーメント、降順ソート、回転不変)。 · 例: `shape_desc_pose`
- `central_moments` (`points → descriptor`) — 重心中心化した中心モーメント μ_{pqr}(並進不変、キー=(p,q,r))を返す。 · 例: `moment_invariants`
- `inertia_tensor` (`points → matrix`) — 点群の慣性テンソル (3,3)(中心 2 次モーメントから、等質量・総質量 1)。 · 例: `moment_invariants`

### morphology(7)
- `morph_dilate3d` (`voxel → voxel`) — 3D グレースケール dilation(SE 半径 r の局所 max)。明領域を膨張。 · 例: `morphology_3d`
- `morph_erode3d` (`voxel → voxel`) — 3D グレースケール erosion(SE の局所 min)。明領域を収縮。se は dilate と同じ。 · 例: `morphology_3d`
- `morph_open3d` (`voxel → voxel`) — 3D opening = erosion → dilation。SE より小さい**明構造(棘・粒)**を除く。 · 例: `morphology_3d`
- `morph_close3d` (`voxel → voxel`) — 3D closing = dilation → erosion。SE より小さい**暗構造(隙間・空洞)**を埋める。 · 例: `morphology_3d`
- `morph_gradient3d` (`voxel → voxel`) — 3D モルフォロジー勾配 = dilation − erosion。**境界/表面**を抽出(sobel 代替のエッジ源)。 · 例: `morphology_3d`
- `morph_tophat3d` (`voxel → voxel`) — 3D white top-hat = vol − opening。SE より小さい **明構造**を抽出(keypoint 前処理)。 · 例: `diff_features`, `morphology_3d`
- `morph_blackhat3d` (`voxel → voxel`) — 3D black-hat = closing − vol。SE より小さい **暗構造/穴**を抽出。 · 例: `diff_features`

### motion(1)
- `scene_flow_lk` (`voxel, voxel → flow`) — Lucas-Kanade scene flow(2D optical flow の 3D 版)。voxel ごとの運動場 d=(dz,dy,dx)。 · 例: `motion_scene`

### motion_segment(3)
- `segment_rigid_motions` (`points, points → labels`) — 2 点群を運動が一致する剛体ごとに分割する(反復 RANSAC による multi-body 分割)。 · 例: `motion_seg`
- `estimate_flow` (`points, points → flow`) — pts0 の各点から pts1 の最近傍への 3-D 変位ベクトル場 (N, 3) を返す(最近傍フロー)。 · 例: `motion_scene`
- `fit_rigid` (`points, points → pose`) — 対応点から閉形式 Kabsch で剛体変換 (R, t) を推定する(pts_from[i] -> pts_to[i])。 · 例: `motion_scene`

### normals_orient(2)
- `estimate_oriented_normals` (`points → normals`) — PCA 法線推定 + Hoppe 大域向き付けの合成。→ (N,3) の向き付き単位法線。 · 例: `oriented_normals`
- `orient_normals` (`points, normals → normals`) — Hoppe 法で法線を**大域一貫**に向き付け(MST 伝播)。→ (N,3)。 · 例: `oriented_normals`

### occupancy(4)
- `occupancy_grid` (`points → voxel`) — 点群 (N,3) → 3-D 占有ボクセル格子 (res,res,res) bool(点の落ちた voxel を占有)。 · 例: `occupancy_esdf`
- `esdf` (`voxel → sdf`) — 占有格子 → Euclidean 符号付き距離場 (ESDF)(外=+ 最近占有まで, 内=- 最近自由まで)。 · 例: `occupancy_esdf`
- `inflate` (`voxel → voxel`) — 障害物を ``radius``(world 単位)膨張した占有格子 bool(= ESDF<=radius を占有)。 · 例: `sensor_seg`
- `query_distance` (`sdf, points → measurement`) — 任意 world 座標 (M,3) での ESDF 値 (M,) を返す(``mode``='trilinear' 補間 or 'nearest')。 · 例: `occupancy_esdf`

### optics(5)
- `reflect` (`vector, normals → normals`) — 入射方向 d を法線 n の面で鏡面反射。r = d − 2(d·n)n。 · 例: `sensor_seg`, `snell_refraction`
- `refract` (`vector, normals → normals`) — Snell 屈折(ベクトル形)。d=入射(面へ向かう), n=入射側外向き法線, 屈折率 eta1→eta2。 · 例: `snell_refraction`
- `fresnel_reflectance` (`measurement → measurement`) — Fresnel 反射率(無偏光=s/p 平均)。透明体界面で反射/透過に分かれる割合。 · 例: `snell_refraction`
- `normal_from_reflection` (`vector, vector → vector`) — 入射+反射から鏡面の法線を復元(deflectometry)。n ∝ (r − d)、入射に逆らう向きへ。 · 例: `sensor_seg`
- `snell_angle` (`measurement → measurement`) — 入射角(度)→ 屈折角(度)。n1 sinθi = n2 sinθt。臨界角超は NaN(全反射)。 · 例: `snell_refraction`

### photometric(4)
- `photometric_stereo` (`images → normalmap`) — Lambertian フォトメトリックステレオ: 既知光源方向の N 枚から法線とアルベドを復元。→ (normals HxWx3, albedo HxW)。 · 例: `photometric_stereo`
- `surface_normals` (`image2d → normalmap`) — 高さ場 z(HxW)→ 単位法線 (H,W,3)。n ∝ (-dz/dx, -dz/dy, 1)。深度→法線の順変換。 · 例: `photometric_stereo`
- `integrate_normals` (`normalmap → image2d`) — 法線場 → 高さ場 z を Frankot-Chellappa 積分。→ z HxW(定数分の自由度あり・平均0基準)。 · 例: `photometric_stereo`
- `render_lambertian` (`normalmap → image2d`) — 法線 + アルベド + 光源方向 → Lambertian 画像(検査サンプル生成 / GT 検証 / 逆レンダの順方向)。→ HxW。 · 例: `photometric_stereo`, `render_shade`

### plane_sweep_stereo(2)
- `plane_sweep_depth` (`image2d, image2d → depth`) — plane-sweep stereo で密な深度マップを推定。→ (H,W) depth。 · 例: `plane_sweep_depth`
- `warp_by_plane` (`image2d → image2d`) — homography H で img を逆ワープ。→ out[y,x] = img(H·(x,y,1))(bilinear)。 · 例: `motion_scene`

### pose_estimation(3)
- `dlt_pose` (`points, image2d → pose`) — DLT で 3D-2D 対応からカメラ姿勢を復元(K 既知)。→ (R (3,3), t (3,))。6 点以上必要。 · 例: `pnp_pose_outliers`, `pose_estimation`
- `pnp_ransac` (`points, image2d → pose`) — 外れ値に頑健な PnP(RANSAC + 最終 DLT リフィット)。→ (R, t, inlier_mask, info)。 · 例: `pnp_pose_outliers`, `pose_estimation`
- `reprojection_error` (`points, pose → measurement`) — 再投影誤差(RMS ピクセル)。姿勢の当てはまり評価。→ scalar。 · 例: `pnp_pose_outliers`, `pose_estimation`

### pose_graph(3)
- `optimize_pose_graph` (`pose → pose`) — 相対姿勢制約 + ループ閉じから大域姿勢を最適化。→ dict{poses, rmse, cost}。 · 例: `pose_graph_slam`
- `relative_pose` (`pose, pose → pose`) — T_i⁻¹ ∘ T_j = i←j の相対姿勢。pose_* = [rvec|t] (6,)。→ (rvec_ij (3,), t_ij (3,))。 · 例: `pose_graph_slam`, `sfm_recon`
- `mean_edge_error` (`pose → measurement`) — エッジ残差の RMS(姿勢グラフの整合度)。→ scalar。 · 例: `sfm_recon`

### preprocess(5)
- `statistical_outlier_removal` (`points → points`) — 各点の k 近傍平均距離が大域的に外れる点を除去する(統計的外れ値除去)。 · 例: `pcl_geodesic`
- `radius_outlier_removal` (`points → points`) — 半径 radius 内の近傍数が min_neighbors 未満の点を除去する(孤立点除去)。 · 例: `pcl_geodesic`
- `voxel_grid_downsample` (`points → points`) — 辺 voxel_size の格子で点群を間引き、各セルを重心 1 点に集約する(決定論的)。 · 例: `pointcloud_downsampling`
- `mls_smooth` (`points → points`) — 各点を局所多項式曲面へ射影してノイズを落とす(Moving Least Squares 平滑)。 · 例: `pcl_geodesic`
- `volume_downsample` (`voxel → voxel`) — Block-pool a ``(D, H, W)`` volume by an integer *factor* per axis (data 間引き). · 例: `volume_downsampling`

### probe(3)
- `vol_profile_line` (`voxel → pairs`) — Gray-value profile along the straight probe ``p0 -> p1``. · 例: `wall_thickness_probe`
- `vol_edge_probe` (`voxel → table`) — Sub-sample edges along the probe ``p0 -> p1``. · 例: `wall_thickness_probe`
- `vol_wall_thickness` (`voxel → signal`) — Wall thicknesses along the probe ``p0 -> p1`` — the industrial-CT · 例: `wall_thickness_probe`

### range_image(4)
- `depth_to_organized_points` (`depth → pointmap`) — organized 深度画像 → 格子整列 3D 点 (H,W,3)。 · 例: `range_image`
- `normals_from_depth` (`depth → normalmap`) — organized 深度 → 向き付き単位法線 (H,W,3)。隣接画素の 3D 点の外積(格子構造を利用、O(HW))。 · 例: `range_image`
- `occlusion_edges` (`depth → image2d`) — 深度の不連続(前景/背景境界 = 遮蔽エッジ)を検出。→ bool HxW。 · 例: `range_image`
- `bearing_angle_image` (`depth → image2d`) — bearing-angle 画像: 走査方向に沿った視線と局所面のなす角(range image の古典記述子)。→ HxW(度)。 · 例: `sensor_seg`

### reconstruct(4)
- `poisson_lite` (`points → mesh`) — 点群 (N,3) → (vertices(V,3), faces(F,3)) の表面メッシュ(スクリーンド Poisson 軽量近似)。 · 例: `poisson_surface_recon`
- `alpha_shape_mesh` (`points → mesh`) — alpha shapes による**表面三角形メッシュ**(点群 → (vertices, faces))。 · 例: `alpha_shape_topology`
- `alpha_shape_boundary` (`points → points`) — alpha shapes による**境界点インデックス**を返す(点群 → 境界点)。 · 例: `sfm_recon`
- `estimate_alpha` (`points → measurement`) — 点群のスケールから推奨 alpha を返す(最近傍距離の中央値ベース)。 · 例: `alpha_shape_topology`, `sfm_recon`

### refine(6)
- `refine_peak_newton` (`score, position → position`) — スコア/相関 volume の整数ピークを 3D Newton でサブボクセル精緻化する(反復最適化)。 · 例: `refinement`
- `refine_translation_lk` (`voxel, voxel, position → position`) — Gauss-Newton 逆合成 Lucas-Kanade による 3D 並進サブボクセル精緻化。 · 例: `refinement`
- `refine_lm` (`voxel, voxel, position → pose`) — Levenberg-Marquardt による並進(+等方スケール/輝度ゲイン)サブボクセル精緻化。 · 例: `refinement`
- `refine_rotation_z` (`voxel, voxel, angle → angle`) — z 軸回転角の **Gauss-Newton 精緻化**(Lucas-Kanade on SSD、1 パラメータ)。 · 例: `refinement`
- `icp_point2point_3d` (`points, points → pose`) — 点群を point-to-point ICP(Kabsch/SVD)で精緻化する。 · 例: `gicp_register`, `itokawa_self_register`, `itokawa_shape_match`, `partial_overlap_icp`
- `icp_point2plane` (`points, points, normals → pose`) — 点-面 ICP(Gauss-Newton, 小角近似)で剛体変換を高精度に精緻化する。 · 例: `refinement`

### regionprops(7)
- `label_components` (`voxel → voxel`) — 3D 二値ボリュームを連結成分にラベリングする。 · 例: `region_props_3d`, `watershed3d`
- `region_props` (`voxel → table`) — 各連結成分のリージョンプロパティ一覧を返す。 · 例: `region_props_3d`
- `largest_component` (`voxel → voxel`) — 最大(最多ボクセル)連結成分の bool マスクを返す。 · 例: `region_props_3d`
- `filter_by_volume` (`voxel → voxel`) — min_voxels 未満の連結成分を除去した bool マスクを返す。 · 例: `region_props_3d`
- `inner_box3` (`voxel → primitive`) — 二値ボクセル領域に完全に内接する最大の軸平行ボックス(2-D ``inner_rectangle1`` の · 例: `inner_box_inspection`
- `vol_label` (`voxel → labels`) — 3-D connected-component labelling with a selectable neighbourhood. · 例: `ct_bone_segmentation`, `molecule_atom_count`, `vessel_metrology`
- `vol_region_props` (`labels → table`) — Per-component quantitative descriptors from a label volume. · 例: `vessel_metrology`

### registration_metrics(4)
- `inlier_ratio` (`points, points → measurement`) — 対応集合の inlier 率 = ‖T·source[i] − target[i]‖ < thresh の割合。→ [0,1]。 · 例: `pose_estimation`, `ransac_prim`, `reg_eval`
- `rmse_inliers` (`points, points → measurement`) — inlier 対応(残差 < thresh)上の RMSE と inlier 数。→ (rmse, n_inliers)。 · 例: `reg_eval`
- `registration_recall` (`points, points → measurement`) — 3DMatch 流の per-pair 登録成否 = 1.0(成功)/ 0.0(失敗)。 · 例: `reg_eval`
- `rotation_translation_error` (`pose, pose → measurement`) — 2 つの 4×4 変換間の相対回転誤差(測地角[度], RRE)と相対並進誤差(RTE)。 · 例: `reg_eval`

### render(14)
- `project_points` (`points → image2d`) — 3D 点群 (N,3) → 画像座標 (u,v) と深度。ピンホール(depth_to_points の順方向)。 · 例: `pnp_pose_outliers`, `pose_estimation`
- `render_point_depth` (`points → depth`) — 点群 → 深度画像(z-buffer、各画素に最近点の深度)。観測合成/外観検査サンプル。 · 例: `sfm_recon`
- `render_volume_projection` (`voxel → image2d`) — voxel を任意視点で 2D 投影(mode=xray=減衰積算 / mip=最大値)。DRR(X線)・世界モデル観測。 · 例: `ct_hand_radiograph`
- `render_shaded` (`normalmap → image2d`) — 法線マップ (H,W,3) + 光源方向 → Lambertian 陰影画像(外観サンプル生成、光学と接続)。 · 例: `render_ao`
- `ambient_occlusion` (`mesh → image2d`) — メッシュを AO マップ画像 ``(H, W)`` [0,1] にレンダリングして返す。 · 例: `render_ao`
- `cast_shadow` (`mesh, vector → image2d`) — メッシュのキャスト影 / ソフトシャドウを計算し、可視性マップ (H,W) ∈ [0,1] を返す。 · 例: `render_beauty`, `render_shadow`
- `phong_shade` (`normalmap → image2d`) — Phong 反射モデルで法線マップを陰影付け(環境光 + 拡散 + **鏡面**)。→ ``(H, W)``。 · 例: `render_beauty`, `render_shade`
- `matcap_shade` (`normalmap, image2d → image2d`) — MatCap: 視空間法線を lit-sphere テクスチャに写して素材の見えを転写。→ ``(H, W[, C])``。 · 例: `render_shade`
- `supersample_mesh` (`mesh → image2d`) — メッシュを SSAA でアンチエイリアス描画 -> float 画像 ``(H, W)`` (or ``(H, W, C)``)。 · 例: `render_ssaa`
- `antialias` (`image2d → image2d`) — 高解像画像を整数倍 ``ss`` で縮小(area-average anti-aliasing)。 · 例: `render_ssaa`
- `edge_alias_energy` (`image2d → measurement`) — エッジのエイリアス(ジャギー)エネルギー = ラプラシアンの RMS(小さいほど滑らか)。 · 例: `render_beauty`, `render_ssaa`
- `tonemap_reinhard` (`image2d → image2d`) — Reinhard トーンマップで HDR を ``[0, 1]`` の LDR へ圧縮。→ float64、入力と同形状。 · 例: `render_beauty`, `render_tonemap`
- `tonemap_aces` (`image2d → image2d`) — ACES filmic 近似(Narkowicz 2015)で HDR を ``[0, 1]`` の LDR へ圧縮。→ float64。 · 例: `render_tonemap`
- `render_beauty` (`mesh → image2d`) — メッシュを全品質層合成で「映える静止 3D」1 枚に描く → RGB ``(size, size, 3)`` float [0,1]。 · 例: `render_beauty`

### restoration(2)
- `vol_gaussian_psf` (`measurement → voxel`) — A normalised (sums to 1) 3-D Gaussian PSF kernel. *sigma* is a scalar or · 例: `deconv_fft_restore`
- `vol_richardson_lucy` (`voxel, voxel → voxel`) — Richardson–Lucy deconvolution of a non-negative volume by a known PSF. · 例: `deconv_fft_restore`

### rle_region(9)
- `vol_rle_encode` (`voxel → rle_region`) — Encode a binary volume as x-runs (the 3-D HALCON-region representation). · 例: `rle_region_efficiency`
- `vol_rle_decode` (`rle_region → voxel`) — Decode a ``VolRLE`` back to a dense ``(D, H, W)`` float64 ``{0, 1}`` · 例: `rle_region_efficiency`
- `vol_rle_volume` (`rle_region → measurement`) — Voxel count of the region, computed on the runs (no decode). Measured · 例: `rle_region_efficiency`
- `vol_rle_bbox` (`rle_region → primitive`) — Tight bounding box ``(z0, y0, x0, z1, y1, x1)`` (exclusive upper bounds) · 例: `rle_region_efficiency`
- `vol_rle_centroid` (`rle_region → position`) — Centroid ``(z, y, x)`` of the region, computed on the runs (no decode). · 例: `rle_region_efficiency`
- `vol_rle_union` (`rle_region, rle_region → rle_region`) — Union of two RLE regions, computed on the runs (no decode). Cost scales · 例: `rle_region_efficiency`
- `vol_rle_intersect` (`rle_region, rle_region → rle_region`) — Intersection of two RLE regions on the runs (no decode). · 例: `rle_region_efficiency`
- `vol_rle_difference` (`rle_region, rle_region → rle_region`) — Set difference ``a \ b`` on the runs (no decode). · 例: `rle_region_efficiency`
- `vol_rle_components` (`voxel → rle_region`) — Split a binary volume into per-component ``VolRLE`` regions. · 例: `rle_region_efficiency`

### robust_fit(7)
- `ransac_plane` (`points → primitive`) — 外れ値に頑健な RANSAC 平面適合。 · 例: `ransac_prim`
- `ransac_sphere` (`points → primitive`) — 外れ値に頑健な RANSAC 球適合。 · 例: `ransac_prim`
- `ransac_line` (`points → primitive`) — 外れ値に頑健な RANSAC 直線適合。 · 例: `geometry_metrology`
- `ransac_cylinder` (`points, normals → primitive`) — 外れ値に頑健な RANSAC 円筒適合(点法線が必要)。 · 例: `ransac_prim`
- `fit_cone` (`points → primitive`) — 点群に無限円錐を当てはめ ``{apex, axis, half_angle, residual}`` を返す。 · 例: `fit_primitives_ext`
- `fit_torus` (`points → primitive`) — 点群にトーラスを当てはめ ``{center, axis, R, r, residual}`` を返す。 · 例: `fit_primitives_ext`
- `fit_ellipsoid` (`points → primitive`) — 点群に任意姿勢の 3 軸楕円体を代数フィットし ``{center, axes, radii, residual}`` を返す。 · 例: `fit_primitives_ext`

### scene_flow3d(3)
- `nearest_neighbor_flow` (`points, points → flow`) — 各点 pts0 から pts1 の最近傍への 3-D 変位ベクトル場 (N, 3) を返す。 · 例: `scene_flow_rigid`
- `rigid_flow` (`points, points → pose`) — pts0 -> pts1 を説明する単一剛体運動を最近傍対応 + Kabsch(ICP 風)で推定。 · 例: `scene_flow_rigid`
- `smooth_flow` (`points, points → flow`) — 最近傍フローを近傍平均で局所平滑化した正則化フロー (N, 3) を返す。 · 例: `scene_flow_rigid`

### sdf_csg(7)
- `sphere_sdf` (`points → sdf`) — 球の符号付き距離場: ``|p - center| - R``(内側負・外側正)。 · 例: `gear_metrology`, `molecule_atom_count`, `procedural_hand`, `render_beauty`, `sdf_csg`, `sfm_recon`
- `box_sdf` (`points → sdf`) — 軸平行直方体の**厳密**な符号付き距離場(内側負・外側正)。 · 例: `gear_metrology`, `sdf_csg`
- `sdf_union` (`sdf, sdf → sdf`) — 2 SDF の和集合 A∪B = 要素ごとの min(a, b)(内側=負がどちらかにあれば内側)。 · 例: `gear_metrology`, `sdf_csg`
- `sdf_intersect` (`sdf, sdf → sdf`) — 2 SDF の積集合 A∩B = 要素ごとの max(a, b)(両方の内側でのみ内側)。 · 例: `gear_metrology`
- `sdf_subtract` (`sdf, sdf → sdf`) — 差集合 A\B = max(a, -b)(A の内側 かつ B の外側 = ``-b`` の内側)。 · 例: `sdf_csg`
- `sdf_smooth_union` (`sdf, sdf → sdf`) — 滑らかに丸めた和集合(polynomial smooth-min)。``k>0`` で継ぎ目を半径 ~k で丸める。 · 例: `render_beauty`
- `sdf_offset` (`sdf → sdf`) — SDF のゼロ等値面を距離 ``r`` だけ法線方向へ動かす = ``sdf - r``(r>0 膨張, r<0 収縮)。 · 例: `sfm_recon`

### segment(4)
- `region_growing` (`points → labels`) — 法線類似で領域成長し連結した平滑領域へ同ラベルを付す(曲率ゲート無し変種)。 · 例: `sensor_seg`
- `euclidean_cluster` (`points → labels`) — 半径 tol の近接グラフの連結成分で距離クラスタリング(-1=ノイズ)。 · 例: `object_segmentation`
- `plane_segmentation` (`points → labels`) — 反復 RANSAC で最大 max_planes 枚の平面を逐次抽出(残差点 -1)。 · 例: `object_segmentation`
- `vol_watershed` (`voxel → labels`) — Marker-controlled 3-D watershed segmentation (**optional — scikit-image**). · 例: `molecule_atom_count`, `watershed3d`

### shape_descriptor(5)
- `d2_distribution` (`points → descriptor`) — ランダムな 2 点対のユークリッド距離分布(Osada 2002 の D2)。 · 例: `shape_desc_pose`
- `a3_distribution` (`points → descriptor`) — ランダムな 3 点 (A, B, C) が頂点 B で作る角の分布(Osada 2002 の A3)。 · 例: `shape_desc_pose`
- `extent_signature` (`points → descriptor`) — PCA 主軸(共分散の固有ベクトル)方向の広がりの比を返す。 · 例: `shape_desc_pose`
- `describe` (`points → descriptor`) — D2 + A3 + extent を連結した大域形状記述子を返す。 · 例: `denoise_evolution`, `shape_desc_pose`, `shape_retrieval`
- `shape_distance` (`descriptor, descriptor → measurement`) — 2 つの記述子間の距離。小さいほど同形状。 · 例: `moment_invariants`, `shape_desc_pose`, `shape_retrieval`

### space_carving(3)
- `carve` (`images → voxel`) — bounds を res^3 voxel に離散化し、全シルエット内に射影される voxel を残す(空間彫刻)。 · 例: `space_carving`
- `visual_hull` (`images → voxel`) — 多視点シルエットの visual hull を voxel 占有として返す(:func:`carve` の別名)。 · 例: `space_carving`
- `synthesize_silhouette` (`points → image2d`) — 3-D 点群を (K,R,t) カメラへ射影し占有画素 True のシルエット(H,W bool)を返す。 · 例: `space_carving`

### structured_light(5)
- `wrapped_phase` (`images → image2d`) — N-step 位相シフト縞画像から wrapped phase (-π, π] を求める。 · 例: `structured_light`
- `unwrap_phase_2d` (`image2d → image2d`) — wrapped phase を skimage.restoration.unwrap_phase で連続位相に展開する。 · 例: `structured_light`
- `graycode_decode` (`images → image2d`) — Gray code ビット画像列 → 整数フリンジ次数マップ(絶対次数)。 · 例: `graycode_structured_light`
- `decode_fringe` (`images → depth`) — 位相シフト画像列を一括復号: wrapped → unwrap →(参照減算で)高さ。 · 例: `structured_light`
- `synthesize_fringes` (`image2d → images`) — 既知の height map から N-step 位相シフト縞画像列を合成する(テスト/サンプル生成用)。 · 例: `structured_light`

### superquadric(4)
- `fit_superquadric` (`points → primitive`) — 点群にスーパー2次曲面を least_squares で当てはめ dict{a,eps,R,t,residual} を返す。 · 例: `superquadric_fit`
- `sample_surface` (`primitive → points`) — スーパー2次曲面の表面点を (eta, omega) パラメトリックにサンプリング。 · 例: `mesh_lod_download`, `superquadric_fit`
- `inside_outside` (`points → measurement`) — スーパー2次曲面の内外関数 F(表面=1, 内部<1, 外部>1)。 · 例: `superquadric_fit`
- `superquadric_residual` (`points → measurement`) — Gross-Boult 体積補正残差 mean( (sqrt(a1 a2 a3)(F^eps1 - 1))^2 )。 · 例: `superquadric_fit`

### surface_fit(4)
- `fit_poly_surface` (`image2d → surface`) — 散布 (x,y,z) → z=f(x,y) 多項式最小二乗。返り値 model(coef/powers/degree/rms/pv)。 · 例: `contours_to_terrain`
- `eval_poly_surface` (`surface → image2d`) — model を (x,y) で評価 → z(x の shape で返す)。 · 例: `contours_to_terrain`
- `surface_form_error` (`image2d → measurement`) — 高さ場 grid → 理想曲面(多項式)残差=形状誤差(平面度 deg1/球面度 deg2)。→ (residual, rms, pv)。 · 例: `geometry_metrology`
- `background_flatten` (`image2d → image2d`) — 画像の低次曲面(照明ムラ)をフィット減算=シェーディング補正。→ flattened。 · 例: `geometry_metrology`

### symmetry(4)
- `detect_reflection_symmetry` (`points → primitive`) — PCA 主軸を法線とする候補平面(重心通過)から最良の反射対称面を選ぶ。 · 例: `dl_mesh_symmetry`, `itokawa_symmetry_honest`, `reflection_symmetry`, `symmetry`
- `detect_rotational_symmetry` (`points → primitive`) — PCA 主軸を候補軸として最良の回転対称(軸 × order)を選ぶ。 · 例: `rotational_symmetry_fold`, `symmetry`
- `reflect_points` (`points → points`) — 点群を平面(点 plane_point・法線 plane_normal)で鏡映。→ (N,3)。 · 例: `reflection_symmetry`
- `reflection_symmetry_score` (`points → measurement`) — 反射対称スコア = chamfer(鏡映, 元) / 中央値最近傍間隔(小さいほど対称、スケール不変)。→ float。 · 例: `dl_mesh_symmetry`, `reflection_symmetry`

### transform(12)
- `points_to_voxel` (`points → voxel`) — 点群 (N,3) → 密度 voxel (size³)。scatter_add で splat、任意で gaussian 平滑。 · 例: `sh_descriptor_retrieval`, `shape_desc_pose`
- `gaussians_to_voxel` (`gaussians → voxel`) — 3DGS(異方性ガウス)→ 密度 voxel。各ガウスを means に opacity で置き、平均 scale で平滑。 · 例: `transforms_repr`
- `mesh_to_voxel` (`mesh → voxel`) — mesh(頂点+面)→ 密度 voxel。面上を一様サンプリング → splat(mesh 行を全手法へ接続)。 · 例: `transforms_repr`
- `mesh_to_points` (`mesh → points`) — mesh(頂点+面)→ 表面点群(面積重み一様サンプリング)。mesh→point cloud 変換。 · 例: `mesh_decimate`
- `depth_to_points` (`depth → points`) — 深度マップ(2.5D)→ point cloud(ピンホール逆投影)。depth 行を全手法へ接続。 · 例: `transforms_repr`
- `voxel_to_mips` (`voxel → images`) — 3D → 直交 3 方向の最大値投影(MIP)。2D 手法(accel の 2D NCC 等)を適用する入口。 · 例: `transforms_repr`
- `voxel_to_mesh` (`voxel → mesh`) — voxel → mesh(marching cubes、skimage)。返り値 (verts, faces, normals)。voxel→mesh 変換。 · 例: `mesh_smooth`
- `tsdf_from_depth` (`depth → sdf`) — 深度マップ(2.5D)→ TSDF volume(RGB-D 再構成の標準表現)。depth→TSDF 変換。 · 例: `transforms_repr`
- `signed_distance_field` (`voxel → sdf`) — occupancy/密度 voxel → 符号付き距離場 SDF(内側<0・外側>0)。edt_jfa を両側に。 · 例: `transforms_repr`
- `sdf_to_occupancy` (`sdf → voxel`) — SDF → occupancy voxel(iso 以下=内側=1)。SDF から voxel へ戻す。 · 例: `transforms_repr`
- `estimate_point_normals` (`points → normals`) — 点群 (N,3) → 単位法線(局所 k 近傍共分散の最小固有ベクトル=PCA)。 · 例: `fpfh_correspondence`
- `to_points` (`voxel, points, mesh, depth, gaussians → points`) — 任意の 3D 構造 → 点群(共通表現)。全5構造を 1 本の入口へ統合。 · 例: `transforms_repr`

### tsdf_fusion(3)
- `fuse` (`depth → sdf`) — 深度列を new_volume + integrate で 1 つの TSDF volume に融合。返り値 (tsdf, weight)。 · 例: `tsdf_fusion_demo`
- `integrate` (`sdf, depth → sdf`) — 深度 1 枚を投影的 TSDF で volume に統合(in-place、重み付き移動平均)。 · 例: `transforms_repr`
- `extract_surface_points` (`sdf → points`) — TSDF ゼロ交差から表面点 (M,3) を抽出(marching cubes 不要、線形補間)。 · 例: `transforms_repr`, `tsdf_fusion_demo`

### two_view(5)
- `fundamental_8point` (`image2d, image2d → matrix`) — 正規化 8 点法で基礎行列 F を推定(rank-2 強制)。→ F (3,3)。8 点以上必要。 · 例: `two_view_pose`
- `essential_8point` (`image2d, image2d → matrix`) — 対応点 + K から本質行列 E を直接。→ E (3,3)。 · 例: `sfm_recon`
- `recover_pose` (`image2d, image2d → pose`) — 対応点 + K から相対姿勢 (R,t) と 3D 構造を復元(cheirality で一意化)。→ (R, t_unit, points3d)。 · 例: `two_view_pose`
- `triangulate` (`image2d, image2d → points`) — DLT 三角測量: 2 視点の対応点 + 射影行列 → 3D 点。→ (N,3)。 · 例: `sfm_recon`
- `sampson_distance` (`image2d, image2d → measurement`) — エピポーラ拘束の Sampson 距離(1 次幾何誤差、各対応)。→ (N,)。 · 例: `two_view_pose`

## 2-D pipeline operators(ops registry)by category
_計 742 ops / 46 categories。_


1 画像を取り 1 画像/領域/輪郭/特徴を返すパイプライン op。`in → out` のデータ種で連鎖を組む。HALCON 別名は用途の手掛かり。

### 3d(12)
- `vol_gaussian` `volume → volume` · 例: `gallery2d_physics_alife_3d`
- `vol_median` `volume → volume` · 例: `gallery2d_physics_alife_3d`
- `vol_erode` `volume → volume` · 例: `gallery2d_physics_alife_3d`
- `vol_dilate` `volume → volume` · 例: `gallery2d_physics_alife_3d`
- `vol_threshold` `volume → volume` · 例: `gallery2d_physics_alife_3d`
- `vol_reg_dilate` `volume → volume` · 例: `gallery2d_physics_alife_3d`
- `vol_reg_erode` `volume → volume` · 例: `gallery2d_physics_alife_3d`
- `vol_dilation_ball` `volume → volume` · 例: `gallery2d_physics_alife_3d`
- `vol_erosion_ball` `volume → volume` · 例: `gallery2d_physics_alife_3d`
- `vol_opening_ball` `volume → volume` · 例: `gallery2d_physics_alife_3d`
- `vol_mip` `volume → image` · 例: `gallery2d_physics_alife_3d`
- `vol_slice` `volume → image` · 例: `gallery2d_physics_alife_3d`

### arithmetic(10)
- `abs_image` (halcon: `abs_image`) `image → image` · 例: `gallery2d_gray_arith`
- `sqrt_image` (halcon: `sqrt_image`) `image → image` · 例: `gallery2d_gray_arith`
- `exp_image` (halcon: `exp_image`) `image → image` · 例: `gallery2d_gray_arith`
- `log_image` (halcon: `log_image`) `image → image` · 例: `gallery2d_gray_arith`
- `sin_image` (halcon: `sin_image`) `image → image` · 例: `gallery2d_gray_arith`
- `cos_image` (halcon: `cos_image`) `image → image` · 例: `gallery2d_gray_arith`
- `asin_image` (halcon: `asin_image`) `image → image` · 例: `gallery2d_gray_arith`
- `acos_image` (halcon: `acos_image`) `image → image` · 例: `gallery2d_gray_arith`
- `atan_image` (halcon: `atan_image`) `image → image` · 例: `gallery2d_gray_arith`
- `tan_image` (halcon: `tan_image`) `image → image` · 例: `gallery2d_gray_arith`

### artificial-life(12)
- `alife_gray_scott` `image → image` · 例: `gallery2d_physics_alife_3d`
- `alife_turing` `image → image` · 例: `gallery2d_physics_alife_3d`, `sim2real_and_alife`
- `alife_life_step` `image → image` · 例: `gallery2d_physics_alife_3d`, `sim2real_and_alife`
- `alife_cyclic_ca` `image → image` · 例: `gallery2d_physics_alife_3d`, `sim2real_and_alife`
- `alife_perona_malik` `image → image` · 例: `gallery2d_physics_alife_3d`
- `alife_curvature_flow` `image → image` · 例: `gallery2d_physics_alife_3d`
- `alife_dla` `image → image` · 例: `gallery2d_physics_alife_3d`, `sim2real_and_alife`
- `alife_reaction_bz` `image → image` · 例: `gallery2d_physics_alife_3d`, `sim2real_and_alife`
- `alife_wolfram1d` `image → image` · 例: `gallery2d_physics_alife_3d`
- `alife_langton_ant` `image → image` · 例: `gallery2d_physics_alife_3d`
- `alife_lenia` `image → image` · 例: `gallery2d_physics_alife_3d`
- `alife_sandpile` `image → image` · 例: `gallery2d_physics_alife_3d`

### artistic(3)
- `xcv_stylization` `image → image` · 例: `gallery2d_color_artistic`
- `xcv_pencil_sketch` `image → image` · 例: `gallery2d_color_artistic`
- `xpil_emboss` `image → image` · 例: `gallery2d_color_artistic`

### augmentation(10)
- `aug_shot_noise` `image → image` · 例: `gallery2d_color_artistic`, `sim2real_and_alife`
- `aug_read_noise` `image → image` · 例: `gallery2d_color_artistic`
- `aug_fixed_pattern` `image → image` · 例: `gallery2d_color_artistic`, `sim2real_and_alife`
- `aug_motion_blur` `image → image` · 例: `gallery2d_color_artistic`
- `aug_vignette` `image → image` · 例: `gallery2d_color_artistic`, `sim2real_and_alife`
- `aug_chromatic` `image → image` · 例: `gallery2d_color_artistic`
- `aug_rolling_shutter` `image → image` · 例: `gallery2d_color_artistic`, `sim2real_and_alife`
- `aug_jpeg_blocks` `image → image` · 例: `gallery2d_color_artistic`, `sim2real_and_alife`
- `aug_cutout` `image → image` · 例: `gallery2d_color_artistic`
- `aug_barrel` `image → image` · 例: `gallery2d_color_artistic`, `sim2real_and_alife`

### barcode(1)
- `decode_barcode` (halcon: `find_bar_code`) `image → feature` · 例: `gallery2d_physics_alife_3d`

### classification(1)
- `classify_shape` `region → feature` · 例: `gallery2d_features`

### color(8)
- `cfa_to_rgb` (halcon: `cfa_to_rgb`) `image → color` · 例: `gallery2d_color_artistic`
- `trans_from_rgb` (halcon: `trans_from_rgb`) `color → color` · 例: `gallery2d_color_artistic`
- `trans_to_rgb` (halcon: `trans_to_rgb`) `color → color` · 例: `gallery2d_color_artistic`
- `linear_trans_color` (halcon: `linear_trans_color`) `color → color` · 例: `gallery2d_color_artistic`
- `principal_comp` (halcon: `principal_comp`) `color → color` · 例: `gallery2d_color_artistic`
- `rgb1_to_gray` (halcon: `rgb1_to_gray`) `color → image` · 例: `gallery2d_color_artistic`
- `rgb3_to_gray` (halcon: `rgb3_to_gray`) `color → image` · 例: `gallery2d_color_artistic`
- `access_channel` (halcon: `access_channel`) `color → image` · 例: `gallery2d_color_artistic`

### contour(26)
- `edges_sub_pix` (halcon: `edges_sub_pix`) `image → contour` · 例: `gallery2d_contour_measure`, `quickstart`
- `select_contours` (halcon: `select_contours_xld`) `contour → contour` · 例: `gallery2d_contour_measure`, `quickstart`
- `smooth_contours` (halcon: `smooth_contours_xld`) `contour → contour` · 例: `gallery2d_contour_measure`
- `fit_line_contours` (halcon: `fit_line_contour_xld`) `contour → contour` · 例: `gallery2d_contour_measure`
- `contours_to_region` (halcon: `gen_region_contour_xld`) `contour → region` · 例: `gallery2d_contour_measure`, `quickstart`
- `sk_find_contours` `image → contour` · 例: `gallery2d_contour_measure`
- `edges_sub_pix` (halcon: `edges_sub_pix`) `image → contour` · 例: `gallery2d_contour_measure`, `quickstart`
- `lines_gauss` (halcon: `lines_gauss`) `image → contour` · 例: `gallery2d_contour_measure`
- `select_contours_xld` (halcon: `select_contours_xld`) `contour → contour` · 例: `gallery2d_contour_measure`
- `smooth_contours_xld` (halcon: `smooth_contours_xld`) `contour → contour` · 例: `gallery2d_contour_measure`
- `gen_region_contour_xld` (halcon: `gen_region_contour_xld`) `contour → region` · 例: `gallery2d_contour_measure`
- `close_contours_xld` (halcon: `close_contours_xld`) `contour → contour` · 例: `gallery2d_contour_measure`
- `affine_trans_contour_xld` (halcon: `affine_trans_contour_xld`) `contour → contour` · 例: `gallery2d_contour_measure`
- `projective_trans_contour_xld` (halcon: `projective_trans_contour_xld`) `contour → contour` · 例: `gallery2d_contour_measure`
- `polar_trans_contour_xld` (halcon: `polar_trans_contour_xld`) `contour → contour` · 例: `gallery2d_contour_measure`
- `shape_trans_xld` (halcon: `shape_trans_xld`) `contour → contour` · 例: `gallery2d_contour_measure`
- `threshold_sub_pix` (halcon: `threshold_sub_pix`) `image → contour` · 例: `gallery2d_contour_measure`
- `zero_crossing_sub_pix` (halcon: `zero_crossing_sub_pix`) `image → contour` · 例: `gallery2d_contour_measure`
- `lines_facet` (halcon: `lines_facet`) `image → contour` · 例: `gallery2d_contour_measure`
- `gen_region_polygon_xld` (halcon: `gen_region_polygon_xld`) `contour → region` · 例: `gallery2d_contour_measure`
- `affine_trans_polygon_xld` (halcon: `affine_trans_polygon_xld`) `contour → contour` · 例: `gallery2d_contour_measure`
- `gen_contour_region_xld` (halcon: `gen_contour_region_xld`) `region → contour` · 例: `gallery2d_contour_measure`
- `select_shape_xld` (halcon: `select_shape_xld`) `contour → contour` · 例: `gallery2d_contour_measure`
- `contour_point_num_xld` (halcon: `contour_point_num_xld`) `contour → feature` · 例: `gallery2d_contour_measure`
- `edges_color_sub_pix` (halcon: `edges_color_sub_pix`) `color → contour` · 例: `gallery2d_contour_measure`
- `lines_color` (halcon: `lines_color`) `color → contour` · 例: `gallery2d_contour_measure`

### decomposition(7)
- `dc_structure_texture` `image → image` · 例: `gallery2d_texture_freq`
- `dc_texture_residual` `image → image` · 例: `gallery2d_texture_freq`
- `dc_rpca_lowrank` `image → image` · 例: `gallery2d_texture_freq`
- `dc_rpca_sparse` `image → image` · 例: `gallery2d_texture_freq`
- `dc_retinex` `image → image` · 例: `gallery2d_texture_freq`
- `dc_local_contrast_norm` `image → image` · 例: `gallery2d_texture_freq`
- `dc_homomorphic` `image → image` · 例: `gallery2d_texture_freq`

### deformation(3)
- `deform_tps` `image → image` · 例: `gallery2d_geometry`
- `deform_ffd` `image → image` · 例: `gallery2d_geometry`
- `deform_mls` `image → image` · 例: `gallery2d_geometry`

### domain(2)
- `it_full_domain` `image → image` · 例: `gallery2d_gray_arith`
- `it_crop_domain` (halcon: `crop_domain`) `image → image` · 例: `gallery2d_gray_arith`

### edges(57)
- `sobel_mag` (halcon: `sobel_amp`) `image → image` · 例: `gallery2d_edges`
- `laplace` (halcon: `laplace`) `image → image` · 例: `gallery2d_edges`
- `prewitt_mag` (halcon: `prewitt_amp`) `image → image` · 例: `gallery2d_edges`
- `roberts_mag` (halcon: `roberts`) `image → image` · 例: `gallery2d_edges`
- `dog` (halcon: `diff_of_gauss`) `image → image` · 例: `gallery2d_edges`
- `grad_dir` `image → image` · 例: `gallery2d_edges`
- `log` (halcon: `laplace_of_gauss`) `image → image` · 例: `gallery2d_edges`, `signal_funct1d`
- `corner_response` (halcon: `points_harris`) `image → image` · 例: `gallery2d_edges`
- `sk_scharr` (halcon: `edges_image`) `image → image` · 例: `gallery2d_edges`
- `sk_farid` (halcon: `edges_image`) `image → image` · 例: `gallery2d_edges`
- `sk_dog` (halcon: `diff_of_gauss`) `image → image` · 例: `gallery2d_edges`
- `sk_hessian_det` `image → image` · 例: `gallery2d_edges`
- `sk_corner_harris` (halcon: `points_harris`) `image → image` · 例: `gallery2d_edges`
- `cv_scharr` (halcon: `edges_image`) `image → image` · 例: `gallery2d_edges`
- `cv_laplacian` (halcon: `laplace`) `image → image` · 例: `gallery2d_edges`
- `cv_corner_harris` (halcon: `points_harris`) `image → image` · 例: `gallery2d_edges`
- `cv_min_eigen` (halcon: `points_harris`) `image → image` · 例: `gallery2d_edges`
- `cv_precorner` (halcon: `corner_response`) `image → image` · 例: `gallery2d_edges`
- `derivate_gauss` (halcon: `derivate_gauss`) `image → image` · 例: `gallery2d_edges`
- `laplace_of_gauss` (halcon: `laplace_of_gauss`) `image → image` · 例: `gallery2d_edges`
- `diff_of_gauss` (halcon: `diff_of_gauss`) `image → image` · 例: `gallery2d_edges`
- `sobel_amp` (halcon: `sobel_amp`) `image → image` · 例: `gallery2d_edges`
- `sobel_dir` (halcon: `sobel_dir`) `image → image` · 例: `gallery2d_edges`
- `prewitt_amp` (halcon: `prewitt_amp`) `image → image` · 例: `gallery2d_edges`
- `prewitt_dir` (halcon: `prewitt_dir`) `image → image` · 例: `gallery2d_edges`
- `roberts` (halcon: `roberts`) `image → image` · 例: `gallery2d_edges`
- `kirsch_amp` (halcon: `kirsch_amp`) `image → image` · 例: `gallery2d_edges`
- `kirsch_dir` (halcon: `kirsch_dir`) `image → image` · 例: `gallery2d_edges`
- `frei_amp` (halcon: `frei_amp`) `image → image` · 例: `gallery2d_edges`
- `robinson_amp` (halcon: `robinson_amp`) `image → image` · 例: `gallery2d_edges`
- `laplace` (halcon: `laplace`) `image → image` · 例: `gallery2d_edges`
- `points_foerstner` (halcon: `points_foerstner`) `image → image` · 例: `gallery2d_edges`
- `points_harris_binomial` (halcon: `points_harris_binomial`) `image → image` · 例: `gallery2d_edges`
- `dots_image` (halcon: `dots_image`) `image → image` · 例: `gallery2d_edges`
- `frei_dir` (halcon: `frei_dir`) `image → image` · 例: `gallery2d_edges`
- `robinson_dir` (halcon: `robinson_dir`) `image → image` · 例: `gallery2d_edges`
- `edges_color` (halcon: `edges_color`) `color → image` · 例: `gallery2d_edges`
- `xsk_hessian_eig` `image → image` · 例: `gallery2d_edges`
- `xpil_contour` `image → image` · 例: `gallery2d_edges`
- `xpil_find_edges` `image → image` · 例: `gallery2d_edges`
- `xsp_morph_laplace` `image → image` · 例: `gallery2d_edges`
- `xsp_gauss_grad_mag` `image → image` · 例: `gallery2d_edges`
- `xsk2_corner_kr` `image → image` · 例: `gallery2d_edges`
- `xsk2_inv_gauss_grad` `image → image` · 例: `gallery2d_edges`
- `xwt_hf_reconstruct` `image → image` · 例: `gallery2d_edges`
- `xwt_directional_detail` `image → image` · 例: `gallery2d_edges`
- `xsk3_corner_moravec` `image → image` · 例: `gallery2d_edges`
- `xsk3_corner_fast` `image → image` · 例: `gallery2d_edges`
- `xkor_laplacian` `image → image` · 例: `gallery2d_edges`
- `xkor_harris` `image → image` · 例: `gallery2d_edges`
- `xkor_gftt` `image → image` · 例: `gallery2d_edges`
- `xkor_hessian` `image → image` · 例: `gallery2d_edges`
- `xkor_dog` `image → image` · 例: `gallery2d_edges`
- `f2_shock` (halcon: `shock_filter`) `image → image` · 例: `gallery2d_edges`
- `f2_topographic` (halcon: `topographic_sketch`) `image → image` · 例: `gallery2d_edges`
- `tf_steerable_filter` `image → image` · 例: `gallery2d_edges`
- `tf_phase_congruency` `image → image` · 例: `gallery2d_edges`

### extra(14)
- `xsitk_curvature_flow` `image → image` · 例: `gallery2d_color_artistic`
- `xsitk_minmax_curv_flow` `image → image` · 例: `gallery2d_color_artistic`
- `xsitk_curv_aniso_diff` `image → image` · 例: `gallery2d_color_artistic`
- `xsitk_laplacian_sharpen` `image → image` · 例: `gallery2d_color_artistic`
- `xsitk_grayscale_fillhole` `image → image` · 例: `gallery2d_color_artistic`
- `xsitk_grayscale_grindpeak` `image → image` · 例: `gallery2d_color_artistic`
- `xsitk_opening_by_recon` `image → image` · 例: `gallery2d_color_artistic`
- `xsitk_closing_by_recon` `image → image` · 例: `gallery2d_color_artistic`
- `xsitk_signed_maurer_dist` `region → image` · 例: `gallery2d_color_artistic`
- `xsitk_connected_threshold` `image → region` · 例: `gallery2d_color_artistic`
- `xsitk_confidence_connected` `image → region` · 例: `gallery2d_color_artistic`
- `xsitk_maxentropy_thresh` `image → region` · 例: `gallery2d_color_artistic`
- `xsitk_moments_thresh` `image → region` · 例: `gallery2d_color_artistic`
- `xsitk_huang_thresh` `image → region` · 例: `gallery2d_color_artistic`

### features(71)
- `blob_count` (halcon: `count_obj`) `region → feature` · 例: `gallery2d_features`, `quickstart`
- `area_frac` (halcon: `area_center`) `region → feature` · 例: `gallery2d_features`
- `count_contours` (halcon: `count_obj`) `contour → feature` · 例: `gallery2d_features`
- `total_length` (halcon: `length_xld`) `contour → feature` · 例: `gallery2d_features`
- `vol_count` `volume → feature` · 例: `gallery2d_features`
- `sk_euler` (halcon: `euler_number`) `region → feature` · 例: `gallery2d_features`
- `sk_entropy_feat` (halcon: `entropy_gray`) `image → feature` · 例: `gallery2d_features`
- `sk_blur_effect` `image → feature` · 例: `gallery2d_features`
- `cv_cc_count` (halcon: `connection`) `region → feature` · 例: `gallery2d_features`
- `cv_hough_lines` (halcon: `hough_lines`) `image → feature` · 例: `gallery2d_features`
- `cv_hough_circles` (halcon: `hough_circles`) `image → feature` · 例: `gallery2d_features`
- `cv_good_features` `image → feature` · 例: `gallery2d_features`
- `area_center` (halcon: `area_center`) `region → feature` · 例: `gallery2d_features`
- `count_obj` (halcon: `count_obj`) `region → feature` · 例: `gallery2d_features`
- `circularity` (halcon: `circularity`) `region → feature` · 例: `draw_annotate`, `gallery2d_features`
- `compactness` (halcon: `compactness`) `region → feature` · 例: `gallery2d_features`
- `convexity` (halcon: `convexity`) `region → feature` · 例: `gallery2d_features`
- `rectangularity` (halcon: `rectangularity`) `region → feature` · 例: `gallery2d_features`
- `eccentricity` (halcon: `eccentricity`) `region → feature` · 例: `gallery2d_features`
- `orientation_region` (halcon: `orientation_region`) `region → feature` · 例: `gallery2d_features`
- `roundness` (halcon: `roundness`) `region → feature` · 例: `gallery2d_features`
- `diameter_region` (halcon: `diameter_region`) `region → feature` · 例: `gallery2d_features`
- `euler_number` (halcon: `euler_number`) `region → feature` · 例: `gallery2d_features`
- `min_max_gray` (halcon: `min_max_gray`) `image → feature` · 例: `gallery2d_features`
- `intensity` (halcon: `intensity`) `image → feature` · 例: `gallery2d_features`
- `gray_histo_abs` (halcon: `gray_histo_abs`) `image → feature` · 例: `gallery2d_features`
- `entropy_gray` (halcon: `entropy_gray`) `image → feature` · 例: `gallery2d_features`
- `length_xld` (halcon: `length_xld`) `contour → feature` · 例: `gallery2d_features`
- `contlength` (halcon: `contlength`) `region → feature` · 例: `gallery2d_features`
- `area_holes` (halcon: `area_holes`) `region → feature` · 例: `gallery2d_features`
- `height_width_ratio` (halcon: `height_width_ratio`) `region → feature` · 例: `gallery2d_features`
- `moments_region_2nd` (halcon: `moments_region_2nd`) `region → feature` · 例: `gallery2d_features`
- `moments_region_2nd_invar` (halcon: `moments_region_2nd_invar`) `region → feature` · 例: `gallery2d_features`
- `area_center_xld` (halcon: `area_center_xld`) `contour → feature` · 例: `gallery2d_features`
- `circularity_xld` (halcon: `circularity_xld`) `contour → feature` · 例: `gallery2d_features`
- `compactness_xld` (halcon: `compactness_xld`) `contour → feature` · 例: `gallery2d_features`
- `convexity_xld` (halcon: `convexity_xld`) `contour → feature` · 例: `gallery2d_features`
- `moments_region_3rd` (halcon: `moments_region_3rd`) `region → feature` · 例: `gallery2d_features`
- `moments_region_central` (halcon: `moments_region_central`) `region → feature` · 例: `gallery2d_features`
- `moments_region_central_invar` (halcon: `moments_region_central_invar`) `region → feature` · 例: `gallery2d_features`
- `moments_region_2nd_rel_invar` (halcon: `moments_region_2nd_rel_invar`) `region → feature` · 例: `gallery2d_features`
- `moments_region_3rd_invar` (halcon: `moments_region_3rd_invar`) `region → feature` · 例: `gallery2d_features`
- `estimate_noise` (halcon: `estimate_noise`) `image → feature` · 例: `gallery2d_features`
- `eccentricity_xld` (halcon: `eccentricity_xld`) `contour → feature` · 例: `gallery2d_features`
- `orientation_xld` (halcon: `orientation_xld`) `contour → feature` · 例: `gallery2d_features`
- `elliptic_axis_xld` (halcon: `elliptic_axis_xld`) `contour → feature` · 例: `gallery2d_features`
- `diameter_xld` (halcon: `diameter_xld`) `contour → feature` · 例: `gallery2d_features`
- `rectangularity_xld` (halcon: `rectangularity_xld`) `contour → feature` · 例: `gallery2d_features`
- `moments_xld` (halcon: `moments_xld`) `contour → feature` · 例: `gallery2d_features`
- `hough_line_trans` (halcon: `hough_line_trans`) `image → image` · 例: `gallery2d_features`
- `hough_circle_trans` (halcon: `hough_circle_trans`) `image → image` · 例: `gallery2d_features`
- `get_region_thickness` (halcon: `get_region_thickness`) `region → feature` · 例: `gallery2d_features`
- `connect_and_holes` (halcon: `connect_and_holes`) `region → feature` · 例: `gallery2d_features`
- `elliptic_axis` (halcon: `elliptic_axis`) `region → feature` · 例: `gallery2d_features`
- `count_channels` (halcon: `count_channels`) `color → feature` · 例: `gallery2d_features`
- `xsk_blob_log` `image → feature` · 例: `gallery2d_features`
- `xsk_blob_dog` `image → feature` · 例: `gallery2d_features`
- `xsk_blob_doh` `image → feature` · 例: `gallery2d_features`
- `xsk_orb_count` `image → feature` · 例: `gallery2d_features`
- `xcv_orb_count` `image → feature` · 例: `gallery2d_features`
- `xcv2_lap_var` `image → feature` · 例: `gallery2d_features`
- `xcv2_fast_count` `image → feature` · 例: `gallery2d_features`
- `xwt_detail_energy` `image → feature` · 例: `gallery2d_features`
- `xwt_packet_entropy` `image → feature` · 例: `gallery2d_features`
- `xsk3_is_low_contrast` `image → feature` · 例: `gallery2d_features`
- `xsk3_estimate_sigma` `image → feature` · 例: `gallery2d_features`
- `xcv3_gray_hu1` `image → feature` · 例: `gallery2d_features`
- `xcv3_sift_count` `image → feature` · 例: `gallery2d_features`
- `xcv3_brisk_count` `image → feature` · 例: `gallery2d_features`
- `xcv3_agast_count` `image → feature` · 例: `gallery2d_features`
- `xcv3_lsd_count` `image → feature` · 例: `gallery2d_features`

### filtering(1)
- `tf_gradient_domain_reintegrate` `image → image` · 例: `gallery2d_smoothing_rank`

### frequency(19)
- `lowpass` `image → image` · 例: `gallery2d_texture_freq`, `signal_filter`
- `highpass` (halcon: `highpass_image`) `image → image` · 例: `gallery2d_texture_freq`, `signal_filter`
- `sk_butterworth` `image → image` · 例: `gallery2d_texture_freq`
- `fft_image` (halcon: `fft_image`) `image → image` · 例: `gallery2d_texture_freq`
- `power_real` (halcon: `power_real`) `image → image` · 例: `gallery2d_texture_freq`
- `power_byte` (halcon: `power_byte`) `image → image` · 例: `gallery2d_texture_freq`
- `phase_rad` (halcon: `phase_rad`) `image → image` · 例: `gallery2d_texture_freq`
- `highpass_image` (halcon: `highpass_image`) `image → image` · 例: `gallery2d_texture_freq`
- `bandpass_image` (halcon: `bandpass_image`) `image → image` · 例: `gallery2d_texture_freq`
- `fft_image_inv` (halcon: `fft_image_inv`) `image → image` · 例: `gallery2d_texture_freq`
- `fft_generic` (halcon: `fft_generic`) `image → image` · 例: `gallery2d_texture_freq`
- `power_ln` (halcon: `power_ln`) `image → image` · 例: `gallery2d_texture_freq`
- `rft_generic` (halcon: `rft_generic`) `image → image` · 例: `gallery2d_texture_freq`
- `phase_deg` (halcon: `phase_deg`) `image → image` · 例: `gallery2d_texture_freq`
- `xsp_dct` `image → image` · 例: `gallery2d_texture_freq`
- `xsp_dct_lowpass` `image → image` · 例: `gallery2d_texture_freq`
- `xsk2_radon` `image → image` · 例: `gallery2d_texture_freq`
- `xwt_subband_tile` `image → image` · 例: `gallery2d_texture_freq`
- `xwt_mra_component` `image → image` · 例: `gallery2d_texture_freq`

### geometry(28)
- `rotate_img` (halcon: `rotate_image`) `image → image` · 例: `gallery2d_geometry`
- `rescale_img` (halcon: `zoom_image_size`) `image → image` · 例: `gallery2d_geometry`
- `affine_warp` (halcon: `affine_trans_image`) `image → image` · 例: `gallery2d_geometry`
- `sk_swirl` (halcon: `polar_trans_image`) `image → image` · 例: `gallery2d_geometry`
- `mirror_image` (halcon: `mirror_image`) `image → image` · 例: `gallery2d_geometry`
- `transpose_region` (halcon: `transpose_region`) `region → region` · 例: `gallery2d_geometry`
- `rotate_image` (halcon: `rotate_image`) `image → image` · 例: `gallery2d_geometry`
- `zoom_image_factor` (halcon: `zoom_image_factor`) `image → image` · 例: `gallery2d_geometry`
- `zoom_image_size` (halcon: `zoom_image_size`) `image → image` · 例: `gallery2d_geometry`
- `affine_trans_image` (halcon: `affine_trans_image`) `image → image` · 例: `gallery2d_geometry`
- `polar_trans_image` (halcon: `polar_trans_image`) `image → image` · 例: `gallery2d_geometry`
- `projective_trans_image` (halcon: `projective_trans_image`) `image → image` · 例: `gallery2d_geometry`
- `projective_trans_image_size` (halcon: `projective_trans_image_size`) `image → image` · 例: `gallery2d_geometry`
- `projective_trans_region` (halcon: `projective_trans_region`) `region → region` · 例: `gallery2d_geometry`
- `polar_trans_image_inv` (halcon: `polar_trans_image_inv`) `image → image` · 例: `gallery2d_geometry`
- `affine_trans_image_size` (halcon: `affine_trans_image_size`) `image → image` · 例: `gallery2d_geometry`
- `polar_trans_image_ext` (halcon: `polar_trans_image_ext`) `image → image` · 例: `gallery2d_geometry`
- `affine_trans_region` (halcon: `affine_trans_region`) `region → region` · 例: `gallery2d_geometry`
- `mirror_region` (halcon: `mirror_region`) `region → region` · 例: `gallery2d_geometry`
- `zoom_region` (halcon: `zoom_region`) `region → region` · 例: `gallery2d_geometry`
- `polar_trans_region_inv` (halcon: `polar_trans_region_inv`) `region → region` · 例: `gallery2d_geometry`
- `xpil_offset` `image → image` · 例: `gallery2d_geometry`
- `xcv2_warp_logpolar` `image → image` · 例: `gallery2d_geometry`
- `it_add_image_border` (halcon: `add_image_border`) `image → image` · 例: `gallery2d_geometry`
- `it_crop_part` (halcon: `crop_part`) `image → image` · 例: `gallery2d_geometry`
- `it_crop_rectangle1` (halcon: `crop_rectangle1`) `image → image` · 例: `gallery2d_geometry`
- `it_change_format` (halcon: `change_format`) `image → image` · 例: `gallery2d_geometry`
- `tf_log_polar` `image → image` · 例: `gallery2d_geometry`

### gray(41)
- `gamma` (halcon: `pow_image`) `image → image` · 例: `gallery2d_gray_arith`
- `invert` (halcon: `invert_image`) `image → image` · 例: `gallery2d_gray_arith`
- `scale_clip` (halcon: `scale_image`) `image → image` · 例: `gallery2d_gray_arith`
- `equalize` (halcon: `equ_histo_image`) `image → image` · 例: `gallery2d_gray_arith`
- `sigmoid` (halcon: `scale_image_max`) `image → image` · 例: `gallery2d_gray_arith`
- `clahe` `image → image` · 例: `gallery2d_gray_arith`
- `sk_adapthist` `image → image` · 例: `gallery2d_gray_arith`
- `sk_enhance_contrast` `image → image` · 例: `gallery2d_gray_arith`
- `sk_autolevel` (halcon: `scale_image_max`) `image → image` · 例: `gallery2d_gray_arith`
- `sk_adjust_log` (halcon: `log_image`) `image → image` · 例: `gallery2d_gray_arith`
- `cv_clahe` `image → image` · 例: `gallery2d_gray_arith`
- `cv_trunc` (halcon: `scale_image`) `image → image` · 例: `gallery2d_gray_arith`
- `gamma_image` (halcon: `gamma_image`) `image → image` · 例: `gallery2d_gray_arith`
- `pow_image` (halcon: `pow_image`) `image → image` · 例: `gallery2d_gray_arith`
- `invert_image` (halcon: `invert_image`) `image → image` · 例: `gallery2d_gray_arith`
- `scale_image` (halcon: `scale_image`) `image → image` · 例: `gallery2d_gray_arith`
- `equ_histo_image` (halcon: `equ_histo_image`) `image → image` · 例: `gallery2d_gray_arith`
- `illuminate` (halcon: `illuminate`) `image → image` · 例: `gallery2d_gray_arith`
- `scale_image_max` (halcon: `scale_image_max`) `image → image` · 例: `gallery2d_gray_arith`
- `equ_histo_image_rect` (halcon: `equ_histo_image_rect`) `image → image` · 例: `gallery2d_gray_arith`
- `bit_not` (halcon: `bit_not`) `image → image` · 例: `gallery2d_gray_arith`
- `monotony` (halcon: `monotony`) `image → image` · 例: `gallery2d_gray_arith`
- `xcv_detail_enhance` `image → image` · 例: `gallery2d_gray_arith`
- `xpil_edge_enhance` `image → image` · 例: `gallery2d_gray_arith`
- `xpil_detail` `image → image` · 例: `gallery2d_gray_arith`
- `xpil_posterize` `image → image` · 例: `gallery2d_gray_arith`
- `xpil_solarize` `image → image` · 例: `gallery2d_gray_arith`
- `xpil_autocontrast` `image → image` · 例: `gallery2d_gray_arith`
- `xpil_contrast` `image → image` · 例: `gallery2d_gray_arith`
- `xsp_detrend_flatten` `image → image` · 例: `gallery2d_gray_arith`
- `xsk3_rank_subtract_mean` `image → image` · 例: `gallery2d_gray_arith`
- `xsk3_rank_equalize` `image → image` · 例: `gallery2d_gray_arith`
- `xsk3_integral_image` `image → image` · 例: `gallery2d_gray_arith`
- `xkor_clahe` `image → image` · 例: `gallery2d_gray_arith`
- `f2_lut_trans` (halcon: `lut_trans`) `image → image` · 例: `gallery2d_gray_arith`
- `f2_expand_domain` (halcon: `expand_domain_gray`) `image → image` · 例: `gallery2d_gray_arith`
- `f2_bit_slice` (halcon: `bit_slice`) `image → image` · 例: `gallery2d_gray_arith`
- `it_bit_lshift` (halcon: `bit_lshift`) `image → image` · 例: `gallery2d_gray_arith`
- `it_bit_rshift` (halcon: `bit_rshift`) `image → image` · 例: `gallery2d_gray_arith`
- `it_bit_mask` (halcon: `bit_mask`) `image → image` · 例: `gallery2d_gray_arith`
- `it_convert_image_type` (halcon: `convert_image_type`) `image → image` · 例: `gallery2d_gray_arith`

### halcon_ext(81)
- `hx_gen_circle` (halcon: `gen_circle`) `image → region` · 例: `gallery2d_halcon_ext`
- `hx_gen_ellipse` (halcon: `gen_ellipse`) `image → region` · 例: `gallery2d_halcon_ext`
- `hx_gen_rectangle2` (halcon: `gen_rectangle2`) `image → region` · 例: `gallery2d_halcon_ext`
- `hx_gen_checker_region` (halcon: `gen_checker_region`) `image → region` · 例: `gallery2d_halcon_ext`
- `hx_gen_grid_region` (halcon: `gen_grid_region`) `image → region` · 例: `gallery2d_halcon_ext`
- `hx_gabor` (halcon: `convol_gabor`) `image → image` · 例: `gallery2d_halcon_ext`
- `hx_fit_surface1` (halcon: `fit_surface_first_order`) `image → image` · 例: `gallery2d_halcon_ext`
- `hx_fit_surface2` (halcon: `fit_surface_second_order`) `image → image` · 例: `gallery2d_halcon_ext`
- `hx_cooc_feature` (halcon: `cooc_feature_image`) `image → feature` · 例: `gallery2d_halcon_ext`
- `hx_full_domain` (halcon: `full_domain`) `image → region` · 例: `gallery2d_halcon_ext`
- `hx_mean_shape` (halcon: `mean_image_shape`) `image → image` · 例: `gallery2d_halcon_ext`
- `hx_close_edges` (halcon: `close_edges`) `image → image` · 例: `gallery2d_halcon_ext`
- `hx_close_edges_length` (halcon: `close_edges_length`) `image → image` · 例: `gallery2d_halcon_ext`
- `hx_expand_region` (halcon: `expand_region`) `region → region` · 例: `gallery2d_halcon_ext`
- `hx_region_to_mean` (halcon: `region_to_mean`) `image → image` · 例: `gallery2d_halcon_ext`
- `hx_nonmax_dir` (halcon: `nonmax_suppression_dir`) `image → image` · 例: `gallery2d_halcon_ext`
- `hx_char_threshold` (halcon: `char_threshold`) `image → region` · 例: `gallery2d_halcon_ext`
- `hx_histo_to_thresh` (halcon: `histo_to_thresh`) `image → region` · 例: `gallery2d_halcon_ext`
- `hx_gen_lowpass` (halcon: `gen_lowpass`) `image → image` · 例: `gallery2d_halcon_ext`
- `hx_gen_highpass` (halcon: `gen_highpass`) `image → image` · 例: `gallery2d_halcon_ext`
- `hx_gen_bandpass` (halcon: `gen_bandpass`) `image → image` · 例: `gallery2d_halcon_ext`
- `hx_erosion1` (halcon: `erosion1`) `region → region` · 例: `gallery2d_halcon_ext`
- `hx_dilation1` (halcon: `dilation1`) `region → region` · 例: `gallery2d_halcon_ext`
- `hx_opening` (halcon: `opening`) `region → region` · 例: `gallery2d_halcon_ext`
- `hx_closing` (halcon: `closing`) `region → region` · 例: `gallery2d_halcon_ext`
- `hx_dilation2` (halcon: `dilation2`) `region → region` · 例: `gallery2d_halcon_ext`
- `hx_gen_disc_se` (halcon: `gen_disc_se`) `image → region` · 例: `gallery2d_halcon_ext`
- `hx_gen_circle_sector` (halcon: `gen_circle_sector`) `image → region` · 例: `gallery2d_halcon_ext`
- `hx_gen_ellipse_sector` (halcon: `gen_ellipse_sector`) `image → region` · 例: `gallery2d_halcon_ext`
- `hx_gen_empty_region` (halcon: `gen_empty_region`) `image → region` · 例: `gallery2d_halcon_ext`
- `hx_clip_region_rel` (halcon: `clip_region_rel`) `region → region` · 例: `gallery2d_halcon_ext`
- `hx_gen_bandfilter` (halcon: `gen_bandfilter`) `image → image` · 例: `gallery2d_halcon_ext`
- `hx_gen_derivative_filter` (halcon: `gen_derivative_filter`) `image → image` · 例: `gallery2d_halcon_ext`
- `hx_fill_interlace` (halcon: `fill_interlace`) `image → image` · 例: `gallery2d_halcon_ext`
- `hx_shade_height_field` (halcon: `shade_height_field`) `image → image` · 例: `gallery2d_halcon_ext`
- `hx_plane_deviation` (halcon: `plane_deviation`) `image → image` · 例: `gallery2d_halcon_ext`
- `hx_detect_edge_segments` (halcon: `detect_edge_segments`) `image → region` · 例: `gallery2d_halcon_ext`
- `hx_gen_image_proto` (halcon: `gen_image_proto`) `image → image` · 例: `gallery2d_halcon_ext`
- `hx_get_domain` (halcon: `get_domain`) `image → region` · 例: `gallery2d_halcon_ext`
- `hx_region_to_label` (halcon: `region_to_label`) `image → image` · 例: `gallery2d_halcon_ext`
- `hx_rectangle1_domain` (halcon: `rectangle1_domain`) `image → region` · 例: `gallery2d_halcon_ext`
- `hx_lowlands` (halcon: `lowlands`) `image → region` · 例: `gallery2d_halcon_ext`
- `hx_plateaus_center` (halcon: `plateaus_center`) `image → region` · 例: `gallery2d_halcon_ext`
- `hx_move_region` (halcon: `move_region`) `region → region` · 例: `gallery2d_halcon_ext`
- `hx_split_skeleton_region` (halcon: `split_skeleton_region`) `region → region` · 例: `gallery2d_halcon_ext`
- `hx_test_region_point` (halcon: `test_region_point`) `region → feature` · 例: `gallery2d_halcon_ext`
- `hx_test_region_points` (halcon: `test_region_points`) `region → feature` · 例: `gallery2d_halcon_ext`
- `hx_sort_contours` (halcon: `sort_contours_xld`) `contour → contour` · 例: `gallery2d_halcon_ext`
- `hx_clip_contours` (halcon: `clip_contours_xld`) `contour → contour` · 例: `gallery2d_halcon_ext`
- `hx_clip_end_points` (halcon: `clip_end_points_contours_xld`) `contour → contour` · 例: `gallery2d_halcon_ext`
- `hx_smallest_circle_xld` (halcon: `smallest_circle_xld`) `contour → feature` · 例: `gallery2d_halcon_ext`
- `hx_smallest_rect1_xld` (halcon: `smallest_rectangle1_xld`) `contour → feature` · 例: `gallery2d_halcon_ext`
- `hx_test_closed_xld` (halcon: `test_closed_xld`) `contour → feature` · 例: `gallery2d_halcon_ext`
- `hx_regress_contours` (halcon: `regress_contours_xld`) `contour → feature` · 例: `gallery2d_halcon_ext`
- `hx_moments_any_xld` (halcon: `moments_any_xld`) `contour → feature` · 例: `gallery2d_halcon_ext`
- `hx_split_contours` (halcon: `split_contours_xld`) `contour → contour` · 例: `gallery2d_halcon_ext`
- `hx_gen_parallel_contour` (halcon: `gen_parallel_contour_xld`) `contour → contour` · 例: `gallery2d_halcon_ext`
- `hx_fit_circle_contour` (halcon: `fit_circle_contour_xld`) `contour → feature` · 例: `gallery2d_halcon_ext`
- `hx_fit_ellipse_contour` (halcon: `fit_ellipse_contour_xld`) `contour → feature` · 例: `gallery2d_halcon_ext`
- `hx_fit_rectangle2_contour` (halcon: `fit_rectangle2_contour_xld`) `contour → feature` · 例: `gallery2d_halcon_ext`
- `hx_smallest_rect2_xld` (halcon: `smallest_rectangle2_xld`) `contour → feature` · 例: `gallery2d_halcon_ext`
- `hx_crop_contours` (halcon: `crop_contours_xld`) `contour → contour` · 例: `gallery2d_halcon_ext`
- `hx_dist_ellipse_contour` (halcon: `dist_ellipse_contour_xld`) `contour → feature` · 例: `gallery2d_halcon_ext`
- `hx_test_self_intersect` (halcon: `test_self_intersection_xld`) `contour → feature` · 例: `gallery2d_halcon_ext`
- `hx_union_adjacent` (halcon: `union_adjacent_contours_xld`) `contour → contour` · 例: `gallery2d_halcon_ext`
- `hx_polar_trans_inv` (halcon: `polar_trans_contour_xld_inv`) `contour → contour` · 例: `gallery2d_halcon_ext`
- `hx_select_xld_point` (halcon: `select_xld_point`) `contour → contour` · 例: `gallery2d_halcon_ext`
- `hx_estimate_tilt_lr` (halcon: `estimate_tilt_lr`) `image → feature` · 例: `gallery2d_halcon_ext`
- `hx_estimate_tilt_zc` (halcon: `estimate_tilt_zc`) `image → feature` · 例: `gallery2d_halcon_ext`
- `hx_estimate_sl_al_lr` (halcon: `estimate_sl_al_lr`) `image → feature` · 例: `gallery2d_halcon_ext`
- `hx_estimate_sl_al_zc` (halcon: `estimate_sl_al_zc`) `image → feature` · 例: `gallery2d_halcon_ext`
- `hx_estimate_al_am` (halcon: `estimate_al_am`) `image → feature` · 例: `gallery2d_halcon_ext`
- `hx_add_noise_contour` (halcon: `add_noise_white_contour_xld`) `contour → contour` · 例: `gallery2d_halcon_ext`
- `hx_radial_distort_contour` (halcon: `change_radial_distortion_contours_xld`) `contour → contour` · 例: `gallery2d_halcon_ext`
- `hx_dist_ellipse_points` (halcon: `dist_ellipse_contour_points_xld`) `contour → feature` · 例: `gallery2d_halcon_ext`
- `hx_dist_rect2_points` (halcon: `dist_rectangle2_contour_points_xld`) `contour → feature` · 例: `gallery2d_halcon_ext`
- `hx_distance_pc` (halcon: `distance_pc`) `contour → feature` · 例: `gallery2d_halcon_ext`
- `hx_disparity_to_xyz` (halcon: `disparity_image_to_xyz`) `image → image` · 例: `gallery2d_halcon_ext`
- `hx_distance_pr` (halcon: `distance_pr`) `region → feature` · 例: `gallery2d_halcon_ext`
- `hx_distance_sc` (halcon: `distance_sc`) `contour → feature` · 例: `gallery2d_halcon_ext`
- `hx_fuzzy_measure_pairs` (halcon: `fuzzy_measure_pairs`) `image → feature` · 例: `gallery2d_halcon_ext`

### intensity-transform(1)
- `xmh_soft` `image → image` · 例: `gallery2d_gray_arith`

### macro(4)
- `macro_denoise` `image → image` · 例: `gallery2d_physics_alife_3d`, `sim2real_and_alife`
- `macro_edge` `image → region` · 例: `gallery2d_physics_alife_3d`
- `macro_binarize` `image → image` · 例: `gallery2d_physics_alife_3d`
- `macro_vol_denoise` `volume → volume` · 例: `gallery2d_physics_alife_3d`

### matching(2)
- `ncc_locate` (halcon: `find_ncc_model`) `image → match` · 例: `gallery2d_contour_measure`
- `shape_locate` (halcon: `find_shape_model`) `image → match` · 例: `gallery2d_contour_measure`

### measure1d(5)
- `m1_measure_projection` (halcon: `measure_projection`) `image → feature` · 例: `gallery2d_contour_measure`
- `m1_measure_pos` (halcon: `measure_pos`) `image → contour` · 例: `gallery2d_contour_measure`
- `m1_measure_thresh` (halcon: `measure_thresh`) `image → feature` · 例: `gallery2d_contour_measure`
- `m1_measure_pairs` (halcon: `measure_pairs`) `image → feature` · 例: `gallery2d_contour_measure`
- `m1_fuzzy_measure_pos` (halcon: `fuzzy_measure_pos`) `image → contour` · 例: `gallery2d_contour_measure`

### misc(1)
- `identity` (halcon: `copy_image`) `any → any` · 例: なし

### morphology(33)
- `gerode` (halcon: `gray_erosion`) `image → image` · 例: `gallery2d_morphology`
- `gdilate` (halcon: `gray_dilation`) `image → image` · 例: `gallery2d_morphology`
- `gopen` (halcon: `gray_opening`) `image → image` · 例: `gallery2d_morphology`
- `gclose` (halcon: `gray_closing`) `image → image` · 例: `gallery2d_morphology`
- `tophat` (halcon: `gray_tophat`) `image → image` · 例: `gallery2d_morphology`
- `bothat` (halcon: `gray_bothat`) `image → image` · 例: `gallery2d_morphology`
- `morph_grad` (halcon: `gray_range_rect`) `image → image` · 例: `gallery2d_morphology`
- `sk_area_opening` `image → image` · 例: `gallery2d_morphology`
- `cv_open` (halcon: `gray_opening`) `image → image` · 例: `gallery2d_morphology`
- `cv_close` (halcon: `gray_closing`) `image → image` · 例: `gallery2d_morphology`
- `cv_tophat` (halcon: `gray_tophat`) `image → image` · 例: `gallery2d_morphology`
- `cv_gradient` (halcon: `gray_range_rect`) `image → image` · 例: `gallery2d_morphology`
- `cv_blackhat` (halcon: `gray_bothat`) `image → image` · 例: `gallery2d_morphology`
- `cv_erode` (halcon: `gray_erosion`) `image → image` · 例: `gallery2d_morphology`
- `cv_dilate` (halcon: `gray_dilation`) `image → image` · 例: `gallery2d_morphology`
- `gray_erosion` (halcon: `gray_erosion`) `image → image` · 例: `gallery2d_morphology`
- `gray_dilation` (halcon: `gray_dilation`) `image → image` · 例: `gallery2d_morphology`
- `gray_opening` (halcon: `gray_opening`) `image → image` · 例: `gallery2d_morphology`
- `gray_closing` (halcon: `gray_closing`) `image → image` · 例: `gallery2d_morphology`
- `gray_opening_shape` (halcon: `gray_opening_shape`) `image → image` · 例: `gallery2d_morphology`
- `gray_closing_shape` (halcon: `gray_closing_shape`) `image → image` · 例: `gallery2d_morphology`
- `gray_tophat` (halcon: `gray_tophat`) `image → image` · 例: `gallery2d_morphology`
- `gray_bothat` (halcon: `gray_bothat`) `image → image` · 例: `gallery2d_morphology`
- `gray_erosion_shape` (halcon: `gray_erosion_shape`) `image → image` · 例: `gallery2d_morphology`
- `gray_dilation_shape` (halcon: `gray_dilation_shape`) `image → image` · 例: `gallery2d_morphology`
- `gray_opening_rect` (halcon: `gray_opening_rect`) `image → image` · 例: `gallery2d_morphology`
- `gray_closing_rect` (halcon: `gray_closing_rect`) `image → image` · 例: `gallery2d_morphology`
- `xsk2_reconstruction` `image → image` · 例: `gallery2d_morphology`
- `xsk2_diameter_opening` `image → image` · 例: `gallery2d_morphology`
- `xsk3_area_closing` `image → image` · 例: `gallery2d_morphology`
- `xsk3_diameter_closing` `image → image` · 例: `gallery2d_morphology`
- `f2_gray_skeleton` (halcon: `gray_skeleton`) `image → image` · 例: `gallery2d_morphology`
- `f2_gray_inside` (halcon: `gray_inside`) `image → image` · 例: `gallery2d_morphology`

### morphology/markers(1)
- `xmh_regmin` `image → region` · 例: `gallery2d_segmentation`

### noise(2)
- `add_noise_white` (halcon: `add_noise_white`) `image → image` · 例: `gallery2d_smoothing_rank`
- `add_noise_distribution` (halcon: `add_noise_distribution`) `image → image` · 例: `gallery2d_smoothing_rank`

### physics(6)
- `ph_perona_malik` `image → image` · 例: `gallery2d_physics_alife_3d`
- `ph_coherence_enhancing_diffusion` `image → image` · 例: `gallery2d_physics_alife_3d`
- `ph_reaction_diffusion` `image → image` · 例: `gallery2d_physics_alife_3d`
- `ph_heat_flow` `image → image` · 例: `gallery2d_physics_alife_3d`
- `ph_mean_curvature_motion` `image → image` · 例: `gallery2d_physics_alife_3d`
- `ph_total_variation_flow` `image → image` · 例: `gallery2d_physics_alife_3d`

### rank(23)
- `median` (halcon: `median_image`) `image → image` · 例: `consumer_onocollo`, `gallery2d_smoothing_rank`, `perception_pipeline`, `quickstart`
- `min_filter` (halcon: `gray_erosion_rect`) `image → image` · 例: `gallery2d_smoothing_rank`
- `max_filter` (halcon: `gray_dilation_rect`) `image → image` · 例: `gallery2d_smoothing_rank`
- `percentile` (halcon: `rank_image`) `image → image` · 例: `gallery2d_smoothing_rank`
- `sk_median_disk` (halcon: `median_image`) `image → image` · 例: `gallery2d_smoothing_rank`
- `cv_median` (halcon: `median_image`) `image → image` · 例: `gallery2d_smoothing_rank`
- `median_image` (halcon: `median_image`) `image → image` · 例: `gallery2d_smoothing_rank`
- `median_rect` (halcon: `median_rect`) `image → image` · 例: `gallery2d_smoothing_rank`
- `median_separate` (halcon: `median_separate`) `image → image` · 例: `gallery2d_smoothing_rank`
- `gray_erosion_rect` (halcon: `gray_erosion_rect`) `image → image` · 例: `gallery2d_smoothing_rank`
- `gray_dilation_rect` (halcon: `gray_dilation_rect`) `image → image` · 例: `gallery2d_smoothing_rank`
- `gray_range_rect` (halcon: `gray_range_rect`) `image → image` · 例: `gallery2d_smoothing_rank`
- `rank_image` (halcon: `rank_image`) `image → image` · 例: `gallery2d_smoothing_rank`
- `rank_rect` (halcon: `rank_rect`) `image → image` · 例: `gallery2d_smoothing_rank`
- `trimmed_mean` (halcon: `trimmed_mean`) `image → image` · 例: `gallery2d_smoothing_rank`
- `eliminate_min_max` (halcon: `eliminate_min_max`) `image → image` · 例: `gallery2d_smoothing_rank`
- `median_weighted` (halcon: `median_weighted`) `image → image` · 例: `gallery2d_smoothing_rank`
- `mean_sp` (halcon: `mean_sp`) `image → image` · 例: `gallery2d_smoothing_rank`
- `eliminate_sp` (halcon: `eliminate_sp`) `image → image` · 例: `gallery2d_smoothing_rank`
- `dual_rank` (halcon: `dual_rank`) `image → image` · 例: `gallery2d_smoothing_rank`
- `xpil_mode_filter` `image → image` · 例: `gallery2d_smoothing_rank`
- `xsk2_rank_geomean` `image → image` · 例: `gallery2d_smoothing_rank`
- `xkor_median` `image → image` · 例: `gallery2d_smoothing_rank`

### region(78)
- `reg_erode` (halcon: `erosion_circle`) `region → region` · 例: `gallery2d_region`
- `reg_dilate` (halcon: `dilation_circle`) `region → region` · 例: `gallery2d_region`
- `reg_open` (halcon: `opening_circle`) `region → region` · 例: `gallery2d_region`
- `reg_close` (halcon: `closing_circle`) `region → region` · 例: `gallery2d_region`
- `fill_holes` (halcon: `fill_up`) `region → region` · 例: `gallery2d_region`
- `select_largest` (halcon: `select_shape_std`) `region → region` · 例: `gallery2d_region`
- `remove_small` (halcon: `select_shape`) `region → region` · 例: `gallery2d_region`, `quickstart`
- `invert_region` (halcon: `complement`) `region → region` · 例: `gallery2d_region`
- `dist_transform` (halcon: `distance_transform`) `region → image` · 例: `gallery2d_region`
- `region_boundary` (halcon: `boundary`) `region → region` · 例: `gallery2d_region`
- `convex_fill` (halcon: `shape_trans`) `region → region` · 例: `gallery2d_region`
- `sk_skeleton` (halcon: `skeleton`) `region → region` · 例: `gallery2d_region`
- `sk_medial` (halcon: `skeleton`) `region → region` · 例: `gallery2d_region`
- `sk_convex` (halcon: `shape_trans`) `region → region` · 例: `gallery2d_region`
- `sk_thin` (halcon: `thinning`) `region → region` · 例: `gallery2d_region`
- `sk_remove_holes` (halcon: `fill_up`) `region → region` · 例: `gallery2d_region`
- `sk_clear_border` `region → region` · 例: `gallery2d_region`
- `sk_find_boundaries` (halcon: `boundary`) `region → region` · 例: `gallery2d_region`
- `cv_dist` (halcon: `distance_transform`) `region → image` · 例: `gallery2d_region`
- `erosion_circle` (halcon: `erosion_circle`) `region → region` · 例: `gallery2d_region`
- `dilation_circle` (halcon: `dilation_circle`) `region → region` · 例: `gallery2d_region`
- `opening_circle` (halcon: `opening_circle`) `region → region` · 例: `gallery2d_region`
- `closing_circle` (halcon: `closing_circle`) `region → region` · 例: `gallery2d_region`
- `erosion_rectangle1` (halcon: `erosion_rectangle1`) `region → region` · 例: `gallery2d_region`
- `dilation_rectangle1` (halcon: `dilation_rectangle1`) `region → region` · 例: `gallery2d_region`
- `opening_rectangle1` (halcon: `opening_rectangle1`) `region → region` · 例: `gallery2d_region`
- `closing_rectangle1` (halcon: `closing_rectangle1`) `region → region` · 例: `gallery2d_region`
- `fill_up` (halcon: `fill_up`) `region → region` · 例: `gallery2d_region`
- `boundary` (halcon: `boundary`) `region → region` · 例: `gallery2d_region`
- `skeleton` (halcon: `skeleton`) `region → region` · 例: `gallery2d_region`
- `thinning` (halcon: `thinning`) `region → region` · 例: `gallery2d_region`
- `shape_trans` (halcon: `shape_trans`) `region → region` · 例: `gallery2d_region`
- `select_shape_std` (halcon: `select_shape_std`) `region → region` · 例: `gallery2d_region`
- `select_shape` (halcon: `select_shape`) `region → region` · 例: `gallery2d_region`
- `distance_transform` (halcon: `distance_transform`) `region → image` · 例: `gallery2d_region`
- `pruning` (halcon: `pruning`) `region → region` · 例: `gallery2d_region`
- `closest_point_transform` (halcon: `closest_point_transform`) `region → image` · 例: `gallery2d_region`
- `junctions_skeleton` (halcon: `junctions_skeleton`) `region → region` · 例: `gallery2d_region`
- `erosion_golay` (halcon: `erosion_golay`) `region → region` · 例: `gallery2d_region`
- `dilation_golay` (halcon: `dilation_golay`) `region → region` · 例: `gallery2d_region`
- `opening_golay` (halcon: `opening_golay`) `region → region` · 例: `gallery2d_region`
- `closing_golay` (halcon: `closing_golay`) `region → region` · 例: `gallery2d_region`
- `erosion_seq` (halcon: `erosion_seq`) `region → region` · 例: `gallery2d_region`
- `dilation_seq` (halcon: `dilation_seq`) `region → region` · 例: `gallery2d_region`
- `morph_skeleton` (halcon: `morph_skeleton`) `region → region` · 例: `gallery2d_region`
- `thinning_golay` (halcon: `thinning_golay`) `region → region` · 例: `gallery2d_region`
- `thinning_seq` (halcon: `thinning_seq`) `region → region` · 例: `gallery2d_region`
- `fill_up_shape` (halcon: `fill_up_shape`) `region → region` · 例: `gallery2d_region`
- `remove_noise_region` (halcon: `remove_noise_region`) `region → region` · 例: `gallery2d_region`
- `smallest_rectangle1` (halcon: `smallest_rectangle1`) `region → region` · 例: `gallery2d_region`
- `get_region_contour` (halcon: `get_region_contour`) `region → region` · 例: `gallery2d_region`
- `get_region_convex` (halcon: `get_region_convex`) `region → region` · 例: `gallery2d_region`
- `xsp_chamfer_dist` `region → image` · 例: `gallery2d_region`
- `xsk2_isotropic_close` `region → region` · 例: `gallery2d_region`
- `xcv2_hitmiss` `region → region` · 例: `gallery2d_region`
- `xsk3_rank_majority` `region → region` · 例: `gallery2d_region`
- `r2_inner_circle` (halcon: `inner_circle`) `region → region` · 例: `gallery2d_region`
- `r2_inner_rectangle1` (halcon: `inner_rectangle1`) `region → region` · 例: `gallery2d_region`
- `r2_smallest_rectangle1` `region → region` · 例: `gallery2d_region`
- `r2_smallest_circle` (halcon: `smallest_circle`) `region → region` · 例: `gallery2d_region`
- `r2_smallest_rectangle2` (halcon: `smallest_rectangle2`) `region → region` · 例: `gallery2d_region`
- `r2_sort_region` (halcon: `sort_region`) `region → region` · 例: `gallery2d_region`
- `r2_union1` (halcon: `union1`) `region → region` · 例: `gallery2d_region`
- `r2_partition_rectangle` (halcon: `partition_rectangle`) `region → region` · 例: `gallery2d_region`
- `r2_runlength_features` (halcon: `runlength_features`) `region → feature` · 例: `gallery2d_region`
- `r2_split_skeleton_lines` (halcon: `split_skeleton_lines`) `region → region` · 例: `gallery2d_region`
- `em_skeleton` `region → region` · 例: `gallery2d_region`
- `r2_endpoints_skeleton` `region → region` · 例: `gallery2d_region`
- `r3_background_seg` (halcon: `background_seg`) `region → region` · 例: `gallery2d_region`
- `r3_clip_region` (halcon: `clip_region`) `region → region` · 例: `gallery2d_region`
- `r3_eliminate_runs` (halcon: `eliminate_runs`) `region → region` · 例: `gallery2d_region`
- `r3_rank_region` (halcon: `rank_region`) `region → region` · 例: `gallery2d_region`
- `r3_region_features` (halcon: `region_features`) `region → feature` · 例: `gallery2d_region`
- `r3_runlength_distribution` (halcon: `runlength_distribution`) `region → feature` · 例: `gallery2d_region`
- `r3_select_region_point` (halcon: `select_region_point`) `region → region` · 例: `gallery2d_region`
- `r3_partition_dynamic` (halcon: `partition_dynamic`) `region → region` · 例: `gallery2d_region`
- `r3_polar_trans_region` (halcon: `polar_trans_region`) `region → region` · 例: `gallery2d_region`
- `r3_label_to_region` (halcon: `label_to_region`) `region → region` · 例: `gallery2d_region`

### region-morphology(1)
- `xmh_majority` `region → region` · 例: `gallery2d_region`

### region-transform(1)
- `xmh_bwperim` `region → region` · 例: `gallery2d_region`

### restoration(12)
- `xsk_inpaint` `image → image` · 例: `gallery2d_smoothing_rank`
- `xsk_richardson_lucy` `image → image` · 例: `gallery2d_smoothing_rank`
- `xsk_unwrap_phase` `image → image` · 例: `gallery2d_smoothing_rank`
- `xcv_inpaint` `image → image` · 例: `gallery2d_smoothing_rank`
- `xsk2_wiener` `image → image` · 例: `gallery2d_smoothing_rank`
- `xcv3_inpaint_ns` `image → image` · 例: `gallery2d_smoothing_rank`
- `iv_richardson_lucy` `image → image` · 例: `gallery2d_smoothing_rank`
- `iv_wiener_deconv_spatial` `image → image` · 例: `gallery2d_smoothing_rank`
- `iv_unsharp_deblur` `image → image` · 例: `gallery2d_smoothing_rank`
- `iv_motion_deblur` `image → image` · 例: `gallery2d_smoothing_rank`
- `iv_backproject_superres` `image → image` · 例: `gallery2d_smoothing_rank`
- `iv_gradient_inpaint` `image → image` · 例: `gallery2d_smoothing_rank`

### segment(7)
- `sg_slic_superpixels` `image → region` · 例: `gallery2d_segmentation`
- `sg_felzenszwalb` `image → region` · 例: `gallery2d_segmentation`
- `sg_gmm_segment` `image → region` · 例: `gallery2d_segmentation`
- `sg_kmeans_intensity` `image → region` · 例: `gallery2d_segmentation`
- `sg_region_growing_seeded` `image → region` · 例: `gallery2d_segmentation`
- `sg_normalized_cut_2` `image → region` · 例: `gallery2d_segmentation`
- `sg_watershed_gradient` `image → region` · 例: `gallery2d_segmentation`

### segmentation(56)
- `threshold` (halcon: `threshold`) `image → region` · 例: `gallery2d_segmentation`
- `otsu` (halcon: `binary_threshold`) `image → region` · 例: `ct_inspection`, `gallery2d_segmentation`, `quickstart`, `segment_and_classify`
- `dyn_threshold` (halcon: `dyn_threshold`) `image → region` · 例: `gallery2d_segmentation`
- `canny` (halcon: `edges_image`) `image → region` · 例: `gallery2d_segmentation`
- `local_max` (halcon: `local_max_sub_pix`) `image → region` · 例: `gallery2d_segmentation`
- `adaptive_gauss_thresh` (halcon: `local_threshold`) `image → region` · 例: `gallery2d_segmentation`
- `sk_otsu` (halcon: `binary_threshold`) `image → region` · 例: `gallery2d_segmentation`
- `sk_li` (halcon: `binary_threshold`) `image → region` · 例: `gallery2d_segmentation`
- `sk_yen` (halcon: `binary_threshold`) `image → region` · 例: `gallery2d_segmentation`
- `sk_sauvola` (halcon: `var_threshold`) `image → region` · 例: `gallery2d_segmentation`
- `sk_niblack` (halcon: `var_threshold`) `image → region` · 例: `gallery2d_segmentation`
- `sk_canny` (halcon: `edges_image`) `image → region` · 例: `gallery2d_segmentation`
- `sk_felzenszwalb` `image → region` · 例: `gallery2d_segmentation`
- `sk_slic` `image → region` · 例: `gallery2d_segmentation`
- `sk_chan_vese` `image → region` · 例: `gallery2d_segmentation`
- `sk_local_maxima` (halcon: `local_max`) `image → region` · 例: `gallery2d_segmentation`
- `sk_hysteresis` (halcon: `hysteresis_threshold`) `image → region` · 例: `gallery2d_segmentation`
- `cv_otsu` (halcon: `binary_threshold`) `image → region` · 例: `gallery2d_segmentation`
- `cv_adaptive_mean` (halcon: `dyn_threshold`) `image → region` · 例: `gallery2d_segmentation`
- `cv_adaptive_gauss` (halcon: `local_threshold`) `image → region` · 例: `gallery2d_segmentation`
- `cv_canny` (halcon: `edges_image`) `image → region` · 例: `gallery2d_segmentation`
- `h_threshold` (halcon: `threshold`) `image → region` · 例: `gallery2d_segmentation`
- `binary_threshold` (halcon: `binary_threshold`) `image → region` · 例: `gallery2d_segmentation`
- `auto_threshold` (halcon: `auto_threshold`) `image → region` · 例: `gallery2d_segmentation`
- `dyn_threshold` (halcon: `dyn_threshold`) `image → region` · 例: `gallery2d_segmentation`
- `var_threshold` (halcon: `var_threshold`) `image → region` · 例: `gallery2d_segmentation`
- `local_threshold` (halcon: `local_threshold`) `image → region` · 例: `gallery2d_segmentation`
- `hysteresis_threshold` (halcon: `hysteresis_threshold`) `image → region` · 例: `gallery2d_segmentation`
- `edges_image` (halcon: `edges_image`) `image → region` · 例: `gallery2d_segmentation`
- `watersheds` (halcon: `watersheds`) `image → region` · 例: `gallery2d_segmentation`
- `watersheds_threshold` (halcon: `watersheds_threshold`) `image → region` · 例: `gallery2d_segmentation`
- `regiongrowing` (halcon: `regiongrowing`) `image → region` · 例: `gallery2d_segmentation`
- `local_max` (halcon: `local_max`) `image → region` · 例: `gallery2d_segmentation`
- `dual_threshold` (halcon: `dual_threshold`) `image → region` · 例: `gallery2d_segmentation`
- `segment_image_mser` (halcon: `segment_image_mser`) `image → region` · 例: `gallery2d_segmentation`
- `regiongrowing_mean` (halcon: `regiongrowing_mean`) `image → region` · 例: `gallery2d_segmentation`
- `zero_crossing` (halcon: `zero_crossing`) `image → region` · 例: `gallery2d_segmentation`
- `local_min` (halcon: `local_min`) `image → region` · 例: `gallery2d_segmentation`
- `bin_threshold` (halcon: `bin_threshold`) `image → region` · 例: `gallery2d_segmentation`
- `fast_threshold` (halcon: `fast_threshold`) `image → region` · 例: `gallery2d_segmentation`
- `nonmax_suppression_amp` (halcon: `nonmax_suppression_amp`) `image → region` · 例: `gallery2d_segmentation`
- `pouring` (halcon: `pouring`) `image → region` · 例: `gallery2d_segmentation`
- `xsk_random_walker` `image → region` · 例: `gallery2d_segmentation`
- `xsk_flood` `image → region` · 例: `gallery2d_segmentation`
- `xcv_grabcut` `image → region` · 例: `gallery2d_segmentation`
- `xcv_watershed_markers` (halcon: `watersheds`) `image → region` · 例: `gallery2d_segmentation`
- `xsk2_multiotsu` `image → image` · 例: `gallery2d_segmentation`
- `xsk2_h_maxima` `image → region` · 例: `gallery2d_segmentation`
- `xcv2_meanshift` `image → image` · 例: `gallery2d_segmentation`
- `xmh_bernsen` `image → region` · 例: `gallery2d_segmentation`
- `xsk3_rank_otsu` `image → region` · 例: `gallery2d_segmentation`
- `xsk3_h_minima` `image → region` · 例: `gallery2d_segmentation`
- `xsk3_threshold_local_median` `image → region` · 例: `gallery2d_segmentation`
- `xsk3_peak_local_max` `image → region` · 例: `gallery2d_segmentation`
- `xkor_canny` `image → region` · 例: `gallery2d_segmentation`
- `it_region_to_bin` (halcon: `region_to_bin`) `image → image` · 例: `gallery2d_segmentation`

### self-similarity(1)
- `xmh_selfmatch` `image → image` · 例: `gallery2d_features`

### smoothing(48)
- `gaussian` (halcon: `gauss_filter`) `image → image` · 例: `ct_inspection`, `gallery2d_smoothing_rank`, `quickstart`
- `mean_box` (halcon: `mean_image`) `image → image` · 例: `gallery2d_smoothing_rank`
- `bilateral` (halcon: `bilateral_filter`) `image → image` · 例: `gallery2d_smoothing_rank`, `quickstart`
- `unsharp` (halcon: `emphasize`) `image → image` · 例: `gallery2d_smoothing_rank`
- `sk_tv` `image → image` · 例: `gallery2d_smoothing_rank`
- `sk_wavelet` `image → image` · 例: `gallery2d_smoothing_rank`
- `sk_rolling_ball` `image → image` · 例: `gallery2d_smoothing_rank`
- `sk_nlm` `image → image` · 例: `gallery2d_smoothing_rank`
- `sk_tv_bregman` `image → image` · 例: `gallery2d_smoothing_rank`
- `cv_bilateral` (halcon: `bilateral_filter`) `image → image` · 例: `gallery2d_smoothing_rank`
- `cv_box` (halcon: `mean_image`) `image → image` · 例: `gallery2d_smoothing_rank`
- `cv_gaussian` (halcon: `gauss_filter`) `image → image` · 例: `gallery2d_smoothing_rank`
- `cv_nlmeans` `image → image` · 例: `gallery2d_smoothing_rank`
- `cv_sharpen` (halcon: `emphasize`) `image → image` · 例: `gallery2d_smoothing_rank`
- `dl_aniso_diffusion` (halcon: `anisotropic_diffusion`) `image → image` · 例: `gallery2d_smoothing_rank`
- `dl_guided_filter` (halcon: `guided_filter`) `image → image` · 例: `gallery2d_smoothing_rank`
- `gauss_filter` (halcon: `gauss_filter`) `image → image` · 例: `gallery2d_smoothing_rank`
- `gauss_image` (halcon: `gauss_image`) `image → image` · 例: `gallery2d_smoothing_rank`
- `mean_image` (halcon: `mean_image`) `image → image` · 例: `gallery2d_smoothing_rank`
- `binomial_filter` (halcon: `binomial_filter`) `image → image` · 例: `gallery2d_smoothing_rank`
- `smooth_image` (halcon: `smooth_image`) `image → image` · 例: `gallery2d_smoothing_rank`
- `mean_curvature_flow` (halcon: `mean_curvature_flow`) `image → image` · 例: `gallery2d_smoothing_rank`
- `sigma_image` (halcon: `sigma_image`) `image → image` · 例: `gallery2d_smoothing_rank`
- `anisotropic_diffusion` (halcon: `anisotropic_diffusion`) `image → image` · 例: `gallery2d_smoothing_rank`
- `isotropic_diffusion` (halcon: `isotropic_diffusion`) `image → image` · 例: `gallery2d_smoothing_rank`
- `coherence_enhancing_diff` (halcon: `coherence_enhancing_diff`) `image → image` · 例: `gallery2d_smoothing_rank`
- `bilateral_filter` (halcon: `bilateral_filter`) `image → image` · 例: `gallery2d_smoothing_rank`
- `guided_filter` (halcon: `guided_filter`) `image → image` · 例: `gallery2d_smoothing_rank`
- `simulate_motion` (halcon: `simulate_motion`) `image → image` · 例: `gallery2d_smoothing_rank`
- `simulate_defocus` (halcon: `simulate_defocus`) `image → image` · 例: `gallery2d_smoothing_rank`
- `xcv_edge_preserving` `image → image` · 例: `gallery2d_smoothing_rank`
- `xpil_smooth_more` `image → image` · 例: `gallery2d_smoothing_rank`
- `xpil_unsharp_mask` `image → image` · 例: `gallery2d_smoothing_rank`
- `xsp_wiener` `image → image` · 例: `gallery2d_smoothing_rank`
- `xsp_savgol` `image → image` · 例: `gallery2d_smoothing_rank`
- `xsp_dct_denoise` `image → image` · 例: `gallery2d_smoothing_rank`
- `xsp_cspline_smooth` `image → image` · 例: `gallery2d_smoothing_rank`
- `xwt_visushrink` `image → image` · 例: `gallery2d_smoothing_rank`
- `xwt_firm_denoise` `image → image` · 例: `gallery2d_smoothing_rank`
- `xwt_lf_reconstruct` `image → image` · 例: `gallery2d_smoothing_rank`
- `xsk3_rank_mean_bilateral` `image → image` · 例: `gallery2d_smoothing_rank`
- `xcv3_denoise_tvl1` `image → image` · 例: `gallery2d_smoothing_rank`
- `xcv3_pyr_laplacian` `image → image` · 例: `gallery2d_smoothing_rank`
- `xkor_gaussian` `image → image` · 例: `gallery2d_smoothing_rank`
- `xkor_bilateral` `image → image` · 例: `gallery2d_smoothing_rank`
- `xkor_unsharp` `image → image` · 例: `gallery2d_smoothing_rank`
- `xkor_motion_blur` `image → image` · 例: `gallery2d_smoothing_rank`
- `f2_gauss_pyramid` (halcon: `gen_gauss_pyramid`) `image → image` · 例: `gallery2d_smoothing_rank`

### subpix(6)
- `sp_local_max_sub_pix` `image → contour` · 例: `gallery2d_geometry`
- `sp_local_min_sub_pix` (halcon: `local_min_sub_pix`) `image → contour` · 例: `gallery2d_geometry`
- `sp_saddle_points_sub_pix` (halcon: `saddle_points_sub_pix`) `image → contour` · 例: `gallery2d_geometry`
- `sp_critical_points_sub_pix` (halcon: `critical_points_sub_pix`) `image → contour` · 例: `gallery2d_geometry`
- `sp_plateaus` (halcon: `plateaus`) `image → contour` · 例: `gallery2d_geometry`
- `sp_lowlands_center` (halcon: `lowlands_center`) `image → contour` · 例: `gallery2d_geometry`

### tactile(5)
- `tac_contact_mask` `image → region` · 例: `sim2real_and_alife`
- `tac_height_from_shading` `image → image` · 例: `sim2real_and_alife`
- `tac_surface_normal` `image → image` · 例: `sim2real_and_alife`
- `tac_pressure_proxy` `image → image` · 例: `sim2real_and_alife`
- `tac_shear_field` `image → image` · 例: `sim2real_and_alife`

### texture(22)
- `std_filter` (halcon: `deviation_image`) `image → image` · 例: `gallery2d_texture_freq`
- `gabor` (halcon: `gen_gabor`) `image → image` · 例: `gallery2d_texture_freq`
- `sk_frangi` (halcon: `lines_gauss`) `image → image` · 例: `gallery2d_texture_freq`
- `sk_meijering` (halcon: `lines_gauss`) `image → image` · 例: `gallery2d_texture_freq`
- `sk_hessian` (halcon: `lines_gauss`) `image → image` · 例: `gallery2d_texture_freq`
- `sk_gabor` (halcon: `gen_gabor`) `image → image` · 例: `gallery2d_texture_freq`
- `sk_lbp` `image → image` · 例: `gallery2d_texture_freq`
- `sk_entropy` (halcon: `entropy_image`) `image → image` · 例: `gallery2d_texture_freq`
- `sk_shape_index` `image → image` · 例: `gallery2d_texture_freq`
- `deviation_image` (halcon: `deviation_image`) `image → image` · 例: `gallery2d_texture_freq`
- `texture_laws` (halcon: `texture_laws`) `image → image` · 例: `gallery2d_texture_freq`
- `entropy_image` (halcon: `entropy_image`) `image → image` · 例: `gallery2d_texture_freq`
- `gen_gabor` (halcon: `gen_gabor`) `image → image` · 例: `gallery2d_texture_freq`
- `cooc_feature_matrix` (halcon: `cooc_feature_matrix`) `image → feature` · 例: `gallery2d_texture_freq`
- `xsk_struct_coherence` `image → image` · 例: `gallery2d_texture_freq`
- `xsk_meijering` `image → image` · 例: `gallery2d_texture_freq`
- `xsk_sato` `image → image` · 例: `gallery2d_texture_freq`
- `xsp_hilbert_env` `image → image` · 例: `gallery2d_texture_freq`
- `xsk2_hog` `image → image` · 例: `gallery2d_texture_freq`
- `f2_symmetry` (halcon: `symmetry`) `image → image` · 例: `gallery2d_texture_freq`
- `tf_census_transform` `image → image` · 例: `gallery2d_texture_freq`
- `tf_rank_transform` `image → image` · 例: `gallery2d_texture_freq`

### texture-feature(1)
- `xmh_pftas` `image → feature` · 例: `gallery2d_features`

### texture/shape-feature(1)
- `xmh_zernike` `image → feature` · 例: `gallery2d_features`

### tomography(5)
- `tm_radon_forward` `image → image` · 例: `gallery2d_physics_alife_3d`
- `tm_fbp_reconstruct` `image → image` · 例: `gallery2d_physics_alife_3d`
- `tm_sart_reconstruct` `image → image` · 例: `gallery2d_physics_alife_3d`
- `tm_backproject_unfiltered` `image → image` · 例: `gallery2d_physics_alife_3d`
- `tm_sinogram_denoise` `image → image` · 例: `gallery2d_physics_alife_3d`

### transform(3)
- `xmh_haar` `image → image` · 例: `gallery2d_geometry`
- `xmh_daubechies` `image → image` · 例: `gallery2d_geometry`
- `tf_radon_sinogram` `image → image` · 例: `gallery2d_geometry`

### xldgeom(10)
- `xg_moments` (halcon: `moments_points_xld`) `contour → feature` · 例: `gallery2d_geometry`
- `xg_area_center` (halcon: `area_center_points_xld`) `contour → feature` · 例: `gallery2d_geometry`
- `xg_eccentricity` (halcon: `eccentricity_points_xld`) `contour → feature` · 例: `gallery2d_geometry`
- `xg_orientation` (halcon: `orientation_points_xld`) `contour → feature` · 例: `gallery2d_geometry`
- `xg_elliptic_axis` (halcon: `elliptic_axis_points_xld`) `contour → feature` · 例: `gallery2d_geometry`
- `xg_height_width_ratio` (halcon: `height_width_ratio_xld`) `contour → feature` · 例: `gallery2d_geometry`
- `xg_regress_contours` `contour → feature` · 例: `gallery2d_geometry`
- `xg_clip_contours` `contour → contour` · 例: `gallery2d_geometry`
- `xg_gen_polygons` (halcon: `gen_polygons_xld`) `contour → contour` · 例: `gallery2d_geometry`
- `xg_crop_contours` `contour → contour` · 例: `gallery2d_geometry`

## 1-D operators(ops1d)by category
_計 37 ops / 3 categories。_


プロファイル/信号の 1-D op。源流は 2-D の measure1d・3-D の probe・音声/センサー系列(dsp)— 取り出した (x, y) 列を funct1d/dsp で加工して測る。

### function(23)
- `create_funct_1d_array` (`signal → signal`) — A 1-D function from equidistant samples (HALCON ``create_funct_1d_array``).
- `create_funct_1d_pairs` (`signal, signal → pairs`) — A 1-D function from arbitrary ``(x, y)`` pairs, resampled to an
- `smooth_funct_1d_gauss` (`signal → signal`) — Gaussian smoothing of a 1-D function (HALCON ``smooth_funct_1d_gauss``).
- `smooth_funct_1d_mean` (`signal → signal`) — Iterated moving-average smoothing (HALCON ``smooth_funct_1d_mean``).
- `derivate_funct_1d` (`signal → signal`) — First derivative by central differences (HALCON ``derivate_funct_1d``).
- `integrate_funct_1d` (`signal → signal`) — Cumulative integral by the trapezoidal rule (HALCON ``integrate_funct_1d``).
- `zero_crossings_funct_1d` (`signal → indices`) — Indices where the function changes sign (HALCON ``zero_crossings_funct_1d``).
- `local_min_max_funct_1d` (`signal → table`) — Indices of strict local maxima / minima (HALCON ``local_min_max_funct_1d``).
- `abs_funct_1d` (`signal → signal`) — Absolute value of the y-values (HALCON ``abs_funct_1d``).
- `negate_funct_1d` (`signal → signal`) — Sign-flipped y-values (HALCON ``negate_funct_1d``).
- `invert_funct_1d` (`signal → pairs`) — Swap the roles of x and y: ``x = f^-1(y)`` (HALCON ``invert_funct_1d``).
- `scale_y_funct_1d` (`signal → signal`) — Linear map of the y-values, ``mult * y + add`` (HALCON ``scale_y_funct_1d``).
- `transform_funct_1d` (`signal → pairs`) — Independent affine transform of x and y (HALCON ``transform_funct_1d``).
- `compose_funct_1d` (`signal, signal → signal`) — Composition ``y1(y2)``: the values of *y2* used as positions into *y1*
- `sample_funct_1d` (`signal → signal`) — Every *step*-th sample (HALCON ``sample_funct_1d``).
- `match_funct_1d_trans` (`signal, signal → table`) — Best integer translation between two functions by cross-correlation
- `distance_funct_1d` (`signal, signal → measurement`) — Distance between two functions on the same grid (HALCON ``distance_funct_1d``).
- `num_points_funct_1d` (`signal → measurement`) — Number of samples (HALCON ``num_points_funct_1d``).
- `x_range_funct_1d` (`signal → pairs`) — The x-domain ``(0.0, n - 1.0)`` (HALCON ``x_range_funct_1d``).
- `y_range_funct_1d` (`signal → pairs`) — The value range ``(min(y), max(y))`` (HALCON ``y_range_funct_1d``).
- `get_pair_funct_1d` (`signal → pairs`) — The ``(x, y)`` pair at *index* (HALCON ``get_pair_funct_1d``).
- `get_y_value_funct_1d` (`signal → measurement`) — The y-value at (fractional) position *x* (HALCON ``get_y_value_funct_1d``).
- `funct_1d_to_pairs` (`signal → pairs`) — The function as explicit ``(x, y)`` pairs (HALCON ``funct_1d_to_pairs``).

### io(3)
- `read_wav` (`file → signal`) — Read a WAV file (stdlib) -> ``(x float64 [-1,1], rate)``. Multi-channel is
- `write_wav` (`signal → file`) — Write a float ``[-1,1]`` mono signal to a 16-bit PCM WAV (stdlib).
- `read_audio` (`file → signal`) — Read any audio format -> ``(x, rate)``. Uses ``soundfile`` if available

### signal(11)
- `lowpass` (`signal → signal`) — Butterworth low-pass (scipy, zero-phase filtfilt). *cutoff* must be inside
- `highpass` (`signal → signal`) — Butterworth high-pass. Same Nyquist / length contract as :func:`lowpass`.
- `bandpass` (`signal → signal`) — Butterworth band-pass between *low* and *high* Hz. Both edges must be inside
- `envelope` (`signal → signal`) — Amplitude envelope via the analytic (Hilbert) signal — the shape of a
- `rms` (`signal → measurement`) — RMS level. Scalar for the whole signal, or a framewise array when *frame*
- `resample` (`signal → signal`) — Resample a signal to *new_rate* (Fourier method).
- `spectrum` (`signal → pairs`) — Single-sided magnitude spectrum -> ``(freqs, magnitude)`` (real FFT).
- `spectrogram` (`signal → image2d`) — STFT magnitude spectrogram -> ``(freqs, times, S)`` with ``S`` shape
- `zero_crossing_rate` (`signal → measurement`) — Fraction of adjacent samples that change sign — a cheap pitch/noisiness cue.
- `find_peaks` (`signal → indices`) — Peak indices (scipy.signal.find_peaks) — impacts / defect echoes.
- `signal_features` (`signal → table`) — A compact acoustic/vibration feature vector for anomaly detection:

## Math operators(opsmath)by category
_計 26 ops / 4 categories。_


視覚計測を支える数学 op(線形代数/統計/補間・多項式)+ 複素解析の計算可能な切り口(周回積分・Cauchy 積分公式・偏角の原理・Laurent 係数/留数・等角写像・Cauchy-Riemann 残差)。北極星は「数学辞典級の網羅」(NEXT_OPS_PLAN §F)。FFT/複素画像は complexops・volfreq、1-D 関数は funct1d を参照。

### complex(10)
- `cplx_contour_circle` (` → cpoints`) — Sample a circle as a closed contour — the standard integration path.
- `cplx_poly_eval` (`signal, cpoints → cpoints`) — Evaluate a polynomial on the complex plane (Horner, complex-capable).
- `cplx_contour_integral` (`cpoints, cpoints → cscalar`) — Closed contour integral ``∮ f(z) dz`` by the chordal trapezoidal rule.
- `cplx_winding_number` (`cpoints → measurement`) — Winding number of a closed contour around a point (turning number).
- `cplx_cauchy_value` (`cpoints, cpoints → cscalar`) — Cauchy's integral formula: recover ``f(w)`` **inside** a contour from its
- `cplx_argument_principle` (`cpoints, cpoints → measurement`) — Argument principle: count zeros minus poles enclosed by a contour, from
- `cplx_laurent_coeffs` (`cpoints, cpoints → table`) — Laurent (and Taylor) coefficients on a **uniformly sampled circle** —
- `cplx_joukowski` (`cpoints → cpoints`) — Joukowski (Zhukovsky) conformal map ``w = z + c^2 / z``.
- `cplx_mobius` (`cpoints → cpoints`) — Möbius (linear fractional) map ``w = (a z + b) / (c z + d)``.
- `cplx_cr_residual` (`cimage → measurement`) — Cauchy-Riemann residual of a sampled complex field — "is this field

### interp_poly(5)
- `interp_linear` (`signal, signal, signal → signal`) — Piecewise-linear interpolation of ``(x, y)`` samples at query *xq*.
- `interp_cubic` (`signal, signal, signal → signal`) — Cubic-spline interpolation (``scipy.interpolate.CubicSpline``).
- `poly_fit` (`signal, signal → table`) — Least-squares polynomial fit with its conditioning **on the record**.
- `poly_eval` (`signal, signal → signal`) — Evaluate a polynomial (coefficients highest-power-first) at *x*.
- `poly_roots` (`signal → roots`) — All roots of a polynomial (coefficients highest-power-first) — complex

### linalg(6)
- `mat_solve` (`matrix, signal → signal`) — Solve the square linear system ``A x = b`` (LAPACK ``gesv``, LU with
- `mat_lstsq` (`matrix, signal → table`) — Least-squares solution of an over-determined system ``A x ≈ b``
- `mat_svd` (`matrix → table`) — Singular value decomposition ``A = U @ diag(s) @ Vt`` (LAPACK ``gesdd``).
- `mat_eigh` (`matrix → table`) — Eigen-decomposition of a **symmetric** matrix (LAPACK ``syevd``).
- `mat_pinv` (`matrix → matrix`) — Moore-Penrose pseudo-inverse via SVD, with the cutoff **explicit**.
- `mat_cond` (`matrix → measurement`) — Spectral (2-norm) condition number ``s_max / s_min`` — the numerical

### stats(5)
- `stat_describe` (`signal → table`) — Five-number-plus summary of a 1-D sample, as a plain dict.
- `stat_histogram` (`signal → pairs`) — Histogram of a 1-D sample with the binning **explicit**.
- `stat_covariance` (`matrix → matrix`) — Sample covariance matrix of ``(N, D)`` observations → ``(D, D)``.
- `stat_correlation` (`matrix → matrix`) — Pearson correlation matrix of ``(N, D)`` observations → ``(D, D)``.
- `stat_zscore` (`signal → signal`) — Standardise a 1-D sample: ``(x - mean) / std`` (population ``ddof=0``).

## References(アルゴリズムの一次情報・further reading)

各 op の原理はモジュール docstring にも一次文献名を明記。以下は主要技術族の外部参照。

- Marching cubes(voxel→mesh) — <https://en.wikipedia.org/wiki/Marching_cubes>
- Elliptic Fourier descriptors — <https://en.wikipedia.org/wiki/Elliptic_Fourier_descriptor>
- Thin plate spline(TPS 変形) — <https://en.wikipedia.org/wiki/Thin_plate_spline>
- Image morphing(feature-based) — <https://en.wikipedia.org/wiki/Morphing>
- Perspective-n-Point(PnP 姿勢) — <https://en.wikipedia.org/wiki/Perspective-n-Point>
- RANSAC(ロバスト推定) — <https://en.wikipedia.org/wiki/Random_sample_consensus>
- Iterative closest point(ICP/GICP) — <https://en.wikipedia.org/wiki/Iterative_closest_point>
- Superquadrics — <https://en.wikipedia.org/wiki/Superquadrics>
- Signed distance function(ESDF) — <https://en.wikipedia.org/wiki/Signed_distance_function>
- Photometric stereo — <https://en.wikipedia.org/wiki/Photometric_stereo>
- Phase unwrapping(structured light) — <https://en.wikipedia.org/wiki/Phase_unwrapping>
- Medial axis / skeleton — <https://en.wikipedia.org/wiki/Medial_axis>
- Geodesic(距離) — <https://en.wikipedia.org/wiki/Geodesic>
- Digital elevation model(DEM) — <https://en.wikipedia.org/wiki/Digital_elevation_model>
- Spline interpolation — <https://en.wikipedia.org/wiki/Spline_interpolation>
- Delaunay triangulation — <https://en.wikipedia.org/wiki/Delaunay_triangulation>
- Fourier transform — <https://en.wikipedia.org/wiki/Fourier_transform>
- Image moment(invariants) — <https://en.wikipedia.org/wiki/Image_moment>

