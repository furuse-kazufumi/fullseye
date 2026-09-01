# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsacoustics — fullseye 音響状態監視・音響指標 op の統一レジストリ。

動機(2026-09-01)はユーザーの一言 —「1D が扱えるなら音響データも扱えるよね」—
と、それを受けた **fullseye 自身の空白の実測**。`dsp.py` には音声 I/O
(`read_wav` / `read_audio` / `write_wav`)と基本 DSP(`spectrum` /
`spectrogram` / `lowpass` / `highpass` / `bandpass` / `envelope` / `rms` /
`find_peaks` / `signal_features` / `resample` / `zero_crossing_rate`)が
**既にあった**。だが登録名 1661 個に対し `stft` / `mel` / `mfcc` / `octave` /
`acoust` / `beamform` は**どの表面にも 1 件もヒットしなかった**。
つまり「扱える」は素材の話までで、**現場で使う道具になっていなかった**。

現場が音に対して実際に投げる問いは、生スペクトルより狭くて難しい:

  * **どの欠陥か。** 転がり軸受の外輪剥離は欠陥周波数で鳴らない。数 kHz の
    構造共振が、200 Hz 以下の欠陥周波数で**振幅変調**されて届く。欠陥周波数は
    生スペクトルには**成分として存在しない**(実測: 生振幅 4.3e-16)。
    包絡線スペクトルで初めて立つ(実測: ピーク 107.000000 Hz、振幅 0.499677)。
  * **そのピークは次数か共振か。** 回転数が動けば次数は滲み、共振は残る。
    角度領域へリサンプルすると立場が厳密に逆転する(実測: 次数 3.5 の振幅は
    通常スペクトルで 0.070203 / 次数スペクトルで 0.999371)。
  * **何 dB か、誰の定義で。** 基準値と周波数重み付けを言わない dB は無意味。
  * **その振動はこの加振から来たのか。** 2 チャネル、伝達関数、そして
    その答えをどこまで信じてよいかを言うコヒーレンス。

本レジストリはその台帳(acoustics.py、19 op / 6 カテゴリ)。

来歴は公開文献のみ(docs/PROVENANCE.md の naming rule に従い、特定の製品・
企業を動機にも名前にも使わない):Allen & Rabiner, Proc. IEEE 65(11) 1977 +
Griffin & Lim, IEEE TASSP 32(2) 1984(STFT と重み付き重畳加算の厳密逆)/
Darlow, Badgley & Hogg 1974 + Randall & Antoni, MSSP 25(2) 2011(高周波共振
=包絡線解析)/ Harris, *Rolling Bearing Analysis*(軸受欠陥運動学。数表では
なく幾何から導出)/ Fyfe & Munck, MSSP 11(2) 1997(角度リサンプルによる
計算次数追跡)/ Bogert, Healy & Tukey 1963 + Randall, MSSP 97 2017
(ケプストラム)/ Antoni, MSSP 20(2) 2006(スペクトル尖度)/ Welch,
IEEE TAE 15(2) 1967 + Bendat & Piersol, *Random Data*(Welch 平均・H1/H2・
コヒーレンス)。オクターブ帯域と A/C 特性は**定義式から計算**しており、
規格の数表は 1 つも転記していない(A(1000) が厳密に 0.0 になるのは、
公表オフセット定数を足すのではなく自身の 1 kHz 値で割っているため)。

既存資産との棲み分け(**再実装せず import して合成**):
  * 音声 I/O・Butterworth・生スペクトル・spectrogram・Hilbert 包絡線・RMS・
    リサンプル・ピーク検出 = **dsp**。1 つも作り直していない:
    ``envelope_spectrum`` は ``dsp.bandpass`` と ``dsp.envelope`` を呼び、
    ``order_spectrum`` の主張は ``dsp.spectrum`` との**比較**で立てている。
    本モジュールが足すのは dsp が止まっている先 — 可逆 STFT、復調、次数追跡、
    ケプストラム、分数オクターブ、重み付け曲線、2 チャネル推定。
  * 汎用 1-D 関数代数(平滑・微分・積分・零交差・マッチング)= **funct1d**。
    本モジュールの返す配列は素の 1-D float64 なので、そのまま食える。
  * **motionmag は「同じ物理量(微小振動)をカメラで測る」経路**。
    あちらの観測量は向きつきサブ帯域の局所位相で答えは画素変位、こちらの
    観測量は音圧で答えは Hz の変調率。補完関係であって重複ではない。
    ``motionmag.displacement_series`` の返り ``(T, 2)`` は普通の 1-D 信号
    なので、その列を ``stft`` / ``cepstrum`` / ``envelope_spectrum`` に流せば
    **カメラが見た振動をこの台帳の道具で解析できる**。240 fps のカメラは
    120 Hz まで、48 kHz のマイクは 24 kHz まで — 軸受が実際に鳴る構造共振に
    届くのは後者だけで、だから軸受診断は音響の問題、モード形状の可視化は
    光学の問題になる。
  * **rangedoppler は「コヒーレント狭帯域 RF」のアレイ処理**(複素ベースバンド
    ビートキューブ、搬送波長、単一波長の位相ランプで作る操舵ベクトル)。
    **音響ビームフォーマは意図的にここに置いていない**。広帯域実信号の
    マイクアレイは別レジーム(操舵遅延が素子ごとの位相 1 個ではなく
    非整数サンプル遅延になる)で、互換性のない 2 つ目のビームフォーマを
    repo に足すのは 0 個より悪い。将来やるなら**既存の隣に置いて操舵行列を
    共有する**のが筋。
  * fail-closed のスカラ検証・サイズ上限・範囲外拒否の流儀 = **photoncount**
    (``dtof_cube_simulate`` の「一意測距範囲を超えたら拒否」に対応するのが
    本モジュールの「Nyquist を超える搬送波・側波帯・次数は折り返さず拒否」)。

