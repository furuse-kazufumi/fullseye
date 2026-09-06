# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsdem —— fullseye の数値標高モデル(DEM)解析 op の統一レジストリ。

実体は ``demops.py``(19 op / 5 カテゴリ)。この台帳は 3 つの役目を持つ:

1. **docs/ops へノートを出す**(``tools/opdocs.py`` の :data:`LEDGER_DIMS`)。
   ここに載っていない族は RAG コーパスにも Studio ヘルプにも 1 枚も出ない。
2. **連鎖ファザーに食わせる**(``typed_catalog.catalog()``)。載せないと
   「発見ゼロ」に見えるが、実際には**一度も実行されていない**という、この
   repo が 2026-09-02 に 192 op で踏んだ形になる。
3. 宣言型と素の返りの橋渡し(:data:`RESULT_ADAPTERS`。この族は空 —— 下記)。

使い方::

    import opsdem
    opsdem.list_ops("hydrology")
    opsdem.call("dem_slope", dem, cell_size=5.0)
"""
import demops

_MOD = {"demops": demops}

# --------------------------------------------------------------------------
# 型語彙: **新語を 1 つも作らない**。その判断の記録。
# --------------------------------------------------------------------------
# 基準は opsphoton / opsastrostack と同じ一つだけ ——
# 「混ぜたときに例外ではなく、もっともらしく間違った数値が出るか」。
#
#   * 入力 = ``depth``。DEM は**深度画像そのもの**(メートルの高さ格子)で、
#     プールの種 ``1.0 + rng.random((32, 32))`` はまさにその形。``image2d``
#     ではなく ``depth`` を選んだのは単位の理由で、``image2d`` プールは
#     [0,1] の輝度であり、それを「メートルの標高」と名乗らせると
#     ``cell_size`` との比が 2 桁ずれた傾斜が例外なしで出る。
#
#     ★ 正直な限界: ``depth`` プールにはカメラの透視投影による深度も入りうる。
#     透視深度は 1 px が地上で何メートルかが深さとともに変わるので、一定の
#     ``cell_size`` を当てた傾斜は**もっともらしく間違う**。ではなぜ型を
#     分けないか —— これは型の取り違えではなく ``cell_size`` の与え方の
#     誤りと同じ種類の誤りで、``cell_size`` は既に**必須引数**(既定値を置か
#     ない)にしてある。型を増やしても正射でない深度は防げず(述語は
#     「2-D の実数配列」までしか見られない)、代わりに種を持つ op が 1 つも
#     無い ``dem`` プールができて **13 op すべてが永久に未実行**になる。
#     防げないものを型で防いだことにするより、必須引数と docstring で明示し、
#     ファザーには実際に走らせるほうを採った。
#
#   * ``dem_fill_sinks`` の出力だけ ``depth`` —— 窪地を埋めた結果は**まだ
#     標高格子**で、そのまま ``dem_flow_direction`` へ入る。ここを
#     ``image2d`` と宣言すると族内の連鎖(埋める → 流す)が型で切れる。
#
#   * ``dem_flow_direction`` は ``labels`` —— 返りは int8 の 0-7 と -1(流出先
#     なし)で、**順序に意味が無い符号**である。``mask`` を名乗ると二値の
#     ように扱われ、``image2d`` を名乗ると 3 と 4 の平均に意味があることに
#     なってしまう。``labels`` の述語(整数 dtype の 1-3 次元)にそのまま該当。
#
#   * ``dem_stream_network`` は二値だが ``image2d`` —— 中身は 0.0/1.0 に加えて
#     **欠測の nan** を持つ float64 で、``mask`` の述語(bool か整数 dtype)を
#     満たさない。bool にすると「河道でない」と「そもそも値が無い」が
#     区別できなくなるので、型のほうを実装に合わせた。
#
#   * 残りはすべて ``image2d`` —— 傾斜[度]・方位[度]・曲率[1/m]・陰影[0,1]・
#     起伏[m]・地平線仰角[度]・天空率[0,1]・可視[0/1]。どれも 2-D の実数場で、
#     既存の 2-D op(平滑化・閾値・morphology・疑似カラー・図注)が意味を
#     保ったまま使える。**値域は [0,1] とは限らない**が、それは
#     ``astrostack`` の合成結果と同じ立場で、``image2d`` は輝度の約束では
#     なく「2-D の実数場」の約束としてこの repo では使われている。
#
# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 面の幾何 —— 1 次・2 次の微分量。局所 3x3 で閉じる。
    "surface": [
        ("dem_slope", "demops", ["depth"], "image2d"),
        ("dem_aspect", "demops", ["depth"], "image2d"),
        ("dem_curvature", "demops", ["depth"], "image2d"),
        ("dem_roughness", "demops", ["depth"], "image2d"),
        ("dem_tpi", "demops", ["depth"], "image2d"),
    ],
    # 陰影 —— 光源方向を与えた反射。可視化であると同時に日照の目安。
    "shading": [
        ("dem_hillshade", "demops", ["depth"], "image2d"),
    ],
    # 水文 —— 格子全体に及ぶ大域演算(優先度キュー / トポロジカル順)。
    "hydrology": [
        ("dem_fill_sinks", "demops", ["depth"], "depth"),
        ("dem_flow_direction", "demops", ["depth"], "labels"),
        ("dem_flow_accumulation", "demops", ["depth"], "image2d"),
        ("dem_stream_network", "demops", ["depth"], "image2d"),
    ],
    # 地心座標 —— 地球中心から見た表現と、地球の丸みの補正。
    # 平面として扱える範囲を超えると、見通しも傾斜も静かに間違う。
    "geodesy": [
        ("dem_geodetic_to_ecef", "demops", [], "points"),
        ("dem_ecef_to_geodetic", "demops", ["points"], "points"),
        ("dem_geocentric_grid", "demops", ["depth"], "coordgrid"),
        ("dem_earth_curvature_drop", "demops", [], "measurement"),
        ("dem_cell_size_webmercator", "demops", [], "measurement"),
        ("dem_geodetic_slope", "demops", ["depth"], "image2d"),
    ],
    # 可視性 —— 視線が地形に遮られるか。日射・眺望・電波見通しに効く。
    "visibility": [
        ("dem_horizon_angle", "demops", ["depth"], "image2d"),
        ("dem_sky_view_factor", "demops", ["depth"], "image2d"),
        ("dem_viewshed", "demops", ["depth"], "image2d"),
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


OPSDEM = _build()

#: 宣言 out 型と素の返りの橋渡し。**意図的に空** —— 13 op すべてが 2-D 配列を
#: 1 つだけ返す(実測で確認済み)。旗で返り型が変わる op も、タプルを返す op も
#: この族には無い。将来 ``return_mask`` のような旗を足すなら、旗ではなく
#: 常にタプルを返す形にして、ここに ``_first`` を登録すること
#: (``opsastrostack`` の RESULT_ADAPTERS にその理由が書いてある)。
RESULT_ADAPTERS = {}


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSDEM.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


def get(name):
    """op 名 → 実体(callable、素の返り型)。"""
    return OPSDEM[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSDEM[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSDEM[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSDEM.items() if m["func"] is None]


if __name__ == "__main__":
    print("opsdem: %d ops / %d categories" % (len(OPSDEM), len(categories())))
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
    for cat in categories():
        print("  %-11s %s" % (cat, ", ".join(list_ops(cat))))
