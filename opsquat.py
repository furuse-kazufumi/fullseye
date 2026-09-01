# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsquat — fullseye 四元数画像 op の統一レジストリ。

動機(2026-09-01、ユーザーの問い)「複素数画像が使えるなら、**4 元数画像**も
使えたら面白いことができるか?」。fullseye 自身の在庫を実測すると:

  * ``pose_quat.py`` に四元数・双対四元数の関数が **28 個実在**するが、
    api / fullseye ファサードのどちらからも **1 つも引けない**(module-only)。
    3D 姿勢の代数はあるのに、画像の語彙には一度も届いていなかった。
  * 四元数「画像」は 3 つの在庫表面すべてで **0 件**。``riesz`` / ``monogenic``
    / ``hypercomplex`` / ``qft`` / ``clifford`` も登録名 1598 個に対して 0 件。

そこで **本質的な差がどこにあるか**を先に決めてから作った。複素数の画素は
2 次元値で回転軸が 1 本しかない。四元数の画素 ``(0,R,G,B)`` は 3 次元ベクトル
で、``q x conj(q)`` は**色空間内の 3 次元回転**になる。そして 2 次元信号の
「解析信号」は複素数の中には無く、**Riesz 変換の対**が要る = 値が四元数
(Clifford 数)になる。この 2 点だけが本物の能力差で、本レジストリはその台帳
(quatimage.py、19 op / 7 カテゴリ)。

来歴は公開文献のみ(docs/PROVENANCE.md の naming rule に従い、特定の製品・
企業を動機にも名前にも使わない): Felsberg & Sommer, IEEE TSP 49(12) 2001
(monogenic signal)/ Wadhwa, Rubinstein, Durand & Freeman, ICCP 2014
(Riesz pyramid による位相ベース増幅)/ Sangwine, Electronics Letters 32(21)
1996 + Ell & Sangwine, IEEE TIP 16(1) 2007(四元数フーリエ変換)/ Sangwine &
Ell, ICIP 1999(四元数相関)/ Mallick et al., CVPR 2005(鏡面不変部分空間)。

**正直な差し引き(全部実測、詳細は各 docstring)**:
  * 色回転 ``q x conj(q)`` は **3x3 直交行列と完全に同じ写像**。四元数が勝つ
    のは表現量(4 vs 9)と合成の閉性だけ(100k 回合成のドリフト実測: 四元数
    0.0 / 行列 4.4e-10)。**チャンネルごとの処理**に対しては原理的に勝つ
    (対角行列は零のチャンネルから何も作れない。灰色軸射影の最良対角近似は
    純赤画素で誤差 0.4714、本 op は 0.0)。
  * QFT は 3 回のチャンネル FFT の**線形再結合にすぎない**(実測 1.14e-13 で
    一致)。速くもならない(256x256 で **2.42 倍遅い**)。左右で別物なのは
    本物で、``side`` は既定値なしの必須引数にした。
  * Riesz 変位計測は雑音下で steerable の約 2 倍正確、1.2-2.1 倍速い。しかし
    **1 オクターブに複数方位の成分が入ると 13 % の静かな偏り**が出る
    (``motionmag.synthesize_translation`` の既定クリップがまさにそれ)。
    負けは負けとして ``riesz_displacement`` の表に書いてある。

既存資産との棲み分け(**再実装せず import して合成、あるいは明示的に非重複**):
  * 3D 姿勢の四元数代数 = pose_quat。``quat_color_rotate`` は
    ``axis_angle_to_quat`` で回転子を作り ``quat_to_hom_mat3d`` で行列にする =
    **import して使う**。28 関数のうち画素単位に効くのはこの 2 つ(+ 検証用の
    ``quat_compose`` / ``quat_conjugate`` / ``quat_rotate_point_3d``)だけで、
    残りは pose/dual-quat/screw = 剛体変換の語彙なので画像には出てこない。
  * 複素画像 = complexops(``cx_fft`` 系 / ``phase_unwrap``)。重複しない。
    2 次元の解析信号は複素数の中に**存在しない**というのが本モジュールの前提。
  * 位相ベース増幅の別解 = motionmag(complex steerable)。``band_snr`` を
    **import して呼ぶ**ので、2 つの増幅器は自分のコストを同じ物差しで報告する。
  * 二色性反射 = specularity。``quat_color_filter(mode="remove")`` は
    ``specular_free_transform`` と**同じ射影**なので **delegate する**
    (作り直さない。一致は偶然でなく構成による)。
  * 実数の方向づきエッジ応答 = ``backends_transform2.tf_steerable_filter``。
    直交対でなく位相を持たない別物。そのまま残す。

使い方:
    import opsquat
    opsquat.list_ops("riesz")
    q = opsquat.get("monogenic_signal")(image)
    opsquat.get("monogenic_orientation")(q)
