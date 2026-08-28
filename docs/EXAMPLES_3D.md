# Fullseye 3-D ビジョン — 事例ギャラリー(EXAMPLES_3D)

Fullseye の 3-D オペレータ群(`ops3d` = 265 の型付き op)を、**実問題を解く実行可能な事例**（全 90 件）で示します。
各事例は自己完結・自己検証のスクリプト(`examples_3d/<id>.py`)で、データを読み・op を呼び・**ground truth を print して assert** します。
一覧は `examples3d.py` レジストリが正本で、`examples3d.validate()` が全件を実行して**動くものだけ**を掲示します。

> このファイルは `tools/gen_examples3d_doc.py` がレジストリから自動生成します(手編集しないこと)。

```python
import examples3d
examples3d.names()                 # 全事例 id
print(examples3d.code('cad_to_scan'))  # 実行可能ソース
examples3d.validate()              # 全件実行(動作確認)
```

直接実行も可能:

```
PYTHONPATH=<repo> PYTHONUTF8=1 py -3.11 examples_3d/<id>.py
```

## 実データ源

- **合成データ(制御GT)** — 64 事例
- **手続き生成(GTは幾何/解析)** — 14 事例
- **骨格CT(MS-Human-700 実解剖骨)** — 4 事例
- **小惑星イトカワ(Gaskell形状モデル/JAXA)** — 5 事例
- **DL実データ(オプトイン取得 / fullseye samples)** — 3 事例

実データの帰属・引用は `studio_assets/sample_3d/ATTRIBUTION.md`(骨格CT/イトカワ)および `fullseye samples list`(DL実データの各ソース URL / ライセンス)を参照。

## タスク別 事例

### 位置合わせ / SLAM

- **CADモデルをノイズ入り3Dスキャンに位置合わせ** (`cad_to_scan`, synthetic) — 初期姿勢なしで CAD 設計形状を実物スキャン点群に合わせ、置かれた向きと位置を復元する(FPFH+RANSACで粗く→ICPでセンサノイズ床まで)。
- **手法を自動選択する点群登録** (`auto_register`, synthetic) — 2点群の近さを見て、近ければ ICP・大きく離れていれば FPFH+ICP を自動選択する(手法指定不要)。
- **登録品質の評価(recall/RMSE/inlier)** (`reg_eval`, synthetic) — 登録結果が成功か失敗かを inlier率・RMSE・recall で定量化。対応ゼロでは NaN を返し捏造しない。
- **2視点からの相対カメラ姿勢(SfM初期化)** (`two_view_pose`, synthetic) — 2枚の画像の対応点から基礎/基本行列を解き、相対カメラ姿勢と3D点を復元する(単眼SfM/VOの初手)。
- **N視点バンドル調整による精緻化** (`bundle_adjust`, synthetic) — 全カメラ姿勢と3D構造を再投影誤差最小で同時最適化し、摂動から機械精度へ回復する。
- **ループ閉じ込みのポーズグラフSLAMバックエンド** (`pose_graph_slam`, synthetic) — ノイズ入りオドメトリ+ループ閉じ辺を最適化し、蓄積したドリフトを低減する。
- **小惑星の姿勢を主成分で正準化** (`itokawa_pose_canonical`, itokawa) — 不明な向きで届いた小惑星形状を、慣性主軸で形状固有の正準姿勢へ整える(カタログ化・比較用)。
- **未知姿勢で置かれた小惑星スキャンの位置合わせ** (`itokawa_self_register`, itokawa) — 未知の探査機姿勢で撮った小惑星スキャンを ICP で基準形状に戻す。不規則形状は球と違い登録できる。
- **平面主体スキャンのGICP位置合わせ** (`gicp_register`, synthetic) — 床+直交2壁のコーナーを既知変換で動かし gicp(共分散重みマハラノビス)で復元。回転<1度、平面が滑る状況で点対点ICPを約6.5倍上回る。
- **部分重なりスキャンの登録(FPFH+ICP)** (`partial_overlap_icp`, procedural) — 非対称ブロブを別方向2視点で部分スキャン(幾何重なり56%)。scan Bに55度回転+並進を掛け、register_pointclouds(FPFH+RANSAC→ICP)でAへ登録。回転誤差0.86度<4・RMSE0.150が床0.148水準。PCA主軸103度/単位行列ICP58度のnullを桁違いに下回る。

