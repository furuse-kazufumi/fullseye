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
    {"id": "poc_cad_scan_deviation", "task": "metrology", "data": "synthetic",
     "name": "CAD と実測点群の差分検査(合わせた分だけ欠陥が消え、無い所にへこみが出る)",
     "summary": "解析形状の部品に既知のへこみ・反り・摩耗を仕込み、ゼロ点(位置合わせなしの最近傍距離 19.03 mm)から粗合わせ→ICP→符号付き偏差→公差外面積まで通す。**位置合わせが吸えるのは J=[n|X×n] の 6 次元だけ**で、局所へこみの読みは 3.7 % しか薄まらないのに、★**反りでは真値 1.2 µm の中央に深さ 121 µm の偽のへこみが出る**(閉形式の予測 -a/3 = -120 µm、引かれ方の傾きは実測 -0.322 対 予測 -1/3)。★稜線で最近傍が隣の面へ飛び、欠陥ゼロ・雑音ゼロ・姿勢は真値の対照でも 66.5 mm^2 の偽の公差外領域が出る。崖は 4 本(初期姿勢・密度・雑音 σ√(2/π)・片面欠測)で測り、素の直方体を対照に置くと**対称形でだけ残差が別解を隠す**ことも分かる。"},
    {"id": "poc_dfm_thickness_overhang", "task": "geometry", "data": "synthetic",
     "name": "造形しやすさを形から測る(しきい値に貼りついた面と、丸めで飛ぶ判定)",
     "summary": "★★サポートが要る面積はしきい値 45 度の両側で段差になり、44.9 度の 185.22 mm^2 が 45.1 度で 576.10 mm^2 —— 0.2 度で 3.11 倍。部品に「ちょうど 45 度の斜面」が 390.32 mm^2 あるため。★その段差は等値面の取り方で消える —— 距離場から取ると 390.88 → 0.87 mm^2(100 % 消失、44.9 度でも解析値の 195 % 過大)、平滑化 sigma=1.5 voxel でも 12 % 削れる。★肉厚は 2 voxel 刻みに潰れ、予想した「内接球なら 1 voxel 刻み」は外れて侵食と 12 点すべて同値。刻みを持たないのはグレー値の探針だけ(誤差の中央値 0.011 mm)だが、2 voxel を切ると壁 2 枚を 1 枚と数え 4.500 mm を返す。★工具の隙間は両方向に誤判定し、粗さ 0.500 mm で 1.500 → 2.000 mm と太って入らない工具を通す。★向きを 6 通り振っても最良で 0.86 倍にしかならず、効いたのは設計(斜面を 5 度ずらすと 0.28 倍)。"},
    {"id": "poc_symmetry_restoration", "task": "geometry", "data": "synthetic",
     "name": "対称性を使った欠損復元(文化財・化石。仮定した対称面が崖になる)",
     "summary": "左右対称な仮面(高さ場が x について厳密な偶関数)の完全形と対称面を真値に持ち、片側を球で削って復元を測る。★崖は角度 1.39 度(84 分角)・位置 1.41 mm —— そこを超えると対称復元(RMS 0.81 mm)は素朴な穴埋め補間(1.60 mm)に負ける。★幾何で先に予測して当てた: 鏡像は 2 sin α・(回転軸からの距離)だけ動くが面に沿った成分は面が吸うので、法線成分の予測が相対誤差 4.6 %(素朴な 2d sin α は 50.6 %、位置ずれでも素朴な 2t は 62.1 % 外し法線成分は 1.9 %)。★★壊れ方は 2 種類で、α=1.5 度では復元 RMS がまだ 1.69 mm(ゼロ点並み)なのに足した点の 91 % は真の面から 1 mm 以上浮いた「無い面」。★★欠損は対称面をずらす前に別の軸へ飛ばす —— 失った点が 3.1 % を超えると PCA 候補が 1.09 対 2.18 から 6.74 対 4.90 へ逆転し、それでも復元 RMS 2.85 mm は「何もしない 13.28 mm」より良く見えるので残差では気づけない。★予想は外れ、重心が 3.86 mm 動いても残差を掃引する精緻化は 0.105 mm まで戻す(粗い面のずれの 98 %)。★★本当に対称でない形(片側装飾 3 mm + ねじれ 2.2 mm)では、面が真値でも装飾が 3436 mm^3 捏造されるか 3495 mm^3 消され、復元部は定義上ぴったり対称になるので「対称だから正しい」という検算が原理的にできない。"},
    {"id": "poc_print_warpage_risk", "task": "geometry", "data": "synthetic",
     "name": "積層造形の反りと剥離(面積の履歴で決まる分と、決まらない分)",
     "summary": "★★最終形状だけを見る予測器はどんな形でも厳密にゼロを返す(2.712e-21)—— 断面の重心の定義から Σ a_k (z_k - z_bar) = 0 になるので、反りは層の履歴にしか入っていない。ゼロ点(底面積・最大断面積・体積)の順位相関は 3 つとも -0.25 で、いちばん底面積の大きい平板がいちばん反らない。★閉形式は 2 層で Timoshenko(1925)と比 1.000000 で一致し、24 層で κh/ε = 2.4174 に飽和する(背を高くしても反らない)。7 形状中 4 形状で誤差 0.4 % 以内だが、★★層面積の履歴が 1 mm^2 も違わない三つ子のたわみは 0.4109 / 0.3809 / 0.3271 mm と 26 % 開く —— 面積の履歴は「置き場所」に構造的に盲目。★予想した「細い首で平面保持が壊れる」は外れ(首 16 → 1 mm で比 0.9998 → 1.0030、しかも反りは 0.4344 → 0.3532 mm と減る)、崖は細長比 L/H = 1.0(誤差 4.2 / 8.4 %)。力学の崖より先に表現の崖が来て、設計 0.25 mm の首はボクセル 0.50 mm では跡形も無く部品が 2 つに分かれる。★★同じ形・同じ体積・同じ底面積でも層厚 1.00 → 0.25 mm でたわみ 4.63 倍だが、「単位高さあたりの収縮が一定」と置き直すと 1.16 倍 —— ε の定義を書かずに「薄い層は反る」と言ってはいけない。★剥離は応力で決まらず(dx 2.00 → 0.50 mm で 9.53 → 11.89 MPa と収束しない)、端 6 mm の力は 0.3 % で収束するのに EIκ からは予測できない(変動係数 97 %、三つ子で 48 倍差)。効くのは端の材料の背で、底板 1 → 8 mm で力は 1.5 → 698.1 N の 479 倍。"},
    {"id": "poc_bev_sensor_fusion", "task": "perception_templates", "data": "synthetic",
     "name": "鳥瞰図への多センサ融合(px で合格の校正が、遠くでは長さになる)",
     "summary": "★★再投影 1 px = 1/f ラジアン = 距離 R で R/f メートル。f=265 px なら 22 m 先で 0.083 m/px で、yaw 0.20 度 = 0.98 px の「サブピクセル合格」でも BEV では既に 0.077 m ずれる。★★融合(IoU 0.7033)が単センサの最良 0.5417 を上回る分は**すべて視界**から来る —— 横に 1.8 m 離した 2 センサの影は 20 m 先で食い違い、左の遠方車は LiDAR が 24 セル / カメラが 0 セル、右は 0 / 52 セルと綺麗に入れ替わる。★予想が外れたのは崖の尺度で、点がセルを跨ぐ割合は幾何の予測と最大差 0.0553 で当たるのに、yaw 0.5 度で 68 % が跨いでも IoU は 5.8 % しか落ちない(効くのはセル 0.2 m でなく車幅 1.9 m)。★同じ yaw 1 度から最大値則は偽占有 96 セル、平均則は見逃し 85 セルを作るが IoU は 0.6583 と 0.6600 でほぼ同じ —— IoU 1 本では急停止と衝突を区別できない。★信頼度重み則は「なめらかに混ざる」はずが、雑音モデルが交差しないので評価セルの 80.4 % で LiDAR が勝ち、**実質「LiDAR 優先」の順位規則に退化**していた。"},
    {"id": "poc_ct_void_morphology", "task": "tomography_3d", "data": "synthetic",
     "name": "X 線 CT のボイド形態(合否 1 個の数字は、寿命に効く形に盲目)",
     "summary": "★★体積率を 3.000 % に厳密にそろえたまま位置・形・近接だけを変えた 5 条件を接合層に仕込むと、2 値化してボイド率だけを出すゼロ点は 2.46〜2.63 %(開き 0.17 ポイント)としか分けない ―― 合否 5 % なら全条件合格、1 % なら全条件不合格。同じ 5 条件を形態は桁で分ける(界面離隔 60.0 対 10.0 µm、扁平度 0.97 対 0.25、最近接 160.0 対 20.0 µm)。★応力の代理指標(界面に接するボイドの投影面積)は 0 → 14.68 % まで動き、界面に接する扁平ボイドは同体積の球の 2.09 倍(閉形式 1.93、実測との差は 1 ポイント以内)、連なりの跨ぎ率は 13.1 倍。★★崖の予想が 2 つとも外れた ―― ボクセル 60 µm(球の径の半分 58 µm を超える)でもボイド率は 3.21 % と崩れず(線形の被覆率で積むと体積は保存される。格子の位相を 3 通り振ると ±1.36 ポイント振れるだけ)、先に死ぬのは形のほうで、扁平度は 60 µm で測れなくなり界面欠損率は 14.16 → 9.78 %(-31 %)と**合格の側へ**落ちる。離隔も『42 µm より粗いと判別不能』は外れで、順序は最後まで残るが値は嘘になる(真値 0 µm の接触側がボクセル 1.0〜1.3 個に貼りつき、真値 42.2 µm の層中央は 120 µm と 2.8 倍)。★しきい値 0.50 で連なりのボイドが融合して塊が 24 → 5 個に落ち、その瞬間『最近接ボイド間隔』は 20 → 340 µm に跳ねる ―― 指標が壊れるのではなく測っている対象が黙って入れ替わる。連結半径の掃引は設計どおり(連なり 10.0 µm / 予測 8.7、散在 75.0 µm / 予測 70.5)で、雑音 sigma 0.15 では偽ボイドが 24 → 1794 個に爆発するのにボイド率は 2.61 → 2.94 % しか動かない。**寿命そのものは測っていない ―― 示せたのは合否 1 個の数字の盲目さまで**。"},
    {"id": "poc_battery_ct_degradation", "task": "tomography_3d", "data": "synthetic",
     "name": "電池セルの内部劣化を CT で測る(膨れの何割が外から見えるか)",
     "summary": "積層電極 17 層(ピッチ 0.320 mm)とアルミ缶を真値つきで組み、順投影→ビームハードニング→光子雑音→FBP まで通してから測る。ゼロ点=外形だけの指標。★電極が 10 % 膨れて積層が 0.340 mm 伸びても、クリアランス 0.240 mm が飲むので**外形に出るのは 29.4 %**(幾何の予測どおり)。その割合は劣化の大きさではなく**セルの初期クリアランスで決まる設計量**で、0.40 mm のセルでは何も見えない。★端板は周辺固定なので中央だけふくらみ、**ノギスは体積等価な平均の 3.6 倍**を読む(+0.235 対 +0.066 mm、予測 4.0 倍)。★★外形のふくらみを揃えた 3 つ(一様膨れ / 局所膨れ / ガス空隙)は缶の高さ 6.313 mm でばらつき 0.000 mm ―― 外形では原理的に分けられないが、内部は層厚 0.190/0.187/0.173 mm・空隙率 0.00/0.00/5.20 %・平面度 0.0156/0.0428/0.0784 mm で分かれる(一様と局所は層厚では分かれず**平面度が分ける**)。同じ外形を作る内部の膨張体積は 0.6715 対 0.3880 mm3 と 1.7 倍違い、**外形の変化量から中の劣化量は逆算できない**。★層厚は真値 0.200 に対し 0.175 mm と 12.5 % 過小(ぼけで縞が正弦波に近づき、微分ピーク間隔が半周期 0.160 mm へ引かれる)なのに、同じプロファイルの**層間隔は 0.321 mm で真値を保つ**。★★崖は 2 つ予測してから測った ―― 標本化定理なら voxel/層厚 0.80、隙間 0.120 mm を 2 標本で跨ぐなら 0.30。**実測は 0.30 で、狭いほうの特徴(電極厚ではなく隙間)が崖を決めた**。★雑音とビームハードニングでは壊れ方が違い、フォトン数 1000 分の 1 でも層数は 1 枚しか動かないのに空隙体積は -10.3 → -24.8 %、ビームハードニングは外形も層厚も動かさず空隙だけを -9.1 → -14.7 % 痩せさせる。SoH や寿命は測っていない(そう明記した)。"},
    {"id": "poc_structure_4d_deterioration", "task": "metrology", "data": "synthetic",
     "name": "構造物の 4D 差分(点検のたびに測る場所がずれる)",
     "summary": "★★劣化ゼロで測り直しただけで最近傍差分(C2C)は中央値 21.07 mm・最大 42.64 mm の「劣化」を返し、しきい値 1 mm の偽の補修候補 5.098 L は本物 5.882 L の 87 % に達する(法線方向なら 0.55 / 3.55 mm)。★偽の劣化は点間隔でほぼ決まり(密度 300→2400 pt/m² で 26.83→10.14 mm、予測 0.5/√ρ との比 0.930〜0.994)、★★「密度を揃えればよい」は逆で 30 / 50 mm 格子に間引くと 21.39 → 22.30 / 24.44 mm と悪くなる —— 揃えるとは細かいほうを粗いほうに合わせることだから。★★劣化が全域に広がっていると合わせは平均を吸い、支間中央のたわみ 2.999 mm は 0.933 mm(吸われた割合 0.689、閉形式 2/3 = 0.667)に潰れて支点に -1.737 mm の偽の隆起が出る(端だけで合わせても 0.296 は吸われる)。★残差姿勢の作る嘘は測る前に (t+ω×(p-c))·n で出せ(雑音床と直交合成して比 0.969〜1.010)、腹板には ω_y が、下フランジには ω_z が厳密に効かない —— 面 1 枚では検算できない。★★点検を 3 回に増やしても速度は良くならない(等間隔 3 点の傾きは両端の差分と厳密に一致、差 1.8e-15 mm/年)。★★押し出し形状の橋軸方向は「決まらない」のでなく法線推定の雑音が決めてしまい(推定 n_x² は設計の 11〜7207 倍でキャンバーに無反応)、その嘘は平面でなく支承の円柱にだけ 41.2 mm の偽の水平移動として出る一方、支承の沈下 4.00 mm は -0.14 mm に消える。"},
    {"id": "poc_scan_to_bim_asbuilt", "task": "metrology", "data": "synthetic",
     "name": "設計モデルと実物の差(部屋が合わせの自由度を吸い、余りを他の部材へ配る)",
     "summary": "半空間・直方体・円柱の CSG で部屋を組み、壁の傾き +3.00 mrad・壁の開き 2.50 mrad・床の勾配 -1.50 mrad と反り 12.0 mm・柱の半径 +6.5/-4.0 mm・開口のずれ 25/18 mm を既知量で仕込んで 3 か所から走査する。★ゼロ点(点群まるごとを設計へ合わせて平均距離を 1 個)は誤差ゼロの建物 2.20 mm・両方入り 3.61 mm で **1.41 mm しか動かない** —— 場所ごとに符号の違う偏差を平均が打ち消す。★もう 1 つの素朴な数字である対称 Chamfer 距離は 25.67 → 26.17 mm と 0.50 mm しか動かず、しかも値が平均距離の 10 倍以上 —— 後ろ半分が「設計面から見た最近点」なので**欠陥でなく走査できなかった所の広さ**を測っている(スキャン位置を増やすだけで「品質が上がる」)。★★合わせは剛体モードを吸うだけでなく**余りを他の部材へ配る**: 全体 ICP のあと壁は真値の 69 %、床の勾配は 41 % に痩せ、**完全に水平な天井が +0.89 mrad 傾いて見える**。これは ICP を走らせる前に閉形式で予測でき(偏差の場を J=[p×n|n] の 6 次元へ射影 → ω_y=-0.89 mrad)、実測との差は最大 0.05 mrad。剛体でない「壁の開き」(+2.46 対 真値 +2.50)と対称な反りは残るので、**動くのは剛体モードだけ**。判定の食い違いは合わせない 0 件 → 全体 ICP 2 件 → 床と 2 壁を基準 4 件と、合わせるほど増える(基準合わせでは無傷の天井が +1.69 mrad で不合格になる)。★崖は欠測率では決まらない: 同じ 90 % でも無作為なら 0.098 mrad、下から順に残す構造的欠測なら 1.234 mrad(12.6 倍)。効くのは残った面の高さ L(2.86 → 0.19 m)で、σ√12/(L√N) の予測は L>=1.1 m で 21 % 以内(予測 0.161 / 実測 0.204)、L=0.19 m では 62 % 外す。★★レジストレーション誤差は系統誤差なので点を増やしても消えず、同じ 2514 点で雑音だけなら偽の傾き 0.040 mrad が姿勢誤差 1.0 mrad で 0.189 mrad(4.7 倍、信号対雑音 75 → 15.9)。★混合画素に壊されるのは幾何でなく推定器で、RANSAC の平面は 0 → 40 % を通して最大 0.058 mrad しか動かないのに、min/max の obb から出す窓の高さは最大 27.74 mm を**単調でなく**外す(前段に平面の inlier 取りを挟むと 0.60 mm)。★そのとき割り当ての正答率は 99.87 → 99.01 % としか落ちず、正答率という 1 個の数字はこの壊れ方に盲目。★平面度 PV は完全に平らな床でも 4.89 mm(許容 ±7 mm の 70 %)を雑音だけで使う(RMS なら 2.03 mm)。道具の穴: 6 枚の半空間の交わりは箱の厳密 SDF と内側は 0.0000 mm 一致だが外側の角で最大 1006.6 mm 過小評価する。"},
    {"id": "poc_pipe_wall_loss", "task": "metrology", "data": "synthetic",
     "name": "配管内面の減肉を展開図で測る(軸ずれと管底腐食は同じ 1 周期に居る)",
     "summary": "★軸が 4.0 mm ずれるだけで、腐食ゼロの真円の管の 44.8 % が減肉と判定される(偽の体積 116378 mm^3 = 本物の孔食 777 mm^3 の 149.9 倍)。中心が e ずれた円は展開図で振幅 e の 1 周期の正弦波になる、と幾何で先に予測してから測り、差は最大 1.84 ポイント。崖はしきい値そのものの所に立ち、0.40 mm で 0 %、しきい値と同じ 0.50 mm で 4.95 %(ここだけ予測 0.00 % を外す ―― 雑音 σ=0.05 mm が旗を立てている)。★軸ずれは 1 周期だけでなく 2 次で全周にも効き、平均半径が -e²/(4R) 縮む(予測との差 0.0016 mm)。オフセット 6 mm は全周減肉 0.60 mm の 30 % を打ち消して減肉を隠す。★★分離できないのは軸ずれと管底腐食で、下水管でいちばん多い三日月形の腐食はその 79 % が k=1 に居る ―― 1 周期を消す補正は偽陽性を 45.37 → 34.56 % に落とす代わりに管底腐食の検出率を 100.0 → 34.4 %、体積を -68 % にする。現場の定番(スライスごとの円あてはめ)はさらに全周減肉を 52.0 → 36.1 % に落とし、溶接ビード高さを 1.58 → 0.01 mm(真値 1.50)にする ―― 全周に一様な形は何であれ見えなくなる。★★「軸をどこまで自由に動かしてよいか」の 1 本のつまみに全部が並び、予想は「上げるほど本物が消える」だったが実測は両端で落ちる U 字だった: 平行移動だけ(0 次)は傾きを表せず残った 1 周期が腐食を打ち消して 8.1 %、1 次で 92.4 %、2 次で 85.5 %、毎スライス自由で 48.6 %。偽の減肉は単調に減る(22.19 → 11.25 → 0.00 %)。いちばん良い次数は「軸は直線、管はたわむ」という物理そのもので、孔食 99.1 % / 全周減肉 76.2 % / 管底腐食 85.5 % を残して偽陽性 0.76 %。★その最良の補正にも崖があり、管底腐食が管長いっぱいまで伸びると検出率 86.6 → 10.9 %、推定した最深部 0.96 → 0.32 mm(真値 1.5)―― z によらず一定な腐食は軸のずれと幾何的に区別できない。同じ管を CT 側(ボクセル 1.5 mm)から測ると崖の場所が変わり、左右対称のはずの全周減肉が 4.91 / 6.04 mm と 1.13 mm 食い違う(真値の減肉 0.60 mm より大きい)。"},
    {"id": "poc_recycling_sorting", "task": "separation", "data": "synthetic",
     "name": "混合廃棄物の材質選別(消せる汚れと消せない汚れは代数で決まる)",
     "summary": "材質スペクトルをガウス吸収帯の閉形式で作り、汚れ・濡れ・傾き・重なり・混合画素を既知量で仕込んで真値を握る。★ゼロ点(総当たりで最良の band 対 1721/2021 nm の比)は綺麗な場面で 0.972 と強く、SAM の 0.995 にほとんど負けない —— 差が出るのは劣化してから。★★不変性は代数で予測できる: 乗算汚れ 0→0.8 で生 SAM 0.995→0.990、加算ベースライン 0→0.6 で生 SAM 0.995→0.827 に対し 2 次微分は全水準 0.995。★予想は 2 つ外れた —— 濡れは 2 次微分で 0.818 まで耐え(生 SAM 0.282)、理由は 2 階微分がガウス帯を 1/σ² で重みづけるから((43/70)²=0.37)。連続体除去は加算が弱いと勝ち(0.983 対 0.865)強いと逆転する(0.736 対 0.827)。★★特徴の無い金属は微分で消える(再現率 0.06 → 平坦度の門で 0.98)。★★乗算汚れが壊すのは分類でなく検出(0.990 のまま、検出込みだと 0.716)。対照群の効く順序は 濡れ +0.148 > 乗算汚れ +0.015 > 混合画素 +0.012 > 傾き +0.009 > 加算汚れ -0.127 で、★加算汚れは止めると下がる(破片をベルトから浮かせていた: 未検出 1.1→17.3 %)。★★「似た組が先に壊れる」はライブラリの話で、雑音だけなら予測 1 位 PP-PE が的中(相関 0.84)なのに全部入りでは 紙-金属 に入れ替わる。★境界を捨てると再現率 0.822→0.834 なのに組成誤差は 3.42→3.50 pp と悪化し、線形混合分解は劣化なしで境界を 0.003 で当てるのに全部入りでは 0.183。"},
    {"id": "poc_machine_condition_fusion", "task": "diagnostics", "data": "synthetic",
     "name": "熱・振動・形状の総合診断(束ねても情報が増えない条件)",
     "summary": "★★3 センサ融合 100.0 % は**振動のみ 100.0 %** と同点 —— 基準条件では熱も形状も 1 pt も足さない。融合が効き始めるのは振動が壊れてからで、雑音 σ=1.6 で 45.8 % → 78.1 %(+32.3 pt)。★★芯ずれは軸心のずれ 1 つが原因なので振動・熱・形状の**どれ 1 個でも 100.0 %**(真値の重症度との相関 2X 0.843 / 継手温度 0.841 / 芯ずれ量 0.978 —— 独立な 3 つの証拠ではない)。逆に**熱だけでは 正常・アンバランス・ゆるみ が互いの中で 48/48 回まわり**(仕込んだ軸受発熱 2.5/2.7/2.6 W)、形状だけでは芯ずれ以外の 5 モードが 1 つの塊(6.2〜37.5 %)。振動を抜くとアンバランス 100.0→50.0 %、ゆるみ 100.0→31.2 %。★崖は特徴 1 個の上で先に予測: ゆるみの 0.5X は次数分解能 < 0.5 すなわち **T > 2/f_r = 68.6 ms**(実測 50→70 ms の 1 段で d' 2.45→4.32 = +76 %、その前の段は +4 %)、熱の広がりは閉形式の半値直径 66 mm(実測 64 mm から崩れ 96 mm で d' 0.00)。★側帯波は「1/T < FTF = 86.1 ms」と予測して**外れ**、ピークを読む窓 0.6/T が側帯波間隔の半分を切る **1.2/FTF = 103 ms** が正しい条件だった。★★そして崖はどれも 6 クラス識別率には出ない —— 同じセンサの他の特徴が肩代わりする(**冗長性はセンサ間だけでなくセンサ内にもある**)。★アンチエイリアス無しで 3200 Hz へ間引くと衝撃列 k=29 が 167.9 Hz(実測 168.0 Hz)へ折り返し、**間隔が BPFO ちょうどなので軸受らしく見える**。"},
    {"id": "poc_warehouse_flow", "task": "flow", "data": "synthetic",
     "name": "庫内の滞留を種類別に読む(1 つの「滞留時間」に畳むと全部が混雑になる)",
     "summary": "★★ゼロ点の総滞留時間 321.5 秒のうち真の待ちは 198.0 秒(61.6 %)で、残りは**生産的な作業 60.0 秒**と待ちの前後の徐行 63.5 秒 ―― 「滞留を減らせ」は削ってはいけない時間を指す。★★対照群で人待ちを全部止めると -39.0 秒、通路の干渉を全部止めると -38.0 秒(差 2.6 %)で、1 本の数字では「通路を広げる」のか「人を増やす」のかが決まらない。★★欠品は滞留を -5.3 % しか動かさないのに余計な移動を 94.6 m(= 78.8 秒)生む。★崖は幾何で予測できる: 柱に 3 標本要るので長さ T の待ちは Δt >(T + 徐行 2.5 秒)/2 で消える ―― 予測 2.2/2.5/5.0/6.2/10.2 秒に対し実測 2.0/3.0/4.0/6.0/10.0 秒(5 種類とも 1.0 秒以内)。★★3 つの軸は別々の型を殺す(標本間隔 = 短い待ち、遮蔽 = 棚に張りつく型 1.00→0.40、ID の併合 = 2 人の関係を読む型 1.00→0.40)のに、総滞留時間は ID 掃引で 1 秒も動かない。★2-D ヒートマップの最大値は誰も待っていない下段通路(55 フレーム)で、18 秒待っている棚前(48)より大きい。"},
    {"id": "poc_crop_phenotyping", "task": "terrain", "data": "synthetic",
     "name": "作物の葉面積を上から測る(葉が重なると投影が畳む)",
     "summary": "葉を解析曲面で組み、片面葉面積 pi/4·L·W と投影係数 G(theta) を閉形式で持ったまま、天頂からの厳密な z-buffer で群落を測る。★植被率からの Beer-Lambert 反転は消光係数を真値に直しても LAI 4.85 で -52.2 % で、2 段階クランピングから予測した天井 2.26 の近く(実測 2.70)で止まる。★遮蔽は天頂の植被率を 1 ビットも変えない —— 壊れ方は「投影が畳む分 2.68(投影 m^2/m^2)」と「遮蔽が奪う分 3.80(葉 m^2/m^2)」の 2 つで単位から別物、対照群(葉の方位を互生から乱数へ)がクランピング指数 0.478 -> 0.946 と原因を名指しする。★見える葉面積の天井 1/k = 1.374 は閉形式どおり、崖は点密度の対数でしか動かず 4 倍で +1.92。★葉角は面積加重が正しい式なのに、推定法線に掛けると -30.1 % まで崩れ重みなしの平均 -1.2 % に負ける。"},
    {"id": "poc_safety_clearance", "task": "perception_templates", "data": "synthetic",
     "name": "人と機械の安全距離(「近い」を測る点を置き換えると危険が消える)",
     "summary": "多関節の人体(カプセル 10 本)と可動アームを合成し、真の最小分離距離を線分どうしの閉形式(総当たりと最大差 5.6e-05 m)と線分-直方体の凸 1 次元最小化で持ち、危険(真値 < 0.640 m)と停止判定(推定 < 0.690 m)を分けて数えた。★ゼロ点の重心 1 点は危険時に +0.166 m / 最大 +0.304 m 遠く言い(予想は腕の伸び - 被せた半径 = +0.232 m で桁も向きも当たり)、危険の 14.3 % を見落として誤検知は 0.8 % —— 足元 1 点はさらに 28.6 %。★★崖は 3 つあるが誤りの向きが違う: 理想でも誤検知は 3.4 % 出る(停止判定が物理の危険より 0.050 m 大きい設計余裕ぶん)のに対し、遮蔽を入れるとその誤検知が 0.0 % に減って代わりに見落としが 18.1 % 出る —— 見えない点は必ず『もっと遠い』としか言えないので、遮蔽は誤りを危険な側へ移すだけ。★遮蔽は点を増やしても消えない(1 台 800 点 18.1 % / 100 点 29.5 %、遮蔽なしの 100 点は 4.8 %)、効くのは 2 台目だけ(0.0 %)。★★Z_d を繰り返し性から見積もると 0.036 m(3σ)だが、同じ点群を測り直しても遮蔽の形は変わらないので原理的に写らず、遮蔽の偏りの 95 % 点 0.178 m の 5 分の 1 —— 見落としを 0 にする Z_d 0.150 m を入れると停止時間が 18.3 → 24.4 % に増える。★予想を外したのは点密度の式で、(s/2)²/(2r) は最疎で 0.107 m と踏んだが実測 +0.040 m(2.7 倍の過大)。★Chamfer 0.0388 m は隠れた手を薄めるが Hausdorff 0.2481 m(6.4 倍)は分離距離の過大評価と同じ桁に残る。★占有格子 + ESDF は距離を必ず遠く言い、40/20/10 mm で +0.0104 / +0.0056 / +0.0024 m —— 予想の半ボクセルではなく約 1/4 ボクセル(三線形補間が階段を均す)。"},
    {"id": "poc_leak_localization", "task": "ranging", "data": "synthetic",
     "name": "音で漏水を位置決めする(音速を誤ると掘る場所がずれる)",
     "summary": "埋設管 120 m の 2 点で録った漏水音の到達時間差から位置を出す。★音速が真値なら 0 dB で 0.0107 m(CRLB 0.0091 m の 1.2 倍)、崖は予測 -20.1 dB に対し実測 -12.5 dB で 7.6 dB 楽観だった。★量子化誤差は散らばりでなく場所ごとの偏り —— 位置を 41 点振ると RMS 0.0221 m で予測 c/(2fs)/√12 = 0.0220 m と一致するが、1 点に固定すると小数部が固定されて毎回同じだけ外す。★★音速 10 % の誤りは 1.798 m(予測 1.800 m、中点では ±15 % でも 0.0007 m)、管種が途中で変わると τ = 0 になり、どの音速を仮定しても 18.001 m 外す —— パラメータでなくモデルの誤り。★反射では予想が外れ、GCC-PHAT は生の相関に 1 割しか勝たない(誤差 0.121 m のほぼ全部が偏り。左右の継手を入れ替えると符号が反転し、対称にすると 0.000 m)。"},
    {"id": "poc_pv_thermal_survey", "task": "diagnostics", "data": "synthetic",
     "name": "太陽光発電所のドローン熱画像(ΔT を測っているつもりで、風と角度を測っている)",
     "summary": "定常熱収支の閉形式が真値なので、故障の ΔT を予測と 0.07 K 以内で突き合わせられる。★余剰発熱 320 W/m² のホットスポットは 11.20 K が 4.23 K になって届く —— 薄めているのは予想した熱伝導(×0.960)ではなく**カメラ**(×0.511)と、大気と放射率設定(×0.854)。★★崖を決めるのはしきい値でなく**面積の門**: 「ピークが 3.0 K を割る」予測 3.0 m/s は外れ、塊の面積 2πσ²ln(P/θ) が 4 px を割る予測 1.1 m/s が実測 1.0 m/s と一致する。★★電気的故障ゼロの対照群でも全体平均基準なら塊 6 個(健全 1 / 非故障 5)—— 正体は風の当たらないモジュールが 4 K 熱いだけで、モジュール中央値なら 0 個。ただし中央値は**モジュール丸ごとの異常に盲目**(+3.43 K が +0.08 K)、平面除去は広い故障を食う(ストリング 5.55 → 4.10 K)。★★列間影は同じストリングの日向側を +4.68 K 熱くし、本物のストリング故障 +5.55 K と 0.87 K しか違わない。★入射角 65° で ΔT は 0.93 倍、射影補正で位置ずれは 80.1 → 0.5 px に戻るのに ΔT は 0.61 倍(幾何は直せるが放射は直らない)。★NETD は 20 → 3000 mK まで振っても偽ゼロ(予想外れ)だが、非故障の塊が 1 → 44 個に増えて総面積は 1620 → 1892 px —— 個数で報告すると雑音が『発見』に化ける。"},
    {"id": "poc_cold_chain_excursion", "task": "diagnostics", "data": "synthetic",
     "name": "冷蔵輸送の逸脱判定(ロガーの置き場所が合否を決める)",
     "summary": "★★真に不合格な製品セルは 108 / 490(22.0 %)なのに、製品にロガーを 1 個貼ると **82.4 % の置き方が「合格」**と言う ―― 1 個の記録が出す逸脱時間は置き場所で 0〜585 分に散る。★★要因を 1 つずつ止めると壊れ方が分かれる: 荷が均一なら偽合格も偽不合格も 0.0 %、壁からの侵入だけなら偽合格 95.5 %・偽不合格 0.0 %、壁を止めて扉だけ残すと真の不合格が 2.0 % に落ちるのに**偽不合格が 3.5 % 現れ**、しかも製品に貼ったロガーは **100 % が合格**と言う(短いパルスは熱容量のある製品に入らない)。★崖は先に予測できる ―― 時定数の崖は中央通路 4 か所で実測 138/63/35/19 分、「荷室の空気 τ=5 分 + ロガー」の 2 段モデルが 113/58/34/19(短い側で相対 0〜3 %)、教科書の 1 極公式 A(1-e^(-W/τ)) はそこで 21 % ずれる。サンプリング間隔の崖は予測 1-W_eff/Δt と**差 0.0 分ポイント**(位相を全部試して 26.7/45.0/63.3 %)、量子化の崖も実効しきい値 limit+q/2 の予測と**差 0 分**。★★同じ記録から出した 3 指標は「12 °C に許す時間」に直すと 60 分(逸脱時間)/ 276 分(MKT)/ 197 分(劣化)と **4.6 倍**ずれ、720 セル中 **82 セル(11.4 %)で合否が揃わない**。MKT は集計窓で動き、12 時間なら 7.09 °C(合格)でも逸脱を含む 4 時間で切ると 8.04 °C(不合格)。★逸脱は vol_label で (t,y,x) の 11 個の塊として数えられ、最大の塊は t=120 分に生まれて 600 分続き 5.8 m x 2.4 m に広がる(vol_region_props の surface_area / sphericity は軸の単位が混ざるので**使ってはいけない**)。★★予想が外れた: 慣用の 3 点(扉寄り・中央・吹き出し口寄り)は ±1 m 揺らしても偽合格 3.3 % で、ランダム 3 個の 55.4 % より**ずっと当たる** ―― ただし効いているのは扉寄りの 1 点だけ(単独 2.9 % / 中央 100.0 % / 吹き出し口寄り 100.0 %)。"},
    {"id": "poc_weld_bead_scan_angle", "task": "metrology", "data": "synthetic",
     "name": "光切断で溶接ビードを走査する(分解能と遮蔽は同じノブの表裏)",
     "summary": "★★三角測量角 θ は高さ分解能を 1/sinθ で良くする一方、傾き cotθ を超えて登る面を陰に落とす。幾何からの予測どおり遠側母材面は **37.0 度でいっせいに背を向け**、左アンダーカットはそれより早い **20.8〜34.5 度**から欠け始める(★深い溝ほど早い ―― 通してはいけない欠陥から消える)。★★危ないのは 28 度で「測れた率」が 100 % のまま溝の区間の 25 % が欠測し、深さが **27 % 過小**に返ること。さらに角度を上げると深い断面が「測れない」に落ちて、生き残った断面の真値の平均が 0.260 → 0.047 mm と流れる**生存者バイアス**で平均誤差だけが改善して見える。★最適角は量ごとに違い(左溝 20 / 凸み・左脚長・のど厚 24 / 右脚長 36 / 右溝 64 度)、近側の脚長まで 40 度で消える(根が 2 枚の母材面の交線だから)。★「重心を使った」だけでは推定量が決まらない ―― 光条幅への向きが固定窓 σ^-0.61 と追従窓 σ^+0.88 で逆になり、ずれは `clip(I-BG,0,None)` の 1 行(外すと σ^-0.98 で予測どおり)。"},
    {"id": "poc_asbuilt_wall_deviation", "task": "metrology", "data": "synthetic",
     "name": "竣工した部屋の壁を測る(外接直方体は寸法でなく部屋の向きを測っている)",
     "summary": "★★AABB から内法を読むゼロ点は東西 +19.1 mm 過大で、部屋を 1 度回すと +80.1 mm、10 度で +611.1 mm——測っているのは W cosψ + D sinψ という部屋の向き。平面 2 枚の距離は ψ を振っても +2.24 mm から動かない。★AABB は点を 256 倍にすると +14.9 → +19.7 mm と広がり、一致推定量ですらない(雑音の最大値統計 2σ√(2 ln N)、伸び方の予測は 0.6 mm で的中)。★★外れ点への壊れ方は 2 種類——最小二乗は 10 % 混入で真値の 11 倍(66.3 mrad、閉形式 63.8 と 4 % 以内)、RANSAC は 45 % まで持ち 55 % で家具へ乗り換える(倒れは 0.13 mrad と小さいまま面は 449.9 mm ずれる)。★★面のふくらみ 1 個が倒れ -1.258 mrad・直交度 +0.500 mrad・内法 +2.2 mm を同時に汚し、広いふくらみほど吸われて(σ=3.0 m で 90.1 %)雑音の床 4.17 mm に沈む。"},
    {"id": "poc_battery_electrode_breathing", "task": "metrology", "data": "synthetic",
     "name": "電極の呼吸を µm で測る(サブピクセルなら何でもよいわけではない)",
     "summary": "積層 3 単位・境界 13 本・1 px = 1 µm、真値は負極 1.00 % / 正極 0.20 % / セパレータ 0 %(積層 480.0 → 482.136 µm = +0.4450 %)。ゼロ点 Z1(二値化して画素数)は量子化 1 px に埋もれて **12 層中 0 層**しか読めないが、ゼロ点 Z2(固定しきい値 55 % の交差)は**サブピクセルなので雑音なしでは当たる**(+0.004495)。★★殺すのは対照群 ―― 伸びゼロのまま**オフセット +0.10 をかけるだけで Z2 は -1.07e-02、真値の 2.4 倍を逆符号で**返し、ゲイン x1.30 では交差が 12 → 6 本に落ちて測定不能。同条件で勾配ピーク(`fs.ledger.measure_pos`)は 0.0 のまま(|dI/dr| のピークは I → aI + b で動かない)。★★自分の「誤差 1.8e-14 px」を疑って積層を小数画素ずらすと、それは**真値を画素の中心に乗せた検査の産物**で、実際は RMS 0.0088 / 最大 0.0122 px の**ピークロッキング**(負極 1 層のひずみに 3.0 % 効く。`piv_peak_locking` の c0 はこの大きさに気づかない: 推定 1.37 / 真値 1.60)。★雑音は Cramer-Rao 下界から予測でき、実測/下界 = 2.47 / 2.62 / 2.54 / 2.59 と**比が雑音でほぼ動かない**が、層別の予測は当たる(3.28e-03 対 3.50e-03)のに**全体の予測は 1.7 倍甘い**。★★いちばん欲しい層別が σ_n=0.10 で 3.3e-03 と全体 6.5e-04 の **5.0 倍**ばらつく(てこの腕 480 → 58 px の幾何)。★全体のひずみも 2 通りで精度と偏りが逆を向き、回帰は一様でないと -2.65 % 偏る(一様 0.45 % を掛けると偏りは +3.8e-06 に消える、と対照群で確認)。★★崖は 2 段で予測を外した ―― **CNR 5.3 で本数が壊れ始め**、予測した 3σ の崖 CNR 0.96 より **5.5 倍手前**で死ぬ。しかも CNR 1.9 の行は生き残りだけ残るので**ばらつきが逆に良く見える**。"},
    {"id": "poc_battery_electrode_tortuosity", "task": "tomography_3d", "data": "synthetic",
     "name": "電極の屈曲度を CT から測る(Bruggeman は向きに盲目)",
     "summary": "合成マイクロ CT の多孔電極で、同じ 1 個のボリュームから屈曲度が 3 つ出る ―― Bruggeman 1.499 / 測地 1.182 / 輸送方程式(真値)1.843。ゼロ点の経験則 τ = ε^(-0.5) は**必ず小さめに外し**、ε = 0.691 → 0.168 で誤差 -8.2 % → -69.1 % と単調に開く。実測の Bruggeman 指数は ε>=0.40 で 1.78 / ε<0.25 で 2.70 で、**1.5 乗則は高空隙率の近似ですらない**。★★測地屈曲度の 2 乗は Bruggeman に 0.8 / 5.7 / 6.9 % で寄り添うが、**2 つの「よく合う数字」は真値に対して同じ向きに外れている**だけ。★★決定打は対照群 ―― 空隙率を 0.4448 対 0.4510 に揃えて粒子だけ 4:1 に潰す(カレンダリング)と、厚み方向 τ は 1.843 → 6.794(異方比 0.97 → 4.20)。経験則は ε しか見ないので同じ 1.5 を返し、**面内は当たって見え(-8 %)厚み方向は壊滅(-78 %)**。★もっともらしい犯人「閉気孔」は対照群で外れ(全空隙の 0.05 / 1.50 / 1.92 %)、効いているのは粒子半径の 0.40 倍しかない首。ただし**そのスカラーも向きを分けられない**(扁平床は内接半径 1 分布なのに τ_z / τ_x が 4.2 倍)。★予想が外れた ―― 「voxel が首の直径を超えたら崩れる」と予測したが**崖は無く**、voxel を 5.5 倍粗くすると τ_f は 1.771 → 3.041(+72 %)へ単調に増える一方、**ε は -0.4 % しか動かない**。図も検出数も壊れないまま数字だけが片側へずれる。"},
    {"id": "poc_bump_coplanarity", "task": "metrology", "data": "synthetic",
     "name": "バンプの共平面性と基板そりの分離(引きすぎると本物の不良も消える)",
     "summary": "Cu ピラー 256 本の高さ場に そり PV 50 µm・個体差 1σ 4 µm・短小 6 本を仕込み、そりを当てはめて引いた残差が本当に個体差かを測る。ゼロ点(平面だけ = JEDEC の着座平面)は読み取り RMS 誤差 8.84 µm で個体差 1σ の 2.2 倍、★不合格 62 本を 1 つに畳むと見えないが内訳は誤検出 58 本と**見逃し 1 本**で、壊れ方は 2 種類ある。2 次曲面で 1.23 µm・誤検出 0 になる一方、★予想「高次ほど良い」は外れて 3 次は 1.37 µm と悪化する(高次成分が 4 次のロブなので 3 次では 1 µm も取れず、増えた 4 項が個体差と雑音を吸う)。崖は幾何で先に予測でき、取り切れない割合 r1=0.17664 / r2=0.02355 から出した PV 22.6 / 169.9 µm に対し実測 22.6 / 169.4 µm(比 0.996 / 0.998)。★★中央が 8 µm 沈む本物の低次不良を足すと残差から 88.2 % 消えるのに孤立短小の検出数は 5→5 本で変わらず、見逃しだけ 0→2 本に増える ―― **「検出できている」は健全さの証拠にならない**。消えた分は捨てられておらず報告されるそりが 30.06→36.20 µm と膨らむ。★進化 op の auto_threshold は値域を [0,1] とみなすので、µm 単位の高さ場をそのまま渡すと 0.5 µm の位置で切って前景 1141 画素(正解 437)を返す。"},
    {"id": "poc_crack_width_timeseries", "task": "metrology", "data": "synthetic",
     "name": "ひび割れの伸びを 12 期で測る(幅が当たる測り方と、伸びが当たる測り方は別)",
     "summary": "★幅を 25.0 % 過小に言う 2 値化が、成長率は +153.0 % 過大に言う(積分法は幅 +0.00001 mm・成長率 +3.1 %)―― 一定の偏りは差分で消えるが、2 値化の偏りは幅に依存する 1 画素の階段なので消えない。★★幅を 0.30 mm に凍結してぼけ・照明・据え直しだけ動かす対照群でも 2 値化は +0.0117 mm/年 の「成長」を出し、要因を 1 つずつ止めると犯人はぼけ(単独 +0.0122、照明 -0.0001、据え直し -0.0024)。積分法が強いのは畳み込みが輝度欠損の総量を保存するから(1e-16 の桁で検算)。★★据え直しの半画素は経路が水平だと全列の位相が揃って画面ごと 1 px 跳ぶ(σ 0.0546 mm)。崖は「測る区間 259 列で中心線が 1 px 動く傾き」1/259 = 0.0039 の予測どおり、傾き 0.002 で半分を切る。★2 値化が死ぬ境界は w/σ で 1.219(出ない)/ 1.221(出る)と刃物のように鋭く、erf の閉形式 1.349σ にざらつきの最大値ぶん(実測 0.0494)を入れた予測 1.197 と -1.9 %。"},
    {"id": "poc_die_tilt_tsv_overlay", "task": "tomography_3d", "data": "synthetic",
     "name": "ダイの傾きと TSV の位置ずれ(同じ 1 つの CT から。傾きは回転まで偽装する)",
     "summary": "上下 2 枚のダイの 7×7 TSV に 真の位置ずれ (+0.800, −0.450) µm・回転 +0.01500° を仕込み、上ダイを接合面まわりに (1.20°, 0.70°) 傾けた CT 1 個だけで測り返す。ゼロ点(上面の開口の重心差)は 2.419 µm 外し、仕様 ±1.0 µm の 2.4 倍・真の位置ずれ 0.918 µm より大きい。★偽装量は「ダイ厚 × 上面法線の横成分」の閉形式で、ダイ厚 100.032 µm も傾き 1.1979°/0.6968° も同じ CT から測って 比 0.996 / 0.999 で一致する ―― ビアの軸で下面へ引き直すと 0.0023 µm(ゼロ点の 1/1049)。★★予想「傾きは並進と倍率だけを偽装し回転は偽装しない」は外れ: Rx(α)Ry(β) の上 2×2 は sinα sinβ のせん断を持ち、極分解すると偽の回転 予測 +0.00733° / 実測(対照群との差)+0.00696° が出る。真の回転の 46 % で、**軸補正では消えない** ―― 測った法線から α,β を解いて逆投影して初めて対照群と同じ +0.01386° に戻る(倍率も予測 −147.0 / 実測 −144.5 ppm)。崖は合成傾きで解いた 0.491° に対し実測 0.492°(比 1.001)、補正後は 2.0° でも 0.0113 µm。★★いちばん効いたのは幾何でなく標本化: 部分体積を 1 ボクセル幅の直線ランプで刻んでから畳み込むと折り返しが残り、同じ場の傾きを 0.5° で +7.3 %・1.2° で −8.0 % とばらばらに外す。PSF を場のほうに(erf の縁として)入れて標本化すると比 1.0000。しきい値で切った画素の重心も二値化が折り返しを呼び 1.223°/0.750°、生 gray を円板で積むと 1.200°/0.697°。"},
    {"id": "poc_pallet_load_utilization", "task": "geometry", "data": "synthetic",
     "name": "パレットの積載率(1 つの数字が隙間とはみ出しを同じ値にする)",
     "summary": "★★見かけの積載率が同じ 2 つの荷を閉形式で作った(62.65 % と 62.67 %、差 0.02 pt)。中身は逆で、荷 A は 3.11 pt が上から見えない空洞、荷 B ははみ出し 2.10 pt(90 mm)+ 高さ超過 0.58 pt(天端 1911 mm / 制限 1800 mm)——処置も「積み直す」と「降ろす」で逆。★荷を 1 個の外形とみなすと荷 B は AABB 113.90 % / OBB 166.44 % と 100 % を超える(はみ出しを体積として数え込む)。★★高さマップのセル寸法 1 つが逆向きに 2 通り壊す: 幅 w の隙間は max(0, 1 - g/w) で消え(g=40 mm で 20 mm の隙間は完全消失、g=w は位相で全か無か)、同時に 1 mm も出ていない荷に 周長 x g/2 x 天端 の偽はみ出しが立って g=40 mm から真のはみ出し 0.0450 m3 を追い越す。★IoU 0.9493 / 1.0000 はこの違いに構造的に盲目で、代わりに inner_box3 の「あと 1 個入る最大の箱 400 x 1000 x 100 mm」がそのまま使える答えになる。"},
    {"id": "poc_settlement_significance", "task": "metrology", "data": "synthetic",
     "name": "沈下の有意性を検出限界で切る(平均は「全体が沈んだ」、LoD は「沈んだのは半分」)",
     "summary": "Peck の横断ガウス x Attewell の縦断で最大 8 mm の沈下場を仕込み、2 時期の点群(180 / 120 pt/m²、測距雑音 2 mm)から M3C2 と LoD を出す。★ゼロ点の C2C は変化ゼロでも中央値 47.74 mm(真の最大沈下の 6 倍。正体は点間隔 91 mm)を返し符号も無い。★★平均 -2.43 mm に対し有意なのは 275/551 core(49.9 %)でその平均は -4.34 mm、TPR 88.7 % / FPR 3.6 %。★★LoD は粗さと密度の地図で、同じ 2〜4 mm の沈下が舗装(粗さ 1.5 mm)では 100 %、砂利の路肩(15 mm・密度半分)では 30.6 % しか有意にならない ―― 素朴な閉形式との比 0.77〜0.94 は一貫して 1 未満で、局所平面に吸われる分を残差で置き換えると 1.02〜1.03。★★法線を鉛直で代用すると勾配 2.06 % が σ = g·r/2 = 6.18 mm に化け、損をするのは滑らかな面のほう(アスファルト 0.51 → 1.46 mm、粗い路肩は 3.58 → 4.42 mm)。★★合わせ残差 -0.70 mm だけで有意 core が 20 → 249 に跳ね、BH も塊の規則も桁で減らせない(系統誤差は多重比較の問題ではない)―― 安定域の中央値で較正して 20 に戻る。★★有意なものだけ足すと体積は -13.9 %、その欠け量は core ごとの LoD で先に計算できる(LoD を 1 個の数字で代表すると 3.3 倍過小に見積もる)。"},
    {"id": "poc_colormap_readability", "task": "imaging_quality", "data": "synthetic",
     "name": "疑似カラーの選び方と値の写し方(無い境目を数える / 崖を先に当てる)",
     "summary": "段差ゼロと分かっている場を塗り、CIE L* と CIEDE2000 で偽の境目を数える —— jet 3 本 / hsv 4 本 / viridis 0 本。★★立つ位置は閉形式で当たる(jet の明度折返し 予測 0.3750/0.4490/0.6250 対 実測 0.3750/0.4492/0.6250、最大ずれ 0.0002)。本物の段差が偽の境目を追い越す崖は jet 0.296 %FS / viridis 0.050 %FS で、**画像を見ずに LUT だけから予測できる**(実測と一致)。★配色より写し方が効く: 4.3 桁の 1/r² で実効階調 linear 1.4 → rank 76.0、外れ値 1 個で log が -41 %(27.4 → 16.3)、percentile と rank は不変。★★明度が単調でも安全ではない —— cividis は L* 折返し 0 回なのに色差の山が 3 本。★勝てない側も: 質的パレットは色数(tab10=10)を超えると循環し、24 領域で隣接対の最小色差 0.0 —— 連続マップ (3.5) にも乱数 RGB (3.9〜13.0) にも負ける。"},
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
