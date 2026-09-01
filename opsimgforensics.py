# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsimgforensics — fullseye **画像フォレンジック** op の統一レジストリ(:mod:`imgforensics` の台帳)。

動機は fullseye 自身の空白の実測(2026-09-02)。op カタログ全文に対して
``prnu`` / ``ela`` / ``copy_move`` / ``jpeg_ghost`` / ``phash`` / ``dhash`` /
``watermark`` / ``stegan`` を検索すると **一件もヒットしない**。一方で改竄を
*作る*側の道具は揃っていた —— :mod:`defectgen`(欠陥合成)、``backends_aug`` の
``aug_jpeg_blocks`` / ``aug_fixed_pattern`` / ``aug_motion_blur``、
:mod:`imagemorph` の warp、:mod:`features` のキーポイントとマッチ、
:mod:`mosaic` の RANSAC、:mod:`imgio` の入出力。

**この非対称がこの族の存在理由である**。改竄側を自分で作れるということは、
検出器を測るときに **正解(どこを、どこへ、どれだけずらしたか)が手元にある**
ということで、「例外が出ないこと」ではなく「**既知の答えを当てられるか、
当てられない条件はどれか**」を数で固定できる。``tests/test_imgforensics.py`` は
その形で書いてある。

## この族は「改竄されている」と言わない

14 op のどれも ``tampered: True`` / ``is_forged`` のような判定を返さない。
返すのは **証拠量**(PCE、ハミング距離、シフトベクトルと対応数、量子化ステップ、
ブロックごとの σ)と、**その量が何を意味しないか**(各 table の ``caveats``)。
理由は 2 つあり、どちらも実測に基づく:

1. **前提が崩れても例外が出ない**。ELA は「元が JPEG」を仮定し、崩れると
   貼付部/背景の比が 4.898 → **1.096**(区別不能)になるが、地図は同じように
   返る。PRNU は再圧縮で PCE 7246 → **207**(品質 30)まで落ちるが、やはり
   有限値が返る。「しきい値を超えたので改竄」と書ける op を用意することは、
   この repo が潰そうとしている失敗を自分でやることになる。
2. **量は単調でない**。同じ PCE 200 が「品質 30 に圧縮された同一カメラ」でも
   「解像度が上がって偶然強く出た別カメラ」でもありうる。しきい値は撮影条件ごとに
   決めるもので、ライブラリが同梱できるものではない。

## 入出力 sort の判断

既存語彙をそのまま使ったもの(**新語を作らなかった**):

  * ``image2d`` —— ELA 地図・ゴースト品質地図・雑音 σ 地図・透かし入り画像。
    どれも「画素の格子に並んだ実数」であり、既存の image2d 消費 op(色付け、
    正規化、しきい値、モルフォロジ)が **意味を持って**使える。
  * ``images`` —— :func:`imgforensics.jpeg_ghost_map` が返す品質ごとの地図の列。
    既存の ``images`` 語彙(同じ shape の 2-D の列)そのもので、
    :func:`imgforensics.jpeg_ghost_quality` が食う。産む 1・食う 1 で閉じている。
  * ``table`` —— 照合結果・品質推定・コピー&ムーブの領域対・透かしの掃引表。
    どれも dict か list で、既存 ``table`` 述語 ``isinstance(v, (list, dict))``
    をそのまま満たす。**新語を作らなかった判断は :mod:`opsvolcolor` と同じ基準**で、
    「混ぜると例外でなく、もっともらしく間違った数値が出るか」を満たさない ——
    table を食う既存 op(``abcd_matrix`` / ``wavefront_stats`` / ``istft``)は
    どれもキーが無くて ValueError になる。
  * ``measurement`` —— :func:`imgforensics.hash_distance` の返り(Python の int)。

新語を **2 つ**作った。どちらも上の基準を実測で満たしたものだけである。

### 新語 1: ``phash`` —— 知覚ハッシュ / 透かしのビット列

**bool の 1-D 配列**。既存語彙に相乗りさせられない理由は実測にある:

  * bool の 1-D は既存の ``signal`` / ``indices`` / ``descriptor`` の述語を
    **3 つとも満たす**(``signal`` = ndim 1、``indices`` = ndim 1、
    ``descriptor`` = ndim 1 か 2)。
  * 64 ビットのハッシュを ``signal`` の消費 op へ渡すと、``signal1d`` の
    **5 op(fft_spectrum / lowpass / highpass / bandpass / smooth)が例外も NaN も
    出さず**、(64,) の有限な結果を返す(2026-09-02 実測)。「ハッシュの低域通過」
    という意味の無い有限値である。
  * 逆向き —— float の 1-D を :func:`imgforensics.hash_distance` へ渡す —— は
    **fail-closed** にしてある(dtype を検査して ValueError)。素通しにすると
    ``!=`` はほぼ全ビットで真になり、「距離 64 = 完全に別画像」という
    *もっともらしい* 答えが出るからである。
  * つまり **安全なのは片側だけ**。実行時チェックでは守れないので型で分ける
    (``rgbvolume`` を ``lightfield`` から分けたのと同じ判断)。