### 再構成

- **進化探索で見つけた点群デノイズ・パイプライン** (`denoise_evolution`, synthetic) — 外れ値除去・平滑化・間引きの順番を遺伝的アルゴリズムに探させ、無処理と人手の定番を上回る。
- **複数深度フレームをTSDFで融合し表面抽出** (`tsdf_fusion_demo`, synthetic) — 複数視点の深度観測を TSDF に融合し、単一観測よりノイズに頑健な表面を得る。
- **複数断層の2D輪郭を積層して3D曲面(メッシュ)に** (`contours_to_surface`, synthetic) — 各スライスの閉輪郭を塗って voxel 積層→marching cubes で曲面メッシュ化。頂点は球面に乗り体積も一致(断面一定=円柱仮定は1.5倍過大)。輪郭→領域→voxel→メッシュの表現変換。
- **等高線(標高付き輪郭)から地形の高さ場(DEM)を復元** (`contours_to_terrain`, synthetic) — 等高線点(x,y,標高)を fit_poly_surface でサーフェス当てはめし DEM 格子へ展開。線の間も内挿し全域RMSEが最近傍等高線の階段近似を桁違いに下回る(GIS/測量)。
- **多視点シルエットから visual hull を彫る** (`space_carving`, synthetic) — 既知形状を複数の既知視点で synthesize_silhouette→carve し visual_hull を得る(recall 1.0)。1視点は柱状に過大、多視点で真形状へ収束。
- **トーラス点群のalpha shape再構成で穴(genus1)を保持** (`alpha_shape_topology`, procedural) — 中実トーラス(主R1.0/管r0.35)9000点をestimate_alpha+alpha_shape_meshで再構成。z軸穴プローブ41点の内包率がalpha=0.000(穴を保持)、凸包null=1.000(穴を充填・厳密Delaunayでも1.000)。オイラー標数χ_alpha=0(トーラス)対χ_hull=2(球)でも判別的。
- **Poisson軽量表面再構成(向き付き点群→水密メッシュ)** (`poisson_surface_recon`, procedural) — でこぼこ閉曲面(外向き法線を勾配で厳密算出)の向き付き点群6000点をrecon3d.poisson_liteで水密メッシュ(V11788/F23572)へ。真曲面との正規化chamfer0.01006が外接球null(0.081=8倍)・乱数法線null(0.041=4倍)より桁違いに小さい。

### モデリング

- **SDFのCSG合成(和/差)でソリッドを作りメッシュ化** (`sdf_csg`, synthetic) — 符号付き距離場の集合演算(球∪箱−小球)で陰関数ソリッドを作り、等値面をメッシュへ。
- **CTボリュームから骨をセグメンテーションし、接触骨を分離して計数・体積計測** (`ct_bone_segmentation`, skeleton_ct) — 骨を閾値化し、関節で繋がる指骨を収縮で分離してから連結成分で数え、体積を測る(閾値内外の密度コントラストで検証)。
- **CTボリュームから骨表面メッシュを抽出(marching cubes)** (`ct_surface_extraction`, skeleton_ct) — CTボリュームに marching cubes をかけ、骨表面を三角メッシュ化する(3Dプリント/FEA向け)。
- **3Dモルフォロジ(opening/closing/gradient/top-hat)で体積を整える** (`morphology_3d`, synthetic) — closingで空洞8→0(本体は不変)、openingでトゲ3→0、gradientは境界殻のみ、top-hatはトゲだけ抽出。素のdilate/erodeが本体まで膨張/収縮する差で判別。
- **手続き的に手全体の骨格を組む(27骨のカプセルSDF→メッシュ)** (`procedural_hand`, procedural) — 手根骨8+中手骨5+指骨14をカプセルSDFで解剖学配置しmarching cubesでメッシュ化。指先バンドの連結成分=四指(>=4)・細長さ4.66で「手」と判別。同体積の球null(指1本)を上回る。教材/デモ/合成データの自前生成。

