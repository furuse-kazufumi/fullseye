# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opssegmentation —— HALCON "Segmentation" 章の 9 op(画素分類・領域成長・マーカー分水嶺)の統一レジストリ。

実体は ``segmentation.py``(9 op / 4 カテゴリ)。台帳の役目は 3 つ:
docs/ops へノートを出す・連鎖ファザーに食わせる・宣言型と素の返りを橋渡しする。

使い方::

    import opssegmentation
    opssegmentation.list_ops("grow")
    lab = opssegmentation.call("watersheds_marker", image, markers)

## なぜ台帳に載せたか(2026-10-02)

``segmentation.py`` は 2026-08 から wheel に同梱され(pyproject の py-modules)、
``fullseye/data/halcon_facade_map.json`` を通して ``fullseye.vision.segment.<名前>``
からは届いていた。だが **``fullseye.ledger`` / ``fullseye.op`` / ``fullseye.<名前>``
のどれにも無く**、``tests/test_public_reachability.py`` の数え方では 9 本とも
「公開経路から呼べない関数」だった。``examples/poc_cell_counting.py`` と
``examples/poc_particle_sizing.py`` は揃って「2-D の分水嶺が公開経路に無い」を
道具の穴として挙げ、``docs/ops/blob/guides/blob_analysis.md`` も同じ行を持つ。
facade(統一 registry)は HALCON 名で引く層で、docs/ops のノート・連鎖ファザー・
``op_run`` の入力補助には乗らない —— 台帳に載せて初めてそれらが付く。

## なぜ族を分けたか

相乗りできる先を先に探した。``opsblob``(連結成分解析)は **二値領域を物体の
集まりとして扱う**層で、入口が ``mask``。こちらは **グレー値・特徴空間から領域を
作る**層で、入口が画像(1 枚・2 枚・多チャネル)と学習済みクラス。``blob_split``
(距離の降順で回す分水嶺)と ``watersheds_marker``(skimage の immersion 型)は
同じ目的の別算法で、``blob2d`` の docstring が「skimage 不在時に黙って別算法に
落ちるから使わない」と書いている —— その違いを 1 つの族に混ぜると、台帳の
「割る」カテゴリが同名の別物を 2 本持つことになる。
2-D レジストリ(``backends_auto``)には ``watersheds`` / ``regiongrowing`` /
``regiongrowing_mean`` が在るが、どれも **画像 1 枚 + a/b ノブ**の形で、マーカー
画像・参照画像・学習済みクラスといった第 2 入力を取れない。

## 型語彙: **新語はゼロ**。その判断の記録

* 画像 1 枚は ``image2d``、多チャネル特徴は ``images``(2-D の list)。
  ``regiongrowing_n`` / ``class_ndim_norm`` は (H, W, D) も受けるが、台帳は list で
  宣言する —— (H, W, 3) は ``rgbimage`` / ``pointmap`` の述語にも当たり、
  「RGB を 3 チャネル特徴として」渡しても例外が出ないので、list で意図を明示する。
* 領域(bool 2-D)は既存の ``mask``。``check_difference`` / ``class_2dim_sup`` /
  ``class_ndim_norm`` / ``expand_gray`` の返りは画素ごとの真偽なので述語どおり。
* ラベル画像は既存の ``labels2d``(int、0 以上)。``watersheds_marker`` /
  ``regiongrowing_n`` は 1..n、``class_2dim_unsup`` と ``classify_image_class_lut``
  は **0 もクラス番号**として返す(HALCON も同様にクラス 0 を持つ)。
  ``opsblob`` の「背景 0」の約束とは意味が違うので、``blob_features`` に渡す前に
  番号を 1 から振り直すこと(ノート参照)。
* 学習済みクラス(``learn_ndim_norm`` の返り)は dict(``mean`` / ``cov`` / ``inv``)
  なので既存の ``table``。生産者 1(``learn_ndim_norm``)・消費者 1
  (``class_ndim_norm``)で族の中に閉じる。
* 特徴ベクトル群 (N, D) は既存の ``matrix``。LUT は 1-D なので既存の ``signal``。

