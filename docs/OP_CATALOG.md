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

### 2-D 画像/信号/幾何(5 例)

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

### 3-D 点群/体積/曲面(52 例)

**registration**
- **CADモデルをノイズ入り3Dスキャンに位置合わせ** — 初期姿勢なしで CAD 設計形状を実物スキャン点群に合わせ、置かれた向きと位置を復元する(FPFH+RANSACで粗く→ICPでセンサノイズ床まで)。 `py -3.11 examples_3d/cad_to_scan.py`
- **手法を自動選択する点群登録** — 2点群の近さを見て、近ければ ICP・大きく離れていれば FPFH+ICP を自動選択する(手法指定不要)。 `py -3.11 examples_3d/auto_register.py`
- **登録品質の評価(recall/RMSE/inlier)** — 登録結果が成功か失敗かを inlier率・RMSE・recall で定量化。対応ゼロでは NaN を返し捏造しない。 `py -3.11 examples_3d/reg_eval.py`
- **2視点からの相対カメラ姿勢(SfM初期化)** — 2枚の画像の対応点から基礎/基本行列を解き、相対カメラ姿勢と3D点を復元する(単眼SfM/VOの初手)。 `py -3.11 examples_3d/two_view_pose.py`
- **N視点バンドル調整による精緻化** — 全カメラ姿勢と3D構造を再投影誤差最小で同時最適化し、摂動から機械精度へ回復する。 `py -3.11 examples_3d/bundle_adjust.py`
- **ループ閉じ込みのポーズグラフSLAMバックエンド** — ノイズ入りオドメトリ+ループ閉じ辺を最適化し、蓄積したドリフトを低減する。 `py -3.11 examples_3d/pose_graph_slam.py`
- **小惑星の姿勢を主成分で正準化** — 不明な向きで届いた小惑星形状を、慣性主軸で形状固有の正準姿勢へ整える(カタログ化・比較用)。 `py -3.11 examples_3d/itokawa_pose_canonical.py`
- **未知姿勢で置かれた小惑星スキャンの位置合わせ** — 未知の探査機姿勢で撮った小惑星スキャンを ICP で基準形状に戻す。不規則形状は球と違い登録できる。 `py -3.11 examples_3d/itokawa_self_register.py`
- **平面主体スキャンのGICP位置合わせ** — 床+直交2壁のコーナーを既知変換で動かし gicp(共分散重みマハラノビス)で復元。回転<1度、平面が滑る状況で点対点ICPを約6.5倍上回る。 `py -3.11 examples_3d/gicp_register.py`

**metrology**
- **平面度メトロロジー(基準面からの偏差)** — 点群に平面を当て、基準面からの偏差=平面度を測る。既知の膨らみ高さと一致することで検証。 `py -3.11 examples_3d/plane_flatness.py`
- **真球度/丸さ検査** — 点群に球を当て、真球からの偏差=真球度を測る。完全な球ほど偏差が小さいことを確認。 `py -3.11 examples_3d/roundness.py`
- **30%外れ値下での頑健プリミティブ適合** — 平面/球/円柱を RANSAC で当て、外れ値30%が混じってもパラメータを正しく復元する。 `py -3.11 examples_3d/ransac_prim.py`

**depth**
- **2視点プレーンスイープ・ステレオ深度** — 既知カメラの2画像から、深度平面を掃引して photo-consistency 最小の深度を画素ごとに選ぶ。 `py -3.11 examples_3d/plane_sweep_depth.py`
- **エッジ保存の深度デノイズ+穴埋め** — 段差を跨がずにノイズを平滑化し、浅い穴を調和補間で埋める(深い穴はNaNのまま残す)。 `py -3.11 examples_3d/depth_denoise.py`
- **骨格CTからX線ラジオグラフ(DRR)を合成** — 手骨のCT密度ボリュームを厚み方向に積算し、2次元の手のX線像(DRR)を合成する。 `py -3.11 examples_3d/ct_hand_radiograph.py`
- **低線量スパースビューCT再構成(radon→SART)** — 指の断面をX線投影し、SART(反復)とFBPで再構成する。低線量ゆえの控えめな品質を正直に評価。 `py -3.11 examples_3d/ct_sparse_view_recon.py`

**reconstruction**
- **進化探索で見つけた点群デノイズ・パイプライン** — 外れ値除去・平滑化・間引きの順番を遺伝的アルゴリズムに探させ、無処理と人手の定番を上回る。 `py -3.11 examples_3d/denoise_evolution.py`
- **複数深度フレームをTSDFで融合し表面抽出** — 複数視点の深度観測を TSDF に融合し、単一観測よりノイズに頑健な表面を得る。 `py -3.11 examples_3d/tsdf_fusion_demo.py`
- **複数断層の2D輪郭を積層して3D曲面(メッシュ)に** — 各スライスの閉輪郭を塗って voxel 積層→marching cubes で曲面メッシュ化。頂点は球面に乗り体積も一致(断面一定=円柱仮定は1.5倍過大)。輪郭→領域→voxel→メッシュの表現変換。 `py -3.11 examples_3d/contours_to_surface.py`
- **等高線(標高付き輪郭)から地形の高さ場(DEM)を復元** — 等高線点(x,y,標高)を fit_poly_surface でサーフェス当てはめし DEM 格子へ展開。線の間も内挿し全域RMSEが最近傍等高線の階段近似を桁違いに下回る(GIS/測量)。 `py -3.11 examples_3d/contours_to_terrain.py`
- **多視点シルエットから visual hull を彫る** — 既知形状を複数の既知視点で synthesize_silhouette→carve し visual_hull を得る(recall 1.0)。1視点は柱状に過大、多視点で真形状へ収束。 `py -3.11 examples_3d/space_carving.py`

**modeling**
- **SDFのCSG合成(和/差)でソリッドを作りメッシュ化** — 符号付き距離場の集合演算(球∪箱−小球)で陰関数ソリッドを作り、等値面をメッシュへ。 `py -3.11 examples_3d/sdf_csg.py`
- **CTボリュームから骨をセグメンテーションし、接触骨を分離して計数・体積計測** — 骨を閾値化し、関節で繋がる指骨を収縮で分離してから連結成分で数え、体積を測る(閾値内外の密度コントラストで検証)。 `py -3.11 examples_3d/ct_bone_segmentation.py`
- **CTボリュームから骨表面メッシュを抽出(marching cubes)** — CTボリュームに marching cubes をかけ、骨表面を三角メッシュ化する(3Dプリント/FEA向け)。 `py -3.11 examples_3d/ct_surface_extraction.py`
- **3Dモルフォロジ(opening/closing/gradient/top-hat)で体積を整える** — closingで空洞8→0(本体は不変)、openingでトゲ3→0、gradientは境界殻のみ、top-hatはトゲだけ抽出。素のdilate/erodeが本体まで膨張/収縮する差で判別。 `py -3.11 examples_3d/morphology_3d.py`

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

**motion**
- **動的シーンの剛体運動セグメンテーション** — 2時刻の点群から、別々に動く剛体ごとに分割する。無相関ノイズでは剛体を捏造しない。 `py -3.11 examples_3d/motion_seg.py`
- **剛体シーンフロー(既知R,tと密フィールドの復元)** — 点群を既知剛体変換で動かし rigid_flow で復元(回転<1度・並進<1voxel)。smooth_flow が生NN流のEPEを約半分に、residual_flow は剛体部でノイズ床。 `py -3.11 examples_3d/scene_flow_rigid.py`

**pose_estimation**
- **外れ値ありの3D-2D対応からカメラ6自由度姿勢を推定(PnP+RANSAC)** — 既知寸法の箱の3D-2D対応(30%外れ値・0.5px雑音)から pnp_ransac で姿勢復元。回転<2度・並進<2%で、恒等姿勢や素のDLTを明確に上回る。 `py -3.11 examples_3d/pose_estimation.py`

**segmentation**
- **ビンピッキング: 台平面除去→物体クラスタリング** — 地面平面を plane_segmentation で剥がし、残りを euclidean_cluster で3物体に分離。クラスタ数・重心が真値一致、全点1クラスタ扱いの零点を上回る。 `py -3.11 examples_3d/object_segmentation.py`
- **3Dボリュームの連結成分ラベリングと塊ごとの計測(個数/体積/重心)** — 複数ブロブを連結成分で分離し、体積誤差0voxel・重心誤差0.0で計測。largest_componentで最大塊、filter_by_volumeで小塊除去。全前景を1領域とする零点(重心ズレ13.5voxel)を上回る。 `py -3.11 examples_3d/region_props_3d.py`

**mapping**
- **占有格子+ESDFで連続クリアランスを問い合わせ** — 部屋点群から occupancy_grid→esdf を作り、自由空間点で最近接障害物までの連続距離を query_distance。占有0/1のみの零点を約39倍上回る(衝突回避マージン判定)。 `py -3.11 examples_3d/occupancy_esdf.py`

**shape_fitting**
- **点群から角丸ブロックをスーパー楕円体で当てはめ** — 既知スーパー楕円体からの雑音点群を fit_superquadric で復元(半径5%以内・内外分類>95%)。球1個を当てた残差を大きく下回る(把持点判定向け)。 `py -3.11 examples_3d/superquadric_fit.py`
- **3D Houghで平面・球のプリミティブを検出** — 投票ベースの hough_plane_3d/hough_sphere_3d で平面(法線誤差0.55度)・球(中心誤差0voxel)を復元。素朴PCA(80度)や重心(22voxel)の零点を明確に上回る。 `py -3.11 examples_3d/detect_primitives_3d.py`

**shape_descriptors**
- **3Dモーメント不変量(剛体+一様スケールに不変)** — 点群に既知の平行移動・回転・一様スケールを掛けても moment_invariants はほぼ不変で、別形状とは明確に区別。生モーメントは同変換で大きく変動。 `py -3.11 examples_3d/moment_invariants.py`

**shape_analysis**
- **中軸骨格と位相署名で形状を区別** — 中実円柱の芯を skeletonize_vol/medial_axis_points で抽出(既知中心軸上)、topology_signature+medial_match でトーラス(genus1)を球/円柱と区別。ランダム署名の零点を上回る。 `py -3.11 examples_3d/medial_topology.py`
- **曲面上の測地距離と最遠点サンプリング** — 球面点群で kNN グラフ上の geodesic_distances が大円距離と一致(誤差1.7%)、farthest_point_sampling で均等な代表点。直線ユークリッド距離は曲面上で系統的に過小。 `py -3.11 examples_3d/geodesic_distance.py`
- **3D空間曲線の微分幾何(曲率κ・捩率τ・弧長・Frenet標構)** — 順序付き点列からκ/τ/弧長とFrenet標構を求め、ヘリックスの解析解と相対誤差<0.01%で一致。直線(κ=0)・平面円(τ=0)の零点を判別的に上回り、変速でもGram-Schmidt射影の正しさを確認。 `py -3.11 examples_3d/space_curve.py`

**range_sensing**
- **360度点群⇄距離画像の往復(球面投影)** — project_spherical→unproject_spherical の往復で形状を保存(誤差<voxel)。奥行きを潰す平面正射影より55倍良い。 `py -3.11 examples_3d/lidar_projection.py`
- **深度画像から法線・遮蔽エッジを読む** — organized 深度から法線(平面で0度誤差)と手前/奥の段差エッジを検出。一次勾配しきい値は平面の傾きを誤検出、二次差分の occlusion_edges は誤検出0。 `py -3.11 examples_3d/range_image.py`

**shape_from_shading**
- **複数光源の陰影から法線・高さを復元(フォトメトリックステレオ)** — 既知光源方向の陰影群から photometric_stereo で法線(誤差0.88度)、integrate_normals で高さ(相関1.0)。単一輝度=高さの素朴推定を大きく上回る。 `py -3.11 examples_3d/photometric_stereo.py`

**structured_light**
- **位相シフト縞投影で高さを復元** — 縞合成→wrapped_phase→unwrap_phase_2d→decode で高さ(RMSE 0.63%)。位相アンラップ無しは2π跳びで88%誤る。 `py -3.11 examples_3d/structured_light.py`

**deformable_registration**
- **TPSベースの非剛体位置合わせ** — 既知TPS曲げ変形をかけた標的へ register_nonrigid で位置合わせし残差をノイズ床へ。剛体ICPは曲げを吸収できず残差が大きい(制御点で tps_warp が厳密に写ることも確認)。 `py -3.11 examples_3d/nonrigid_deform.py`

