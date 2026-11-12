# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""金属の表面の欠陥(傷・打痕・汚れ・正常)を、画素の分類 → 領域の特徴 → 学習した分類器で仕分ける。

Rendered (synthetic) metal-surface patches with defects (scratch, dent, stain, none) sorted by Fullseye's trained
classifiers — pixel classifiers paint the anomaly and the stain, region features feed GMM / MLP / SVM / k-NN,
and the GMM says "I don't know" to a defect it never saw (corrosion pits). Each headline number is set next
to a training-free baseline and to the same run with the lighting changed.

    py -3.11 examples/poc_surface_defect_classifiers.py

``CI`` では分岐しない(縮小モードは無い。常に同じ全量を走らせる)。種 5 本の全量 + 軽い版 15 種 + 確認実験で約 1.5 分
(以前の 17 秒から増えたのは、種を 20 本に増やした再現率の数え直しと、y 勾配・照明を変えた確認実験のため)。
``FULLSEYE_FIGURES=off`` で図の書き出しだけ止められる。

【この PoC が答える問題】
分類の op 14 本(``train_class_gmm`` / ``classify_class_gmm`` / ``evaluate_class_gmm`` /
``train_class_mlp`` / ``classify_class_mlp`` / ``train_class_svm`` / ``classify_class_svm`` /
``train_class_knn`` / ``classify_class_knn`` / ``learn_ndim_norm`` / ``class_ndim_norm`` /
``class_2dim_sup`` / ``class_2dim_unsup`` / ``classify_image_class_lut``)は、どの PoC からも
使われていなかった。研削した金属の小片(96x96 px)を物理的に描き、どの分類器がどこまで当たるか、
知らない欠陥を「分からない」と言えるかを、描画に仕込んだ真値で数える。

【撮像(真値はここだけが持つ)】
* 面の高さ: 研削の筋(白色雑音を x に σ 6 px・y に σ 0.6 px でぼかした異方的な凹凸)。
* 傷 = 細い V 溝(幅 0.8〜1.8 px、長さ 25〜70 px、向きは任意)、打痕 = 滑らかな窪み(σ 3〜7 px)、
  未知の欠陥 = 腐食の孔の群れ(12〜30 個、σ 0.7〜1.3 px)。どれも**高さ**を変え、色は変えない。
* 汚れ = **反射率**を茶色に落とす(油・錆。形は滑らかな不定形)。高さは変えない。
* 陰影: 高さの勾配から法線を出し、斜めの照明で Lambert + Blinn-Phong の鏡面(金属の灰色)。
  ぼけ σ 0.6 px、雑音 σ 0.01、8 bit に量子化。
* 欠陥の強さ(深さ・汚れの濃さ)は小片ごとに 0〜1 の「重さ」で振る —— 薄い欠陥ほど正常と紛れる。
* 1 つの種で 4 クラス x 150 枚 + 孔 50 枚。種 5 本(11〜15)で描き直し、分割もやり直す。

【推定(画像しか見ない)】
1. 画素: 学習側の正常な小片の画素で ``learn_ndim_norm`` が (輝度の高域・色度・筋を横切る勾配 |dY/dx|)
   の正規分布を学び、``class_ndim_norm`` が Mahalanobis 距離で「正常らしくない」画素を塗る。
   閾値は学習側の正常画素の 99.9 % 点(評価側を見ない)。
2. 汚れの画素: 色度を [0, 1] に写した画像に ``classify_image_class_lut``(256 段、切れ目は**学習側の汚れの小片と
   その真のマスク**を使った教師ありの、誤りが最小になる段。正常な画素から学ぶのではない)/ ``class_2dim_sup``(学習側の汚れを 2 px 削った芯を参照領域にした 2 チャネルの箱。
   この op は参照領域と同じ画像を塗るので、学習側の小片を横に並べた右に評価の小片をつなぐ)/
   ``class_2dim_unsup``(k-means、k = 2、教師なし)で塗り、真の汚れの画素と IoU で比べる。**基準線**は学習なしの
   大津の 2 値化を 1 枚ごとに色度 (R−B)/ΣRGB にかけるだけのもの(汚れの有無は言えず、正常な小片も割る)。
3. 領域の特徴(7 個、画像と画素モデルだけから): 異常画素の面積・連結成分の数、異常度の上位 40 画素の
   広がりと伸び、色度の差、輝度の差と散らばり。
4. 分類器: GMM(成分 1・2)、MLP、線形 SVM、k-NN(k = 5)。学習 50 % / 検証 20 % / 評価 30 %(層化)。
   GMM の「分からない」の閾値は**検証側**の対数密度の 5 % 点。**基準線**は特徴 1 個(異常画素の連結成分の数)の
   外れ値判定(検証側の両側 2.5 % 点の外を拒否)。
5. 確認実験(GMM(1) と画素の特徴だけ): |dY/dy| を足す / |dY/dx| の代わりにする / 照明の方位を 90・180・270° 回す。
   傷の再現率と孔の拒否率を数え直す。傷の再現率は種を 20 本(11〜30)に増やして合算し、Wilson の 95 % 区間で言う。

【門(数値)】
1. 閉形式: ``learn_ndim_norm`` の平均・共分散が np.mean / np.cov + 1e-6 I と一致。``train_class_gmm``
   (成分 1)の平均・共分散がクラスの平均・共分散(bias)+ 1e-6 I と一致し、scipy の多変量正規で書いた
   2 次判別と評価側の予測が 99.5 % 以上一致(実測 100 %)。k-NN は総当たりの距離 + 多数決の自前実装と
   99 % 以上一致(実測 100 %)。
2. 第 2 実装(scikit-learn があれば): GaussianMixture(クラスごと)・MLPClassifier・LinearSVC(hinge)・
   KNeighborsClassifier を同じ特徴・同じ分割で学習し、種ごとの正解率の差が tol = 3·sqrt(2p(1−p)/n) + 1/n
   (同じ強さの分類器 2 つが n 個の評価で見せる差の 3σ + 1 個ぶん)以内、クラスごとの再現率の差も同じ形の
   tol 以内。実測: |差|/tol は最大 0.41(MLP)、予測の一致は GMM(1) 1.000・k-NN 0.996・SVM 0.989・
   GMM(2) 0.929・MLP 0.903。scikit-learn が無い環境では、多項ロジスティック回帰(scipy の L-BFGS)を
   線形の判別の第 2 実装にして SVM・MLP を、閉形式の 2 次判別で GMM(2) を同じ門で比べる。
3. 分割を守る: しきい値(画素モデル・LUT・拒否)はどれも学習・検証側だけで決める。種 5 本の正解率の
   平均 ± 標準偏差は GMM(1) 0.884 ± 0.017・GMM(2) 0.881 ± 0.017・MLP 0.884 ± 0.015・SVM 0.871 ± 0.022・
   k-NN 0.886 ± 0.015(評価 180 枚/種)。標準偏差が 0 でないこと(同じ結果の写しではない)を門にする。
4. 「分からない」: 腐食の孔(学習に無い)を GMM の対数密度で拒否した率 0.948(門 0.9 以上)、既知の
   小片を誤って拒否した率 0.060(門 q + 3·sqrt(q(1−q)/n) = 0.072、q = 0.05 は検証側で決めた率)。
   scikit-learn の GaussianMixture(1) に同じ規則をかけても 0.948 / 0.060。**基準線(特徴 1 個の外れ値判定)は
   孔 0.976・既知の誤拒否 0.021 で GMM と同じかそれ以上**(門: 孔の拒否が GMM 以上、誤拒否が同じ上限の内)。
   種 20 本の合算(孔 1000 枚)は GMM 0.939 [0.922–0.952]、基準線 0.982 [0.972–0.989]。
