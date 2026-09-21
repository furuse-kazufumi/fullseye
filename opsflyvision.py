# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsflyvision — fullseye ハエ視覚経路(視葉)op の統一レジストリ。

動機(2026-09-13): fullseye は視覚系の**設計**側(optics / visiondesign)と
点群・姿勢・シーンフローの**処理**側を持つが、「広視野・低解像度の複眼と
少数のニューロンから運動・衝突時間・進行方向を出す」昆虫視葉の**処理経路**が
1 本も無かった。本レジストリはその経路(flyvision.py、8 op / 7 カテゴリ)で、
どれも学習網ではなく**閉形式の教科書モデル**であり、それぞれ突き合わせる
厳密な恒等式を持つ(下記の各ガイド閾値)。

来歴は公開文献のみ(docs/PROVENANCE.md の naming rule に従い、特定の製品・
企業を動機にも名前にも使わない): Hassenstein & Reichardt, *Z. Naturforsch.*
1956(相関型運動検出器)/ Hausen, *Biol. Cybern.* 1982(水平系の広視野統合)/
Gabbiani, Krapp & Laurent, *J. Neurosci.* 1999(η=θ'·exp(−αθ) 接近検出)/
Lee, *Perception* 1976(光学的膨張からの τ)/ Krapp & Hengstenberg,
*Nature* 1996(整合フィルタと視野上の方向場)/ Lappalainen et al.,
*Nature* 2024(六角格子と boxeye の画素歪み)。

既存資産との棲み分け(**再実装せず import して合成**):
  * 光学フロー由来の自己運動 = sceneflow。あちらの `time_to_contact` /
    `looming` / `focus_of_expansion` / `flow_divergence` は**密なフロー場**
    (画素ごとの (u,v))から読む。こちらの `fly_tau_from_expansion` は
    **1 本の膨張する角度**(θ(t))から読む —— 広視野の looming 検出器が実際に
    持っている入力で、そのために密フローを一度も計算しない。
  * 1-D フィルタ・スペクトル = dsp / funct1d。個眼の時系列は素の 1-D 配列なので
    そのまま渡せる。`fly_emd_response` だけは**2 チャネルの低域積の opponent**で、
    フィルタではなく運動モデルなので再ラップしない。
  * カメラ投影・較正 = camera / calib。`fly_hex_resample` は縦視野角の
    ピンホール規約(fov_deg = 全縦視野)を使うが、内部・外部行列の機構は
    複製しない —— 光軸は単に格子の中心。

使い方:
    import opsflyvision
    opsflyvision.list_ops("motion")
    opsflyvision.get("fly_hex_lattice")(radius=8)
"""
import flyvision

_MOD = {"flyvision": flyvision}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
#
# --------------------------------------------------------------------------
# 型語彙の判断: **新語を 1 つも作らない**(既存の語彙にそのまま収まる)
# --------------------------------------------------------------------------
#   * table   — `fly_hex_lattice` の返り(格子)と `fly_dsi` の返り(dsi/pref)は
#     どちらも dict = 既存 table。**格子を食う 2 op(fly_hex_resample /
#     fly_hs_readout)は必要な鍵の実在を実行時に検証**するので、csi_design や
#     fly_dsi の dict を「格子」と取り違えても黙っては通らず、鍵名で
#     fail-closed する(_as_lattice)。
#   * image2d — `fly_sky_1f` が産む等距円筒パノラマ、`fly_hex_resample` が食う
#     ピンホール画像。どちらも 2-D の実配列で、既存の 2-D op がそのまま効く。
#   * signal  — 個眼配列(1-D)。`fly_hex_resample` の出力、`fly_emd_response` /
#     `fly_lgmd_eta` / `fly_tau_from_expansion` の入出力。1-D の実関数で、非負性
#     すら約束しない広い sort へ戻すのが正しい(dsp / funct1d へ直結する)。
#   * matrix  — `fly_hs_readout` が食う (k, n) の応答行列。個眼ごとの応答を
#     複数種そろえた**一般の 2-D 数値行列**であって画像ではないので、image2d
#     ではなく既存の matrix(opsmath の一般行列)に載せる。列数が格子と食い違えば
#     fail-closed する。
#   * measurement — `fly_hs_readout` は単一の opponent 比(実スカラ)。
#
# ★ 重みは公開しない: `fly_hex_resample` の個眼×画素の重み行列は
#   `functools.lru_cache` で**内部にだけ**保持し、op の入出力型には現さない ——
#   出すと「画素座標系に依存する巨大な派生物」が型プールを汚し、下流の 2-D op が
#   それを画像と取り違えて黙って処理してしまう(zscan を video に渡すと通る、と
#   同じ事故の型)。出さないことでこの取り違えを構造的に不可能にする。
_CATALOG = {
    # --------------------------------------------------------------------
    # 2026-09-22: 眼と「自分がどう回ったか」のあいだの段。どれも学習なしの閉形式で、
    # コネクトームで測られた配線(三腕・ON/OFF・六角の隣)をそのまま式にしている。
    # --------------------------------------------------------------------
    # ラミナ —— 明るさを捨てて対比にする。型は matrix(個眼動画 (T, n)。行が時刻、
    #   列が個眼)。image2d には**しない**: 行が時刻で列が個眼の配列は 2-D 画像
    #   ではなく、2-D の op に渡すと「走るが意味が無い」出力になる。
    "lamina": [
        ("fly_lamina_filter", "flyvision", ["matrix"], "matrix"),
        ("fly_onoff_split", "flyvision", ["matrix"], "matrix"),
    ],
    # 方向 —— (6, n) の方向別応答と、そこから作る (n, 2) の局所フロー。どちらも
    #   一般の 2-D 数値行列 = matrix(既存の fly_hs_readout が食う形と同じ)。
    "direction": [
        ("fly_t4t5_field", "flyvision", ["matrix", "table"], "matrix"),
        ("fly_flow_from_directions", "flyvision", ["matrix", "table"], "matrix"),
    ],
    # 自己運動 —— 整合フィルタ(テンプレート)と、そこへの当てはめ。格子は table、
    #   回転の見積もりは dict = table。
    "selfmotion": [
        ("fly_matched_filter", "flyvision", ["table"], "matrix"),
        ("fly_egomotion_from_flow", "flyvision", ["matrix", "table"], "table"),
        ("fly_eye_merge", "flyvision", ["table", "table"], "table"),
    ],
    "lattice": [
        ("fly_hex_lattice", "flyvision", [], "table"),
    ],
    "stimulus": [
        ("fly_sky_1f", "flyvision", [], "image2d"),
    ],
    "sample": [
        ("fly_hex_resample", "flyvision", ["image2d", "table"], "signal"),
        ("fly_hex_quantize", "flyvision", ["signal"], "signal"),
    ],
    "motion": [
        ("fly_emd_response", "flyvision", ["signal", "signal"], "signal"),
    ],
    "looming": [
        ("fly_lgmd_eta", "flyvision", ["signal"], "signal"),
        ("fly_tau_from_expansion", "flyvision", ["signal"], "signal"),
    ],
    "integrate": [
        ("fly_hs_readout", "flyvision", ["matrix", "table"], "measurement"),
    ],
    "tuning": [
        ("fly_dsi", "flyvision", ["signal"], "table"),
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


OPSFLYVISION = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSFLYVISION.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し(ops3d / opsmath / opsinterferometry と同じ
#: 一級機構)。
#:
#: **現在は空 — 意図的に**。flyvision の 8 op はすべて宣言型そのもの
#: (dict / ndarray / float)を素で返す設計にしてある。空にしておくと
#: :func:`call` は :func:`get` と同じ値を返し、連鎖ファザーの TYPEMISS 検査が
#: **素の返りをそのまま**宣言と突き合わせる = 検証が最も厳しい。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable、素の返り型)。宣言型が欲しければ :func:`call`。"""
    return OPSFLYVISION[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSFLYVISION[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSFLYVISION[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSFLYVISION.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsflyvision: {len(OPSFLYVISION)} ops / "
          f"{len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
