"""examples3d — the worked-example gallery for Fullseye's 3-D vision toolkit.

The 3-D operators (``ops3d`` — 230 typed ops) solve real Physical-AI perception
problems, but an operator no one can *find or run* is invisible. This module is the
discoverable index: every entry is a **self-contained, self-asserting runnable
script** under ``examples_3d/`` that loads data, calls the toolkit, prints a
ground-truth check and asserts it. Studio's "3-D Examples" gallery and
``docs/EXAMPLES_3D.md`` both source their list from here, and :func:`validate`
runs every script so the gallery only ever advertises examples that actually work.

Varied data provenances, so the examples run on genuine shapes, not just spheres:

  * ``synthetic``     — controllable synthetic data with exact ground truth.
  * ``procedural``    — shapes built from the toolkit's own generators (e.g. a
                        27-bone hand from capsule SDFs) — no data file, always runs.
  * ``skeleton_ct``   — a hand-skeleton X-ray-CT phantom voxelised from the real
                        MS-Human-700 anatomical bone meshes (volumetric / tomography).
  * ``itokawa``       — a decimated surface cloud of asteroid 25143 Itokawa from the
                        public-domain Gaskell shape model (JAXA Hayabusa; see
                        ``studio_assets/sample_3d/ATTRIBUTION.md``).
  * ``download``      — a real mesh fetched on demand by the opt-in downloader
                        (``fullseye samples``); the example SKIPs (exit 0) until the
                        user downloads it, so ``validate`` stays network-free.

Usage::

    import examples3d
    examples3d.names()                      # every example id
    examples3d.by_task()["registration"]    # ids grouped by task
    print(examples3d.code("cad_to_scan"))   # the runnable source
    examples3d.validate()                   # run all; returns {id: (ok, note)}

Each script is also runnable directly::

    PYTHONPATH=<repo> py -3.11 examples_3d/cad_to_scan.py
"""
from __future__ import annotations

import os
import subprocess
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(_ROOT, "examples_3d")

