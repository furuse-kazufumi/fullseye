# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsphoton — fullseye 光子計数・時間分解 op の統一レジストリ。

動機(2026-09-01)は fullseye 自身の空白の実測。**光子計数(photon counting)
と時間分解センシング(time-resolved sensing)** — 単一光子検出器で光子を 1 個ずつ
数え、その到達時刻から距離(dToF)や蛍光寿命(FLIM)を出す分野 — は
教科書がある成熟領域だが、fullseye は 1194 op を持ちながら
`photon` / `spad` / `tcspc` / `arrival` / `dtof` / `time_of_flight` の
いずれにも 1 件もヒットしなかった。つまり「画素値になる **前** の、
光子を 1 個ずつ数える世界」がまるごと空白だった。
本レジストリはその台帳(photoncount.py、17 op / 6 カテゴリ)。

来歴は公開文献のみ(docs/PROVENANCE.md の naming rule に従い、特定の製品・
企業を動機にも名前にも使わない):Anscombe 1948(分散安定化変換)/
Makitalo & Foi, IEEE TIP 2011(厳密不偏逆変換の閉形式)/ Coates,
J. Phys. E 1968(TCSPC パイルアップ補正)/ Knoll, *Radiation Detection and
Measurement*(デッドタイム 2 法則)/ Digman et al., Biophys. J. 2008
(phasor 表現と universal semicircle)。

既存資産との棲み分け(**再実装せず import して合成**):
  * ガウス読み出しノイズ = ``backends_aug.aug_read_noise``(加法・信号非依存)。
    こちらは**光子ショットノイズ**(分散 = 平均)。両者が出会う唯一の場所が
    ``anscombe_transform`` の一般化形で、``gain`` / ``read_sigma`` は
    aug_read_noise が注入するパラメータそのもの。
  * 正規化ショットノイズ増強 = ``backends_aug.aug_shot_noise``
    (``Poisson(v*K)/K`` を [0,1] にクリップして返す学習データ増強)。
    ``photon_sample`` は**カウントそのもの**を返す — Fano / Anscombe /
    Coates / dToF はすべて N が要るので、再スケール + クリップでは不可逆。
  * Poisson 逆畳み込み = ``volrestore.vol_richardson_lucy``。RL は
    **まさに本モジュールが生成する Poisson モデル下の最尤デブラー**なので
    合成関係にある(photon_sample / dtof_cube_simulate が光子制限データを作り、
    vol_gaussian_psf + vol_richardson_lucy が復元する)。ここでは一切デブラー
    しないし、あちらは一切サンプリングしない。
  * 光学設計(PSF / MTF / 回折 / 被写界深度)= optics。
    ``tcspc_irf_convolve`` はその**時間軸版**であり、空間側は複製しない。
  * 1-D 信号処理 = dsp / funct1d。到達時刻ヒストグラムは**そのまま
    ``signal``** なので、あちらの op が直接使える(ラップし直さない)。

使い方:
    import opsphoton
    opsphoton.list_ops("dtof")
    opsphoton.get("dtof_depth")(hist, bin_ps=100.0, mode="gaussian")