5. 出来すぎていないか: ラベルを入れ替えて学習すると正解率 0.238(門 1/4 + 3σ = 0.293)。特徴 1 個だけの
   正解率は最大 0.726(面積)で全体の 0.884 に届かない。誤りは薄い欠陥に集まる —— 5 つの分類器すべてで
   重さの下 1/3 の正解率が上 1/3 より低い(GMM(1) 0.807 / 0.937)。再現率 100 % は汚れだけで、内訳は
   色度の差: 汚れの最小 0.055 > 他の最大 0.009。汚れは反射率の色を変える唯一の欠陥で、特徴は画像から
   測っているので、真値の漏れではない(門: 100 % は汚れだけ、かつ色度の差に隙間がある)。
6. 汚れの画素: **基準線(学習なしの大津)の IoU 0.939 ± 0.015 が LUT の 0.915 ± 0.009 より上**(門: 5 種すべてで基準線が
   上、平均の差は 0〜0.06 —— LUT は学習なしの基準線を超えない)。違いは「汚れ無し」を言えるか: 正常な小片での誤検出は
   LUT 0.0000(門 1 %)、大津は画素の 0.51(常に割る)。class_2dim_sup 0.729 ± 0.066(LUT より 0.1 以上下)、誤検出 2.5 %。
   class_2dim_unsup は生のチャネルで 0.333、チャネルを標準化すると 0.535(門: 標準化で 0.1 以上良くなる)。
7. 筋に沿う傷: 種 20 本の合算で、筋から 15° 以内の再現率 0.324(145 本中 47、Wilson 95 % 0.253–0.404)、45° より立った傷は
   0.944(461 本中 435、0.919–0.961)。門は区間で: 前者の上端 < 0.5、後者の下端 > 0.85。見落とし 0.676(0.596–0.747)。
8. 原因の確認実験: |dY/dy| を足しても 0.300、|dY/dx| の代わりにすると 0.225、照明の方位を 90・180・270° 回すと
   0.050・0.425・0.150(各 n = 40、基準 0.275)。どれも 0.5 未満(門)—— 筋沿いの傷が見えるようになる条件は見つかっていない。
9. 照明を変えた孔の拒否: GMM 0.948(基準の照明)・0.800・0.964・0.792、基準線 0.976・0.876・0.980・0.876。GMM の拒否率は
   照明で 0.1 以上動く(門)—— 見出しの 0.948 は 1 条件に固有の値。

【★ この PoC が出した所見】
(a) **研削の筋に沿う傷は見落とす(原因は未特定)**: 種 20 本の合算で、筋から 15° 以内の傷の再現率は 0.324(145 本中 47、
    Wilson 95 % 0.253–0.404)、つまり約 3 本に 2 本を見落とす(0.676、0.596–0.747)。45° より立った傷は 0.944(461 本中 435)。
    見落とした傷の大半は「正常」と呼ばれる(種 5 本で 56 本中 41 本)。**原因は特定できていない**: 画素の特徴の
    |dY/dx| が筋に沿う傷を消すのではないかと疑って |dY/dy| を足しても 0.275 → 0.300、|dY/dx| の代わりにすると 0.225
    (立った傷は 0.949 → 0.542)、照明の方位を回しても 0.050・0.425・0.150 で、どれでも直らなかった。
    原因の候補(筋に沿う傷の陰影の小ささ、領域の特徴 7 個、画素の 99.9 % 閾値)は切り分けていない。
(b) ``class_2dim_sup`` は参照領域の**最小・最大**の箱なので、参照の中のいちばん薄い画素が箱の端を決める。
    学習側で誤りが最小の 1 本の切れ目を選ぶ LUT(0.915)に IoU で負け、誤検出も 2.5 % 出る。
    **ただし LUT も学習なしの基準線(1 枚ごとの大津、色度、IoU 0.939)には届かない**: この汚れは色が変わるだけの易しい
    課題で、1 つの閾値で足りる。LUT が勝つのは「汚れが無い小片で何も塗らない」(誤検出 0.0000 対 大津 0.51)ことだけ。
(c) ``class_2dim_unsup`` は特徴を標準化しない k-means なので、分散の大きい輝度(研削の筋)で 2 つに割れる。
    標準化すると良くなるが、それでも筋の明暗で割れる小片が残る(0.535)。教師なしの 2 分割は
    「汚れが無い」とも言えない(正常な小片もかならず 2 つに割る。大津も同じ)。
(d) GMM の対数密度で拒否できなかった孔(250 枚中 13 枚)は傷(6)か打痕(7)と呼ばれる。既知の小片の
    誤った拒否は傷 21・汚れ 16・正常 11・打痕 6 枚(5 種の合計、各 225 枚)。
    **特徴 1 個(異常画素の連結成分の数)の外れ値判定のほうが孔を多く拒否し(0.976 対 0.948、20 種の合算で 0.982 対 0.939)、
    既知の誤拒否も少ない(0.021 対 0.060)**。孔は連結成分が多いという 1 つの違いで足りるので、GMM の対数密度という
    道具立てが効いている証拠にはならない。
    拒否率は照明にも依る: 照明の方位を 90・180・270° 回すと GMM は 0.800・0.964・0.792(基準線 0.876・0.980・0.876)。
    見出しの 0.948 は基準の照明 1 条件の値で、方位を変えると 0.79 まで下がった。
(e) 分類器どうしの差は小さい(正解率 0.871〜0.886、種のばらつき ±0.02 と同じ大きさ)。この特徴では
    分類器を選んでも差はほとんど出ない。(a) の見落としは、確認実験で試した変更(y 勾配・照明の向き)では直らなかった。

    EXTEND: 実画像に差し替えるには ``render_patch`` の返りを撮った小片(RGB、[0, 1])にし、
    真値の代わりに人が付けたラベルを ``labels`` に入れる。門 1・2 はそのまま回り、門 5 の重さ別の内訳は
    人が付けた「軽微/重大」で代える。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")        # scikit-learn(任意)が物理コア数を数えに行く警告を止める

L = fs.ledger
SIZE = 96
CLASSES = ("normal", "scratch", "dent", "stain")
UNKNOWN = "pits"
N_PER_CLASS = 150
N_UNKNOWN = 50
SEEDS = (11, 12, 13, 14, 15)
EXTRA_SEEDS = tuple(range(16, 31))          # 軽い版(GMM(1)・拒否・傷の向きだけ)で足す種。合算して 20 種
LIGHT_VARIANTS = (("azimuth +90 deg", (-0.30, 0.55, 0.78)), ("azimuth +180 deg", (-0.55, -0.30, 0.78)),
                  ("azimuth +270 deg", (0.30, -0.55, 0.78)))     # 基準の LIGHT を方位だけ回した 3 通り
SPLIT = (0.5, 0.2, 0.3)                     # 学習 / 検証 / 評価
METAL = np.array([0.78, 0.79, 0.81])
STAIN_TINT = np.array([0.80, 0.58, 0.36])   # 汚れの反射率の色(茶色)
LIGHT = np.array([0.55, 0.30, 0.78])
BLUR, NOISE = 0.6, 0.01
TOP_N = 40
REJECT_Q = 0.05                             # 拒否の閾値 = 検証側の対数密度の 5 % 点
CORE_ERODE = 2                              # class_2dim_sup の参照領域 = 学習側の汚れを 2 px 削った芯


# --- 撮像 / rendering --------------------------------------------------------------------------
def _grid():
    y, x = np.mgrid[0:SIZE, 0:SIZE].astype(float)
    return y, x


