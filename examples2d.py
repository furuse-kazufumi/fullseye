# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""examples2d — the worked-example gallery for Fullseye's 2-D geometric vision ops.

An operator no one can *find or run* is invisible. This module is the discoverable
index for the 2-D geometric examples: every entry is a **self-contained,
self-asserting runnable script** under ``examples/`` that builds data, calls the
toolkit, prints a ground-truth check and asserts it. Studio's "2-D Examples" gallery
sources its list from here, and :func:`validate` runs every script so the gallery
only ever advertises examples that actually work.

Mirror of :mod:`examples3d`; kept separate so 2-D (image-plane) and 3-D (point-cloud
/ volume) galleries stay legible. Add a new example by dropping a runnable script in
``examples/`` and appending an entry here — or, if it cannot self-run (needs external
assets / hardware), list it in :data:`EXCLUDED` with the reason. ``tests/test_examples2d``
reconciles both against the directory in *both* directions (:func:`registry_gaps`).

Usage::

    import examples2d
    examples2d.names()                         # every example id
    examples2d.by_task()["morphing"]           # ids grouped by task
    print(examples2d.code("image_morph"))      # the runnable source
    examples2d.validate()                      # run all; returns {id: (ok, note)}

Each script is also runnable directly::

    py -3.11 examples/image_morph.py