袋小路にならないことも確認済み: 産む op 2(``perceptual_hash`` /
``watermark_extract``)・食う op 3(``hash_distance`` / ``watermark_embed`` /
``watermark_capacity``)。しかも **産んだものを食う経路に意味がある** ——
``hash_distance(埋めたビット, watermark_extract(...))`` がそのまま BER になる。

### 新語 2: ``fingerprint`` —— PRNU センサ指紋

``(H, W)`` の float64 で、ゼロ平均・単位分散。**``image2d`` の述語を完全に満たす**
ので、実行時には普通の画像と区別できない。実測(2026-09-02、64x64 の指紋を
``image2d`` を食う既存 op へ):

  * ``imgio`` の **11 op**(``to_float01`` ``to_uint8`` ``normalize``
    ``ensure_gray`` ``ensure_color`` ``apply_cmap`` ``colorize_depth``
    ``colorize_disparity`` ``shaded_relief`` ``colorize_height``
    ``colorize_labels``)+ ``segmentation.regiongrowing_n`` の計 **12 op** が
    例外も非有限も出さずに結果を返す。指紋を「深度」や「高さ」として色付けした
    有限の絵である。
  * 逆に普通の画像を :func:`imgforensics.fingerprint_correlate` へ渡す向きは、
    ``|mean| > 0.05 * std`` のゲートで弾ける(実測: 指紋 4.8e-18 に対し
    自然画像 4.626 / 暗い画像 4.626 / 高コントラスト 1.801)。
  * **ただしゲートは完全ではない**。自分でゼロ平均化した画像は通り、
    PCE = -5.97 という有限値が返る(実測)。ここでも **安全なのは片側だけ**である。

袋小路にならないことも確認済み: 産む op 1(``sensor_fingerprint``)・
食う op 2(``fingerprint_correlate`` / ``fingerprint_strength_map``)。
``fingerprint_strength_map`` が ``image2d`` への **出口**になっているので、
新語彙が行き止まりにならない。

## optional 依存の扱い

``func`` は import 時に解決するが、**中身の optional 依存(Pillow / PyWavelets)は
呼ぶまで触らない**。したがって Pillow が無い環境でも本モジュールの import と
:func:`list_ops` は通り、``error_level_map`` を **呼んだときだけ**
:class:`ImportError` になる。:data:`NEEDS` にどの op が何を要るかを表で持たせてある
(親が facade へ配線するとき、環境依存の op を事前に除ける)。

## 使い方

    import opsimgforensics
    opsimgforensics.list_ops("hash")
    opsimgforensics.get("perceptual_hash")(img, mode="dct")
    opsimgforensics.call("copy_move_regions", img)      # 宣言型 table