**augmentation**
- **点群データ拡張(回転/スケール/ドロップアウト/ジッタ)** — 学習用の点群拡張4種を指定パラメータどおり適用(回転=距離不変・向き変化、scale倍率、dropout点数、jitter std)。恒等nullを判別的に上回り、連鎖でも複合性質を保つ。 `py -3.11 examples_3d/augment_pointcloud.py`

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
_計 230 ops / 53 categories。_


### augment(6)
- `jitter` (`points → points`) — 各点に等方ガウスノイズ ``N(0, sigma)`` を付加(センサ位置ノイズの模倣)。
- `random_rotation` (`points → points`) — ランダム回転を適用し ``(rotated, R)`` を返す(視点変化の模倣)。
- `random_scale` (`points → points`) — 一様スケール ``s ~ U(lo, hi)`` を原点まわりに適用し ``(scaled, s)`` を返す。
- `random_dropout` (`points → points`) — 点の ``ratio`` 割合をランダム除去し ``(kept, kept_idx)`` を返す(欠損の模倣)。
- `elastic_deform` (`points → points`) — 滑らかな乱数変位場で弾性変形(相関距離 ``sigma``, RMS 振幅 ``alpha``)。
- `cutout` (`points → points`) — 空間的な軸平行ボックス領域を除去し ``(kept, kept_idx)`` を返す(局所欠損の模倣)。

### bundle_adjust(3)
- `bundle_adjust` (`pose, points → pose`) — 再投影誤差最小でカメラ姿勢と 3D 点を同時最適化。→ dict{cameras, points, rmse, cost}。
- `mean_reprojection_error` (`pose, points → measurement`) — 再投影 RMS 誤差(ピクセル)。
- `project` (`points → image2d`) — 3D 点 (n,3) をカメラ (rvec,t,K) で 2D (n,2) に射影(透視除算)。

### curvature(5)
- `principal_curvatures` (`points → curvature`) — 各点の主曲率 (k1>=k2)。→ (k1 (N,), k2 (N,))。
- `mean_curvature` (`points → measurement`) — 平均曲率 H=(k1+k2)/2。→ (N,)。向きに依存する量。
- `gaussian_curvature` (`points → measurement`) — ガウス曲率 K=k1·k2(法線の反転に不変)。→ (N,)。
- `shape_index` (`points → descriptor`) — Koenderink の shape index s∈[-1,1](凸球+1・円柱+0.5・鞍点0・凹球-1)。→ (N,)。
- `estimate_normals` (`points → normals`) — 外向き(近傍重心から離れる)に統一した点群法線。→ (N,3)。

### curve(5)
- `curvature_torsion` (`points → measurement`) — 各点の曲率 κ と捩率 τ(再パラメータ化不変な閉形式)。→ (kappa (N,), tau (N,))。
- `frenet_frame` (`points → frame`) — Frenet 標構(接線 T, 主法線 N, 陪法線 B)を各点で。→ (T, N, B) 各 (Npts,3) 単位ベクトル。
- `arc_length` (`points → measurement`) — 曲線の累積弧長と全長。→ (cumulative (N,), total float)。
- `resample_uniform` (`points → points`) — 弧長で等間隔に n 点へ再サンプル(線形補間)。→ (n,3)。
- `fit_spline_curve` (`points → points`) — 順序付き 3D 点列を B スプラインで平滑し再サンプル。→ (M,3)。ノイズのある軌跡/エッジの平滑化。

### curvilinear(3)
- `polar_unwrap` (`image2d → image2d`) — 画像の円環/円板を (θ×r) 矩形へアンラップ(工業: ラベル/リング/回転体の検査)。
- `cylinder_unwrap` (`voxel → image2d`) — voxel の円筒面を (height×θ×r) へアンラップ(円筒部品/配管の内外面検査)。軸=z(D 軸)。
- `fit_zernike` (`image2d → descriptor`) — 円板画像 → Zernike 係数(光学/波面計測の**極座標曲面近似**)。返り値 {(n,m): coef}。

### deform(4)
- `tps_fit` (`points, points → deformation`) — 3D Thin-Plate-Spline を制御点対応から当てはめる。
- `tps_warp` (`deformation, points → points`) — TPS モデルで点群を変形する。
- `register_nonrigid` (`points, points → points`) — 非剛体 ICP で ``src`` を ``dst`` へ寄せる。
- `register_cpd_rigid` (`points, points → pose`) — Coherent Point Drift(CPD)剛体版で回転+並進を EM 推定する。

### depth_denoise(3)
- `bilateral_filter_depth` (`depth → depth`) — 深度画像の bilateral filter(段差保存デノイズ)。→ float64 (H,W)。
- `joint_bilateral` (`depth, image2d → depth`) — joint / cross bilateral: 平滑対象は depth、range 重みは guide の差で作る。→ float64 (H,W)。
- `fill_holes` (`depth → depth`) — 無効画素(穴)を近傍有効画素から調和(ラプラス)緩和で補間。→ float64 (H,W)。

### describe(2)
- `sh_descriptor` (`voxel → descriptor`) — 球面調和記述子。同心球 shell の SH 帯域エネルギー ‖f_l(r)‖ を (半径 × 周波数) で返す。
- `match_sh_descriptor` (`voxel, voxel → measurement`) — SH 記述子同士のコサイン類似度(回転不変な形状照合)。1 に近いほど同形状。voxel × SH 列。

### detect(2)
- `hough_plane_3d` (`voxel → primitive`) — 平面検出(2D Hough 直線の 3D リフト)。勾配=法線を使い (法線 n, 距離 d) 空間へ投票。
- `hough_sphere_3d` (`voxel → primitive`) — 球検出(2D Hough 円の 3D リフト)。中心 = p + sgn·r·n を半径 r ごとに投票。

### edges(5)
- `gradient3d` (`voxel → gradient`) — ガウス平滑後の中心差分勾配を計算する。
- `canny3d` (`voxel → voxel`) — 3D Canny エッジ検出(非最大抑制 + ヒステリシス)。
- `log_zero_crossings` (`voxel → voxel`) — Laplacian-of-Gaussian のゼロ交差エッジ。
- `link_edges` (`voxel → voxel`) — エッジ mask を 26 近傍で連結成分ラベリングする。
- `edge_points` (`voxel → points`) — エッジ mask を (M,3) の座標点群にする(下流の chamfer / Hough 用)。

### feature(4)
- `sobel3d` (`voxel → gradient`) — 3D 勾配 (gz,gy,gx)。導関数[-1,0,1]×平滑[1,2,1] の分離 conv3d。
- `hessian3d` (`voxel → hessian`) — 3D Hessian の 6 独立成分 (fzz,fyy,fxx,fzy,fzx,fyx)。分離 conv3d(2 階/1 階×平滑)。
- `curvature_maps` (`voxel → curvature`) — level-set の主曲率 → shape index S(Koenderink)と curvedness。閉形式(Kindlmann 2003)。
- `edt_jfa` (`voxel → sdf`) — 3D ユークリッド距離変換 = Jump Flooding Algorithm(GPU)。各 voxel → 最近 seed 距離。

### feature_register(7)
- `harris3d_keypoints` (`voxel → keypoints`) — 3D Harris キーポイント検出(2D Harris コーナー検出の 3D 版)。
- `iss_keypoints` (`points → keypoints`) — ISS(Intrinsic Shape Signatures、3D Harris 相当)キーポイント検出。
- `compute_fpfh` (`points, normals → descriptor`) — FPFH 記述子 (N, 3*n_bins) を計算(Rusu 2009)。
- `shot_descriptor` (`points, normals → descriptor`) — SHOT 記述子(Tombari 2010)。各キーポイントに LRF を張り、球状支持を
- `register_spin` (`points, points → pose`) — Spin Image 記述子 + RANSAC による初期推定なし疎特徴剛体位置合わせ。
- `register_fpfh` (`points, points → pose`) — FPFH 記述子 + RANSAC で **初期推定なし** の剛体位置合わせ (R,t) を推定する。
- `register_shot` (`points, points → pose`) — SHOT 記述子による疎特徴マッチング + RANSAC 剛体姿勢推定(全パイプライン)。

### freeform(5)
- `fit_bspline_surface` (`points → surface`) — 散布 (x, y, z) に双三次(既定)B スプライン曲面を最小二乗フィット(bisplrep)。
- `eval_bspline_surface` (`surface → image2d`) — フィット済み曲面 tck を評価(bisplev)。散布点(既定)または格子の 2 モード。
- `surface_residual` (`points, surface → measurement`) — 散布データと曲面 tck の残差統計を返す(形状誤差=フィットからの逸脱)。
- `fit_bspline_curve` (`points → surface`) — 順序付き点列(M,D)に B スプライン曲線をフィット(splprep, パラメトリック)。
- `eval_bspline_curve` (`surface → points`) — 曲線 tck をパラメータ u∈[0,1] 上 n 点で等間隔評価(splev)。

### fusion(2)
- `register_cross` (`any, any → pose`) — 異種構造間の剛体登録。両者を点群へ変換 → 登録器(fpfh=大回転/icp=要 coarse init)。
- `fuse_to_voxel` (`any → voxel`) — 複数構造を共通密度 voxel へ融合(TRIZ 統合)。items=[(data,kind,params_dict), ...]。

### geodesic(4)
- `geodesic_distances` (`points → measurement`) — source から全点への測地距離(kNN グラフ上 Dijkstra)。→ (N,) float(不達は inf)。
- `geodesic_mesh` (`mesh → measurement`) — 三角メッシュのエッジグラフ上 Dijkstra で source から各頂点への測地距離。→ (V,) float。
- `farthest_point_sampling` (`points → keypoints`) — 測地距離での最遠点サンプリング(均等間引き)。→ 選択インデックス列 (n,) int。
- `knn_graph` (`points → graph`) — 各点の k 近傍インデックスと Euclid 距離(自己を除く)。→ (idx (N,k) int, dist (N,k) float)。

### geometry(15)
- `line_from_2points` (`points → primitive`) — 2 点 → 直線(通過点, 単位方向)。2 座標で線が定まる(2D/3D 共通)。
- `plane_from_3points` (`points → primitive`) — 3 点 → 平面(通過点, 単位法線)。3 座標で面が定まる(2D/3D 共通)。
- `angle_3points` (`points → measurement`) — 3 点のなす角(頂点 b、度)。∠ABC。
- `angle_between_lines` (`primitive → measurement`) — 2 直線方向のなす鋭角(度)。
- `angle_between_planes` (`primitive → measurement`) — 2 平面の二面角(法線 n1,n2、度)。
- `angle_line_plane` (`primitive → measurement`) — 直線(方向 d)と平面(法線 n)のなす角(度)。
- `distance_point_plane` (`points, primitive → measurement`) — 点-平面距離(符号なし)。
- `distance_point_line` (`points, primitive → measurement`) — 点-直線距離。
- `distance_line_line` (`primitive → measurement`) — 2 直線間距離(ねじれの位置=skew も可)。平行なら点-線距離に退避。
- `intersect_line_plane` (`primitive → position`) — 直線 ∩ 平面 → 点(平行なら None)。
- `intersect_planes` (`primitive → primitive`) — 平面 ∩ 平面 → 直線(通過点, 方向)。平行なら None。
- `fit_line_3d` (`points → primitive`) — 点群 → 最小二乗直線(通過点=重心, 方向=最大主軸)。返り値 (point, direction)。
- `fit_plane_3d` (`points → primitive`) — 点群 → 最小二乗平面(通過点=重心, 法線=最小主軸, 残差 RMS)。返り値 (point, normal, resid)。
- `fit_sphere_3d` (`points → primitive`) — 点群 → 最小二乗球(代数フィット)。返り値 (center, radius)。配管/ボール計測に。
- `fit_circle_3d` (`points → primitive`) — 点群 → 3D 円(平面フィット → 面内で 2D 円フィット)。返り値 (center, radius, normal)。

### gicp(2)
- `gicp` (`points, points → pose`) — Generalized-ICP(共分散重みマハラノビス ICP)で剛体変換 (R,t) を推定する。
- `estimate_covariances` (`points → descriptor`) — 各点の局所共分散を固有値 (ε,1,1) に置換した plane-to-plane 共分散 (N,3,3)。