### 特徴

- **主曲率・形状指数による把持アフォーダンス** (`curvature_grasp`, synthetic) — 点群の主曲率と形状指数から、球・円柱・鞍点を識別する(把持面の当たり判定)。
- **反射・回転対称性の検出** (`symmetry`, synthetic) — 点群の反射面と回転対称の位数を chamfer 採点で検出する。
- **大域記述子(D2/A3)による形状検索** (`shape_retrieval`, synthetic) — 距離分布 D2・角分布 A3 の大域記述子で、回転しても同形状は近く・異形状は遠く照合する。
- **小惑星表面の曲率解析(尾根・クレーターの検出)** (`itokawa_curvature`, itokawa) — 表面の主曲率・曲率度・形状指数を求め、平坦部と尾根/窪みを仕分ける(値が実在表面の幾何であることを近傍相関で確認)。
- **chamfer距離による形状照合** (`itokawa_shape_match`, itokawa) — chamfer 距離で「同一の天体か別物か」を数値判定する(自身の回転コピーは近く・同大の球は遠い)。
- **対称性検出(正直な結果:小惑星は非対称)** (`itokawa_symmetry_honest`, itokawa) — 反射対称スコアを小惑星と対称な楕円体で比較。ラブルパイル小惑星は非対称=検出器が正しく低スコアを返す。
- **点群に大域整合した外向き法線を付与(PCA推定→MST向き伝播)** (`oriented_normals`, synthetic) — 符号未定のPCA法線を Hoppe MST で外向きに揃える。球面サンプルで生法線の外向き一致0.50(コイン投げ)を向き付け1.00へ改善、接平面精度1.00。退化入力は捏造せず拒否。
- **球面調和記述子による回転不変な3D形状検索** (`shape_descriptor`, synthetic) — 向き未知の形状(球/箱/円柱の回転コピー)を SH 帯域エネルギー記述子で照合。検索3/3正解・分離マージン>0で、回転で全マスが入れ替わる素ボクセル占有の1/3を上回る。
- **3Dボリュームのエッジ検出(canny3d: NMS+ヒステリシス)** (`edges_3d`, synthetic) — なだらかな内部を持つ中実ボールの外周だけを1ボクセルに細線化。オンシェル率1.000・内部誤検出0で、生勾配の固定しきい値null(0.464・誤検出4012)を+0.536上回る。
- **実メッシュ曲率が詳細形状を判別(Stanford Dragon)** (`dl_mesh_curvature`, download) — DL実データStanford Dragon(87万面)をread_mesh→vertex_curvature(cotangent Laplace-Beltrami)。正規化曲率はmedian9.2・MAD6.2・|Hn|>2が88%と広く分布し、同スケールの滑球null(median1.00・0%)をMAD比1.4e7倍で判別。未取得時はSKIPしexit0。
- **FPFH記述子で部分ビュー間の点対応を張る** (`fpfh_correspondence`, procedural) — 同一物体の2部分ビュー(58度回転+並進・重なり1514点)で法線推定→FPFH記述子(33次元)を計算し記述子最近傍で対応。幾何正答率0.633がランダム対応0.0034・記述子シャッフル0.0020(チャンス率)を約185倍上回る。register全体でなく記述子マッチ品質を直接測る。

### 形状解析

