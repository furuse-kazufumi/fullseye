# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsinterferometry — fullseye コヒーレンス走査干渉・クロマティック共焦点 op の統一レジストリ。

動機(2026-09-01)は fullseye 自身の空白の実測(`docs/INDUSTRY_SIGNALS.md` §3)。
**コヒーレンス包絡線で高さを出す経路**が 3 つの在庫表面すべてで 0 件だった
(`interferomet` / `wli` / `chromatic_conf` = 0)。既存の `fringe` は
**位相シフト法**で、位相から高さを出す — 精密だが原理的に 2π 不定性を持ち、
λ/4 を超える段差を**黙って別の値として返す**。本レジストリはその不定性を
持たない側の台帳(interferometry.py、9 op / 5 カテゴリ)。

来歴は公開文献のみ(docs/PROVENANCE.md の naming rule に従い、特定の製品・
企業を動機にも名前にも使わない): de Groot, *Adv. Opt. Photon.* 2015(走査
干渉信号モデル)/ Caber, *Appl. Opt.* 1993(粗面に対する包絡線検出)/
Larkin, *JOSA A* 1996(包絡線検出アルゴリズム)/ Born & Wolf 7.5.8
(ガウス光源のコヒーレンス長)/ Tiziani & Uhde, *Appl. Opt.* 1994
(波長→高さ写像)/ ISO 25178-604・602(用語)。

既存資産との棲み分け(**再実装せず import して合成**):
  * 位相シフト干渉法・縞投影 = fringe(`wrapped_phase` / `unwrap_phase_2d` /
    `phase_to_height` / `decode_fringe` / `synthesize_fringes`)。ここでは
    wrapped phase を一切計算せず、あちらは包絡線を一切検出しない。両者が
    出会う唯一の場所が `tests/test_interferometry.py` の突き合わせ試験で、
    **同一の合成表面**を両方に食わせて 2π 不定性の有無を数値で示す。
  * 位相アンラップ = complexops.`phase_unwrap` / fringe.`unwrap_phase_2d`。
    本モジュールは一度もアンラップしない(**しなくて済むことが要点**)。
  * 1-D 包絡線 = dsp.`envelope`(登録名は 2-D 版の `xsp_hilbert_env`)。
    `csi_envelope` は **dsp.envelope をそのまま呼ぶ**うえで、干渉縞に固有の
    「直流台座の除去」だけを足す。生の干渉信号を dsp.envelope に直接渡すと
    返るのは台座であって包絡線ではない(実測誤差 0.5 = 台座そのもの)。
  * 光学設計(焦点距離・被写界深度・回折・MTF)= optics / visiondesign。
    `csi_design` はその**軸方向版**で、空間側は一切複製しない。
  * 光子計数の (H,W,T) 立方体 = photoncount。あちらは**時間軸が最後**、
    こちらは**走査軸が最初**。混ぜると黙って間違う(下記 zscan の項)。

使い方:
    import opsinterferometry
    opsinterferometry.list_ops("surface")
    opsinterferometry.get("csi_height_map")(stack, z_step_um=0.05)