# id -> metadata. `name`/`summary` are plain-language (what real problem it solves);
# `task` groups the gallery; `data` is the provenance (synthetic / skeleton_ct / itokawa).
# Every id maps to examples_3d/<id>.py. All entries are verified by :func:`validate`.
EXAMPLES = [
    # -- registration ------------------------------------------------------------ #
    {"id": "cad_to_scan", "task": "registration", "data": "synthetic",
     "name": "CADモデルをノイズ入り3Dスキャンに位置合わせ",
     "summary": "初期姿勢なしで CAD 設計形状を実物スキャン点群に合わせ、置かれた向きと位置を復元する(FPFH+RANSACで粗く→ICPでセンサノイズ床まで)。"},
    {"id": "auto_register", "task": "registration", "data": "synthetic",
     "name": "手法を自動選択する点群登録",
     "summary": "2点群の近さを見て、近ければ ICP・大きく離れていれば FPFH+ICP を自動選択する(手法指定不要)。"},
    {"id": "reg_eval", "task": "registration", "data": "synthetic",
     "name": "登録品質の評価(recall/RMSE/inlier)",
     "summary": "登録結果が成功か失敗かを inlier率・RMSE・recall で定量化。対応ゼロでは NaN を返し捏造しない。"},
    {"id": "two_view_pose", "task": "registration", "data": "synthetic",
     "name": "2視点からの相対カメラ姿勢(SfM初期化)",
     "summary": "2枚の画像の対応点から基礎/基本行列を解き、相対カメラ姿勢と3D点を復元する(単眼SfM/VOの初手)。"},
    {"id": "bundle_adjust", "task": "registration", "data": "synthetic",
     "name": "N視点バンドル調整による精緻化",
     "summary": "全カメラ姿勢と3D構造を再投影誤差最小で同時最適化し、摂動から機械精度へ回復する。"},
    {"id": "pose_graph_slam", "task": "registration", "data": "synthetic",
     "name": "ループ閉じ込みのポーズグラフSLAMバックエンド",
     "summary": "ノイズ入りオドメトリ+ループ閉じ辺を最適化し、蓄積したドリフトを低減する。"},
    # -- metrology --------------------------------------------------------------- #
    {"id": "plane_flatness", "task": "metrology", "data": "synthetic",
     "name": "平面度メトロロジー(基準面からの偏差)",
     "summary": "点群に平面を当て、基準面からの偏差=平面度を測る。既知の膨らみ高さと一致することで検証。"},
    {"id": "roundness", "task": "metrology", "data": "synthetic",
     "name": "真球度/丸さ検査",
     "summary": "点群に球を当て、真球からの偏差=真球度を測る。完全な球ほど偏差が小さいことを確認。"},
    {"id": "ransac_prim", "task": "metrology", "data": "synthetic",
     "name": "30%外れ値下での頑健プリミティブ適合",
     "summary": "平面/球/円柱を RANSAC で当て、外れ値30%が混じってもパラメータを正しく復元する。"},
    # -- depth ------------------------------------------------------------------- #
    {"id": "plane_sweep_depth", "task": "depth", "data": "synthetic",
     "name": "2視点プレーンスイープ・ステレオ深度",
     "summary": "既知カメラの2画像から、深度平面を掃引して photo-consistency 最小の深度を画素ごとに選ぶ。"},
    {"id": "depth_denoise", "task": "depth", "data": "synthetic",
     "name": "エッジ保存の深度デノイズ+穴埋め",
     "summary": "段差を跨がずにノイズを平滑化し、浅い穴を調和補間で埋める(深い穴はNaNのまま残す)。"},
    # -- reconstruction / modeling ---------------------------------------------- #
    {"id": "denoise_evolution", "task": "reconstruction", "data": "synthetic",
     "name": "進化探索で見つけた点群デノイズ・パイプライン",
     "summary": "外れ値除去・平滑化・間引きの順番を遺伝的アルゴリズムに探させ、無処理と人手の定番を上回る。"},
    {"id": "tsdf_fusion_demo", "task": "reconstruction", "data": "synthetic",
     "name": "複数深度フレームをTSDFで融合し表面抽出",
     "summary": "複数視点の深度観測を TSDF に融合し、単一観測よりノイズに頑健な表面を得る。"},
    {"id": "sdf_csg", "task": "modeling", "data": "synthetic",
     "name": "SDFのCSG合成(和/差)でソリッドを作りメッシュ化",
     "summary": "符号付き距離場の集合演算(球∪箱−小球)で陰関数ソリッドを作り、等値面をメッシュへ。"},
    # -- features ---------------------------------------------------------------- #
    {"id": "curvature_grasp", "task": "features", "data": "synthetic",
     "name": "主曲率・形状指数による把持アフォーダンス",
     "summary": "点群の主曲率と形状指数から、球・円柱・鞍点を識別する(把持面の当たり判定)。"},
    {"id": "symmetry", "task": "features", "data": "synthetic",
     "name": "反射・回転対称性の検出",
     "summary": "点群の反射面と回転対称の位数を chamfer 採点で検出する。"},
    {"id": "shape_retrieval", "task": "features", "data": "synthetic",
     "name": "大域記述子(D2/A3)による形状検索",
     "summary": "距離分布 D2・角分布 A3 の大域記述子で、回転しても同形状は近く・異形状は遠く照合する。"},
    {"id": "motion_seg", "task": "motion", "data": "synthetic",
     "name": "動的シーンの剛体運動セグメンテーション",
     "summary": "2時刻の点群から、別々に動く剛体ごとに分割する。無相関ノイズでは剛体を捏造しない。"},
    # -- skeleton CT (real anatomical bone geometry, volumetric) ----------------- #
    {"id": "ct_hand_radiograph", "task": "depth", "data": "skeleton_ct",
     "name": "骨格CTからX線ラジオグラフ(DRR)を合成",
     "summary": "手骨のCT密度ボリュームを厚み方向に積算し、2次元の手のX線像(DRR)を合成する。"},
    {"id": "ct_bone_segmentation", "task": "modeling", "data": "skeleton_ct",
     "name": "CTボリュームから骨をセグメンテーションし、接触骨を分離して計数・体積計測",
     "summary": "骨を閾値化し、関節で繋がる指骨を収縮で分離してから連結成分で数え、体積を測る(閾値内外の密度コントラストで検証)。"},
    {"id": "ct_surface_extraction", "task": "modeling", "data": "skeleton_ct",
     "name": "CTボリュームから骨表面メッシュを抽出(marching cubes)",
     "summary": "CTボリュームに marching cubes をかけ、骨表面を三角メッシュ化する(3Dプリント/FEA向け)。"},
    {"id": "ct_sparse_view_recon", "task": "depth", "data": "skeleton_ct",
     "name": "低線量スパースビューCT再構成(radon→SART)",
     "summary": "指の断面をX線投影し、SART(反復)とFBPで再構成する。低線量ゆえの控えめな品質を正直に評価。"},
    # -- Itokawa asteroid (real Gaskell shape model, public domain) -------------- #
    {"id": "itokawa_pose_canonical", "task": "registration", "data": "itokawa",
     "name": "小惑星の姿勢を主成分で正準化",
     "summary": "不明な向きで届いた小惑星形状を、慣性主軸で形状固有の正準姿勢へ整える(カタログ化・比較用)。"},
    {"id": "itokawa_self_register", "task": "registration", "data": "itokawa",
     "name": "未知姿勢で置かれた小惑星スキャンの位置合わせ",
     "summary": "未知の探査機姿勢で撮った小惑星スキャンを ICP で基準形状に戻す。不規則形状は球と違い登録できる。"},
    {"id": "itokawa_curvature", "task": "features", "data": "itokawa",
     "name": "小惑星表面の曲率解析(尾根・クレーターの検出)",
     "summary": "表面の主曲率・曲率度・形状指数を求め、平坦部と尾根/窪みを仕分ける(値が実在表面の幾何であることを近傍相関で確認)。"},
    {"id": "itokawa_shape_match", "task": "features", "data": "itokawa",
     "name": "chamfer距離による形状照合",
     "summary": "chamfer 距離で「同一の天体か別物か」を数値判定する(自身の回転コピーは近く・同大の球は遠い)。"},
    {"id": "itokawa_symmetry_honest", "task": "features", "data": "itokawa",
     "name": "対称性検出(正直な結果:小惑星は非対称)",
     "summary": "反射対称スコアを小惑星と対称な楕円体で比較。ラブルパイル小惑星は非対称=検出器が正しく低スコアを返す。"},
    # -- pose estimation --------------------------------------------------------- #
    {"id": "pose_estimation", "task": "pose_estimation", "data": "synthetic",
     "name": "外れ値ありの3D-2D対応からカメラ6自由度姿勢を推定(PnP+RANSAC)",
     "summary": "既知寸法の箱の3D-2D対応(30%外れ値・0.5px雑音)から pnp_ransac で姿勢復元。回転<2度・並進<2%で、恒等姿勢や素のDLTを明確に上回る。"},
    # -- segmentation ------------------------------------------------------------ #
    {"id": "object_segmentation", "task": "segmentation", "data": "synthetic",
     "name": "ビンピッキング: 台平面除去→物体クラスタリング",
     "summary": "地面平面を plane_segmentation で剥がし、残りを euclidean_cluster で3物体に分離。クラスタ数・重心が真値一致、全点1クラスタ扱いの零点を上回る。"},
    # -- mapping ----------------------------------------------------------------- #
    {"id": "occupancy_esdf", "task": "mapping", "data": "synthetic",
     "name": "占有格子+ESDFで連続クリアランスを問い合わせ",
     "summary": "部屋点群から occupancy_grid→esdf を作り、自由空間点で最近接障害物までの連続距離を query_distance。占有0/1のみの零点を約39倍上回る(衝突回避マージン判定)。"},
    # -- shape fitting ----------------------------------------------------------- #
    {"id": "superquadric_fit", "task": "shape_fitting", "data": "synthetic",
     "name": "点群から角丸ブロックをスーパー楕円体で当てはめ",
     "summary": "既知スーパー楕円体からの雑音点群を fit_superquadric で復元(半径5%以内・内外分類>95%)。球1個を当てた残差を大きく下回る(把持点判定向け)。"},
    # -- motion ------------------------------------------------------------------ #
    {"id": "scene_flow_rigid", "task": "motion", "data": "synthetic",
     "name": "剛体シーンフロー(既知R,tと密フィールドの復元)",
     "summary": "点群を既知剛体変換で動かし rigid_flow で復元(回転<1度・並進<1voxel)。smooth_flow が生NN流のEPEを約半分に、residual_flow は剛体部でノイズ床。"},
    # -- shape descriptors ------------------------------------------------------- #
    {"id": "moment_invariants", "task": "shape_descriptors", "data": "synthetic",
     "name": "3Dモーメント不変量(剛体+一様スケールに不変)",
     "summary": "点群に既知の平行移動・回転・一様スケールを掛けても moment_invariants はほぼ不変で、別形状とは明確に区別。生モーメントは同変換で大きく変動。"},
    # -- shape analysis ---------------------------------------------------------- #
    {"id": "medial_topology", "task": "shape_analysis", "data": "synthetic",
     "name": "中軸骨格と位相署名で形状を区別",
     "summary": "中実円柱の芯を skeletonize_vol/medial_axis_points で抽出(既知中心軸上)、topology_signature+medial_match でトーラス(genus1)を球/円柱と区別。ランダム署名の零点を上回る。"},
    # -- surface from contours(表現変換 2D輪郭→3D)------------------------------ #
    {"id": "contours_to_surface", "task": "reconstruction", "data": "synthetic",
     "name": "複数断層の2D輪郭を積層して3D曲面(メッシュ)に",
     "summary": "各スライスの閉輪郭を塗って voxel 積層→marching cubes で曲面メッシュ化。頂点は球面に乗り体積も一致(断面一定=円柱仮定は1.5倍過大)。輪郭→領域→voxel→メッシュの表現変換。"},
    {"id": "contours_to_terrain", "task": "reconstruction", "data": "synthetic",
     "name": "等高線(標高付き輪郭)から地形の高さ場(DEM)を復元",
     "summary": "等高線点(x,y,標高)を fit_poly_surface でサーフェス当てはめし DEM 格子へ展開。線の間も内挿し全域RMSEが最近傍等高線の階段近似を桁違いに下回る(GIS/測量)。"},
    # -- registration / sensing / reconstruction(バッチ2)------------------------ #
    {"id": "gicp_register", "task": "registration", "data": "synthetic",
     "name": "平面主体スキャンのGICP位置合わせ",
     "summary": "床+直交2壁のコーナーを既知変換で動かし gicp(共分散重みマハラノビス)で復元。回転<1度、平面が滑る状況で点対点ICPを約6.5倍上回る。"},
    {"id": "lidar_projection", "task": "range_sensing", "data": "synthetic",
     "name": "360度点群⇄距離画像の往復(球面投影)",
     "summary": "project_spherical→unproject_spherical の往復で形状を保存(誤差<voxel)。奥行きを潰す平面正射影より55倍良い。"},
    {"id": "photometric_stereo", "task": "shape_from_shading", "data": "synthetic",
     "name": "複数光源の陰影から法線・高さを復元(フォトメトリックステレオ)",
     "summary": "既知光源方向の陰影群から photometric_stereo で法線(誤差0.88度)、integrate_normals で高さ(相関1.0)。単一輝度=高さの素朴推定を大きく上回る。"},
    {"id": "range_image", "task": "range_sensing", "data": "synthetic",
     "name": "深度画像から法線・遮蔽エッジを読む",
     "summary": "organized 深度から法線(平面で0度誤差)と手前/奥の段差エッジを検出。一次勾配しきい値は平面の傾きを誤検出、二次差分の occlusion_edges は誤検出0。"},
    {"id": "structured_light", "task": "structured_light", "data": "synthetic",
     "name": "位相シフト縞投影で高さを復元",
     "summary": "縞合成→wrapped_phase→unwrap_phase_2d→decode で高さ(RMSE 0.63%)。位相アンラップ無しは2π跳びで88%誤る。"},
    {"id": "space_carving", "task": "reconstruction", "data": "synthetic",
     "name": "多視点シルエットから visual hull を彫る",
     "summary": "既知形状を複数の既知視点で synthesize_silhouette→carve し visual_hull を得る(recall 1.0)。1視点は柱状に過大、多視点で真形状へ収束。"},
    {"id": "nonrigid_deform", "task": "deformable_registration", "data": "synthetic",
     "name": "TPSベースの非剛体位置合わせ",
     "summary": "既知TPS曲げ変形をかけた標的へ register_nonrigid で位置合わせし残差をノイズ床へ。剛体ICPは曲げを吸収できず残差が大きい(制御点で tps_warp が厳密に写ることも確認)。"},
    {"id": "geodesic_distance", "task": "shape_analysis", "data": "synthetic",
     "name": "曲面上の測地距離と最遠点サンプリング",
     "summary": "球面点群で kNN グラフ上の geodesic_distances が大円距離と一致(誤差1.7%)、farthest_point_sampling で均等な代表点。直線ユークリッド距離は曲面上で系統的に過小。"},
    # -- volumetric / point-cloud primitives(バッチ3)---------------------------- #
    {"id": "oriented_normals", "task": "features", "data": "synthetic",
     "name": "点群に大域整合した外向き法線を付与(PCA推定→MST向き伝播)",
     "summary": "符号未定のPCA法線を Hoppe MST で外向きに揃える。球面サンプルで生法線の外向き一致0.50(コイン投げ)を向き付け1.00へ改善、接平面精度1.00。退化入力は捏造せず拒否。"},
    {"id": "shape_descriptor", "task": "features", "data": "synthetic",
     "name": "球面調和記述子による回転不変な3D形状検索",
     "summary": "向き未知の形状(球/箱/円柱の回転コピー)を SH 帯域エネルギー記述子で照合。検索3/3正解・分離マージン>0で、回転で全マスが入れ替わる素ボクセル占有の1/3を上回る。"},
    {"id": "space_curve", "task": "shape_analysis", "data": "synthetic",
     "name": "3D空間曲線の微分幾何(曲率κ・捩率τ・弧長・Frenet標構)",
     "summary": "順序付き点列からκ/τ/弧長とFrenet標構を求め、ヘリックスの解析解と相対誤差<0.01%で一致。直線(κ=0)・平面円(τ=0)の零点を判別的に上回り、変速でもGram-Schmidt射影の正しさを確認。"},
    {"id": "edges_3d", "task": "features", "data": "synthetic",
     "name": "3Dボリュームのエッジ検出(canny3d: NMS+ヒステリシス)",
     "summary": "なだらかな内部を持つ中実ボールの外周だけを1ボクセルに細線化。オンシェル率1.000・内部誤検出0で、生勾配の固定しきい値null(0.464・誤検出4012)を+0.536上回る。"},
    {"id": "region_props_3d", "task": "segmentation", "data": "synthetic",
     "name": "3Dボリュームの連結成分ラベリングと塊ごとの計測(個数/体積/重心)",
     "summary": "複数ブロブを連結成分で分離し、体積誤差0voxel・重心誤差0.0で計測。largest_componentで最大塊、filter_by_volumeで小塊除去。全前景を1領域とする零点(重心ズレ13.5voxel)を上回る。"},
    {"id": "detect_primitives_3d", "task": "shape_fitting", "data": "synthetic",
     "name": "3D Houghで平面・球のプリミティブを検出",
     "summary": "投票ベースの hough_plane_3d/hough_sphere_3d で平面(法線誤差0.55度)・球(中心誤差0voxel)を復元。素朴PCA(80度)や重心(22voxel)の零点を明確に上回る。"},
    {"id": "morphology_3d", "task": "modeling", "data": "synthetic",
     "name": "3Dモルフォロジ(opening/closing/gradient/top-hat)で体積を整える",
     "summary": "closingで空洞8→0(本体は不変)、openingでトゲ3→0、gradientは境界殻のみ、top-hatはトゲだけ抽出。素のdilate/erodeが本体まで膨張/収縮する差で判別。"},
    {"id": "augment_pointcloud", "task": "augmentation", "data": "synthetic",
     "name": "点群データ拡張(回転/スケール/ドロップアウト/ジッタ)",
     "summary": "学習用の点群拡張4種を指定パラメータどおり適用(回転=距離不変・向き変化、scale倍率、dropout点数、jitter std)。恒等nullを判別的に上回り、連鎖でも複合性質を保つ。"},
    # -- bounds / mesh processing / primitive fit(Wave A)------------------------- #
    {"id": "hull_bounds", "task": "metrology", "data": "synthetic",
     "name": "点群のバウンディング(凸包/OBB/AABB/最小包含球)",
     "summary": "生点群から凸包・向き付き箱(OBB)・軸整列箱(AABB)・最小包含球を起こす。新規 min_enclosing_sphere は素朴球 r=9.95→5.63(比0.57・全点内包)、OBB体積は回転箱で AABB の0.20倍。把持/衝突/寸法検査の基本メトロロジー。"},
    {"id": "mesh_smooth", "task": "mesh_process", "data": "synthetic",
     "name": "三角形メッシュの平滑化(Laplacian/Taubin・非収縮)",
     "summary": "ノイズメッシュを接続グラフ上で平滑化。RMS 0.627→Laplacian 0.306/Taubin 0.215。Taubin は平均半径ズレ0.025で Laplacian 0.298 の約1/12=非収縮。marching cubes/スキャン後処理向け。"},
    {"id": "mesh_decimate", "task": "mesh_process", "data": "synthetic",
     "name": "メッシュ簡略化(QEM edge-collapse)で目標面数へ軽量化",
     "summary": "球1280面→384面(目標厳密)、頂点は球面上・watertight維持・対称Hausdorff 3.3%R。同数までランダム間引くnullは穴792本・Hausdorff 21.3%Rで6.4倍劣る。スキャン/CADの軽量化。"},
    {"id": "mesh_props", "task": "mesh_process", "data": "synthetic",
     "name": "メッシュの法線・表面積・平均曲率(接続情報から)",
     "summary": "面/頂点法線・表面積・cotangent平均曲率を面の巻き順とラプラシアンから測る。球(R2.5)で面積誤差0.12%・曲率0.4000(1/R)・法線外向き率1.00。面積null(49.7%誤差)・平面曲率nullを判別的に上回る。"},
    {"id": "watershed3d", "task": "segmentation", "data": "synthetic",
     "name": "接触物体の分離(距離変換ベース3D watershed)",
     "summary": "接触して1連結成分に融合した2球をwatershedで2個に分離。重心を真値へ最大0.31voxel・体積誤差<5%。連結成分(null)はcount=1に融合し重心が10voxelずれる — 個数でも重心でも上回る。CT/粉体/細胞の計数。"},
    {"id": "fit_primitives_ext", "task": "shape_fitting", "data": "synthetic",
     "name": "プリミティブ当てはめ拡張(円錐/トーラス/楕円体)",
     "summary": "点群に円錐(半角誤差0.008°)・トーラス(R,r誤差~3e-4)・楕円体(半径相対誤差<0.2%)を当てはめ。誤モデル(球/平面)の残差をそれぞれ38x/64x/50x下回る。漏斗/配管/細胞・慣性の寸法検査。"},
    # -- decimation family / procedural modeling(間引き3種 + 手続き生成)---------- #
    {"id": "pointcloud_downsampling", "task": "decimation", "data": "synthetic",
     "name": "点群の間引き(voxel grid / farthest-point)で密度を均す",
     "summary": "6万点の密度ムラ点群をvoxel格子(重心集約, カバレッジ0.134<=理論0.260)とFPS(0.097)で間引き。同数のランダム間引き(0.310, 穴あり)を判別的に上回る。LiDAR/深度カメラの前処理でICP・特徴計算を軽くする。"},
    {"id": "volume_downsampling", "task": "decimation", "data": "synthetic",
     "name": "ボリューム(3D CT)の間引き — max/mean プールの使い分け",
     "summary": "260^3=1758万ボクセル(Frangi上限超過で拒否)を4倍間引きして上限内へ。既知8欠陥をmaxプールは8/8保持・meanプールは0/8にwashout。微小欠陥検出にはmaxが正しいことを計数で判別的に示す。工業CT/ラミノグラフィの前処理。"},
    {"id": "procedural_hand", "task": "modeling", "data": "procedural",
     "name": "手続き的に手全体の骨格を組む(27骨のカプセルSDF→メッシュ)",
     "summary": "手根骨8+中手骨5+指骨14をカプセルSDFで解剖学配置しmarching cubesでメッシュ化。指先バンドの連結成分=四指(>=4)・細長さ4.66で「手」と判別。同体積の球null(指1本)を上回る。教材/デモ/合成データの自前生成。"},
    # -- wave: 多様タスク補強(pose / 構造化光 / 光学 / 対称 / DL実データLOD)-------- #
    {"id": "mesh_lod_download", "task": "mesh_process", "data": "download",
     "name": "DL実データメッシュの多段LOD間引き(QEM)",
     "summary": "DL版Stanford Bunny(6.9万面)をQEMで50/25/10%へ間引き。面数34725→17361→6944と単調減少・Hausdorff/diag<=0.020・Chamfer/diag<=0.0024(1/10面でも平均誤差一定)。同面数ランダムドロップ(0.0034)に平均誤差で勝ち、片側クロップnullはHausdorff0.59=30倍で帯外。未取得時はSKIPしexit0。"},
    {"id": "pnp_pose_outliers", "task": "pose_estimation", "data": "synthetic",
     "name": "誤対応4割下のカメラ姿勢推定(PnP+RANSAC)",
     "summary": "200点の3D-2D対応の40%が誤対応でもpnp_ransacが姿勢復元: 回転誤差0.11度・inlier再投影0.66px・inlier適合率100%。同じ汚染データの素dlt_pose(RANSACなし)は33.7度に破綻し319倍判別的に上回る。"},
    {"id": "graycode_structured_light", "task": "structured_light", "data": "synthetic",
     "name": "Gray code 構造化光の絶対デコード",
     "summary": "物体で湾曲した投影機コラム番号(0..127)をGray codeビット面7枚からgraycode_decodeで絶対復号。全12288画素で整数厳密一致(100%)。極性反転(0%)/面順取り違え(13%)/最頻値決め打ち(2%)のnullを判別的に上回る。撮影ノイズ42%まで厳密。"},
    {"id": "snell_refraction", "task": "optics", "data": "synthetic",
     "name": "スネル屈折とフレネル反射(解析GT検証)",
     "summary": "match3dの光線光学opを閉じた式で検証。Snell残差1e-16・屈折角一致3.9e-14度、Fresnel垂直入射0.040=解析値・grazing→1・臨界角超で全反射(NaN/None/1.0)。無屈折null(屈折角が平均20.5度ずれ)を判別的に棄却。"},
    {"id": "reflection_symmetry", "task": "shape_analysis", "data": "synthetic",
     "name": "点群の鏡映対称面の復元",
     "summary": "既知平面で鏡映対称な点群から初期推定なしにdetect_reflection_symmetryが対称面を復元: 法線誤差0.0度・鏡映残差1.5e-11。非対称null(残差1.14)は約7.8e10倍大きく、でたらめ平面(最良1.27)も桁違いで判別的。"},
    # -- wave: 多様な形状(トーラス結び目/歯車/分子/DL実Dragon/地形)------------------ #
    {"id": "torus_knot_curve", "task": "shape_analysis", "data": "procedural",
     "name": "トーラス結び目の弧長・捩率計測(非平面曲線)",
     "summary": "(2,3)トーラス結び目を密ポリラインで生成しcurve3dのarc_length/curvature_torsionを検証。弧長は台形積分と相対7.6e-7一致・中央|τ|0.283は同長の平面円(捩率6e-10)の5.1e8倍で非平面を判別。円のκ=1/rも誤差7e-13で正確。"},
    {"id": "gear_metrology", "task": "metrology", "data": "procedural",
     "name": "平歯車の歯数をSDFジオメトリから逆計測",
     "summary": "sdf_opsのCSGで平歯車を手続き生成し、歯先帯r=0.44の占有を角度サンプルしてラン計数で歯数N=12→12/20→20を厳密復元(0.2度ジッタでも不変)。歯なし円板null=0本・誤半径 内1/外0本で判別的。"},
    {"id": "molecule_atom_count", "task": "segmentation", "data": "procedural",
     "name": "分子の接触原子カウント(距離変換+マーカ分水嶺)",
     "summary": "シクロヘキサンC6椅子型を6原子球の和集合(41万voxel・1連結成分)にボクセル化。距離変換+マーカ分水嶺で接触原子を6個に分離・重心を真値へ最大0.52voxel。素朴な連結成分null=1個に融合(43voxelずれ)を個数6vs1で上回る。"},
    {"id": "dl_mesh_curvature", "task": "features", "data": "download",
     "name": "実メッシュ曲率が詳細形状を判別(Stanford Dragon)",
     "summary": "DL実データStanford Dragon(87万面)をread_mesh→vertex_curvature(cotangent Laplace-Beltrami)。正規化曲率はmedian9.2・MAD6.2・|Hn|>2が88%と広く分布し、同スケールの滑球null(median1.00・0%)をMAD比1.4e7倍で判別。未取得時はSKIPしexit0。"},
    {"id": "terrain_traversability", "task": "mapping", "data": "procedural",
     "name": "地形の走行可能性マッピング(段差検出)",
     "summary": "平坦+緩スロープ+急段差(0.5m壁)の点群→標高マップ→走行可能性マップ。平坦/緩は走行可能率1.00・段差は非走行可能率1.00。段差検出 実op1.00 vs 全可null/巨大max_step null 0.00、GT精度1.00 vs 0.83。"},
    # -- rendering quality(Wave B・映える静止3D)---------------------------------- #
    {"id": "render_ao", "task": "rendering", "data": "synthetic",
     "name": "レンダリング品質: アンビエントオクルージョン(接触影・凹部の環境影)",
     "summary": "物体空間AOで半球到達性を[0,1]化。平面に載る球で頂上AO1.00/接触部0.06(高さとSpearman1.00)、溝は深さに単調低下。一様AO=1(null)は凹凸を判別不能。拡散のみのLambertianに乗算し立体感を出す。"},
    {"id": "render_shadow", "task": "rendering", "data": "synthetic",
     "name": "レンダリング品質: キャスト/ソフトシャドウ(接地影)",
     "summary": "shadow mappingで接地影。球を床に載せ解析GTだ円とIoU 0.978。影なし(従来陰影)はIoU 0.00(接地影を全く当てられない)を判別的に上回る。半影は光源角サイズで単調に拡大。"},
    {"id": "render_shade", "task": "rendering", "data": "synthetic",
     "name": "レンダリング品質: matcap/Phong鏡面シェーディング",
     "summary": "拡散のみに鏡面を追加。Phongハイライトのピークが反射方向N=norm(L+V)と0.63px一致。Lambertianの最輝点は反射方向を54px外す(nullを約85倍上回る)。matcapはlit-sphere転写で素材感を持ち込む。"},
    {"id": "render_ssaa", "task": "rendering", "data": "synthetic",
     "name": "レンダリング品質: スーパーサンプリング(SSAA)でジャギー除去",
     "summary": "ss倍レンダ→面積平均縮小。傾き22°エッジでエイリアスエネルギー0.275→0.164(0.59倍)・中間輝度画素0%→0.95%、ss=1..6で単調減少。z-bufferの階段状シルエットを滑らかに。"},
    {"id": "render_tonemap", "task": "rendering", "data": "synthetic",
     "name": "レンダリング品質: トーンマップ(HDR→LDR)で白飛び救済",
     "summary": "鏡面HDR(max5.41)をReinhard/ACESで[0,1]へ。全域Spearman1.00で単調、素朴クリップがハイライト域を1段に潰す(分散0)のに対し順位相関1.0・194段の階調を保持。"},
    {"id": "render_beauty", "task": "rendering", "data": "synthetic",
     "name": "レンダリング品質: hero レンダラ render_beauty(全層合成の映える静止3D)",
     "summary": "ラスタライズ/Phong鏡面/AO/接地影/SSAA/トーンマップを1本に合成。sphere-on-groundで各層を実測: AOは接触凹部を0.07→0.02と選択的に暗化(露出頂部0.01は不変)、鏡面は小面積ハイライト(frac0.018)、接地影はwith-mesh993px vs null0px、reinhardは単調(clip34段潰しを回避)、SSAAはedge0.040→0.026。sdf_ops生成メッシュでhero画像を出力。"},
]

