# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsoptics — fullseye 光学 op の統一レジストリ(optics を一望・発見可能に)。

ユーザー方針(2026-09-01)「光学系で使うような演算 op が充実するといいな」。
fullseye は産業ビジョン(検査ライン)と Physical AI(ロボット知覚)の両方に
足場があり、その**手前**にあるのがレンズ・回折・偏光の計算 — 「どの焦点距離
か」「被写界深度はどれだけか」「回折で潰れる最小欠陥は何 µm か」「偏光板で
テカりは消えるか」。本レジストリはその台帳(optics.py 21 op + raytrace.py 15 op
+ lensimage.py 5 op + lensopt.py 3 op + illumdesign.py 6 op = 50 op / 8 カテゴリ、
optics の wave に 2026-09-15 の瞳形状 PSF 3 op を含む)。

shape_from_polarization(sfpolar.py、2026-10-13 追加)— **偏光で形を測る**。偏光の分解
(``polarization_demosaic`` → specularity の ``polarization_dolp_map`` / Stokes)はあったが、
DoLP から天頂角、AoLP から方位角を逆算して法線にする経路が無かった(``polar_cam`` の
順方向デモだけ)。鏡面(Fresnel 反射、Brewster を挟んで 2 解)と拡散(Fresnel 透過、1 解)の
閉形式、方位の π の曖昧さを**集合のまま**返す ``sfp_normals``、凸の事前情報 + Brewster の稜線
または粗い深度で選ぶ ``sfp_disambiguate``、屈折率の推定、鏡像拡張した Frankot–Chellappa の積分。

light_transport(lighttransport.py、2026-10-13 追加)— **凹みの中の光**。縞投影も ToF も
「画素に届く光は 1 経路」と仮定していて(``fringe`` / ``photoncount`` は直接光だけ、``gi_render``
の相互反射は Mitsuba が要り分離も誤差予測も無い)、V 溝・内角・フィレットでは向かいの面からの
相互反射が位相を引っぱる。2-D(押し出し形状)の Lambert ラジオシティを crossed-strings の
形態係数で解いた**輸送行列**、Nayar ら(2006)の高周波パターンによる直接・大域の分離、縞の
位相バイアスの予測(直接と大域のフェーザ和)、マイクロ位相シフトの復号、ToF の多経路
(反射ごとの遅延を入れた複素ラジオシティ)。

coherent(coherent.py、2026-10-13 追加)— **レーザーで撮る**。imaging_sim は強度の PSF を
畳み込むインコヒーレント結像だけで、``optscene.light_spec`` がレーザーに付ける
``coherent=True`` の印を使う経路が無かった。coherent は粗面のランダム位相を瞳(コヒーレント
伝達関数)に通して ``|E|²`` を取る: スペックルの生成と統計(Goodman の指数・ガンマ分布、
Airy の自己相関、画素の積分)、光切断の光条をスペックル込みで描く op、三角測量の高さの
不確かさの床 ``δz = C·λ/(2π sin u sin θ)``(Dorsch, Häusler & Herrmann 1994)と低減の閉形式。

telecentric(telecentric.py、2026-10-15 追加)— **テレセントリックレンズと寸法計測**。``lens_spec`` の
``telecentric=True`` は旗だけで、テレセンの光学系も、その旗を読む経路も無かった。しかも ``raytrace`` の光線は
入射瞳を狙うので、入射瞳が無限遠の物体側テレセンでは ``chief_ray`` が止まる。telecentric は同じ処方(table)に
対して光線の狙いを**絞りそのもの**に置き直し、同じ単レンズの絞りの位置だけを変えた 3 種(通常 / 物体側 /
両側テレセン)の生成、主光線の傾き(テレセン度)、像面を固定して物体を動かしたときの倍率、段差の上下の
寸法の誤差、ぼけの RMS、前玉で決まる視野(ケラレ)、``render3d`` へのピンホールの写しを返す。

drawing(optdraw.py、2026-10-15 追加)— **光学系の図面**。``raytrace`` の処方も ``vision_layout`` も数と dict を
返すだけで、図を 1 枚も出さなかった。optdraw はレンズの子午断面図(面の sag・コバ・絞り・像面・絞りを狙った
実光線・EFL / BFL / 全長 / 像高の寸法線・処方表)、撮像系の設置図(側面図と上面図、視野の錐・WD・DOF の帯・照明 5 種)、
単レンズの製作図(ISO 10110 の 3 分割の表、公差は ``tolerance_analysis`` から)を組み、stdlib だけの SVG と
DXF R12 に書き出し、書いた図から座標と文字を読み戻す(門は読み戻しで採点する)。

optimization(lensopt.py)/ illumination(illumdesign.py)— 2026-09-03 追加。
raytrace は処方を**評価**する側、lensopt は減衰最小二乗で処方を**変える**側
(曲率/間隔/円錐/非球面係数を変数に、多視野・多波長の横収差 + EFL 拘束)。
illumdesign はレンズの手前の**照明設計**(リング/ドーム/バー/同軸/バックライトの
放射照度・一様性、傷の斜面と顔料のコントラスト、仰角スイープ、候補族の順位付け)。
raytrace には実硝材カタログ(``glass_catalog`` / ``sellmeier``、Sellmeier 20 種)、
非球面(``asph=(A4, A6, …)``)、``chromatic_shift``、``chief_ray`` も同日追加。

imaging_sim(lensimage.py、2026-09-03 追加)— **設計したレンズで撮る**。ユーザー
の要望「擬似物理空間に光学系を組み、AI 学習用の欠陥画像を生成したい」に応える
出口: 処方 → 実収差瞳の回折 PSF(``psf_from_opd``)→ 歪曲表と逆写像格子
(``distortion_map``)→ 歪曲・視野依存ぼけ・周辺光量・センサ雑音まで通した
画像(``render_through_lens``)→ defectgen の欠陥をレンズ越しに描き、マスクは
同じ歪曲だけ通して注釈を像に揃えたデータセット(``defect_dataset``)。

design(raytrace.py、2026-09-03 追加)— **近軸の先**。optics は薄肉・ABCD・
スカラ回折で「設計の出発点」を出すが、実レンズがそこからどれだけずれるかは
面を 1 枚ずつ**実光線**で通さないと分からない。raytrace は球面/円錐面の逐次
処方(``lens_system`` が返す table)を全 op の共通入力にし、近軸諸元
(``paraxial_trace`` / ``thick_lens``)、スポット(``spot_diagram`` /
``spot_stats`` / ``ray_fan``)、射出瞳基準球に対する OPD(``opd_map`` →
``match3d.fit_zernike`` → ``optics.wavefront_stats`` を ``wavefront_from_opd``
が一本に連結)、面ごとの Seidel 和(``seidel_coefficients``)、製造公差の
Monte-Carlo と感度(``tolerance_analysis``)を返す。棲み分け: **optics =
近軸/波動(閉形式)、raytrace = 実光線・設計(処方から数値で)**。硝材は
``glass``((n_d, V_d) → 2 項 Cauchy)。``example_system`` は singlet / doublet /
paraboloid / sphere_mirror の 4 処方(テストと例の共通出発点)。