def render_patch(kind, weight, rng, light=None):
    """1 枚の小片を描く。返り: RGB 画像 (H, W, 3) in [0, 1]、真の汚れの画素 (H, W) bool、
    傷の向きと研削の筋(x 軸)のなす角 [deg](傷でなければ nan)。

    ``weight`` (0〜1) は欠陥の強さ。高さの欠陥(傷・打痕・孔)は陰影だけを、汚れは反射率だけを変える。
    """
    y, x = _grid()
    base = ndi.gaussian_filter(rng.normal(size=(SIZE, SIZE)), (0.6, 6.0), mode="wrap")
    h = 0.5 * base / base.std()                              # 研削の筋 [任意単位、勾配で効く]
    cy, cx = rng.uniform(30, 66, size=2)
    stain = np.zeros((SIZE, SIZE))
    lay = np.nan
    if kind == "scratch":
        th = rng.uniform(0, np.pi)
        lay = float(np.degrees(min(th, np.pi - th)))
        ln, w = rng.uniform(25, 70), rng.uniform(0.8, 1.8)
        u = (x - cx) * np.cos(th) + (y - cy) * np.sin(th)
        v = -(x - cx) * np.sin(th) + (y - cy) * np.cos(th)
        taper = 1.0 / (1.0 + np.exp((np.abs(u) - ln / 2) / 1.5))
        h -= (0.6 + 2.4 * weight) * np.exp(-v ** 2 / (2 * w ** 2)) * taper
    elif kind == "dent":
        s = rng.uniform(3.0, 7.0)
        h -= (1.5 + 9.0 * weight) * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * s ** 2))
    elif kind == UNKNOWN:
        for _ in range(int(rng.integers(12, 31))):
            r, a = 22 * np.sqrt(rng.uniform()), rng.uniform(0, 2 * np.pi)
            py, px, s = cy + r * np.sin(a), cx + r * np.cos(a), rng.uniform(0.7, 1.3)
            h -= (1.0 + 2.0 * weight) * np.exp(-((x - px) ** 2 + (y - py) ** 2) / (2 * s ** 2))
    elif kind == "stain":
        blob = ndi.gaussian_filter(rng.normal(size=(SIZE, SIZE)), 5.0, mode="wrap")
        blob /= blob.std()
        ax, ay = rng.uniform(8, 18, size=2)
        ell = ((x - cx) / ax) ** 2 + ((y - cy) / ay) ** 2
        field = 1.6 * (1.0 - ell) + 0.6 * blob
        stain = 1.0 / (1.0 + np.exp(-np.clip(field / 0.15, -50, 50)))
    elif kind != "normal":
        raise ValueError("unknown kind %r" % kind)
    gy, gx = np.gradient(h)
    n = np.stack([-gx, -gy, np.ones_like(h)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    lv = (LIGHT if light is None else np.asarray(light, float))
    lv = lv / np.linalg.norm(lv)
    half = (lv + np.array([0.0, 0.0, 1.0]))
    half /= np.linalg.norm(half)
    diff = np.clip(n @ lv, 0.0, None)
    spec = np.clip(n @ half, 0.0, None) ** 20
    alpha = (0.3 + 0.6 * weight) * stain                     # 汚れの濃さ
    albedo = METAL[None, None, :] * (1.0 - alpha[..., None] * (1.0 - STAIN_TINT[None, None, :]))
    img = albedo * (0.25 + 0.6 * diff[..., None]) + 0.25 * (1.0 - alpha[..., None]) * spec[..., None]
    img = ndi.gaussian_filter(img, (BLUR, BLUR, 0))
    img = img + rng.normal(0.0, NOISE, img.shape)
    img = np.round(np.clip(img, 0.0, 1.0) * 255.0) / 255.0
    return img, stain > 0.5, lay


def make_dataset(seed, light=None):
    rng = np.random.default_rng(seed)
    imgs, masks, labels, weights, lays = [], [], [], [], []
    for kind in CLASSES + (UNKNOWN,):
        n = N_UNKNOWN if kind == UNKNOWN else N_PER_CLASS
        for _ in range(n):
            w = float(rng.uniform())
            im, m, lay = render_patch(kind, w, rng, light)
            lays.append(lay)
            imgs.append(im)
            masks.append(m)
            labels.append(kind)
            weights.append(w)
    return np.array(imgs), np.array(masks), np.array(labels), np.array(weights), np.array(lays)


def split(labels, seed):
    """既知のクラスを層化で 学習 / 検証 / 評価 に分ける。未知の孔は全部評価へ。"""
    rng = np.random.default_rng(seed + 1000)
    tr, va, te = [], [], []
    for c in CLASSES:
        idx = rng.permutation(np.flatnonzero(labels == c))
        a, b = int(SPLIT[0] * len(idx)), int((SPLIT[0] + SPLIT[1]) * len(idx))
        tr += list(idx[:a])
        va += list(idx[a:b])
        te += list(idx[b:])
    unk = list(np.flatnonzero(labels == UNKNOWN))
    return np.array(tr), np.array(va), np.array(te), np.array(unk)


# --- 画素の特徴 / pixel features -----------------------------------------------------------------
def luminance(img):
    return img @ np.array([0.299, 0.587, 0.114])


def chroma(img):
    return (img[..., 0] - img[..., 2]) / (img.sum(-1) + 1e-6)


def chroma01(img):
    """色度を [0, 1] に写す(LUT の入口)。金属 ≈ 0.43、濃い汚れ ≈ 0.75。"""
    return np.clip((chroma(img) + 0.15) / 0.5, 0.0, 1.0)


def pixel_features(img, gy=None):
    """画素の特徴 (輝度の高域・色度・|dY/dx|)。``gy="add"`` で |dY/dy| を 4 個目に足し、``gy="replace"`` で
    |dY/dx| を |dY/dy| に置き換える(所見 (a) の確認実験用。既定は足さない)。"""
    Y = luminance(img)
    hp = Y - ndi.gaussian_filter(Y, 4.0)
    sm = ndi.gaussian_filter(Y, 1.0)
    gx = np.abs(np.gradient(sm, axis=1))                         # 筋(x に沿う)を横切る向きの勾配
    if gy is None:
        cols = [hp, chroma(img), gx]
    elif gy == "add":
        cols = [hp, chroma(img), gx, np.abs(np.gradient(sm, axis=0))]
    elif gy == "replace":
        cols = [hp, chroma(img), np.abs(np.gradient(sm, axis=0))]
    else:
        raise ValueError("gy must be None, 'add' or 'replace'")
    return np.stack(cols, axis=-1)


def mahalanobis(F, model):
    d = F.reshape(-1, F.shape[-1]) - model["mean"]
    return np.sqrt(np.einsum("ij,jk,ik->i", d, model["inv"], d)).reshape(F.shape[:2])


# --- 領域の特徴 / region features ------------------------------------------------------------------
FEATURE_NAMES = ("log area", "log components", "top-N spread", "top-N elongation",
                 "chroma excess", "luminance excess", "luminance spread")


def region_features(img, pix_model, thresh, gy=None):
    """画像と画素モデルだけから 7 個の特徴を出す(真値は見ない)。"""
    F = pixel_features(img, gy)
    inside = L.class_ndim_norm(F, pix_model, thresh=thresh)
    anom = ~inside
    lab, n = ndi.label(anom)
    sizes = ndi.sum(anom, lab, np.arange(1, n + 1)) if n else np.zeros(0)
    keep = sizes >= 3
    area = float(sizes[keep].sum())
    md = mahalanobis(F, pix_model)
    top = np.argsort(md.ravel())[-TOP_N:]
    ty, tx = np.unravel_index(top, md.shape)
    ev = np.sort(np.linalg.eigvalsh(np.cov(np.stack([ty, tx]).astype(float))))
    ev = np.clip(ev, 1e-3, None)
    c = F[..., 1].ravel()
    hp = F[..., 0].ravel()
    return np.array([np.log1p(area), np.log1p(float(keep.sum())), np.sqrt(ev.sum()),
                     0.5 * np.log(ev[1] / ev[0]), c[top].mean() - np.median(c),
                     hp[top].mean(), hp[top].std()])


# --- 独立な参照 / independent references -----------------------------------------------------------
def qda_reference(Xtr, ytr, Xte, reg=1e-6):
    """2 次判別を閉形式で: クラスごとの平均・共分散(bias)+ 事前確率、scipy の多変量正規の対数密度。"""
    from scipy.stats import multivariate_normal
    classes = np.unique(ytr)
    scores = []
    for c in classes:
        R = Xtr[ytr == c]
        cov = np.cov(R.T, bias=True) + reg * np.eye(R.shape[1])
        scores.append(np.log(len(R) / len(Xtr)) + multivariate_normal(R.mean(0), cov).logpdf(Xte))
    return classes[np.argmax(np.stack(scores, 1), 1)]


def knn_reference(Xtr, ytr, Xte, k=5):
    """総当たりの距離 + 多数決(同票は距離の和が小さい側)。標準化は学習側の平均・標準偏差。"""
    mu, sd = Xtr.mean(0), Xtr.std(0)
    A, B = (Xtr - mu) / sd, (Xte - mu) / sd
    D = np.sqrt(((B[:, None, :] - A[None, :, :]) ** 2).sum(-1))
    out = []
    for row in D:
        nn = np.argsort(row, kind="stable")[:k]
        vals, cnt = np.unique(ytr[nn], return_counts=True)
        top = vals[cnt == cnt.max()]
        out.append(top[0] if top.size == 1 else top[np.argmin([row[nn][ytr[nn] == v].sum() for v in top])])
    return np.array(out)


def logistic_reference(Xtr, ytr, Xte):
    """多項ロジスティック回帰(L2 1e-3)を scipy の L-BFGS で解く —— 線形の判別の第 2 実装。"""
    from scipy.optimize import minimize
    mu, sd = Xtr.mean(0), Xtr.std(0)
    A, B = (Xtr - mu) / sd, (Xte - mu) / sd
    classes = np.unique(ytr)
    Y = (ytr[:, None] == classes[None, :]).astype(float)
    D, K = A.shape[1], classes.size

    def f(w):
        W, b = w[:D * K].reshape(D, K), w[D * K:]
        o = A @ W + b
        o -= o.max(1, keepdims=True)
        lp = o - np.log(np.exp(o).sum(1, keepdims=True))
        p = np.exp(lp)
        g = (p - Y) / len(A)
        return (-(Y * lp).sum() / len(A) + 5e-4 * (W ** 2).sum(),
                np.concatenate([(A.T @ g + 1e-3 * W).ravel(), g.sum(0)]))

    w = minimize(f, np.zeros(D * K + K), jac=True, method="L-BFGS-B").x
    return classes[np.argmax(B @ w[:D * K].reshape(D, K) + w[D * K:], 1)]


def sklearn_references(Xtr, ytr, Xte, Xva, Xunk):
    """scikit-learn の第 2 実装(あれば)。返り: 名前 -> 評価側の予測、と GMM の拒否の率。"""
    try:
        from sklearn.mixture import GaussianMixture
        from sklearn.neighbors import KNeighborsClassifier
        from sklearn.neural_network import MLPClassifier
        from sklearn.preprocessing import StandardScaler
        from sklearn.svm import LinearSVC
    except ImportError:                                       # 任意の依存。無ければ閉形式の参照だけで門を回す
        return None
    classes = np.unique(ytr)
    out = {}
    for k in (1, 2):
        gms = [GaussianMixture(k, covariance_type="full", reg_covar=1e-6, random_state=0, n_init=3)
               .fit(Xtr[ytr == c]) for c in classes]
        pri = np.log([np.mean(ytr == c) for c in classes])

        def logp(X, gms=gms, pri=pri):
            return np.stack([g.score_samples(X) for g in gms], 1) + pri
        out["gmm%d" % k] = classes[np.argmax(logp(Xte), 1)]
        if k == 1:
            from scipy.special import logsumexp
            thr = np.quantile(logsumexp(logp(Xva), 1), REJECT_Q)
            out["reject_known"] = float(np.mean(logsumexp(logp(Xte), 1) < thr))
            out["reject_unknown"] = float(np.mean(logsumexp(logp(Xunk), 1) < thr))
    sc = StandardScaler().fit(Xtr)
    A, B = sc.transform(Xtr), sc.transform(Xte)
    out["mlp"] = MLPClassifier((8,), activation="tanh", solver="lbfgs", alpha=1e-4, max_iter=3000,
                               random_state=0).fit(A, ytr).predict(B)
    out["svm"] = LinearSVC(C=1.0, loss="hinge", intercept_scaling=10.0, max_iter=200000,
                           dual=True).fit(A, ytr).predict(B)
    out["knn"] = KNeighborsClassifier(5).fit(A, ytr).predict(B)
    return out


# --- 汚れの画素 / stain pixels ---------------------------------------------------------------------
def iou(a, b):
    u = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum() / u) if u else 1.0


def stain_lut(imgs, masks):
    """色度 [0, 1] の 256 段の LUT。閾値は学習側の画素で誤りが最小になる段(評価側を見ない)。"""
    u = np.concatenate([chroma01(im).ravel() for im in imgs])
    t = np.concatenate([m.ravel() for m in masks])
    idx = np.clip(np.round(u * 255).astype(int), 0, 255)
    pos = np.bincount(idx[t], minlength=256)
    neg = np.bincount(idx[~t], minlength=256)
    err = np.cumsum(pos) + (neg.sum() - np.cumsum(neg))      # 段 i 以下を 0、超を 1 にしたときの誤り
    cut = int(np.argmin(err))
    return (np.arange(256) > cut).astype(np.int64), cut / 255.0


# --- 学習なしの基準線 / training-free baselines ---------------------------------------------------------
def otsu_threshold(v, bins=256):
    """大津の閾値(クラス間分散が最大になる段の中心)。学習なし・1 枚ごと。"""
    hist, edges = np.histogram(v, bins=bins)
    mid = 0.5 * (edges[1:] + edges[:-1])
    p = hist / hist.sum()
    w0 = np.cumsum(p)
    mu = np.cumsum(p * mid)
    sb = (mu[-1] * w0 - mu) ** 2 / (w0 * (1.0 - w0) + 1e-12)
    return float(mid[int(np.argmax(sb))])


def otsu_stain(img):
    """基準線: 色度 (R-B)/ΣRGB の画像を 1 枚ごとに大津で 2 値化(学習なし)。汚れの有無は言えない(常に割る)。"""
    u = chroma(img)
    return u > otsu_threshold(u)


def wilson(k, n, z=1.96):
    """二項の割合 k/n の Wilson 95 % 区間 (下端, 上端)。"""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1.0 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1.0 - p) / n + z * z / (4 * n * n)) / d
    return float(c - h), float(c + h)