_BY_ID = {e["id"]: e for e in EXAMPLES}


def names() -> list[str]:
    """Every example id, in gallery order."""
    return [e["id"] for e in EXAMPLES]


def get(example_id: str) -> dict:
    """Metadata dict for an example id (KeyError if unknown)."""
    return _BY_ID[example_id]


def tasks() -> list[str]:
    """Distinct task categories, in first-seen order."""
    seen = []
    for e in EXAMPLES:
        if e["task"] not in seen:
            seen.append(e["task"])
    return seen


def by_task() -> dict:
    """``{task: [id, ...]}`` for grouping the gallery."""
    out: dict[str, list[str]] = {}
    for e in EXAMPLES:
        out.setdefault(e["task"], []).append(e["id"])
    return out


def by_data() -> dict:
    """``{provenance: [id, ...]}`` — synthetic / skeleton_ct / itokawa."""
    out: dict[str, list[str]] = {}
    for e in EXAMPLES:
        out.setdefault(e["data"], []).append(e["id"])
    return out


def path(example_id: str) -> str:
    """Absolute path to the runnable script for an example id."""
    return os.path.join(DIR, example_id + ".py")


def code(example_id: str) -> str:
    """The runnable source of an example (for the 'view code' gallery panel)."""
    with open(path(example_id), encoding="utf-8") as f:
        return f.read()