- **中軸骨格と位相署名で形状を区別** (`medial_topology`, synthetic) — 中実円柱の芯を skeletonize_vol/medial_axis_points で抽出(既知中心軸上)、topology_signature+medial_match でトーラス(genus1)を球/円柱と区別。ランダム署名の零点を上回る。
- **曲面上の測地距離と最遠点サンプリング** (`geodesic_distance`, synthetic) — 球面点群で kNN グラフ上の geodesic_distances が大円距離と一致(誤差1.7%)、farthest_point_sampling で均等な代表点。直線ユークリッド距離は曲面上で系統的に過小。
- **3D空間曲線の微分幾何(曲率κ・捩率τ・弧長・Frenet標構)** (`space_curve`, synthetic) — 順序付き点列からκ/τ/弧長とFrenet標構を求め、ヘリックスの解析解と相対誤差<0.01%で一致。直線(κ=0)・平面円(τ=0)の零点を判別的に上回り、変速でもGram-Schmidt射影の正しさを確認。
- **点群の鏡映対称面の復元** (`reflection_symmetry`, synthetic) — 既知平面で鏡映対称な点群から初期推定なしにdetect_reflection_symmetryが対称面を復元: 法線誤差0.0度・鏡映残差1.5e-11。非対称null(残差1.14)は約7.8e10倍大きく、でたらめ平面(最良1.27)も桁違いで判別的。
- **トーラス結び目の弧長・捩率計測(非平面曲線)** (`torus_knot_curve`, procedural) — (2,3)トーラス結び目を密ポリラインで生成しcurve3dのarc_length/curvature_torsionを検証。弧長は台形積分と相対7.6e-7一致・中央|τ|0.283は同長の平面円(捩率6e-10)の5.1e8倍で非平面を判別。円のκ=1/rも誤差7e-13で正確。
- **恐竜骨格の左右対称面(矢状面)の復元** (`dl_mesh_symmetry`, download) — スミソニアン三角竜骨格(CC0,10万頂点→4090点stride)をdetect_reflection_symmetryに渡し矢状面を残差2.48で復元(最薄主軸=左右方向に一致)。他2主平面4.28/4.30と区別、片側20%破壊で15.87(6.4倍)へ悪化=左右対称を判別的に検出。未取得時はSKIPしexit0。
- **回転対称位数の復元(6枚歯スパーギア)** (`rotational_symmetry_fold`, procedural) — 歯数6の平歯車リム2160点を生成。detect_rotational_symmetryで対称軸z(|z|=1.000)、約数構造(rotational_symmetry_score)から位数N=6を復元。約数{2,3,6}残差~1e-11・非約数{4,5,7,9,12}>0.5、位数6残差4.3e-11が無対称ランダム1.52の3.5e10倍。
- **ガウス曲率の符号で表面をドーム/鞍点に分類** (`curvature_shape_index`, procedural) — トーラス(R1.0/r0.35)密点群にgaussian_curvatureを当て、外周(楕円K>0)/内周(双曲K<0)を符号で分離精度1.000で分類(解析真値K=cos v/(r(R+r cos v))と一致)。このR,rは外周も内周もH>0なので平均曲率符号null=0.500(分離不能)を判別的に上回る。把持点選び/欠陥判定。

### 形状当てはめ

- **点群から角丸ブロックをスーパー楕円体で当てはめ** (`superquadric_fit`, synthetic) — 既知スーパー楕円体からの雑音点群を fit_superquadric で復元(半径5%以内・内外分類>95%)。球1個を当てた残差を大きく下回る(把持点判定向け)。
- **3D Houghで平面・球のプリミティブを検出** (`detect_primitives_3d`, synthetic) — 投票ベースの hough_plane_3d/hough_sphere_3d で平面(法線誤差0.55度)・球(中心誤差0voxel)を復元。素朴PCA(80度)や重心(22voxel)の零点を明確に上回る。
- **プリミティブ当てはめ拡張(円錐/トーラス/楕円体)** (`fit_primitives_ext`, synthetic) — 点群に円錐(半角誤差0.008°)・トーラス(R,r誤差~3e-4)・楕円体(半径相対誤差<0.2%)を当てはめ。誤モデル(球/平面)の残差をそれぞれ38x/64x/50x下回る。漏斗/配管/細胞・慣性の寸法検査。

### 形状記述子

- **3Dモーメント不変量(剛体+一様スケールに不変)** (`moment_invariants`, synthetic) — 点群に既知の平行移動・回転・一様スケールを掛けても moment_invariants はほぼ不変で、別形状とは明確に区別。生モーメントは同変換で大きく変動。
- **球面調和記述子による回転不変な3D形状検索** (`sh_descriptor_retrieval`, procedural) — 球/立方体/トーラス/円柱/円錐の5クラスをボクセル化しsh_descriptor化。一様ランダム3D回転したクエリをmatch_sh_descriptorで検索→30/30=100%正解・分離マージン0.312。非回転不変null(軸周辺分布)は回転で100%→37%に崩れSHが+63pt上回る。

