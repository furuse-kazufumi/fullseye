"""Optional library backends — scale the registry by WRAPPING ecosystems.

Reimplementing thousands of HALCON/OpenCV/skimage operators is the wrong move; the
right one is to *wrap* what already exists and keep only the differentiating layer
(typed IR + evolution + honest gate + codegen) in-house. If scikit-image / OpenCV
are installed, `build()` returns typed Op wrappers that the registry appends — so
op count scales with library coverage and evolution/codegen/catalog pick them up
for free. Every wrapper is exception-safe (a failing call degrades to identity)
because these are best-effort adapters over large APIs — see `_safe` for why that
degradation is a LAST RESORT and how to make it detectable.

Backend ops are prefixed (`sk_`, `cv_`) so they never shadow the always-available
numpy/scipy core; the core keeps working when neither library is present.
"""
from __future__ import annotations

import os

import numpy as np

from backend_safe import signed01

# ★The _safe fallback is a LAST RESORT and it can MASK A DEAD OP. For
# out_sort=="image" `backend_safe.fallback` returns the clipped INPUT, so a
# wrapper whose library call raises on every input looks to evolution / difftest
# / coverage like a working identity op instead of a failure. Runtime robustness
# is kept, but the degradation is DETECTABLE: every swallowed exception is
# recorded in the shared fallback ledger and strict mode re-raises instead.
#
# 2026-09-02: the ledger / strict switch moved DOWN into ``backend_safe`` so that
# the 23 other backend files (each with a private ``_safe``) report to the SAME
# place — before, this module was the only one of 24 wrapper families that
# recorded anything. The names below are kept as thin aliases for callers and
# tests that import them from here.
import backend_safe as _bs
from backend_safe import is_strict, set_strict, strict_mode  # noqa: F401  (re-exported)

_ERR_MAX = _bs._EVENT_MAX


def swallowed_errors() -> list[dict]:
    """Copy of the recorded fallback events (oldest first, bounded ring).

    Alias of :func:`backend_safe.fallbacks`; each dict also carries the legacy
    ``"fn"`` key (= ``"name"``).
    """
    return [dict(e, fn=e["name"]) for e in _bs.fallbacks()]


def last_error():
    """The most recently recorded fallback as a dict, or None."""
    e = _bs.last_fallback()
    return None if e is None else dict(e, fn=e["name"])


def clear_errors() -> None:
    """Drop the recorded fallbacks (call before a probe run)."""
    _bs.clear_fallbacks()


def _safe(fn, out_sort=None):
    """Wrap `fn` so a library failure degrades to a sort-valid fallback — RECORDED.

    Delegates to :func:`backend_safe.guard`: in strict mode (``strict_mode()`` /
    ``IMGEVOLVE_STRICT_BACKENDS=1``) the exception propagates; otherwise the event is
    appended to the ledger (``swallowed_errors()`` / ``fullseye.fallbacks()``), the op
    warns once, and the sort fallback is returned.
    """
    return _bs.guard(fn, out_sort)


def _u8(v):
    return (np.clip(v, 0, 1) * 255).astype(np.uint8)