"""
import photoncount

_MOD = {"photoncount": photoncount}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
#   既存語彙の再利用: image2d / signal(1-D)/ depth / measurement(実スカラのみ)
#   / table(dict or list)
#
# 既存語彙をそのまま使った判断(新語を作らなかったもの):
#   * signal — 到達時刻ヒストグラム(bin ごとのカウント)と SPAD の計数レート列は
#     どちらも「1-D の標本化された関数」そのもの。dsp / funct1d の平滑化・
#     スペクトル・リサンプルがそのまま効く(実際に効かせたいので分けない)。
#     非負という物理制約は fail-closed の ValueError で守る — 語彙を分けるほどの
#     嘘ではない(負の値を持つ signal は「常に」拒否されるのではなく、非負の
#     signal は完全に正当な入力だから)。連鎖ファザーの signal 生成元は
#     正弦波(負値あり)なので CONTRACT になるが、``tcspc_simulate`` が
#     **0 引数で signal を産む**ため、そこから光子ヒストグラムが pool に入り
#     tcspc / dtof / lifetime 一族が実経路で回る(optics の airy_pattern と同型)。
#   * image2d — 光子カウント画像。整数値を float64 に載せた 2-D 配列であり、
#     既存の 2-D op(フィルタ・閾値・morphology)が意味を持ったまま使える。
#   * depth — dtof_cube_depth の返りは (H, W) の距離マップ = 既存の depth 語彙
#     そのもの。stereo / range_image 側の depth op へ直結する。
#   * measurement — dtof_depth は単一画素の距離(実スカラ)。
#   * table — 統計・フィット結果の dict。
#
# 新語彙 1 つと、その理由(**既存では型レベルの嘘になる**もののみ追加。
# 先例 = opsmath の cpoints / cscalar、opsoptics の jones / stokes、そして
# 何より pointmap / normalmap — 構造チェックが完全に同一((H,W,3) の float)
# でも意味が違うので別プールにした先例):
#   * histcube — 画素ごとの到達時刻ヒストグラム立方体 **(H, W, T)、時間軸が
#     最後**。既存の ``voxel`` は「3-D 配列」で TYPE_CHECKS も ndim == 3 だけ
#     なので構造上は通ってしまう。しかし voxel は **(D, H, W) の空間格子**で、
#     軸の意味が違う: (D,H,W) のボリュームを histcube として渡すと
#     dtof_cube_depth は W を時間軸と読み、**例外ではなく「もっともらしく
#     間違った深度マップ」**を返す(実測: 一様ボリュームで全画素 0.0075 m)。
#     これは pointmap / normalmap を分けたのと同じ判断で、分けないと
#     ファザーが voxel プールから立方体を流し込み、TYPEMISS も CONTRACT も
#     出ないまま無意味な深度が下流を汚す。なお flat な histcube は
#     dtof_cube_depth 側でも empty 判定して黙って通さない(二重防御)。
_CATALOG = {
    "counting": [
        ("photon_sample", "photoncount", ["image2d"], "image2d"),
        ("photon_statistics", "photoncount", ["image2d"], "table"),
        ("photon_uncertainty", "photoncount", ["image2d"], "image2d"),
    ],
    "transform": [
        ("anscombe_transform", "photoncount", ["image2d"], "image2d"),
        ("anscombe_inverse", "photoncount", ["image2d"], "image2d"),
    ],
    "spad": [
        ("spad_deadtime_apply", "photoncount", ["signal"], "signal"),
        ("spad_deadtime_correct", "photoncount", ["signal"], "signal"),
        ("tcspc_coates_correct", "photoncount", ["signal"], "signal"),
    ],
    "tcspc": [
        ("tcspc_simulate", "photoncount", [], "signal"),
        ("tcspc_irf_convolve", "photoncount", ["signal"], "signal"),
        ("tcspc_background_subtract", "photoncount", ["signal"], "signal"),
        ("tcspc_stats", "photoncount", ["signal"], "table"),
    ],
    "dtof": [
        ("dtof_depth", "photoncount", ["signal"], "measurement"),
        ("dtof_cube_simulate", "photoncount", ["depth"], "histcube"),
        ("dtof_cube_depth", "photoncount", ["histcube"], "depth"),
    ],
    "lifetime": [
        ("lifetime_fit", "photoncount", ["signal"], "table"),
        ("lifetime_phasor", "photoncount", ["signal"], "table"),
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


OPSPHOTON = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSPHOTON.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し(ops3d / ops1d / opsmath / opsoptics と同じ
#: 一級機構)。
#:
#: **現在は空 — 意図的に**。opsmath では ``mat_svd`` が数学慣習の
#: ``U, s, Vt = ...`` タプルを返すため adapter が要ったが、photoncount の 17 op は
#: すべて宣言型そのもの(ndarray / dict / float)を素で返す設計にしてある
#: (例: ``tcspc_stats`` は「(peak, centroid, fwhm) タプル」ではなく dict を返す)。
#: 空にしておくと :func:`call` は :func:`get` と同じ値を返し、連鎖ファザーの
#: TYPEMISS 検査が**素の返りをそのまま**宣言と突き合わせる = 検証が最も厳しい。
#: タプル返しの op を将来足すならここに登録すること(空欄を埋めるために既存の
#: 返り型をタプルへ変える、は本末転倒なのでしない)。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable、素の返り型)。宣言型が欲しければ :func:`call`。"""
    return OPSPHOTON[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSPHOTON[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSPHOTON[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSPHOTON.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsphoton: {len(OPSPHOTON)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