### 陰影からの形状復元

- **複数光源の陰影から法線・高さを復元(フォトメトリックステレオ)** (`photometric_stereo`, synthetic) — 既知光源方向の陰影群から photometric_stereo で法線(誤差0.88度)、integrate_normals で高さ(相関1.0)。単一輝度=高さの素朴推定を大きく上回る。

### 計測 / メトロロジー

- **平面度メトロロジー(基準面からの偏差)** (`plane_flatness`, synthetic) — 点群に平面を当て、基準面からの偏差=平面度を測る。既知の膨らみ高さと一致することで検証。
- **真球度/丸さ検査** (`roundness`, synthetic) — 点群に球を当て、真球からの偏差=真球度を測る。完全な球ほど偏差が小さいことを確認。
- **30%外れ値下での頑健プリミティブ適合** (`ransac_prim`, synthetic) — 平面/球/円柱を RANSAC で当て、外れ値30%が混じってもパラメータを正しく復元する。
- **最大内接ボックス(inner_rectangle1 の 3-D 版)** (`inner_box_inspection`, synthetic) — 空洞のある部品(二値ボクセル)に内接する最大の軸平行ボックス=「保証できる最大の中実ブロック」を厳密に求める(総当たりと完全一致)。深さ区間の論理積×2-D最大内接長方形。空洞をまたぐ前景bbox(非中実)を判別的に下回る。regionprops3d.inner_box3。
- **最小体積の有向境界箱(OBB=smallest_rectangle2 の 3-D 版)** (`oriented_bounding_box`, synthetic) — 傾いた直方体の実寸を最小体積 OBB で復元(半径 (5,2,1)・中心・体積 80 を機械精度)。軸平行 AABB は回転で ~1.8 倍に膨張し、PCA 箱(pcseg.obb)は非対称形状で最小にならない — min-volume OBB(凸包面×回転キャリパー, measure3d.smallest_box3)が両者を判別的に下回る。把持/梱包の寸法検査。
- **点群のバウンディング(凸包/OBB/AABB/最小包含球)** (`hull_bounds`, synthetic) — 生点群から凸包・向き付き箱(OBB)・軸整列箱(AABB)・最小包含球を起こす。新規 min_enclosing_sphere は素朴球 r=9.95→5.63(比0.57・全点内包)、OBB体積は回転箱で AABB の0.20倍。把持/衝突/寸法検査の基本メトロロジー。
- **平歯車の歯数をSDFジオメトリから逆計測** (`gear_metrology`, procedural) — sdf_opsのCSGで平歯車を手続き生成し、歯先帯r=0.44の占有を角度サンプルしてラン計数で歯数N=12→12/20→20を厳密復元(0.2度ジッタでも不変)。歯なし円板null=0本・誤半径 内1/外0本で判別的。
- **円筒軸メトロロジー(30%外れ値ロバスト)** (`cylinder_axis_metrology`, procedural) — 汚れた産業スキャン(30%グロス外れ値・2000点)からパイプの軸方向と半径を計測。fit_cylinder_ransacで半径誤差1.27%・軸誤差0.78°・面残差0.00165m。非ロバスト全点フィット(半径誤差101%)と誤プリミティブ平面RANSAC(残差0.058m)を5倍超マージンで判別的に上回る。

### 深度 / ステレオ / トモグラフィ

