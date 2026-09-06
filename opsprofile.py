# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsprofile —— 断面形状(profile)計測 op の統一レジストリ。

実体は ``profileops.py``(12 op / 4 カテゴリ)。翼型・羽根・押し出し材・
ガスケットなど、**細長い閉断面を弦に沿って測る**層。

使い方::

    import opsprofile
    ref = opsprofile.call("profile_synth_naca4", "2412")
    dev = opsprofile.call("profile_deviation", measured, ref)
"""
import profileops

_MOD = {"profileops": profileops}

# --------------------------------------------------------------------------
# 型語彙: **新語を 1 つも作らない**。その判断の記録。
# --------------------------------------------------------------------------
# 輪郭は既存の ``pairs``(``(N, 2)`` の ``(x, y)``)。この repo で ``pairs`` は
# 2 つの意味で使われている ——「1 価の関数データ」(spectrum / MTF / ray_fan)と
#「多角形」(filled_polygon が食う)。後者と同じ立場を採る。
#
# **混ぜたら嘘になるか**: 関数データ(MTF 曲線など)を ``profile_thickness`` に
# 渡すと、もっともらしい厚み分布が出るか? —— 出ない。``profile_sides`` が
# 「どの弦位置でも上面と下面の両方が取れない = これは閉じた断面ではない」と
# 名指しで拒否する(実測済み)。つまり**型ではなく検証で守れる**。
#
# 逆に型を分けると、既存の輪郭生成 op(``gen_region_contour_xld`` /
# ``smooth_contours`` / ``convex_hull`` 系、``filled_polygon``)との接続が
# 切れる。97 個ある輪郭 op の隣に置く族なので、そこを切るのは損が大きい。
#
#   * ``profile_chord_frame`` / ``profile_sides`` / ``profile_deviation`` は
#     ``table``(dict)。
#   * ``profile_leading_edge_radius`` / ``profile_trailing_edge_gap`` は
#     ``measurement``(実スカラ 1 個)。
#   * ``profile_thickness`` / ``profile_camber`` は ``pairs`` ——
#     ``(x, t)`` の関数データそのもので、``pairs_to_signal`` / ``plot_series`` /
#     ``interp_cubic`` がそのまま食う。**ここは「関数データとしての pairs」**で、
#     輪郭としての pairs とは意味が違うが、同じ型で正しい(どちらも (x, y) の
#     並びであり、下流の op はどちらでも定義どおりに働く)。
_CATALOG = {
    # 生成 —— 真値は閉形式から
    "synth": [
        ("profile_synth_naca4", "profileops", [], "pairs"),
        ("profile_perturb", "profileops", ["pairs"], "pairs"),
    ],
    # 整える —— 弦の枠・正規化・取り直し
    "frame": [
        ("profile_chord_frame", "profileops", ["pairs"], "table"),
        ("profile_normalise", "profileops", ["pairs"], "pairs"),
        ("profile_resample", "profileops", ["pairs"], "pairs"),
    ],
    # 測る —— 断面としての量
    "measure": [
        ("profile_sides", "profileops", ["pairs"], "table"),
        ("profile_thickness", "profileops", ["pairs"], "pairs"),
        ("profile_camber", "profileops", ["pairs"], "pairs"),
        ("profile_leading_edge_radius", "profileops", ["pairs"], "measurement"),
        ("profile_trailing_edge_gap", "profileops", ["pairs"], "measurement"),
    ],
    # 比べる —— 位置合わせと偏差
    "compare": [
        ("profile_align", "profileops", ["pairs", "pairs"], "pairs"),
        ("profile_deviation", "profileops", ["pairs", "pairs"], "table"),
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


OPSPROFILE = _build()

#: 宣言 out 型と素の返りの橋渡し。``profile_align`` だけがタプル
#: ``(aligned, info)`` を返す —— 合わせ方の情報は**返り値の一部**であって、
#: 旗で有無が切り替わるものではない(旗で返り型が変わると台帳がどちらの姿を
#: 宣言しても嘘になる)。
RESULT_ADAPTERS = {
    "profile_align": (lambda r: r[0]),      # (aligned, info) -> pairs
}


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSPROFILE.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


def get(name):
    """op 名 → 実体(callable、素の返り型)。"""
    return OPSPROFILE[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSPROFILE[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSPROFILE[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSPROFILE.items() if m["func"] is None]


if __name__ == "__main__":
    print("opsprofile: %d ops / %d categories" % (len(OPSPROFILE), len(categories())))
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
    for cat in categories():
        print("  %-8s %s" % (cat, ", ".join(list_ops(cat))))