def count_outlier_reject(Xva, X, col=1):
    """基準線: 特徴 1 個(異常画素の連結成分の数 = ``col``)の外れ値判定。検証側の両側 2.5 % 点の外を拒否。"""
    lo, hi = np.quantile(Xva[:, col], [REJECT_Q / 2, 1.0 - REJECT_Q / 2])
    return (X[:, col] < lo) | (X[:, col] > hi)


# --- 1 回 / one seed ----------------------------------------------------------------------------
def run_seed(seed, light=None, gy=None, full=True):
    """1 つの種で描き直して全部を走らせる。``full=False`` は GMM(1) と拒否・傷の向きだけの軽い版
    (照明を変える実験・y 勾配の確認実験・種を増やした再現率の数え直し用)。``light`` は照明の向き、
    ``gy`` は :func:`pixel_features` の確認実験の指定。"""
    imgs, masks, labels, weights, lays = make_dataset(seed, light)
    tr, va, te, unk = split(labels, seed)
    res = {"seed": seed}

    # 1. 画素のモデル(学習側の正常な小片だけ)
    ntr = tr[labels[tr] == "normal"]
    Fn = np.concatenate([pixel_features(imgs[i], gy).reshape(-1, 3 + (gy == "add")) for i in ntr])
    D = Fn.shape[1]
    pix = L.learn_ndim_norm(Fn)
    assert np.allclose(pix["mean"], Fn.mean(0), atol=1e-12)
    assert np.allclose(pix["cov"], np.cov(Fn.T) + 1e-6 * np.eye(D), rtol=1e-9, atol=1e-15)
    md_n = np.sqrt(np.einsum("ij,jk,ik->i", Fn - pix["mean"], pix["inv"], Fn - pix["mean"]))
    thresh = float(np.quantile(md_n, 0.999))
    res["pix_thresh"] = thresh

    # 2. 汚れの画素
    s_tr = tr[labels[tr] == "stain"]
    s_te = te[labels[te] == "stain"]
    n_te = te[labels[te] == "normal"]
    if full:
        lut, cut = stain_lut(imgs[s_tr], masks[s_tr])
        res["lut_cut"] = cut
        lut_iou = [iou(L.classify_image_class_lut(chroma01(imgs[i]), lut) > 0, masks[i]) for i in s_te]
        lut_fp = float(np.mean([L.classify_image_class_lut(chroma01(imgs[i]), lut).mean() for i in n_te]))
        # 学習なしの基準線: 1 枚ごとの大津(色度)。正常な小片でも割るので、汚れの無い小片の誤検出も数える。
        otsu_iou = [iou(otsu_stain(imgs[i]), masks[i]) for i in s_te]
        otsu_fp = float(np.mean([otsu_stain(imgs[i]).mean() for i in n_te]))
        # class_2dim_sup は参照領域と同じ画像を塗る op なので、学習側の汚れの小片を横に並べた画像の右に
        # 評価の小片を 1 枚つなぎ、参照領域は学習側の芯だけに置いて、右端の 96 列を切り出す。
        U_tr = np.concatenate([chroma01(imgs[i]) for i in s_tr], 1)
        Y_tr = np.concatenate([luminance(imgs[i]) for i in s_tr], 1)
        R_tr = np.concatenate([ndi.binary_erosion(masks[i], iterations=CORE_ERODE) for i in s_tr], 1)

        def sup(i):
            a = np.concatenate([U_tr, chroma01(imgs[i])], 1)
            b = np.concatenate([Y_tr, luminance(imgs[i])], 1)
            ref = np.concatenate([R_tr, np.zeros((SIZE, SIZE), bool)], 1)
            return L.class_2dim_sup(a, b, ref)[:, -SIZE:]

        sup_iou = [iou(sup(i), masks[i]) for i in s_te]
        sup_fp = float(np.mean([sup(i).mean() for i in n_te]))
        uns_raw, uns_z = [], []
        for i in s_te:
            u, Y = chroma01(imgs[i]), luminance(imgs[i])
            for out, (a, b) in ((uns_raw, (u, Y)), (uns_z, ((u - u.mean()) / u.std(), (Y - Y.mean()) / Y.std()))):
                lab = L.class_2dim_unsup(a, b, n_clusters=2)
                hi = int(np.argmax([u[lab == k].mean() if (lab == k).any() else -1 for k in range(2)]))
                out.append(iou(lab == hi, masks[i]))
        res.update(lut_iou=float(np.mean(lut_iou)), lut_fp=lut_fp, sup_iou=float(np.mean(sup_iou)), sup_fp=sup_fp,
                   uns_raw=float(np.mean(uns_raw)), uns_z=float(np.mean(uns_z)), lut_iou_all=np.array(lut_iou),
                   uns_z_all=np.array(uns_z), stain_w=weights[s_te], s_te=s_te,
                   otsu_iou=float(np.mean(otsu_iou)), otsu_fp=otsu_fp, otsu_iou_all=np.array(otsu_iou))
        res["sup_fn"] = sup
        res["lut"] = lut

    # 3. 領域の特徴
    X = np.array([region_features(im, pix, thresh, gy) for im in imgs])
    assert np.isfinite(X).all() and np.all(X.std(0) > 0)
    Xtr, ytr, Xva, Xte, yte, Xunk = X[tr], labels[tr], X[va], X[te], labels[te], X[unk]
    res.update(X=X, labels=labels, weights=weights, lays=lays, te=te, tr=tr, unk=unk, imgs=imgs, masks=masks,
               pix=pix)

    # 4. 分類器(Fullseye)
    pred = {}
    g1 = L.train_class_gmm(Xtr, ytr, n_centers=1)
    for c, comp in zip(g1["classes"], g1["components"]):    # 成分 1 の EM は閉形式(クラスの平均・共分散)に一致する
        R = Xtr[ytr == c]
        assert np.allclose(comp["means"][0], R.mean(0), rtol=1e-10, atol=1e-12)
        assert np.allclose(comp["covs"][0], np.cov(R.T, bias=True) + 1e-6 * np.eye(R.shape[1]), rtol=1e-8, atol=1e-12)
    pred["gmm1"] = L.classify_class_gmm(g1, Xte)["labels"]
    res["pred"] = pred
    res["yte"] = yte

    # 拒否: 検証側の対数密度の 5 % 点(評価側も未知の孔も見ない)
    thr = float(np.quantile(L.evaluate_class_gmm(g1, Xva)["log_density"], REJECT_Q))
    ld_te = L.evaluate_class_gmm(g1, Xte)["log_density"]
    ld_unk = L.evaluate_class_gmm(g1, Xunk)["log_density"]
    res.update(reject_known=float(np.mean(ld_te < thr)), reject_unknown=float(np.mean(ld_unk < thr)),
               ld_te=ld_te, ld_unk=ld_unk, ld_thr=thr)
    # 基準線: 特徴 1 個(連結成分の数)の外れ値判定、検証側の両側 2.5 % 点
    res.update(cnt_known=float(np.mean(count_outlier_reject(Xva, Xte))),
               cnt_unknown=float(np.mean(count_outlier_reject(Xva, Xunk))))
    if not full:
        return res

    g2 = L.train_class_gmm(Xtr, ytr, n_centers=2, seed=seed)
    pred["gmm2"] = L.classify_class_gmm(g2, Xte)["labels"]
    pred["mlp"] = L.classify_class_mlp(L.train_class_mlp(Xtr, ytr), Xte)["labels"]
    pred["svm"] = L.classify_class_svm(L.train_class_svm(Xtr, ytr), Xte)["labels"]
    pred["knn"] = L.classify_class_knn(L.train_class_knn(Xtr, ytr), Xte, k=5)["labels"]

    # 5. 独立な参照
    res["qda"] = qda_reference(Xtr, ytr, Xte)
    res["knn_ref"] = knn_reference(Xtr, ytr, Xte)
    res["logreg"] = logistic_reference(Xtr, ytr, Xte)
    res["sk"] = sklearn_references(Xtr, ytr, Xte, Xva, Xunk)

    # 6. ラベルを入れ替えた学習(漏れの検査)
    perm = np.random.default_rng(seed + 7).permutation(ytr)
    res["perm_acc"] = float(np.mean(L.classify_class_gmm(L.train_class_gmm(Xtr, perm), Xte)["labels"] == yte))
    return res