- **2視点プレーンスイープ・ステレオ深度** (`plane_sweep_depth`, synthetic) — 既知カメラの2画像から、深度平面を掃引して photo-consistency 最小の深度を画素ごとに選ぶ。
- **エッジ保存の深度デノイズ+穴埋め** (`depth_denoise`, synthetic) — 段差を跨がずにノイズを平滑化し、浅い穴を調和補間で埋める(深い穴はNaNのまま残す)。
- **骨格CTからX線ラジオグラフ(DRR)を合成** (`ct_hand_radiograph`, skeleton_ct) — 手骨のCT密度ボリュームを厚み方向に積算し、2次元の手のX線像(DRR)を合成する。
- **低線量スパースビューCT再構成(radon→SART)** (`ct_sparse_view_recon`, skeleton_ct) — 指の断面をX線投影し、SART(反復)とFBPで再構成する。低線量ゆえの控えめな品質を正直に評価。
- **ステレオ視差からの多深度パッチ奥行き復元** (`stereo_depth_scene`, synthetic) — 校正済みステレオ対(f*B=96)に近8/中16/遠32mの3テクスチャパッチを視差12/6/3pxで合成し、disparity_map→depth_from_disparityで復元。パッチ内部の相対誤差0.00%・near>mid>far順序も正。最良定数null63.9%・視差ゼロnull(∞)を判別的に上回る。

### セグメンテーション

- **ビンピッキング: 台平面除去→物体クラスタリング** (`object_segmentation`, synthetic) — 地面平面を plane_segmentation で剥がし、残りを euclidean_cluster で3物体に分離。クラスタ数・重心が真値一致、全点1クラスタ扱いの零点を上回る。
- **3Dボリュームの連結成分ラベリングと塊ごとの計測(個数/体積/重心)** (`region_props_3d`, synthetic) — 複数ブロブを連結成分で分離し、体積誤差0voxel・重心誤差0.0で計測。largest_componentで最大塊、filter_by_volumeで小塊除去。全前景を1領域とする零点(重心ズレ13.5voxel)を上回る。
- **接触物体の分離(距離変換ベース3D watershed)** (`watershed3d`, synthetic) — 接触して1連結成分に融合した2球をwatershedで2個に分離。重心を真値へ最大0.31voxel・体積誤差<5%。連結成分(null)はcount=1に融合し重心が10voxelずれる — 個数でも重心でも上回る。CT/粉体/細胞の計数。
- **分子の接触原子カウント(距離変換+マーカ分水嶺)** (`molecule_atom_count`, procedural) — シクロヘキサンC6椅子型を6原子球の和集合(41万voxel・1連結成分)にボクセル化。距離変換+マーカ分水嶺で接触原子を6個に分離・重心を真値へ最大0.52voxel。素朴な連結成分null=1個に融合(43voxelずれ)を個数6vs1で上回る。
- **屋外LiDARシーンの地面除去→物体分割** (`lidar_scene_segmentation`, procedural) — 傾斜地面(~5.4度)上の4物体(球/箱/円柱/円錐)のLiDAR点群5316点を、fit_plane_ransac+height_above_planeで地面除去→euclidean_clustersで分割。検出4==K=4・重心を真物体へ全単射(最大0.128m)。地面除去なしnullは全物体癒着で1クラスタ。

### 間引き(decimation)

- **点群の間引き(voxel grid / farthest-point)で密度を均す** (`pointcloud_downsampling`, synthetic) — 6万点の密度ムラ点群をvoxel格子(重心集約, カバレッジ0.134<=理論0.260)とFPS(0.097)で間引き。同数のランダム間引き(0.310, 穴あり)を判別的に上回る。LiDAR/深度カメラの前処理でICP・特徴計算を軽くする。
- **ボリューム(3D CT)の間引き — max/mean プールの使い分け** (`volume_downsampling`, synthetic) — 260^3=1758万ボクセル(Frangi上限超過で拒否)を4倍間引きして上限内へ。既知8欠陥をmaxプールは8/8保持・meanプールは0/8にwashout。微小欠陥検出にはmaxが正しいことを計数で判別的に示す。工業CT/ラミノグラフィの前処理。

### メッシュ処理