### lidar_projection(3)
- `project_spherical` (`points → image2d`) — 回転式 LiDAR の球面レンジ画像へ投影 (v_res, h_res)。空セル=0, 近い点優先(最小 range)。
- `unproject_spherical` (`image2d → points`) — 球面レンジ画像 → 3D 点 (M, 3)。range>0 のセルのみをビン中心角で逆投影。
- `project_cylindrical` (`points → image2d`) — 円柱レンジ画像へ投影 (z_bins, h_res)。方位角(列)× z(行)、画素=水平半径 ρ=hypot(x,y)。

### match_localize(6)
- `match_shape_3d` (`voxel, voxel → position`) — 3D 形状ベース(勾配方向)マッチング = 2D shapematch_gpu の voxel 版(「輪郭マッチング」)。
- `match_chamfer_3d` (`voxel, voxel → position`) — chamfer / 距離場マッチング(部分・遮蔽に頑健)。voxel × chamfer 列。
- `match_curvature_3d` (`voxel, voxel → position`) — 曲率(shape index)マッチング。voxel × 曲率列(線→面リフトの本丸)。
- `match_hough_3d` (`voxel, voxel → position`) — generalized Hough 3D(Ballard R-table 投票)。voxel × Hough 列。
- `match_mip_2d` (`voxel, voxel → position`) — MIP 投影 → 2D NCC(構造=voxel → 2D × 手法=NCC、変換=直交 MIP)。
- `match_points_ncc` (`points, points → position`) — 点群同士マッチング(構造=point cloud × 手法=NCC、変換=splat)。model を scene 内で定位。

### match_pose(4)
- `match_phase_3d` (`voxel, voxel → shift`) — 3D 位相相関(FFT)。b を a に合わせる整数シフト (dz,dy,dx) を返す。
- `match_pca` (`points, points → pose`) — PCA 姿勢マッチング(構造=point cloud × 手法=主軸整列)。
- `moment_axes` (`points → axes`) — 点群/重み付き点の **重心 + 主軸**(慣性テンソルの固有ベクトル)。姿勢推定の基礎。
- `match_logpolar_z` (`voxel, voxel → rot_scale`) — log-polar × 位相相関(Fourier-Mellin)で **z 軸回転 + 等方スケール**を復元。

### medial(5)
- `distance_ridge` (`voxel → voxel`) — EDT のリッジ(距離場の局所極大)を medial として抽出。返り値 (ridge_mask, edt)。
- `skeletonize_vol` (`voxel → voxel`) — 3D バイナリ voxel を細線化して 1 voxel 幅の骨格に。skimage の Lee(1994)法ラッパ。
- `medial_axis_points` (`voxel → points`) — medial voxel の座標と局所半径(= その点の EDT 値)を点群化。返り値 (points, radius)。
- `topology_signature` (`voxel → descriptor`) — 骨格の 26 近傍次数から位相記述子を作る。端点/分岐点/通常点/孤立点の個数を返す。
- `medial_match` (`voxel, voxel → measurement`) — 2 つの voxel 形状の medial(位相 + 半径分布)による粗照合スコア。返り値 [0,1]。

### metrics(7)
- `chamfer_distance` (`points, points → measurement`) — 対称 Chamfer 距離 = 0.5*(mean_a min_b + mean_b min_a)。→ scalar。小さいほど一致。
- `hausdorff_distance` (`points, points → measurement`) — 対称 Hausdorff 距離 = max(max_a min_b, max_b min_a)。→ scalar。最悪ケースの乖離。
- `fscore` (`points, points → measurement`) — F-score @ tau = precision と recall の調和平均。→ (f, precision, recall)。再構成の標準指標。
- `rmse_correspondence` (`points, points → measurement`) — 対応既知(同 index)の RMSE = sqrt(mean |a_i - b_i|^2)。→ scalar。登録残差の評価。
- `normal_consistency` (`points, normals → measurement`) — 最近傍対応での法線一致度 = mean|cos(na, nb)|(向き無視)。→ [0,1]。1=完全一致。
- `voxel_iou` (`voxel, voxel → measurement`) — voxel 占有の IoU(intersection over union)。→ [0,1]。体積一致度。
- `pose_error` (`pose, pose → measurement`) — 姿勢誤差 = (回転角[度], 並進ノルム)。登録結果の GT 比較。→ (rot_deg, trans_err)。

### moment_invariant(4)
- `moment_invariants` (`points → descriptor`) — 並進+回転+スケール不変な形状特徴ベクトル(Sadjadi–Hall 流 + 高次半径分布)。
- `principal_moments` (`points → descriptor`) — 慣性テンソルの固有値(主慣性モーメント、降順ソート、回転不変)。
- `central_moments` (`points → descriptor`) — 重心中心化した中心モーメント μ_{pqr}(並進不変、キー=(p,q,r))を返す。
- `inertia_tensor` (`points → matrix`) — 点群の慣性テンソル (3,3)(中心 2 次モーメントから、等質量・総質量 1)。

### morphology(5)
- `morph_dilate3d` (`voxel → voxel`) — 3D グレースケール dilation(cube SE 半径 r の局所 max)。明領域を膨張。
- `morph_erode3d` (`voxel → voxel`) — 3D グレースケール erosion(cube SE の局所 min)。明領域を収縮。
- `morph_gradient3d` (`voxel → voxel`) — 3D モルフォロジー勾配 = dilation − erosion。**境界/表面**を抽出(sobel 代替のエッジ源)。
- `morph_tophat3d` (`voxel → voxel`) — 3D white top-hat = vol − opening。SE より小さい **明構造**を抽出(keypoint 前処理)。
- `morph_blackhat3d` (`voxel → voxel`) — 3D black-hat = closing − vol。SE より小さい **暗構造/穴**を抽出。

### motion(1)
- `scene_flow_lk` (`voxel, voxel → flow`) — Lucas-Kanade scene flow(2D optical flow の 3D 版)。voxel ごとの運動場 d=(dz,dy,dx)。

### motion_segment(3)
- `segment_rigid_motions` (`points, points → labels`) — 2 点群を運動が一致する剛体ごとに分割する(反復 RANSAC による multi-body 分割)。
- `estimate_flow` (`points, points → flow`) — pts0 の各点から pts1 の最近傍への 3-D 変位ベクトル場 (N, 3) を返す(最近傍フロー)。
- `fit_rigid` (`points, points → pose`) — 対応点から閉形式 Kabsch で剛体変換 (R, t) を推定する(pts_from[i] -> pts_to[i])。

### normals_orient(2)
- `estimate_oriented_normals` (`points → normals`) — PCA 法線推定 + Hoppe 大域向き付けの合成。→ (N,3) の向き付き単位法線。
- `orient_normals` (`points, normals → normals`) — Hoppe 法で法線を**大域一貫**に向き付け(MST 伝播)。→ (N,3)。

### occupancy(4)
- `occupancy_grid` (`points → voxel`) — 点群 (N,3) → 3-D 占有ボクセル格子 (res,res,res) bool(点の落ちた voxel を占有)。
- `esdf` (`voxel → sdf`) — 占有格子 → Euclidean 符号付き距離場 (ESDF)(外=+ 最近占有まで, 内=- 最近自由まで)。
- `inflate` (`voxel → voxel`) — 障害物を ``radius``(world 単位)膨張した占有格子 bool(= ESDF<=radius を占有)。
- `query_distance` (`sdf, points → measurement`) — 任意 world 座標 (M,3) での ESDF 値 (M,) を返す(``mode``='trilinear' 補間 or 'nearest')。

### optics(5)
- `reflect` (`vector, normals → vector`) — 入射方向 d を法線 n の面で鏡面反射。r = d − 2(d·n)n。
- `refract` (`vector, normals → vector`) — Snell 屈折(ベクトル形)。d=入射(面へ向かう), n=入射側外向き法線, 屈折率 eta1→eta2。
- `fresnel_reflectance` (`measurement → measurement`) — Fresnel 反射率(無偏光=s/p 平均)。透明体界面で反射/透過に分かれる割合。
- `normal_from_reflection` (`vector, vector → normals`) — 入射+反射から鏡面の法線を復元(deflectometry)。n ∝ (r − d)、入射に逆らう向きへ。
- `snell_angle` (`measurement → measurement`) — 入射角(度)→ 屈折角(度)。n1 sinθi = n2 sinθt。臨界角超は NaN(全反射)。

### photometric(4)
- `photometric_stereo` (`images → normals`) — Lambertian フォトメトリックステレオ: 既知光源方向の N 枚から法線とアルベドを復元。→ (normals HxWx3, albedo HxW)。
- `surface_normals` (`image2d → normals`) — 高さ場 z(HxW)→ 単位法線 (H,W,3)。n ∝ (-dz/dx, -dz/dy, 1)。深度→法線の順変換。
- `integrate_normals` (`normals → image2d`) — 法線場 → 高さ場 z を Frankot-Chellappa 積分。→ z HxW(定数分の自由度あり・平均0基準)。
- `render_lambertian` (`normals → image2d`) — 法線 + アルベド + 光源方向 → Lambertian 画像(検査サンプル生成 / GT 検証 / 逆レンダの順方向)。→ HxW。

### plane_sweep_stereo(2)
- `plane_sweep_depth` (`image2d, image2d → depth`) — plane-sweep stereo で密な深度マップを推定。→ (H,W) depth。
- `warp_by_plane` (`image2d → image2d`) — homography H で img を逆ワープ。→ out[y,x] = img(H·(x,y,1))(bilinear)。

### pose_estimation(3)
- `dlt_pose` (`points, image2d → pose`) — DLT で 3D-2D 対応からカメラ姿勢を復元(K 既知)。→ (R (3,3), t (3,))。6 点以上必要。
- `pnp_ransac` (`points, image2d → pose`) — 外れ値に頑健な PnP(RANSAC + 最終 DLT リフィット)。→ (R, t, inlier_mask, info)。
- `reprojection_error` (`points, pose → measurement`) — 再投影誤差(RMS ピクセル)。姿勢の当てはまり評価。→ scalar。

### pose_graph(3)
- `optimize_pose_graph` (`pose → pose`) — 相対姿勢制約 + ループ閉じから大域姿勢を最適化。→ dict{poses, rmse, cost}。
- `relative_pose` (`pose, pose → pose`) — T_i⁻¹ ∘ T_j = i←j の相対姿勢。pose_* = [rvec|t] (6,)。→ (rvec_ij (3,), t_ij (3,))。
- `mean_edge_error` (`pose → measurement`) — エッジ残差の RMS(姿勢グラフの整合度)。→ scalar。

### preprocess(4)
- `statistical_outlier_removal` (`points → points`) — 各点の k 近傍平均距離が大域的に外れる点を除去する(統計的外れ値除去)。
- `radius_outlier_removal` (`points → points`) — 半径 radius 内の近傍数が min_neighbors 未満の点を除去する(孤立点除去)。
- `voxel_grid_downsample` (`points → points`) — 辺 voxel_size の格子で点群を間引き、各セルを重心 1 点に集約する(決定論的)。
- `mls_smooth` (`points → points`) — 各点を局所多項式曲面へ射影してノイズを落とす(Moving Least Squares 平滑)。

### range_image(4)
- `depth_to_organized_points` (`depth → points`) — organized 深度画像 → 格子整列 3D 点 (H,W,3)。
- `normals_from_depth` (`depth → normals`) — organized 深度 → 向き付き単位法線 (H,W,3)。隣接画素の 3D 点の外積(格子構造を利用、O(HW))。
- `occlusion_edges` (`depth → image2d`) — 深度の不連続(前景/背景境界 = 遮蔽エッジ)を検出。→ bool HxW。
- `bearing_angle_image` (`depth → image2d`) — bearing-angle 画像: 走査方向に沿った視線と局所面のなす角(range image の古典記述子)。→ HxW(度)。

### reconstruct(4)
- `poisson_lite` (`points → mesh`) — 点群 (N,3) → (vertices(V,3), faces(F,3)) の表面メッシュ(スクリーンド Poisson 軽量近似)。
- `alpha_shape_mesh` (`points → mesh`) — alpha shapes による**表面三角形メッシュ**(点群 → (vertices, faces))。
- `alpha_shape_boundary` (`points → points`) — alpha shapes による**境界点インデックス**を返す(点群 → 境界点)。
- `estimate_alpha` (`points → measurement`) — 点群のスケールから推奨 alpha を返す(最近傍距離の中央値ベース)。

