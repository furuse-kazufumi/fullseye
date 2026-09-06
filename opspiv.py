# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opspiv —— 粒子画像流速測定(PIV)op の統一レジストリ。

実体は ``pivops.py``(23 op)と ``dic.py``(3 op)—— 計 26 op / 7 カテゴリ。
台帳の役目は 3 つ:
docs/ops へノートを出す・連鎖ファザーに食わせる・宣言型と素の返りを橋渡しする。

使い方::

    import opspiv
    opspiv.list_ops("estimate")
    flow = opspiv.call("piv_cross_correlate", a, b, window=32)
"""
import dic
import pivops

_MOD = {"pivops": pivops, "dic": dic}

# --------------------------------------------------------------------------
# 型語彙: **新語を 1 つだけ足した**。その判断の記録。
# --------------------------------------------------------------------------
# 基準はこの repo の一つだけ ——「混ぜたときに例外ではなく、もっともらしく
# 間違った数値が出るか」。
#
#   * ★ ``flow2d`` を新設した。既存の ``flow_dense`` は述語が
#     ``ndim == 4 and shape[0] == 3``(3-D シーンフロー)で、2-D の
#     ``(2, h, w)`` は**そもそも該当しない**。名前を借りると台帳が
#     「3 成分を返す」と宣言しながら 2 成分を返すことになり、宣言が嘘になる。
#
#     型を増やすときの本 repo の条件(「種を持つ op が無ければ永久に未実行に
#     なる」)は満たしている: **生成が 7 op**(cross_correlate / multipass /
#     deform_pass / ensemble_correlate / replace_outliers / to_velocity /
#     sample_at_windows)、**消費が 13 op**(場の量 8・可視化 2・検定 2・評価 3
#     の重なりを含む)で、族の中で生成と消費が閉じている。
#     ★ 出口(``visualise`` の 2 op)を必ず持たせている —— 作れるが見られない
#     型は、連鎖の途中で行き止まりになり「狭い sort」を生む。
#
#     両方向の fail-closed も実測で確認済み: ``reprconv.flow_magnitude`` に
#     2-D フローを渡すと ValueError(「(3, D, H, W) を取る」と名指しで拒否)、
#     ``piv_vorticity`` に 3-D シーンフローを渡すと ValueError。
#
#   * 入力の画像対は ``image2d`` —— 粒子画像は 2-D の実数場そのもので、
#     既存の 2-D op(平滑化・閾値・背景差し引き・図注)が意味を保ったまま
#     使える。**輝度が [0,1] に収まる保証は無い**が、それは astrostack の
#     合成結果と同じ立場。
#
#   * ``piv_outlier_mask`` は ``mask`` —— bool の 2-D で述語どおり。
#     ``dem_stream_network`` が nan を持つために mask を名乗れなかったのとは
#     違い、こちらは欠測を ``True``(外れ値)側に畳んであるので bool で閉じる。
#
#   * 統計は ``table``(dict)。``piv_error_stats`` / ``piv_peak_locking``。
#
#   * 速度への変換 ``piv_to_velocity`` の出力も ``flow2d`` —— **単位が
#     px/frame から m/s に変わるが型は同じ**。ここは正直に書いておく:
#     型では単位を守れない。だから両方のスケールを**必須引数**にしてある
#     (``demops`` の ``cell_size`` と同じ判断)。単位を型で分ける案も検討したが、
#     ``m/s`` を作る op が 1 本しか無く、消費する op が 1 本も無い型になる
#     ——「証拠が出てから増やす」の順序に反するので採らなかった。
_CATALOG = {
    # 合成 —— 真値つきの入力を作る(この族の全テストの供給源)
    "synth": [
        ("piv_synth_particles", "pivops", [], "image2d"),
        ("piv_synth_pair", "pivops", [], "image2d"),
        # 列は `images`(2-D 配列の list)。アンサンブル相関と時間統計は
        # **独立な対を並べたもの**では確かめられない(隣り合う 2 枚に対応が
        # 無いので統計が作り方を測ってしまう)ので、入口をここに置く。
        ("piv_synth_sequence", "pivops", [], "images"),
    ],
    # 推定 —— 本体
    "estimate": [
        ("piv_cross_correlate", "pivops", ["image2d", "image2d"], "flow2d"),
        ("piv_multipass", "pivops", ["image2d", "image2d"], "flow2d"),
        # 窓変形。予測で画像そのものを歪めてから相関する(回転場で実測 2.1 倍)
        ("piv_deform_pass", "pivops", ["image2d", "image2d", "flow2d"], "flow2d"),
        # 相関マップを足してからピークを探す(疎・雑音で実測 2.7 倍)
        ("piv_ensemble_correlate", "pivops", ["images"], "flow2d"),
    ],
    # 検定 —— 外れ値
    "validate": [
        ("piv_outlier_mask", "pivops", ["flow2d"], "mask"),
        ("piv_replace_outliers", "pivops", ["flow2d", "mask"], "flow2d"),
    ],
    # 場の量 —— 微分と大きさ
    "field": [
        ("piv_vorticity", "pivops", ["flow2d"], "image2d"),
        ("piv_divergence", "pivops", ["flow2d"], "image2d"),
        ("piv_flow_magnitude", "pivops", ["flow2d"], "image2d"),
        ("piv_to_velocity", "pivops", ["flow2d"], "flow2d"),
        # 速度勾配テンソルと、そこから出る量をまとめて返す(table)
        ("piv_velocity_gradient", "pivops", ["flow2d"], "table"),
        # 渦とせん断を分ける 2 つ。渦度だけ見るとせん断層も光る
        ("piv_q_criterion", "pivops", ["flow2d"], "image2d"),
        ("piv_swirling_strength", "pivops", ["flow2d"], "image2d"),
        ("piv_strain_rate", "pivops", ["flow2d"], "image2d"),
    ],
    # 可視化 —— 出口。ここを持たないと flow2d は「作れるが見られない」型になる
    "visualise": [
        ("piv_flow_to_rgbimage", "pivops", ["flow2d"], "rgb"),
        ("piv_line_integral_convolution", "pivops", ["flow2d"], "image2d"),
    ],
    # 固体側 —— DIC(デジタル画像相関)。**流体の PIV と同じ相関器を使うが、
    # 出す量が違う**。2026-09-06 に実測して足した 3 本(`dic.py`):
    #   * `piv_strain_rate` は剛体回転 2 度で **+1218 µε** を返す(真値 0)。
    #     docstring の「剛体回転では 0」は**線形化した流体の回転**でしか
    #     成り立たず、DIC が測る有限回転では成り立たない。
    #   * `piv_velocity_gradient` は `np.gradient`(2 点差分)なので、
    #     同じ流れ場・500 µε で散らばりが **136.9 µε**。窓最小二乗なら 12.4 µε。
    #   * `info["peak_ratio"]` は貼り替えた 60x60 の領域を分離できない
    #     (内 1.184 / 外 1.329)。ZNCC 係数なら 0.100 / 0.999 で、
    #     `zncc >= 0.8` で切ると RMS が 1.9122 → 0.0036 px(**537 倍**)。
    "solid": [
        ("strain_from_displacement", "dic", ["image2d", "image2d"], "image2d"),
        ("correlation_quality", "dic", ["image2d", "image2d", "flow2d"], "image2d"),
        ("speckle_quality", "dic", ["image2d"], "table"),
    ],
    # 評価 —— 真値との突き合わせと系統誤差
    "assess": [
        ("piv_sample_at_windows", "pivops", ["flow2d"], "flow2d"),
        ("piv_error_stats", "pivops", ["flow2d", "flow2d"], "table"),
        ("piv_peak_locking", "pivops", ["flow2d"], "table"),
        # 時間平均・変動・レイノルズ応力(3 枚以上の列が要る)
        ("piv_time_statistics", "pivops", ["images"], "table"),
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


OPSPIV = _build()

#: 宣言 out 型と素の返りの橋渡し。**4 op がタプルを返す**。
#:
#: 旗で返り型が変わる設計(``return_info=True`` など)は採らない —— 台帳が
#: どちらの姿を宣言しても嘘になるため、常にタプルを返して adapter で
#: 先頭を取り出す(``opsastrostack`` と同じ判断)。素の返りが欲しければ
#: :func:`get` を使う。
_first = (lambda r: r[0])
RESULT_ADAPTERS = {
    "piv_synth_particles": _first,   # (image, positions)   -> image2d
    "piv_synth_pair": _first,        # (a, b, truth)        -> image2d
    "piv_synth_sequence": _first,    # (frames, truth)      -> images
    "piv_cross_correlate": _first,   # (flow, info)         -> flow2d
    "piv_multipass": _first,         # (flow, info)         -> flow2d
    "piv_deform_pass": _first,       # (flow, info)         -> flow2d
    "piv_ensemble_correlate": _first,  # (flow, info)       -> flow2d
    # (exx, eyy, exy) -> image2d。捨てる 2 本は `fullseye.ledger.<名前>.raw` で取れる。
    "strain_from_displacement": _first,
}


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSPIV.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


def get(name):
    """op 名 → 実体(callable、素の返り型)。"""
    return OPSPIV[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSPIV[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSPIV[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSPIV.items() if m["func"] is None]


if __name__ == "__main__":
    print("opspiv: %d ops / %d categories" % (len(OPSPIV), len(categories())))
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
    for cat in categories():
        print("  %-9s %s" % (cat, ", ".join(list_ops(cat))))