## 同じ台帳に足したカテゴリ(2026-10-02)

* ``score`` / ``world``(第 1 陣、``segeval`` / ``segworld``): 分割の採点と真値つき合成世界。
* ``contour``(第 2 陣、``segcontour``): snake・GVF・Chan–Vese・形態学的 AC・DRLSE・再初期化・
  平均曲率流。新語なし(image2d / mask / pairs / table)。ガイド
  ``docs/ops/segmentation/guides/active_contours_and_level_sets.md``。
* ``graph`` / ``threshold``(第 3 陣、``seggraph``): graph cut(最大フロー = 最小カット)・α-expansion・
  SRM・成分木と属性開放・準平坦領域と α-tree・dynamics の階層分水嶺と UCM・超画素 SNIC / quick shift と
  その採点、閾値 4 定理(三角法・isodata・Kittler・Kapur)。新語なし(image2d / labels2d / table)。ガイド
  ``docs/ops/segmentation/guides/graph_hierarchy_and_thresholds.md``。
"""
import segmentation
import segeval
import segworld
import segcontour
import seggraph

_MOD = {"segmentation": segmentation, "segeval": segeval, "segworld": segworld,
        "segcontour": segcontour, "seggraph": seggraph}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 比べる —— 基準画像との差が閾値を超える画素(HALCON check_difference)
    "compare": [
        ("check_difference", "segmentation", ["image2d", "image2d"], "mask"),
    ],
    # 分類する —— 特徴空間(2 次元 / N 次元 / LUT)で画素をクラスに分ける
    "classify": [
        ("class_2dim_sup", "segmentation", ["image2d", "image2d", "mask"], "mask"),
        ("class_2dim_unsup", "segmentation", ["image2d", "image2d"], "labels2d"),
        ("learn_ndim_norm", "segmentation", ["matrix"], "table"),
        ("class_ndim_norm", "segmentation", ["images", "table"], "mask"),
        ("classify_image_class_lut", "segmentation", ["image2d", "signal"], "labels2d"),
    ],
    # 育てる —— 種から / 全画素から、グレー値の近さで領域を広げる
    "grow": [
        ("expand_gray", "segmentation", ["image2d", "mask"], "mask"),
        ("regiongrowing_n", "segmentation", ["images"], "labels2d"),
    ],
    # 割る —— マーカーから流し込む分水嶺
    "watershed": [
        ("watersheds_marker", "segmentation", ["image2d", "labels2d"], "labels2d"),
    ],
    # 採点する —— 分割の予測を真値と比べる物差し(segeval、2026-10-02。入口は 2 枚のラベル画像)
    "score": [
        ("seg_confusion_table", "segeval", ["labels2d", "labels2d"], "table"),
        ("seg_dice_jaccard", "segeval", ["labels2d", "labels2d"], "table"),
        ("seg_boundary_f", "segeval", ["labels2d", "labels2d"], "table"),
        ("seg_hausdorff", "segeval", ["labels2d", "labels2d"], "table"),
        ("seg_mean_surface_distance", "segeval", ["labels2d", "labels2d"], "table"),
        ("seg_under_over_segmentation", "segeval", ["labels2d", "labels2d"], "table"),
        ("seg_object_counts_match", "segeval", ["labels2d", "labels2d"], "table"),
        ("seg_score_card", "segeval", ["labels2d", "labels2d"], "table"),
    ],
    # 作る —— 真値つきの合成世界(segworld、2026-10-02。world_* はノブだけ、
    #   lens_area/voronoi_cells は真値の芯。新語なし: labels2d/table/scalar/points)
    "world": [
        ("world_blobs_touching", "segworld", [], "table"),
        ("world_grains_voronoi", "segworld", [], "table"),
        ("world_parts_with_shadow", "segworld", [], "table"),
        ("world_texture_regions", "segworld", [], "table"),
        ("world_gradient_illumination", "segworld", [], "table"),
        ("world_thin_structures", "segworld", [], "table"),
        ("lens_area", "segworld", [], "scalar"),
        ("voronoi_cells", "segworld", ["points"], "table"),
    ],
    # 輪郭を動かす —— 変分・動的輪郭とレベルセット(segcontour、2026-10-02 第 2 陣)。
    #   返りは全部 dict → table。snake の初期点 (N, 2) [row, col] は既存の pairs。
    #   level_set_reinit / curvature_flow は φ(実数、φ<0 が内側)もマスクも受けるが、
    #   image2d の種(0..1 の傾斜)は内側が無く fail-closed の ValueError → mask で宣言。
    "contour": [
        ("snake_evolve", "segcontour", ["image2d", "pairs"], "table"),
        ("gvf_field", "segcontour", ["image2d"], "table"),
        ("chan_vese_energy", "segcontour", ["image2d", "mask"], "table"),
        ("chan_vese_evolve", "segcontour", ["image2d", "mask"], "table"),
        ("morph_chan_vese", "segcontour", ["image2d", "mask"], "table"),
        ("morph_geodesic_ac", "segcontour", ["image2d", "mask"], "table"),
        ("edge_stop_g", "segcontour", ["image2d"], "table"),
        ("level_set_reinit", "segcontour", ["mask"], "table"),
        ("drle_evolve", "segcontour", ["image2d", "mask"], "table"),
        ("curvature_flow", "segcontour", ["mask"], "table"),
    ],
    # グラフと階層で分ける —— graph cut・α-expansion・SRM・成分木・準平坦領域・階層分水嶺・超画素
    #   (seggraph、2026-10-02 第 3 陣)。返りは全部 dict → table。単入力で走るように第 2 引数
    #   (alpha_expansion の means・area_opening_attr の threshold・quasi_flat_zones の alpha)は既定値つき。
    #   superpixel_quality だけ 2 枚のラベル画像(超画素, 真値)= score と同じ入口。
    "graph": [
        ("graph_cut_binary", "seggraph", ["image2d"], "table"),
        ("alpha_expansion", "seggraph", ["image2d"], "table"),
        ("statistical_region_merging", "seggraph", ["image2d"], "table"),
        ("max_tree", "seggraph", ["image2d"], "table"),
        ("area_opening_attr", "seggraph", ["image2d"], "table"),
        ("quasi_flat_zones", "seggraph", ["image2d"], "table"),
        ("alpha_tree", "seggraph", ["image2d"], "table"),
        ("hierarchical_watershed", "seggraph", ["image2d"], "table"),
        ("ultrametric_contour_map", "seggraph", ["image2d"], "table"),
        ("snic_superpixels", "seggraph", ["image2d"], "table"),
        ("quickshift", "seggraph", ["image2d"], "table"),
        ("superpixel_quality", "seggraph", ["labels2d", "labels2d"], "table"),
    ],
    # 閾値の 4 定理 —— 三角法・isodata・Kittler の最小誤差・Kapur の最大エントロピー(seggraph)。
    #   返りは threshold・mask・基準の曲線の dict → table(mask だけ返すと門が台帳から見えなくなる)。
    "threshold": [
        ("threshold_triangle", "seggraph", ["image2d"], "table"),
        ("threshold_isodata", "seggraph", ["image2d"], "table"),
        ("threshold_kittler", "seggraph", ["image2d"], "table"),
        ("threshold_kapur", "seggraph", ["image2d"], "table"),
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


OPSSEGMENTATION = _build()

#: 宣言 out 型と素の返りの橋渡し。**この族はどの op もタプルを返さない**ので空。
#: (空であること自体が「調べたうえで要らない」の記録 —— 他の族と同じ体裁)
RESULT_ADAPTERS: dict = {}


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSSEGMENTATION.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


def get(name):
    """op 名 → 実体(callable、素の返り型)。"""
    return OPSSEGMENTATION[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSSEGMENTATION[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSSEGMENTATION[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSSEGMENTATION.items() if m["func"] is None]


if __name__ == "__main__":
    print("opssegmentation: %d ops / %d categories" % (len(OPSSEGMENTATION), len(categories())))
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
    for cat in categories():
        print("  %-10s %s" % (cat, ", ".join(list_ops(cat))))