### refine(6)
- `refine_peak_newton` (`score, position → position`) — スコア/相関 volume の整数ピークを 3D Newton でサブボクセル精緻化する(反復最適化)。
- `refine_translation_lk` (`voxel, voxel, position → position`) — Gauss-Newton 逆合成 Lucas-Kanade による 3D 並進サブボクセル精緻化。
- `refine_lm` (`voxel, voxel, position → pose`) — Levenberg-Marquardt による並進(+等方スケール/輝度ゲイン)サブボクセル精緻化。
- `refine_rotation_z` (`voxel, voxel, angle → angle`) — z 軸回転角の **Gauss-Newton 精緻化**(Lucas-Kanade on SSD、1 パラメータ)。
- `icp_point2point_3d` (`points, points → pose`) — 点群を point-to-point ICP(Kabsch/SVD)で精緻化する。
- `icp_point2plane` (`points, points, normals → pose`) — 点-面 ICP(Gauss-Newton, 小角近似)で剛体変換を高精度に精緻化する。

### regionprops(4)
- `label_components` (`voxel → voxel`) — 3D 二値ボリュームを連結成分にラベリングする。
- `region_props` (`voxel → measurement`) — 各連結成分のリージョンプロパティ一覧を返す。
- `largest_component` (`voxel → voxel`) — 最大(最多ボクセル)連結成分の bool マスクを返す。
- `filter_by_volume` (`voxel → voxel`) — min_voxels 未満の連結成分を除去した bool マスクを返す。

### registration_metrics(4)
- `inlier_ratio` (`points, points → measurement`) — 対応集合の inlier 率 = ‖T·source[i] − target[i]‖ < thresh の割合。→ [0,1]。
- `rmse_inliers` (`points, points → measurement`) — inlier 対応(残差 < thresh)上の RMSE と inlier 数。→ (rmse, n_inliers)。
- `registration_recall` (`points, points → measurement`) — 3DMatch 流の per-pair 登録成否 = 1.0(成功)/ 0.0(失敗)。
- `rotation_translation_error` (`pose, pose → measurement`) — 2 つの 4×4 変換間の相対回転誤差(測地角[度], RRE)と相対並進誤差(RTE)。

### render(4)
- `project_points` (`points → image2d`) — 3D 点群 (N,3) → 画像座標 (u,v) と深度。ピンホール(depth_to_points の順方向)。
- `render_point_depth` (`points → depth`) — 点群 → 深度画像(z-buffer、各画素に最近点の深度)。観測合成/外観検査サンプル。
- `render_volume_projection` (`voxel → image2d`) — voxel を任意視点で 2D 投影(mode=xray=減衰積算 / mip=最大値)。DRR(X線)・世界モデル観測。
- `render_shaded` (`normals → image2d`) — 法線マップ (H,W,3) + 光源方向 → Lambertian 陰影画像(外観サンプル生成、光学と接続)。

### robust_fit(4)
- `ransac_plane` (`points → primitive`) — 外れ値に頑健な RANSAC 平面適合。
- `ransac_sphere` (`points → primitive`) — 外れ値に頑健な RANSAC 球適合。
- `ransac_line` (`points → primitive`) — 外れ値に頑健な RANSAC 直線適合。
- `ransac_cylinder` (`points, normals → primitive`) — 外れ値に頑健な RANSAC 円筒適合(点法線が必要)。

### scene_flow3d(3)
- `nearest_neighbor_flow` (`points, points → flow`) — 各点 pts0 から pts1 の最近傍への 3-D 変位ベクトル場 (N, 3) を返す。
- `rigid_flow` (`points, points → pose`) — pts0 -> pts1 を説明する単一剛体運動を最近傍対応 + Kabsch(ICP 風)で推定。
- `smooth_flow` (`points, points → flow`) — 最近傍フローを近傍平均で局所平滑化した正則化フロー (N, 3) を返す。

### sdf_csg(7)
- `sphere_sdf` (`points → sdf`) — 球の符号付き距離場: ``|p - center| - R``(内側負・外側正)。
- `box_sdf` (`points → sdf`) — 軸平行直方体の**厳密**な符号付き距離場(内側負・外側正)。
- `sdf_union` (`sdf, sdf → sdf`) — 2 SDF の和集合 A∪B = 要素ごとの min(a, b)(内側=負がどちらかにあれば内側)。
- `sdf_intersect` (`sdf, sdf → sdf`) — 2 SDF の積集合 A∩B = 要素ごとの max(a, b)(両方の内側でのみ内側)。
- `sdf_subtract` (`sdf, sdf → sdf`) — 差集合 A\B = max(a, -b)(A の内側 かつ B の外側 = ``-b`` の内側)。
- `sdf_smooth_union` (`sdf, sdf → sdf`) — 滑らかに丸めた和集合(polynomial smooth-min)。``k>0`` で継ぎ目を半径 ~k で丸める。
- `sdf_offset` (`sdf → sdf`) — SDF のゼロ等値面を距離 ``r`` だけ法線方向へ動かす = ``sdf - r``(r>0 膨張, r<0 収縮)。

### segment(3)
- `region_growing` (`points → labels`) — 法線類似で領域成長し連結した平滑領域へ同ラベルを付す(曲率ゲート無し変種)。
- `euclidean_cluster` (`points → labels`) — 半径 tol の近接グラフの連結成分で距離クラスタリング(-1=ノイズ)。
- `plane_segmentation` (`points → labels`) — 反復 RANSAC で最大 max_planes 枚の平面を逐次抽出(残差点 -1)。

### shape_descriptor(5)
- `d2_distribution` (`points → descriptor`) — ランダムな 2 点対のユークリッド距離分布(Osada 2002 の D2)。
- `a3_distribution` (`points → descriptor`) — ランダムな 3 点 (A, B, C) が頂点 B で作る角の分布(Osada 2002 の A3)。
- `extent_signature` (`points → descriptor`) — PCA 主軸(共分散の固有ベクトル)方向の広がりの比を返す。
- `describe` (`points → descriptor`) — D2 + A3 + extent を連結した大域形状記述子を返す。
- `shape_distance` (`descriptor, descriptor → measurement`) — 2 つの記述子間の距離。小さいほど同形状。

### space_carving(3)
- `carve` (`images → voxel`) — bounds を res^3 voxel に離散化し、全シルエット内に射影される voxel を残す(空間彫刻)。
- `visual_hull` (`images → voxel`) — 多視点シルエットの visual hull を voxel 占有として返す(:func:`carve` の別名)。
- `synthesize_silhouette` (`points → image2d`) — 3-D 点群を (K,R,t) カメラへ射影し占有画素 True のシルエット(H,W bool)を返す。

### structured_light(5)
- `wrapped_phase` (`images → image2d`) — N-step 位相シフト縞画像から wrapped phase (-π, π] を求める。
- `unwrap_phase_2d` (`image2d → image2d`) — wrapped phase を skimage.restoration.unwrap_phase で連続位相に展開する。
- `graycode_decode` (`images → image2d`) — Gray code ビット画像列 → 整数フリンジ次数マップ(絶対次数)。
- `decode_fringe` (`images → depth`) — 位相シフト画像列を一括復号: wrapped → unwrap →(参照減算で)高さ。
- `synthesize_fringes` (`image2d → images`) — 既知の height map から N-step 位相シフト縞画像列を合成する(テスト/サンプル生成用)。

### superquadric(4)
- `fit_superquadric` (`points → primitive`) — 点群にスーパー2次曲面を least_squares で当てはめ dict{a,eps,R,t,residual} を返す。
- `sample_surface` (`primitive → points`) — スーパー2次曲面の表面点を (eta, omega) パラメトリックにサンプリング。
- `inside_outside` (`points → measurement`) — スーパー2次曲面の内外関数 F(表面=1, 内部<1, 外部>1)。
- `superquadric_residual` (`points → measurement`) — Gross-Boult 体積補正残差 mean( (sqrt(a1 a2 a3)(F^eps1 - 1))^2 )。

### surface_fit(4)
- `fit_poly_surface` (`image2d → surface`) — 散布 (x,y,z) → z=f(x,y) 多項式最小二乗。返り値 model(coef/powers/degree/rms/pv)。
- `eval_poly_surface` (`surface → image2d`) — model を (x,y) で評価 → z(x の shape で返す)。
- `surface_form_error` (`image2d → measurement`) — 高さ場 grid → 理想曲面(多項式)残差=形状誤差(平面度 deg1/球面度 deg2)。→ (residual, rms, pv)。
- `background_flatten` (`image2d → image2d`) — 画像の低次曲面(照明ムラ)をフィット減算=シェーディング補正。→ flattened。

### symmetry(4)
- `detect_reflection_symmetry` (`points → primitive`) — PCA 主軸を法線とする候補平面(重心通過)から最良の反射対称面を選ぶ。
- `detect_rotational_symmetry` (`points → primitive`) — PCA 主軸を候補軸として最良の回転対称(軸 × order)を選ぶ。
- `reflect_points` (`points → points`) — 点群を平面(点 plane_point・法線 plane_normal)で鏡映。→ (N,3)。
- `reflection_symmetry_score` (`points → measurement`) — 反射対称スコア = chamfer(鏡映, 元) / 中央値最近傍間隔(小さいほど対称、スケール不変)。→ float。

### transform(12)
- `points_to_voxel` (`points → voxel`) — 点群 (N,3) → 密度 voxel (size³)。scatter_add で splat、任意で gaussian 平滑。
- `gaussians_to_voxel` (`gaussians → voxel`) — 3DGS(異方性ガウス)→ 密度 voxel。各ガウスを means に opacity で置き、平均 scale で平滑。
- `mesh_to_voxel` (`mesh → voxel`) — mesh(頂点+面)→ 密度 voxel。面上を一様サンプリング → splat(mesh 行を全手法へ接続)。
- `mesh_to_points` (`mesh → points`) — mesh(頂点+面)→ 表面点群(面積重み一様サンプリング)。mesh→point cloud 変換。
- `depth_to_points` (`depth → points`) — 深度マップ(2.5D)→ point cloud(ピンホール逆投影)。depth 行を全手法へ接続。
- `voxel_to_mips` (`voxel → image2d`) — 3D → 直交 3 方向の最大値投影(MIP)。2D 手法(accel の 2D NCC 等)を適用する入口。
- `voxel_to_mesh` (`voxel → mesh`) — voxel → mesh(marching cubes、skimage)。返り値 (verts, faces, normals)。voxel→mesh 変換。
- `tsdf_from_depth` (`depth → sdf`) — 深度マップ(2.5D)→ TSDF volume(RGB-D 再構成の標準表現)。depth→TSDF 変換。
- `signed_distance_field` (`voxel → sdf`) — occupancy/密度 voxel → 符号付き距離場 SDF(内側<0・外側>0)。edt_jfa を両側に。
- `sdf_to_occupancy` (`sdf → voxel`) — SDF → occupancy voxel(iso 以下=内側=1)。SDF から voxel へ戻す。
- `estimate_point_normals` (`points → normals`) — 点群 (N,3) → 単位法線(局所 k 近傍共分散の最小固有ベクトル=PCA)。
- `to_points` (`voxel, points, mesh, depth, gaussians → points`) — 任意の 3D 構造 → 点群(共通表現)。全5構造を 1 本の入口へ統合。

### tsdf_fusion(3)
- `fuse` (`depth → sdf`) — 深度列を new_volume + integrate で 1 つの TSDF volume に融合。返り値 (tsdf, weight)。
- `integrate` (`sdf, depth → sdf`) — 深度 1 枚を投影的 TSDF で volume に統合(in-place、重み付き移動平均)。
- `extract_surface_points` (`sdf → points`) — TSDF ゼロ交差から表面点 (M,3) を抽出(marching cubes 不要、線形補間)。

### two_view(5)
- `fundamental_8point` (`image2d, image2d → matrix`) — 正規化 8 点法で基礎行列 F を推定(rank-2 強制)。→ F (3,3)。8 点以上必要。
- `essential_8point` (`image2d, image2d → matrix`) — 対応点 + K から本質行列 E を直接。→ E (3,3)。
- `recover_pose` (`image2d, image2d → pose`) — 対応点 + K から相対姿勢 (R,t) と 3D 構造を復元(cheirality で一意化)。→ (R, t_unit, points3d)。
- `triangulate` (`image2d, image2d → points`) — DLT 三角測量: 2 視点の対応点 + 射影行列 → 3D 点。→ (N,3)。
- `sampson_distance` (`image2d, image2d → measurement`) — エピポーラ拘束の Sampson 距離(1 次幾何誤差、各対応)。→ (N,)。

