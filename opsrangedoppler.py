# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsrangedoppler — fullseye コヒーレント測距 op の統一レジストリ。

動機(2026-09-01)は fullseye 自身の空白の実測。`docs/INDUSTRY_SIGNALS.md` の
在庫確認を 3 表面(型付きカタログ + 進化レジストリ / api.py / ソース全体の
静的 def 走査)すべてで回したところ、**`doppler` / `radar` / `beamform` /
`delay_and_sum` はどの表面でも 0 件**だった。既存の `lidar_scan` /
`pseudo_lidar` はレイキャストの**幾何**しか持たず、信号処理層が丸ごと空で、
その結果 **速度が「不正確」なのではなく「表現できない」**状態だった。
本レジストリはその層の台帳(rangedoppler.py、8 op / 4 カテゴリ)。

来歴は公開文献と教科書のみ(docs/PROVENANCE.md の naming rule に従い、特定の
製品・企業を動機にも名前にも使わない):B. R. Mahafza, *Radar Systems Analysis
and Design*, CRC / M. A. Richards, *Fundamentals of Radar Signal Processing*,
McGraw-Hill(FMCW のビート周波数とレンジ-ドップラー処理)/ H. L. Van Trees,
*Optimum Array Processing*, Wiley 2002(遅延和ビームフォーミングとビーム幅)/
F. J. Harris, *Proc. IEEE* 66(1):51-83, 1978(窓関数とサイドローブ)。

既存資産との棲み分け(**再実装せず import して合成**):
  * レイキャストの幾何 = lidar_sim / pseudo_lidar。あちらは「どこに面が
    あるか」、こちらは「その距離と速度がコヒーレントセンサでどんな信号に
    なるか」。距離は**入力として与えられる**もので、ここでは一本も光線を
    飛ばさない。
  * 直接飛行時間(dToF)= photoncount(`dtof_*` / `tcspc_*`)。同じ「距離」を
    **逆の原理**で出す。棲み分けの実測は下の型語彙の節を参照。
  * 1-D 信号処理 = dsp / funct1d。`fmcw_range_profile` と
    `beamform_delay_sum` の返りは**素の 1-D float64**なので、あちらの op が
    そのまま使える(ラップし直さない)。
  * 2-D 画像処理 = fullseye 本体。レンジ-ドップラーマップを **image2d** で
    宣言しているのは意図で、閾値・morphology・ラベリング・blob 計測は
    まさに CFAR 検出器の部品そのものであり、既に存在する。

使い方:
    import opsrangedoppler
    opsrangedoppler.list_ops("process")
    opsrangedoppler.get("fmcw_design")(n_samples=128, n_chirps=64)
