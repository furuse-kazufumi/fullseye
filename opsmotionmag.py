# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsmotionmag — fullseye モーション増幅・位相変位計測 op の統一レジストリ。

動機(2026-09-01)は fullseye 自身の空白の実測。**モーション増幅(motion
magnification)と位相ベースの微小変位計測** — 見えないほど小さい振動を、
帯域通過した局所位相を α 倍して「見えるように再合成」し、あるいは
「何ピクセルか」を数値で返す分野 — は 2012 年と 2013 年の公開論文が確立した
成熟領域だが、fullseye は 1194 op を持ちながら `magnif` / `eulerian` /
`riesz` のいずれにも 1 件もヒットしなかった(`docs/INDUSTRY_SIGNALS.md` §3 の
3 表面実測)。既存の `tf_steerable_filter` は**位相を持たない実数の
エッジ応答**、`optical_flow_*` は**1 画素以上の運動を推定する別レジーム**で、
どちらも「増幅」ではない。本レジストリはその台帳(motionmag.py、9 op /
4 カテゴリ)。

来歴は公開文献のみ(docs/PROVENANCE.md の naming rule に従い、特定の製品・
企業を動機にも名前にも使わない): Freeman & Adelson, IEEE PAMI 13(9) 1991
(steerable filters)/ Simoncelli & Freeman, ICIP 1995 + Portilla &
Simoncelli, IJCV 40(1) 2000(steerable pyramid)/ Wu, Rubinstein, Shih,
Guttag, Durand & Freeman, ACM TOG 31(4) 2012(時間帯域通過による
Eulerian 増幅)/ Wadhwa, Rubinstein, Durand & Freeman, ACM TOG 32(4) 2013
(振幅でなく**位相**を増幅する)。

既存資産との棲み分け(**再実装せず import して合成、あるいは明示的に非重複**):
  * フレーム列の型と約束 = videops。``(T, H, W)`` float64、2-D フレームの
    list も受ける、という規約は**そのまま踏襲**した(motionmag 側の
    ``_require_video`` は同じ契約にサイズ上限と complex/masked 拒否を足した
    だけ)。videops の ``moving_average`` / ``spatiotemporal_gaussian`` は
    低域通過で、``temporal_bandpass`` は**同じ族の帯域選択メンバ**。重複しない。
  * 密なオプティカルフロー = flow(``optical_flow_lk`` / ``optical_flow_hs``)。
    こちらは 1 画素以上の運動と独立運動体が守備範囲。motionmag は
    **帯域制限された成分のサブピクセル変位**で、レジームが違う。
    motionmag は flow を一度も呼ばないし、flow の再実装もしない。
  * フローの解釈(全体運動モデル・残差・分割)= motion。無関係、不変。
  * FFT / complex 画像の一般配管 = complexops(``cx_fft`` 系 /
    ``phase_unwrap`` / ``cx_wiener_deconvolve``)、FFT 畳み込み・相関 =
    filters_freq。どちらも再実装しない。ステアラブル束だけは numpy.fft の上に
    自前で組んである — **tight frame でないと再合成が厳密にならない**ためで、
    厳密さがこのモジュールの契約そのもの。
  * 実数の方向づきエッジ応答 = ``backends_transform2.tf_steerable_filter``。
    直交対でなく位相を持たず可逆でもないので増幅には使えない。別物として
    そのまま残す。
  * 1-D 信号処理・スペクトル = dsp / funct1d。``displacement_series`` の返り
    ``(T, 2)`` はそのまま ``dsp.spectrum`` に流せる(共振周波数が読める)ので、
    ラップし直さない。

使い方:
    import opsmotionmag
    opsmotionmag.list_ops("magnify")
    v = opsmotionmag.get("synthesize_translation")()
    r = opsmotionmag.get("motion_magnify")(v, 8.0, 3.0, 5.0, 32.0)
    r["video"], r["image_snr_change_db"], r["motion_snr_out_db"]