## 2-D pipeline operators(ops registry)by category
_計 735 ops / 46 categories。_


1 画像を取り 1 画像/領域/輪郭/特徴を返すパイプライン op。`in → out` のデータ種で連鎖を組む。HALCON 別名は用途の手掛かり。

### 3d(7)
- `vol_gaussian` `volume → volume`
- `vol_median` `volume → volume`
- `vol_erode` `volume → volume`
- `vol_dilate` `volume → volume`
- `vol_threshold` `volume → volume`
- `vol_mip` `volume → image`
- `vol_slice` `volume → image`

### arithmetic(10)
- `abs_image` (halcon: `abs_image`) `image → image`
- `sqrt_image` (halcon: `sqrt_image`) `image → image`
- `exp_image` (halcon: `exp_image`) `image → image`
- `log_image` (halcon: `log_image`) `image → image`
- `sin_image` (halcon: `sin_image`) `image → image`
- `cos_image` (halcon: `cos_image`) `image → image`
- `asin_image` (halcon: `asin_image`) `image → image`
- `acos_image` (halcon: `acos_image`) `image → image`
- `atan_image` (halcon: `atan_image`) `image → image`
- `tan_image` (halcon: `tan_image`) `image → image`

### artificial-life(12)
- `alife_gray_scott` `image → image`
- `alife_turing` `image → image`
- `alife_life_step` `image → image`
- `alife_cyclic_ca` `image → image`
- `alife_perona_malik` `image → image`
- `alife_curvature_flow` `image → image`
- `alife_dla` `image → image`
- `alife_reaction_bz` `image → image`
- `alife_wolfram1d` `image → image`
- `alife_langton_ant` `image → image`
- `alife_lenia` `image → image`
- `alife_sandpile` `image → image`

### artistic(3)
- `xcv_stylization` `image → image`
- `xcv_pencil_sketch` `image → image`
- `xpil_emboss` `image → image`

### augmentation(10)
- `aug_shot_noise` `image → image`
- `aug_read_noise` `image → image`
- `aug_fixed_pattern` `image → image`
- `aug_motion_blur` `image → image`
- `aug_vignette` `image → image`
- `aug_chromatic` `image → image`
- `aug_rolling_shutter` `image → image`
- `aug_jpeg_blocks` `image → image`
- `aug_cutout` `image → image`
- `aug_barrel` `image → image`

### barcode(1)
- `decode_barcode` (halcon: `find_bar_code`) `image → feature`

### classification(1)
- `classify_shape` `region → feature`

### color(8)
- `cfa_to_rgb` (halcon: `cfa_to_rgb`) `image → color`
- `trans_from_rgb` (halcon: `trans_from_rgb`) `color → color`
- `trans_to_rgb` (halcon: `trans_to_rgb`) `color → color`
- `linear_trans_color` (halcon: `linear_trans_color`) `color → color`
- `principal_comp` (halcon: `principal_comp`) `color → color`
- `rgb1_to_gray` (halcon: `rgb1_to_gray`) `color → image`
- `rgb3_to_gray` (halcon: `rgb3_to_gray`) `color → image`
- `access_channel` (halcon: `access_channel`) `color → image`

### contour(26)
- `edges_sub_pix` (halcon: `edges_sub_pix`) `image → contour`
- `select_contours` (halcon: `select_contours_xld`) `contour → contour`
- `smooth_contours` (halcon: `smooth_contours_xld`) `contour → contour`
- `fit_line_contours` (halcon: `fit_line_contour_xld`) `contour → contour`
- `contours_to_region` (halcon: `gen_region_contour_xld`) `contour → region`
- `sk_find_contours` `image → contour`
- `edges_sub_pix` (halcon: `edges_sub_pix`) `image → contour`
- `lines_gauss` (halcon: `lines_gauss`) `image → contour`
- `select_contours_xld` (halcon: `select_contours_xld`) `contour → contour`
- `smooth_contours_xld` (halcon: `smooth_contours_xld`) `contour → contour`
- `gen_region_contour_xld` (halcon: `gen_region_contour_xld`) `contour → region`
- `close_contours_xld` (halcon: `close_contours_xld`) `contour → contour`
- `affine_trans_contour_xld` (halcon: `affine_trans_contour_xld`) `contour → contour`
- `projective_trans_contour_xld` (halcon: `projective_trans_contour_xld`) `contour → contour`
- `polar_trans_contour_xld` (halcon: `polar_trans_contour_xld`) `contour → contour`
- `shape_trans_xld` (halcon: `shape_trans_xld`) `contour → contour`
- `threshold_sub_pix` (halcon: `threshold_sub_pix`) `image → contour`
- `zero_crossing_sub_pix` (halcon: `zero_crossing_sub_pix`) `image → contour`
- `lines_facet` (halcon: `lines_facet`) `image → contour`
- `gen_region_polygon_xld` (halcon: `gen_region_polygon_xld`) `contour → region`
- `affine_trans_polygon_xld` (halcon: `affine_trans_polygon_xld`) `contour → contour`
- `gen_contour_region_xld` (halcon: `gen_contour_region_xld`) `region → contour`
- `select_shape_xld` (halcon: `select_shape_xld`) `contour → contour`
- `contour_point_num_xld` (halcon: `contour_point_num_xld`) `contour → feature`
- `edges_color_sub_pix` (halcon: `edges_color_sub_pix`) `color → contour`
- `lines_color` (halcon: `lines_color`) `color → contour`

### decomposition(7)
- `dc_structure_texture` `image → image`
- `dc_texture_residual` `image → image`
- `dc_rpca_lowrank` `image → image`
- `dc_rpca_sparse` `image → image`
- `dc_retinex` `image → image`
- `dc_local_contrast_norm` `image → image`
- `dc_homomorphic` `image → image`

### deformation(3)
- `deform_tps` `image → image`
- `deform_ffd` `image → image`
- `deform_mls` `image → image`

### domain(2)
- `it_full_domain` `image → image`
- `it_crop_domain` (halcon: `crop_domain`) `image → image`

### edges(57)
- `sobel_mag` (halcon: `sobel_amp`) `image → image`
- `laplace` (halcon: `laplace`) `image → image`
- `prewitt_mag` (halcon: `prewitt_amp`) `image → image`
- `roberts_mag` (halcon: `roberts`) `image → image`
- `dog` (halcon: `diff_of_gauss`) `image → image`
- `grad_dir` `image → image`
- `log` (halcon: `laplace_of_gauss`) `image → image`
- `corner_response` (halcon: `points_harris`) `image → image`
- `sk_scharr` (halcon: `edges_image`) `image → image`
- `sk_farid` (halcon: `edges_image`) `image → image`
- `sk_dog` (halcon: `diff_of_gauss`) `image → image`
- `sk_hessian_det` `image → image`
- `sk_corner_harris` (halcon: `points_harris`) `image → image`
- `cv_scharr` (halcon: `edges_image`) `image → image`
- `cv_laplacian` (halcon: `laplace`) `image → image`
- `cv_corner_harris` (halcon: `points_harris`) `image → image`
- `cv_min_eigen` (halcon: `points_harris`) `image → image`
- `cv_precorner` (halcon: `corner_response`) `image → image`
- `derivate_gauss` (halcon: `derivate_gauss`) `image → image`
- `laplace_of_gauss` (halcon: `laplace_of_gauss`) `image → image`
- `diff_of_gauss` (halcon: `diff_of_gauss`) `image → image`
- `sobel_amp` (halcon: `sobel_amp`) `image → image`
- `sobel_dir` (halcon: `sobel_dir`) `image → image`
- `prewitt_amp` (halcon: `prewitt_amp`) `image → image`
- `prewitt_dir` (halcon: `prewitt_dir`) `image → image`
- `roberts` (halcon: `roberts`) `image → image`
- `kirsch_amp` (halcon: `kirsch_amp`) `image → image`
- `kirsch_dir` (halcon: `kirsch_dir`) `image → image`
- `frei_amp` (halcon: `frei_amp`) `image → image`
- `robinson_amp` (halcon: `robinson_amp`) `image → image`
- `laplace` (halcon: `laplace`) `image → image`
- `points_foerstner` (halcon: `points_foerstner`) `image → image`
- `points_harris_binomial` (halcon: `points_harris_binomial`) `image → image`
- `dots_image` (halcon: `dots_image`) `image → image`
- `frei_dir` (halcon: `frei_dir`) `image → image`
- `robinson_dir` (halcon: `robinson_dir`) `image → image`
- `edges_color` (halcon: `edges_color`) `color → image`
- `xsk_hessian_eig` `image → image`
- `xpil_contour` `image → image`
- `xpil_find_edges` `image → image`
- `xsp_morph_laplace` `image → image`
- `xsp_gauss_grad_mag` `image → image`
- `xsk2_corner_kr` `image → image`
- `xsk2_inv_gauss_grad` `image → image`
- `xwt_hf_reconstruct` `image → image`
- `xwt_directional_detail` `image → image`
- `xsk3_corner_moravec` `image → image`
- `xsk3_corner_fast` `image → image`
- `xkor_laplacian` `image → image`
- `xkor_harris` `image → image`
- `xkor_gftt` `image → image`
- `xkor_hessian` `image → image`
- `xkor_dog` `image → image`
- `f2_shock` (halcon: `shock_filter`) `image → image`
- `f2_topographic` (halcon: `topographic_sketch`) `image → image`
- `tf_steerable_filter` `image → image`
- `tf_phase_congruency` `image → image`

### extra(14)
- `xsitk_curvature_flow` `image → image`
- `xsitk_minmax_curv_flow` `image → image`
- `xsitk_curv_aniso_diff` `image → image`
- `xsitk_laplacian_sharpen` `image → image`
- `xsitk_grayscale_fillhole` `image → image`
- `xsitk_grayscale_grindpeak` `image → image`
- `xsitk_opening_by_recon` `image → image`
- `xsitk_closing_by_recon` `image → image`
- `xsitk_signed_maurer_dist` `region → image`
- `xsitk_connected_threshold` `image → region`
- `xsitk_confidence_connected` `image → region`
- `xsitk_maxentropy_thresh` `image → region`
- `xsitk_moments_thresh` `image → region`
- `xsitk_huang_thresh` `image → region`