def discover() -> list[str]:
    """Every ``examples_3d/*.py`` on disk (superset check against EXAMPLES)."""
    if not os.path.isdir(DIR):
        return []
    return sorted(f[:-3] for f in os.listdir(DIR)
                  if f.endswith(".py") and not f.startswith("_"))


def run(example_id: str, timeout: int = 240) -> tuple[bool, str]:
    """Run one example as a subprocess (repo root on PYTHONPATH). -> (ok, tail_output)."""
    env = dict(os.environ)
    env["PYTHONPATH"] = _ROOT + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONUTF8"] = "1"
    try:
        p = subprocess.run([sys.executable, path(example_id)], cwd=_ROOT, env=env,
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    tail = (p.stdout or "").strip().splitlines()
    note = tail[-1] if tail else (p.stderr or "").strip().splitlines()[-1:] or ""
    return p.returncode == 0, (note if isinstance(note, str) else " ".join(note))


def validate(ids=None) -> dict:
    """Run each example and report which are usable -> ``{id: (ok, note)}``.

    The gallery advertises only what passes here, so a broken example is surfaced,
    never silently shown. Pass ``ids`` to check a subset.
    """
    ids = ids or names()
    return {i: run(i) for i in ids}


if __name__ == "__main__":
    ok = 0
    for i, (name, (good, note)) in enumerate(validate().items(), 1):
        mark = "PASS" if good else "FAIL"
        print(f"[{i:2d}/{len(names())}] {mark}  {name}: {note}")
        ok += good
    print(f"\n{ok}/{len(names())} examples usable")
    sys.exit(0 if ok == len(names()) else 1)