既存資産との棲み分け(**再実装せず import して合成**):
  * 光線と面の相互作用 = match3d(``reflect`` / ``refract`` (Snell) /
    ``snell_angle`` / ``fresnel_reflectance`` / ``normal_from_reflection``)。
    optics は近軸・スカラ。実際に面で曲がる光線が要るならそちら。
  * Zernike **フィット** = ``match3d.fit_zernike``。``wavefront_stats`` は
    その返り dict をそのまま食い、**match3d 自身の基底ビルダーを再利用**する
    ので規約がずれない(フィットは match3d、統計は optics)。
  * PSF ぼけ・逆畳み込み = volrestore(``vol_gaussian_psf`` /
    ``vol_richardson_lucy``)と complexops(``cx_wiener_deconvolve``)。
    ``psf_to_mtf`` は PSF を**特性化**するだけで復元はしない。
  * FFT / complex 画像 = complexops(``cx_fft`` 系・``phase_unwrap``)。
  * 位相シフト干渉法・縞投影 = fringe(``wrapped_phase`` が一般 N-step、
    ``unwrap_phase_2d`` / ``phase_to_height``)。4-step PSI をここに置くのは
    重複なので**置かない**。

使い方:
    import opsoptics
    opsoptics.list_ops("polarization")
    opsoptics.get("thin_lens")(focal_mm=50.0, object_mm=200.0)