### features(71)
- `blob_count` (halcon: `count_obj`) `region → feature`
- `area_frac` (halcon: `area_center`) `region → feature`
- `count_contours` (halcon: `count_obj`) `contour → feature`
- `total_length` (halcon: `length_xld`) `contour → feature`
- `vol_count` `volume → feature`
- `sk_euler` (halcon: `euler_number`) `region → feature`
- `sk_entropy_feat` (halcon: `entropy_gray`) `image → feature`
- `sk_blur_effect` `image → feature`
- `cv_cc_count` (halcon: `connection`) `region → feature`
- `cv_hough_lines` (halcon: `hough_lines`) `image → feature`
- `cv_hough_circles` (halcon: `hough_circles`) `image → feature`
- `cv_good_features` `image → feature`
- `area_center` (halcon: `area_center`) `region → feature`
- `count_obj` (halcon: `count_obj`) `region → feature`
- `circularity` (halcon: `circularity`) `region → feature`
- `compactness` (halcon: `compactness`) `region → feature`
- `convexity` (halcon: `convexity`) `region → feature`
- `rectangularity` (halcon: `rectangularity`) `region → feature`
- `eccentricity` (halcon: `eccentricity`) `region → feature`
- `orientation_region` (halcon: `orientation_region`) `region → feature`
- `roundness` (halcon: `roundness`) `region → feature`
- `diameter_region` (halcon: `diameter_region`) `region → feature`
- `euler_number` (halcon: `euler_number`) `region → feature`
- `min_max_gray` (halcon: `min_max_gray`) `image → feature`
- `intensity` (halcon: `intensity`) `image → feature`
- `gray_histo_abs` (halcon: `gray_histo_abs`) `image → feature`
- `entropy_gray` (halcon: `entropy_gray`) `image → feature`
- `length_xld` (halcon: `length_xld`) `contour → feature`
- `contlength` (halcon: `contlength`) `region → feature`
- `area_holes` (halcon: `area_holes`) `region → feature`
- `height_width_ratio` (halcon: `height_width_ratio`) `region → feature`
- `moments_region_2nd` (halcon: `moments_region_2nd`) `region → feature`
- `moments_region_2nd_invar` (halcon: `moments_region_2nd_invar`) `region → feature`
- `area_center_xld` (halcon: `area_center_xld`) `contour → feature`
- `circularity_xld` (halcon: `circularity_xld`) `contour → feature`
- `compactness_xld` (halcon: `compactness_xld`) `contour → feature`
- `convexity_xld` (halcon: `convexity_xld`) `contour → feature`
- `moments_region_3rd` (halcon: `moments_region_3rd`) `region → feature`
- `moments_region_central` (halcon: `moments_region_central`) `region → feature`
- `moments_region_central_invar` (halcon: `moments_region_central_invar`) `region → feature`
- `moments_region_2nd_rel_invar` (halcon: `moments_region_2nd_rel_invar`) `region → feature`
- `moments_region_3rd_invar` (halcon: `moments_region_3rd_invar`) `region → feature`
- `estimate_noise` (halcon: `estimate_noise`) `image → feature`
- `eccentricity_xld` (halcon: `eccentricity_xld`) `contour → feature`
- `orientation_xld` (halcon: `orientation_xld`) `contour → feature`
- `elliptic_axis_xld` (halcon: `elliptic_axis_xld`) `contour → feature`
- `diameter_xld` (halcon: `diameter_xld`) `contour → feature`
- `rectangularity_xld` (halcon: `rectangularity_xld`) `contour → feature`
- `moments_xld` (halcon: `moments_xld`) `contour → feature`
- `hough_line_trans` (halcon: `hough_line_trans`) `image → image`
- `hough_circle_trans` (halcon: `hough_circle_trans`) `image → image`
- `get_region_thickness` (halcon: `get_region_thickness`) `region → feature`
- `connect_and_holes` (halcon: `connect_and_holes`) `region → feature`
- `elliptic_axis` (halcon: `elliptic_axis`) `region → feature`
- `count_channels` (halcon: `count_channels`) `color → feature`
- `xsk_blob_log` `image → feature`
- `xsk_blob_dog` `image → feature`
- `xsk_blob_doh` `image → feature`
- `xsk_orb_count` `image → feature`
- `xcv_orb_count` `image → feature`
- `xcv2_lap_var` `image → feature`
- `xcv2_fast_count` `image → feature`
- `xwt_detail_energy` `image → feature`
- `xwt_packet_entropy` `image → feature`
- `xsk3_is_low_contrast` `image → feature`
- `xsk3_estimate_sigma` `image → feature`
- `xcv3_gray_hu1` `image → feature`
- `xcv3_sift_count` `image → feature`
- `xcv3_brisk_count` `image → feature`
- `xcv3_agast_count` `image → feature`
- `xcv3_lsd_count` `image → feature`

### filtering(1)
- `tf_gradient_domain_reintegrate` `image → image`

### frequency(19)
- `lowpass` `image → image`
- `highpass` (halcon: `highpass_image`) `image → image`
- `sk_butterworth` `image → image`
- `fft_image` (halcon: `fft_image`) `image → image`
- `power_real` (halcon: `power_real`) `image → image`
- `power_byte` (halcon: `power_byte`) `image → image`
- `phase_rad` (halcon: `phase_rad`) `image → image`
- `highpass_image` (halcon: `highpass_image`) `image → image`
- `bandpass_image` (halcon: `bandpass_image`) `image → image`
- `fft_image_inv` (halcon: `fft_image_inv`) `image → image`
- `fft_generic` (halcon: `fft_generic`) `image → image`
- `power_ln` (halcon: `power_ln`) `image → image`
- `rft_generic` (halcon: `rft_generic`) `image → image`
- `phase_deg` (halcon: `phase_deg`) `image → image`
- `xsp_dct` `image → image`
- `xsp_dct_lowpass` `image → image`
- `xsk2_radon` `image → image`
- `xwt_subband_tile` `image → image`
- `xwt_mra_component` `image → image`

### geometry(28)
- `rotate_img` (halcon: `rotate_image`) `image → image`
- `rescale_img` (halcon: `zoom_image_size`) `image → image`
- `affine_warp` (halcon: `affine_trans_image`) `image → image`
- `sk_swirl` (halcon: `polar_trans_image`) `image → image`
- `mirror_image` (halcon: `mirror_image`) `image → image`
- `transpose_region` (halcon: `transpose_region`) `region → region`
- `rotate_image` (halcon: `rotate_image`) `image → image`
- `zoom_image_factor` (halcon: `zoom_image_factor`) `image → image`
- `zoom_image_size` (halcon: `zoom_image_size`) `image → image`
- `affine_trans_image` (halcon: `affine_trans_image`) `image → image`
- `polar_trans_image` (halcon: `polar_trans_image`) `image → image`
- `projective_trans_image` (halcon: `projective_trans_image`) `image → image`
- `projective_trans_image_size` (halcon: `projective_trans_image_size`) `image → image`
- `projective_trans_region` (halcon: `projective_trans_region`) `region → region`
- `polar_trans_image_inv` (halcon: `polar_trans_image_inv`) `image → image`
- `affine_trans_image_size` (halcon: `affine_trans_image_size`) `image → image`
- `polar_trans_image_ext` (halcon: `polar_trans_image_ext`) `image → image`
- `affine_trans_region` (halcon: `affine_trans_region`) `region → region`
- `mirror_region` (halcon: `mirror_region`) `region → region`
- `zoom_region` (halcon: `zoom_region`) `region → region`
- `polar_trans_region_inv` (halcon: `polar_trans_region_inv`) `region → region`
- `xpil_offset` `image → image`
- `xcv2_warp_logpolar` `image → image`
- `it_add_image_border` (halcon: `add_image_border`) `image → image`
- `it_crop_part` (halcon: `crop_part`) `image → image`
- `it_crop_rectangle1` (halcon: `crop_rectangle1`) `image → image`
- `it_change_format` (halcon: `change_format`) `image → image`
- `tf_log_polar` `image → image`

### gray(41)
- `gamma` (halcon: `pow_image`) `image → image`
- `invert` (halcon: `invert_image`) `image → image`
- `scale_clip` (halcon: `scale_image`) `image → image`
- `equalize` (halcon: `equ_histo_image`) `image → image`
- `sigmoid` (halcon: `scale_image_max`) `image → image`
- `clahe` `image → image`
- `sk_adapthist` `image → image`
- `sk_enhance_contrast` `image → image`
- `sk_autolevel` (halcon: `scale_image_max`) `image → image`
- `sk_adjust_log` (halcon: `log_image`) `image → image`
- `cv_clahe` `image → image`
- `cv_trunc` (halcon: `scale_image`) `image → image`
- `gamma_image` (halcon: `gamma_image`) `image → image`
- `pow_image` (halcon: `pow_image`) `image → image`
- `invert_image` (halcon: `invert_image`) `image → image`
- `scale_image` (halcon: `scale_image`) `image → image`
- `equ_histo_image` (halcon: `equ_histo_image`) `image → image`
- `illuminate` (halcon: `illuminate`) `image → image`
- `scale_image_max` (halcon: `scale_image_max`) `image → image`
- `equ_histo_image_rect` (halcon: `equ_histo_image_rect`) `image → image`
- `bit_not` (halcon: `bit_not`) `image → image`
- `monotony` (halcon: `monotony`) `image → image`
- `xcv_detail_enhance` `image → image`
- `xpil_edge_enhance` `image → image`
- `xpil_detail` `image → image`
- `xpil_posterize` `image → image`
- `xpil_solarize` `image → image`
- `xpil_autocontrast` `image → image`
- `xpil_contrast` `image → image`
- `xsp_detrend_flatten` `image → image`
- `xsk3_rank_subtract_mean` `image → image`
- `xsk3_rank_equalize` `image → image`
- `xsk3_integral_image` `image → image`
- `xkor_clahe` `image → image`
- `f2_lut_trans` (halcon: `lut_trans`) `image → image`
- `f2_expand_domain` (halcon: `expand_domain_gray`) `image → image`
- `f2_bit_slice` (halcon: `bit_slice`) `image → image`
- `it_bit_lshift` (halcon: `bit_lshift`) `image → image`
- `it_bit_rshift` (halcon: `bit_rshift`) `image → image`
- `it_bit_mask` (halcon: `bit_mask`) `image → image`
- `it_convert_image_type` (halcon: `convert_image_type`) `image → image`

### halcon_ext(81)
- `hx_gen_circle` (halcon: `gen_circle`) `image → region`
- `hx_gen_ellipse` (halcon: `gen_ellipse`) `image → region`
- `hx_gen_rectangle2` (halcon: `gen_rectangle2`) `image → region`
- `hx_gen_checker_region` (halcon: `gen_checker_region`) `image → region`
- `hx_gen_grid_region` (halcon: `gen_grid_region`) `image → region`
- `hx_gabor` (halcon: `convol_gabor`) `image → image`
- `hx_fit_surface1` (halcon: `fit_surface_first_order`) `image → image`
- `hx_fit_surface2` (halcon: `fit_surface_second_order`) `image → image`
- `hx_cooc_feature` (halcon: `cooc_feature_image`) `image → feature`
- `hx_full_domain` (halcon: `full_domain`) `image → region`
- `hx_mean_shape` (halcon: `mean_image_shape`) `image → image`
- `hx_close_edges` (halcon: `close_edges`) `image → image`
- `hx_close_edges_length` (halcon: `close_edges_length`) `image → image`
- `hx_expand_region` (halcon: `expand_region`) `region → region`
- `hx_region_to_mean` (halcon: `region_to_mean`) `image → image`
- `hx_nonmax_dir` (halcon: `nonmax_suppression_dir`) `image → image`
- `hx_char_threshold` (halcon: `char_threshold`) `image → region`
- `hx_histo_to_thresh` (halcon: `histo_to_thresh`) `image → region`
- `hx_gen_lowpass` (halcon: `gen_lowpass`) `image → image`
- `hx_gen_highpass` (halcon: `gen_highpass`) `image → image`
- `hx_gen_bandpass` (halcon: `gen_bandpass`) `image → image`
- `hx_erosion1` (halcon: `erosion1`) `region → region`
- `hx_dilation1` (halcon: `dilation1`) `region → region`
- `hx_opening` (halcon: `opening`) `region → region`
- `hx_closing` (halcon: `closing`) `region → region`
- `hx_dilation2` (halcon: `dilation2`) `region → region`
- `hx_gen_disc_se` (halcon: `gen_disc_se`) `image → region`
- `hx_gen_circle_sector` (halcon: `gen_circle_sector`) `image → region`
- `hx_gen_ellipse_sector` (halcon: `gen_ellipse_sector`) `image → region`
- `hx_gen_empty_region` (halcon: `gen_empty_region`) `image → region`
- `hx_clip_region_rel` (halcon: `clip_region_rel`) `region → region`
- `hx_gen_bandfilter` (halcon: `gen_bandfilter`) `image → image`
- `hx_gen_derivative_filter` (halcon: `gen_derivative_filter`) `image → image`
- `hx_fill_interlace` (halcon: `fill_interlace`) `image → image`
- `hx_shade_height_field` (halcon: `shade_height_field`) `image → image`
- `hx_plane_deviation` (halcon: `plane_deviation`) `image → image`
- `hx_detect_edge_segments` (halcon: `detect_edge_segments`) `image → region`
- `hx_gen_image_proto` (halcon: `gen_image_proto`) `image → image`
- `hx_get_domain` (halcon: `get_domain`) `image → region`
- `hx_region_to_label` (halcon: `region_to_label`) `image → image`
- `hx_rectangle1_domain` (halcon: `rectangle1_domain`) `image → region`
- `hx_lowlands` (halcon: `lowlands`) `image → region`
- `hx_plateaus_center` (halcon: `plateaus_center`) `image → region`
- `hx_move_region` (halcon: `move_region`) `region → region`
- `hx_split_skeleton_region` (halcon: `split_skeleton_region`) `region → region`
- `hx_test_region_point` (halcon: `test_region_point`) `region → feature`
- `hx_test_region_points` (halcon: `test_region_points`) `region → feature`
- `hx_sort_contours` (halcon: `sort_contours_xld`) `contour → contour`
- `hx_clip_contours` (halcon: `clip_contours_xld`) `contour → contour`
- `hx_clip_end_points` (halcon: `clip_end_points_contours_xld`) `contour → contour`
- `hx_smallest_circle_xld` (halcon: `smallest_circle_xld`) `contour → feature`
- `hx_smallest_rect1_xld` (halcon: `smallest_rectangle1_xld`) `contour → feature`
- `hx_test_closed_xld` (halcon: `test_closed_xld`) `contour → feature`
- `hx_regress_contours` (halcon: `regress_contours_xld`) `contour → feature`
- `hx_moments_any_xld` (halcon: `moments_any_xld`) `contour → feature`
- `hx_split_contours` (halcon: `split_contours_xld`) `contour → contour`
- `hx_gen_parallel_contour` (halcon: `gen_parallel_contour_xld`) `contour → contour`
- `hx_fit_circle_contour` (halcon: `fit_circle_contour_xld`) `contour → feature`
- `hx_fit_ellipse_contour` (halcon: `fit_ellipse_contour_xld`) `contour → feature`
- `hx_fit_rectangle2_contour` (halcon: `fit_rectangle2_contour_xld`) `contour → feature`
- `hx_smallest_rect2_xld` (halcon: `smallest_rectangle2_xld`) `contour → feature`
- `hx_crop_contours` (halcon: `crop_contours_xld`) `contour → contour`
- `hx_dist_ellipse_contour` (halcon: `dist_ellipse_contour_xld`) `contour → feature`
- `hx_test_self_intersect` (halcon: `test_self_intersection_xld`) `contour → feature`
- `hx_union_adjacent` (halcon: `union_adjacent_contours_xld`) `contour → contour`
- `hx_polar_trans_inv` (halcon: `polar_trans_contour_xld_inv`) `contour → contour`
- `hx_select_xld_point` (halcon: `select_xld_point`) `contour → contour`
- `hx_estimate_tilt_lr` (halcon: `estimate_tilt_lr`) `image → feature`
- `hx_estimate_tilt_zc` (halcon: `estimate_tilt_zc`) `image → feature`
- `hx_estimate_sl_al_lr` (halcon: `estimate_sl_al_lr`) `image → feature`
- `hx_estimate_sl_al_zc` (halcon: `estimate_sl_al_zc`) `image → feature`
- `hx_estimate_al_am` (halcon: `estimate_al_am`) `image → feature`
- `hx_add_noise_contour` (halcon: `add_noise_white_contour_xld`) `contour → contour`
- `hx_radial_distort_contour` (halcon: `change_radial_distortion_contours_xld`) `contour → contour`
- `hx_dist_ellipse_points` (halcon: `dist_ellipse_contour_points_xld`) `contour → feature`
- `hx_dist_rect2_points` (halcon: `dist_rectangle2_contour_points_xld`) `contour → feature`
- `hx_distance_pc` (halcon: `distance_pc`) `contour → feature`
- `hx_disparity_to_xyz` (halcon: `disparity_image_to_xyz`) `image → image`
- `hx_distance_pr` (halcon: `distance_pr`) `region → feature`
- `hx_distance_sc` (halcon: `distance_sc`) `contour → feature`
- `hx_fuzzy_measure_pairs` (halcon: `fuzzy_measure_pairs`) `image → feature`