def scratch_recall(runs):
    """傷の再現率(GMM(1))を、研削の筋との角で分けて数える。返り: (along 命中, n), (across 命中, n), (全体の命中, n), 正常と呼んだ数。"""
    yy = np.concatenate([r["yte"] for r in runs])
    pp = np.concatenate([r["pred"]["gmm1"] for r in runs])
    aa = np.concatenate([r["lays"][r["te"]] for r in runs])
    sc = yy == "scratch"
    along, across = sc & (aa < 15), sc & (aa > 45)
    return ((int(np.sum(pp[along] == "scratch")), int(along.sum())),
            (int(np.sum(pp[across] == "scratch")), int(across.sum())),
            (int(np.sum(pp[sc] == "scratch")), int(sc.sum())),
            int(np.sum(pp[sc] == "normal")))


def binom_tol(p, n):
    """同じ強さの分類器 2 つが n 個の評価で見せる正解率の差の 3σ(+ 1 個ぶんの量子化)。"""
    p = min(max(p, 1.0 / n), 1.0 - 1.0 / n)
    return 3.0 * np.sqrt(2.0 * p * (1.0 - p) / n) + 1.0 / n


def compare(pred, ref, y):
    """正解率の差・クラスごとの再現率の差が binom_tol の内か。返り: (|d|, tol, 一致率, 再現率の最悪の比)。"""
    n = len(y)
    a, b = float(np.mean(pred == y)), float(np.mean(ref == y))
    tol = binom_tol(0.5 * (a + b), n)
    worst = 0.0
    for c in CLASSES:
        m = y == c
        ra, rb = float(np.mean(pred[m] == c)), float(np.mean(ref[m] == c))
        worst = max(worst, abs(ra - rb) / binom_tol(0.5 * (ra + rb), int(m.sum())))
    return abs(a - b), tol, float(np.mean(pred == ref)), worst