- **三角形メッシュの平滑化(Laplacian/Taubin・非収縮)** (`mesh_smooth`, synthetic) — ノイズメッシュを接続グラフ上で平滑化。RMS 0.627→Laplacian 0.306/Taubin 0.215。Taubin は平均半径ズレ0.025で Laplacian 0.298 の約1/12=非収縮。marching cubes/スキャン後処理向け。
- **メッシュ簡略化(QEM edge-collapse)で目標面数へ軽量化** (`mesh_decimate`, synthetic) — 球1280面→384面(目標厳密)、頂点は球面上・watertight維持・対称Hausdorff 3.3%R。同数までランダム間引くnullは穴792本・Hausdorff 21.3%Rで6.4倍劣る。スキャン/CADの軽量化。
- **メッシュの法線・表面積・平均曲率(接続情報から)** (`mesh_props`, synthetic) — 面/頂点法線・表面積・cotangent平均曲率を面の巻き順とラプラシアンから測る。球(R2.5)で面積誤差0.12%・曲率0.4000(1/R)・法線外向き率1.00。面積null(49.7%誤差)・平面曲率nullを判別的に上回る。
- **DL実データメッシュの多段LOD間引き(QEM)** (`mesh_lod_download`, download) — DL版Stanford Bunny(6.9万面)をQEMで50/25/10%へ間引き。面数34725→17361→6944と単調減少・Hausdorff/diag<=0.020・Chamfer/diag<=0.0024(1/10面でも平均誤差一定)。同面数ランダムドロップ(0.0034)に平均誤差で勝ち、片側クロップnullはHausdorff0.59=30倍で帯外。未取得時はSKIPしexit0。

### 姿勢推定

- **外れ値ありの3D-2D対応からカメラ6自由度姿勢を推定(PnP+RANSAC)** (`pose_estimation`, synthetic) — 既知寸法の箱の3D-2D対応(30%外れ値・0.5px雑音)から pnp_ransac で姿勢復元。回転<2度・並進<2%で、恒等姿勢や素のDLTを明確に上回る。
- **誤対応4割下のカメラ姿勢推定(PnP+RANSAC)** (`pnp_pose_outliers`, synthetic) — 200点の3D-2D対応の40%が誤対応でもpnp_ransacが姿勢復元: 回転誤差0.11度・inlier再投影0.66px・inlier適合率100%。同じ汚染データの素dlt_pose(RANSACなし)は33.7度に破綻し319倍判別的に上回る。

### 構造化光

- **位相シフト縞投影で高さを復元** (`structured_light`, synthetic) — 縞合成→wrapped_phase→unwrap_phase_2d→decode で高さ(RMSE 0.63%)。位相アンラップ無しは2π跳びで88%誤る。
- **Gray code 構造化光の絶対デコード** (`graycode_structured_light`, synthetic) — 物体で湾曲した投影機コラム番号(0..127)をGray codeビット面7枚からgraycode_decodeで絶対復号。全12288画素で整数厳密一致(100%)。極性反転(0%)/面順取り違え(13%)/最頻値決め打ち(2%)のnullを判別的に上回る。撮影ノイズ42%まで厳密。

### 光学(光線)

- **スネル屈折とフレネル反射(解析GT検証)** (`snell_refraction`, synthetic) — match3dの光線光学opを閉じた式で検証。Snell残差1e-16・屈折角一致3.9e-14度、Fresnel垂直入射0.040=解析値・grazing→1・臨界角超で全反射(NaN/None/1.0)。無屈折null(屈折角が平均20.5度ずれ)を判別的に棄却。

### 地図 / ナビゲーション

- **占有格子+ESDFで連続クリアランスを問い合わせ** (`occupancy_esdf`, synthetic) — 部屋点群から occupancy_grid→esdf を作り、自由空間点で最近接障害物までの連続距離を query_distance。占有0/1のみの零点を約39倍上回る(衝突回避マージン判定)。
- **地形の走行可能性マッピング(段差検出)** (`terrain_traversability`, procedural) — 平坦+緩スロープ+急段差(0.5m壁)の点群→標高マップ→走行可能性マップ。平坦/緩は走行可能率1.00・段差は非走行可能率1.00。段差検出 実op1.00 vs 全可null/巨大max_step null 0.00、GT精度1.00 vs 0.83。

### レンジセンシング