使い方:
    import opsacoustics
    opsacoustics.list_ops("bearing")
    x = opsacoustics.get("synthesize_bearing_signal")(25600.0, 1.0, 3000.0, 107.0)
    opsacoustics.get("envelope_spectrum")(x, 25600.0, 2000.0, 4000.0)["peak_freq"]
"""
import acoustics

_MOD = {"acoustics": acoustics}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
#   既存語彙の再利用のみ: signal / table / measurement
#
# --------------------------------------------------------------------------
# 新語彙は 1 つも作っていない。その判断の実測根拠
# --------------------------------------------------------------------------
# 判定基準は本 repo で一貫している「**既存語彙で宣言すると型レベルの嘘になるか**」
# = 混ぜたときに例外が出るのか、**もっともらしく間違った数字が返る**のか。
# 後者なら分ける(opsphoton の counts / histcube、opsmotionmag の video、
# opsoptics の jones / stokes が先例)。音響でこれを当てると **分けない**に
# 倒れる。理由は 3 つあり、どれも実測。
#
#   1. **任意の実数 1-D は本当に正当な音響信号である。** counts は「負の
#      光子数はあり得ない」ので signal を渡すと必ず CONTRACT になり、photon 族が
#      一度も実行されなかった。音響にはその制約が無い: ファザーの signal
#      (正弦 + 雑音 256 点、負値あり)を rate=100 / low=0.05 / high=0.2 の
#      既存 PARAM_HINTS で **signal を取る 18 op 全部に流して実測**したところ、
#      **型に起因する拒否も NONFINITE 漏れも 1 件も出なかった**
#      (負値も正値も音圧・加速度として正当だから)。「任意の signal を
#      音響信号として渡せる」は嘘ではない ― 本当にそうなのである。
#      残る 1 op(``istft``)だけが signal を拒否するが、これは型語彙の問題では
#      なく「幾何と窓を失った複素行列は逆変換できない」という内容の話で、
#      宣言も ``["table"]`` にしてある(先例 =
#      ``complex_steerable_reconstruct`` が table -> image2d)。
#
#   2. **危険なのは配列ではなく `rate` という別のスカラである。** 取り違えの
#      本体は「25600 Hz の記録を 48000 Hz として読む」であって、これは
#      **ndarray の型では原理的に防げない**(サンプリング周波数は配列の中に
#      入っていない)。実測: 正しい軸受記録に偽の rate を渡すと欠陥周波数の
#      報告が 107.0000 Hz -> 200.6250 Hz へ動き、A 特性 Leq も最大 1/3
#      オクターブ帯域も全部動くが、**例外も NaN も出ない**。専用型を作っても
#      これは防げず、既存 dsp / funct1d 1-D 族との接続を切る損だけが残る。
#      防御はスカラ側に置いた:
#      ``_finite_scalar`` が rate の str / bool / complex を **拒否**する
#      (``float("16000")`` は成功してしまうので、これが無いと未パースの設定値が
#      サンプリング周波数として通り抜け、以後の全周波数・全次数・全 dB が
#      未知の係数で狂ったまま、例外はどこにも出ない)。
#
#   3. **軸の意味が違う 1-D は、そもそも pool に入れていない。**
#      ``angular_resample`` が返すのは**角度**で添字づけられた列で、これを
#      ``rate`` を取る op に渡せば「回転数で測った軸から Hz が出る」=
#      例外も NaN も無く間違った数字が返る。opsphoton が histcube を voxel から
#      分けたのと同じ状況だが、ここでは**新語を作る代わりに table に包んで
#      素の signal として流通させない**という手を採った(先例 =
#      ``motionmag.motion_magnify`` が video アダプタを意図的に置かないこと)。
#      新語 1 つと狭い sort を増やすより、危険な産物を pool に出さないほうが
#      安い。dict の中の ``["signal"]`` を取り出すのは呼び出し側の明示的な行為
#      になり、そのとき ``samples_per_rev`` が同じ dict にある。
#
# 既存語彙をそのまま使った内訳:
#   * signal — 波形、重み付け後の波形、重み付け曲線(dB 配列)。すべて
#     1-D float64 で、dsp / funct1d の op が意味を保ったまま掛かる。
#   * table  — STFT(complex 行列 + 幾何 + 窓。これを 1 個の配列に潰すと
#     istft が不可能になる)、スペクトル系の (freqs, magnitude, peak…) 一式、
#     軸受運動学の 4 レート、角度領域記録、帯域定義、統計レベル、
#     2 チャネル推定(応答とコヒーレンスは**必ず一緒に読む**べきもので、
#     切り離せる経路を作らない ― opsmotionmag が SNR を増幅結果から
#     切り離さないのと同じ理由)。
#   * measurement — ``equivalent_level`` は実スカラ 1 個(dB)。
#
# 入口と出口(死んだ語彙にならないことの確認):
#   入口 = ``synthesize_bearing_signal``([] -> signal)が既知の答えを持つ
#   波形を産み、``synthesize_speed_ramp``([] -> table)が速度プロファイル付きの
#   走行記録を産む。自己ループ = ``apply_weighting``(signal -> signal)。
#   出口 = ``istft``(table -> signal)と ``weighting_response``
#   (signal -> signal)が table / signal の間を往復し、
#   ``equivalent_level``(signal -> measurement)が既存の測定値族へ落ちる。
#   さらに ``stft`` -> ``istft`` は**厳密往復**なので、プール内で不変量が回る。
_CATALOG = {
    "transform": [
        ("stft", "acoustics", ["signal"], "table"),
        ("istft", "acoustics", ["table"], "signal"),
        ("stft_cola_check", "acoustics", [], "table"),
    ],
    "synthesis": [
        ("synthesize_bearing_signal", "acoustics", [], "signal"),
        ("synthesize_speed_ramp", "acoustics", [], "table"),
    ],
    "bearing": [
        ("envelope_spectrum", "acoustics", ["signal"], "table"),
        ("bearing_defect_frequencies", "acoustics", [], "table"),
        ("spectral_kurtosis", "acoustics", ["signal"], "table"),
        ("cepstrum", "acoustics", ["signal"], "table"),
    ],
    "order": [
        ("angular_resample", "acoustics", ["signal"], "table"),
        ("order_spectrum", "acoustics", ["signal"], "table"),
    ],
    "level": [
        ("octave_bands", "acoustics", [], "table"),
        ("octave_spectrum", "acoustics", ["signal"], "table"),
        ("weighting_response", "acoustics", ["signal"], "signal"),
        ("apply_weighting", "acoustics", ["signal"], "signal"),
        ("equivalent_level", "acoustics", ["signal"], "measurement"),
        ("percentile_level", "acoustics", ["signal"], "table"),
    ],
    "dual": [
        ("coherence", "acoustics", ["signal", "signal"], "table"),
        ("transfer_function", "acoustics", ["signal", "signal"], "table"),
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


OPSACOUSTICS = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSACOUSTICS.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し(ops3d / ops1d / opsmath / opsoptics /
#: opsphoton / opsmotionmag と同じ一級機構)。
#:
#: **現在は空 — 意図的に**。19 op すべてが宣言型そのもの(ndarray / dict /
#: float)を素で返す設計にしてある。空にしておくと :func:`call` は :func:`get`
#: と同じ値を返し、連鎖ファザーの TYPEMISS 検査が**素の返りをそのまま**宣言と
#: 突き合わせる = 検証が最も厳しい。
#:
#: 埋めたくなる誘惑が 2 つあるので明記しておく。
#:
#: 1. ``angular_resample`` は ``{"signal": ..., "samples_per_rev": ...}`` を
#:    返し、その ``"signal"`` だけ剥がせば signal 型として下流へ流せる。
#:    **それを書かない**のは、剥がした配列が**角度で添字づけられている**ため。
#:    ``rate`` を取る op に渡すと例外も NaN も無しに「回転数の軸から Hz」を
#:    返す。opsphoton が histcube を voxel から分けた理由と同じ危険を、
#:    こちらは「pool に出さない」で塞いでいる。
#: 2. ``transfer_function`` は ``response`` と ``coherence`` を同じ dict で
#:    返す。応答だけ剥がす adapter は、**H2 推定が 100 % 外れていても
#:    5.04 という数字は何もおかしく見えない**(実測、真値 2.5)という
#:    この族の中心的な正直さを迂回する道になる。
#:
#: タプル返しの op を将来足すならここに登録すること(空欄を埋めるために既存の
#: 返り型をタプルへ変える、は本末転倒なのでしない)。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable、素の返り型)。宣言型が欲しければ :func:`call`。"""
    return OPSACOUSTICS[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSACOUSTICS[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSACOUSTICS[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSACOUSTICS.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsacoustics: {len(OPSACOUSTICS)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
    for c in categories():
        print(f"  [{c}] {len(list_ops(c))} ops")