def single_feature_accuracy(runs):
    """特徴 1 個だけで GMM(成分 1)を学習したときの評価側の正解率(種の平均)。漏れの内訳を見る。"""
    out = []
    for j in range(len(FEATURE_NAMES)):
        acc = []
        for r in runs:
            X, y = r["X"][:, j:j + 1], r["labels"]
            m = L.train_class_gmm(X[r["tr"]], y[r["tr"]])
            acc.append(np.mean(L.classify_class_gmm(m, X[r["te"]])["labels"] == y[r["te"]]))
        out.append(float(np.mean(acc)))
    return out


def mosaic(rows):
    return np.concatenate([np.concatenate(r, 1) for r in rows], 0)


def main():
    runs = [run_seed(s) for s in SEEDS]
    extra = [run_seed(s, full=False) for s in EXTRA_SEEDS]       # 種を増やして割合を安定させる(20 種)
    names = ("gmm1", "gmm2", "mlp", "svm", "knn")
    n_te = len(runs[0]["yte"])

    # --- 1. 画素のモデル ---------------------------------------------------------------------------
    print("1. learn_ndim_norm on training normal pixels: mean / cov equal np.mean / np.cov + 1e-6 I (asserted);"
          " Mahalanobis cut (99.9 %% of training normal pixels) %s"
          % ", ".join("%.2f" % r["pix_thresh"] for r in runs))

    # --- 2. 汚れの画素 -----------------------------------------------------------------------------
    print("\n2. stain pixels on the test stain patches (mean IoU over seeds +- std; false positives on test normal patches)")
    rows = []
    for key, fp, nm in (("otsu_iou", "otsu_fp", "BASELINE per-image Otsu on chroma (no training)"),
                        ("lut_iou", "lut_fp", "classify_image_class_lut (cut from training pixels)"),
                        ("sup_iou", "sup_fp", "class_2dim_sup (training stain cores as reference)"),
                        ("uns_raw", None, "class_2dim_unsup k=2, raw channels"),
                        ("uns_z", None, "class_2dim_unsup k=2, z-scored channels")):
        v = np.array([r[key] for r in runs])
        f = np.array([r[fp] for r in runs]) if fp else None
        print("   %-52s IoU %.3f +- %.3f%s" % (nm, v.mean(), v.std(),
                                                "" if f is None else "  false positive %.4f" % f.max()))
        rows.append([nm, "%.3f +- %.3f" % (v.mean(), v.std()), "-" if f is None else "%.4f" % f.max()])
    lut_iou = np.array([r["lut_iou"] for r in runs])
    otsu_iou = np.array([r["otsu_iou"] for r in runs])
    otsu_fp = np.array([r["otsu_fp"] for r in runs])
    print("   baseline - LUT = %+.3f IoU (per seed %s). The LUT's cut was trained on the stain pixels and the true mask;"
          " the baseline trains nothing, yet is at least as good: on this easy task the LUT does not beat a training-free"
          " baseline.\n   Otsu cannot say 'no stain' (it splits a clean patch too): it paints %.2f of the pixels of a"
          " stain-free test patch, the LUT %.4f."
          % ((otsu_iou - lut_iou).mean(), ", ".join("%+.3f" % v for v in otsu_iou - lut_iou), otsu_fp.mean(),
             max(r["lut_fp"] for r in runs)))
    assert np.all(otsu_iou > lut_iou) and 0.0 < (otsu_iou - lut_iou).mean() < 0.06   # 基準線が上、差は小さい(実測に従う)
    assert otsu_fp.min() > 0.3 and max(r["lut_fp"] for r in runs) < 0.01             # 違いは「汚れ無し」を言えるか
    assert np.mean([r["sup_iou"] for r in runs]) < lut_iou.mean() - 0.1             # class_2dim_sup は LUT に負ける
    assert np.mean([r["uns_z"] for r in runs]) > np.mean([r["uns_raw"] for r in runs]) + 0.1
    w_all = np.concatenate([r["stain_w"] for r in runs])
    i_all = np.concatenate([r["lut_iou_all"] for r in runs])
    print("   LUT IoU by stain weight: lower third %.3f, upper third %.3f"
          % (i_all[w_all < 1 / 3].mean(), i_all[w_all > 2 / 3].mean()))
    pixel_table = rows

    # --- 3. 正解率 ---------------------------------------------------------------------------------
    print("\n3. accuracy on the test split, %d seeds x %d test patches (train %d / validation %d per seed)"
          % (len(SEEDS), n_te, len(runs[0]["tr"]), int(SPLIT[1] * N_PER_CLASS) * len(CLASSES)))
    acc = {n: np.array([np.mean(r["pred"][n] == r["yte"]) for r in runs]) for n in names}
    for n in names:
        print("   %-5s %.3f +- %.3f  (min %.3f, max %.3f)" % (n, acc[n].mean(), acc[n].std(), acc[n].min(), acc[n].max()))
        assert acc[n].std() > 0.0, n                       # 分割で揺れている(同じ結果の写しではない)
        assert acc[n].min() > 0.8, n
    best = max(names, key=lambda n: acc[n].mean())

    # --- 4. 閉形式の参照 ---------------------------------------------------------------------------
    agq = np.array([np.mean(r["pred"]["gmm1"] == r["qda"]) for r in runs])
    agk = np.array([np.mean(r["pred"]["knn"] == r["knn_ref"]) for r in runs])
    print("\n4. closed form: gmm1 vs QDA (scipy multivariate_normal) agreement min %.4f;"
          " knn vs brute-force vote min %.4f" % (agq.min(), agk.min()))
    assert agq.min() >= 0.995 and agk.min() >= 0.99

    # --- 5. 第 2 実装 ------------------------------------------------------------------------------
    have_sk = all(r["sk"] is not None for r in runs)
    print("\n5. second implementation: %s" % ("scikit-learn" if have_sk else
                                             "scikit-learn absent -> multinomial logistic regression (scipy)"))
    ref_rows = []
    for n in names:
        if have_sk:
            refs = [r["sk"][n] for r in runs]
            ref_name = {"gmm1": "GaussianMixture(1)", "gmm2": "GaussianMixture(2)", "mlp": "MLPClassifier",
                        "svm": "LinearSVC", "knn": "KNeighbors(5)"}[n]
        elif n in ("mlp", "svm", "gmm2"):
            refs = [r["logreg"] if n != "gmm2" else r["qda"] for r in runs]
            ref_name = "logistic (scipy)" if n != "gmm2" else "QDA (closed form)"
        else:
            continue
        cmp = [compare(r["pred"][n], rp, r["yte"]) for r, rp in zip(runs, refs)]
        racc = np.array([np.mean(rp == r["yte"]) for r, rp in zip(runs, refs)])
        d = np.array([c[0] for c in cmp])
        t = np.array([c[1] for c in cmp])
        ag = np.array([c[2] for c in cmp])
        wr = max(c[3] for c in cmp)
        print("   %-5s vs %-19s ref acc %.3f +- %.3f; |d acc| max %.3f (tol %.3f); |d acc|/tol max %.2f;"
              " recall |d|/tol max %.2f; agreement %.3f" % (n, ref_name, racc.mean(), racc.std(), d.max(),
                                                           t.min(), (d / t).max(), wr, ag.mean()))
        assert np.all(d <= t) and wr <= 1.0, (n, d, t, wr)
        ref_rows.append([n, "%.3f +- %.3f" % (acc[n].mean(), acc[n].std()), ref_name,
                         "%.3f +- %.3f" % (racc.mean(), racc.std()), "%.2f" % (d / t).max(), "%.3f" % ag.mean()])

    # --- 6. 分からない / reject ---------------------------------------------------------------------
    rk = np.array([r["reject_known"] for r in runs])
    ru = np.array([r["reject_unknown"] for r in runs])
    n_known, n_unk = n_te * len(runs), N_UNKNOWN * len(runs)
    tol_frr = REJECT_Q + 3 * np.sqrt(REJECT_Q * (1 - REJECT_Q) / n_known)
    print("\n6. GMM rejection (cut = %d %% point of the validation log density):" % round(100 * REJECT_Q))
    print("   corrosion pits (never trained) rejected %.3f (per seed %s)" % (ru.mean(), ", ".join("%.2f" % v for v in ru)))
    print("   known test patches rejected %.3f (limit %.3f = q + 3 sqrt(q(1-q)/n))" % (rk.mean(), tol_frr))
    assert ru.mean() >= 0.9 and rk.mean() <= tol_frr
    if have_sk:
        sk_u = np.array([r["sk"]["reject_unknown"] for r in runs])
        sk_k = np.array([r["sk"]["reject_known"] for r in runs])
        print("   scikit-learn GaussianMixture(1) with the same rule: pits %.3f, known %.3f" % (sk_u.mean(), sk_k.mean()))
        assert abs(sk_u.mean() - ru.mean()) <= 2.0 / N_UNKNOWN and abs(sk_k.mean() - rk.mean()) <= 2.0 / n_te
    accepted_as = {}
    for r in runs:
        ok = r["ld_unk"] >= r["ld_thr"]
        if not ok.any():
            continue
        g1 = L.train_class_gmm(r["X"][r["tr"]], r["labels"][r["tr"]])
        for lab in L.classify_class_gmm(g1, r["X"][r["unk"]][ok])["labels"]:
            accepted_as[lab] = accepted_as.get(lab, 0) + 1
    print("   pits that slipped through were called: %s" % (accepted_as or "none"))
    # 基準線: 特徴 1 個(異常画素の連結成分の数)の外れ値判定。検証側の両側 2.5 % 点の外を拒否する。
    cu = np.array([r["cnt_unknown"] for r in runs])
    ck = np.array([r["cnt_known"] for r in runs])
    print("   BASELINE one feature (number of anomalous components), two-sided 2.5 %% cuts of the validation side:"
          " pits %.3f (per seed %s), known rejected %.3f" % (cu.mean(), ", ".join("%.2f" % v for v in cu), ck.mean()))
    print("   -> the GMM's 'I do not know' (pits %.3f, known %.3f) is no better than the one-feature outlier test"
          " (pits %.3f, known %.3f)" % (ru.mean(), rk.mean(), cu.mean(), ck.mean()))
    assert cu.mean() >= ru.mean() and ck.mean() <= tol_frr
    pool = runs + extra
    pg = np.mean([r["reject_unknown"] for r in pool])
    pc = np.mean([r["cnt_unknown"] for r in pool])
    n_pit = N_UNKNOWN * len(pool)
    print("   %d seeds pooled (%d pits): GMM %.3f [Wilson 95 %% %.3f-%.3f], one-feature baseline %.3f [%.3f-%.3f]"
          % (len(pool), n_pit, pg, *wilson(round(pg * n_pit), n_pit), pc, *wilson(round(pc * n_pit), n_pit)))

    # --- 7. 出来すぎていないか / leakage --------------------------------------------------------------
    perm = np.array([r["perm_acc"] for r in runs])
    tol_perm = 0.25 + 3 * np.sqrt(0.25 * 0.75 / n_known)
    print("\n7. leakage checks")
    print("   labels permuted before training: accuracy %.3f (limit %.3f = 1/4 + 3 sigma)" % (perm.mean(), tol_perm))
    assert perm.mean() <= tol_perm
    sfa = single_feature_accuracy(runs)
    print("   single-feature GMM accuracy: %s" % ", ".join("%s %.3f" % (n, a) for n, a in zip(FEATURE_NAMES, sfa)))
    assert max(sfa) < acc["gmm1"].mean()                   # 1 個で全部が決まる特徴は無い
    recall = {c: np.mean([np.mean(r["pred"]["gmm1"][r["yte"] == c] == c) for r in runs]) for c in CLASSES}
    print("   gmm1 recall per class: %s" % ", ".join("%s %.3f" % kv for kv in recall.items()))
    perfect = [c for c, v in recall.items() if v == 1.0] + [n for n in names if acc[n].max() == 1.0]
    if perfect:
        # 再現率 100 % のクラスの内訳: 色度の差だけで汚れ / それ以外 を分けられるか(汚れは反射率の色を変える唯一の欠陥)
        ce = np.concatenate([r["X"][r["te"], 4] for r in runs])
        yy = np.concatenate([r["yte"] for r in runs])
        gap = ce[yy == "stain"].min() - ce[yy != "stain"].max()
        print("   100 %% for %s -> chroma excess: stain min %.4f, others max %.4f (gap %.4f); the stain is the only"
              " defect that changes the albedo colour, and the feature is measured from the image" % (
                  perfect, ce[yy == "stain"].min(), ce[yy != "stain"].max(), gap))
        assert set(perfect) <= {"stain"} and gap > 0
    lo_hi = []
    for n in names:
        wl, wh = [], []
        for r in runs:
            y, w, p = r["yte"], r["weights"][r["te"]], r["pred"][n]
            d = y != "normal"
            wl.append(np.mean(p[d & (w < 1 / 3)] == y[d & (w < 1 / 3)]))
            wh.append(np.mean(p[d & (w > 2 / 3)] == y[d & (w > 2 / 3)]))
        lo_hi.append((n, float(np.mean(wl)), float(np.mean(wh))))
    print("   defect accuracy by weight (lower / upper third): %s"
          % ", ".join("%s %.3f / %.3f" % t for t in lo_hi))
    assert all(lo < hi for _, lo, hi in lo_hi)               # 誤りは薄い欠陥に集まる
    # 傷を見落とす向き: 種 5 本(主)と、種を 20 本に増やした合算(割合と Wilson 95 % 区間)
    (a5, n5), (c5, m5), _, _ = scratch_recall(runs)
    (aa_k, aa_n), (ac_k, ac_n), (st_k, st_n), called_normal = scratch_recall(runs + extra)
    lo_a, hi_a = wilson(aa_k, aa_n)
    lo_c, hi_c = wilson(ac_k, ac_n)
    print("   gmm1 scratch recall, 5 seeds: within 15 deg of the grinding lay %.3f (%d of %d), more than 45 deg %.3f (%d of %d)"
          % (a5 / n5, a5, n5, c5 / m5, c5, m5))
    print("   gmm1 scratch recall, %d seeds pooled: within 15 deg %.3f (%d of %d, Wilson 95 %% %.3f-%.3f) -> missed %.3f"
          " (%.3f-%.3f); more than 45 deg %.3f (%d of %d, %.3f-%.3f); all scratches %.3f (%d of %d), %d called normal"
          % (len(runs) + len(extra), aa_k / aa_n, aa_k, aa_n, lo_a, hi_a, 1 - aa_k / aa_n, 1 - hi_a, 1 - lo_a,
             ac_k / ac_n, ac_k, ac_n, lo_c, hi_c, st_k / st_n, st_k, st_n, called_normal))
    assert hi_a < 0.5 and lo_c > 0.85                      # 筋に沿う傷は半分以上を見落とし、立った傷はほぼ見える(区間で)
    assert aa_n >= 100 and ac_n >= 400

    # --- 8. 見落としの原因を確かめる実験 / what does not fix the missed scratches ----------------------------
    # 「筋を横切る勾配 |dY/dx| を選んだから筋沿いの傷も消える」という説明は支持されない: y 方向の勾配を足しても
    # 置き換えても、照明の向きを回しても、筋に沿う傷は見えるようにならない。原因はこの実験では特定していない。
    print("\n8. what does not fix the scratches along the lay (5 seeds, GMM(1); recall within 15 deg / more than 45 deg)")
    print("   %-34s %-18s %-18s" % ("pixel features / light", "within 15 deg", "more than 45 deg"))
    print("   %-34s %-18s %-18s" % ("|dY/dx| (as is)", "%.3f (%d of %d)" % (a5 / n5, a5, n5),
                                    "%.3f (%d of %d)" % (c5 / m5, c5, m5)))
    fix_along = {}
    for tag, kw in (("|dY/dx| + |dY/dy| added", {"gy": "add"}), ("|dY/dy| instead of |dY/dx|", {"gy": "replace"})):
        rr = [run_seed(sd, full=False, **kw) for sd in SEEDS]
        (k1, n1), (k2, n2), _, _ = scratch_recall(rr)
        fix_along[tag] = k1 / n1
        print("   %-34s %-18s %-18s" % (tag, "%.3f (%d of %d)" % (k1 / n1, k1, n1), "%.3f (%d of %d)" % (k2 / n2, k2, n2)))
    light_rows = [("base light (0.55, 0.30, 0.78)", runs)]
    for nm, lt in LIGHT_VARIANTS:
        light_rows.append((nm, [run_seed(sd, light=lt, full=False) for sd in SEEDS]))
    for nm, rr in light_rows[1:]:
        (k1, n1), (k2, n2), _, _ = scratch_recall(rr)
        fix_along[nm] = k1 / n1
        print("   %-34s %-18s %-18s" % ("light " + nm, "%.3f (%d of %d)" % (k1 / n1, k1, n1), "%.3f (%d of %d)" % (k2 / n2, k2, n2)))
    assert all(v < 0.5 for v in fix_along.values()), fix_along      # どれも直らない(各 n = 40 の点推定)

    # --- 9. 照明の向きを変えると「分からない」の率は動く / the rejection rate belongs to one lighting ----------
    print("\n9. pit rejection under other lighting (5 seeds each; GMM log density vs one-feature baseline; known = false rejection)")
    print("   %-34s %-22s %-22s" % ("light", "GMM pits / known", "baseline pits / known"))
    rej_g = []
    for nm, rr in light_rows:
        g_u, g_k = np.mean([r["reject_unknown"] for r in rr]), np.mean([r["reject_known"] for r in rr])
        c_u, c_k = np.mean([r["cnt_unknown"] for r in rr]), np.mean([r["cnt_known"] for r in rr])
        rej_g.append(g_u)
        print("   %-34s %.3f / %.3f          %.3f / %.3f" % (nm, g_u, g_k, c_u, c_k))
    print("   -> the GMM's pit rejection ranges %.3f-%.3f over four lightings: the headline rate is one condition's value"
          % (min(rej_g), max(rej_g)))
    assert max(rej_g) - min(rej_g) >= 0.1

    # --- 図 / figures ------------------------------------------------------------------------------
    r0 = runs[0]
    rng = np.random.default_rng(5)
    kinds = CLASSES + (UNKNOWN,)
    ws = (0.05, 0.3, 0.55, 0.8, 1.0)
    pics = [[render_patch(k, w, rng)[0] for w in ws] for k in kinds]
    anoms = [[np.repeat((~L.class_ndim_norm(pixel_features(im), r0["pix"], thresh=r0["pix_thresh"]))[..., None]
                        .astype(float), 3, -1) for im in row] for row in pics]
    for a in (mosaic(pics), mosaic(anoms)):
        assert np.isfinite(a).all() and float(np.ptp(a)) > 0.3
    figs.save_grid("defect_patches", [mosaic(pics), mosaic(anoms)],
                   captions=["rows: %s; columns: weight %s (the normal row has no defect: its weight is unused)"
                             % (" / ".join(kinds), " ".join("%.2f" % w for w in ws)),
                             "class_ndim_norm: pixels unlike training normal metal (Mahalanobis > %.2f)"
                             % r0["pix_thresh"]],
                   ncols=2, caption="rendered (synthetic) ground-metal patches (height defects shade, the stain changes colour)")
    s_te = r0["s_te"]
    k_mid = int(s_te[int(np.argmin(np.abs(r0["stain_w"] - 0.25)))])
    im = r0["imgs"][k_mid]
    u, Y = chroma01(im), luminance(im)
    lab = L.class_2dim_unsup((u - u.mean()) / u.std(), (Y - Y.mean()) / Y.std(), n_clusters=2)
    hi = int(np.argmax([u[lab == k].mean() for k in range(2)]))
    panels = [im, r0["masks"][k_mid].astype(float), (L.classify_image_class_lut(u, r0["lut"]) > 0).astype(float),
              r0["sup_fn"](k_mid).astype(float), (lab == hi).astype(float)]
    big = [np.kron(p, np.ones((3, 3, 1))) if p.ndim == 3 else np.kron(p, np.ones((3, 3))) for p in panels]
    figs.save_grid("stain_pixels", big,
                   captions=["test stain patch (weight %.2f)" % r0["weights"][k_mid], "true stain pixels",
                             "classify_image_class_lut IoU %.2f" % iou(panels[2] > 0, r0["masks"][k_mid]),
                             "class_2dim_sup IoU %.2f" % iou(panels[3] > 0, r0["masks"][k_mid]),
                             "class_2dim_unsup (z-scored) IoU %.2f" % iou(panels[4] > 0, r0["masks"][k_mid])],
                   ncols=5, gray=[False, True, True, True, True], caption="painting the stain pixel by pixel")
    figs.save_table("stain_pixel_iou", ["pixel classifier", "IoU on test stains", "false positive on normal"],
                    pixel_table, title="stain pixels, %d seeds" % len(SEEDS),
                    caption="LUT cut: supervised on training stain patches and true masks; Otsu baseline trains nothing")
    figs.save_table("classifier_accuracy", ["Fullseye", "accuracy", "second implementation", "accuracy",
                                            "|d acc| / tol", "agreement"],
                    ref_rows, title="%d seeds x %d test patches" % (len(SEEDS), n_te),
                    caption="tol = 3 sqrt(2p(1-p)/n) + 1/n; same features, same split")
    pooled_y, pooled_p = [], []
    for r in runs:
        g1 = L.train_class_gmm(r["X"][r["tr"]], r["labels"][r["tr"]])
        for idx, ld in ((r["te"], r["ld_te"]), (r["unk"], r["ld_unk"])):
            p = L.classify_class_gmm(g1, r["X"][idx])["labels"].astype(object)
            p[ld < r["ld_thr"]] = "reject"
            pooled_p.append(p)
            pooled_y.append(r["labels"][idx])
    pooled_y, pooled_p = np.concatenate(pooled_y), np.concatenate(pooled_p)
    assert np.isclose(np.mean(pooled_p[pooled_y == UNKNOWN] == "reject"), ru.mean())     # 表と門が同じ数を数えている
    cols = list(CLASSES) + ["reject"]
    table = [[t] + [str(int(np.sum((pooled_y == t) & (pooled_p == c)))) for c in cols] for t in kinds]
    print("\n   pooled gmm1 confusion with reject (rows = truth):")
    for row in table:
        print("   %-8s %s" % (row[0], " ".join("%5s" % v for v in row[1:])))
    figs.save_table("gmm_confusion_reject", ["truth / called"] + cols, table,
                    title="train_class_gmm + evaluate_class_gmm, %d seeds pooled" % len(SEEDS),
                    caption="pits never seen in training: %.0f %% rejected; known patches rejected %.1f %%"
                    % (100 * ru.mean(), 100 * rk.mean()))
    edges = np.linspace(0, 1, 6)
    mid = 0.5 * (edges[1:] + edges[:-1])
    series = []
    for n, style in (("gmm1 (solid)", None), ("mlp (dashed)", "dashed"), ("knn (dotted)", "dotted")):
        a = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            hit = [np.mean(r["pred"][n.split()[0]][m] == r["yte"][m]) for r in runs
                   for m in [(r["yte"] != "normal") & (r["weights"][r["te"]] >= lo) & (r["weights"][r["te"]] < hi)]
                   if m.any()]
            a.append(float(np.mean(hit)))
        series.append((n, mid, np.array(a)))
    figs.save_plot("accuracy_by_weight", series, xlabel="defect weight (depth / stain density, 0-1)",
                   ylabel="accuracy on defect patches", title="errors gather on faint defects",
                   ylim=(0.0, 1.0),
                   kinds=["line"] * 3, styles=[None, "dashed", "dotted"], colors=["emphasis", "neutral", "reference"],
                   caption="%d seeds, test split; best overall %s %.3f; axis from 0" % (len(SEEDS), best, acc[best].mean()))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("PASS")


if __name__ == "__main__":
    main()