"""
import quatimage

_MOD = {"quatimage": quatimage}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
#   既存語彙の再利用: image2d / rgbimage / video / table / pairs
#
# 既存語彙をそのまま使った判断(新語を作らなかったもの):
#   * image2d  — ``quat_norm`` / ``monogenic_amplitude`` / ``monogenic_phase``
#     / ``monogenic_orientation`` の返りは (H, W) の実マップ。既存の 2-D op
#     (閾値・morphology・blob・edge)が意味を持ったまま掛かる(「局所位相が
#     pi/2 付近 = ステップエッジ」を二値化して領域にする、が実際の使い道)。
#     [0,1] を超えるものがあるが image2d 語彙は元々そう。
#   * rgbimage — ``quaternion_to_rgb`` の返り。specularity と共有の (H,W,3)
#     線形 RGB そのもので、専用語を作ると二色性反射ファミリとの接続を切る。
#   * video / table / pairs — motionmag と同じ規約をそのまま踏襲。
#     ``riesz_displacement_series`` の (T,2) は dsp.spectrum へ直に流せる。
#
# 新語彙 1 つと、その理由(**既存では型レベルの嘘になる**もののみ追加。
# 先例 = opsphoton の histcube、opsoptics の jones/stokes、opsmotionmag の video):
#   * qimage — 四元数画像 ``(H, W, 4)`` float64、成分順 (w, x, y, z)。
#     既存で構造が近いのは rgbimage / pointmap / normalmap だが、いずれも
#     ``shape[2] == 3`` を要求するので **構造検査で弾かれる** = 相乗りは
#     そもそも不可能(型を分けるかどうかの問題ですらない)。voxel / video /
#     score は ndim==3 なので (H,W,4) を**受けてしまう**が、カタログのどの
#     op も qimage をそれらの型として宣言しないので混入経路が無い。逆向き
#     (voxel を qimage 欄へ)は shape[2]==4 で弾かれる。
#     **死んだ語彙にはならない**: 入口が 2 つ(``monogenic_signal`` /
#     ``riesz_transform`` が image2d から、``rgb_to_quaternion`` が rgbimage
#     から)、自己ループが 7 つ(共役・正規化・積・色回転・色フィルタ・QFT・
#     逆 QFT)、出口が 2 系統(``quaternion_to_rgb`` で rgbimage へ、
#     ``quat_norm`` / ``monogenic_*`` で image2d へ)。既存の最大プール
#     (image2d)から必ず埋まり、産物は必ず下流へ戻る。
#
# **プールの中身が 2 種類ある、という設計上の注意**(生成器のコメントも参照):
#     qimage には「モノジェニック信号 (band, R1, R2, 0)」と「色四元数
#     (0, R, G, B)」という意味の違う 2 種類が入る。構造は同じ (H,W,4) で、
#     取り違えても例外も NaN も出ない ―― 色画像を monogenic_orientation に
#     渡すと ``atan2(G, R)`` という**滑らかで完全にもっともらしい**方位マップ
#     が返る。そこで quatimage 側が k 成分(第 4 成分)で機械的に判定して
#     fail-closed する(``_require_monogenic``)。型を 2 つに割らなかったのは、
#     判定が**データから確実にできる**ため(色四元数の k = 青チャンネル = O(1)、
#     モノジェニック信号の k = 恒等的に 0)で、jones/stokes のように「長さが
#     同じで判定不能」な場合とは条件が違う。
_CATALOG = {
    "convert": [
        ("rgb_to_quaternion", "quatimage", ["rgbimage"], "qimage"),
        ("quaternion_to_rgb", "quatimage", ["qimage"], "rgbimage"),
        ("quat_norm", "quatimage", ["qimage"], "image2d"),
    ],
    "algebra": [
        ("quat_conjugate_image", "quatimage", ["qimage"], "qimage"),
        ("quat_normalize_image", "quatimage", ["qimage"], "qimage"),
        ("quat_image_multiply", "quatimage", ["qimage", "qimage"], "qimage"),
    ],
    "riesz": [
        ("riesz_transform", "quatimage", ["image2d"], "qimage"),
        ("monogenic_signal", "quatimage", ["image2d"], "qimage"),
        ("monogenic_amplitude", "quatimage", ["qimage"], "image2d"),
        ("monogenic_phase", "quatimage", ["qimage"], "image2d"),
        ("monogenic_orientation", "quatimage", ["qimage"], "image2d"),
    ],
    "color": [
        ("quat_color_rotate", "quatimage", ["qimage"], "qimage"),
        ("quat_color_filter", "quatimage", ["qimage"], "qimage"),
    ],
    "fourier": [
        ("qft2", "quatimage", ["qimage"], "qimage"),
        ("iqft2", "quatimage", ["qimage"], "qimage"),
    ],
    "motion": [
        ("riesz_motion_magnify", "quatimage", ["video"], "table"),
        ("riesz_displacement", "quatimage", ["video"], "table"),
        ("riesz_displacement_series", "quatimage", ["video"], "pairs"),
    ],
    "match": [
        ("quat_correlate", "quatimage", ["qimage", "qimage"], "qimage"),
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


OPSQUAT = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSQUAT.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し(ops3d / ops1d / opsmath / opsoptics /
#: opsphoton / opsmotionmag と同じ一級機構)。
#:
#: **現在は空 — 意図的に**。19 op すべてが宣言型そのもの(ndarray / dict /
#: (n,2) 配列)を素で返す設計にしてある。空にしておくと :func:`call` は
#: :func:`get` と同じ値を返し、連鎖ファザーの TYPEMISS 検査が**素の返りを
#: そのまま**宣言と突き合わせる = 検証が最も厳しい。
#:
#: opsmotionmag と同じ誘惑が 1 つある: ``riesz_motion_magnify`` は
#: ``{"video": ..., "snr_in": ..., ...}`` を返し、``"video"`` だけ取り出せば
#: video 型として下流へ流せる。**書かない**理由も同じで、増幅結果を SNR から
#: 切り離して受け取れる経路を作ることが「増幅の cost を benefit と同じ返り値で
#: 見せる」という約束を迂回する道になるため。video が欲しい下流は ``r["video"]``
#: と明示的に書く。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable、素の返り型)。宣言型が欲しければ :func:`call`。"""
    return OPSQUAT[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSQUAT[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSQUAT[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSQUAT.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsquat: {len(OPSQUAT)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