"""
import imgforensics

_MOD = {"imgforensics": imgforensics}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
#   既存語彙の再利用: image2d / images / table / measurement
#   新語彙: phash / fingerprint(根拠はモジュール docstring。どちらも実測つき)
_CATALOG = {
    # 知覚ハッシュ。phash の入口 1・出口 1
    "hash": [
        ("perceptual_hash", "imgforensics", ["image2d"], "phash"),
        ("hash_distance", "imgforensics", ["phash", "phash"], "measurement"),
    ],
    # 証拠量を「解釈できる形」にする層。しきい値は同梱せず、利用者自身の
    # 清浄データから帰無分布を測る ―― 分離点は枚数・解像度・圧縮率・被写体で
    # 動くので、出荷時に決められる値ではないため(各 op の caveats どおり)。
    #
    # ここは **measurement の消費側**でもある。2026-09-02 の点検まで
    # measurement は hash_distance が産むだけで食う op が無い袋小路だった。
    "calibration": [
        ("null_distribution", "imgforensics", ["signal"], "table"),
        ("evidence_quantile", "imgforensics", ["measurement", "table"], "table"),
    ],
    # PRNU センサ指紋。fingerprint の入口 1・出口 2(うち 1 つは image2d へ抜ける)
    "sensor": [
        ("sensor_fingerprint", "imgforensics", ["images"], "fingerprint"),
        ("fingerprint_correlate", "imgforensics", ["image2d", "fingerprint"], "table"),
        ("fingerprint_strength_map", "imgforensics", ["fingerprint"], "image2d"),
    ],
    # 圧縮履歴。images の入口と出口が対になっている
    "compression": [
        ("error_level_map", "imgforensics", ["image2d"], "image2d"),
        ("jpeg_quality_estimate", "imgforensics", ["image2d"], "table"),
        ("jpeg_ghost_map", "imgforensics", ["image2d"], "images"),
        ("jpeg_ghost_quality", "imgforensics", ["images"], "image2d"),
    ],
    # ノイズ整合性
    "noise": [
        ("noise_inconsistency_map", "imgforensics", ["image2d"], "image2d"),
    ],
    # 自己複製(コピー&ムーブ)
    "copy_move": [
        ("copy_move_regions", "imgforensics", ["image2d"], "table"),
    ],
    # 電子透かし。phash を食い、phash を産む
    "watermark": [
        ("watermark_embed", "imgforensics", ["image2d", "phash"], "image2d"),
        ("watermark_extract", "imgforensics", ["image2d"], "phash"),
        ("watermark_capacity", "imgforensics", ["image2d", "phash"], "table"),
    ],
}

#: op → 必要な optional 依存(空 tuple = numpy + scipy だけで動く)。
#: 親が facade へ配線するとき、環境に無い依存の op を事前に外すのに使う。
#: **import 時には触らない** —— 表があること自体は環境に依存しない。
NEEDS = {
    "perceptual_hash": (), "hash_distance": (),
    "sensor_fingerprint": (),          # denoiser="wavelet" のときだけ pywt
    "fingerprint_correlate": (), "fingerprint_strength_map": (),
    "error_level_map": ("PIL",),
    "jpeg_quality_estimate": (),
    "jpeg_ghost_map": ("PIL",),
    "jpeg_ghost_quality": (),
    "noise_inconsistency_map": (),
    "copy_move_regions": (),
    "watermark_embed": ("pywt",),
    "watermark_extract": ("pywt",),
    "watermark_capacity": ("pywt",),   # jpeg_quality を渡すと PIL も
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
                         "func": fn, "doc": doc, "needs": NEEDS.get(name, ())}
    return reg


OPSIMGFORENSICS = _build()


#: 親が ``tools/chain_fuzz.py`` の ``TYPE_CHECKS`` へ足すための **述語の提案**。
#: 述語が無い型は「宣言 out 型が何であっても TYPEMISS にならない」穴なので、
#: 新語彙を足すときは述語も一緒に出す(このモジュールは既存ファイルを変更しない)。
#:
#: ★``phash`` の述語で **dtype を見ることが本体**である。``ndim == 1`` だけだと
#:   既存の ``signal`` と完全に重なり、分けた意味が無くなる。
#: ★``fingerprint`` の述語は ``image2d`` と **形では区別できない**。ゼロ平均性で
#:   切るしかなく、それは実行時の統計的な当て推量なので、述語も同じ弱さを持つ
#:   (だから型で分けている)。この弱さを述語のコメントに残しておくこと。
TYPE_CHECK_PROPOSALS = {
    "phash": "lambda v: isinstance(v, np.ndarray) and v.ndim == 1 "
             "and v.dtype == np.bool_ and v.size > 0",
    "fingerprint": "lambda v: isinstance(v, np.ndarray) and v.ndim == 2 "
                   "and v.dtype.kind == 'f' and v.size > 0 "
                   "and np.all(np.isfinite(v)) and float(v.std()) > 0 "
                   "and abs(float(v.mean())) <= 0.05 * float(v.std())",
}

#: 親が ``tools/chain_fuzz.py`` の ``make_generators()`` へ足すための **種の提案**。
#: 種が無い型は「同じ連鎖の中で先に生成 op が引かれた場合だけ」到達するので、
#: 実測では「一度も実行されないまま発見ゼロ」になる(keypoints で実測済みの罠)。
#:
#: ★``fingerprint`` の種は **必ず ``sensor_fingerprint`` を通して作る**こと。
#:   ``rng.standard_normal((H, W))`` を直接置くと、それは指紋ではなく白色雑音で、
#:   照合は常に「無相関」を返す = 検査面が増えたつもりで増えない。
#: ★``images`` の種は **同じ shape** で **2 枚以上**。1 枚だと sensor_fingerprint が
#:   fail-closed し続けて一度も走らない。
GENERATOR_PROPOSALS = {
    "phash": "lambda rng: rng.integers(0, 2, 64).astype(bool)",
    "fingerprint": "lambda rng: imgforensics.sensor_fingerprint(["
                   "np.clip(rng.random((64, 64)) * 0.6 + 0.2 + 0.03 * k"
                   " + 0.01 * rng.standard_normal((64, 64)), 0, 1)"
                   " for k in [rng.standard_normal((64, 64))] * 4])",
    "images": "lambda rng: [np.clip(rng.random((64, 64)), 0, 1) for _ in range(4)]",
}

#: 引数の既定値がプールの値と噛み合わない op(``OP_PARAM_HINTS`` へ入れるべきもの)。
#: 既定のままだと毎回 ValueError になり、**一度も実行されないまま「発見ゼロ」**に
#: 見える。
#:
#: ★``jpeg_ghost_quality`` の ``qualities=None`` は「40..95 step 5 の 12 本」を
#:   仮定するので、``images`` の種が 12 本でないと必ず ValueError になる。
#:   これは意図した fail-closed(添字と品質がずれた地図を返さない)なので、
#:   ファザー側で本数を合わせる。
#: ★``watermark_*`` の ``bits`` は容量(LL の 8x8 ブロック数)以下でなければ
#:   ならない。64x64 の image2d + level 1 の LL は 32x32 = 16 ブロック。
OP_PARAM_HINT_PROPOSALS = {
    ("jpeg_ghost_map", "qualities"): "lambda rng: [50, 70, 90]",
    ("jpeg_ghost_quality", "qualities"): "lambda rng: None  # images の種を 12 本にする",
    ("perceptual_hash", "hash_size"): "lambda rng: 8",
    ("watermark_embed", "bits"): "lambda rng: rng.integers(0, 2, 16).astype(bool)",
    ("watermark_capacity", "bits"): "lambda rng: rng.integers(0, 2, 16).astype(bool)",
    ("watermark_extract", "n_bits"): "lambda rng: 16",
    ("copy_move_regions", "step"): "lambda rng: 2   # 既定 1 は 64x64 でも十分速いが保険",
}

#: 宣言 out 型と素の返りの橋渡し。**意図的に空** —— 14 op すべてが宣言型そのものを
#: 素で返す設計にしてある。空にしておくと :func:`call` は :func:`get` と同じ値を
#: 返し、連鎖ファザーの TYPEMISS 検査が **素の返りをそのまま**宣言と突き合わせる
#: = 検証が最も厳しい。
#:
#: フォレンジックの台帳で adapter を置くのは特に危険で、「宣言と実装がずれていても
#: adapter が吸収する」状態を作ると、**もっともらしい嘘を検出するために作った
#: モジュールが、自分の嘘を隠す**ことになる。
RESULT_ADAPTERS = {}

#: 文書化済みの非有限を返す op。**空** —— どの op も非有限を返さない。
#: :func:`imgforensics._as_image` が入口で非有限を拒否し、ゼロ除算になりうる箇所
#: (指紋の分母、PCE のエネルギー、相関のノルム)はすべて明示的な
#: :class:`ValueError` にしてある。``watermark_capacity`` の ``psnr_db`` だけは
#: **完全一致のとき ``inf``** を返しうるが、それは table の中の値であって
#: op の返り型ではない(``table`` は非有限検査の対象外)。
NONFINITE_BY_CONTRACT = frozenset()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSIMGFORENSICS.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


def get(name):
    """op 名 → 実体(callable、素の返り型)。宣言型が欲しければ :func:`call`。"""
    return OPSIMGFORENSICS[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSIMGFORENSICS[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報(category / module / in / out / func / doc / needs)。"""
    return OPSIMGFORENSICS[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSIMGFORENSICS.items() if m["func"] is None]