#: lambda で定義された op の説明(lambda に docstring は書けない)。
#: ops.py の登録ループが Op.doc に積む。キーは op 名。
DOCS: dict[str, str] = {
    "sk_scharr": (
        "Scharr 勾配の大きさ。skimage の ``filters.scharr`` をそのまま呼び、"
        "水平/垂直それぞれの Scharr カーネル(3x3)の応答を合成した勾配強度を返す。\n\n"
        "HALCON の `edges_image`(Extract edges using Deriche, Lanser, Shen, or "
        "Canny filters.)に相当(近似。アルゴリズムは異なる)。Sobel より回転対称性"
        "(方向によらず応答が均一)が良いとされるカーネル。a, b は未使用 —— スケール"
        "や閾値の調整点が無く、常に固定カーネルで一発計算する軽量なエッジ検出。"
    ),
    "sk_farid": (
        "Farid-Simoncelli 勾配の大きさ。skimage の ``filters.farid`` をそのまま呼ぶ。"
        "5 タップの最適化された微分カーネルによる勾配強度で、Sobel/Scharr よりさらに"
        "回転対称性(方向誤差)が小さいとされる。\n\n"
        "HALCON の `edges_image` に相当(近似)。a, b は未使用。sk_scharr と同系統の"
        "「まず試すエッジ検出」だが、こちらは 5x5 相当のより大きなサポートを使う分"
        "ノイズにやや強い。"
    ),
    "sk_frangi": (
        "Frangi の管状構造検出フィルタ(vesselness filter)。血管・しわ・川のような"
        "細長い管状構造を、Hessian 行列の固有値比から検出する。\n\n"
        "HALCON の `lines_gauss`(Detect lines and their width.)に相当(近似。線の"
        "幅や XLD 輪郭は返さず、応答強度の画像のみを返す)。2026-08-30 に a, b を配線"
        "した: a はスケール範囲(``sigmas=range(1, 2+round(a*4))`` —— 最大 σ を 1〜5 "
        "に振る。a=0.5 で旧来の固定範囲 ``range(1,4)`` とビット一致)、b は Frangi の "
        "blobness 感度 β を 0.15〜0.85 に振る(b=0.5 で skimage 既定の 0.5 と一致し、"
        "既定出力は変わらない)。既定で ``black_ridges=True``(明るい背景上の暗い管を"
        "検出する)ため、白い背景に黒い線が乗った画像でないと応答が弱く出る点に注意。"
    ),
    "sk_meijering": (
        "Meijering の神経突起検出フィルタ(neuriteness filter)。Frangi と同じく "
        "Hessian の固有値から管状構造の類似度を計算するが、正規化の方法が異なる"
        "(神経突起画像向けにチューニングされた式)。\n\n"
        "HALCON の `lines_gauss` に相当(近似)。a, b は未使用 —— スケールは "
        "``sigmas=range(1, 4)`` に固定。sk_frangi と並べて使い、どちらが対象の線構造"
        "に強く反応するか比較する用途を想定。既定で ``black_ridges=True``。"
    ),
    "sk_hessian": (
        "Hybrid Hessian フィルタ。Frangi とほぼ同じ管状構造検出だが、平滑化の方法が"
        "異なる(近似的に Frangi の代替として使える)。\n\n"
        "HALCON の `lines_gauss` に相当(近似)。a, b は未使用 —— スケールは "
        "``sigmas=range(1, 4)`` に固定。sk_frangi / sk_meijering と 3 兄弟で、同じ入力"
        "に対する応答の違いを見比べる目的で並べてある。"
    ),
    "sk_dog": (
        "DoG(Difference of Gaussians、ガウス差分)フィルタ。2 つの異なる σ でぼかした"
        "画像の差分を取り、LoG(Laplacian of Gaussian)に近いバンドパス応答(特定の空間"
        "周波数帯だけを強調するエッジ/ブロブ検出)を安く得る。\n\n"
        "HALCON の `diff_of_gauss`(Approximate the LoG operator.)に相当。実装は "
        "``filters.difference_of_gaussians(v, 1.0, 1.0+3.0*a)`` の絶対値を正規化した"
        "もの —— 小さい方の σ は 1.0 に固定し、a は大きい方の σ を 1.0〜4.0 に振る"
        "(σ の比が広がるほど検出する構造のスケール帯が広がる)。b は未使用。"
    ),
    "sk_gabor": (
        "Gabor フィルタの応答強度。正弦波で変調したガウスカーネルを畳み込み、特定の"
        "空間周波数・方向を持つテクスチャに強く反応する古典的な特徴抽出器。\n\n"
        "HALCON の `gen_gabor`(Generate a Gabor filter.)に相当(近似。カーネル生成"
        "ではなく畳み込み結果を返す)。実装は ``filters.gabor(v, frequency=0.1+0.3*a)`` "
        "の実部(戻り値の 1 番目、虚部は捨てている)を絶対値化して正規化したもの —— "
        "a は周波数を 0.1〜0.4 に振る。方向 ``theta`` は既定の 0(水平方向のしま模様に"
        "最も反応)に固定されており、b は未使用。方向を振りたい場合は本 op では"
        "できないので注意。"
    ),
    "sk_butterworth": (
        "Butterworth フィルタ(周波数領域)。画像を FFT した上で、指定したカットオフ"
        "周波数より高い成分だけを通すハイパスフィルタとして働く(既定 ``high_pass=True``"
        " のまま呼んでいる)。輪郭やテクスチャの高周波成分を強調する。\n\n"
        "HALCON に直接対応するものは無い(空欄)。実装は "
        "``filters.butterworth(v, cutoff_frequency_ratio=0.05+0.3*a)`` を ``[0,1]`` に "
        "clip しただけ —— a はカットオフ比を 0.05〜0.35 に振る(小さいほど低周波まで"
        "削られ、応答が強く/広く出る)。b は未使用。ハイパスなので低コントラストな平坦"
        "領域は 0 付近に落ち、直流成分(平均輝度)の情報は失われる。"
    ),
    "sk_tv": (
        "全変動ノイズ除去(TV denoising、Chambolle 法)。エッジを保ったまま平坦部の"
        "ノイズを滑らかにする —— メディアン/ガウスぼかしと違い、輪郭のシャープさを"
        "崩しにくいのが特徴。\n\n"
        "HALCON に直接対応するものは無い。実装は "
        "``restoration.denoise_tv_chambolle(v, weight=0.02+0.3*a)`` —— a は denoising"
        " weight を 0.02〜0.32 に振り、**大きいほど強く平滑化される**(この符号の向きは"
        "後述の sk_tv_bregman と逆なので混同注意)。b は未使用。"
    ),
    "sk_wavelet": (
        "ウェーブレット変換によるノイズ除去。画像をウェーブレット領域に分解し、"
        "BayesShrink 基準のしきい値処理で小さい(=ノイズとみなせる)係数を落として"
        "から逆変換する。\n\n"
        "HALCON に直接対応するものは無い。実装は "
        "``restoration.denoise_wavelet(v)`` をそのまま ``[0,1]`` に clip したもので、"
        "しきい値やウェーブレット基底はすべて skimage の既定値まかせ —— a, b は未使用"
        "(調整点が無い、最も枯れた設定でとりあえずノイズを落としたい時用)。"
    ),
    "sk_adapthist": (
        "CLAHE(Contrast Limited Adaptive Histogram Equalization、コントラスト制限"
        "付き適応ヒストグラム均等化)。画像を小領域に分けて局所的にヒストグラムを均等化"
        "し、明暗差の大きい画像でも局所コントラストを底上げする。\n\n"
        "HALCON に直接対応するものは無い。実装は "
        "``exposure.equalize_adapthist(clip(v,0,1), clip_limit=0.01+0.05*a)`` —— a は"
        " clip_limit(コントラスト制限の強さ)を 0.01〜0.06 に振る(大きいほど強く"
        "コントラストが上がりノイズも増幅されやすい)。b は未使用。タイル分割数は"
        "skimage の既定値(8x8)のまま。"
    ),
    "sk_median_disk": (
        "円盤(disk)形の footprint によるメディアンフィルタ。通常の正方形カーネルと"
        "違い、円形に近い等方的な平滑化になる。\n\n"
        "HALCON の `median_image`(Compute a median filter with various masks.)に"
        "相当。実装は ``filters.median(v, footprint=disk(1+int(a*3)))`` —— a は円盤の"
        "半径を 1〜4 に振る(半径が大きいほど強く滑らかになるが細部も消える)。b は"
        "未使用。"
    ),
    "sk_otsu": (
        "大津の判別分析法(Otsu's method)による大域しきい値二値化。クラス間分散を"
        "最大化するしきい値を自動で選び、画像全体を前景/背景に二分する。\n\n"
        "HALCON の `binary_threshold`(Segment an image using binary "
        "thresholding.)に相当。実装は ``v > filters.threshold_otsu(v)`` —— a, b は"
        "未使用(しきい値は完全自動)。双峰性(2 山)のヒストグラムを持つ画像で最も"
        "うまく働き、コントラストが低い/単峰の画像では境界がずれやすい。"
    ),
    "sk_li": (
        "Li の最小相互エントロピー法(Minimum Cross Entropy)による大域しきい値"
        "二値化。前景/背景の分布間の相互エントロピーを反復的に最小化してしきい値を"
        "決める、大津法とは別系統の自動しきい値法。\n\n"
        "HALCON の `binary_threshold` に相当(近似。アルゴリズムは別物)。実装は "
        "``v > filters.threshold_li(v)`` —— a, b は未使用。大津法よりノイズや裾の"
        "重いヒストグラムに強いとされる場面がある。"
    ),
    "sk_yen": (
        "Yen の最大相関基準(maximum correlation criterion)による大域しきい値"
        "二値化。ヒストグラムのエントロピーベースの評価量を最大化してしきい値を選ぶ、"
        "大津法・Li 法とはまた別の自動しきい値法。\n\n"
        "HALCON の `binary_threshold` に相当(近似)。実装は "
        "``v > filters.threshold_yen(v)`` —— a, b は未使用。同じ画像に大津/Li/Yen を"
        "並べて試し、しきい値が安定する方を選ぶ用途を想定。"
    ),
    "sk_sauvola": (
        "Sauvola の局所適応しきい値。各ピクセル周辺の局所平均・標準偏差から"
        "ローカルにしきい値を決める手法で、照明ムラのある文書画像の二値化"
        "(文字抽出)向けに設計されている。\n\n"
        "HALCON の `var_threshold`(Threshold an image by local mean and standard "
        "deviation analysis.)に相当。実装は "
        "``v > filters.threshold_sauvola(v, window_size=2*int(a*6)+3)`` —— a は"
        "局所窓のサイズを 3〜15(奇数)に振る(小さいほど照明ムラに強いが計算が細かく"
        "ノイズにも敏感)。b は未使用。k, r パラメータは skimage の既定値のまま。"
    ),
    "sk_niblack": (
        "Niblack の局所適応しきい値。Sauvola と同じく局所平均・標準偏差から"
        "しきい値を決めるが、係数の与え方がより単純(古典的)で、Sauvola より前景を"
        "広めに(=ノイズを拾いやすく)判定する傾向がある。\n\n"
        "HALCON の `var_threshold` に相当(近似)。実装は "
        "``v > filters.threshold_niblack(v, window_size=2*int(a*6)+3)`` —— a は局所窓"
        "サイズを 3〜15(奇数)に振る。b は未使用。sk_sauvola と同じ入力・同じ a の"
        "振り方で並べ、結果を見比べる用途を想定。"
    ),
    "sk_canny": (
        "Canny エッジ検出(領域版)。ガウス平滑化 → 勾配計算 → 非極大抑制 → "
        "ヒステリシスしきい値、という古典的な多段パイプラインでエッジ画素を求め、"
        "真偽値の領域として返す。\n\n"
        "HALCON の `edges_image` に相当。実装は "
        "``feature.canny(v, sigma=0.5+2.0*a)`` —— a は前段のガウス平滑化の σ を "
        "0.5〜2.5 に振る(大きいほど細かいノイズ由来のエッジが消え、太い輪郭だけ残る)。"
        "b は未使用 —— ヒステリシスの低/高しきい値は skimage が画像から自動推定した"
        "値のまま(明示指定していない)。"
    ),
    "sk_skeleton": (
        "領域の骨格化(skeletonization)。前景領域をトポロジー(連結関係・穴の数)"
        "を保ったまま 1 画素幅の線に細める。\n\n"
        "HALCON の `skeleton`(Compute the skeleton of a region.)に相当(近似。"
        "アルゴリズムは Zhang-Suen 系)。実装は ``morphology.skeletonize(binm(v))`` "
        "—— 入力はまず ``binm``(> 0.5 のしきい値)で真偽値化される。a, b は未使用。"
    ),
    "sk_medial": (
        "中心軸変換(medial axis transform)。距離変換の尾根線を抽出する方式で"
        "骨格を求める、sk_skeleton とは別アルゴリズム。輪郭からの距離情報を保った"
        "骨格になりやすい。\n\n"
        "HALCON の `skeleton` に相当(近似)。実装は "
        "``morphology.medial_axis(binm(v), rng=0)`` —— ``rng=0`` はタイ(同点)の"
        "崩し方を決める乱数シードを固定し、毎回同じ結果になるようにしている。"
        "a, b は未使用。distance 出力(``return_distance``)は使っておらず、骨格の"
        "真偽値マスクのみを返す。"
    ),
    "sk_convex": (
        "凸包(convex hull)による領域の変形。前景領域を包む最小の凸多角形を求め、"
        "その内部を塗りつぶした領域を返す —— くびれや凹みを全て埋める。\n\n"
        "HALCON の `shape_trans`(Transform the shape of a region.)に相当(近似。"
        "``shape_trans`` は他の変形モードも持つ汎用命令だが、ここでは凸包のみ)。実装は "
        "``morphology.convex_hull_image(binm(v))``。a, b は未使用。"
    ),
    "sk_thin": (
        "モルフォロジー的細線化(thinning)。sk_skeleton と似た 1 画素幅化だが、"
        "アルゴリズムが異なりヒット・オア・ミス変換ベースで、骨格の枝(スパー)が"
        "出にくい傾向がある。\n\n"
        "HALCON の `thinning`(Remove the result of a hit-or-miss operation from a "
        "region.)に相当。実装は ``morphology.thin(binm(v))``。a, b は未使用。"
        "sk_skeleton / sk_medial と 3 通りの細線化を並べ、対象形状に合うものを選べる"
        "ようにしてある。"
    ),
    "sk_remove_holes": (
        "小さい穴埋め。前景領域の内部にある背景の孔(穴)のうち、面積が"
        "しきい値未満のものだけを塗りつぶす —— 大きな孔(意図した開口部)は残す。\n\n"
        "HALCON の `fill_up`(Fill up holes in regions.)に相当(近似。HALCON 版は"
        "全ての孔を埋めるが、こちらは面積フィルタ付き)。実装は "
        "``morphology.remove_small_holes(binm(v), area_threshold=int(8+a*60))`` —— "
        "a は埋める孔の面積上限を 8〜68 画素に振る。b は未使用。"
    ),
    "sk_euler": (
        "オイラー数(Euler number)。「連結成分の数 − 穴の数」で定義されるトポロジー"
        "的な特徴量で、領域の形そのもの(位置・大きさ)ではなく「繋がり方」だけを"
        "表す整数値になる。\n\n"
        "HALCON の `euler_number`(Calculate the Euler number.)に相当。実装は "
        "``measure.euler_number(binm(v))``。a, b は未使用。出力は 1 個のスカラー"
        "(``feature`` 型)。"
    ),
    "sk_find_contours": (
        "等高線抽出(marching squares)。グレースケール画像上で指定したレベル値と"
        "交差する曲線を辿り、サブピクセル精度の輪郭座標列の集合として返す —— 二値"
        "画像の外周だけでなく、連続値の等高線も扱える点が二値輪郭抽出と違う。\n\n"
        "HALCON に直接対応するものは無い(空欄)。実装は "
        "``measure.find_contours(v, level=0.2+0.5*a)`` のうち頂点数 3 未満の断片を"
        "捨てたもの —— a は等高線のレベル(しきい値)を 0.2〜0.7 に振る。b は未使用。"
        "戻り値は画像形状と輪郭座標配列のリストを持つ辞書(``contour`` 型)。"
    ),
    "sk_lbp": (
        "LBP(Local Binary Pattern、局所二値パターン)。各画素を中心に円周上の"
        "近傍画素と大小比較して 2 進コードを作る、照明変化に強いテクスチャ記述子。\n\n"
        "HALCON に直接対応するものは無い。実装は "
        "``feature.local_binary_pattern(v, 8, 1+int(a*3))`` を正規化したもの —— "
        "近傍点数 P=8 は固定、a は半径 R を 1〜4 に振る(半径が大きいほど粗いスケール"
        "のテクスチャを拾う)。b は未使用。method は既定の ``'default'``(回転不変では"
        "ない、最も基本的な符号化)。"
    ),
    "sk_entropy": (
        "局所エントロピー。各画素の周辺(円盤状の近傍)にあるグレー値分布の"
        "シャノンエントロピー(2 進対数)を計算し、その場所を符号化するのに必要な"
        "最小ビット数として画像化する —— テクスチャの複雑さ・情報量の指標。\n\n"
        "HALCON の `entropy_image`(Calculate the entropy of gray values within a "
        "rectangular window.)に相当(近似。窓形状は矩形でなく円盤)。実装は "
        "``filters.rank.entropy(_u8s(v), disk(1+int(a*3)))`` を正規化したもの —— "
        "a は円盤半径を 1〜4 に振る。b は未使用。入力は内部で 8 bit 化されるため、"
        "元画像の微妙な階調差は失われる。"
    ),
    "sk_enhance_contrast": (
        "局所コントラスト強調。各画素を、局所近傍の最大値と最小値のどちらに近いかで"
        "判定し、近い方の値へ置き換える —— 中間的な値を持つ画素が両極端に押し出され、"
        "見かけ上のコントラストが上がる(2 値化に近い効果が出ることもある)。\n\n"
        "HALCON に直接対応するものは無い。実装は "
        "``filters.rank.enhance_contrast(_u8s(v), disk(1+int(a*3)))`` を 255 で"
        "割ったもの —— a は円盤半径を 1〜4 に振る。b は未使用。"
    ),
    "sk_autolevel": (
        "局所オートレベル。各画素周辺の局所ヒストグラムの最小〜最大値を "
        "0〜255 いっぱいに引き伸ばす —— グローバルな階調ではなく場所ごとに"
        "コントラストを最大化する適応的なレベル補正。\n\n"
        "HALCON の `scale_image_max`(Maximum gray value spreading in the value "
        "range 0 to 255.)に相当(近似。HALCON 版は画像全体、こちらは局所窓ごと)。"
        "実装は ``filters.rank.autolevel(_u8s(v), disk(1+int(a*3)))`` を 255 で"
        "割ったもの —— a は円盤半径を 1〜4 に振る。b は未使用。ほぼ一様な領域では"
        "ノイズまで強く引き伸ばされる点に注意。"
    ),
    "sk_shape_index": (
        "形状指標(shape index)。Hessian 行列の固有値から、局所的な表面形状を "
        "-1(球状の窪み)〜0(鞍点)〜+1(球状の膨らみ)の 1 次元スカラーで表す —— "
        "曲率の「向き」を要約する記述子。\n\n"
        "HALCON に直接対応するものは無い。実装は "
        "``feature.shape_index(v, sigma=0.5+2.0*a)`` の NaN(平坦領域で未定義になる)"
        "を 0 に置き換えてから ``signed01``(符号付き応答の 0 を 0.5 に写像し、"
        "±最大値を 0/1 に写像する)で ``[0,1]`` へ写した値 —— a は Hessian を計算する"
        "際のガウス微分の σ を 0.5〜2.5 に振る。b は未使用。"
    ),
    "sk_hessian_det": (
        "Hessian 行列式によるブロブ検出応答。2 階微分の行列(Hessian)の行列式は、"
        "ブロブ状の構造で正、鞍点状の構造で負になる符号付き応答。\n\n"
        "HALCON に直接対応するものは無い。実装は "
        "``feature.hessian_matrix_det(v, sigma=0.5+2.5*a)`` を ``signed01`` で "
        "``[0,1]`` へ写した値(符号を保つため 0.5 が「応答ゼロ」に対応)—— a は"
        "スケール σ を 0.5〜3.0 に振る。b は未使用。"
    ),
    "sk_corner_harris": (
        "Harris コーナー応答(skimage 実装)。勾配の構造テンソルから、平坦部/エッジ/"
        "コーナーを見分ける符号付きスコアを計算する古典的なコーナー検出器。\n\n"
        "HALCON の `points_harris`(Detect points of interest using the Harris "
        "operator.)に相当(近似。座標点ではなく応答画像を返す)。実装は "
        "``feature.corner_harris(v, sigma=0.5+2.0*a)`` を ``signed01`` で ``[0,1]`` "
        "へ写した値 —— a は微分に使うガウス σ を 0.5〜2.5 に振る。b は未使用。"
        "Harris の自由パラメータ k は skimage の既定値(0.05)のまま固定。OpenCV 版の"
        "cv_corner_harris とはパラメータの振り方が異なるので同一結果にはならない。"
    ),
    "sk_adjust_log": (
        "対数階調変換(log transform)。``out = gain * log(1 + in)`` 型の対数カーブで"
        "暗部を持ち上げる階調補正 —— ガンマ補正と似た用途だが、暗部だけをより強く"
        "持ち上げる非線形カーブになる。\n\n"
        "HALCON の `log_image`(Calculate the logarithm of an image.)に相当。実装は "
        "``exposure.adjust_log(clip(v,0,1), gain=0.5+1.5*a)`` の結果を ``[0,1]`` へ "
        "clip したもの —— a は gain を 0.5〜2.0 に振る。b は未使用。gain が 1 を"
        "超えると出力が 1 を僅かに超えることが実測されている(a=0.5 で max=1.1380)"
        "ため、``image`` 契約([0,1])を守るために出口で明示的に clip している —— "
        "パイプライン内では ``ops._apply`` の段間 clip と同じ値になるためビット不変"
        "だが、直接呼び出した時の白飛びの見え方は clip 追加前と変わる。"
    ),
    "sk_rolling_ball": (
        "ローリングボール法による背景差し引き。画像の輝度を地形と見立て、指定半径の"
        "球をその下から転がして得られる包絡面を背景と推定し、元画像から引き算する"
        "—— 照明ムラ(緩やかな輝度勾配)の除去に使う。\n\n"
        "HALCON に直接対応するものは無い。実装は "
        "``v - restoration.rolling_ball(v, radius=5+int(a*20))`` を ``[0,1]`` へ "
        "clip したもの —— a は球の半径を 5〜25 に振る(大きいほど緩やかな照明ムラ"
        "しか背景とみなさず、細かい構造は残る)。b は未使用。"
    ),
    "sk_nlm": (
        "Non-local means(非局所平均法)ノイズ除去。近接画素だけでなく画像全体から"
        "似たパッチを探して平均する —— 反復模様やテクスチャを保ったまま平坦部の"
        "ノイズだけを落とせるのが、単純な平滑化との違い。\n\n"
        "HALCON に直接対応するものは無い。実装は "
        "``restoration.denoise_nl_means(v, patch_size=5, h=0.02+0.2*a)`` —— a は"
        "カットオフ距離 h(大きいほど「似ている」と判定される範囲が広がり、強く"
        "ノイズ除去される代わりにディテールも失われやすい)を 0.02〜0.22 に振る。"
        "パッチサイズは 5x5 に固定。b は未使用。"
    ),
    "sk_tv_bregman": (
        "全変動ノイズ除去(TV denoising、Split-Bregman 法)。sk_tv と同じ TV"
        "正則化の考え方だが最適化アルゴリズムが異なり(Bregman 分割法)、収束が速い"
        "とされる。\n\n"
        "HALCON に直接対応するものは無い。実装は "
        "``restoration.denoise_tv_bregman(v, weight=1.0+8.0*a)`` を ``[0,1]`` へ "
        "clip したもの —— a は weight を 1.0〜9.0 に振るが、この関数の weight は"
        "**小さいほど強く平滑化される**(sk_tv の weight とは符号の向きが逆 —— "
        "``denoise_tv_chambolle`` は大きいほど強く、``denoise_tv_bregman`` は"
        "小さいほど強い。混同すると意図と逆方向に a を動かすことになるので注意)。"
        "b は未使用。"
    ),
    "sk_swirl": (
        "渦巻き変形(swirl warp)。画像中心の周りで、中心に近いほど大きく回転させる"
        "非線形な幾何変換 —— 極座標変換を応用した歪みエフェクト。\n\n"
        "HALCON の `polar_trans_image`(Transform an image to polar coordinates)に"
        "相当(近似。極座標画像そのものではなく、渦状に歪ませた直交座標画像を返す)。"
        "実装は ``transform.swirl(v, strength=1+4*a, radius=30)`` を ``[0,1]`` へ "
        "clip したもの —— a は渦の強さを 1〜5 に振る。渦の半径は 30 画素に固定。"
        "b は未使用。"
    ),
    "sk_area_opening": (
        "面積オープニング(area opening)。通常のモルフォロジー的開処理が"
        "構造要素の形で小さい明部を削るのに対し、こちらは面積(連結画素数)だけで"
        "判定し、指定面積未満の明るい連結成分を消す —— 形状に依らず「小さい」ものを"
        "落とせる。\n\n"
        "HALCON に直接対応するものは無い。実装は "
        "``morphology.area_opening(v, area_threshold=int(16+a*100))`` —— a は面積"
        "しきい値を 16〜116 画素に振る。b は未使用。connectivity は既定の 1"
        "(4 近傍)のまま。"
    ),
    "sk_felzenszwalb": (
        "Felzenszwalb のグラフベース領域分割。画素をノードとする最小全域木クラスタ"
        "リングで、明確な境界が無くても画像を過分割(オーバーセグメンテーション)"
        "する高速な手法。ここでは分割結果の境界線を領域として返す。\n\n"
        "HALCON に直接対応するものは無い。実装は "
        "``segmentation.find_boundaries(segmentation.felzenszwalb(v, scale=20+200*a, "
        "channel_axis=None))`` —— a は scale(観測レベル。大きいほどセグメントが"
        "少なく大きくなる)を 20〜220 に振る。sigma(前処理の平滑化)・min_size は"
        "既定値(0.8, 20)のまま固定。b は未使用。"
    ),
    "sk_slic": (
        "SLIC(Simple Linear Iterative Clustering)によるスーパーピクセル分割。"
        "色(ここではグレー値)と座標を合わせた空間で k-means クラスタリングを行い、"
        "ほぼ均等な大きさの領域に分割する。ここでは分割結果の境界線を領域として"
        "返す。\n\n"
        "HALCON に直接対応するものは無い。実装は "
        "``segmentation.find_boundaries(segmentation.slic(v, "
        "n_segments=int(10+80*a), channel_axis=None))`` —— a はおおよそのセグメント"
        "数を 10〜90 に振る(大きいほど細かく分割される)。b は未使用。"
    ),
    "sk_chan_vese": (
        "Chan-Vese セグメンテーション。レベルセット(等位集合)を輝度の分散が"
        "領域内で最小になるように反復して動かす能動輪郭モデルで、エッジがはっきり"
        "しない対象でも領域を検出できる。\n\n"
        "HALCON に直接対応するものは無い。実装は "
        "``segmentation.chan_vese(v, mu=0.1+0.4*a, max_num_iter=60)`` —— a は"
        "'edge length' 重み mu を 0.1〜0.5 に振る(大きいほど輪郭が丸く滑らかになり"
        "細部を無視しやすくなる)。反復回数は 60 に固定。b は未使用。初期レベルセット"
        "は既定の 'checkerboard'(チェッカーボード状)。"
    ),
    "sk_local_maxima": (
        "局所極大点の検出。近傍のどの画素よりも真に大きい(プラトー=同値の連結"
        "領域も許容)画素の集合を領域として返す —— ピーク検出・特徴点抽出の下処理。\n\n"
        "HALCON の `local_max`(Detect all local maxima in an image.)に相当。実装は "
        "``morphology.local_maxima(v)``。a, b は未使用 —— footprint は既定値"
        "(全方向 1 近傍)のまま。"
    ),
    "sk_hysteresis": (
        "ヒステリシスしきい値処理。2 段のしきい値を使い、高い方を超える画素をまず"
        "確定させ、低い方を超えつつ確定画素と連結している画素も追加で採用する —— "
        "Canny のエッジ連結ステップと同じ考え方を汎用の応答画像に適用したもの。\n\n"
        "HALCON の `hysteresis_threshold`(Perform a hysteresis threshold operation "
        "on an image.)に相当。実装は "
        "``filters.apply_hysteresis_threshold(v, 0.2+0.3*a, 0.5+0.3*b)`` —— a は"
        "低い方のしきい値を 0.2〜0.5 に、b は高い方のしきい値を 0.5〜0.8 に振る。"
        "a を大きく・b を小さくすると 2 つが逆転しうる(low > high)ので、極端な"
        "組み合わせでは skimage 側の挙動に委ねられる点に注意。"
    ),
    "sk_clear_border": (
        "画像端に接する成分の除去。前景領域のうち画像の外周に触れている連結成分を"
        "すべて背景に落とす —— 視野の端で切れた(全体像が写っていない)物体を"
        "解析対象から除外する定番の前処理。\n\n"
        "HALCON に直接対応するものは無い。実装は "
        "``segmentation.clear_border(binm(v))``。a, b は未使用 —— 除去判定に使う"
        "縁の幅(buffer_size)は既定の 0(画像端そのものに触れている成分のみ対象)。"
    ),
    "sk_find_boundaries": (
        "領域境界の抽出。ラベル画像(ここでは真偽値領域)の中で、異なるラベル同士"
        "(前景/背景)が接する画素だけを True にした境界マスクを返す。\n\n"
        "HALCON の `boundary`(Reduce a region to its boundary.)に相当。実装は "
        "``segmentation.find_boundaries(binm(v))``。a, b は未使用 —— connectivity は"
        "既定の 1、mode は既定の 'thick'(境界の両側 1 画素ずつを含む太めの境界)。"
    ),
    "sk_entropy_feat": (
        "画像全体のシャノンエントロピー(1 スカラー特徴量)。輝度ヒストグラムの"
        "分布の広がり・情報量を 1 個の数値で要約する —— 値が高いほど輝度分布が"
        "均一に散らばっている(情報量が多い/コントラストが豊富)ことを示す。\n\n"
        "HALCON の `entropy_gray`(Determine the entropy and anisotropy of "
        "images.)に相当(近似。異方性は計算しない)。実装は "
        "``measure.shannon_entropy(v)``(既定の底 2、単位はビット)。a, b は未使用。"
    ),
    "sk_blur_effect": (
        "ぼけ具合の推定(1 スカラー特徴量)。画像を意図的に少し再ぼかしして、元と"
        "再ぼかし後でどれだけエッジの鋭さが変わるかを比較する手法で、0(ぼけ無し)〜"
        "1(最大限ぼけている)のスコアを返す —— 参照画像なしでピント/ブレを定量化"
        "できる。\n\n"
        "HALCON に直接対応するものは無い。実装は ``measure.blur_effect(v)``。"
        "a, b は未使用 —— 再ぼかしフィルタのサイズは既定値(11)のまま。"
    ),
    "cv_bilateral": (
        "バイラテラルフィルタ(OpenCV 実装)。空間的な近さと輝度値の近さの両方を"
        "重みにしたガウス的平滑化で、エッジ(輝度差の大きい境界)をぼかさずに平坦部"
        "だけを滑らかにする。\n\n"
        "HALCON の `bilateral_filter`(bilateral filtering of an image.)に相当。"
        "実装は ``cv2.bilateralFilter(v, d=5, sigmaColor=0.05+0.4*b, "
        "sigmaSpace=1.0+3.0*a)`` —— カーネル直径 d は 5 に固定、**a は空間方向の"
        "広がり sigmaSpace を 1.0〜4.0 に、b は輝度方向の許容差 sigmaColor を "
        "0.05〜0.45 に振る**(引数の並びが sigmaColor, sigmaSpace の順なので a/b の"
        "対応がずれやすい点に注意)。"
    ),
    "cv_median": (
        "メディアンフィルタ(OpenCV 実装)。正方形近傍内の中央値に置き換える"
        "定番のノイズ除去(特に胡椒塩ノイズに強く、エッジも比較的保たれる)。\n\n"
        "HALCON の `median_image` に相当。実装は "
        "``cv2.medianBlur(_u8(v), ksize=3+2*int(a*3))`` —— a はカーネルサイズを "
        "3, 5, 7, 9(奇数)に振る。b は未使用。8 bit に量子化してから処理するため、"
        "元画像の微妙な階調は失われる。sk_median_disk と違い正方形カーネル。"
    ),
    "cv_box": (
        "単純平均化フィルタ(box filter、OpenCV 実装)。正方形近傍内の単純平均を"
        "取るだけの最も基本的な平滑化 —— ガウス平滑化より計算は軽いが、リング状の"
        "アーティファクトが出やすい。\n\n"
        "HALCON の `mean_image`(Smooth by averaging.)に相当。実装は "
        "``cv2.blur(v, (k,k))``、``k=3+2*int(a*3)`` —— a はカーネルサイズを "
        "3, 5, 7, 9 に振る。b は未使用。"
    ),
    "cv_gaussian": (
        "ガウス平滑化(OpenCV 実装)。ガウスカーネルによる標準的なぼかしで、"
        "box filter よりリンギングが出にくい。\n\n"
        "HALCON の `gauss_filter`(Smooth using discrete Gauss functions.)に相当。"
        "実装は ``cv2.GaussianBlur(v, (0,0), sigmaX=0.3+2.7*a)`` —— カーネルサイズを"
        "指定せず ``(0,0)`` にすることで OpenCV に σ から自動算出させている。a は σ を"
        "0.3〜3.0 に振る。b は未使用。"
    ),
    "cv_scharr": (
        "Scharr 勾配の大きさ(OpenCV 実装)。水平・垂直それぞれの Scharr 微分の"
        "絶対値を足し合わせて勾配強度とする —— sk_scharr(skimage 版)と同種の"
        "エッジ検出だが、合成方法(平方和のノルムではなく絶対値の和)が異なるため"
        "同一結果にはならない。\n\n"
        "HALCON の `edges_image` に相当(近似)。実装は "
        "``|cv2.Scharr(v,CV_64F,1,0)| + |cv2.Scharr(v,CV_64F,0,1)|`` を正規化した"
        "もの。a, b は未使用。"
    ),
    "cv_laplacian": (
        "ラプラシアンフィルタ(OpenCV 実装)。2 階微分による等方的なエッジ/ブロブ"
        "検出で、輪郭のみならず孤立点にも強く反応する(ノイズにも敏感)。\n\n"
        "HALCON の `laplace`(Calculate the Laplace operator by using finite "
        "differences.)に相当。実装は ``|cv2.Laplacian(v, CV_64F)|`` を正規化した"
        "もの —— カーネルサイズは既定の 1(3x3 の基本 4 近傍ラプラシアンカーネル)"
        "に固定。a, b は未使用。"
    ),
    "cv_clahe": (
        "CLAHE(コントラスト制限付き適応ヒストグラム均等化、OpenCV 実装)。"
        "sk_adapthist と同じ考え方の局所コントラスト強調だが、OpenCV の実装・"
        "タイル分割方式を使う。\n\n"
        "HALCON に直接対応するものは無い。実装は "
        "``cv2.createCLAHE(clipLimit=1.0+4.0*a).apply(_u8(v))`` を 255 で割った"
        "もの —— a は clipLimit(コントラスト制限の強さ)を 1.0〜5.0 に振る。"
        "タイルグリッドサイズは既定の 8x8 のまま。b は未使用。"
    ),
    "cv_open": (
        "グレー値モルフォロジー開処理(opening、OpenCV 実装)。収縮してから膨張する"
        "ことで、構造要素より小さい明るい突起・孤立点を消す。\n\n"
        "HALCON の `gray_opening`(Perform a gray value opening on an image.)に"
        "相当。実装は ``cv2.morphologyEx(v, MORPH_OPEN, se)``、楕円形の構造要素 se は"
        "``getStructuringElement(MORPH_ELLIPSE, (k,k))``、``k=3+2*int(a*3)`` —— a は"
        "構造要素のサイズを 3〜9 に振る。b は未使用。"
    ),
    "cv_close": (
        "グレー値モルフォロジー閉処理(closing、OpenCV 実装)。膨張してから収縮"
        "することで、構造要素より小さい暗い穴・隙間を埋める(cv_open の逆の効果)。\n\n"
        "HALCON の `gray_closing`(Perform a gray value closing on an image.)に"
        "相当。実装は ``cv2.morphologyEx(v, MORPH_CLOSE, se)``(楕円形構造要素、"
        "サイズは cv_open と同じ ``3+2*int(a*3)``)—— a は構造要素サイズを 3〜9 に"
        "振る。b は未使用。"
    ),
    "cv_tophat": (
        "トップハット変換(top-hat、OpenCV 実装)。「元画像 − 開処理結果」を計算し、"
        "明るい背景の上にある、構造要素より小さい明るい特徴だけを抽出する。\n\n"
        "HALCON の `gray_tophat`(Perform a gray value top hat transformation on an "
        "image.)に相当。実装は ``cv2.morphologyEx(v, MORPH_TOPHAT, se)`` を正規化"
        "したもの、se は楕円形でサイズ ``3+2*int(a*3)`` —— a は構造要素サイズを "
        "3〜9 に振る。b は未使用。"
    ),
    "cv_gradient": (
        "モルフォロジー勾配(OpenCV 実装)。「膨張結果 − 収縮結果」で、領域の輪郭"
        "(縁取り)だけを取り出す —— 通常の微分ベースのエッジ検出とは別系統の輪郭"
        "抽出。\n\n"
        "HALCON の `gray_range_rect`(Determine the gray value range within a "
        "rectangle.)に相当(近似。矩形窓内の最大-最小レンジを取る点は同じ発想)。"
        "実装は ``cv2.morphologyEx(v, MORPH_GRADIENT, se)`` を正規化したもの、se は"
        "楕円形でサイズ ``3+2*int(a*3)`` —— a は構造要素サイズを 3〜9 に振る。b は"
        "未使用。"
    ),
    "cv_otsu": (
        "大津の判別分析法による大域しきい値二値化(OpenCV 実装)。sk_otsu と同じ"
        "アルゴリズムだが、内部で 8 bit に量子化してから計算する点が異なる(結果が"
        "わずかにずれ得る)。\n\n"
        "HALCON の `binary_threshold` に相当。実装は "
        "``cv2.threshold(_u8(v), 0, 255, THRESH_BINARY+THRESH_OTSU)`` の結果を"
        "真偽値化したもの。a, b は未使用。"
    ),
    "cv_adaptive_mean": (
        "局所平均によるしきい値二値化(adaptive threshold、mean 版、OpenCV 実装)。"
        "各画素の周辺の単純平均から定数を引いた値をしきい値として使う —— 照明ムラの"
        "ある画像で大域しきい値より安定する。\n\n"
        "HALCON の `dyn_threshold`(Segment an image using a local threshold.)に"
        "相当。実装は ``cv2.adaptiveThreshold(_u8(v), 255, ADAPTIVE_THRESH_MEAN_C, "
        "THRESH_BINARY, blockSize=2*int(a*6)+3, C=int(b*10))`` —— a は局所窓の"
        "サイズ(blockSize)を 3〜15(奇数)に、b は局所平均から引く定数 C を 0〜10 に"
        "振る(C が大きいほど前景と判定される画素が減る)。"
    ),
    "cv_adaptive_gauss": (
        "局所ガウス重み付き平均によるしきい値二値化(adaptive threshold、"
        "Gaussian 版、OpenCV 実装)。cv_adaptive_mean と同じ枠組みだが、局所平均を"
        "単純平均ではなくガウス重み付き平均で取るため、窓の境界付近の急な変化が"
        "出にくい。\n\n"
        "HALCON の `local_threshold`(Segment an image using local thresholding.)に"
        "相当。実装は ``cv2.adaptiveThreshold(_u8(v), 255, "
        "ADAPTIVE_THRESH_GAUSSIAN_C, THRESH_BINARY, blockSize=2*int(a*6)+3, "
        "C=int(b*10))`` —— a は blockSize を 3〜15(奇数)に、b は定数 C を 0〜10 に"
        "振る。"
    ),
    "cv_canny": (
        "Canny エッジ検出(領域版、OpenCV 実装)。sk_canny と同じアルゴリズムだが、"
        "OpenCV 版はガウス平滑化の σ ではなく 2 本のしきい値を直接指定する API に"
        "なっている。\n\n"
        "HALCON の `edges_image` に相当。実装は "
        "``cv2.Canny(_u8(v), threshold1=int(50+100*a), threshold2=int(100+150*b))`` "
        "の結果を真偽値化したもの —— a は下側しきい値(弱いエッジの採用ライン)を "
        "50〜150 に、b は上側しきい値(強いエッジの確定ライン)を 100〜250 に振る。"
        "a を大きく b を小さく振ると下側が上側を上回ることがあり、その場合の挙動は "
        "OpenCV の実装依存になる点に注意。"
    ),
    "cv_corner_harris": (
        "Harris コーナー応答(OpenCV 実装)。sk_corner_harris と同じ Harris の"
        "考え方だが、勾配計算・平滑化のブロックサイズなどを固定パラメータで計算する"
        "OpenCV 版。\n\n"
        "HALCON の `points_harris` に相当(近似)。実装は "
        "``cv2.cornerHarris(v, blockSize=2, ksize=3, k=0.04)`` を ``signed01`` で "
        "``[0,1]`` へ写した値 —— blockSize(近傍サイズ)・ksize(Sobel 開口)・k"
        "(Harris の自由パラメータ)はすべて固定。a, b は未使用 —— skimage 版と違い"
        "スケールを振る仕組みが無い、素の Harris 応答。"
    ),
    "cv_min_eigen": (
        "最小固有値によるコーナー強度(Shi-Tomasi 系、OpenCV 実装)。勾配の構造"
        "テンソルの 2 つの固有値のうち小さい方を返す —— Harris のような重み付け"
        "(k 依存)が無く、より直接的に「良い特徴点」らしさを測る指標(cv_good_"
        "features の内部でも使われる基準と同種)。\n\n"
        "HALCON の `points_harris` に相当(近似。アルゴリズムは別物)。実装は "
        "``cv2.cornerMinEigenVal(v, blockSize=3+2*int(a*2))`` を正規化したもの —— "
        "a は評価に使う近傍サイズ(blockSize)を 3, 5, 7 に振る。b は未使用。"
    ),
    "cv_precorner": (
        "コーナー候補検出(preCornerDetect、OpenCV 実装)。1 次・2 次微分を組み合わ"
        "せた特殊な式でコーナーらしさを符号付きスコア化する —— 本来は "
        "``cv2.cornerSubPix`` によるサブピクセル精密化の前段候補検出として使う"
        "関数。\n\n"
        "HALCON の `corner_response`(Searching corners in images.)に相当(近似)。"
        "実装は ``|cv2.preCornerDetect(v, ksize=3)|`` を正規化したもの。a, b は"
        "未使用 —— ksize(Sobel 開口)は 3 に固定。"
    ),
    "cv_nlmeans": (
        "Non-local means ノイズ除去(OpenCV 実装、グレースケール版)。sk_nlm と同じ"
        "考え方(画像全体から似たパッチを探して平均する)を OpenCV の高速実装で行う。"
        "\n\n"
        "HALCON に直接対応するものは無い。実装は "
        "``cv2.fastNlMeansDenoising(_u8(v), h=3+20*a, templateWindowSize=7, "
        "searchWindowSize=21)`` を 255 で割ったもの —— a はフィルタ強度 h を 3〜23 "
        "に振る(大きいほど強く除去されディテールも失われる)。パッチ/探索窓は"
        "既定サイズに固定。b は未使用。"
    ),
    "cv_blackhat": (
        "ブラックハット変換(black-hat、OpenCV 実装)。「閉処理結果 − 元画像」を"
        "計算し、暗い背景の上にある、構造要素より小さい暗い特徴だけを抽出する"
        "(cv_tophat の暗版)。\n\n"
        "HALCON の `gray_bothat`(Perform a gray value bottom hat transformation on "
        "an image.)に相当。実装は ``cv2.morphologyEx(v, MORPH_BLACKHAT, se)`` を"
        "正規化したもの、se は楕円形でサイズ ``3+2*int(a*3)`` —— a は構造要素サイズ"
        "を 3〜9 に振る。b は未使用。"
    ),
    "cv_erode": (
        "グレー値モルフォロジー収縮(erosion、OpenCV 実装)。近傍の最小値へ置き換え"
        "る操作で、明るい領域を縮小・暗い領域を拡大する。\n\n"
        "HALCON の `gray_erosion`(Perform a gray value erosion on an image.)に"
        "相当。実装は ``cv2.erode(v, se)``、se は楕円形でサイズ "
        "``3+2*int(a*3)`` —— a は構造要素サイズを 3〜9 に振る。b は未使用。"
    ),
    "cv_dilate": (
        "グレー値モルフォロジー膨張(dilation、OpenCV 実装)。近傍の最大値へ置き"
        "換える操作で、明るい領域を拡大・暗い領域を縮小する(cv_erode の逆)。\n\n"
        "HALCON の `gray_dilation`(Perform a gray value dilation on an image.)に"
        "相当。実装は ``cv2.dilate(v, se)``、se は楕円形でサイズ "
        "``3+2*int(a*3)`` —— a は構造要素サイズを 3〜9 に振る。b は未使用。"
    ),
    "cv_sharpen": (
        "アンシャープ的な鮮鋭化フィルタ(3x3 カーネル畳み込み、OpenCV 実装)。"
        "中心 ``1+4a``、上下左右 ``-a`` のカーネル(a=0 では単位カーネル=無変化、"
        "a が大きいほど離散ラプラシアン的な高域強調が強くかかる)を畳み込み、"
        "エッジ付近のコントラストを持ち上げる。\n\n"
        "HALCON の `emphasize`(Enhance contrast of the image.)に相当(近似)。実装は "
        "``cv2.filter2D(v, kernel)`` を ``[0,1]`` へ clip したもの —— a はカーネルの"
        "強さ(鮮鋭化の度合い)を 0〜1 に振る。b は未使用。"
    ),
    "cv_trunc": (
        "階調の上側切り詰め(THRESH_TRUNC、OpenCV 実装)。指定値より明るい画素は"
        "すべてその値に丸め、それ以下の画素はそのまま —— ハイライトだけを潰す"
        "階調操作(暗部には触れない)。\n\n"
        "HALCON の `scale_image`(Scale the gray values of an image.)に相当"
        "(近似。線形スケーリングではなく片側クリップ)。実装は "
        "``cv2.threshold(v, thresh=a, maxval=1.0, THRESH_TRUNC)`` —— a は切り詰め"
        "レベルを 0〜1 に振る。b は未使用。"
    ),
    "cv_dist": (
        "距離変換(distance transform、OpenCV 実装、L2/ユークリッド近似)。前景領域"
        "の各画素について、最も近い背景画素までの距離を計算し、画像として返す —— "
        "領域の「太さ」や中心線抽出の下処理に使う。\n\n"
        "HALCON の `distance_transform`(Compute the distance transformation of a "
        "region.)に相当。実装は ``cv2.distanceTransform(_u8(binm(v)), DIST_L2, "
        "maskSize=3)`` を正規化したもの(cv2 は float32 で返すが、契約に合わせて "
        "float64 化 —— 2026-09-03 実測でベンチマーク済み)。maskSize=3 は 3x3 近傍で"
        "の近似計算(厳密なユークリッド距離ではなく高速近似)。a, b は未使用。"
    ),
    "cv_cc_count": (
        "連結成分数のカウント(1 スカラー特徴量、OpenCV 実装)。二値領域中の"
        "連結成分(前景の塊)の個数を数える —— 背景ラベル分の 1 を引いてから返す。"
        "\n\n"
        "HALCON の `connection`(Compute connected components of a region.)に相当"
        "(近似。分割結果ではなく個数のみを返す)。実装は "
        "``cv2.connectedComponents(_u8(binm(v)))[0] - 1``。a, b は未使用。"
        "connectivity は OpenCV の既定(8 連結)のまま。"
    ),
    "cv_hough_lines": (
        "確率的 Hough 変換による直線(線分)検出(1 スカラー特徴量、OpenCV 実装)。"
        "まず Canny でエッジ画像を作り、そこから直線状に並ぶエッジ画素の集合を投票"
        "方式で探して線分として検出する —— ここでは検出できた線分の本数だけを"
        "返す(0 本なら 0)。\n\n"
        "HALCON の `hough_lines`(Detect lines in edge images with the help of the "
        "Hough transform and returns it in HNF.)に相当(近似。線のパラメータでは"
        "なく本数のみ)。実装は ``cv2.HoughLinesP(Canny(_u8(v),50,150), 1, "
        "pi/180, threshold=int(20+40*a), minLineLength=int(10+20*b), "
        "maxLineGap=5)`` —— a は投票数のしきい値(直線と認める最低票数)を "
        "20〜60 に、b は最小線分長を 10〜30 に振る。Canny の内部しきい値(50, 150)"
        "と maxLineGap(5)は固定。"
    ),
    "cv_hough_circles": (
        "Hough 変換による円検出(1 スカラー特徴量、OpenCV 実装)。エッジの勾配"
        "情報を使う HOUGH_GRADIENT 法で円の中心・半径を投票検出する —— ここでは"
        "検出できた円の個数だけを返す(0 個なら 0)。\n\n"
        "HALCON の `hough_circles`(Detect centers of circles for a specific radius "
        "using the Hough transform.)に相当(近似。中心座標ではなく本数のみ)。"
        "実装は ``cv2.HoughCircles(_u8(v), HOUGH_GRADIENT, dp=1, "
        "minDist=10+int(a*20), param1=100, param2=20+int(b*20), minRadius=3, "
        "maxRadius=20)`` —— a は検出する円同士の最小中心間距離を 10〜30 に、b は"
        "中心検出の投票しきい値 param2(小さいほど誤検出が増える)を 20〜40 に振る。"
        "param1(内部の Canny 高しきい値)と半径範囲(3〜20)は固定。"
    ),
    "cv_good_features": (
        "Shi-Tomasi 法による高品質コーナー検出(1 スカラー特徴量、OpenCV 実装)。"
        "cv_min_eigen と同じ最小固有値基準でコーナーらしさを評価し、非極大抑制と"
        "最小距離フィルタで間引いた上位のコーナーを検出する —— ここでは検出できた"
        "個数だけを返す(0 個なら 0)。\n\n"
        "HALCON に直接対応するものは無い。実装は "
        "``cv2.goodFeaturesToTrack(v, maxCorners=int(10+40*a), "
        "qualityLevel=0.01+0.1*b, minDistance=5)`` —— a は検出上限数を 10〜50 に、"
        "b は品質しきい値(最強コーナーに対する相対比。大きいほど厳しく絞り込まれ"
        "検出数が減る)を 0.01〜0.11 に振る。最小距離は 5 画素に固定。"
    ),
}


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    ops_out = []

    # ---- scikit-image -------------------------------------------------------- #
    try:
        from skimage import (filters, morphology, restoration, exposure, feature,
                             measure, segmentation, transform)

        def _disk(a):
            return morphology.disk(1 + int(a * 3))

        def _u8s(v):
            return (np.clip(v, 0, 1) * 255).astype(np.uint8)

        sk = [
            ("sk_scharr", "edges", "edges_image", IMAGE, IMAGE, lambda v, a, b: norm(filters.scharr(v))),
            ("sk_farid", "edges", "edges_image", IMAGE, IMAGE, lambda v, a, b: norm(filters.farid(v))),
            # 2026-08-30 (KNOWN_ISSUES #2): a,b were completely ignored (fixed
            # sigmas=range(1,4)). Wired: a -> scale range (max sigma 1..5; a=0.5
            # reproduces the historical range(1,4) bit-exactly), b -> Frangi
            # blobness sensitivity beta (b=0.5 -> 0.5 = the skimage default, so
            # the (0.5, 0.5) default output is unchanged).
            ("sk_frangi", "texture", "lines_gauss", IMAGE, IMAGE,
             lambda v, a, b: norm(filters.frangi(v, sigmas=range(1, 2 + int(round(a * 4))),
                                                 beta=0.15 + 0.7 * b))),
            ("sk_meijering", "texture", "lines_gauss", IMAGE, IMAGE,
             lambda v, a, b: norm(filters.meijering(v, sigmas=range(1, 4)))),
            ("sk_hessian", "texture", "lines_gauss", IMAGE, IMAGE,
             lambda v, a, b: norm(filters.hessian(v, sigmas=range(1, 4)))),
            ("sk_dog", "edges", "diff_of_gauss", IMAGE, IMAGE,
             lambda v, a, b: norm(np.abs(filters.difference_of_gaussians(v, 1.0, 1.0 + 3.0 * a)))),
            ("sk_gabor", "texture", "gen_gabor", IMAGE, IMAGE,
             lambda v, a, b: norm(np.abs(filters.gabor(v, frequency=0.1 + 0.3 * a)[0]))),
            ("sk_butterworth", "frequency", "", IMAGE, IMAGE,
             lambda v, a, b: np.clip(filters.butterworth(v, cutoff_frequency_ratio=0.05 + 0.3 * a), 0, 1)),
            ("sk_tv", "smoothing", "", IMAGE, IMAGE,
             lambda v, a, b: restoration.denoise_tv_chambolle(v, weight=0.02 + 0.3 * a)),
            ("sk_wavelet", "smoothing", "", IMAGE, IMAGE,
             lambda v, a, b: np.clip(restoration.denoise_wavelet(v), 0, 1)),
            ("sk_adapthist", "gray", "", IMAGE, IMAGE,
             lambda v, a, b: exposure.equalize_adapthist(np.clip(v, 0, 1), clip_limit=0.01 + 0.05 * a)),
            ("sk_median_disk", "rank", "median_image", IMAGE, IMAGE,
             lambda v, a, b: filters.median(v, footprint=_disk(a))),
            ("sk_otsu", "segmentation", "binary_threshold", IMAGE, REGION,
             lambda v, a, b: (v > filters.threshold_otsu(v)).astype(np.float64)),
            ("sk_li", "segmentation", "binary_threshold", IMAGE, REGION,
             lambda v, a, b: (v > filters.threshold_li(v)).astype(np.float64)),
            ("sk_yen", "segmentation", "binary_threshold", IMAGE, REGION,
             lambda v, a, b: (v > filters.threshold_yen(v)).astype(np.float64)),
            ("sk_sauvola", "segmentation", "var_threshold", IMAGE, REGION,
             lambda v, a, b: (v > filters.threshold_sauvola(v, window_size=2 * int(a * 6) + 3)).astype(np.float64)),
            ("sk_niblack", "segmentation", "var_threshold", IMAGE, REGION,
             lambda v, a, b: (v > filters.threshold_niblack(v, window_size=2 * int(a * 6) + 3)).astype(np.float64)),
            ("sk_canny", "segmentation", "edges_image", IMAGE, REGION,
             lambda v, a, b: feature.canny(v, sigma=0.5 + 2.0 * a).astype(np.float64)),
            ("sk_skeleton", "region", "skeleton", REGION, REGION,
             lambda v, a, b: morphology.skeletonize(binm(v)).astype(np.float64)),
            ("sk_medial", "region", "skeleton", REGION, REGION,
             lambda v, a, b: morphology.medial_axis(binm(v), rng=0).astype(np.float64)),
            ("sk_convex", "region", "shape_trans", REGION, REGION,
             lambda v, a, b: morphology.convex_hull_image(binm(v)).astype(np.float64)),
            ("sk_thin", "region", "thinning", REGION, REGION,
             lambda v, a, b: morphology.thin(binm(v)).astype(np.float64)),
            ("sk_remove_holes", "region", "fill_up", REGION, REGION,
             lambda v, a, b: morphology.remove_small_holes(binm(v), area_threshold=int(8 + a * 60)).astype(np.float64)),
            ("sk_euler", "features", "euler_number", REGION, FEATURE,
             lambda v, a, b: np.float64(measure.euler_number(binm(v)))),
            ("sk_find_contours", "contour", "", IMAGE, CONTOUR,
             lambda v, a, b: {"shape": v.shape,
                              "cs": [c for c in measure.find_contours(v, 0.2 + 0.5 * a) if len(c) >= 3]}),
            # more image->image
            ("sk_lbp", "texture", "", IMAGE, IMAGE,
             lambda v, a, b: norm(feature.local_binary_pattern(v, 8, 1 + int(a * 3)))),
            ("sk_entropy", "texture", "entropy_image", IMAGE, IMAGE,
             lambda v, a, b: norm(filters.rank.entropy(_u8s(v), _disk(a)).astype(np.float64))),
            ("sk_enhance_contrast", "gray", "", IMAGE, IMAGE,
             lambda v, a, b: filters.rank.enhance_contrast(_u8s(v), _disk(a)).astype(np.float64) / 255),
            ("sk_autolevel", "gray", "scale_image_max", IMAGE, IMAGE,
             lambda v, a, b: filters.rank.autolevel(_u8s(v), _disk(a)).astype(np.float64) / 255),
            ("sk_shape_index", "texture", "", IMAGE, IMAGE,
             lambda v, a, b: signed01(np.nan_to_num(feature.shape_index(v, sigma=0.5 + 2.0 * a)))),
            ("sk_hessian_det", "edges", "", IMAGE, IMAGE,
             lambda v, a, b: signed01(feature.hessian_matrix_det(v, sigma=0.5 + 2.5 * a))),
            ("sk_corner_harris", "edges", "points_harris", IMAGE, IMAGE,
             lambda v, a, b: signed01(feature.corner_harris(v, sigma=0.5 + 2.0 * a))),
            # gain > 1 は出力を 1 より上へ押し上げる(実測 max=1.1380, a=0.5)。
            # `image` は [0,1] 契約なので出口で clip(2026-09-02)。`ops._apply` が
            # 段間で掛けている clip と同じなので **パイプライン結果はビット不変**、
            # 直接 `fullseye.apply` した時の白飛びだけが消える。
            ("sk_adjust_log", "gray", "log_image", IMAGE, IMAGE,
             lambda v, a, b: np.clip(exposure.adjust_log(np.clip(v, 0, 1),
                                                         gain=0.5 + 1.5 * a), 0, 1)),
            ("sk_rolling_ball", "smoothing", "", IMAGE, IMAGE,
             lambda v, a, b: np.clip(v - restoration.rolling_ball(v, radius=5 + int(a * 20)), 0, 1)),
            ("sk_nlm", "smoothing", "", IMAGE, IMAGE,
             lambda v, a, b: restoration.denoise_nl_means(v, patch_size=5, h=0.02 + 0.2 * a)),
            ("sk_tv_bregman", "smoothing", "", IMAGE, IMAGE,
             lambda v, a, b: np.clip(restoration.denoise_tv_bregman(v, weight=1.0 + 8.0 * a), 0, 1)),
            ("sk_swirl", "geometry", "polar_trans_image", IMAGE, IMAGE,
             lambda v, a, b: np.clip(transform.swirl(v, strength=1 + 4 * a, radius=30), 0, 1)),
            ("sk_area_opening", "morphology", "", IMAGE, IMAGE,
             lambda v, a, b: morphology.area_opening(v, area_threshold=int(16 + a * 100))),
            # image->region
            ("sk_felzenszwalb", "segmentation", "", IMAGE, REGION,
             lambda v, a, b: segmentation.find_boundaries(
                 segmentation.felzenszwalb(v, scale=20 + 200 * a, channel_axis=None)).astype(np.float64)),
            ("sk_slic", "segmentation", "", IMAGE, REGION,
             lambda v, a, b: segmentation.find_boundaries(
                 segmentation.slic(v, n_segments=int(10 + 80 * a), channel_axis=None)).astype(np.float64)),
            ("sk_chan_vese", "segmentation", "", IMAGE, REGION,
             lambda v, a, b: segmentation.chan_vese(v, mu=0.1 + 0.4 * a, max_num_iter=60).astype(np.float64)),
            ("sk_local_maxima", "segmentation", "local_max", IMAGE, REGION,
             lambda v, a, b: morphology.local_maxima(v).astype(np.float64)),
            ("sk_hysteresis", "segmentation", "hysteresis_threshold", IMAGE, REGION,
             lambda v, a, b: filters.apply_hysteresis_threshold(v, 0.2 + 0.3 * a, 0.5 + 0.3 * b).astype(np.float64)),
            # region->region / feature
            ("sk_clear_border", "region", "", REGION, REGION,
             lambda v, a, b: segmentation.clear_border(binm(v)).astype(np.float64)),
            ("sk_find_boundaries", "region", "boundary", REGION, REGION,
             lambda v, a, b: segmentation.find_boundaries(binm(v)).astype(np.float64)),
            ("sk_entropy_feat", "features", "entropy_gray", IMAGE, FEATURE,
             lambda v, a, b: np.float64(measure.shannon_entropy(v))),
            ("sk_blur_effect", "features", "", IMAGE, FEATURE,
             lambda v, a, b: np.float64(measure.blur_effect(v))),
        ]
        ops_out += [Op(n, c, h, i, o, _safe(f, o)) for (n, c, h, i, o, f) in sk]
    except ImportError:
        pass                                              # skimage absent: documented optional
    except Exception as _e:                               # noqa: BLE001 - installed but broken: never vanish silently
        _bs.record("backends.skimage", _e, None, source="import")
        pass

    # ---- OpenCV -------------------------------------------------------------- #
    try:
        import cv2

        def _se(a):
            k = 3 + 2 * int(a * 3)
            return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))

        cv = [
            ("cv_bilateral", "smoothing", "bilateral_filter", IMAGE, IMAGE,
             lambda v, a, b: cv2.bilateralFilter(v.astype(np.float32), 5, 0.05 + 0.4 * b, 1.0 + 3.0 * a).astype(np.float64)),
            ("cv_median", "rank", "median_image", IMAGE, IMAGE,
             lambda v, a, b: cv2.medianBlur(_u8(v), 3 + 2 * int(a * 3)).astype(np.float64) / 255),
            ("cv_box", "smoothing", "mean_image", IMAGE, IMAGE,
             lambda v, a, b: cv2.blur(v, (3 + 2 * int(a * 3),) * 2)),
            ("cv_gaussian", "smoothing", "gauss_filter", IMAGE, IMAGE,
             lambda v, a, b: cv2.GaussianBlur(v, (0, 0), 0.3 + 2.7 * a)),
            ("cv_scharr", "edges", "edges_image", IMAGE, IMAGE,
             lambda v, a, b: norm(np.abs(cv2.Scharr(v, cv2.CV_64F, 1, 0)) + np.abs(cv2.Scharr(v, cv2.CV_64F, 0, 1)))),
            ("cv_laplacian", "edges", "laplace", IMAGE, IMAGE,
             lambda v, a, b: norm(np.abs(cv2.Laplacian(v, cv2.CV_64F)))),
            ("cv_clahe", "gray", "", IMAGE, IMAGE,
             lambda v, a, b: cv2.createCLAHE(clipLimit=1.0 + 4.0 * a).apply(_u8(v)).astype(np.float64) / 255),
            ("cv_open", "morphology", "gray_opening", IMAGE, IMAGE,
             lambda v, a, b: cv2.morphologyEx(v, cv2.MORPH_OPEN, _se(a))),
            ("cv_close", "morphology", "gray_closing", IMAGE, IMAGE,
             lambda v, a, b: cv2.morphologyEx(v, cv2.MORPH_CLOSE, _se(a))),
            ("cv_tophat", "morphology", "gray_tophat", IMAGE, IMAGE,
             lambda v, a, b: norm(cv2.morphologyEx(v, cv2.MORPH_TOPHAT, _se(a)))),
            ("cv_gradient", "morphology", "gray_range_rect", IMAGE, IMAGE,
             lambda v, a, b: norm(cv2.morphologyEx(v, cv2.MORPH_GRADIENT, _se(a)))),
            ("cv_otsu", "segmentation", "binary_threshold", IMAGE, REGION,
             lambda v, a, b: (cv2.threshold(_u8(v), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1] > 0).astype(np.float64)),
            ("cv_adaptive_mean", "segmentation", "dyn_threshold", IMAGE, REGION,
             lambda v, a, b: (cv2.adaptiveThreshold(_u8(v), 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                                     cv2.THRESH_BINARY, 2 * int(a * 6) + 3, int(b * 10)) > 0).astype(np.float64)),
            ("cv_adaptive_gauss", "segmentation", "local_threshold", IMAGE, REGION,
             lambda v, a, b: (cv2.adaptiveThreshold(_u8(v), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                    cv2.THRESH_BINARY, 2 * int(a * 6) + 3, int(b * 10)) > 0).astype(np.float64)),
            ("cv_canny", "segmentation", "edges_image", IMAGE, REGION,
             lambda v, a, b: (cv2.Canny(_u8(v), int(50 + 100 * a), int(100 + 150 * b)) > 0).astype(np.float64)),
            # more image->image
            ("cv_corner_harris", "edges", "points_harris", IMAGE, IMAGE,
             lambda v, a, b: signed01(cv2.cornerHarris(v.astype(np.float32), 2, 3, 0.04))),
            ("cv_min_eigen", "edges", "points_harris", IMAGE, IMAGE,
             lambda v, a, b: norm(cv2.cornerMinEigenVal(v.astype(np.float32), 3 + 2 * int(a * 2)))),
            ("cv_precorner", "edges", "corner_response", IMAGE, IMAGE,
             lambda v, a, b: norm(np.abs(cv2.preCornerDetect(v.astype(np.float32), 3)))),
            ("cv_nlmeans", "smoothing", "", IMAGE, IMAGE,
             lambda v, a, b: cv2.fastNlMeansDenoising(_u8(v), None, 3 + 20 * a, 7, 21).astype(np.float64) / 255),
            ("cv_blackhat", "morphology", "gray_bothat", IMAGE, IMAGE,
             lambda v, a, b: norm(cv2.morphologyEx(v, cv2.MORPH_BLACKHAT, _se(a)))),
            ("cv_erode", "morphology", "gray_erosion", IMAGE, IMAGE,
             lambda v, a, b: cv2.erode(v, _se(a))),
            ("cv_dilate", "morphology", "gray_dilation", IMAGE, IMAGE,
             lambda v, a, b: cv2.dilate(v, _se(a))),
            ("cv_sharpen", "smoothing", "emphasize", IMAGE, IMAGE,
             lambda v, a, b: np.clip(cv2.filter2D(
                 v, -1, np.array([[0, -a, 0], [-a, 1 + 4 * a, -a], [0, -a, 0]])), 0, 1)),
            ("cv_trunc", "gray", "scale_image", IMAGE, IMAGE,
             lambda v, a, b: cv2.threshold(v, a, 1.0, cv2.THRESH_TRUNC)[1]),
            # region->image / feature
            ("cv_dist", "region", "distance_transform", REGION, IMAGE,
             lambda v, a, b: norm(cv2.distanceTransform(_u8(binm(v).astype(np.float64)), cv2.DIST_L2, 3).astype(np.float64))),  # cv2 returns float32; contract is float64 (bench 2026-09-03)
            ("cv_cc_count", "features", "connection", REGION, FEATURE,
             lambda v, a, b: np.float64(cv2.connectedComponents(_u8(binm(v).astype(np.float64)))[0] - 1)),
            # image->feature (Hough / features)
            ("cv_hough_lines", "features", "hough_lines", IMAGE, FEATURE,
             lambda v, a, b: np.float64(0 if (ll := cv2.HoughLinesP(
                 cv2.Canny(_u8(v), 50, 150), 1, np.pi / 180, int(20 + 40 * a),
                 minLineLength=int(10 + 20 * b), maxLineGap=5)) is None else len(ll))),
            ("cv_hough_circles", "features", "hough_circles", IMAGE, FEATURE,
             lambda v, a, b: np.float64(0 if (cc := cv2.HoughCircles(
                 _u8(v), cv2.HOUGH_GRADIENT, 1, 10 + int(a * 20), param1=100, param2=20 + int(b * 20),
                 minRadius=3, maxRadius=20)) is None else cc.shape[1])),
            ("cv_good_features", "features", "", IMAGE, FEATURE,
             lambda v, a, b: np.float64(0 if (pp := cv2.goodFeaturesToTrack(
                 v.astype(np.float32), int(10 + 40 * a), 0.01 + 0.1 * b, 5)) is None else len(pp))),
        ]
        ops_out += [Op(n, c, h, i, o, _safe(f, o)) for (n, c, h, i, o, f) in cv]
    except ImportError:
        pass                                              # cv2 absent: documented optional
    except Exception as _e:                               # noqa: BLE001
        _bs.record("backends.cv2", _e, None, source="import")
        pass

    return ops_out