"""
from __future__ import annotations

import os
import subprocess
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(_ROOT, "examples")

# id -> metadata. `name`/`summary` are plain-language (what real problem it solves);
# `task` groups the gallery; `data` is the provenance. Every id maps to examples/<id>.py.
EXAMPLES = [
    # -- morphing / warping ------------------------------------------------------ #
    {"id": "image_morph", "task": "morphing", "data": "synthetic",
     "name": "2人の顔の中間を作る(対応点駆動モーフ)",
     "summary": "作業者が与えた対応点(目・鼻・口)で特徴を中間形状へワープしてからディゾルブし、"
                "単純αブレンドの二重像(ゴースト)を避けて『本物の中間顔』を作る。区分アフィン/TPS。"},
    # -- shape descriptors ------------------------------------------------------- #
    {"id": "contour_fourier", "task": "shape_descriptors", "data": "synthetic",
     "name": "輪郭の楕円フーリエ記述子(平滑化・不変マッチング)",
     "summary": "閉輪郭をフーリエ級数で表し、高調波打ち切りで平滑化、回転/拡大/移動/始点に不変な"
                "記述子で形状検索する(EFD, Kuhl-Giardina)。"},
    # -- drawing / annotation ---------------------------------------------------- #
    {"id": "draw_annotate", "task": "drawing", "data": "synthetic",
     "name": "画像にマーカー/線/円/輪郭を直接描く(ラスタ描画)",
     "summary": "作業者が指定した対応点を画像そのものに焼き込むラスタ描画op(imagedraw)。"
                "描いた既知シーンを検出器が回収し結果を描き返す(描画→検出→注釈)。"},
    # -- signal / point-sequence math -------------------------------------------- #
    {"id": "signal_filter", "task": "signal_processing", "data": "synthetic",
     "name": "点列の多項式近似・フーリエ・ローパス/ハイパス",
     "summary": "計測1D列をトレンド抽出(多項式)・周波数分析(FFT)・平滑化(ローパス)・"
                "細部抽出(ハイパス)する(signal1d)。各処理に beat-the-null のGT付き。"},
    {"id": "spline_curve", "task": "interpolation", "data": "synthetic",
     "name": "スプライン補間(開/閉曲線・2D/3D・時間変形)",
     "summary": "疎な点列を滑らかに補間・再サンプル。輪郭は閉曲線(滑らかに閉じる)、"
                "軌跡は開曲線、3D空間曲線も同API。座標を時間で補間すれば時間軸の変形も表せる。"},
    # -- family coverage galleries (exercise & GT-validate every op in a category family) -- #
    # Breadth exercisers: each drives its whole op family with finite/out_sort/determinism
    # checks plus beat-the-null GT on representative ops. They keep op→example coverage at
    # 100% (see tests/test_op_example_coverage.py) and double as runnable family demos.
    {"id": "gallery2d_smoothing_rank", "task": "family_coverage", "data": "synthetic",
     "name": "平滑化・ランク・復元フィルタ族を総なめ", "summary":
         "gaussian/median/bilateral/rank/restoration など平滑化フィルタ族の全 op を実行し、"
         "有限性・out_sort・決定性を機械検証(代表 op は beat-the-null GT)。"},
    {"id": "gallery2d_edges", "task": "family_coverage", "data": "synthetic",
     "name": "エッジ・微分・コーナー演算子族を総なめ", "summary":
         "sobel/laplace/canny/harris などエッジ・勾配・コーナー検出族の全 op を GT 検証。"},
    {"id": "gallery2d_morphology", "task": "family_coverage", "data": "synthetic",
     "name": "モルフォロジー(形態学)op 族を総なめ", "summary":
         "収縮/膨張/開閉/tophat/skeleton などグレー・二値形態学の全 op を GT 検証。"},
    {"id": "gallery2d_region", "task": "family_coverage", "data": "synthetic",
     "name": "領域(region)op 族を総なめ", "summary":
         "穴埋め/最大成分/距離変換/外接内接/RLE など region・region-morphology・region-transform を GT 検証。"},
    {"id": "gallery2d_segmentation", "task": "family_coverage", "data": "synthetic",
     "name": "セグメンテーション演算子族を総なめ", "summary":
         "otsu/dyn_threshold/watershed/local_max などしきい値・領域分割族の全 op を GT 検証。"},
    {"id": "gallery2d_features", "task": "family_coverage", "data": "synthetic",
     "name": "特徴抽出・テクスチャ・形状記述子族を総なめ", "summary":
         "特徴点/テクスチャ/形状記述/自己相似の全 op を有限性・決定性で GT 検証。"},
    {"id": "gallery2d_geometry", "task": "family_coverage", "data": "synthetic",
     "name": "2-D 幾何オペレータ族を総なめ", "summary":
         "アフィン/射影/回転/リサンプル/座標変換など幾何変換族の全 op を GT 検証。"},
    {"id": "gallery2d_gray_arith", "task": "family_coverage", "data": "synthetic",
     "name": "濃淡・階調変換・算術・定義域 op 族を総なめ", "summary":
         "gamma/contrast/算術演算/domain(定義域)など濃淡・階調族の全 op を GT 検証。"},
    {"id": "gallery2d_contour_measure", "task": "family_coverage", "data": "synthetic",
     "name": "輪郭・1次元計測・テンプレート照合族を総なめ", "summary":
         "輪郭抽出/subpix/1D 計測/テンプレートマッチ族の全 op を GT 検証。"},
    {"id": "gallery2d_texture_freq", "task": "family_coverage", "data": "synthetic",
     "name": "テクスチャ・周波数・分解 op 族を総なめ", "summary":
         "FFT/gabor/wavelet/分解(decomposition)などテクスチャ・周波数族の全 op を GT 検証。"},
    {"id": "gallery2d_color_artistic", "task": "family_coverage", "data": "synthetic",
     "name": "色・芸術・拡張(sim2real)op 族を総なめ", "summary":
         "色空間変換/芸術効果/augmentation など色・拡張族の全 op を GT 検証。"},
    {"id": "gallery2d_halcon_ext", "task": "family_coverage", "data": "synthetic",
     "name": "HALCON 拡充 tier(hx_ 一族)を総なめ", "summary":
         "HALCON 互換の拡充 op(``hx_`` prefix, category=halcon_ext)の全 op を GT 検証。"},
    {"id": "gallery2d_physics_alife_3d", "task": "family_coverage", "data": "synthetic",
     "name": "物理PDE・人工生命・トモグラフィ・3Dボリューム op 族を総なめ", "summary":
         "拡散/反応拡散/CA/tomography/volume など物理・人工生命・3D 族の全 op を GT 検証。"},
    # -- drawing / 2-D graphics (deferred draw lists, annotation layer, gfx2d) ------ #
    {"id": "drawlist_deferred", "task": "drawing", "data": "synthetic",
     "name": "描画を「ためてから流す」(drawlist 蓄積描画)",
     "summary": "imagedraw の即時描画に対し drawlist はコマンド列を保持し flush() で絵にする。"
                "絵になる前の列を検査・差分・変換できることを、同じ絵を両経路で描いて数値で確かめる。"},
    {"id": "annotate_gallery", "task": "drawing", "data": "synthetic",
     "name": "図注(annotate)op を一枚の図で全部使い真値と突き合わせる",
     "summary": "文字下敷き/矢印/凡例/カラーバー/目盛り/拡大差し込みの annotate 全 op を 1 枚の図に載せ、"
                "配置と画素値を GT と照合する。"},
    {"id": "gfx2d_scene", "task": "drawing", "data": "synthetic",
     "name": "リアルタイム 2-D グラフィックス(gfx2d)で 1 枚の画面を組み立てる",
     "summary": "背景/タイル/スプライト/パーティクル/光/影/ポスト処理を合成し、ストレート α と"
                "乗算済み α の取り違え(この族が黙って間違う唯一の場所)を同じ絵の上で数値化する。"},
    # -- 1-D signals / acoustics -------------------------------------------------- #
    {"id": "signal_funct1d", "task": "signal_processing", "data": "synthetic",
     "name": "減衰振動のセンサー信号を HALCON funct_1d ファミリで解析",
     "summary": "平滑化→極値で周期→ゼロ交差で半周期→微分/積分往復→包絡線から減衰時定数→"
                "相互相関で遅延。各段に beat-the-null の GT 付き。"},
    {"id": "acoustic_condition_monitoring", "task": "signal_processing", "data": "synthetic",
     "name": "音だけで回転機械を診断する(acoustics 音響状態監視)",
     "summary": "マイク 1〜2 本の音圧列から、傷んだ部品・dB 値・加振との因果(伝達関数/コヒーレンス)を"
                "出す。合成音源の既知パラメータを GT に照合。"},
    # -- math for metrology ------------------------------------------------------- #
    {"id": "math_metrology", "task": "math", "data": "synthetic",
     "name": "視覚計測を支える数学 op(mathops)を計測ワークフローで一巡",
     "summary": "平面フィット→残差統計→共分散楕円の主軸化→較正曲線の多項式フィット(条件数監視)→"
                "補間で逆引き。mathops 16 op を実データ風に通し閉形式 GT と照合。"},
    {"id": "math_complex", "task": "math", "data": "synthetic",
     "name": "複素解析 op(mathops tier2)を閉形式の真値と突き合わせる",
     "summary": "偏角原理で零点数、コーシー積分で内部値復元、等角性・正則性判定を点列として持つ"
                "閉曲線から numpy 演算で答える。"},
    # -- optics / sensing physics ------------------------------------------------- #
    {"id": "optics_imaging", "task": "optics_sensing", "data": "synthetic",
     "name": "光学 op(optics)で検査機を 1 台、紙の上で設計する",
     "summary": "倍率→焦点距離/物体距離、ABCD 行列で結像確認、回折限界・被写界深度・MTF を"
                "要求分解能に対して合否判定する。"},
    {"id": "lens_design_demo", "task": "optics_sensing", "data": "synthetic",
     "name": "実光線設計 op(raytrace)で singlet と doublet を比べる",
     "summary": "処方(lens_system)から近軸表・面ごとの Seidel・軸上/5 deg のスポット RMS・"
                "OPD→Zernike・Monte-Carlo 公差 p95 を出し、閉形式(thick_lens / 放物面鏡の"
                "完全結像)と突き合わせる。"},
    {"id": "lightfield_depth", "task": "optics_sensing", "data": "synthetic",
     "name": "ライトフィールド 17 op で plenoptic 検査機を通す",
     "summary": "画素/MLA ピッチから角度・空間分解能と基線長を設計し、センサ生データ→"
                "EPI→深度まで復元して既知深度と照合。"},
    {"id": "photon_timeresolved", "task": "optics_sensing", "data": "synthetic",
     "name": "光子計数・時間分解 op(photoncount)で単一光子距離計を仕立てる",
     "summary": "SPAD の √N 雑音・デッドタイム・パイルアップを持つヒストグラムから距離と蛍光寿命を"
                "出し、17 op を閉形式 GT と照合。"},
    {"id": "coherence_scanning", "task": "optics_sensing", "data": "synthetic",
     "name": "コヒーレンス走査干渉(interferometry)で段差表面を測る",
     "summary": "位相シフト法(fringe)が 2π 周期で壊れる段差を、同じ表面で白色干渉の包絡線ピークから"
                "正しく測り、両者の差を数値に出す。"},
    {"id": "specular_photometric", "task": "optics_sensing", "data": "synthetic",
     "name": "光沢面の外観検査(specularity 13 op)",
     "summary": "Lambertian 前提の形状復元がハイライトで壊れる場所を見せてから、二色性射影分離・"
                "影下の頑健最小二乗・偏光分離を順に通し、破綻点(4 灯遮蔽)も隠さず出す。"},
    {"id": "fmcw_range_doppler", "task": "optics_sensing", "data": "synthetic",
     "name": "コヒーレント測距 op(rangedoppler)で 4D レーダを仕立てる",
     "summary": "FMCW の位相を保つビート信号から距離-速度マップと角度を出す。lidar_scan には無い"
                "速度軸を既知ターゲットの GT と照合。"},
    {"id": "event_camera", "task": "optics_sensing", "data": "synthetic",
     "name": "通常フレームからイベントカメラ(DVS)表現を作り運動を復元",
     "summary": "フレーム対/短クリップを events 表現(タイムサーフェス等)に変換し、"
                "コントラスト最大化で注入した運動を回収する(events.py ファサード、終了コードで判定)。"},
    # -- image quality / forensics / color / astronomy ---------------------------- #
    {"id": "image_quality_metrics", "task": "imaging_quality", "data": "synthetic",
     "name": "画質 op(imgmetrics)で保存時の量子化段数を 1 つ選ぶ",
     "summary": "CIEDE2000 を公開検証表 34 組で、SSIM を既知条件で検定してから、"
                "「欠陥が見えなくならない」を合否条件に落として量子化段を決める。"},
    {"id": "image_forensics_audit", "task": "imaging_quality", "data": "synthetic",
     "name": "1 枚の写真を証拠として「どこまで言えるか」まで切り分ける(forensics)",
     "summary": "知覚ハッシュ→帰無分布→PRNU カメラ指紋→JPEG 品質/ELA/ゴースト→雑音整合→"
                "コピー&ムーブ(誤差 0 px)→電子透かしの 7 段。改竄側を自分で作った GT で検定。"},
    {"id": "color_transport", "task": "imaging_quality", "data": "synthetic",
     "name": "2 台のカメラの色を揃える(colortransport 色輸送)",
     "summary": "クロストークと黒レベルずれを持つカメラ B の色を A に合わせ(ヒストグラム/"
                "最適輸送ベース)、既知の変換を回収できるかを GT で照合。"},
    {"id": "astro_stacking", "task": "imaging_quality", "data": "synthetic",
     "name": "一晩ぶんの生フレームから 1 枚の星像を作り星の明るさを測る",
     "summary": "フラット補正→宇宙線除去→ディザ位置合わせ→スタック→測光。"
                "既知の星の明るさ・位置を GT に照合(12 枚の合成生フレーム)。"},
    {"id": "motion_magnification", "task": "imaging_quality", "data": "synthetic",
     "name": "見えない振動を見せる/測る(motionmag モーション増幅・位相変位)",
     "summary": "0.2 画素の振動を帯域通過した局所位相から増幅表示し、同じ量からサブピクセル"
                "変位を数値で出して既知振幅と照合。"},
    {"id": "quaternion_monogenic", "task": "imaging_quality", "data": "synthetic",
     "name": "四元数画像 op(quatimage)を閉形式の真値と突き合わせる",
     "summary": "色の 3 次元回転とモノジェニック信号が本物の差で、それ以外(QFT 等)は差でない"
                "ことを 19 op の GT 照合で示す(勝つ/勝たない/負ける を実測で分ける)。"},
    # -- tomography / 3-D volume / CAD linkage / representation ------------------- #
    {"id": "ct_reconstruction", "task": "tomography_3d", "data": "synthetic",
     "name": "CT で 1 本の試料をスキャンし、寸法 mm と欠陥の数まで出す",
     "summary": "楕円ファントムの閉形式サイノグラム→FBP 再構成→外径測定→空洞計数。"
                "真値(30.00 mm / 1 個)との誤差を印字し断定する。"},
    {"id": "tomography_reconstruct", "task": "tomography_3d", "data": "synthetic",
     "name": "投影からボクセルと体積 mm³ まで一本で閉じる(tomography 族)",
     "summary": "サイノグラムから再構成した後は既存の 3-D op(窓/ラベル/境界/メッシュ/領域統計)を"
                "そのまま呼び、既知体積と照合。"},
    {"id": "ct_inspection", "task": "tomography_3d", "data": "synthetic",
     "name": "X 線 CT / ラミノグラフィ検査: スライス毎に内部空洞を見つけて測る",
     "summary": "合成円柱ボリューム(空洞 2 つ)をスライス毎に denoise→材料分割→空洞抽出→計測。"
                "--laminography で限られた角度の軸方向ぼけを模す(テンプレート、数値を印字)。"},
    {"id": "voxel_labels_color", "task": "tomography_3d", "data": "synthetic",
     "name": "ボクセルのラベル色分け(volcolor)で CT の粒子を数えて見せる",
     "summary": "vol_label/vol_region_props の結果を色付けし、「切ってから色を付ける」と"
                "「色を付けてから切る」の差を数値に出す。"},
    {"id": "defect_to_cad", "task": "tomography_3d", "data": "synthetic",
     "name": "2-D 画像で見つけた欠陥は CAD のどの面のどこか(cadmap)",
     "summary": "姿勢(ICP/PPF)から先、画素→レイ→CAD 面 ID と (x,y,z)・面積 mm² へ写す。"
                "既知配置の欠陥で往復誤差を確認。"},
    {"id": "representation_conversion", "task": "tomography_3d", "data": "synthetic",
     "name": "部品 2 回スキャンのずれ量を 8 つの表現で測って往復する",
     "summary": "法線/曲率/記述子/添字/スコア/シフト/回転倍率/フロー/変形/複素など 12 系統の表現を"
                "経由して既知剛体変位を測り、戻るものは誤差 0、戻らないものは落ちた量を数値で言う。"},
    {"id": "representation_roundtrip", "task": "tomography_3d", "data": "synthetic",
     "name": "表現変換(reprconv)op を往復させて嘘を露見させる",
     "summary": "産む op はあるが食う op が無かった 25 型を消費する reprconv 族を往復させ、"
                "可逆なものは誤差 0、不可逆なものは何がどれだけ落ちるかを印字する。"},
    # -- robot perception templates (copy-and-adapt; synthetic data, CLI --save) -- #
    {"id": "perception_pipeline", "task": "perception_templates", "data": "synthetic",
     "name": "整流ステレオ対→深度→点群→地形高さマップ→通行可能性",
     "summary": "ロボット移動用の一本道テンプレート(--save で色付き PNG + PLY)。合成データ、"
                "実行して数値を印字するテンプレート型(tests/test_examples.py で煙試験)。"},
    {"id": "segment_and_classify", "task": "perception_templates", "data": "synthetic",
     "name": "物体を分割→記述(Hu+形状)→プロトタイプと照合して識別",
     "summary": "ピック/仕分けに必要な知覚のテンプレート。prototypes を 1 度作り、"
                "segment_objects の結果を分類する。"},
    {"id": "motion_analysis", "task": "perception_templates", "data": "synthetic",
     "name": "2 フレーム→密なオプティカルフロー→大域運動除去→独立運動領域",
     "summary": "動画対から運動を読むテンプレート(--save で色付きフロー PNG)。"
                "物理クリップ/身体言語の「本当に動いたか」に使う。"},
    {"id": "grasp_pose", "task": "perception_templates", "data": "synthetic",
     "name": "観測点群を既知モデルに登録して 6-DoF 姿勢と把持接近方向を出す",
     "summary": "ノイズ・欠け・変位のある観測点群→ダウンサンプル→法線→登録→姿勢。"
                "マニピュレーション用テンプレート(合成データ、--save で PLY)。"},
    {"id": "perception_on_video", "task": "perception_templates", "data": "synthetic/real clip",
     "name": "実クリップの知覚: フロー→運動エネルギー/イベント→大域運動除去→点追跡",
     "summary": "mp4/gif を渡せば実映像で走り、無ければ合成クリップに落ちる。GT が無いので"
                "測光自己整合(identity 基準比)の honest 指標で判定。"},
    {"id": "physical_ai_perception", "task": "perception_templates", "data": "synthetic",
     "name": "Physical-AI 知覚パイプライン 2 本(把持/歩行)を fullseye だけで組む",
     "summary": "MANIPULATION: 地面除去→クラスタ→PPF 6-DoF→反対把持。LOCOMOTION: 深度→点群+法線→"
                "高さマップ→足場候補→支持多角形と安定余裕。"},
    {"id": "import_and_grasp", "task": "perception_templates", "data": "synthetic",
     "name": "物体を取り込み→シム用に整える→把持位置→レンダリング",
     "summary": "OBJ/STL/PLY/OFF メッシュを水密化し正確な慣性テンソル(MuJoCo 用)、反対把持候補の"
                "ランク付け、深度/シルエットのレンダまで numpy だけで通す。"},
    {"id": "gaussian_splat_cloud", "task": "perception_templates", "data": "synthetic",
     "name": "3D Gaussian Splatting の出力(中心点群)を fullseye で処理する",
     "summary": "3DGS を学習はしない(GPU レンダラが要る)。結果の点群を取り込みダウンサンプル・"
                "法線推定・2 回撮影の登録まで(テンプレート、--save で PLY)。"},
    {"id": "sim2real_and_alife", "task": "perception_templates", "data": "synthetic",
     "name": "sim2real 劣化(aug_*)・人工生命・触覚 op 族の一巡",
     "summary": "光子雑音/固定パターン/ローリングシャッター/JPEG/歪み等でクリーンな描画を実カメラ風に"
                "劣化させ、人工生命・触覚 op も含めて実行する(数値を印字)。"},
    # -- consumer-project examples (how sibling projects use fullseye honestly) ---- #
    {"id": "consumer_hillco", "task": "consumer", "data": "synthetic",
     "name": "hillco / evis(筋骨格ヒューマノイド歩行)が fullseye を使う 3 つの検査",
     "summary": "物理シムが真値を持つ前提で、fullseye は独立な知覚側の二重チェックのみ: 歩行安定性"
                "(支持多角形/COM 余裕)、レンダ動画の運動検証、姿勢の骨格化。制御は駆動しない。"},
    {"id": "consumer_onocollo", "task": "consumer", "data": "synthetic",
     "name": "onocollo(CPU 世界モデル/gaitlab)が fullseye を使う 2 つの検査",
     "summary": "MuJoCo 風状態からの静的安定性チェック(support_polygon/com_support_margin)と、"
                "物理レンダ動画 2 フレームからの運動検証。"},
    # -- whole-workflow tour ------------------------------------------------------ #
    {"id": "quickstart", "task": "workflow", "data": "synthetic",
     "name": "imgevolve quickstart — 全ワークフローを 1 ファイルで",
     "summary": "レジストリ→型付き手組みパイプライン→ゲノム復号→タスク採点→進化ドライバ→"
                "codegen + 差分テスト(約 1.5 分、repo root から実行)。"},
]

# Scripts under examples/ that are deliberately NOT in the gallery — each with the
# honest reason. test_examples2d enforces: registry ∪ EXCLUDED == files on disk,
# and the two sets are disjoint, so a new script cannot slip in unlisted.
EXCLUDED = {
    "g1_policy_staged": "needs a trained G1 walking checkpoint (REF) + MuJoCo; "
                        "no checkpoint ships with the repo, so it cannot self-run",
    "hand_tracking_demo": "needs a photo/webcam argument plus the optional "
                          "mediapipe extra and a downloaded hand_landmarker.task model",
    "perception_staged": "needs FULLSEYE_G1_QPOS / FULLSEYE_MENAGERIE_XML pointing at "
                         "external MuJoCo Menagerie assets (not shipped)",
}

_BY_ID = {e["id"]: e for e in EXAMPLES}


def registry_gaps() -> dict:
    """Two-way registry/disk reconciliation -> ``{"unregistered": [...], "missing": [...], "overlap": [...]}``.

    * ``unregistered``: scripts on disk that are neither in :data:`EXAMPLES` nor :data:`EXCLUDED`;
    * ``missing``: registered/excluded ids with no ``examples/<id>.py`` on disk;
    * ``overlap``: ids listed in both :data:`EXAMPLES` and :data:`EXCLUDED`.
    All three empty == the gallery honestly reflects the directory.
    """
    disk = set(discover())
    reg = set(_BY_ID)
    exc = set(EXCLUDED)
    return {"unregistered": sorted(disk - reg - exc),
            "missing": sorted((reg | exc) - disk),
            "overlap": sorted(reg & exc)}


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
    """``{provenance: [id, ...]}``."""
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
    """Every ``examples/*.py`` on disk (superset check against EXAMPLES)."""
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
    note = tail[-1] if tail else ((p.stderr or "").strip().splitlines()[-1:] or [""])[0]
    return p.returncode == 0, note


def validate(ids=None) -> dict:
    """Run each example and report which are usable -> ``{id: (ok, note)}``.

    The gallery advertises only what passes here, so a broken example is surfaced,
    never silently shown. Pass ``ids`` to check a subset.
    """
    ids = ids or names()
    return {i: run(i) for i in ids}


if __name__ == "__main__":
    ok = 0
    results = validate()
    for i, (name, (good, note)) in enumerate(results.items(), 1):
        mark = "PASS" if good else "FAIL"
        print(f"[{i:2d}/{len(names())}] {mark}  {name}: {note}")
        ok += good
    print(f"\n{ok}/{len(names())} examples usable")
    sys.exit(0 if ok == len(names()) else 1)