### intensity-transform(1)
- `xmh_soft` `image → image`

### macro(4)
- `macro_denoise` `image → image`
- `macro_edge` `image → region`
- `macro_binarize` `image → image`
- `macro_vol_denoise` `volume → volume`

### matching(2)
- `ncc_locate` (halcon: `find_ncc_model`) `image → match`
- `shape_locate` (halcon: `find_shape_model`) `image → match`

### measure1d(5)
- `m1_measure_projection` (halcon: `measure_projection`) `image → feature`
- `m1_measure_pos` (halcon: `measure_pos`) `image → contour`
- `m1_measure_thresh` (halcon: `measure_thresh`) `image → feature`
- `m1_measure_pairs` (halcon: `measure_pairs`) `image → feature`
- `m1_fuzzy_measure_pos` (halcon: `fuzzy_measure_pos`) `image → contour`

### misc(1)
- `identity` (halcon: `copy_image`) `any → any`

### morphology(33)
- `gerode` (halcon: `gray_erosion`) `image → image`
- `gdilate` (halcon: `gray_dilation`) `image → image`
- `gopen` (halcon: `gray_opening`) `image → image`
- `gclose` (halcon: `gray_closing`) `image → image`
- `tophat` (halcon: `gray_tophat`) `image → image`
- `bothat` (halcon: `gray_bothat`) `image → image`
- `morph_grad` (halcon: `gray_range_rect`) `image → image`
- `sk_area_opening` `image → image`
- `cv_open` (halcon: `gray_opening`) `image → image`
- `cv_close` (halcon: `gray_closing`) `image → image`
- `cv_tophat` (halcon: `gray_tophat`) `image → image`
- `cv_gradient` (halcon: `gray_range_rect`) `image → image`
- `cv_blackhat` (halcon: `gray_bothat`) `image → image`
- `cv_erode` (halcon: `gray_erosion`) `image → image`
- `cv_dilate` (halcon: `gray_dilation`) `image → image`
- `gray_erosion` (halcon: `gray_erosion`) `image → image`
- `gray_dilation` (halcon: `gray_dilation`) `image → image`
- `gray_opening` (halcon: `gray_opening`) `image → image`
- `gray_closing` (halcon: `gray_closing`) `image → image`
- `gray_opening_shape` (halcon: `gray_opening_shape`) `image → image`
- `gray_closing_shape` (halcon: `gray_closing_shape`) `image → image`
- `gray_tophat` (halcon: `gray_tophat`) `image → image`
- `gray_bothat` (halcon: `gray_bothat`) `image → image`
- `gray_erosion_shape` (halcon: `gray_erosion_shape`) `image → image`
- `gray_dilation_shape` (halcon: `gray_dilation_shape`) `image → image`
- `gray_opening_rect` (halcon: `gray_opening_rect`) `image → image`
- `gray_closing_rect` (halcon: `gray_closing_rect`) `image → image`
- `xsk2_reconstruction` `image → image`
- `xsk2_diameter_opening` `image → image`
- `xsk3_area_closing` `image → image`
- `xsk3_diameter_closing` `image → image`
- `f2_gray_skeleton` (halcon: `gray_skeleton`) `image → image`
- `f2_gray_inside` (halcon: `gray_inside`) `image → image`

### morphology/markers(1)
- `xmh_regmin` `image → region`

### noise(2)
- `add_noise_white` (halcon: `add_noise_white`) `image → image`
- `add_noise_distribution` (halcon: `add_noise_distribution`) `image → image`

### physics(6)
- `ph_perona_malik` `image → image`
- `ph_coherence_enhancing_diffusion` `image → image`
- `ph_reaction_diffusion` `image → image`
- `ph_heat_flow` `image → image`
- `ph_mean_curvature_motion` `image → image`
- `ph_total_variation_flow` `image → image`

### rank(23)
- `median` (halcon: `median_image`) `image → image`
- `min_filter` (halcon: `gray_erosion_rect`) `image → image`
- `max_filter` (halcon: `gray_dilation_rect`) `image → image`
- `percentile` (halcon: `rank_image`) `image → image`
- `sk_median_disk` (halcon: `median_image`) `image → image`
- `cv_median` (halcon: `median_image`) `image → image`
- `median_image` (halcon: `median_image`) `image → image`
- `median_rect` (halcon: `median_rect`) `image → image`
- `median_separate` (halcon: `median_separate`) `image → image`
- `gray_erosion_rect` (halcon: `gray_erosion_rect`) `image → image`
- `gray_dilation_rect` (halcon: `gray_dilation_rect`) `image → image`
- `gray_range_rect` (halcon: `gray_range_rect`) `image → image`
- `rank_image` (halcon: `rank_image`) `image → image`
- `rank_rect` (halcon: `rank_rect`) `image → image`
- `trimmed_mean` (halcon: `trimmed_mean`) `image → image`
- `eliminate_min_max` (halcon: `eliminate_min_max`) `image → image`
- `median_weighted` (halcon: `median_weighted`) `image → image`
- `mean_sp` (halcon: `mean_sp`) `image → image`
- `eliminate_sp` (halcon: `eliminate_sp`) `image → image`
- `dual_rank` (halcon: `dual_rank`) `image → image`
- `xpil_mode_filter` `image → image`
- `xsk2_rank_geomean` `image → image`
- `xkor_median` `image → image`

### region(76)
- `reg_erode` (halcon: `erosion_circle`) `region → region`
- `reg_dilate` (halcon: `dilation_circle`) `region → region`
- `reg_open` (halcon: `opening_circle`) `region → region`
- `reg_close` (halcon: `closing_circle`) `region → region`
- `fill_holes` (halcon: `fill_up`) `region → region`
- `select_largest` (halcon: `select_shape_std`) `region → region`
- `remove_small` (halcon: `select_shape`) `region → region`
- `invert_region` (halcon: `complement`) `region → region`
- `dist_transform` (halcon: `distance_transform`) `region → image`
- `region_boundary` (halcon: `boundary`) `region → region`
- `convex_fill` (halcon: `shape_trans`) `region → region`
- `sk_skeleton` (halcon: `skeleton`) `region → region`
- `sk_medial` (halcon: `skeleton`) `region → region`
- `sk_convex` (halcon: `shape_trans`) `region → region`
- `sk_thin` (halcon: `thinning`) `region → region`
- `sk_remove_holes` (halcon: `fill_up`) `region → region`
- `sk_clear_border` `region → region`
- `sk_find_boundaries` (halcon: `boundary`) `region → region`
- `cv_dist` (halcon: `distance_transform`) `region → image`
- `erosion_circle` (halcon: `erosion_circle`) `region → region`
- `dilation_circle` (halcon: `dilation_circle`) `region → region`
- `opening_circle` (halcon: `opening_circle`) `region → region`
- `closing_circle` (halcon: `closing_circle`) `region → region`
- `erosion_rectangle1` (halcon: `erosion_rectangle1`) `region → region`
- `dilation_rectangle1` (halcon: `dilation_rectangle1`) `region → region`
- `opening_rectangle1` (halcon: `opening_rectangle1`) `region → region`
- `closing_rectangle1` (halcon: `closing_rectangle1`) `region → region`
- `fill_up` (halcon: `fill_up`) `region → region`
- `boundary` (halcon: `boundary`) `region → region`
- `skeleton` (halcon: `skeleton`) `region → region`
- `thinning` (halcon: `thinning`) `region → region`
- `shape_trans` (halcon: `shape_trans`) `region → region`
- `select_shape_std` (halcon: `select_shape_std`) `region → region`
- `select_shape` (halcon: `select_shape`) `region → region`
- `distance_transform` (halcon: `distance_transform`) `region → image`
- `pruning` (halcon: `pruning`) `region → region`
- `closest_point_transform` (halcon: `closest_point_transform`) `region → image`
- `junctions_skeleton` (halcon: `junctions_skeleton`) `region → region`
- `erosion_golay` (halcon: `erosion_golay`) `region → region`
- `dilation_golay` (halcon: `dilation_golay`) `region → region`
- `opening_golay` (halcon: `opening_golay`) `region → region`
- `closing_golay` (halcon: `closing_golay`) `region → region`
- `erosion_seq` (halcon: `erosion_seq`) `region → region`
- `dilation_seq` (halcon: `dilation_seq`) `region → region`
- `morph_skeleton` (halcon: `morph_skeleton`) `region → region`
- `thinning_golay` (halcon: `thinning_golay`) `region → region`
- `thinning_seq` (halcon: `thinning_seq`) `region → region`
- `fill_up_shape` (halcon: `fill_up_shape`) `region → region`
- `remove_noise_region` (halcon: `remove_noise_region`) `region → region`
- `smallest_rectangle1` (halcon: `smallest_rectangle1`) `region → region`
- `get_region_contour` (halcon: `get_region_contour`) `region → region`
- `get_region_convex` (halcon: `get_region_convex`) `region → region`
- `xsp_chamfer_dist` `region → image`
- `xsk2_isotropic_close` `region → region`
- `xcv2_hitmiss` `region → region`
- `xsk3_rank_majority` `region → region`
- `r2_inner_circle` (halcon: `inner_circle`) `region → region`
- `r2_inner_rectangle1` (halcon: `inner_rectangle1`) `region → region`
- `r2_smallest_rectangle1` `region → region`
- `r2_smallest_circle` (halcon: `smallest_circle`) `region → region`
- `r2_smallest_rectangle2` (halcon: `smallest_rectangle2`) `region → region`
- `r2_sort_region` (halcon: `sort_region`) `region → region`
- `r2_union1` (halcon: `union1`) `region → region`
- `r2_partition_rectangle` (halcon: `partition_rectangle`) `region → region`
- `r2_runlength_features` (halcon: `runlength_features`) `region → feature`
- `r2_split_skeleton_lines` (halcon: `split_skeleton_lines`) `region → region`
- `r3_background_seg` (halcon: `background_seg`) `region → region`
- `r3_clip_region` (halcon: `clip_region`) `region → region`
- `r3_eliminate_runs` (halcon: `eliminate_runs`) `region → region`
- `r3_rank_region` (halcon: `rank_region`) `region → region`
- `r3_region_features` (halcon: `region_features`) `region → feature`
- `r3_runlength_distribution` (halcon: `runlength_distribution`) `region → feature`
- `r3_select_region_point` (halcon: `select_region_point`) `region → region`
- `r3_partition_dynamic` (halcon: `partition_dynamic`) `region → region`
- `r3_polar_trans_region` (halcon: `polar_trans_region`) `region → region`
- `r3_label_to_region` (halcon: `label_to_region`) `region → region`