"""
import rangedoppler

_MOD = {"rangedoppler": rangedoppler}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
#   既存語彙の再利用: image2d / signal / table
#   新語彙: beatcube(理由は下記)
#
# --------------------------------------------------------------------------
# 既存語彙をそのまま使った判断(新語を作らなかったもの)
# --------------------------------------------------------------------------
#   * image2d — レンジ-ドップラーマップ。(n_doppler, n_range) の実 2-D 配列で、
#     **軸の意味が違っても既存 2-D op の意味は壊れない**: 閾値・morphology・
#     ラベリング・blob 計測は「マップ上の輝点を拾う」ことそのもので、これは
#     CFAR 検出器の作り方と一致する。histcube を voxel から分けたときの物差し
#     (「渡すと例外でなく**もっともらしく間違った答え**が返るか」)を当てると、
#     こちらは「返る答えが正しい」側に倒れる。加えて image2d は本 repo で最大の
#     プールなので、beatcube という新語彙の**最も広い出口**になる(下記)。
#   * signal — 角度スペクトルとレンジプロファイル。どちらも 1-D の実配列で、
#     dsp.find_peaks / funct1d.smooth_funct_1d_gauss がそのまま意味を持つ。
#     counts(非負・光子カウント)のような追加の物理制約が無いので、
#     signal プール(負値を含む正弦波)を渡しても型レベルの嘘にならない
#     — 実際 range_doppler_peaks は非負を要求するが、こちらは要求しない。
#   * table — 設計値・検出結果・DOA 結果の dict。TYPE_CHECKS の table は
#     list|dict なので該当。
#
# --------------------------------------------------------------------------
# 新語彙 1 つと、その理由
# --------------------------------------------------------------------------
# 追加の基準は一貫して「**既存語彙で宣言すると型レベルの嘘になるか**」。
# 先例 = opsmath の cpoints / cscalar、opsoptics の jones / stokes、
# opsphoton の counts / countrate / histcube。
#
#   * beatcube — FMCW のビート立方体: **(n_antennas, n_chirps, n_samples) の
#     complex 配列**で、アンテナ / 低速時間(チャープ)/ 高速時間(サンプル)。
#     既存語彙に乗せられない理由は 3 つあり、いずれも実測に基づく:
#
#       (a) **3-D の complex 語彙が既存に無い**。cimage は 2-D complex
#           (TYPE_CHECKS が ndim == 2)なので構造からして入らない。voxel /
#           sdf / score / labels は ndim == 3 だけを見るので**述語は通って
#           しまう**(実測: beatcube は voxel / sdf / labels / pairs / score の
#           5 述語を同時に満たす)が、これは qimage が
#           「voxel / sdf / labels / video / score / histcube の述語も同時に
#           満たす」のと同じ状況で、**プールは宣言型の名前で引かれる**ので
#           分離は成立する。実配列を期待する voxel 系 op に complex を渡すと
#           大半は生の TypeError か暗黙の abs になり、どちらも望ましくない。
#
#       (b) **histcube(dToF)と共有してはいけない**。同じ「距離」を返すが
#           原理が逆で、実測でも両方向とも危険:
#             - 素の状態では **両方向とも fail-closed が効く**。complex な
#               beatcube を dtof_cube_depth に渡すと photoncount 側の
#               `_as_float_array` が complex を拒否し、実の histcube を
#               range_doppler_map に渡すとこちら側が real を拒否する。
#             - しかし **キャスト 1 回で破れる**。`np.abs(beatcube)` を
#               dtof_cube_depth に渡すと例外なく深度マップ(実測 0.0150-1.2142 m)
#               が返り、`histcube.astype(complex)` を range_doppler_map に
#               渡すと例外なくマップ(実測 26.74-2265.5)が返る。どちらも
#               「もっともらしく間違った答え」で、dtype の検査だけでは
#               連鎖ファザーの型接続としては守れない。よって**宣言型で分ける**
#               — histcube を voxel から分けたのとまったく同じ判断。
#           物理的にも別物: histcube は**非負の光子カウント**で位相を持たず、
#           速度軸が存在しない。beatcube は**位相を持つ複素振幅**で、単一光子を
#           数えることはできない。片方をもう片方として宣言するのは嘘である。
#
#       (c) **実 (real) を受け付けない**という契約がこの型の本体。実サンプリング
#           のビートスペクトルは共役対称なので、**すべての標的が 2 回現れる**:
#           本来の位置と、レンジ bin (N_s - k) という**でっち上げの距離**に
#           速度の符号を反転して現れる幽霊。実測: レンジ bin 10 / 速度 bin +4 の
#           標的は (10,+4) と (54,-4) に**どちらも振幅ちょうど 0.5**で立ち、
#           マップ上でどちらが本物かを見分ける材料は何も無い。
#           ★訂正の記録: 本モジュールの初稿は「real では速度の符号が失われる」と
#           書いていたが、それは**誤り**だった(レンジ軸だけの 1-D 実信号では
#           正しいが、2 軸そろうと符号は保持される)。テストが先に破れて発覚した。
#           実際に失われるのは「対のどちらが本物か」と、振幅の半分と、
#           一意測距範囲の半分である。`_as_beat_cube` が dtype 段階で拒否し、
#           直し方(解析信号を明示的に作る)を名指しする。
#
# --------------------------------------------------------------------------
# 狭い sort にしないための入口と出口(実測済みの教訓への対処)
# --------------------------------------------------------------------------
# 本 repo は 2 つの罠を実際に踏んでいる: ① 産む op が無い型は永久に到達不能
# (score が 434 op 中ただ 1 件の blocked だった件)、② 既存プールに相乗り
# させると毎回 fail-closed で弾かれ「発見ゼロ」に見える(photon 族 7/17 が
# 未実行だった件)。beatcube は両方に手当てしてある:
#
#   入口(beatcube を産む op)  : fmcw_beat_simulate(引数のみ、入力型なし)
#                                fmcw_window_apply(beatcube -> beatcube)
#   出口(既存 sort へ戻る op)  : range_doppler_map   -> image2d(最大プール)
#                                fmcw_range_profile  -> signal
#                                beamform_delay_sum  -> signal
#                                beamform_doa        -> table
#
# 入口が「引数だけの源」である点は tcspc_simulate(入力型なし -> counts)と
# 同じ形なので、連鎖ファザーには counts と同様に **専用の生成器**が要る
# (親への申し送り事項。生成器の実体は報告に実行確認済みで載せてある)。
# 出口は image2d と signal という本 repo で最大級のプール 2 つに落ちるので、
# jones(2 op)や countrate(2 op)のような閉じた狭い sort にはならない。
_CATALOG = {
    "design": [
        ("fmcw_design", "rangedoppler", [], "table"),
    ],
    "simulate": [
        ("fmcw_beat_simulate", "rangedoppler", [], "beatcube"),
    ],
    "process": [
        ("fmcw_window_apply", "rangedoppler", ["beatcube"], "beatcube"),
        ("range_doppler_map", "rangedoppler", ["beatcube"], "image2d"),
        ("range_doppler_peaks", "rangedoppler", ["image2d"], "table"),
        ("fmcw_range_profile", "rangedoppler", ["beatcube"], "signal"),
    ],
    "beamform": [
        ("beamform_delay_sum", "rangedoppler", ["beatcube"], "signal"),
        ("beamform_doa", "rangedoppler", ["beatcube"], "table"),
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


OPSRANGEDOPPLER = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSRANGEDOPPLER.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し(ops3d / ops1d / opsmath / opsoptics /
#: opsphoton と同じ一級機構)。
#:
#: **現在は空 — 意図的に**。opsmath では ``mat_svd`` が数学慣習の
#: ``U, s, Vt = ...`` タプルを返すため adapter が要ったが、rangedoppler の 8 op は
#: すべて宣言型そのもの(ndarray / dict)を素で返す設計にしてある(例:
#: ``range_doppler_peaks`` は「(range, velocity) タプルの列」ではなく dict を
#: 返し、``beamform_doa`` も角度リストではなく dict を返す)。空にしておくと
#: :func:`call` は :func:`get` と同じ値を返し、連鎖ファザーの TYPEMISS 検査が
#: **素の返りをそのまま**宣言と突き合わせる = 検証が最も厳しい。タプル返しの
#: op を将来足すならここに登録すること(空欄を埋めるために既存の返り型を
#: タプルへ変える、は本末転倒なのでしない)。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable、素の返り型)。宣言型が欲しければ :func:`call`。"""
    return OPSRANGEDOPPLER[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSRANGEDOPPLER[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSRANGEDOPPLER[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSRANGEDOPPLER.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsrangedoppler: {len(OPSRANGEDOPPLER)} ops / "
          f"{len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
    for c in categories():
        print(f"  [{c}] {len(list_ops(c))} ops")
