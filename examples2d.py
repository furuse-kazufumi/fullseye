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
    # -- numerical performance ---------------------------------------------------- #
    {"id": "blas_thread_budget", "task": "math", "data": "synthetic",
     "name": "分解が遅いのはアルゴリズムのせいではない(BLAS スレッド上限)",
     "summary": "多コア機で SVD 系が遅くなる原因(スレッド過剰割り当て)を自分の機械で測り、"
                "op 側と自前 numpy 側の両方で上限の効果を出す。行列積は逆に遅くなること、"
                "上限は短辺で決まることまで含めて、速さを assert せず印字する。"},
    # -- PoC series(真値つきで実問題を解く。領域ごとの実証)------------------- #
    {"id": "poc_dem_terrain", "task": "terrain", "data": "synthetic",
     "name": "地形を測る(傾斜・水の流れ・日当たりを閉形式と突き合わせる)",
     "summary": "平面・円錐・ガウス丘という解析曲面で傾斜と曲率を検算し、離散化の誤差と式の誤りを2 次収束で区別する。欠測(水面)の扱いで集水量がどう変わるかを 3 通り並べ、日当たりを向き別に出す。**この PoC が天空率の 18 倍の遅さを暴いた**。"},
    {"id": "poc_interferometry_step", "task": "metrology", "data": "synthetic",
     "name": "白色干渉によるナノメートルの段差計測(どこまで測れるか)",
     "summary": "既知の段差 50-500 nm を合成し、コヒーレンス走査で測り返す。"
                "偏りと散らばりを分け、走査ステップと雑音を振って測れなくなる境目を出す。"
                "最大サンプルというゼロ点に対しサブサンプル推定がどれだけ稼ぐかも測る。"},
    {"id": "poc_astro_photometry", "task": "photometry", "data": "synthetic",
     "name": "天体スタックの測光精度(何枚重ねるとどこまで正確に測れるか)",
     "summary": "合成星野の既知フラックスを真値に、枚数を振って測光誤差が 1/√N で"
                "下がるかを測る。宇宙線汚染で単純平均 +5.89 % に対し κ-σ +0.30 %。"
                "**選別は雑音を √2 払って系統誤差を買う取引**であることも数字で示す。"},
    {"id": "poc_ct_fidelity", "task": "tomography", "data": "synthetic",
     "name": "CT 再構成の忠実度(投影数を減らすとどこで壊れるか)",
     "summary": "Shepp-Logan を真値に、投影数 180→12 で FBP の誤差を測る。**フィルタ無し逆投影というゼロ点と 24 本で並び 12 本で逆転する**。投影の質量保存という独立検算つき。"},
    {"id": "poc_bearing_diagnosis", "task": "diagnostics", "data": "synthetic",
     "name": "転がり軸受の異常診断(どこまで雑音に埋もれた欠陥を拾えるか)",
     "summary": "欠陥周波数の閉形式を真値に、SNR を振って検出限界を測る。生スペクトルというゼロ点に対し包絡線解析が **17.5 dB** 稼ぐ。帯域選択の窓長を誤ると共振を外すことも数字で示す。"},
    {"id": "poc_dtof_ranging", "task": "ranging", "data": "synthetic",
     "name": "光子計数 dToF の距離精度(理論限界に乗るか、どこで崩れるか)",
     "summary": "距離を先に決めて光子到着ヒストグラムを合成し、測り返す。ゲート重心は "
                "CRB の 1.003-1.068 倍、傾き -0.506(理論 -0.500)で 1/√N に乗る。"
                "ピーク位置というゼロ点に 4.80 倍。背景 SBR 0.008 で RMSE が 2 桁飛ぶのに"
                "**中央値はほとんど動かない**(3.8 % の試行だけが誤ロックする)ことまで出す。"},
    {"id": "poc_lightfield_depth", "task": "depth", "data": "synthetic",
     "name": "ライトフィールドの深度(81 視点は 2 眼に勝てるのか)",
     "summary": "既知の深度から合成ライトフィールドを作り、EPI 傾き・焦点度・2 眼を並べる。"
                "定数ゼロ点に 22 倍だが、**2 眼には既定設定だと 3.0 倍負ける**"
                "(cubic 補間にして初めて 1.6 倍勝つ)。圧勝するのは鏡面ハイライトの場面だけ、"
                "という切り分けまで数字で置く。"},
    {"id": "poc_polarization_specular", "task": "separation", "data": "synthetic",
     "name": "偏光による鏡面分離(分けた「拡散」は本当に拡散か)",
     "summary": "拡散と鏡面を自分で決めて偏光子 4 枚を合成し、分離を測り返す。"
                "返る拡散は常に真値より **R_p·E** だけ高いという閉形式の偏りを実測 "
                "(差 3.5e-18)。ブリュースター角が最良なのは R_p が消えるからで、"
                "**最適角は評価指標で動く**。飽和だけが例外を出さずに壊す。"},
    {"id": "poc_motion_magnification", "task": "vibration", "data": "synthetic",
     "name": "モーション拡大の振幅精度(拡大は測るための道具か)",
     "summary": "既知の振幅 0.02-0.5 px を拡大して測り返す。拡大率は α=200 まで厳密"
                "(実測/期待 = 1.00000000)。だが**測るなら拡大は要らない** —— 生映像の"
                "位相相関と誤差比 1.14 で引き分ける。崩れるのは拡大率ではなく入力振幅で、"
                "境界は位相の巻きではなく J0 の第 1 零点 3.0619 px。"},
    {"id": "poc_camera_calibration", "task": "calibration", "data": "synthetic",
     "name": "カメラ校正の再投影誤差は何を保証しないか",
     "summary": "内部パラメータと姿勢を自分で決めて推定し返す。板の傾きだけを変えると"
                "**再投影 RMS は比 1.00 倍のまま fx の誤差が 281 倍**(0.026 % 対 7.33 %)。"
                "区別できるのは sigma_fx(129 倍)。傾き 0 度の退化配置は閉形式が拒否するが"
                "非線形最適化は正常な再投影誤差とともに 25 % 外れた答えを返す。"},
    {"id": "poc_forensics_roc", "task": "forensics", "data": "synthetic",
     "name": "画像改ざん検出の ROC(保存ボタン 1 回で何が消えるか)",
     "summary": "改ざんを自分で入れて画素ごとの ROC を出す。JPEG ゴーストの谷の深さで "
                "AUC 0.997 / 偽陽性 1 % で検出率 0.944。だが**全体を q60 で保存し直すと "
                "0.475 と乱数を下回る**。雑音 σ は AUC 0.764 なのに偽陽性 1 % での検出率が "
                "0.000 —— AUC だけで語ると効いて見える典型。"},
    {"id": "poc_bilateral_asymmetry", "task": "morphology", "data": "synthetic",
     "name": "左右非対称性の定量(対称面そのものが変形に引きずられる)",
     "summary": "厳密に左右対称な合成頭蓋の片側に既知の膨らみを入れて測り返す。検査の床は"
                "点対面 rms 0.0297 mm(点対点の 45 分の 1)。**残差が最小になる対称面は"
                "非対称量の 46 % を消す** —— 症状を左右に均して残差を買っているため。"
                "「見つけるなら残差最適面、量を言うならランドマーク面」を数字で分ける。"},
    {"id": "poc_registration_basin", "task": "registration", "data": "synthetic",
     "name": "点群位置合わせの収束域(どれだけずれていたら失敗するか)",
     "summary": "初期姿勢のずれを振って成功率の等高線を出す。境界は初期回転 **90-120 度**で、"
                "並進は直径の 50 % まで振っても回転ほど効かない。PCA 単独は 4 % しか成功せず、"
                "**素の直方体では 83 % が反転した象限を掴む**。球と円柱は 16/16 が"
                "「残差はそのままで別の姿勢」を返す —— 収束したのに間違っている。"},
    {"id": "poc_matrix_code_reading", "task": "decoding", "data": "synthetic",
     "name": "2 値マトリクスコードの読取限界(何画素あれば読めるか)",
     "summary": "QR と同型の構造(位置検出パターン + タイミング + 25x25 格子)を自分で"
                "作り、埋めたビット行列を真値に BER を測る。読める限界は **2 px/モジュール**、"
                "ぼけ σ/m 0.50、傾き 72 度。★**局所閾値は「モジュールが 12 px 以下のときだけ**"
                "**照明ムラに強い**」—— 解像度を上げると BER 0.55 まで崩れる。"},
    {"id": "poc_document_scan", "task": "rectification", "data": "synthetic",
     "name": "書類スキャンの台形補正と影除去(良いところ取りは無い)",
     "summary": "既知のホモグラフィで歪ませて戻す。4 隅 RMS 1.91 px、何もしない 37.4 px から"
                "97.1 % 改善。★**影除去は必ず何かを壊す** —— 地を割ると紙の誤検出は 0 % に"
                "なるが薄い字が全部消え、局所コントラストを上げると薄字は残るが紙の 38-99 % を"
                "字にする。射影とアフィンの取り違えは例外を出さずに 32 倍悪化。"},
    {"id": "poc_camera_shake_deblur", "task": "restoration", "data": "synthetic",
     "name": "手ブレ除去はどこまで戻せるか(核が既知でも雑音が上限を決める)",
     "summary": "ブレ核を自分で決めて掛け、復元して元と比べる。核が厳密に既知でも取り分は"
                "無雑音 34.0 dB → SNR 20 dB で **1.8 dB**。最良の雑音対信号比は理論値と"
                "同じ桁で動く。核が **5.0 度**ずれると取り分が半減、**19.4 度**でゼロ点に"
                "負ける。アンシャープはどの条件でも 0.03 dB しか稼げない。"},
    {"id": "poc_superresolution_limits", "task": "upscaling", "data": "synthetic",
     "name": "超解像は情報を増やすか(単一画像では増えない)",
     "summary": "縮小してから戻して元と比べる。★**bicubic というゼロ点を上回れたのは最大 "
                "+0.036 dB** で、分解能は全手法が低解像側のナイキストで揃って死ぬ。鮮鋭化は"
                "勾配エネルギーを真値ちょうどに戻すが PSNR は 1.57 dB 落ちる。副画素ずれの"
                "16 枚合成は**標本化が足りないときだけ** +13.96 dB で本当に増える。"},
    {"id": "poc_focus_stacking", "task": "depth", "data": "synthetic",
     "name": "深度合成(絵は圧勝、深度はゼロ点に負ける場所がある)",
     "summary": "既知の深度地図から焦点位置を変えた画像列を作り、全焦点画像と深度を**別々に**"
                "評価する。絵は +14.9 dB の圧勝。だが深度は段差帯でゼロ点比 1.10(引き分け)、"
                "★**無テクスチャでは 0.13(8 倍負け)**。しかも突出度の信頼度は嘘の側が"
                "高く出る(0.9923 対 0.9630)—— 峰の絶対値で棄却すると RMS が 1.505 → 0.878 mm。"},
    # -- PoC 第 6 波 ------------------------------------------------------------- #
    {"id": "poc_template_tracking", "task": "registration", "data": "synthetic",
     "name": "テンプレート追跡(見失うより先に、静かにずれる)",
     "summary": "既知の相似変換で動画を合成して真値を握る。ゼロ点(更新なし全域探索)の床は"
                "0.79 px(整数座標のため)。毎フレーム更新のドリフトは log-log 傾き 0.456。"
                "★**ずれたフレームほど相関ピークが高い**(ドリフト検出の AUC 0.182 = 逆相関)。"
                "そっくりな別物体が併走すると、ずれた 152 フレームが**全部**校正しきい値を通って"
                "「見つけた」と報告する —— AUC 0.993 でも運用点が使えない。ピーク値と突出度は"
                "**得意な崖が逆**(平坦な遮蔽はピーク値、紛らわしい対象は突出度)。"},
    {"id": "poc_star_astrometry", "task": "metrology", "data": "synthetic",
     "name": "星の位置を測る(理論下限を下回ったら、それは推定できていない印)",
     "summary": "既知の天球座標に星を置き、既知の投影と PSF で合成するのでプレート定数まで"
                "真値が既知。**理論下限(Fisher)を下回った手法はゼロ**で、暗い端で下回って"
                "見えるゼロ点は真のずれへの感度 0.038 = 初期値を返しているだけ(散らばり"
                "0.2790 px は 1/√12 = 0.2887 と一致)。★予想が外れた 2 件: 既知 PSF の相関は"
                "標本化不足に**弱く**(FWHM 1.0 で 4 手法中最悪)、飽和画素を捨てる処置は"
                "**捨て方で符号が変わる**(重心なら 10 倍悪化、当てはめなら 121 倍改善)。"
                "偽解は 4000 回で 0 件でも「起きない」ではなく「測れていない」—— 総当たり"
                "通り数を掛けて初めて期待 5.77 件という使える数字になる。"},
    {"id": "poc_pigment_unmixing", "task": "separation", "data": "synthetic",
     "name": "多波長で彩色層を剥がす(勝ったのは「多波長」ではなく「近赤外」だった)",
     "summary": "層構造を Kubelka–Munk で合成して真値を握り、下絵検出・顔料存在量・褪色前の"
                "色の復元を 9 手法で比べる。**可視だけ 16 バンドに割っても RGB と同じ**"
                "(再現率 0.118 対 0.119)。近赤外 1 枚は面ごとには完璧(AUC 1.000)なのに"
                "全体では 1 本も閾値が引けない —— 絵具ごとの近赤外反射率の差が下絵の信号"
                "より大きいため。近赤外の差分は逆に**剥落部で盲目**(0.013)になる。"
                "★MNF が PCA に負けた: 雑音共分散を横隣との差で作るので、下絵の上での"
                "横差分エネルギー(他所の 3.9 倍)を雑音として白色化していた。"},
    # -- PoC 第 5 波: 母数の大きい応用 ---------------------------------------------- #
    {"id": "poc_white_balance", "task": "color", "data": "synthetic",
     "name": "色恒常性(どの手法にも「効く条件」があり、勝ち続ける手法は無い)",
     "summary": "既知の反射率チャートに既知の光源を掛けて合成し、角度誤差で測る。白パッチ法は"
                "素のチャートで 1.06 度と最良だが、**一番明るい 1 枚を外すだけで 8.45 度(8 倍)**、"
                "飽和 43% で 13.61 度 = ゼロ点に厳密退化する。灰色世界は有彩色が 60% を占めると"
                "29.79 度でゼロ点に負ける。**最適な p は場面ごとに 1 から ∞ まで動く**。"},
    {"id": "poc_panorama_drift", "task": "geometry", "data": "synthetic",
     "name": "パノラマの累積ドリフト(埋もれていた既存実装はゼロ点を上回らなかった)",
     "summary": "既知の回転列から 36 枚を切り出して 360 度で閉じ、閉ループ誤差で測る。ドリフトの"
                "伸びは log-log の傾き **0.894**(√N の予想は外れ、1 段あたりの偏りが効く)。"
                "**純回転 3 自由度で当てはめると 8 自由度より 2.3 倍良い**(0.275 → 0.118 px)。"
                "既存の `bundle_adjust_mosaic` は 36 枚中 30 枚を単位行列のまま返す。"},
    {"id": "poc_dehazing", "task": "restoration", "data": "synthetic",
     "name": "霞除去(律速は大気光ではなく透過率。薄い霞では除霞が害になる)",
     "summary": "大気散乱モデルで合成するので透過率もシーンも真値が既知。大気光を真値に"
                "差し替えても +0.01 dB、**透過率を真値にすると +3.07 dB** = 伸びしろの全部。"
                "帯別では近景 **-1.49 dB(害)**・遠景 +11.28 dB。視程 782 m 以上では"
                "全体でも負に転じる(beta 0.0025 で -3.39 dB)。"},
    {"id": "poc_surface_roughness", "task": "metrology", "data": "synthetic",
     "name": "表面粗さ(同じデータで Sa は合格・Sz は不合格になる標本間隔がある)",
     "summary": "PSD を指定して高さ場を合成するので Sq の真値が解析的に分かる。標本間隔 8 µm で"
                "**Sa は -3.5%(合格)なのに Sz は -19.8%(不合格)**。Sz は評価領域を広げると"
                "単調に増える = 「どれだけ長く見たか」を測っている。**最も頑健なのは Sa ではなく"
                "Sq**(予想が外れた。折り返しは 2 次モーメントを保つ)。"},
    {"id": "poc_vegetation_cover", "task": "segmentation", "data": "synthetic",
     "name": "植生被覆率(被覆率が当たっていて画素が全部外れる、が実際に起きる)",
     "summary": "合成群落なので被覆率も画素の帰属も真値が既知。発芽期・湿った土でゼロ点の"
                "被覆率誤差は **-0.2 pp(ほぼ完璧)なのに適合率も再現率も 0.000** —— 植生と"
                "答えた画素数だけが偶然一致していた。混合画素が 100% になると二値手法は"
                "生育段階で誤差の向きが逆転する(発芽期 +32〜+46 pp / 繁茂期 -14〜-36 pp)。"},
    # -- shape metrology ----------------------------------------------------------- #
    {"id": "profile_shape_inspection", "task": "metrology", "data": "synthetic",
     "name": "断面形状の検査(翼型・羽根。既知の欠陥を入れて検出できる大きさを出す)",
     "summary": "NACA 4 桁の閉形式を設計形状にして、厚み・キャンバー・前縁半径を測る。"
                "既知の量の欠陥を注入して測り返し、検査の床(同じ形どうしの偏差)と"
                "検出限界を数字で示す。**位置合わせが前縁の欠陥を後縁へ移す**ことも"
                "隠さず印字する。"},
    # -- fluid measurement -------------------------------------------------------- #
    {"id": "piv_flow_from_particles", "task": "flow", "data": "synthetic",
     "name": "粒子画像 2 枚から流れを測る(PIV。真値を自分で作って誤差を出す)",
     "summary": "既知の渦を撒いた粒子画像対を合成し、窓ごとの相互相関で変位場を出す。"
                "零方向への偏りと補正、多段、既知の系統誤差(ピークロッキング)、"
                "非圧縮の発散 0 による独立検算まで。**外れ値検定がここでは害になる**"
                "ことも隠さず印字する。"},
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
    {"id": "paper_figure", "task": "drawing", "data": "synthetic",
     "name": "学術図の図注: 引き出し線・寸法・角度・輪郭・スケールバー・差し込みを 1 枚に組む",
     "summary": "annotate の paper 族(引き出し線の衝突回避/番号+凡例/寸法線/角度/切りのよいスケールバー/"
                "方位/隅の拡大/マスク輪郭/経路文字/色分け+カラーバー/パネル文字)で 4 パネルの論文図を組み、"
                "layout の閉形式(肘・寸法値・角度・バー長・輪郭面積・セル矩形)と描画結果を突き合わせる。"},
    {"id": "precision_union_volume", "task": "workflow", "data": "synthetic",
     "name": "精度ユニオン型ストレージ(PrecisionUnion)を N-D の実データ様式で使う",
     "summary": "ラベルボリューム(無損失)と深度ボリューム(atol 量子化)をタイル別最小ビット深さで保持し、"
                "メモリ比・save/load のファイル比・遅延アフィン連鎖の一致を数値で確かめる。"
                "高エントロピー画像では勝たないことも同じ場で示す(honest な境界)。"},
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
    {"id": "lens_optimize_demo", "task": "optics_sensing", "data": "synthetic",
     "name": "実硝材で色収差を見て、減衰最小二乗でレンズを最適化する(lensopt)",
     "summary": "glass_catalog(Sellmeier)→ chromatic_shift で singlet/doublet の F-C 焦点移動、"
                "bend_singlet の Coddington 形状因子を optimize_lens が等凸から再発見、"
                "円錐 k=-n² と非球面 A4..A8 で無収差化、merit_function を 3 視野 × 3 波長で評価。"},
    {"id": "illumination_design_demo", "task": "optics_sensing", "data": "synthetic",
     "name": "検査照明を設計する(illumdesign)— リング/ドーム/同軸/バックライトの照度と欠陥コントラスト",
     "summary": "light_source → irradiance_map(cos⁴ 則で検証)→ illumination_uniformity、"
                "defect_contrast で暗視野/明視野の傷斜面コントラストとグレアによる顔料コントラスト希釈、"
                "lighting_sweep の最良仰角 = 90°−2×斜面、illumination_design の順位表と経験則の照合。"},
    {"id": "lens_calibration_loop_demo", "task": "optics_sensing", "data": "synthetic",
     "name": "設計レンズでカメラ校正を閉ループ検証する(calibration_views → calib)",
     "summary": "処方の実歪曲で平面ターゲットの多視点対応点を合成し、calib.camera_calibration が"
                "K_true(EFL/画素ピッチ)をどこまで再現するかを、無歪曲の放物面鏡(1e-6)と"
                "樽型歪曲の singlet(焦点距離バイアス+再投影 RMS)で突き合わせる。"},
    {"id": "lens_defect_dataset_demo", "task": "optics_sensing", "data": "synthetic",
     "name": "設計したレンズで欠陥画像を撮る(lensimage)— PSF・歪曲・センサ雑音つき学習データ",
     "summary": "singlet / doublet の実収差瞳から回折 PSF(Airy 第 1 暗環・Strehl)と歪曲表を出し、"
                "defectgen の欠陥をレンズ越しに描いて、同じ歪曲だけ通したマスク(IoU)と "
                "COCO 風注釈を書き出す。"},
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
    {"id": "appearance_structural_colour", "task": "appearance", "data": "synthetic",
     "name": "構造色を波長から作る(回折・薄膜干渉・異方性)",
     "summary": "色を塗らず分光反射率→CIE等色関数→線形sRGB。等色関数ȳピーク554nm、反射率1が白(1,1,1)、"
                "膜厚0が基板フレネルに厳密一致、λ/4が解析値0.077113、CD 1.6µm・Δsin0.35の1次が560nm、"
                "異方性ローブの伸び39:5。同条件でBD 0.32µmは可視域に届かず総量が1/3以下。"},
    {"id": "virtual_machine_vision", "task": "optics", "data": "synthetic",
     "name": "検査セルの光学デジタルツインから学習画像を真値つきで生成",
     "summary": "視野25.875mmと深度294.000mmが閉じた式に厳密一致、透過照明のシルエット19552画素=πr²と1%以内で"
                "部品は厳密に0。色を1画素も変えない凹凸だけの欠陥が拡散+3.41%対低角+93.46%=27倍、ラベルは"
                "照明によらず273画素。個体別bbox 4個の合計が合成マスクと一致。絞るほど高周波が残る。18,994枚/時。"},
    {"id": "glass_and_mirror_optics", "task": "optics", "data": "synthetic",
     "name": "ガラスと鏡面の光学を閉じた式で解く",
     "summary": "垂直入射0.0422=((n1-n2)/(n1+n2))²、Brewster 56.6°でp偏光が1e-15未満、臨界角超は厳密1.0、"
                "平板0.9191=2n/(n²+1)、Beer-Lambertがexp(-1)、Snell残差1e-12未満で全反射は光線ごと、"
                "プリズム最小偏角F/d/C=39.14/38.65/38.43°。金の色(1.00,0.67,0.38)はn,kから出る。"},
    {"id": "machined_metal_and_materials", "task": "appearance", "data": "synthetic",
     "name": "加工された金属表面と素材(粗い拡散・上塗り・布・木・濡れ・腐食)",
     "summary": "Oren-Nayarがσ=0でLambertと厳密一致し端は1.35倍、上塗りは下地の寄与を単調に減らす、"
                "布の縁光沢は鏡面と逆(正面1e-6/縁0.09)、濡れは0.50→0.357、腐食面積0.30→実測0.2995、"
                "すりガラスは直進+拡散=平板の透過率0.923077でエネルギー保存。接線場は同心円が半径と直交。"},
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
    {"id": "video_streaming", "task": "imaging_quality", "data": "synthetic",
     "name": "動画を 1 フレームずつ流して処理する(videostream リング/状態つき op/パイプライン)",
     "summary": "uint8 リング(float64 の 1/8)で背景差分し既知速度の物体を追う。台帳の一括 op と"
                "ストリーム版がフレーム単位で一致することを 6 op で確認。"},
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
    # -- machine-vision layout / optics ------------------------------------------ #
    {"id": "vision_layout_from_catalog", "task": "optics_layout", "data": "synthetic",
     "name": "型番から検査セルを組み、撮る前に成立するかを数字で決める",
     "summary": "カタログのセンサー/レンズ/照明を選び、①レンズがセンサーを覆うか"
                "②必要な寸法を分解できるか③そのフレームレートを伝送路が運べるか"
                "④実際に撮ったらどう写るか、を閉じた式で確かめる(optscene)。"},
    {"id": "studio_raytrace_scene", "task": "optics_layout", "data": "synthetic",
     "name": "光線を追ってレンダラを検算する(交点・法線・反射・遮蔽)",
     "summary": "絵の見た目でなく光線の量で答え合わせをする。交点 z、法線の向き、"
                "反射の法則 |d·n+r·n|<1e-14、遮蔽で可視率が落ちること、"
                "環境光の違いを固定してから studio 描画する(optscene)。"},
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
