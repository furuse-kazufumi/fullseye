# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""``tools/impl_differential.py`` の**手で書く表**(2026-11-03)。

ここに書くのは、実測(``docs/impl_differential.json``)では決まらない 4 つ:

* :data:`REASONS` —— 一致しない組の「違ってよい理由」。**中身(実装のコード)を読んで**特定した原因。
  ``tests/test_impl_differential.py`` が、理由の無い食い違いを赤にする。
* :data:`ALIGNED` —— 「差はつまみの写し方だけ」という仮説を、つまみを揃えて確かめる点。門でもある。
* :data:`SHARED_BACKEND` / :data:`TRIVIAL_MATCH` —— 差がきっかり 0 の組の内訳(同じ下位関数を呼んでいる
  だけか、独立だが自明か)。独立な実装どうしの一致と区別する(「異常に良い一致」は内訳を確かめる)。
* :data:`MERGE_VERDICT` —— 命名整理 第 2 段(``C:/dev/docs/naming_phase2/README.md``)で
  「1 つの名前 + ``impl`` 引数」にまとめてよいか。

原因の種類(:data:`KINDS`)は表の列にそのまま出る。
"""
from __future__ import annotations

#: 原因の種類。
KINDS = {
    "fixed": "不具合(この回で直した)",
    "knob": "つまみの写し方",
    "window": "窓・カーネルの形",
    "border": "端の扱い",
    "quant": "量子化(8 bit)",
    "definition": "定義の違い",
    "other_process": "名前だけ同じ別の処理",
    "sort": "入出力の型が違う",
}

#: 組 (a, b)(名前順)→ (原因の種類, 一言)。**一致した組には書かない**(門が「理由が要らない組に
#: 理由がある」も拾う —— 古い理由が残ると、次に食い違ったときに理由があるように見えてしまう)。
REASONS = {
    # ---- 型が違う(名前が似ているだけ)--------------------------------------------------------
    ("area_center", "xg_area_center"): ("sort",
        "region → match(面積の画素数・重心の行・列)と contour → feature(全輪郭の多角形の面積の和、靴ひも公式)。"
        "HALCON でも area_center と area_center_xld は別 op。xg_ の対になる XLD 版 area_center_xld も"
        "「最大の輪郭 1 本」と「全輪郭の和」で定義が違う"),
    ("eccentricity", "xg_eccentricity"): ("sort",
        "region → match(HALCON の Anisometry / Bulkiness / StructureFactor、面積のモーメントから)と"
        "contour → feature(輪郭点の共分散の固有値から sqrt(1 − λmin/λmax))。量も入力の型も違う"),
    ("elliptic_axis", "xg_elliptic_axis"): ("sort",
        "region → match(Ra, Rb, Phi)と contour → feature(輪郭点の共分散の固有値の比 sqrt(λmax/λmin))"),
    ("height_width_ratio", "xg_height_width_ratio"): ("sort",
        "region → feature(画素の外接矩形)と contour → feature(輪郭点の座標の範囲、画素数より 1 小さい)。"
        "入力の型が違うので同じ入力で比べられない"),
    ("curvature_flow", "xsitk_curvature_flow"): ("sort",
        "台帳の curvature_flow はレベルセット φ(mask)を平均曲率流で動かして経過の表を返す。"
        "xsitk_curvature_flow は SimpleITK の CurvatureFlow で画像を平滑化する(image → image)"),
    ("hx_full_domain", "it_full_domain"): ("sort",
        "hx_full_domain は全 1 の region(HALCON の定義域を全面に)、it_full_domain は画像をそのまま返す"
        "(image → image、numpy の配列は元から全面が定義域)。どちらも自明で、返す型だけが違う"),
    ("m1_measure_pairs", "measure_pairs"): ("sort",
        "台帳の measure_pairs は測定ハンドル(線の位置・幅)を受けてエッジの組の表を返す。"
        "m1_measure_pairs は中央の 1 本の線で明るい物体(立ち上がり→立ち下がりの組)の数を数える feature(b が相対振幅のしきい値)"),
    ("m1_measure_pos", "measure_pos"): ("sort",
        "台帳の measure_pos は測定ハンドルを受けてエッジ位置の表を返す。m1_measure_pos は中央の線上の"
        "エッジ点を contour で返す"),
    ("sart_reconstruct", "tm_sart_reconstruct"): ("sort",
        "台帳の sart_reconstruct は sinogram と角度を受ける(反復 10 回の既定)。tm_sart_reconstruct は"
        "画像の行を角度とみなし、反復 1〜5 回・緩和 0.05〜0.4 を a, b に写した入口(skimage の iradon_sart)"),
    ("shape_index", "sk_shape_index"): ("sort",
        "どちらも Koenderink の shape index だが、台帳の shape_index は点群(近傍 k 点の曲率)、"
        "sk_shape_index は画像の輝度面(Hessian の固有値)"),

    # ---- 名前だけ同じ別の処理 ----------------------------------------------------------------
    ("hx_clip_contours", "xg_clip_contours"): ("other_process",
        "hx_ は画像の内側の矩形(上下 a×0.4H、左右 b×0.4W の余白)の外の点を消す。"
        "xg_ は最長の輪郭の a 倍より短い輪郭を丸ごと捨てる(長さで選別)"),
    ("hx_crop_contours", "xg_crop_contours"): ("other_process",
        "どちらも中央の矩形の内側の点を残すが、窓が違う: hx_ は高さ (0.3+0.6a)H・幅 (0.3+0.6b)W、"
        "xg_ は高さ aH・幅 aW(b は未使用)"),
    ("hx_regress_contours", "xg_regress_contours"): ("other_process",
        "hx_ は輪郭ごとの直線当てはめの残差 RMS の平均を max(H, W) で割る(無次元)。"
        "xg_ は全輪郭の点をまとめた共分散の最小固有値の平方根(画素)。正規化も集め方も違う"),
    ("xsk2_wiener", "xsp_wiener"): ("other_process",
        "xsk2_wiener は skimage の Wiener **逆畳み込み**(5×5 のガウシアン PSF、σ = 0.5+1.5a を仮定)、"
        "xsp_wiener は scipy.signal.wiener の**適応雑音除去**(局所分散、窓 3+2int(3a))。名前の Wiener 以外は別物"),
    ("dl_guided_filter", "guided_filter"): ("other_process",
        "dl_guided_filter は本物の self-guided filter(局所線形モデル、r = 1+int(4a)、eps = 0.001+0.05b)。"
        "guided_filter は docstring が自認するとおり**中身が bilateral_filter と同一**(cv2.bilateralFilter)"
        "の代役で、guided filter ではない"),
    ("sk_hessian", "xkor_hessian"): ("other_process",
        "skimage の filters.hessian は Frangi 系の**管状度**(σ = 1, 2, 3 の多重尺度、白い線で 0)。"
        "xkor_hessian は Sobel 5×5 の 2 階微分による **Hessian の行列式** |Ixx Iyy − Ixy²|"),
    ("iv_richardson_lucy", "xsk_richardson_lucy"): ("definition",
        "同じ Richardson–Lucy だが仮定する PSF が違う: iv_ は σ = 1.2(RL_SIGMA)のガウシアン、xsk_ は 3×3 の箱。"
        "反復回数の写し方も違う(iv_ 1+round(14a)、xsk_ 2+int(15a))"),
    ("xcv_inpaint", "xsk_inpaint"): ("definition",
        "欠損の自動マスク(明るすぎ・暗すぎの画素)は同じ発想だが、埋め方が別のアルゴリズム: "
        "xcv_ は OpenCV の Telea(高速マーチング)、xsk_ は skimage の biharmonic。"
        "しきい値も xcv_ は 8 bit(>235 / <20)、xsk_ は float(>0.92 / <0.08)"),
    ("xcv_orb_count", "xsk_orb_count"): ("definition",
        "別実装の ORB で、検出の既定(FAST のしきい値・ピラミッド・端の 31 画素の除外)が違う。"
        "OpenCV 版は edgeThreshold = patchSize = 31 なので 48 px の画像では 0 個になる。つまみは上限数だけ"),
    ("sg_felzenszwalb", "sk_felzenszwalb"): ("knob",
        "同じ skimage.segmentation.felzenszwalb を別の引数で呼ぶ: sg_ は scale = 40+500a・sigma 0.5・"
        "min_size = 15+85b・境界 outer、sk_ は scale = 20+200a・sigma 0.8・min_size 20・境界 thick。"
        "sigma が固定で違うので、つまみを揃えても一致しない"),

    # ---- canny(4 実装、定義もつまみも違う)------------------------------------------------------
    ("canny", "cv_canny"): ("definition",
        "core の canny は**非極大抑制もヒステリシスも無い**簡易版(σ = 0.5+1.5a でぼかした Sobel 強度を正規化して "
        "0.1+0.5b で二値化 → 太いエッジ)。cv_canny は 8 bit の本物の Canny で、a, b が勾配の下・上しきい値(50〜150 / 100〜250)"),
    ("canny", "sk_canny"): ("definition",
        "core は非極大抑制の無い簡易版。sk_canny は本物の Canny で、a が σ = 0.5+2a、しきい値は skimage の既定"),
    ("canny", "xkor_canny"): ("definition",
        "core は非極大抑制の無い簡易版。xkor_canny は本物の Canny(5×5、σ = 1 固定)で、a, b が 0〜1 の勾配の下・上しきい値"),
    ("cv_canny", "sk_canny"): ("knob",
        "どちらも本物の Canny だが、a の意味が違う(cv_ はしきい値、sk_ は平滑化の σ)。cv_ は平滑化なしの Sobel 3×3・"
        "8 bit・L1 勾配、sk_ は L2 勾配・しきい値は既定"),
    ("cv_canny", "xkor_canny"): ("definition",
        "a, b はどちらもしきい値だが尺度が違う(cv_ は 0〜255 の勾配で 50〜250、xkor_ は 0〜1 で 0.1〜0.7)。"
        "xkor_ は 5×5・σ = 1 の平滑化つき、cv_ は平滑化なし"),
    ("sk_canny", "xkor_canny"): ("knob",
        "どちらも本物の Canny。sk_ は a が σ、しきい値は既定。xkor_ は σ = 1 固定、a, b がしきい値"),

    # ---- clahe -------------------------------------------------------------------------------
    ("clahe", "cv_clahe"): ("knob",
        "core の clahe は a がタイル数 2+int(3a) 枚四方、b が clip limit(ビン平均の 256^b 倍)。"
        "cv_clahe はタイル 8×8 固定・a が clipLimit = 1+4a・入力を 8 bit に落とす"),
    ("clahe", "xkor_clahe"): ("knob",
        "core はタイル数と clip limit を a, b で振る。xkor_clahe はタイル 8×8 固定、a が clip limit = 1+4a"),
    ("cv_clahe", "xkor_clahe"): ("quant",
        "定義もつまみも同じ(8×8、clip 1+4a)。差は cv_clahe が入力を 8 bit に量子化すること(タイルの"
        "ヒストグラムと LUT の丸め)。48 px の画像は 1 タイル 6×6 画素で量子化が効き、最大 0.087"),

    # ---- corner_harris -------------------------------------------------------------------------
    ("cv_corner_harris", "sk_corner_harris"): ("definition",
        "cv_ は blockSize 2 の箱の窓・Sobel 3・k = 0.04 で固定(a, b 未使用)。sk_ はガウシアンの窓 σ = 0.5+2a・"
        "k = 0.05。窓の形・k・微分の尺度が違う"),

    # ---- dog(つまみを揃えると定数倍だけ)----------------------------------------------------------
    ("dog", "sk_dog"): ("knob",
        "core は σ1 = 0.5+2a・σ2 = 1+4b、sk_dog は σ1 = 1 固定・σ2 = 1+3a。σ を揃えると(ALIGNED)"
        "内部は**差 0**(skimage の DoG も中で scipy の gaussian_filter を呼ぶ = 独立でない)。"
        "残る差は端の扱い(core は reflect、skimage は nearest)が画像全体の最大値で割る正規化を通して効く定数倍だけ"),
    ("dog", "xkor_dog"): ("knob",
        "xkor_dog は σ1 = 1.0・σ2 = 1.6 固定(a, b 未使用)。core を a = 0.25・b = 0.15 にすると(ALIGNED)"
        "内部は定数倍を除いて 4e-6 で一致(独立: scipy と kornia)。定数倍は端の扱いが正規化に効く分"),
    ("sk_dog", "xkor_dog"): ("knob",
        "sk_dog を a = 0.2(σ2 = 1.6)にすると xkor_dog と定数倍を除いて 4e-6 で一致(ALIGNED)。"
        "定数倍は端の扱い(nearest と reflect)が正規化に効く分"),

    # ---- gabor ---------------------------------------------------------------------------------
    ("gabor", "hx_gabor"): ("definition",
        "どちらも a が向き θ = πa、L1 で割る固定尺度。包絡と周波数が違う: core は σ = 2・窓 15×15・"
        "周波数 0.1+0.3b、hx_ は σ = 2.2・窓 9×9・0.08+0.35b"),
    ("gabor", "sk_gabor"): ("knob",
        "つまみの役が入れ替わっている: core は a が向き・b が周波数、sk_gabor は a が周波数 0.1+0.3a・"
        "向きは 0 固定。sk_ は帯域幅 1 から σ を決め、実部の絶対値を画像ごとの最大で割る"),
    ("hx_gabor", "sk_gabor"): ("knob",
        "hx_ は a が向き・b が周波数、sk_ は a が周波数・向き 0 固定。包絡・正規化も違う"),

    # ---- gaussian(直した)----------------------------------------------------------------------
    # 2026-11-03 に直す前は xkor_gaussian が 5x5 固定で、cv_gaussian / gaussian と 0.28 食い違っていた。
    # 直したあとは 3 組とも一致なので、ここには書かない(一致した組に理由は要らない)。

    # ---- laplacian / scharr / tophat / median / bilateral / otsu / unsharp -----------------------
    ("cv_laplacian", "xkor_laplacian"): ("window",
        "cv_ は 3×3 の 4 近傍カーネル [0,1,0;1,−4,1;0,1,0] 固定、xkor_ は kornia の laplacian(3×3 は 8 近傍 "
        "[1,1,1;1,−8,1;1,1,1]、a で窓 3〜9)。カーネルが違う"),
    ("cv_scharr", "sk_scharr"): ("definition",
        "勾配の合成が違う: cv_ は |Gx| + |Gy|(L1)、sk_ は sqrt((Gx² + Gy²)/2)(L2)。どちらも画像ごとの最大で割る"),
    ("cv_tophat", "tophat"): ("window",
        "構造要素が違う: cv_ は楕円で大きさ 3+2int(3a)、core は正方形で _k(a) = 3, 5, 7, 9(a の 4 分割)。"
        "既定 a = 0.5 で楕円 5×5 と正方形 7×7。同じ構造要素なら scipy と OpenCV は差 0(確かめた)"),
    ("cv_median", "median"): ("knob",
        "窓の写し方が違う: cv_ は 3+2int(3a)、core は _k(a) = (3,5,7,9)[int(4a)](既定 a = 0.5 で 5 と 7)。"
        "窓を揃えると(ALIGNED)差は cv_ の 8 bit 量子化の 1/255 だけ"),
    ("cv_median", "xkor_median"): ("knob",
        "xkor_median の窓は core と同じ _k(a)。cv_ と窓を揃えると差は 8 bit 量子化の 1/255 だけ(ALIGNED)"),
    ("bilateral", "cv_bilateral"): ("window",
        "OpenCV の bilateralFilter(d = 5)は**半径 2 の円**の窓(21 画素)、core は 5×5 の正方形(25 画素)。"
        "core の式を円の窓にすると cv_ と内部 1.5e-7 で一致した(確かめた)。つまみの写し方は同じ"),
    ("cv_bilateral", "xkor_bilateral"): ("window",
        "xkor_ は core と同じ 5×5 の正方形、cv_ は半径 2 の円の窓。つまみの写し方は同じ"),
    ("cv_otsu", "otsu"): ("quant",
        "同じ大津法。cv_ は 8 bit に落としてから 256 段で切る、core は値の範囲を 256 ビンに分けて"
        "**ビンの上端**で切る。ビンの境に画素が集まる滑らかな画像で 0.7 % の画素が入れ替わる"),
    ("cv_otsu", "sk_otsu"): ("quant",
        "同じ大津法。skimage はビンの**中心**をしきい値にして v > t、cv_ は 8 bit の整数で切る"),
    ("otsu", "sk_otsu"): ("definition",
        "同じ大津法でしきい値をビンのどこに置くかが違う: core は上端(argmax のビンに居る画素を背景に)、"
        "skimage は中心。core は 2026-09-26 に中心から上端へ直した(docs/hardening/otsu-threshold-at-the-bin-midpoint.md)"),
    ("unsharp", "xkor_unsharp"): ("knob",
        "つまみの意味が違う: core は a が強さ 1.5a 倍・b が σ = 0.5+1.5b、xkor_ は強さ 1 固定(a 未使用)・"
        "b が σ = 0.5+2b。揃えると(ALIGNED)画像全体で 3e-7 で一致。"
        "2026-11-03 までは xkor_ の窓が 5×5 固定で揃えても一致しなかった(直した)"),
}

#: 「差はつまみの写し方だけ」を確かめる点。組 → [(a 側の (a, b), b 側の (a, b), 期待)]。
#: 期待は ("score", 上限)(内部の振れ幅比)/ ("affine", 上限)(定数倍とずれを除いた残り)/
#: ("max_abs", 上限)(内部の絶対差)。``tests/test_impl_differential.py`` が毎回確かめる。
ALIGNED = {
    ("cv_median", "median"): [((0.0, 0.5), (0.0, 0.5), ("max_abs", 1 / 255 + 1e-9)),
                              ((0.4, 0.5), (0.4, 0.5), ("max_abs", 1 / 255 + 1e-9)),
                              ((0.7, 0.5), (0.5, 0.5), ("max_abs", 1 / 255 + 1e-9))],
    ("cv_median", "xkor_median"): [((0.7, 0.5), (0.5, 0.5), ("max_abs", 1 / 255 + 1e-6))],
    ("dog", "sk_dog"): [((0.25, 0.25), (1 / 3, 0.5), ("affine", 1e-9))],
    ("dog", "xkor_dog"): [((0.25, 0.15), (0.5, 0.5), ("affine", 5e-5))],
    ("sk_dog", "xkor_dog"): [((0.2, 0.5), (0.5, 0.5), ("affine", 5e-5))],
    ("unsharp", "xkor_unsharp"): [((2 / 3, 0.0), (0.5, 0.0), ("score", 1e-5)),
                                  ((2 / 3, 0.5), (0.5, 0.375), ("score", 1e-5)),
                                  ((2 / 3, 1.0), (0.5, 0.75), ("score", 1e-5))],
}

#: 差がきっかり 0 の組 → 両方が呼んでいる同じ下位関数(**独立でない**)。
#: 載っていない差 0 の組は門が赤にする(内訳を確かめずに「一致」と書かない)。
SHARED_BACKEND = {
    ("sk_meijering", "xsk_meijering"): "skimage.filters.meijering(sigmas=range(1, 4)) を両方が呼ぶ。"
        "xsk_ は入力を [0,1] に clip するだけ(0〜255 の入力でだけ違う)= 重複した op",
    ("sk_skeleton", "skeleton"): "skimage.morphology.skeletonize を両方が呼ぶ。skimage が無い環境の skeleton は "
        "numpy_twins.skeletonize に落ち、それも探針の 2 枚で skimage と 1 画素も違わない(門で確かめる)",
}

#: 差がきっかり 0 の組のうち、**独立な実装**だが定義が自明で差 0 が当然のもの(検算としての重みは小さい)。
TRIVIAL_MATCH = {
    ("r2_smallest_rectangle1", "smallest_rectangle1"): "独立な numpy 実装 2 本(前景画素の行・列の最小・最大で塗る)。"
        "定義が自明なので差 0 は当然",
}

#: 語幹 → (判定, 一言)。判定は 「まとめてよい」/「一部まとめてよい」/「つまみを揃えればまとめてよい」/
#: 「近似としてなら」/「まとめない」。数えるのは前の 3 つ。
VERDICTS = ("まとめてよい", "一部まとめてよい", "つまみを揃えればまとめてよい", "近似としてなら", "まとめない")
MERGE_VERDICT = {
    "gaussian": ("まとめてよい", "3 実装が内部で一致(xkor_gaussian は 2026-11-03 に直して一致)。端は gaussian の b で選べる分だけ違う"),
    "meijering": ("まとめてよい", "同じ skimage 関数の重複。xsk_meijering は sk_meijering の別名にしてよい"),
    "skeleton": ("まとめてよい", "同じ skimage 関数(numpy の双子も一致)。sk_skeleton は skeleton の別名にしてよい"),
    "smallest_rectangle1": ("まとめてよい", "段 1 の C1(r2_smallest_rectangle1 → smallest_rectangle1 の別名)と同じ結論"),
    "bilateral": ("一部まとめてよい", "bilateral と xkor_bilateral は内部 3e-7 で一致。cv_bilateral は円の窓なので impl='cv' は「近い別実装」と書く"),
    "median": ("一部まとめてよい", "median と xkor_median は内部で一致(端は reflect と 0 埋めで違う)。cv_median は窓の写し方と 8 bit が違う"),
    "unsharp": ("つまみを揃えればまとめてよい", "xkor_unsharp の a を強さに繋げば core と一致する(今は a 未使用・強さ 1 固定)"),
    "dog": ("つまみを揃えればまとめてよい", "σ を揃えると定数倍(端の扱いが正規化に効く分)を除いて一致。impl 引数にするなら σ の写し方を 1 つにする"),
    "otsu": ("近似としてなら", "同じ大津法。しきい値のビン内の位置と 8 bit 量子化で 1 % 前後の画素が入れ替わる"),
    "clahe": ("まとめない", "core の clahe はつまみの意味が違う。cv_clahe と xkor_clahe は同じ定義で 8 bit 量子化の差(最大 0.087)"),
    "canny": ("まとめない", "core の canny は非極大抑制の無い簡易版。本物の 3 実装もつまみの意味(σ かしきい値か)と尺度が違う"),
    "corner_harris": ("まとめない", "窓の形・k・微分の尺度が違い、cv_ はつまみが無い"),
    "gabor": ("まとめない", "包絡・周波数の範囲・つまみの役(向き / 周波数)が実装ごとに違う"),
    "laplacian": ("まとめない", "4 近傍と 8 近傍のカーネル"),
    "scharr": ("まとめない", "勾配の合成が L1 と L2"),
    "tophat": ("まとめない", "構造要素の形(楕円 / 正方形)と大きさの写し方が違う"),
    "felzenszwalb": ("まとめない", "同じ skimage 関数を別の固定引数(sigma・min_size・境界の取り方)で呼ぶ"),
    "hessian": ("まとめない", "管状度と行列式 —— 別の量"),
    "guided_filter": ("まとめない", "guided_filter の中身は bilateral。guided filter は dl_guided_filter だけ"),
    "inpaint": ("まとめない", "biharmonic と Telea —— 別のアルゴリズム"),
    "orb_count": ("まとめない", "ORB の既定(端の除外・FAST)が違い、小さい画像で件数が大きく違う"),
    "richardson_lucy": ("まとめない", "仮定する PSF(ガウシアン / 3×3 の箱)が違う"),
    "wiener": ("まとめない", "逆畳み込みと適応雑音除去 —— 別の処理"),
    "clip_contours": ("まとめない", "矩形で切る / 長さで選ぶ —— 別の処理"),
    "crop_contours": ("まとめない", "窓の決め方が違う"),
    "regress_contours": ("まとめない", "正規化と集め方が違う"),
    "area_center": ("まとめない", "region 版と contour 版(HALCON でも別 op)"),
    "eccentricity": ("まとめない", "region 版と contour 版で量も違う"),
    "elliptic_axis": ("まとめない", "region 版と contour 版で量も違う"),
    "height_width_ratio": ("まとめない", "region 版と contour 版"),
    "curvature_flow": ("まとめない", "レベルセットの曲線短縮流と画像の平滑化 —— 別の処理"),
    "full_domain": ("まとめない", "region を返すか画像を返すか(どちらも自明)"),
    "measure_pairs": ("まとめない", "台帳の測定ハンドル版と a, b 入口の数え上げ —— 別の入口"),
    "measure_pos": ("まとめない", "同上"),
    "sart_reconstruct": ("まとめない", "台帳の sinogram 版と a, b 入口 —— 入口が違う(同じ名前で残すなら tm_ を別名に)"),
    "shape_index": ("まとめない", "点群版と画像版"),
}