### region-morphology(1)
- `xmh_majority` `region → region`

### region-transform(1)
- `xmh_bwperim` `region → region`

### restoration(12)
- `xsk_inpaint` `image → image`
- `xsk_richardson_lucy` `image → image`
- `xsk_unwrap_phase` `image → image`
- `xcv_inpaint` `image → image`
- `xsk2_wiener` `image → image`
- `xcv3_inpaint_ns` `image → image`
- `iv_richardson_lucy` `image → image`
- `iv_wiener_deconv_spatial` `image → image`
- `iv_unsharp_deblur` `image → image`
- `iv_motion_deblur` `image → image`
- `iv_backproject_superres` `image → image`
- `iv_gradient_inpaint` `image → image`

### segment(7)
- `sg_slic_superpixels` `image → region`
- `sg_felzenszwalb` `image → region`
- `sg_gmm_segment` `image → region`
- `sg_kmeans_intensity` `image → region`
- `sg_region_growing_seeded` `image → region`
- `sg_normalized_cut_2` `image → region`
- `sg_watershed_gradient` `image → region`

### segmentation(56)
- `threshold` (halcon: `threshold`) `image → region`
- `otsu` (halcon: `binary_threshold`) `image → region`
- `dyn_threshold` (halcon: `dyn_threshold`) `image → region`
- `canny` (halcon: `edges_image`) `image → region`
- `local_max` (halcon: `local_max_sub_pix`) `image → region`
- `adaptive_gauss_thresh` (halcon: `local_threshold`) `image → region`
- `sk_otsu` (halcon: `binary_threshold`) `image → region`
- `sk_li` (halcon: `binary_threshold`) `image → region`
- `sk_yen` (halcon: `binary_threshold`) `image → region`
- `sk_sauvola` (halcon: `var_threshold`) `image → region`
- `sk_niblack` (halcon: `var_threshold`) `image → region`
- `sk_canny` (halcon: `edges_image`) `image → region`
- `sk_felzenszwalb` `image → region`
- `sk_slic` `image → region`
- `sk_chan_vese` `image → region`
- `sk_local_maxima` (halcon: `local_max`) `image → region`
- `sk_hysteresis` (halcon: `hysteresis_threshold`) `image → region`
- `cv_otsu` (halcon: `binary_threshold`) `image → region`
- `cv_adaptive_mean` (halcon: `dyn_threshold`) `image → region`
- `cv_adaptive_gauss` (halcon: `local_threshold`) `image → region`
- `cv_canny` (halcon: `edges_image`) `image → region`
- `h_threshold` (halcon: `threshold`) `image → region`
- `binary_threshold` (halcon: `binary_threshold`) `image → region`
- `auto_threshold` (halcon: `auto_threshold`) `image → region`
- `dyn_threshold` (halcon: `dyn_threshold`) `image → region`
- `var_threshold` (halcon: `var_threshold`) `image → region`
- `local_threshold` (halcon: `local_threshold`) `image → region`
- `hysteresis_threshold` (halcon: `hysteresis_threshold`) `image → region`
- `edges_image` (halcon: `edges_image`) `image → region`
- `watersheds` (halcon: `watersheds`) `image → region`
- `watersheds_threshold` (halcon: `watersheds_threshold`) `image → region`
- `regiongrowing` (halcon: `regiongrowing`) `image → region`
- `local_max` (halcon: `local_max`) `image → region`
- `dual_threshold` (halcon: `dual_threshold`) `image → region`
- `segment_image_mser` (halcon: `segment_image_mser`) `image → region`
- `regiongrowing_mean` (halcon: `regiongrowing_mean`) `image → region`
- `zero_crossing` (halcon: `zero_crossing`) `image → region`
- `local_min` (halcon: `local_min`) `image → region`
- `bin_threshold` (halcon: `bin_threshold`) `image → region`
- `fast_threshold` (halcon: `fast_threshold`) `image → region`
- `nonmax_suppression_amp` (halcon: `nonmax_suppression_amp`) `image → region`
- `pouring` (halcon: `pouring`) `image → region`
- `xsk_random_walker` `image → region`
- `xsk_flood` `image → region`
- `xcv_grabcut` `image → region`
- `xcv_watershed_markers` (halcon: `watersheds`) `image → region`
- `xsk2_multiotsu` `image → image`
- `xsk2_h_maxima` `image → region`
- `xcv2_meanshift` `image → image`
- `xmh_bernsen` `image → region`
- `xsk3_rank_otsu` `image → region`
- `xsk3_h_minima` `image → region`
- `xsk3_threshold_local_median` `image → region`
- `xsk3_peak_local_max` `image → region`
- `xkor_canny` `image → region`
- `it_region_to_bin` (halcon: `region_to_bin`) `image → image`

### self-similarity(1)
- `xmh_selfmatch` `image → image`

### smoothing(48)
- `gaussian` (halcon: `gauss_filter`) `image → image`
- `mean_box` (halcon: `mean_image`) `image → image`
- `bilateral` (halcon: `bilateral_filter`) `image → image`
- `unsharp` (halcon: `emphasize`) `image → image`
- `sk_tv` `image → image`
- `sk_wavelet` `image → image`
- `sk_rolling_ball` `image → image`
- `sk_nlm` `image → image`
- `sk_tv_bregman` `image → image`
- `cv_bilateral` (halcon: `bilateral_filter`) `image → image`
- `cv_box` (halcon: `mean_image`) `image → image`
- `cv_gaussian` (halcon: `gauss_filter`) `image → image`
- `cv_nlmeans` `image → image`
- `cv_sharpen` (halcon: `emphasize`) `image → image`
- `dl_aniso_diffusion` (halcon: `anisotropic_diffusion`) `image → image`
- `dl_guided_filter` (halcon: `guided_filter`) `image → image`
- `gauss_filter` (halcon: `gauss_filter`) `image → image`
- `gauss_image` (halcon: `gauss_image`) `image → image`
- `mean_image` (halcon: `mean_image`) `image → image`
- `binomial_filter` (halcon: `binomial_filter`) `image → image`
- `smooth_image` (halcon: `smooth_image`) `image → image`
- `mean_curvature_flow` (halcon: `mean_curvature_flow`) `image → image`
- `sigma_image` (halcon: `sigma_image`) `image → image`
- `anisotropic_diffusion` (halcon: `anisotropic_diffusion`) `image → image`
- `isotropic_diffusion` (halcon: `isotropic_diffusion`) `image → image`
- `coherence_enhancing_diff` (halcon: `coherence_enhancing_diff`) `image → image`
- `bilateral_filter` (halcon: `bilateral_filter`) `image → image`
- `guided_filter` (halcon: `guided_filter`) `image → image`
- `simulate_motion` (halcon: `simulate_motion`) `image → image`
- `simulate_defocus` (halcon: `simulate_defocus`) `image → image`
- `xcv_edge_preserving` `image → image`
- `xpil_smooth_more` `image → image`
- `xpil_unsharp_mask` `image → image`
- `xsp_wiener` `image → image`
- `xsp_savgol` `image → image`
- `xsp_dct_denoise` `image → image`
- `xsp_cspline_smooth` `image → image`
- `xwt_visushrink` `image → image`
- `xwt_firm_denoise` `image → image`
- `xwt_lf_reconstruct` `image → image`
- `xsk3_rank_mean_bilateral` `image → image`
- `xcv3_denoise_tvl1` `image → image`
- `xcv3_pyr_laplacian` `image → image`
- `xkor_gaussian` `image → image`
- `xkor_bilateral` `image → image`
- `xkor_unsharp` `image → image`
- `xkor_motion_blur` `image → image`
- `f2_gauss_pyramid` (halcon: `gen_gauss_pyramid`) `image → image`

### subpix(6)
- `sp_local_max_sub_pix` `image → contour`
- `sp_local_min_sub_pix` (halcon: `local_min_sub_pix`) `image → contour`
- `sp_saddle_points_sub_pix` (halcon: `saddle_points_sub_pix`) `image → contour`
- `sp_critical_points_sub_pix` (halcon: `critical_points_sub_pix`) `image → contour`
- `sp_plateaus` (halcon: `plateaus`) `image → contour`
- `sp_lowlands_center` (halcon: `lowlands_center`) `image → contour`

### tactile(5)
- `tac_contact_mask` `image → region`
- `tac_height_from_shading` `image → image`
- `tac_surface_normal` `image → image`
- `tac_pressure_proxy` `image → image`
- `tac_shear_field` `image → image`

### texture(22)
- `std_filter` (halcon: `deviation_image`) `image → image`
- `gabor` (halcon: `gen_gabor`) `image → image`
- `sk_frangi` (halcon: `lines_gauss`) `image → image`
- `sk_meijering` (halcon: `lines_gauss`) `image → image`
- `sk_hessian` (halcon: `lines_gauss`) `image → image`
- `sk_gabor` (halcon: `gen_gabor`) `image → image`
- `sk_lbp` `image → image`
- `sk_entropy` (halcon: `entropy_image`) `image → image`
- `sk_shape_index` `image → image`
- `deviation_image` (halcon: `deviation_image`) `image → image`
- `texture_laws` (halcon: `texture_laws`) `image → image`
- `entropy_image` (halcon: `entropy_image`) `image → image`
- `gen_gabor` (halcon: `gen_gabor`) `image → image`
- `cooc_feature_matrix` (halcon: `cooc_feature_matrix`) `image → feature`
- `xsk_struct_coherence` `image → image`
- `xsk_meijering` `image → image`
- `xsk_sato` `image → image`
- `xsp_hilbert_env` `image → image`
- `xsk2_hog` `image → image`
- `f2_symmetry` (halcon: `symmetry`) `image → image`
- `tf_census_transform` `image → image`
- `tf_rank_transform` `image → image`

### texture-feature(1)
- `xmh_pftas` `image → feature`

### texture/shape-feature(1)
- `xmh_zernike` `image → feature`

### tomography(5)
- `tm_radon_forward` `image → image`
- `tm_fbp_reconstruct` `image → image`
- `tm_sart_reconstruct` `image → image`
- `tm_backproject_unfiltered` `image → image`
- `tm_sinogram_denoise` `image → image`

### transform(3)
- `xmh_haar` `image → image`
- `xmh_daubechies` `image → image`
- `tf_radon_sinogram` `image → image`

### xldgeom(10)
- `xg_moments` (halcon: `moments_points_xld`) `contour → feature`
- `xg_area_center` (halcon: `area_center_points_xld`) `contour → feature`
- `xg_eccentricity` (halcon: `eccentricity_points_xld`) `contour → feature`
- `xg_orientation` (halcon: `orientation_points_xld`) `contour → feature`
- `xg_elliptic_axis` (halcon: `elliptic_axis_points_xld`) `contour → feature`
- `xg_height_width_ratio` (halcon: `height_width_ratio_xld`) `contour → feature`
- `xg_regress_contours` `contour → feature`
- `xg_clip_contours` `contour → contour`
- `xg_gen_polygons` (halcon: `gen_polygons_xld`) `contour → contour`
- `xg_crop_contours` `contour → contour`

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

