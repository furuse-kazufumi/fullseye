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
#   既存語彙の再利用: signal / depth / image2d / measurement(実スカラのみ)/ table
#   新語彙: zscan
#
# --------------------------------------------------------------------------
# 既存語彙をそのまま使った判断(新語を作らなかったもの)
# --------------------------------------------------------------------------
#   * signal — z 走査 1 画素の干渉信号、およびクロマティック共焦点の
#     スペクトル。**新語を作らなかったのは実測に基づく判断**で、根拠は 3 つ:
#       (a) 構造上の嘘が無い。counts(非負)や stokes(長さ 4 + 偏光度制約)は
#           既存 signal では**型レベルで嘘**になったが、走査干渉信号は
#           「1-D の標本化された実関数」そのもので、追加の構造制約が無い。
#           制約は「コヒーレンス包絡線を持つこと」という**意味**の側にあり、
#           それは実行時に fail-closed で見る(min_visibility)。
#       (b) 相乗りが実際に有益。dsp の bandpass / detrend / resample と
#           funct1d は干渉信号の正しい前処理そのもので、プールを分けると
#           その接続を切るだけになる。
#       (c) 逆向きの相乗りは**安全に落ちる**ことを実測した。連鎖ファザーの
#           signal 種(正弦波 + 10% 雑音)を csi_peak_position に渡すと
#           包絡線 prominence が 0.241 で、既定 min_visibility=0.30 を
#           下回り CONTRACT になる(= もっともらしい嘘を返さない)。
#     ★ ただし (c) は「族が一度も実行されない」= opsphoton が counts で
#       踏んだ罠と表裏である。そこを塞ぐのが **`csi_signal_simulate`
#       ([] -> signal)** と **`chromatic_confocal_simulate` ([] -> signal)**
#       で、この 2 op が**本物の干渉信号を既存 signal プールへ注ぎ込む**。
#       counts のときと違って新プールを作らずに到達性を確保できるのは、
#       入口 op が既存プールへ直接産めるからである(実測は報告を参照)。
#   * depth   — csi_height_map の返りは (H, W) の高さマップ = 既存 depth 語彙。
#     stereo / range_image / photoncount の depth op へ直結する。
#   * image2d — csi_contrast_map の返りは (H, W) のフリンジ変調度。既存の
#     2-D op(閾値・morphology・blob)が意味を持ったまま使える — 実際
#     「変調度を閾値して有効画素マスクを作る」は現場の標準手順そのもの。
#   * measurement — csi_peak_position / chromatic_confocal_height は単一画素の
#     高さ(実スカラ)。
#   * table   — csi_design の返りは dict。
#
# --------------------------------------------------------------------------
# 新語彙 1 つと、その理由
# --------------------------------------------------------------------------
# 追加の基準は既存 3 台帳と同じ「**既存語彙で宣言すると型レベルの嘘になるか**」。
#
#   * zscan — z 走査スタック **(Z, H, W)、走査軸が最初**。既存 `video` は
#     (T, H, W) で TYPE_CHECKS も「ndim==3 / float / shape[0]>=2 /
#     shape[1],[2]>=4」なので、**構造チェックは完全に一致する**。分けた理由は
#     実測:
#       (a) video を渡しても**例外にならず、もっともらしい高さマップが返る**
#           場合がある。連鎖ファザーの video 種(motionmag.synthesize_translation、
#           サブピクセル並進する格子)を csi_height_map に渡した実測結果は
#           報告に載せる。搬送波を持つ画素は包絡線 prominence を満たしうるので
#           fail-closed に頼りきれない。
#       (b) 軸の意味が違う。video の先頭軸は**時間**で、frame 間隔は fps。
#           zscan の先頭軸は**距離**で、plane 間隔は z_step_um。z_step_um は
#           Nyquist 判定(λ/4)に使われるので、fps を z_step として渡すと
#           判定そのものが無意味になる。
#       (c) 逆向きも危ない。zscan を motion_magnify に渡せば「z を時間と読んだ」
#           増幅が例外なく返る。pointmap / normalmap を分けたのと同じ判断で、
#           **型は入れ物の形でなく意味の約束**。
#     zscan は 3 op(産む 1 + 食う 2)の**狭くない sort** である:
#       入口 = `csi_stack_simulate` (depth -> zscan)。既存 depth プールから
#              直接産めるので、種を置かなくても連鎖の中で到達できる。
#       出口 = `csi_height_map` (zscan -> depth) と
#              `csi_contrast_map` (zscan -> image2d)。どちらも**既存の広い
#              sort へ戻る**ので、袋小路にならない。
#     これは dtof(depth -> histcube -> depth)と同じ形で、あちらが機能した
#     実績のある構成である。
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
