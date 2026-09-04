# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsoptics — fullseye 光学 op の統一レジストリ(optics を一望・発見可能に)。

ユーザー方針(2026-09-01)「光学系で使うような演算 op が充実するといいな」。
fullseye は産業ビジョン(検査ライン)と Physical AI(ロボット知覚)の両方に
足場があり、その**手前**にあるのがレンズ・回折・偏光の計算 — 「どの焦点距離
か」「被写界深度はどれだけか」「回折で潰れる最小欠陥は何 µm か」「偏光板で
テカりは消えるか」。本レジストリはその台帳(optics.py 18 op + raytrace.py 15 op
+ lensimage.py 5 op + lensopt.py 3 op + illumdesign.py 6 op = 47 op / 8 カテゴリ)。

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

_MOD = {"optics": optics, "raytrace": raytrace, "lensimage": lensimage,
        "matappear": matappear, "glassmirror": glassmirror,
        "metalfinish": metalfinish, "surfacelib": surfacelib,
        "lensopt": lensopt, "illumdesign": illumdesign,
        "optscene": optscene}

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
        ("gaussian_beam", "optics", [], "table"),
    ],
    "imaging": [
        ("psf_to_mtf", "optics", ["image2d"], "pairs"),
        ("mtf_diffraction", "optics", [], "pairs"),
        ("wavefront_stats", "optics", ["table"], "table"),
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
        ("lens_spec", "optscene", [], "table"),
        ("light_spec", "optscene", [], "table"),
        ("light_wavelengths", "optscene", ["table"], "pairs"),
        ("vision_layout", "optscene", ["table", "table", "table"], "table"),
        ("layout_capture", "optscene", ["table"], "table"),
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