"""
import coherent
import edgesfr
import sfpolar
import lighttransport
import sensorchar
import sensorgeneral
import illumdesign
import optscene
import lensimage
import lensopt
import numpy as np

import glassmirror
import matappear
import metalfinish
import surfacelib
import optics
import raytrace
import cavityoptics
import materials
import spectralrad
import chromconf
import fiberoptics
import filmoptics
import moirealign
import telecentric
import optdraw
import linescan
import pixelshift
import octscan

_MOD = {"optics": optics, "raytrace": raytrace, "lensimage": lensimage, "cavityoptics": cavityoptics, "materials": materials, "spectralrad": spectralrad, "chromconf": chromconf, "fiberoptics": fiberoptics, "filmoptics": filmoptics, "moirealign": moirealign,
        "telecentric": telecentric,
        "optdraw": optdraw,
        "linescan": linescan,
        "pixelshift": pixelshift,
        "octscan": octscan,
        "matappear": matappear, "glassmirror": glassmirror,
        "metalfinish": metalfinish, "surfacelib": surfacelib,
        "lensopt": lensopt, "illumdesign": illumdesign, "edgesfr": edgesfr, "sensorchar": sensorchar, "sensorgeneral": sensorgeneral,
        "optscene": optscene, "coherent": coherent, "sfpolar": sfpolar,
        "lighttransport": lighttransport}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
#   既存語彙の再利用: image2d / signal / matrix / measurement(実スカラのみ)/
#   table(dict or list)/ pairs((n,2) 配列)/ cimage(2-D complex)/ vector
#
# 既存語彙をそのまま使った判断(新語を作らなかったもの):
#   * matrix   — ABCD(2x2 実)と Mueller(4x4 実)は**まさに行列**で、
#     mat_svd / mat_cond / stat_covariance にそのまま流せる。専用語を作ると
#     数学ファミリとの接続を切るだけで得が無い。
#   * cimage   — Jones 行列(2x2 complex)。complexops が既に使っている
#     「2-D complex 配列」語彙で、cx_magnitude / cx_phase がそのまま Jones
#     行列の振幅・位相を見せる(型として嘘が無い: 実際に 2-D complex)。
#   * table    — ABCD の素子リスト((kind, *params) の列)は list、返りの
#     計測値束は dict。TYPE_CHECKS の table は list|dict なのでどちらも該当。
#   * pairs    — (n,2) の (x, y) 配列(funct1d / dsp.spectrum と同じ規約)。
#     MTF 曲線・cos^4 曲線はまさにこれ。
#
# 新語彙 2 つと、その理由(**既存では型レベルの嘘になる**もののみ追加。
# 先例 = opsmath の cpoints / cscalar):
#   * jones  — Jones ベクトル: **長さ 2 固定**の complex 1-D (Ex, Ey)。
#     opsmath の ``cpoints`` は「複素平面上の順序つき点列(閉曲線)」で、
#     周回積分・巻き数は**点の順序と閉性**が答えそのもの。Jones ベクトルは
#     曲線ではなく 2 成分の場の振幅なので、cpoints を食える型として宣言すると
#     「64 点の輪郭を渡しても良い」という嘘になる(実際は常に ValueError)。
#     ``vector`` は (3,) 実ベクトル固定なので不可。
#   * stokes — Stokes ベクトル: **長さ 4 固定**の実 1-D (S0,S1,S2,S3) で、
#     さらに ``S0 >= sqrt(S1²+S2²+S3²)``(偏光度 <= 1)という**物理的実現
#     可能性**の制約を持つ。``signal`` は「1-D の標本化された関数」で長さも
#     意味も自由 — 256 点の正弦波を Stokes 枠に渡せると宣言するのは嘘で、
#     連鎖ファザーでも常に CONTRACT にしかならず偏光ファミリを一切通らない。
_CATALOG = {
    "geometric": [
        ("thin_lens", "optics", [], "table"),
        ("abcd_matrix", "optics", ["table"], "matrix"),
        ("abcd_trace", "optics", ["matrix"], "table"),
        ("depth_of_field", "optics", [], "table"),
        ("relative_illumination", "optics", [], "pairs"),
    ],
    "wave": [
        ("airy_pattern", "optics", [], "image2d"),
        ("angular_spectrum_propagate", "optics", ["cimage"], "cimage"),
        ("fraunhofer_pattern", "optics", ["image2d"], "image2d"),
        # 2026-09-26 追加(4f 光学プロセッサ = レンズが微分を計算する)。
        # ★真値が閉形式で外部参照が要らない: 恒等フィルタ → 180 度回転、
        #   (i2πf)^n → n 階微分(ガウシアンの微分は閉じた式)、渦位相板の
        #   **巻き数が整数**。fourier_plane_filter は入力を取らない生成器で、
        #   four_f_filter が場と透過関数を受ける(cimage 2 つ)。
        ("fourier_plane_filter", "optics", [], "cimage"),
        ("four_f_filter", "optics", ["cimage", "cimage"], "cimage"),
        ("gaussian_beam", "optics", [], "table"),
        # 2026-09-15 追加(げんしけん = 動物の目の標本シリーズ、第 1 標本コウイカ):
        # 任意形状の瞳(W 字・スリット・軸外の穴)+ Seidel デフォーカスの回折 PSF、
        # 軸方向の焦点ずれ → 波数の閉じた式、帯ごとの像ぼかし。入力は既存語彙のまま
        # (pupil = image2d の振幅透過率、返りは image2d / measurement)。
        # ★ pupil_blur は「画像 × カーネル」の一般畳み込み(filters_freq.convol_fft)
        #   ではない —— PSF の標本間隔 λN/oversample を検出器ピッチへ面積積分して
        #   から畳む、その単位合わせが本体。だから PSF を作る側に置く。
        ("defocus_from_shift", "optics", [], "measurement"),
        ("pupil_psf", "optics", ["image2d"], "image2d"),
        ("pupil_blur", "optics", ["image2d", "image2d"], "image2d"),
    ],
    "imaging": [
        ("psf_to_mtf", "optics", ["image2d"], "pairs"),
        ("mtf_diffraction", "optics", [], "pairs"),
        ("wavefront_stats", "optics", ["table"], "table"),
        # edgesfr(2026-10-01): 刃のエッジの写真から SFR/MTF、黒点の写真から迷光指数を**測る**側。
        # psf_to_mtf は PSF を持っている人向け、現場が持っているのはエッジと黒点の写真(poc_veiling_glare 8 節の穴)。
        ("edge_spread", "edgesfr", ["image2d"], "table"),
        ("sfr_from_edge", "edgesfr", ["table"], "pairs"),
        ("mtf50", "edgesfr", ["pairs"], "measurement"),
        ("veiling_glare_index", "edgesfr", ["image2d", "image2d", "image2d"], "table"),
    ],
    # sensorchar(2026-10-01): カメラを EMVA 1288 Release 4.0 Linear の手順で測る。データシートの η・K・σ_d・
    # 飽和・SNR・DR・DSNU・PRNU を出す側。合成センサ(sensor_capture)が「作る」側、この族が「測る」側。
    # 2026-10-13: 規格の残りの式(8.1 節の高域フィルタ・8.6 節のスペクトログラム・式 25・69・3/4・式 51 と
    # B-スプライン)と、前提 3 を確かめる道具・線形な前処理の閉形式を足した。新しい型の語は作らない
    # (画像は image2d、露光段の列は signal、カーネルは matrix、結果は kind つきでない素の dict = table)。
    "sensorchar": [
        ("emva_pair_statistics", "sensorchar", ["image2d", "image2d"], "table"),
        ("emva_photon_transfer", "sensorchar", ["signal", "signal"], "table"),
        ("emva_quantum_efficiency", "sensorchar", ["signal", "signal"], "table"),
        ("emva_linearity_error", "sensorchar", ["signal", "signal"], "table"),
        ("emva_snr_curve", "sensorchar", ["signal"], "matrix"),
        ("emva_sensitivity_threshold", "sensorchar", [], "table"),
        ("emva_dynamic_range", "sensorchar", [], "table"),
        ("emva_dark_current", "sensorchar", ["signal", "signal"], "table"),
        ("emva_spatial_nonuniformity", "sensorchar", ["volume", "volume"], "table"),
        ("emva_defect_pixels", "sensorchar", ["image2d"], "table"),
        ("emva_highpass", "sensorchar", ["image2d"], "table"),
        ("emva_spectrogram", "sensorchar", ["image2d"], "table"),
        ("emva_total_snr", "sensorchar", ["signal"], "matrix"),
        ("emva_exposure_for_snr", "sensorchar", ["signal"], "signal"),
        ("emva_photon_exposure", "sensorchar", ["signal"], "signal"),
        ("emva_bspline_regression", "sensorchar", ["signal", "signal"], "table"),
        ("emva_ptc_linearity_check", "sensorchar", ["signal", "signal"], "table"),
        ("emva_noise_whiteness", "sensorchar", ["image2d", "image2d"], "table"),
        ("emva_filter_distortion", "sensorchar", ["matrix"], "table"),
    ],
    # sensorgeneral(2026-10-13): EMVA 1288 Release 4.0 General —— 線形でないカメラ(圧伸・対数・HDR・カメラ内の
    # 前処理)を、特性曲線の B-スプラインの傾きで入力(光子)の単位へ戻して測る。η と K は「測れない」と報告する側。
    "sensorgeneral": [
        ("emva_general_sensitivity", "sensorgeneral", ["signal", "signal", "signal"], "table"),
        ("emva_general_nonuniformity", "sensorgeneral", ["volume", "volume"], "table"),
        ("emva_general_relative_qe", "sensorgeneral", ["signal", "signal"], "table"),
    ],
    # appearance(matappear): 微細構造の見え方を**波長から**作る族。回折格子・薄膜干渉・
    # 異方性微小面。入口 2 op(等色関数・分光→sRGB)は波長格子だけで呼べ、残り 3 op は
    # **normalmap**(H,W,3 の法線場)を食って rgbimage / image2d を返す。
    #   ★ normals(点群の (N,3) 法線)ではなく normalmap。両者は形は似ているが、
    #   (N,3) を渡すと _normal_map が ValueError で弾く。ここを normals と申告すると
    #   「点群の法線を渡してよい」という嘘になり、連鎖ファザーは毎回 CONTRACT で
    #   終わって**この族を一度も実行しない**(= 発見ゼロに化ける)。
    "appearance": [
        # 返りは (..., 3) の XYZ 三つ組。`pairs` は (N,2) なので嘘だった
        # (2026-09-04 の敵対的監査で摘発)。行が 3 要素なので `points` が正しく、
        # スカラ波長の (3,) は adapter で (1,3) に揃える。
        ("cie_xyz_from_wavelength", "matappear", ["signal"], "points"),
        ("spectrum_to_srgb", "matappear", ["signal"], "vector"),
        ("thin_film_reflectance", "matappear", ["signal"], "signal"),
        ("grating_wavelengths", "matappear", [], "vector"),
        ("grating_rgb", "matappear", ["normalmap"], "rgbimage"),
        ("thin_film_rgb", "matappear", ["normalmap"], "rgbimage"),
        ("ward_anisotropic", "matappear", ["normalmap"], "image2d"),
    ],
    # glassmirror(2026-09-04、ユーザー「光学的にガラスや鏡面を扱う op が沢山あると良い」):
    # 界面(誘電体・金属)・体積吸収・平行平板・分散を**閉じた式**で。光線追跡は要らない。
    # 既存の match3d.fresnel_reflectance / refract は**スカラ・単一光線の教材版**で、
    # 後者は「1 本でも TIR ならバッチ全体が None」。こちらは配列と per-ray マスク。
    "interface": [
        ("fresnel_dielectric", "glassmirror", ["signal"], "signal"),
        ("fresnel_conductor", "glassmirror", ["signal"], "signal"),
        ("brewster_angle_deg", "glassmirror", [], "measurement"),
        ("critical_angle_deg", "glassmirror", [], "measurement"),
    ],
    "mirror": [
        ("metal_optical_constants", "glassmirror", ["signal"], "pairs"),
        ("metal_mirror_rgb", "glassmirror", [], "vector"),
    ],
    "glassbody": [
        ("beer_lambert_transmittance", "glassmirror", ["signal"], "signal"),
        ("slab_transmittance", "glassmirror", ["signal"], "signal"),
        ("refract_rays", "glassmirror", ["points", "points"], "points"),
        ("prism_min_deviation_deg", "glassmirror", ["signal"], "signal"),
    ],
    # finish(metalfinish、2026-09-04、ユーザー「いろいろ加工された金属表面を再現したい」):
    # 金属の見え方 = 材質(n+ik)× 仕上げ(微小面の向きと粗さ)。ここは後者を作る。
    # 旋盤の同心目・ローレットの交差目・ビーズブラストの無方向は、接線を**場**で
    # 持たないと成立しない(定ベクトルではヘアラインしか作れない)。
    "finish": [
        ("finish_catalog", "metalfinish", [], "table"),
        ("tangent_field", "metalfinish", [], "normalmap"),
        ("micro_normals", "metalfinish", ["normalmap"], "normalmap"),
        ("blast_normals", "metalfinish", ["normalmap"], "normalmap"),
        ("finish_shade", "metalfinish", ["normalmap"], "rgbimage"),
    ],
    # material / surface(surfacelib、2026-09-04、ユーザー「他にもいろんな素材や表面を
    # 再現できるなら対応してほしい」): 金属とガラス以外の大半は
    # (1) 粗い拡散 (2) 透明な上塗り (3) 微細構造 (4) むら の 4 つで説明できる。
    "material": [
        ("material_catalog", "surfacelib", [], "table"),
        ("oren_nayar", "surfacelib", ["normalmap"], "image2d"),
        ("clearcoat_shade", "surfacelib", ["rgbimage", "normalmap"], "rgbimage"),
        ("sheen_shade", "surfacelib", ["normalmap"], "image2d"),
        ("subsurface_approx", "surfacelib", ["normalmap"], "image2d"),
        ("wetness", "surfacelib", ["rgbimage"], "rgbimage"),
    ],
    "surface": [
        ("metallic_flake_normals", "surfacelib", [], "normalmap"),
        ("weave_normals", "surfacelib", [], "normalmap"),
        ("wood_grain", "surfacelib", [], "image2d"),
        ("corrosion_mask", "surfacelib", [], "image2d"),
        ("rough_transmission", "surfacelib", ["signal"], "pairs"),
    ],
    "polarization": [
        ("jones_element", "optics", [], "cimage"),
        ("jones_apply", "optics", ["cimage", "jones"], "jones"),
        ("stokes_from_jones", "optics", ["jones"], "stokes"),
        ("mueller_element", "optics", [], "matrix"),
        ("mueller_apply", "optics", ["matrix", "stokes"], "stokes"),
        ("stokes_analyze", "optics", ["stokes"], "table"),
        # 2026-09-18: 偏光カメラの 3 本(Polanalyser / py-pol の一次情報から再実装)。
        ("polarization_demosaic", "optics", ["image2d"], "polsweep"),
        ("polarization_demosaic_color", "optics", ["image2d"], "rgbvolume"),
        ("mueller_from_intensities", "optics", ["signal"], "matrix"),
        ("mueller_checks", "optics", ["matrix"], "table"),
    ],
    # design(raytrace): 入口 3 op(処方 / 閉形式厚肉 / 硝材)+ 例 1 op は引数無しで
    # 呼べ、残り 8 op は lens_system の返り(table)を食う。table 以外(乱数の
    # list/dict)は全 op が _check_system で ValueError(fail-closed、テスト済)
    "design": [
        ("lens_system", "raytrace", [], "table"),
        ("thick_lens", "raytrace", [], "table"),
        ("glass", "raytrace", [], "table"),
        ("example_system", "raytrace", [], "table"),
        # 2026-09-03 追加: 実硝材(Sellmeier、20 種、データシートの nd/vd で検証済)/
        # 任意 Sellmeier 定数(どちらも引数無しで呼べる入口 op)
        ("glass_catalog", "raytrace", [], "table"),
        ("sellmeier", "raytrace", [], "table"),
        ("paraxial_trace", "raytrace", ["table"], "table"),
        ("seidel_coefficients", "raytrace", ["table"], "table"),
        ("spot_stats", "raytrace", ["table"], "table"),
        ("tolerance_analysis", "raytrace", ["table"], "table"),
        ("wavefront_from_opd", "raytrace", ["table"], "table"),
        ("spot_diagram", "raytrace", ["table"], "pairs"),
        ("ray_fan", "raytrace", ["table"], "pairs"),
        ("opd_map", "raytrace", ["table"], "image2d"),
        # 2026-09-03 追加: 波長ごとの焦点移動・倍率色収差・多色スポット
        ("chromatic_shift", "raytrace", ["table"], "table"),
    ],
    # optimization(lensopt、2026-09-03 追加): 処方を**変える**側。減衰最小二乗
    # (Levenberg–Marquardt)で曲率/間隔/円錐/非球面係数を動かし、多視野・多波長の
    # 横収差 + EFL 拘束の残差二乗和を最小化。merit_function は同じ残差の評価のみ、
    # bend_singlet は Coddington 形状因子の閉形式(最適化の正解合わせ用)。
    "optimization": [
        ("optimize_lens", "lensopt", ["table"], "table"),
        ("merit_function", "lensopt", ["table"], "table"),
        ("bend_singlet", "lensopt", [], "table"),
    ],
    # illumination(illumdesign、2026-09-03 追加): レンズの手前、**照明の設計**。
    # light_source = リング/ドーム/バー/同軸/バックライトの発光点集合(table)、
    # irradiance_map = 部品面(起伏可)の放射照度(逆二乗×cos^m×cos)、
    # illumination_uniformity = min/max・CV・端落ち、defect_contrast = 傾いた面
    # (傷の斜面)と平面の Michelson コントラスト(Lambert + GGX、方位で走査)と
    # 顔料コントラストのグレア希釈、lighting_sweep = リング仰角 vs コントラスト
    # (pairs)、illumination_design = 候補族をコントラストで順位付け(経験則との
    # 一致/不一致を明示)。乱数 table は全 op が ValueError。
    "illumination": [
        ("light_source", "illumdesign", [], "table"),
        ("irradiance_map", "illumdesign", ["table"], "image2d"),
        ("illumination_uniformity", "illumdesign", ["image2d"], "table"),
        ("defect_contrast", "illumdesign", ["table"], "table"),
        ("lighting_sweep", "illumdesign", [], "pairs"),
        ("illumination_design", "illumdesign", [], "table"),
        # 照明の立体角(開口の半角・向き)と観察の NA で、鏡面の傾きの明暗を設計する(2026-10-15)。
        # 反射は方向の球の等長写像なので、明るさは 2 つの球冠の交わり = 閉形式。
        ("solid_angle_light", "illumdesign", [], "table"),
        ("solid_angle_boundaries", "illumdesign", ["table"], "table"),
        ("solid_angle_brightness", "illumdesign", ["table"], "table"),
        ("solid_angle_sweep", "illumdesign", [], "pairs"),
        ("solid_angle_render", "illumdesign", ["normalmap", "table"], "image2d"),
    ],
    # imaging_sim(lensimage、2026-09-03 追加): 処方(table)から**センサが記録する
    # 画像**まで。psf_from_opd = 実収差瞳の回折 PSF(|FFT(mask·e^{i2πW})|²、画素
    # 面積積分)、distortion_map = 実主光線 vs 近軸 f·tanθ の歪曲表 + 逆写像格子、
    # render_through_lens = 歪曲→視野依存ぼけ(zones² タイル PSF の線形ブレンド)
    # →周辺光量(追跡口径食 × cos⁴)→露光/ショット雑音/読出雑音/量子化、
    # defect_dataset = defectgen の欠陥をレンズ越しに描き、マスクは**同じ歪曲だけ**
    # 通す(ぼかさない)ので注釈が像とずれない。乱数 table は全 op が ValueError
    "imaging_sim": [
        ("psf_from_opd", "lensimage", ["table"], "image2d"),
        ("distortion_map", "lensimage", ["table"], "table"),
        ("render_through_lens", "lensimage", ["image2d", "table"], "image2d"),
        ("defect_dataset", "lensimage", [], "table"),
        # 2026-09-03 追加: 設計レンズの実歪曲で平面ターゲットの多視点対応点を合成 →
        # calib.camera_calibration に渡して K_true と突き合わせる閉ループ
        ("calibration_views", "lensimage", ["table"], "table"),
    ],
    # scene(optscene、2026-09-05 追加): **光学系を物理空間に組んで撮る**。
    # これまでの仮想 MV(visiondesign/defectgen/visionlab)は「レンダラを持てない
    # ので画像でなく限界を返す」線引きだった ―― その線引きを外す層。mm 単位の
    # 3-D 空間に部品(球/直方体/円筒/CSG 差集合=中空)・照明(illumdesign の
    # light_source をそのまま食う)・カメラ(焦点距離/画素ピッチ/作動距離)を置き、
    # 実光線で **画像 + 深度の真値 + 画素完全なマスク**を同時に返す。真値が同じ
    # 計算から出るので検査アルゴリズムを採点できる(バックライトのシルエット面積
    # が閉形式 πr² と 0.09% 一致、再投影の往復 1.4e-14)。材質の色は指定せず
    # glassmirror の Fresnel(n,k)、粗さは metalfinish、分散は raytrace から取る。
    "scene": [
        ("scene_material", "optscene", [], "table"),
        ("scene_plane", "optscene", [], "table"),
        ("scene_sphere", "optscene", [], "table"),
        ("scene_box", "optscene", [], "table"),
        ("scene_cylinder", "optscene", [], "table"),
        ("surface_defect", "optscene", ["table", "image2d"], "table"),
        ("surface_finish", "optscene", ["table"], "table"),
        ("random_defects", "optscene", ["table"], "table"),
        ("scene_difference", "optscene", ["table", "table"], "table"),
        ("optical_camera", "optscene", [], "table"),
        ("camera_rays", "optscene", ["table"], "points"),
        ("reflect_rays", "optscene", ["points", "points"], "points"),
        ("trace_rays", "optscene", ["table", "points", "points"], "table"),
        ("illumination_visibility", "optscene", ["table", "points", "table"], "signal"),
        ("render_optscene", "optscene", ["table", "table", "table"], "rgbimage"),
        ("optscene_depth", "optscene", ["table", "table"], "image2d"),
        ("optscene_mask", "optscene", ["table", "table"], "image2d"),
        ("optscene_defect_mask", "optscene", ["table", "table"], "image2d"),
        ("optscene_instances", "optscene", ["table", "table"], "table"),
        ("defocus_blur", "optscene", ["rgbimage", "image2d", "table"], "rgbimage"),
        ("diffraction_blur", "optscene", ["rgbimage", "table"], "rgbimage"),
        ("airy_radius_um", "optscene", [], "measurement"),
        ("sensor_catalog", "optscene", [], "table"),
        ("sensor_spec", "optscene", [], "table"),
        ("lens_catalog", "optscene", [], "table"),
        ("sensor_diagonal_mm", "optscene", ["table"], "measurement"),
        ("covers_sensor", "optscene", ["table", "table"], "table"),
        ("lens_spec", "optscene", [], "table"),
        ("light_catalog", "optscene", [], "table"),
        ("register_light", "optscene", [], "text"),        # 返り値は登録した鍵の文字列(fuzz TYPEMISS 候補 2026-09-20)
        ("light_spec", "optscene", [], "table"),
        ("light_wavelengths", "optscene", ["table"], "pairs"),
        ("vision_layout", "optscene", ["table", "table", "table"], "table"),
        ("layout_capture", "optscene", ["table"], "table"),
        ("linescan_capture", "optscene", ["table", "table", "table"], "table"),
        ("interface_budget", "optscene", ["table"], "table"),
        ("optical_budget", "optscene", [], "table"),
        ("observe_surface", "optscene", [], "table"),
        ("inspection_dataset", "optscene", ["table", "table", "table"], "table"),
        ("dataset_throughput", "optscene", ["table"], "table"),
        # 見せる絵は作り方が違う(環境光・多重反射・分散)ので検査用と別 op にしてある
        ("env_studio", "optscene", ["points"], "signal"),
        ("env_lightbox", "optscene", ["points"], "signal"),
        ("render_studio", "optscene", ["table", "table"], "rgbimage"),
        ("sensor_capture", "optscene", ["rgbimage"], "rgbimage"),
    ],
    # coherent(coherent、2026-10-13 追加): コヒーレント結像とレーザースペックル。
    # coherent_image = 振幅(image2d)+ 位相(image2d、rad)→ 円形瞳 → 強度。
    # speckle_field / laser_line_coherent は窓と物理量だけで描く生成側(入力なし)。
    # speckle_statistics = 強度の画像 → コントラスト・KS・粒径の表。
    # triangulation_speckle_limit / speckle_reduction = 閉形式(表)。
    # ★新しい型の語は作らない(位相も image2d、統計は table)。
    # ★2-D の橋(tb_*)は架からない: 1 入力の op は speckle_statistics だけで、その in の
    #   image2d は sort ``image``(_NEW_SORTS の外)、out の table は sort に写らない
    #   (2026-10-13 に backends_typed.build の条件で確かめて決めた。_OP_BRIDGE_SKIP 不要)。
    "matprop": [  # 材料の物性ライブラリ(硝材・結晶・半導体・金属・液体・プラスチック 83 種、refractiveindex.info の一次文献、CC0)
        # ★材料は名前(別名可)かレコード dict で受ける。波長曲線はすべて pairs(λ [nm], 値)= 光源・QE・
        #   ライトガイドの曲線と同じ形(像 = 光源 × 光学系 × 対象 × QE の波長積分へ渡す)。全部が引数だけで
        #   描く側(画像を受けない)なので 2-D の橋は架けない(_OP_BRIDGE_SKIP)。
        ("material_table", "materials", [], "table"),
        ("material_record", "materials", [], "table"),
        ("material_optical_constants", "materials", [], "table"),
        ("material_dispersion", "materials", [], "pairs"),
        ("material_extinction", "materials", [], "pairs"),
        ("material_absorption", "materials", [], "pairs"),
        ("material_transmittance", "materials", [], "pairs"),
        ("material_reflectance", "materials", [], "pairs"),
        ("abbe_number", "materials", [], "table"),
        ("glass_map", "materials", [], "table"),
        ("thermo_optic_coefficient", "materials", [], "table"),
        ("plate_focus_shift", "materials", [], "table"),
        ("silicon_free_carrier_absorption", "materials", [], "pairs"),
        ("material_from_sellmeier", "materials", [], "table"),
        ("material_from_curves", "materials", [], "table"),
        ("read_glass_catalog_agf", "materials", [], "table"),
        # 2026-10-15 近赤外の吸収帯(食品の異物・樹脂の選別): 樹脂の表は 1.05 µm までで k が無かった。
        #   帯の重ね合わせ(中心は一次文献、幅と強さは推定 —— NIR_BAND_MODELS の注)、水は表の Segelstein。
        ("material_nir_absorption", "materials", [], "pairs"),
        ("carbon_black_absorption", "materials", [], "pairs"),
        ("nir_model_info", "materials", [], "table"),
    ],
    "spectral": [  # 光源・フィルタ・センサの分光曲線と、その積と積分(spectralrad、2026-10-14)
        # ★曲線は materials と同じ pairs(λ [nm], 値)。像の明るさ = ∫ 光源 × 光学系・対象 × QE dλ を
        #   spectral_product で 1 本ずつ掛けて spectral_integral で積む。QE を掛ける前に energy_to_photons。
        #   画像を受けないので 2-D の橋は架けない(_OP_BRIDGE_SKIP)。
        ("blackbody_spectrum", "spectralrad", [], "pairs"),
        ("cie_illuminant_a", "spectralrad", [], "pairs"),
        ("led_spectrum", "spectralrad", [], "pairs"),
        ("bandpass_spectrum", "spectralrad", [], "pairs"),
        ("silicon_photodiode_qe", "spectralrad", [], "pairs"),
        ("energy_to_photons", "spectralrad", ["pairs"], "pairs"),
        ("spectral_product", "spectralrad", ["pairs", "pairs"], "pairs"),
        ("spectral_integral", "spectralrad", ["pairs"], "measurement"),
        ("spectral_stats", "spectralrad", ["pairs"], "table"),
        # 2026-10-15 近赤外の分光撮像(ハイパースペクトル): InGaAs の QE、散乱層の反射(Kubelka–Munk)、
        #   材料表 → 反射率、反射率 → 帯域ごとの電子数(ハロゲン × ガラス × 帯域 × QE)。画像(キューブ)は
        #   hyperspectral_capture_cube(同じ線形写像 hyperspectral_band_weights を画素ごとに掛ける)。
        ("ingaas_photodiode_qe", "spectralrad", [], "pairs"),
        ("kubelka_munk_reflectance", "spectralrad", ["pairs"], "pairs"),
        ("spectral_reflectance_from_material", "spectralrad", [], "pairs"),
        ("hyperspectral_band_weights", "spectralrad", [], "matrix"),
        ("hyperspectral_capture", "spectralrad", ["pairs"], "table"),
    ],
    "film": [  # 薄膜(filmoptics、2026-10-15): 多層膜の分光反射率(転送行列)→ 干渉色 → 膜厚(FFT・モデルあてはめ・画素ごと)
        # ★膜も基板も材料表(materials)の鍵で指定する。画像(分光の帯域画像)を受ける map も表を返すので 2-D の橋は架けない。
        ("multilayer_reflectance", "filmoptics", [], "pairs"),
        ("film_color", "filmoptics", [], "table"),
        ("film_thickness_fft", "filmoptics", ["pairs"], "table"),
        ("film_thickness_fit", "filmoptics", ["pairs"], "table"),
        ("film_thickness_map", "filmoptics", ["images"], "table"),
    ],
    "confocal": [  # クロマティック共焦点(白色共焦点)変位センサ(chromconf、2026-10-15)
        # ★レンズの処方(raytrace)と硝材の分散(materials)→ 波長ごとの焦点位置の較正表 → 戻りスペクトル → ピーク →
        #   高さ・透明板の厚さ。観察対象(透明板・金属)の反射率も同じ材料表から。画像を受けないので 2-D の橋は架けない。
        ("chromatic_confocal_probe", "chromconf", [], "table"),
        ("confocal_axial_response", "chromconf", [], "pairs"),
        ("chromatic_confocal_spectrum", "chromconf", ["table"], "pairs"),
        ("chromatic_confocal_peaks", "chromconf", ["pairs"], "table"),
        ("chromatic_confocal_readout", "chromconf", ["table", "table"], "table"),
        ("chromatic_confocal_limits", "chromconf", ["table"], "table"),
    ],
    "fiber": [  # ステップ型ファイバとライトガイド(fiberoptics、2026-10-14): 材料表のガラスの分散 → 導波(LP モード・MFD)→ 照明の効率
        # ★LP モードは特性方程式の数値解(遮断 = Bessel の零点)。画像を受けないので 2-D の橋は架けない。
        ("material_group_index", "fiberoptics", [], "pairs"),
        ("material_gvd", "fiberoptics", [], "pairs"),
        ("fiber_numerical_aperture", "fiberoptics", [], "table"),
        ("fiber_v_number", "fiberoptics", [], "table"),
        ("fiber_lp_modes", "fiberoptics", [], "table"),
        ("fiber_mode_field_diameter", "fiberoptics", [], "table"),
        ("fiber_bundle_coupling", "fiberoptics", [], "table"),
    ],
    "moire_align": [  # モアレによる位置合わせ(moirealign、2026-10-15): ピッチの僅かに違う 2 枚の格子 → 縞の位相 → nm のずれ
        # ★縞はずれを M = p_m/|Δp| 倍(ウェハが動く)/ p_w/|Δp| 倍(マスクが動く)に拡大する。差動の 2 対で共通の誤差を消す。
        ("moire_magnification", "moirealign", [], "table"),
        ("moire_talbot_gap", "moirealign", [], "table"),
        ("moire_overlay_image", "moirealign", [], "image2d"),
        ("moire_phase", "moirealign", ["image2d"], "table"),
        ("moire_phase_to_shift", "moirealign", [], "table"),
        ("moire_differential_shift", "moirealign", [], "table"),
        ("moire_mark_read", "moirealign", ["image2d", "image2d"], "table"),
        ("moire_phase_crlb", "moirealign", [], "table"),
    ],
    "drawing": [  # 光学系の図面(optdraw、2026-10-15): 図の dict(kind "optdraw")を組み、SVG / DXF の文字列に書き、
        # 読み戻す。★新しい型の語は作らない: 図は印つきの dict(table)で、印の無い table は書き出しの op が
        #   ValueError で拒む。SVG / DXF は既存の text(文字列)、画像は rgbimage。
        ("lens_section_drawing", "optdraw", ["table"], "table"),
        ("vision_setup_drawing", "optdraw", ["table"], "table"),
        ("lens_element_drawing", "optdraw", ["table"], "table"),
        ("drawing_svg", "optdraw", ["table"], "text"),
        ("drawing_dxf", "optdraw", ["table"], "text"),
        ("drawing_raster", "optdraw", ["table"], "rgbimage"),
        ("svg_entities", "optdraw", ["text"], "table"),
        ("dxf_entities", "optdraw", ["text"], "table"),
    ],
    "telecentric": [  # テレセントリックレンズと寸法計測(telecentric、2026-10-15): 絞りの位置で主光線の傾きを決め、
        # 高さで変わる倍率・ケラレ・ぼけを実光線で。★光線は入射瞳でなく絞りを狙う(入射瞳が無限遠でも動く)。
        ("telecentric_lens", "telecentric", [], "table"),
        ("chief_ray_angle", "telecentric", ["table"], "table"),
        ("magnification_vs_depth", "telecentric", ["table"], "pairs"),
        ("telecentricity_error", "telecentric", ["table"], "table"),
        ("defocus_spot_vs_depth", "telecentric", ["table"], "pairs"),
        ("vignetting_vs_field", "telecentric", ["table"], "pairs"),
        ("lens_equivalent_pinhole", "telecentric", ["table"], "table"),
    ],
    "linescan": [  # TDI ラインスキャンカメラとラインスキャン用レンズ(linescan、2026-10-15): 段数と SNR(EMVA 1288 の式 21 を段数倍)、
        # 同期ずれ・ヨーの閉形式 MTF、反射率の地図を搬送して撮る撮像、像高ごとの照度(cos⁴ × 瞳 × 歪曲)と MTF(光線追跡)。
        ("tdi_snr", "linescan", [], "table"),
        ("tdi_sync_mtf", "linescan", [], "table"),
        ("linescan_acquire", "linescan", ["image2d"], "table"),
        ("lens_field_profile", "linescan", ["table"], "table"),
        ("linescan_lens_columns", "linescan", ["table"], "table"),
        ("linescan_lens_example", "linescan", [], "table"),
    ],
    "pixelshift": [  # ピクセルシフト撮像(pixelshift、2026-10-15): センサを 1 画素 / 半画素動かして撮り、格子へ合わせる
        # ★1 画素 4 枚 = 各画素で R・G・B(偽色が消える、解像はそのまま)/ 半画素 = 折り返しが消える(開口の MTF は上がらない)。
        ("pixel_shift_pattern", "pixelshift", [], "matrix"),
        ("pixel_shift_capture", "pixelshift", ["rgbimage", "matrix"], "video"),      # 枚 × 行 × 列
        ("pixel_shift_merge", "pixelshift", ["video", "matrix"], "rgbimage"),
        ("pixel_shift_motion_mask", "pixelshift", ["video", "matrix"], "image2d"),
        ("false_color_metric", "pixelshift", ["rgbimage"], "table"),
        ("pixel_shift_resolution_budget", "pixelshift", [], "table"),
    ],
    # oct(octscan、2026-10-15): 光干渉断層。層の並び → 干渉スペクトル → k 線形化 → 分散補償 → A スキャン → 層厚。
    # ★新しい型の語は作らない。干渉スペクトル・A スキャン・B スキャンの束は kind の印つきの dict(table)で渡し、
    #   印の違う table は消費する op がすべて ValueError で拒む(oct_interferogram / oct_bscan_spectra / oct_ascan /
    #   oct_bscan の 4 種)—— 別の族の table を黙って読む経路が無い。B スキャンの画像だけは image2d(dB)で出し、
    #   界面を辿る op は装置の出力の図(実画像)も同じ image2d で受ける。
    "oct": [
        ("oct_design", "octscan", [], "table"),
        ("oct_dispersion_broadening", "octscan", [], "table"),
        ("oct_interferogram", "octscan", [], "table"),
        ("oct_bscan_simulate", "octscan", [], "table"),
        ("oct_from_spectra", "octscan", ["matrix", "signal"], "table"),
        ("oct_k_linearize", "octscan", ["table"], "table"),
        ("oct_dispersion_estimate", "octscan", ["table"], "table"),
        ("oct_dispersion_compensate", "octscan", ["table"], "table"),
        ("oct_ascan", "octscan", ["table"], "table"),
        ("oct_bscan", "octscan", ["table"], "image2d"),
        ("oct_layer_thickness", "octscan", ["table"], "table"),
        ("oct_bscan_boundaries", "octscan", ["image2d"], "table"),
        ("oct_bscan_flatten", "octscan", ["table", "signal"], "table"),
    ],
    "cavity": [  # 光共振器と Michelson(重力波望遠鏡の設計の式 = エタロン・レーザー共振器・干渉計測の式)
        ("fabry_perot_response", "cavityoptics", [], "table"),
        ("cavity_strain_transfer", "cavityoptics", [], "pairs"),
        ("michelson_dc_readout", "cavityoptics", [], "table"),
        ("pdh_error_signal", "cavityoptics", [], "pairs"),
        ("quantum_noise_budget", "cavityoptics", [], "table"),
    ],
    "coherent": [
        ("coherent_image", "coherent", ["image2d", "image2d"], "image2d"),
        ("speckle_field", "coherent", [], "image2d"),
        ("speckle_statistics", "coherent", ["image2d"], "table"),
        ("laser_line_coherent", "coherent", [], "image2d"),
        ("triangulation_speckle_limit", "coherent", [], "table"),
        ("speckle_reduction", "coherent", [], "table"),
    ],
    # shape_from_polarization(sfpolar、2026-10-13 追加): 偏光からの形状復元。
    # 入口 sfp_render(normalmap -> polsweep)と sfp_normals(polsweep -> table)、
    # 出口 sfp_disambiguate(table -> normalmap)と sfp_height(normalmap -> image2d)。
    # ★新しい型の語は作らない。曖昧な法線の**集合**(候補 2 本 / 4 本)を normalmap と
    #   区別するために新 sort を作るかを考えたが、集合は ``kind == "sfp_candidates"`` の
    #   dict(= table)で返す: (K,H,W,3) を normalmap と申告すると法線を食う op(積分・
    #   陰影)に 4 本重ねの配列が渡るが、table なら normalmap の枠には入らず、逆に
    #   sfp_disambiguate は印の無い table を ValueError で拒む —— 混ぜても黙って嘘を
    #   返す経路が無いので、語彙を増やす理由が無い(2026-10-13 に確かめて決めた)。
    # ★2-D の橋(tb_*)は架からない: 1 入力の op の in は image2d(sort image、_NEW_SORTS の外)
    #   か normalmap / polsweep / table(TYPE_TO_SORT に無い)。_OP_BRIDGE_SKIP 不要。
    "shape_from_polarization": [
        ("sfp_dolp_model", "sfpolar", ["image2d"], "image2d"),
        ("dolp_to_zenith", "sfpolar", ["image2d"], "table"),
        ("aolp_to_azimuth", "sfpolar", ["image2d"], "table"),
        ("sfp_render", "sfpolar", ["normalmap"], "polsweep"),
        ("sfp_normals", "sfpolar", ["polsweep"], "table"),
        ("sfp_disambiguate", "sfpolar", ["table"], "normalmap"),
        ("sfp_estimate_index", "sfpolar", ["image2d", "image2d"], "table"),
        ("sfp_height", "sfpolar", ["normalmap"], "image2d"),
    ],
    # light_transport(lighttransport、2026-10-13 追加): 相互反射(大域光輸送)と、それが縞投影・
    # ToF に入れる位相の誤差。入口 groove_profile(断面)→ transport_matrix_radiosity(輸送行列)、
    # 描画 render_transport(table + images → images)、分離 separate_direct_global(images → table)。
    # ★新しい型の語は作らない。断面と輸送行列は kind の印つきの dict(table)で渡し、印の無い
    #   table は消費する 5 op がすべて ValueError で拒む —— 別の族の table を幾何として黙って
    #   読む経路が無い。パターンと画像は既存の images(2-D 画像の list、fringe の位相シフトと同じ)。
    # ★縞と ToF は 1 つの族(このカテゴリ)にまとめ、sort は分けない。物理は同じ「経路ごとの
    #   フェーザの和の偏角」で、op の入出力はどちらも名前つきの値の dict(table)—— 縞は
    #   bias [rad] と height_error、ToF は depth / bias [m] と鍵の名前も単位も違い、位置で
    #   並んだ配列を取り違えて渡す経路が無い(混ぜても黙って嘘を返さない)ので語彙を増やす理由が無い。
    # ★2-D の橋(tb_*)は架からない: 1 入力の op の in は table / images(TYPE_TO_SORT に無い)。
    "light_transport": [
        ("groove_profile", "lighttransport", [], "table"),
        ("form_factors_2d", "lighttransport", ["table"], "matrix"),
        ("transport_matrix_radiosity", "lighttransport", ["table"], "table"),
        ("high_frequency_patterns", "lighttransport", [], "images"),
        ("render_transport", "lighttransport", ["table", "images"], "images"),
        ("separate_direct_global", "lighttransport", ["images"], "table"),
        ("fringe_multipath_phase_error", "lighttransport", [], "table"),
        ("predict_fringe_phase_error", "lighttransport", ["table"], "table"),
        ("micro_phase_decode", "lighttransport", ["images"], "table"),
        ("tof_multipath_phase", "lighttransport", [], "table"),
        ("tof_transport_depth", "lighttransport", ["table"], "table"),
    ],
}


def _build():
    reg = {}
    for cat, entries in _CATALOG.items():
        for name, mod, ins, out in entries:
            fn = getattr(_MOD[mod], name, None)
            doc = ""
            if fn is not None and fn.__doc__:
                doc = fn.__doc__.strip().splitlines()[0]
            reg[name] = {"category": cat, "module": mod, "in": ins, "out": out,
                         "func": fn, "doc": doc}
    return reg


OPSOPTICS = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSOPTICS.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し(ops3d / ops1d / opsmath と同じ一級機構)。
#:
#: **現在は空 — 意図的に**。opsmath では ``mat_svd`` が数学慣習の
#: ``U, s, Vt = ...`` タプルを返すため adapter が要ったが、optics 18 op も
#: raytrace 12 op もすべて宣言型そのもの(dict / (n,2) 配列 / ndarray)を素で
#: 返す設計にしてある。
#: 空にしておくと :func:`call` は :func:`get` と同じ値を返し、連鎖ファザーの
#: TYPEMISS 検査が**素の返りをそのまま**宣言と突き合わせる = 検証が最も厳しい。
#: タプル返しの op を将来足すならここに登録すること(空欄を埋めるために既存の
#: 返り型をタプルへ変える、は本末転倒なのでしない)。
RESULT_ADAPTERS = {
    # (n, k) の 2 本 → (K, 2) の pairs。どちらも捨てない。
    # スカラ波長では (3,) が返る。宣言 points((N,3))へ揃える。
    "cie_xyz_from_wavelength": lambda r: np.atleast_2d(r),
    "metal_optical_constants": lambda r: (np.stack(r, axis=1)
                                          if isinstance(r, tuple) else r),
    # (方向, TIR マスク) → 方向。マスクが要る呼び手は素の関数を直接呼ぶ。
    "refract_rays": lambda r: r[0] if isinstance(r, tuple) else r,
    # (色の変調, 繊維方向) → 変調。接線は ward_anisotropic へ渡す用で素の関数から取る。
    "wood_grain": lambda r: r[0] if isinstance(r, tuple) else r,
    # (原点, 方向) → 方向。原点は全画素で視点 1 点(camera["eye"])なので情報が無い。
    "camera_rays": lambda r: r[1] if isinstance(r, tuple) else r,
    # bool マスク → 0/1 の画像(宣言 image2d に揃える。面積を数える用途をそのまま保つ)
    "optscene_mask": lambda r: np.asarray(r, dtype=float),
    "optscene_defect_mask": lambda r: np.asarray(r, dtype=float),
    # 深度の真値は当たらない画素が NaN。宣言 image2d のままで NaN を潰さない
    # (0 で埋めると「距離 0 の面」と区別できなくなる)。
    # (直進, 拡散) → (K, 2) の pairs。どちらも捨てない(合計が板の透過率になる)。
    "rough_transmission": lambda r: (np.stack(np.broadcast_arrays(*r), axis=-1).reshape(-1, 2)
                                     if isinstance(r, tuple) else r),
    # B スキャンの表 → 断面像(dB)。深さ軸・横軸が要る呼び手は素の関数から表を取る。
    "oct_bscan": lambda r: np.asarray(r["image_db"], float) if isinstance(r, dict) else r,
}


def get(name):
    """op 名 → 実体(callable、素の返り型)。宣言型が欲しければ :func:`call`。"""
    return OPSOPTICS[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSOPTICS[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSOPTICS[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSOPTICS.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsoptics: {len(OPSOPTICS)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
