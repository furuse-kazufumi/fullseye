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
    {"id": "poc_dimensional_inspection", "task": "metrology", "data": "synthetic",
     "name": "部品の寸法検査(サブピクセル計測と、埋もれていた実装の実地評価)",
     "summary": "SDF から解析的に部品を作り、既知の PSF と画素積分で合成して真値を握る。"
                "ゼロ点(大津の整数幅)比 **41 倍**、スロット幅の偏り -0.5000 → -0.0113 px、"
                "合成不確かさ 0.0196 px = 0.245 um。★壊れるのは「ぼけ」ではなく"
                "**エッジ間距離 / PSF 幅**で、3.09 を切ると偏り 0.05 px 超 —— しかも 1.58 まで"
                "「対が見つかった」と答え続ける(失敗を返さない)。★**縁の定義を宣言しないと"
                "16 px = 200 um 動く**(サブピクセルの 3 桁上)。丸い縁は必ず小さく出る"
                "(直径誤差 ≈ -σ²/ρ を実測で確認)。真値をきりの良い整数に置くと"
                "副画素の周期誤差が消えることも示す。"},
    {"id": "poc_cell_counting", "task": "segmentation", "data": "synthetic",
     "name": "細胞の計数と分割(計数が合っていて分割が全部外れる点がある)",
     "summary": "既知の位置・大きさ・重なりで細胞を配置して真値を握る。★**偏り +0.3 個"
                "(0.4 %)なのに分割誤り 13.3 件**という点が実在する(過分割 +1 と過統合 -1 が"
                "相殺する)。★**過分割は重なりに反応しない** —— 密度を 5 段振っても過分割の"
                "列はほぼ一定で、過分割は種の撒き方が、過統合は重なりが決める別原因。"
                "★「最適な h は密度で動く」は基準を書かないと真偽が決まらない(偏り基準では"
                "1.1→0.0 と動き、1対1 基準では 0.4 で動かない)。縁の規約だけで計数が 13 % 動く。"},
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
    {"id": "poc_dic_strain", "task": "metrology", "data": "synthetic",
     "name": "DIC ひずみ計測(2 度の回転が 600 µε の嘘のひずみを作る)",
     "summary": "斑点の中心を変形写像で移してから描き直すので、真値が補間を通らず厳密。"
                "`piv_cross_correlate` が偏り 0.0002 px / 散らばり 0.0022 px(ゼロ点比 167 倍)"
                "で optical flow を 1 桁上回り、明るさ 0.7 倍 +0.15 でも 3.7e-15 px しか動かない。"
                "**剛体回転 2 度で微小ひずみが -699 µε(鋼の降伏の 3 割)を返す**——"
                "Green-Lagrange は代数的には 0 だが、実測では勾配の誤差が乗って"
                "推定器によっては悪化する。だから既定を置いてはいけない。"
                "★この PoC の所見は**一度書き直している**(既存の PIV 23 op を見落とした)。"},
    {"id": "poc_particle_sizing", "task": "metrology", "data": "synthetic",
     "name": "粒度分布(D50 が合う点は「正確」ではなく打ち消し)",
     "summary": "撒いた円板の半径が真値なので D10/D50/D90 を厳密に検算できる。"
                "面積率を 1.9 → 28.2 % と振ると D50 の誤差は **-4.9 % → +4.5 %** と"
                "単調に動き、13.8 % で 0 を横切る —— そこは正確なのではなく、"
                "**融合 28 件(大きい側へ)と縁切れ 19 件(小さい側へ)が釣り合った**"
                "だけ(塊 140 個中)。★充填率で融合を落とす当たり前の対策は "
                "+6.5 % → **-11.3 % と過剰補正**して悪化する。"
                "個数基準と面積基準の D50 は同じ画像で 1.66 倍違う。"},
    {"id": "poc_allsky_cloud_cover", "task": "photometry", "data": "synthetic",
     "name": "全天カメラの雲量(画素を数えると雲の位置で 1.45 倍動く)",
     "summary": "魚眼(等距離射影)で撮った空の雲量。**同じ角半径 8 度の雲を天頂角 0 → 82 度へ動かすと推定が 0.00789 → 0.01142(真値はどちらも 0.00973)*"
                "*。閉形式 (θ/sinθ)/(θmax²/2) と最大差 0.0026 で一致し、重み sinθ/θ を掛けると 6 通りとも 0.999〜1.000 に直る。★予想は逆だっ"
                "た —— 引き伸ばされるのは天頂ではなく**地平線側の方位方向**。太陽周りの偽陽性は雲ゼロの晴天で雲量 7.25 %、幾何 -5.0 % と検出 +38.0 % が打ち消して"
                "合計 +29.7 % になる。"},
    {"id": "poc_barcode_1d", "task": "decoding", "data": "synthetic",
     "name": "1 次元バーコードが読めなくなる境界(誤読と読み取り不能を分けて数える)",
     "summary": "自作 4-run 符号なので真値は数字そのもの。★**無傷では 6 つの読み方が全部 24/24 で差が出ない** —— 道具の良し悪しは壊してからしか分からない。★★「読めな"
                "い」と言える実装かどうかで誤読率が 6 倍変わる(厳格 7.3 % / 寛容 46.1 %。**寛容のほうが成功率も高い**)。検査数字は寛容の誤読を 46.1 → 2.6 %"
                " にするが 0 にはしない。傾きの崖はatan(60/210)=15.95 度の予測に対し実測 15.5〜16.0 度。ぼけは σ/m に畳めるが傾きは畳めない。"},
    {"id": "poc_crack_width", "task": "metrology", "data": "synthetic",
     "name": "コンクリートのひび割れ幅は 1 画素より細い(数える幅と、積分する幅)",
     "summary": "★同じマスクから規約 2 通り(2·EDT と 2·EDT−1)で幅がちょうど 0.20 mm 違う —— **測ろうとしている量と同じ大きさ**なので、規約を書かない「幅 0"
                ".4 mm」に意味は無い。★★輝度欠損の総量は畳み込みでも画素化でも保存されるので、**積分法は 0.05 mm(0.25 px)まで連続に追える**(偏り -0.15〜+0."
                "05 %)。その保存を 1e-8 の桁で検算する。"},
    {"id": "poc_fabric_defect", "task": "diagnostics", "data": "synthetic",
     "name": "周期のある地に埋もれた欠陥(まとめた ROC が隠すもの)",
     "summary": "★★線欠陥・斑点・ムラを 1 本の ROC にまとめると AUC は高く見えるが、**種類別に描くとムラが 0.5 付近(でたらめ)**になる検出器がある。しかもそれは「格子除"
                "去 + 低周波除去」という現場でいちばん普通のレシピ —— **照明ムラを消す処理が、検出したいムラも消す**。格子のノッチは地の残差を 2 桁下げるが、低周波を落とすかどうか"
                "の 1 行で AUC が壊れる。"},
    {"id": "poc_fiber_orientation", "task": "metrology", "data": "synthetic",
     "name": "繊維の配向分布(角度は 180 度周期。素朴に平均すると 90 度ずれる)",
     "summary": "★★算術平均は真の平均 177.9 度を **105.6 度**と報告する(誤差 -72.3 度)。0 度と 179 度は同じ向きなのに、数として平均すると打ち消して 90 度"
                "へ寄る。2 倍角の円形平均に変えると**同じ画素・同じ構造テンソルのまま誤差 1.4 度**。★真値が 3 通りある(本数基準 / 撒いた長さ基準 / 視野内の長さ基準)。対照"
                "群では 3 つの開きが 0.0135 しか無いのに、長い繊維ほど揃う場面にすると 0.0368 に広がり、本数基準と比べて配向度が +4.9 % ずれる。"},
    {"id": "poc_gear_tooth_metrology", "task": "metrology", "data": "synthetic",
     "name": "歯車の歯形(偏心は 1 次、歯は z 次。歯が 1 枚欠けると両方が混ざる)",
     "summary": "真値はインボリュート曲線の閉形式。★偏心 0.025〜0.200 mm を振ると 1 次振幅は-3.5〜-0.5 % で当たり、24 次成分はほとんど動かない —— 周波数で切"
                "り分かる。★★**歯が 1 枚欠けると全周波数に漏れる**: 偏心ゼロの歯車から 1 枚落としただけで1 次振幅が 0.1851 mm 立ち、これは実在する偏心 0.050 m"
                "m の 3.7 倍。偏心 0.050 mm の歯車では 0.0483 → 0.2251 mm(**+350 %**)。欠けを先に外さないと偏心の推定が汚れる。"},
    {"id": "poc_moire_screen", "task": "imaging_quality", "data": "synthetic",
     "name": "パネル検査のモアレは「本物のムラ」と区別できるか(打ち消しと窓長)",
     "summary": "うなりの周期は 2 つの周期から閉形式で出る(予測 20.00/6.67/4.00 px 対 実測 19.69/6.65/4.00)。★★低域通過でならすと σ=8 px で*"
                "*合計誤差 +0.9 %** —— 完璧に見えるが内訳は**漏れ +8.3 % / 減衰 -7.4 %**。対照群 2 本(縞だけ / ムラだけ)を置かないと見えない。★★素の"
                "ノッチは **δ·L が整数のときだけ**効く(+0.7 % 対 +39.1 %)—— 原因はスペクトルリーケージで、**撮り直しではなく解析窓長という software 側の"
                "問題**。"},
    {"id": "poc_nuclei_ploidy", "task": "photometry", "data": "synthetic",
     "name": "蛍光核の積分輝度から倍数性を出す(面積では分かれない)",
     "summary": "★★誤分類は**面積(真値)15.4 % / 積分輝度 0.0 %**(log の分離度 1.5σ 対 6.2σ)。★★**「測った面積」は面積ではない** —— 固定しきい値"
                "のマスク面積だと 8.0 % と真の面積より良くなる。ln(測定/真値) を ln(明るさ) に回帰すると傾き +0.26・相関 0.97 で、**面積という名前で DNA 量"
                "を漏らしている**。★★飽和 8.8 % のとき DNA 指数は 2.002 と真値ぴったりだが、裾落ち +5.8 % と飽和 -5.3 % が釣り合っているだけ。"},
    {"id": "poc_particle_tracking", "task": "flow", "data": "synthetic",
     "name": "粒子追跡を (行, 列, 時刻) の体積として測る(誤リンクの向きは 1 種類ではない)",
     "summary": "★★粒子 400 個で曖昧 0.1 %・欠測 24.5 %。位置を真値にして欠測だけ消すと拡散係数の比が3.429 → 0.925 —— **同じ「誤り率」でも D が 3.7"
                " 倍動く**。誤り率を 1 本の数字にまとめた時点で、検出を増やすのかリンクを厳しくするのかが決まらなくなる。★★1 歩は 1.7 px しか無いのに欠測誤リンクの飛距離は最近"
                "接距離(4〜21 px)で決まるので、曖昧が D を 7 % 下げるあいだに欠測は **240 % 上げる**。"},
    {"id": "poc_sea_ice_concentration", "task": "separation", "data": "synthetic",
     "name": "海氷密接度(混合画素をどう数えるかで答えが変わる)",
     "summary": "★ゼロ点(1 本のしきい値で 2 値化)は密接度 0.35・相関長 3 セルで **-4.2 ポイント**外し、線形混合分解は +0.02。対照群(標本化そのものの誤差 +0."
                "01)が効いていて、**偏りは標本化ではなく数え方**だと分かる。★★同じしきい値・同じ真値でも塊の大きさで偏りが変わり(-4.2 → -0.2 ポイント)、**周長率で説明が"
                "つく**(偏り = -0.80 × 周長率 + 0.015、R² = 0.984)。第 3 成分(薄氷)は必ず配分され、同じ数字が真値の定義で -4.4 / +2.7 ポイント"
                "に化ける。"},
    {"id": "poc_solar_limb_darkening", "task": "photometry", "data": "synthetic",
     "name": "縁が暗い天体の輪郭はどこか(周辺減光と「50 % 法」)",
     "summary": "★★**「偏りは減光係数 u に比例」という予想は外れた** —— u=0.2 の -0.56 px を比例で伸ばすと u=0.8 は -2.2 px のはずが実測 **-12"
                ".76 px(5.7 倍)**。★対照群(ぼけ σ=0)が機構を分けた: u≤0.5 の偏りを作っていたのは減光ではなく**シーイング**、u>0.5 でだけ幾何が残る。★★ぼ"
                "けの効き方はしきい値で符号が変わり、0.26 付近に打ち消し点が実在する(u を 0.3 にすると 0.38 へ動く)。★黒点が動かすのは半径(0.33 px)ではなく**中心"
                "**(0.005 → 0.591 px、122 倍)。"},
    {"id": "poc_strain_history", "task": "metrology", "data": "synthetic",
     "name": "クリープ試験のひずみ履歴(累積か直接か。交点は時間軸には無かった)",
     "summary": "★★**いちばん大きな予想外れ** —— 終端(6 % ひずみ)で累積 61 µε / 直接 1878 µε と**累積が 31 倍良く、どの時刻でも勝ち続けた**。交点は時間"
                "軸ではなく**雑音の軸**にあり、σ=0.20 で初めて直接が勝つ。★★累積の誤差はランダムウォークでもなかった: 雑音を切ってもほぼ変わらず、散らばりの log-log 傾き"
                "は 0.5 ではなく -0.03。支配しているのは揺らぎではなく **PIV の系統誤差**で、散らばり(14 µε)より偏り(60 µε)が大きい。"},
    {"id": "poc_thermal_drift_metrology", "task": "calibration", "data": "synthetic",
     "name": "カメラの熱ドリフトが寸法計測に効く量(分離できるのは歪みがあるから)",
     "summary": "★★**予想が逆だった** —— 歪みが無ければ主点ドリフトは寸法に**厳密に 0**、焦点距離ドリフトは位置に依らない一定の倍率誤差で、位置を振っても何も分離できない。歪み "
                "k1=-0.12 を入れて初めて主点ドリフトが半径に比例する誤差を作る。1 次式 err(R)=a+b·R に当てはめると a=+224.5 ppm(対照条件 +225.3、差"
                " 0.4 %)、b=+0.2388 ppm/px(主点のみ 0.2190 + f のみ 0.0197 = 0.2387)。★対照群で誤差の床を先に測ると 1 枚 117 ppm"
                "。**ドリフトが床を超えるのは ΔT=1.6 K から**。"},
    {"id": "poc_timelapse_growth", "task": "segmentation", "data": "synthetic",
     "name": "成長のタイムラプスを時空間の連結成分として測る(合体はいつ起きたか)",
     "summary": "★ゼロ点(フレーム独立の計数)は思ったより強く、塊の数が減るフレームは真の合体時刻の1 コマ以内に出る。壊れるのは数ではなく**その先** ——「どれとどれが」「合体か消失か」"
                "「同時に 2 組か」。★★**空間の離散化は合体を早める**(予想が外れた: 画素は面積を持つので円が半画素ぶん太り、まだ接していないのに繋がる。-1.16 / -0.04 フ"
                "レーム)。一方フレーム格子への丸めは必ず遅らせる(+0.17 / +0.94)—— **逆向きの 2 つが混ざる**。"},
    {"id": "poc_traffic_counting", "task": "flow", "data": "synthetic",
     "name": "(x, y, t) で数える(通過台数とオクルージョン、そして L/V という 1 つの定数)",
     "summary": "★**疎な自由流ではスリット法は仮想ループ(1-D)に勝てない** —— どちらも 10/10 で同点。同じ計数列の情報しか使っていないので当然で、2-D にした見返りは台数で"
                "はなく**速度(誤差 0.02 % 以下)**と、壊れ方が絵で見えること。★★同じスリット画像から2 通りの数え方が出て**壊れ方が逆向き**: 帯を全部数えるとフレーム間隔で"
                "千切れて過大(Δt=16 で 10 → 49)、計数線と交わる帯だけなら過大は起きず見逃しだけになる。"},
    {"id": "poc_veiling_glare", "task": "imaging_quality", "data": "synthetic",
     "name": "迷光がコントラスト計測を壊す(MTF 合格・黒レベル不合格を同じレンズで作る)",
     "summary": "★★裾の割合 g を 0 → 0.20 に振ると刃のエッジ SFR の MTF50 は -4.2 %(仕様 0.22 に対し合格のまま)なのに、同じ像の黒レベルは 0.0 → "
                "15.7 %(仕様 3 % に対し不合格)。6 段階のうち **3 段階で判定が割れる**。★★予想が外れた —— 盲点を作るのは**周波数ではなく基準レベルの取り方**で、正"
                "弦チャートの絶対コントラストは周期 4 px でも 32 px でもちょうど (1-g)×コアの MTF。★答えが窓で変わり収束しない(黒四角 16 → 256 px で黒レベ"
                "ル 19.6 → 4.5 %)—— **測る範囲を宣言しない迷光の数字は意味を持たない**。"},
    {"id": "poc_vessel_network", "task": "morphology", "data": "synthetic",
     "name": "血管網を抜いて分岐を測る(ヒゲ、分岐近傍の径の過大、指数の脆さ)",
     "summary": "★★**きれいな合成画像にはヒゲが出なかった**(予想外れ)—— 端点を持つ枝の最短が 15 px で、ヒゲと呼べるものが 1 本も無い。**ヒゲは細線化ではなく境界のざらつき"
                "が作る**(振幅 0 → 0.35 で余分な分岐が 3 → 34 個)。★★ヒゲを刈る長さのしきい値は解像度で成り立ったり成り立たなかったりする: 原寸ならヒゲ最長 9 px "
                "と本物最短 15 px が分かれて12 px で完全に切れるが、半分の解像度では 7 px と 6 px で重なり、**どのしきい値でも両方をゼロにできない**。「刈れば直る」"
                "は解像度に依存する主張だった。"},
    {"id": "poc_water_level", "task": "metrology", "data": "synthetic",
     "name": "河川の水位を斜め写真から測る(透視を無視した行番号は弓なりに外れる)",
     "summary": "★★**「水位が高いほど誤差が大きい」は外れた** —— 行番号を 2 点の目盛りで直す素朴法は**弓なり**に外れる(アンカー上で 0、その間で最大 -6.4 cm)。行 ="
                " (aZ+b)/(cZ+d) を直線で近似した弦と双曲線の差だから。★符号を決めるのは水位ではなく**内挿か外挿か**(内挿 -6.6 cm / 下ペアの外挿 +16.3 cm"
                " / 上ペアの外挿 +14.6 cm と逆符号)。★★同じ反射が検出器で正反対の顔を見せる: しきい値交差は静かに -18.9 cm、キャリパーは検出列 149 → 9 で黙っ"
                "て止まる。"},
    {"id": "poc_weld_bead_profile", "task": "metrology", "data": "synthetic",
     "name": "レーザー三角測量の断面から溶接ビードを測る(測れなかったところを 0 と書く罪)",
     "summary": "★★入射角 40 → 60 度で左つま先の未測定が 18 → 44 % になると、0 埋めのアンダーカット深さは 0.4507 → **-0.0000 mm**(真値 0.45"
                "00)で「健全」として通る。NaN なら 0.0672 mm と「44 % が未測定」が残る。★★幅と脚長は**逆向きに壊れる**(0 埋め -16.9 % / NaN +11"
                ".2 %)ので 1 つの指標に畳むと打ち消す。★ゼロ点(最大値の行、整数)は RMS 0.0169 mm で、サブピクセル 4 種はいずれも 1 桁良いが、**いちばん凝った推"
                "定量が最良とは限らない**。"},
    {"id": "poc_wound_area_tracking", "task": "metrology", "data": "synthetic",
     "name": "創傷面積の経時変化(較正の誤差は面積に 2 乗で効く)",
     "summary": "★★ゼロ点(1 枚目だけで較正)で撮影距離 Z/Z0 を 0.90 → 1.10 と振ると面積誤差は"
                "**+23.58 % → -17.36 %**。閉形式 (Z0/Z)²-1 との差は最大 0.278 pp(= ラスタライズの床)"
                "だが、線形近似の -2ε は 3.58 pp 外れる —— **「2ε」は 1 次項であって法則ではない**。"
                "★★治癒定数 k の推定が壊れる: 距離が 1.2 %/day 漂うと真値 0.1200 に対し 0.1424"
                "(**+18.7 %**)。★ゼロ点は**散らばりがいちばん小さい**ので、ばらつきでは気づけない。"
                "★標識を創面の外へ回す(外挿 → 内挿)だけで平均 |誤差| が 1.11 % → 0.10 %。"},
    {"id": "poc_xyt_event_surface", "task": "geometry", "data": "synthetic",
     "name": "到達時刻面を (x, y, t) の等値面として取り出す(2-D の動画を 1 枚の 3-D の面として測る)",
     "summary": "★★**放物線補間は線形より悪い。しかもしきい値の置き場所で反転する** —— θ=0.5 なら線形 0.0209 / 放物線 0.0406、θ=0.2 なら 0.0744 /"
                " 0.0205。ガウス波形の変曲点θ=exp(-1/2)=0.6065 で 2 次の項が消えるからで、閉形式で言える。★等値面(`marching_cubes`)の時間軸稜線の"
                "頂点は**線形補間そのもの**(最大差 9.9e-07 ms)。★★合流線の上では勾配が 0 に落ちて速度が 1e12 px/ms へ発散するが、その場所は双曲線 r_A-r_"
                "B=c·Δt で**撮る前に予測できる**(対照群の 1 源では発散しない)。"},
    {"id": "poc_photoelasticity", "task": "metrology", "data": "synthetic",
     "name": "光弾性(縞から応力。壊れるのは応力が大きい所ではない)",
     "summary": "円板の直径圧縮は閉形式の応力場を持ち、偏光系は fullseye の `mueller_element` "
                "で組める(教科書の I=sin²(δ/2) と 125 通りで最大差 2.2e-16、"
                "水平直径の力の積分は誤差 0.000 %)。位相シフトで δ は復元できるが "
                "**(δ,θ) ↔ (-δ,θ+90°) の二義性で 2.7 % の画素は符号が反転**する。"
                "巻き戻しが壊れる場所は 2 つ(1 縞 2 画素未満・変調が落ちる等方点)で、"
                "どちらも撮る前に予測できてマスクで外せる。"},
    {"id": "poc_thermography_ndt", "task": "diagnostics", "data": "synthetic",
     "name": "パルスサーモグラフィ(『測れない欠陥』の正体が時間窓だった)",
     "summary": "裏面断熱平板の厳密解が真値なので、深さの推定を近似ゼロで検算できる"
                "(早期の log-log 勾配 -0.5000、d=√(παt*) が 0.3 % で成立)。"
                "**縦横比の限界に見えたものは物理ではなく当てはめ窓**で、25 秒 → 4 秒に"
                "切るだけで小欠陥 8 個の誤差が +59〜+612 % から ±15 % に入る。"
                "なだらかな加熱むら 76 % は検出をほとんど壊さない(**予想が外れた**)——"
                "壊すのは欠陥と同じスケールのむらだけ。"},
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
    # -- 2026-09-07: 入口 op と、例ゼロだった台帳 7 族の穴埋め ------------------------- #
    {"id": "gallery2d_bridge", "task": "family_coverage", "data": "synthetic",
     "name": "入口 op(img_to_*、category=bridge)を総なめ", "summary":
         "1 枚の画像から点群・1-D 信号・動画・体積・ライトフィールド・複素場・光子列・"
         "ビート立方体・行列・キーポイント・モノジェニック信号を作る 12 op を、型契約・"
         "有限性・決定性・ノブの効きに加え op ごとの閉形式(z = 値×10×s、フレームの変位、"
         "距離ビン …)で検証する。"},
    {"id": "dem_geodesy_tour", "task": "terrain", "data": "synthetic",
     "name": "地心座標と地球の丸み(測地⇄ECEF・地心格子・曲率落ち・緯度で変わるセル寸法)",
     "summary": "赤道・極・楕円体方程式・法線移動で ECEF を検算し、3700 点の往復誤差を高さ別に印字する"
                "(楕円体面 2e-9 m、20 km で 4e-6 m —— docstring の 1e-7 m は地表付近の値)。"
                "地心緯度と測地緯度の差 0.19 度、曲率落ちの表、Web メルカトル分解能、"
                "等角度格子の東西傾斜が北緯 60 度で素朴計算だと半分になることを閉形式と突き合わせる。"},
    {"id": "dem_terrain_analysis_tour", "task": "terrain", "data": "synthetic",
     "name": "地形解析ツアー(粗さ・TPI・D8 流向・河道・地平線仰角・可視領域)",
     "summary": "平面・柱・円錐・V 字谷・壁という答えを数えられる地形で 6 op を通す。TRI=√(3/4)|∇z|·cell、"
                "谷底の集水量 W(i+1) と河道マスクのセル単位一致、壁の仰角 atan(H/d)、"
                "壁の影の長さ e·d0/(e-H)。欠測の outlet 方針は「他に下る先が無いときだけ欠測へ」と実測。"},
    {"id": "piv_field_analysis_tour", "task": "flow", "data": "synthetic",
     "name": "PIV の派生 op を一巡する(場の量・可視化・採点・アンサンブル・時間統計を閉形式で検算)",
     "summary": "剛体回転・膨張・せん断の線形場で Q 基準/渦回転強度/ひずみ速度/渦度を厳密に検算し、"
                "Lamb–Oseen 渦で窓変形が多段より誤差を下げることと、Q の面積が閾値で 4 倍変わることを出す。"
                "ZNCC 採点は壊した窓だけ落ち、アンサンブル相関は外れ本数を 52 %→5 % に減らし、"
                "時間統計の RMS を独立な経路で突き合わせ、centroid のピークロッキングと 4 方向の色を固定する。"
                "**RMS だけでは差が見えない**ことも隠さず印字する。"},
    {"id": "profile_frame_tour", "task": "metrology", "data": "synthetic",
     "name": "断面輪郭の枠を作る(正規化・等弧長の取り直し・上下面の分離・位置合わせを閉形式で検算)",
     "summary": "既知の相似変換を掛けた翼型が正規化で機械精度で戻ること、粗密 2 万倍の円が等弧長で一様な角度刻みに"
                "なること、NACA 0012 の上下面が閉形式の ±y_t に 6e-6 で乗ること、7 度・並進の剛体変換を chord/rigid が"
                "取り戻しつつ**2 % の拡大は吸収しない**ことを出す。開いた曲線の拒否も確かめる。"},
    {"id": "shapestat_landmark_tour", "task": "shape_statistics", "data": "synthetic",
     "name": "形態統計(Procrustes / GPA / 形態 PCA / 左右非対称 / 面距離)を真値つきで一巡",
     "summary": "既知の 2 変形モードを持つ合成ランドマーク群で、相似変換の復元(1e-9)・GPA 平均の一致・"
                "PCA 往復・Mahalanobis 閉形式・正中面の復元・±0.2 の符号つき面距離を検算し、"
                "align=True が大きさを食う点と、面の再当てはめが非対称量を縮める点を印字する。"},
    {"id": "shape2d_morph_descriptor_tour", "task": "shape_descriptors", "data": "synthetic",
     "name": "XLD 輪郭 → 不変記述子 → 対応点ワープ(区分アフィン / TPS)を真値つきで一巡",
     "summary": "from_xld で (row,col) 点列を取り、invariants の回転/拡大/移動/始点不変を 1e-9 で確かめ、"
                "add_frame_corners + 2 種のワープで恒等・平行移動・1 点の着地・面積比 1.25^2 を検算する。"
                "(row,col) のまま渡す座標順の事故が例外なく黙って外れることも示す。"},
    {"id": "blob_split_tour", "task": "blob_analysis", "data": "synthetic",
     "name": "融合した 2 円板を距離変換 → h-maxima の種 → 分水嶺で割る(閉形式で検算)",
     "summary": "blob_distance の中心値=半径、blob_seeds の種を h-maxima 閉形式と画素単位で照合、"
                "blob_split の 4 領域・前景保存を確かめる。h より低い塊にも種が立つ点と、"
                "割れ目が番号の大きい種の側へ食い込む偏りを隠さず印字する。"},
    {"id": "annotate_paper_tour", "task": "drawing", "data": "synthetic",
     "name": "経路に沿う文字の配置表とパネル文字 (a)(b) を閉形式で検算",
     "summary": "annotate_text_path_layout の弧長・位置・傾き・used を閉形式と突き合わせ(L 字経路で 0/90 度)、"
                "annotate_panel_label の板の縁が margin に乗ること・text_box と画素同一であることを確かめる。"},
    {"id": "poc_exoplanet_transit", "task": "photometry", "data": "synthetic",
     "name": "系外惑星トランジットの相対測光(深さと継続時間は別々に壊れる)",
     "summary": "目標星だけに 10 ppt の周辺減光つきトランジットを仕込んだ 240 枚を star_detect → frame_align → aperture_photometry で測る。ゼロ点は雲で深さ +72 ppt、比なら -0.13 ppt / T14 -0.9 fr。★比較星の選び方で残差 rms が 6.0 倍変わるが T14 の誤差は動かず、逆分散重みは生の分散で決めると雲に騙されて単純和の 1.52 倍悪い。★★開口 1σ の崖は予想した重心誤差ではなく op の開口マスクの階段(supersample=8 で不動の星が理論比 1.69、32 で 0.93)。検出限界 SNR=5 は暦既知で 1.48 ppt(理論 1.45)、暦未知は 2.0 ppt で深さより先に継続時間が壊れる。★★ドリフト 2 px とフラット 3 % は単独で 0.16 / 0.08 ppt、掛け算で 0.94 ppt、4 px で 2.97 ppt(真値の 30 %)。"},
    {"id": "poc_metal_grain_size", "task": "metrology", "data": "synthetic",
     "name": "結晶粒度 G(面積法と切片法は別の崖で落ちる)",
     "summary": "Voronoi の粒と真値ラベルで ASTM E112 の G を厳密に検算できる(閉形式 π/(4√λ) と +1.5 %、E112 の 2 式は同じ組織で +0.32 段ずれる)。★ゼロ点の面積法は雑音だけ -0.02・むらだけ -0.40 が**両方で +3.82** と相互作用で死ぬ。★★粒界の途切れの崖は面積法 **7.2 %**、切片法 **40.7 %** ―― 予想の 29.3 % は外れ、マスク上で消える粒界は f の 0.76 倍だった。closing 9×9 は 13 点中 12 点で素の版より悪い。混粒の全体 G 7.82 に ±0.5 で入るタイルは 4/64。"},
    {"id": "poc_colocalization_crosstalk", "task": "separation", "data": "synthetic",
     "name": "蛍光の共局在と漏れ込み(Pearson と Manders は別の場所で壊れる)",
     "summary": "2 色の小胞画像を真の共局在率 0〜100 % で合成し、漏れ込み [[1,α],[β,1]]・PSF・光子雑音を掛けて Pearson r と Otsu-Manders を測る。★無関係な 2 色が α=β=10 % で r=0.203 / M1=0.133、対称漏れ込みなら r=2α/(1+α²) で 0.5 を超える崖は α=0.282(予想 2−√3=0.268、片側なら 30 % でも 0.289)。★★単染色対照から分離すると r は戻る(0.007)が **Manders は戻らない** —— Otsu より下の裾が落ちて 100 % でも 0.705(閉形式の予想 0.756)。生の M1 が真値を横切る α=0.222 は裾落ちと漏れ込みの相殺。★★ぼけは Pearson を動かさず(0.011→0.089)Manders だけ 0.044→0.946 に押し、σ=2.5 px で Otsu の前景が小胞から細胞体へ飛び移る段差。★Costes のシャッフル検定は漏れ込みだけの r を p=0.000 で有意と言い、Costes 自動しきい値は漏れ込みで台まで落ちて M2=1.000 に崩壊する。"},
    {"id": "poc_mri_bias_field", "task": "segmentation", "data": "synthetic",
     "name": "MRI バイアス場と組織面積(GM と WM は逆向きに壊れ、足すと隠れる)",
     "summary": "楕円殻の脳ファントムで 3 組織の真値面積を握り、乗算場と Rician 雑音を掛けて 3 クラス大津で測る。★★振幅 30 % で **GM +20.2 % / WM -7.7 % なのに GM+WM は +0.0 %**(脳実質体積は両方間違っても動かない)。★雑音を止めると符号が反転(GM -11.8 %)し、崖は幾何予測 30 % に対し実測 17.5 %。★★log I をそのまま平滑する補正は**場が無くても GM +81.8 %** 壊す(解剖が場に見える)が、分割残差の Wells 型反復なら 40 % でも +1.8 %。周波数の崖は基底で決まり(多項式 32 / ガウス 16 / 格子 B スプライン 8 px)、4 px では理想補正だけが残る。SNR 15 で場なしでも GM +8.5 %(裾の予測 +6.3 %)。"},
    {"id": "poc_river_surface_velocity", "task": "flow", "data": "synthetic",
     "name": "河川表面流速を斜め動画から測る(速度の誤差と流量の誤差は別物)",
     "summary": "★★ゼロ点(斜め画像のまま 1 尺度で m/s に直す)は近岸 +0.31 / 遠岸 -0.28 m/s と符号が逆、見かけの川幅 3.3 m(真値 8 m)で流量 -57 %。正射化で速度 RMS 0.074 m/s・流量 -7.8 %。★★対照群の流量 -3.0 % のうち -2.5 % は岸 0 との台形積分だけで生じ、速度と無関係。★★密度 0.05 % の崖は nan 0 % なのに外れ値旗 44 %、アンサンブル相関は外れ窓を 46 → 44 % としか救わない。★窓を広げても岸の速度は「窓幅×勾配」の予想(0.12〜0.28 m/s)より桁で小さい -0.008 m/s、代わりに流量が -1.1 → -7.0 %。★★静止した映り込みは細かいときだけ効き、引かれてから(速度比 0.70)張り付く(0.03)、時間中央値引きで 0.998。★dt の崖は 1/4 則でなく対の消失(探索上限を外しても同じ k=4)。"},
    {"id": "poc_prnu_camera_fingerprint", "task": "diagnostics", "data": "synthetic",
     "name": "カメラ指紋 PRNU(枚数で育ち、保存ボタンで消える)",
     "summary": "★★清浄条件では同一カメラ PCE 中央値 2192 / 別カメラ 15.7(AUC 1.000)。★指紋は √N で育つが N=1 では最尤がゼロ点に負ける(ΣWI/ΣI² が W/I に退化)。★★JPEG 相当の量子化は品質 50 相当で PCE 3.6 %(量子化利得² の予測 3.8 %)、0.5× 縮小で 1.5 % ―― 幾何の上限 20 % より下で、**デノイザがなまった指紋を被写体として取り去る**。★★K=0 のカメラでも同じ背景 30 枚から PCE 1706 の偽指紋が出る。"},
    {"id": "poc_screw_thread_metrology", "task": "metrology", "data": "synthetic",
     "name": "ねじのピッチ・フランク角・有効径(傾きは左右フランクに逆符号)",
     "summary": "★列幅の FFT はピッチを**半分**と答える(単条ねじの上下輪郭は P/2 ずれる)。★★軸の傾き 3 度で左右フランク角は 33.18 / 26.74 度 ―― 半和が真のフランク角、半差が傾き。片側フランクのピッチは 1 次で ±3 % 狂い、頂点間隔は 2 次(-0.12 %)。★ぼけ σ=4 px で壊れるのは d2(-0.06 %)でなく α(-0.57 度)。★標本化の崖は α(8 px/山)→ d2(4 px/山)→ FFT の P(2 px/山 まで当たり、1.5 px/山 は 3.0 px に折り返す)の順。"},
    {"id": "poc_change_detection_misreg", "task": "registration", "data": "synthetic",
     "name": "変化検出と位置合わせ誤差(偽陽性はエッジの帯、しかも崖つき)",
     "summary": "★★2 時期の差分は位置合わせ誤差でエッジが全部「変化」になるが、その偽陽性はずれ 0.3 px まで雑音の床で **0.5 px から崖**(PSF から予測した δ*=τσ√2π/C=0.351 px と一致)、3 px で 7175 px。★エッジ総長×ずれの比例則は 3 px で 0.78 倍だが崖を説明せず、PSF と雑音を入れた台帳予測は 0.84〜1.07 倍 ―― 漏れるのは樹冠テクスチャ(1.5 px で 482 px、勾配則で 409 px と予測できる)。★★位置合わせ 3 経路は残留 0.02〜0.13 px まで戻すが、唯一の位相相関は 3-D 用の整数精度で残留 0.72 px、その偽陽性 995 px は「ずれだけ」の掃引を同じ残留で読んだ 915 px に乗る(位置合わせ後も同じ崖)。★変化の大きさの崖は面積の重なり則 (1−δ/(s√2))² でなく画素被覆則(被覆 > τ/C)で決まり、36 点で差 0.000。伐採は完璧な位置合わせでも検出率 0.33、照明差だけの偽陽性 17198 px は放射補正で 0、histogram_match は変化そのものを消しにかかって 383 px 出す。"},
    {"id": "poc_leaf_disease_area", "task": "segmentation", "data": "synthetic",
     "name": "葉の病斑面積率(等級は色の軸より葉マスクと縁の定義で決まる)",
     "summary": "閉形式の葉と既知面積の病斑に土・照明むら・白飛び・影を重ねた合成葉。緑の固定しきい値は土だけで **+65.2 pt**、射影 G で葉を切り a* で病斑を切ると標準場面で -0.8 pt。★白飛びの鏡面反射は a* に**偽陽性しか出さない**(20 % で +12.6 pt、偽陰性 0.0 ―― 予想した符号の逆転は起きない)、白を足しても動かない色相なら +2.0 pt。★★縁のぼけ幅 4 px では境界を 25 %/75 % 線のどちらに置くかだけで **±3.5 pt** 動き(Steiner の式が 0.4 pt 以内で予測)、等級境界 ±3 pt の 40 枚は土の上では 19〜35 枚が誤等級、黒布 + 明るさ葉マスク + 色相固定なら 8 枚。"},
    {"id": "poc_beam_modal_video", "task": "vibration", "data": "synthetic",
     "name": "動画からのモード同定(f は当たる、ζ が先に嘘をつく)",
     "summary": "★★片持ち梁 3 モードの自由減衰を妨害入り動画に合成し、位相法と PIV で f_n / ζ_n / MAC を測る。**f_n は 0.06 Hz 以内で当たるのに ζ_1 は同じ時系列から半値幅 0.0778 / 包絡線 0.0188 / 当てはめ 0.0181(真値 0.02)**。半値幅の 3.9 倍は窓長 2 s の分解能下限(予測 0.0738)そのもの。★振幅を 0.02→2 px で掃引すると崖の順番は f → ζ → MAC_2 → MAC_3 で、0.02 px では f_1 誤差 +0.030 Hz のまま ζ_1 が真値の 0.23 倍。★照明 100 Hz の折り返しは fps 48.5 でちょうど f_1 = 3.00 Hz に乗り、輝度のゼロ点は ζ を出せない。★phase_displacement の wrap_limit_px(0.018 px)は崖を予測せず、先端 3.1 px でも壊れなかった。"},
    {"id": "poc_bone_trabecular_thickness", "task": "metrology", "data": "synthetic",
     "name": "骨梁の厚さ Tb.Th・間隔 Tb.Sp・骨体積率(平板モデル vs 直接法)",
     "summary": "★真値が複数ある: 幅の長さ加重平均 104.8 µm、面積加重 113.9、最大内接円の定義 121.6、平板モデル 118.4 µm ―― どれと比べるかで 9〜16 % 動く。★★解像度の崖は平均でなく分布に来る(60 µm 画素で重なり 0.83 → 0.09。平均は量子化 -29.5 % と大津の太り +27.1 % が打ち消す)。★★雑音は斑点(σ 0.10 から)と途切れ(σ 0.15 から)で Tb.Sp を逆向きに引き、opening r=1 は細い骨梁ごと切る(途切れ 5 → 16 本)が面積オープニングは斑点だけ消す。★カップ状バイアス β=0.6 は全体の BV/TV -0.5 % なのに中心/縁の Tb.Th が 84/112 µm ―― 場所で壊れる。log 域のまま大津を取ると +19.6 % 太る。"},
    {"id": "poc_weld_radiograph_porosity", "task": "diagnostics", "data": "synthetic",
     "name": "溶接 X 線透過像の気孔検出と等級(等級を 1 段間違える割合)",
     "summary": "★ゼロ点は余盛のつま先を気孔に数える(塊 124 個、面積 15.19 mm² vs 真値 7.93)。★検出の崖は CNR = 16.12·d² で先に予測できるが、Rose の CNR = 4 では 0.50 mm と外れ、平滑化 + 最小面積 3 px の条件で 0.58 mm 予測 / 0.57 mm 実測。★★背景推定 op の窓上限(矩形オープニング 9 px)は 2.0 mm から検出率 50 % を割り 2.5 mm で 0 % の崖 ―― op を選ぶことが測定範囲を選ぶ。★直径は 3 通りで偏りの向きも大きさも違う(しきい値径は 0.6 mm で -48 % 縮み、体積径は μ 既知で -2〜-6 %、キャリパ径は予想「太る」に反し 0.8 mm 以上で -9〜-16 % 縮む)。★散乱 SPR=1 で体積径 -22.6 %(予測 -20.6 %)。★★等級を 1 段間違える画像: ゼロ点 90 % → 体積径 23 %(内訳 直径 20 %・見落とし 10 %・偽陽性 7 %)。"},
    {"id": "poc_solar_el_inspection", "task": "diagnostics", "data": "synthetic",
     "name": "太陽電池 EL 検査(暗い = 不活性ではない。種別ごとに測る)",
     "summary": "★★ゼロ点(Otsu の暗画素率)は 21.7 % で真値 4.77 % の 4.6 倍 ―― 暗画素の 42 % はフィンガー/バスバー、33 % は結晶粒とビネッティングで、本物の不活性領域は 20 %。等級は D(真値 C)。★行・列プロファイルで格子を割り、孤立領域 / 断線帯 / クラックを別々の門で取ると面積率 4.61 %(-0.15 ポイント)・クラック再現率 0.88〜1.00・断線 8/8 で等級 C。★★sk_frangi は最大値で正規化するので、校正線は画像中でいちばん強くないと尺度を固定しない(実クラックと同じ線は 0.69、幅 3 px の黒線は 1.00)。校正なしが壊れるのは欠陥ゼロの側で偽クラック 147 px ―― 良品ほど偽検出が出る。★崖: 結晶粒コントラスト c=0.24 から偽クラックが出て断線が飲まれる(ヘッセ行列の予測 1.48 は 6 倍外れ)、クラック幅 1.25 px(幅 × 深さの線形則で予測 1.38 px)、光子数 K=50 で断線 7/8(予測 12 は 4 倍楽観的)。cos^4 の当てはめは行列プロファイルが先に吸うので要らなかった。"},
    {"id": "poc_tree_ring_dendro", "task": "metrology", "data": "synthetic",
     "name": "年輪年代学(年数の誤差と幅の相関は別に数える)",
     "summary": "★髄から 1 本の放射線でピークを数えるゼロ点は 24 方向中 18 方向でしか年数が合わないが、**間違えた 6 方向でも幅系列の相関は中央値 0.900** ―― 年数と幅の相関は別の壊れ方をする。★★極座標展開(髄中心)→外縁で半径を正規化→θ 方向メディアン→24 扇形の測定線の合意で 36 年ちょうど・幅の相関 0.996。★髄の推定誤差 20 px でも幅の相関 0.994: 予想「偏心は幅を cos で変調する」は外れで、**cos が乗るのは半径(傾き -14.9 px)、幅は 1 次で打ち消す(-0.02 px)**。減るのは髄近くの年数で幾何の予測どおり 2 年。細い年輪の崖は合意法 2.5 px(閉形式モデルの予測 1.9 px)・ゼロ点 3.0 px(予測 2.9 px)。ぼけ σ 4 px でゼロ点は欠落でなく**偽輪 13 本**を数える。"},
    {"id": "poc_solder_fillet_aoi", "task": "diagnostics", "data": "synthetic",
     "name": "はんだフィレットの AOI(3 リング照明は傾きの 3 段量子化器)",
     "summary": "接触角と断面積で決まる円弧のフィレットに 3 リング照明(GGX を窓で積分)を当てた合成 AOI。★★接触角 18° の凹円弧は壁で 72° まで立ち、最低リングでも見えるのは高さの **28.8 %**(予測)―― 色帯の傾きを積分する素朴な推定は真値の 0.284 倍。色が変わる**位置**から円弧を壁へ外挿すると自由円弧で +1.7 % ± 5.3 %、爪先がパッド端に固定されると -42.3 %。★位置ずれ **0.16 mm** で爪先が 30° を超えて緑帯が消え、真値は上がっているのに良品が「不足」になる(真値が不足になるのは 0.28 mm)。★粗さは予想と違い暗部の縁を動かさず、0.5 で赤帯の消失と同時に壊れる。ゼロ点(パッド平均色 ΔE)は良品 56 % / ブリッジ 68 % を NG にして区別せず、円弧推定は良品 98 % / ブリッジ 100 % / 浮き 88 %(取りこぼしは 8.7〜11.0° の小さな浮き)。"},
    {"id": "poc_fresco_craquelure", "task": "forensics", "data": "synthetic",
     "name": "絵画のひび割れ網(壊れるのは分岐次数だけ)",
     "summary": "★★乾燥ひびと経年ひびをボロノイ網の真値 2 種で作り、セル径・直線度・次数 4 割合の 3 指標で分ける(真値 18.0 vs 45.2 px / 0.960 vs 1.000 / 0.20 vs 0.83)。**質感と斜光で動くのは次数 4 割合だけ**(経年 0.87 → 0.64 / 0.70)で、予想した「直線度が壊れる」は外れた。★幅の崖も質感の爆発も来ない(0.15 px で再現率 0.696、c = 0.64 で偽陽性 0.382)—— 線検出は線に沿って積分する。★sk_frangi は分岐点で落ちて斜光でセルが 52 → 16 個に崩れ、暗さそのもの(cv_blackhat)が全リッジ op に勝つ。"},
    {"id": "poc_mesh_quality_repair", "task": "geometry", "data": "synthetic",
     "name": "メッシュの健全性診断と修復(直した分だけ欠陥は消え、量は戻らない)",
     "summary": "★オイラー標数は 6 種の欠陥のうち 5 種に盲目で、穴 6 個と重複面 6 枚を同時に入れると健全な部品と頂点・辺・面・χ が 1 つも違わなくなる。★★「水密になった」と「体積・表面積が戻った」は別の指標 —— 幅ゼロの割れは 2 通りに直せてどちらも水密になるが、表面積の誤差は 0.0000 % と +0.1201 % に分かれる。★穴埋め後の体積は球欠の閉形式で予測できる(θ=32° で予測 -1.644 % / 実測 -1.642 %)が、表面積は縁が階段なので予測 -2.145 % に対して実測 +6.868 % と符号すら逆。★★簡略化は体積より先に曲率を壊し(50 % 削減で体積 -0.019 %・曲率 p95 +31 %)、自己交差は水密・多様体・χ をすべて通り抜ける(表面積 +4.414 % / 体積 -0.332 %)。"},
    {"id": "poc_lidar_terrain_change", "task": "terrain", "data": "synthetic",
     "name": "斜面の土量を測る(縦に引くか法線で測るか、そして合わせすぎの罠)",
     "summary": "既知体積の掘削 164.2 m3 と堆積 133.7 m3 を傾斜地に仕込み、2 時期の点群から DoD(格子の引き算)と M3C2(法線方向)で測り返す。★予想「斜面では cos だけ体積が縮む」は外れ ―― 水平投影面積で積むと cos は約分し、誤差は 0〜40 度でどれも -0.011 %。間違うのは体積でなく厚さで、深さの比は sec θ に一致する。★★変化なしの対照が偽掘削 83.8 m3(真値の 51 %)を出し、しきい値を入れて 18.1 m3 に落ちる ―― **しきい値は飾りではなく本体**。★★変化域が視野の 33 % あると位置合わせが変化を吸い、正味は真値の 12.6 % に潰れる(trim 0.6 で 101.1 % に復帰)。M3C2 の利得は傾斜からしか来ない(検出限界の比は平地 1.18、40 度 3.40)。"},
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