- **360度点群⇄距離画像の往復(球面投影)** (`lidar_projection`, synthetic) — project_spherical→unproject_spherical の往復で形状を保存(誤差<voxel)。奥行きを潰す平面正射影より55倍良い。
- **深度画像から法線・遮蔽エッジを読む** (`range_image`, synthetic) — organized 深度から法線(平面で0度誤差)と手前/奥の段差エッジを検出。一次勾配しきい値は平面の傾きを誤検出、二次差分の occlusion_edges は誤検出0。

### 運動 / シーンフロー

- **動的シーンの剛体運動セグメンテーション** (`motion_seg`, synthetic) — 2時刻の点群から、別々に動く剛体ごとに分割する。無相関ノイズでは剛体を捏造しない。
- **剛体シーンフロー(既知R,tと密フィールドの復元)** (`scene_flow_rigid`, synthetic) — 点群を既知剛体変換で動かし rigid_flow で復元(回転<1度・並進<1voxel)。smooth_flow が生NN流のEPEを約半分に、residual_flow は剛体部でノイズ床。

### 非剛体位置合わせ

- **TPSベースの非剛体位置合わせ** (`nonrigid_deform`, synthetic) — 既知TPS曲げ変形をかけた標的へ register_nonrigid で位置合わせし残差をノイズ床へ。剛体ICPは曲げを吸収できず残差が大きい(制御点で tps_warp が厳密に写ることも確認)。

### データ拡張

- **点群データ拡張(回転/スケール/ドロップアウト/ジッタ)** (`augment_pointcloud`, synthetic) — 学習用の点群拡張4種を指定パラメータどおり適用(回転=距離不変・向き変化、scale倍率、dropout点数、jitter std)。恒等nullを判別的に上回り、連鎖でも複合性質を保つ。

### レンダリング品質

- **レンダリング品質: アンビエントオクルージョン(接触影・凹部の環境影)** (`render_ao`, synthetic) — 物体空間AOで半球到達性を[0,1]化。平面に載る球で頂上AO1.00/接触部0.06(高さとSpearman1.00)、溝は深さに単調低下。一様AO=1(null)は凹凸を判別不能。拡散のみのLambertianに乗算し立体感を出す。
- **レンダリング品質: キャスト/ソフトシャドウ(接地影)** (`render_shadow`, synthetic) — shadow mappingで接地影。球を床に載せ解析GTだ円とIoU 0.978。影なし(従来陰影)はIoU 0.00(接地影を全く当てられない)を判別的に上回る。半影は光源角サイズで単調に拡大。
- **レンダリング品質: matcap/Phong鏡面シェーディング** (`render_shade`, synthetic) — 拡散のみに鏡面を追加。Phongハイライトのピークが反射方向N=norm(L+V)と0.63px一致。Lambertianの最輝点は反射方向を54px外す(nullを約85倍上回る)。matcapはlit-sphere転写で素材感を持ち込む。
- **レンダリング品質: スーパーサンプリング(SSAA)でジャギー除去** (`render_ssaa`, synthetic) — ss倍レンダ→面積平均縮小。傾き22°エッジでエイリアスエネルギー0.275→0.164(0.59倍)・中間輝度画素0%→0.95%、ss=1..6で単調減少。z-bufferの階段状シルエットを滑らかに。
- **レンダリング品質: トーンマップ(HDR→LDR)で白飛び救済** (`render_tonemap`, synthetic) — 鏡面HDR(max5.41)をReinhard/ACESで[0,1]へ。全域Spearman1.00で単調、素朴クリップがハイライト域を1段に潰す(分散0)のに対し順位相関1.0・194段の階調を保持。
- **レンダリング品質: hero レンダラ render_beauty(全層合成の映える静止3D)** (`render_beauty`, synthetic) — ラスタライズ/Phong鏡面/AO/接地影/SSAA/トーンマップを1本に合成。sphere-on-groundで各層を実測: AOは接触凹部を0.07→0.02と選択的に暗化(露出頂部0.01は不変)、鏡面は小面積ハイライト(frac0.018)、接地影はwith-mesh993px vs null0px、reinhardは単調(clip34段潰しを回避)、SSAAはedge0.040→0.026。sdf_ops生成メッシュでhero画像を出力。