"""
import interferometry

_MOD = {"interferometry": interferometry}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
#   既存語彙の再利用: depth / image2d / signal / measurement(実スカラのみ)/ table
#   新語彙: zscan / sweep
#
# --------------------------------------------------------------------------
# 既存語彙をそのまま使った判断(新語を作らなかったもの)
# --------------------------------------------------------------------------
#   * depth   — csi_height_map の返りは (H, W) の高さマップ = 既存 depth 語彙。
#     stereo / range_image / photoncount の depth op へ直結する。同時に
#     **zscan の入口でもある**(csi_stack_simulate: depth -> zscan)ので、
#     depth プールが在るだけで新語彙が到達可能になる。
#   * image2d — csi_contrast_map の返りは (H, W) のフリンジ変調度。既存の
#     2-D op(閾値・morphology・blob)が意味を持ったまま使える — 「変調度を
#     閾値して有効画素マスクを作る」は現場の標準手順そのもの。
#   * signal  — csi_envelope の**出力**。包絡線は 1-D の実関数であって非負性
#     以外の約束を持たないので、ここは既存の広い sort へ**戻す**のが正しい。
#     これが sweep 語彙の出口になっている(袋小路にしない)。
#   * measurement — csi_peak_position / chromatic_confocal_height は単一画素の
#     高さ(実スカラ)。
#   * table   — csi_design の返りは dict。
#
# --------------------------------------------------------------------------
# 新語彙 2 つと、その理由(どちらも実測に基づく)
# --------------------------------------------------------------------------
# 追加の基準は既存台帳と同じ「**既存語彙で宣言すると型レベルの嘘になるか**」、
# および「**相乗りさせると一度も実行されないまま発見ゼロに見えないか**」。
#
#   * zscan — z 走査スタック **(Z, H, W)、走査軸が最初**。既存 `video` は
#     (T, H, W) で TYPE_CHECKS も「ndim==3 / float / shape[0]>=2 /
#     shape[1],[2]>=4」なので**構造チェックは完全に一致する**。分けた理由は
#     危険な向きが実測で確認できたこと:
#       (a) zscan -> video 側は**黙って通る**。csi_stack_simulate が作った
#           スタックを motionmag.motion_magnify / temporal_band_power /
#           phase_displacement / band_snr に渡すと、4 op すべてが例外も NaN も
#           出さず「増幅結果」「帯域パワー」「変位場」を返す(実測)。
#           z を時間として読んだ、意味の無い有限値である。
#       (b) zscan -> histcube 側も**黙って通る**。photoncount.dtof_cube_depth
#           に渡すと 0.0075-0.47 m の有限な深度マップが返る(実測)。
#       (c) 逆向き(video -> csi_height_map)は 8 seed すべてで fail-closed
#           (1023-1024 / 1024 画素が無効)。安全なのは片側だけなので、
#           実行時チェックには頼れない。
#     zscan は 3 op(産む 1 + 食う 2)で、入口 = `csi_stack_simulate`
#     (depth -> zscan、既存 depth プールから直接産める)、出口 =
#     `csi_height_map` (-> depth) と `csi_contrast_map` (-> image2d)。
#     dtof(depth -> histcube -> depth)と同じ形で、袋小路にならない。
#
#   * sweep — **掃引軸に沿って標本化した非負の 1-D 強度で、局在したピークを
#     1 つ持つもの**。z 走査干渉信号(走査位置軸)とクロマティック共焦点の
#     スペクトル(波長軸)の 2 種を**同じ語彙に入れている** — 実配列の形と
#     統計が同じで、軸の較正は常に**明示引数**(z_step_um / wavelength_step_nm)
#     だからである。2 種を混ぜる生成器は `qimage` の先例に倣う(色四元数と
#     モノジェニック信号を必ず両方出す)。
#     ★ 既存 `signal` に相乗りさせなかったのは**実測の結果**である。最初は
#       「csi_signal_simulate ([] -> signal) が本物の干渉信号をプールへ注ぐから
#       到達できる」と判断したが、その配線で連鎖ファザーを回すと
#       **600 連鎖(300x長さ6 + 300x長さ8)で csi_peak_position と
#       chromatic_confocal_height が 1 度も実行されなかった**(記録は
#       CONTRACT が 7 件のみ)。原因は signal 種が負値を持つ正弦波で、
#       入口 op が同じ連鎖で先に引かれる確率が低いこと。opsphoton が counts で
#       踏んだ罠とまったく同じで、**fail-closed が完璧に効いた結果として
#       「発見ゼロ」が頑健さに見える**。sweep を専用プールにした同条件の
#       再測定では 9 op すべてが実行された。
#     2 種を混ぜても取り違えが黙って通らないことは、**それぞれ専用の判別で
#     担保**してある(どちらも閉形式で測った閾値):
#       - スペクトルを csi_peak_position に渡す → `carrier_tolerance`。
#         干渉信号は搬送波が 2/λ(Nyquist の 0.333)に立つが、共焦点ピークは
#         0.010。実測で 1000 倍の単位誤りも同じ検査が捕まえる。
#       - 干渉信号を chromatic_confocal_height に渡す →
#         `max_carrier_fraction`。共焦点応答の AC 成分は低周波だけ(実測
#         0.010 / 0.010 / 0.015)、干渉信号は 0.333。
#     入口 = `csi_signal_simulate` / `chromatic_confocal_simulate`(どちらも
#     引数なしで産む)、出口 = `csi_envelope` (-> signal) と 2 つの
#     measurement op。
_CATALOG = {
    "simulate": [
        ("csi_signal_simulate", "interferometry", [], "sweep"),
        ("csi_stack_simulate", "interferometry", ["depth"], "zscan"),
        ("chromatic_confocal_simulate", "interferometry", [], "sweep"),
    ],
    "envelope": [
        ("csi_envelope", "interferometry", ["sweep"], "signal"),
    ],
    "locate": [
        ("csi_peak_position", "interferometry", ["sweep"], "measurement"),
    ],
    "surface": [
        ("csi_height_map", "interferometry", ["zscan"], "depth"),
        ("csi_contrast_map", "interferometry", ["zscan"], "image2d"),
    ],
    "chromatic": [
        ("chromatic_confocal_height", "interferometry", ["sweep"], "measurement"),
    ],
    "design": [
        ("csi_design", "interferometry", [], "table"),
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


OPSINTERFEROMETRY = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSINTERFEROMETRY.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し(ops3d / ops1d / opsmath / opsoptics /
#: opsphoton と同じ一級機構)。
#:
#: **現在は空 — 意図的に**。interferometry の 9 op はすべて宣言型そのもの
#: (ndarray / float / dict)を素で返す設計にしてある。とくに
#: ``csi_peak_position`` は「(位置, 包絡線, 信頼度) タプル」ではなく
#: **float だけ**を返し、包絡線が要るなら ``csi_envelope``、信頼度が要るなら
#: ``csi_contrast_map`` を呼ぶ — adapter を要らなくするためではなく、
#: 1 op = 1 量のほうが連鎖の型検査が厳しくなるからである。空にしておくと
#: :func:`call` は :func:`get` と同じ値を返し、連鎖ファザーの TYPEMISS 検査が
#: **素の返りをそのまま**宣言と突き合わせる = 検証が最も厳しい。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable、素の返り型)。宣言型が欲しければ :func:`call`。"""
    return OPSINTERFEROMETRY[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSINTERFEROMETRY[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSINTERFEROMETRY[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSINTERFEROMETRY.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsinterferometry: {len(OPSINTERFEROMETRY)} ops / "
          f"{len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