def requires(dep=None):
    """optional 依存が要る op。``dep`` 指定でその依存だけに絞る。

    **実際にその依存が入っているかは調べない**(調べると import 時に重い依存を
    触ることになり、「import は通る」という約束が壊れる)。表を返すだけである。
    """
    return {n: m["needs"] for n, m in OPSIMGFORENSICS.items()
            if m["needs"] and (dep is None or dep in m["needs"])}


def conversion_edges():
    """単入力の変換 ``(in, out)`` 一覧。台帳が新設した辺を数えるのに使う。"""
    return sorted({(m["in"][0], m["out"]) for m in OPSIMGFORENSICS.values()
                   if len(m["in"]) == 1 and m["in"][0] != m["out"]})


def new_sorts():
    """本台帳が導入した新語彙と、その入口 / 出口の op(袋小路検査用)。"""
    out = {}
    for sort in ("phash", "fingerprint"):
        producers = [n for n, m in OPSIMGFORENSICS.items() if m["out"] == sort]
        consumers = [n for n, m in OPSIMGFORENSICS.items() if sort in m["in"]]
        out[sort] = {"producers": producers, "consumers": consumers}
    return out


if __name__ == "__main__":
    print(f"opsimgforensics: {len(OPSIMGFORENSICS)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
    for sort, d in new_sorts().items():
        print(f"新語彙 {sort}: 産む {len(d['producers'])} {d['producers']} / "
              f"食う {len(d['consumers'])} {d['consumers']}")
    print("単入力の変換辺:", conversion_edges())
    print("optional 依存が要る op:", requires())