"""
import motionmag

_MOD = {"motionmag": motionmag}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
#   既存語彙の再利用: image2d / table / pairs
#   新語彙: video(理由は下記)
#
# 既存語彙をそのまま使った判断(新語を作らなかったもの):
#   * image2d — ``temporal_band_power`` の返りは (H, W) の実マップ。既存の
#     2-D op(閾値・morphology・blob)が意味を持ったまま掛かる(「どこが何 Hz
#     で振動しているか」の地図を二値化して領域にする、が実際の使い道)。
#     [0,1] を超えるが image2d 語彙は元々そう(videops の motion_energy と同じ)。
#   * table — 分解結果 dict、SNR 計測 dict、増幅結果 dict、変位場 dict。
#     TYPE_CHECKS の table は list|dict なのでどれも該当する。
#   * pairs — ``displacement_series`` の返りは (T, 2) の (dx, dy)。
#     funct1d / dsp.spectrum / opsoptics の MTF 曲線と同じ「(n,2) 配列」規約
#     そのもので、専用語を作ると 1-D 族との接続を切るだけで得が無い。
#
# 新語彙 1 つと、その理由(**既存では型レベルの嘘になる**もののみ追加。
# 先例 = opsphoton の histcube、opsoptics の jones/stokes):
#   * video — フレーム列 ``(T, H, W)``、T が**時間軸**で fps が付随する。
#     既存 ``voxel`` は ndim==3 という同じ構造検査を通り、生成器
#     (16³ のボール)も値域 [0,1] の有限配列なので**弾かれない** — つまり
#     相乗りさせても「毎回 fail-closed で一度も実行されない」死に方はしない。
#     しかしそれは救いではなく罠で、voxel を渡すと ``motion_magnify`` は
#     例外も NaN も出さずに**意味の無い数値を静かに返す**(z 軸を時間と
#     読み替え、呼び出し側が渡した fps がどこにも対応しない)。これは
#     opsphoton が histcube を voxel から分けたときの判断基準
#     (「voxel を渡すと黙って間違った深度が出る」)と**同じ物差しで同じ答え**
#     になる。
#     死んだ語彙にはならない: ``synthesize_translation`` が video を産む
#     入口 op として台帳に載っており(photoncount の ``tcspc_simulate`` が
#     counts / histcube の入口であるのと同じ構図)、``temporal_bandpass`` が
#     video → video で連鎖を伸ばし、``temporal_band_power`` が
#     video → image2d で既存 2-D 族へ、``displacement_series`` が
#     video → pairs で既存 1-D 族へ橋を架ける。**入口・自己ループ・2 つの
#     出口**が揃っているので、プールは必ず埋まり、産物は必ず下流へ流れる。
_CATALOG = {
    "synthesis": [
        ("synthesize_translation", "motionmag", [], "video"),
    ],
    "decompose": [
        ("complex_steerable_decompose", "motionmag", ["image2d"], "table"),
        ("complex_steerable_reconstruct", "motionmag", ["table"], "image2d"),
    ],
    "temporal": [
        ("temporal_bandpass", "motionmag", ["video"], "video"),
        ("temporal_band_power", "motionmag", ["video"], "image2d"),
        ("band_snr", "motionmag", ["video"], "table"),
    ],
    "magnify": [
        ("motion_magnify", "motionmag", ["video"], "table"),
    ],
    "measure": [
        ("phase_displacement", "motionmag", ["video"], "table"),
        ("displacement_series", "motionmag", ["video"], "pairs"),
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


OPSMOTIONMAG = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSMOTIONMAG.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し(ops3d / ops1d / opsmath / opsoptics /
#: opsphoton と同じ一級機構)。
#:
#: **現在は空 — 意図的に**。9 op すべてが宣言型そのもの(ndarray / dict /
#: (n,2) 配列)を素で返す設計にしてある。空にしておくと :func:`call` は
#: :func:`get` と同じ値を返し、連鎖ファザーの TYPEMISS 検査が**素の返りを
#: そのまま**宣言と突き合わせる = 検証が最も厳しい。
#:
#: 埋めたくなる誘惑が 1 つあるので明記しておく: ``motion_magnify`` は
#: ``{"video": ..., "snr_in": ..., ...}`` という dict を返し、その ``"video"``
#: だけを取り出せば video 型として下流へ流せる。**それをここに書かない**のは、
#: 増幅結果を SNR から切り離して受け取れる経路を作ることが、このモジュールの
#: 中心的な正直さの約束(「増幅の costを benefit と同じ返り値で見せる」)を
#: 迂回する道になるため。video を欲しい下流は ``r["video"]`` と明示的に書く。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable、素の返り型)。宣言型が欲しければ :func:`call`。"""
    return OPSMOTIONMAG[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSMOTIONMAG[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSMOTIONMAG[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSMOTIONMAG.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsmotionmag: {len(OPSMOTIONMAG)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
