# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opscadmap — fullseye「画像 → CAD 面」逆写像 op の統一レジストリ。

動機(2026-09-02)は fullseye 自身の空白の実測(`docs/INDUSTRY_SIGNALS.md` §3 の
行 6)。3-D 側には ``align_cad_to_scan`` / ICP 3 種 / ``ppf`` 一式があり、
**姿勢は出せる**。だが「2-D 画像上で見つけた欠陥が CAD 面上のどの座標か」に
落とす逆写像が 3 つの在庫表面すべてで 0 件だった。本レジストリはその出口
(cadmap.py、4 op / 4 カテゴリ)。

来歴は公開文献のみ(`docs/PROVENANCE.md` の naming rule に従い、特定の製品・
企業を動機にも名前にも使わない): Möller & Trumbore, *J. Graphics Tools* 1997
(光線×三角形)/ Hartley & Zisserman 2004 §6.1(ピンホールの投影と逆投影)/
Catmull 1974(最近傍のみ可視という遮蔽規約)。

既存資産との棲み分け(**再実装せず import して合成**):
  * カメラ規約 = camera(``intrinsic_matrix`` / ``project_points``)。cadmap は
    **camera.py の OpenCV 系規約(+Z 前方・画素中心は整数座標)に合わせてある**。
    ``render3d`` は -Z 前方・画素中心は半整数で、混ぜると黙って符号と半画素が
    ずれる。順方向の投影は ``camera.project_points`` をそのまま呼んでいる。
  * mesh の形と索引の検証 = ``render3d._mesh_arrays``、K の検証 =
    ``render3d._check_intrinsics``、K の生成 = ``render3d.intrinsics_from_fov``。
    どれも再実装していない(二重実装は片方だけ直る事故になる)。
  * ``render3d.render_mesh`` は **ラスタライザ**(全画素の depth 画像)。cadmap は
    **任意の画素だけを問い合わせる**逆向きで、しかも face_id と重心座標を返す。
    depth 画像しか要らないなら render_mesh のほうが速い。
  * 姿勢を**求める**のは pipeline3d / registration / ppf の仕事。cadmap は姿勢を
    **既知として受け取る**側で、一度も推定しない。

使い方::

    import opscadmap
    opscadmap.list_ops("raycast")
    opscadmap.get("cad_pixel_to_surface")((V, F), uv, K=K, R=R, t=t)
"""
import cadmap

_MOD = {"cadmap": cadmap}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
#
# --------------------------------------------------------------------------
# **新語彙を 1 つも足していない**。その判断の根拠(実測)
# --------------------------------------------------------------------------
# 追加の基準は既存台帳と同じ「既存語彙で宣言すると型レベルの嘘になるか」だが、
# ここでは 4 op すべてが既存 sort にそのまま収まった:
#
#   * mesh   — 入力はすべて ``(V, F)`` タプル = 本 repo の ``mesh`` sort そのもの
#     (``meshrepair.convex_hull`` の返りと同じ形)。**mesh は 1 引数で受ける**
#     ようにしてある。これは意図的で、既存の 3d 族には ``mesh_to_voxel(vertices,
#     faces, ...)`` のように **(V, F) を 2 つの位置引数に割る** op があり、連鎖
#     ファザーは 1 入力種別につき 1 位置引数しか割り当てないので、2 番目の
#     ``faces`` が必須引数として残り ``PARAM_HINTS`` にも無く、**その op は
#     一度も実行されない**(実測: ``chain_fuzz.catalog()`` の mesh 入力 15 op の
#     うち 2 引数型がこの状態)。cadmap はその罠を踏まない形にしてある。
#   * keypoints — ``cad_pixel_to_surface`` の画素 (N,2)。既存生成器
#     ``rng.random((160,2)) * 32`` がそのまま食える。
#   * points  — ``cad_surface_to_pixel`` の 3-D 点 (N,3)。既存生成器あり。
#   * labels  — ``cad_defect_to_cad`` の欠陥ラベル画像 (H,W)。既存の
#     セグメンテーション op の出力がそのまま入口になる。float ラベルも
#     **値が整数なら**受ける(連結成分を float で返す op が実在するため)。
#   * table   — 画素→面の記録(dict)と欠陥表(list of dict)。
#   * indices — ``cad_visible_faces`` の返りは 1-D の面 ID 配列。
#
# --------------------------------------------------------------------------
# 到達可能性(狭い sort にしないための確認、実測 2026-09-02)
# --------------------------------------------------------------------------
# ``mesh`` は**既に到達可能**である。``chain_fuzz.make_generators()`` に mesh の
# 種は無いが、``convex_hull`` (points -> mesh) / ``voxel_to_mesh`` (voxel -> mesh)
# / ``poisson_lite`` / ``alpha_shape_mesh`` が産むので、型到達可能性の不動点
# 計算では mesh は到達側に入る(実測)。したがって cadmap の 4 op は
# 「産む入口が無くて永久に到達不能」にはならない。
#
# ただし **``mesh`` は ``TYPE_CHECKS`` に述語を持たない**(実測)。これは
# 「宣言 out が mesh の op が何を返しても TYPEMISS にならない」ということで、
# 型の嘘が検出されない穴になっている。述語と種の提案は下の
# ``SUGGESTED_TYPE_CHECK`` / ``SUGGESTED_GENERATOR`` に置いた(配線は親が行う)。
_CATALOG = {
    "raycast": [
        ("cad_pixel_to_surface", "cadmap", ["mesh", "keypoints"], "table"),
    ],
    "project": [
        ("cad_surface_to_pixel", "cadmap", ["mesh", "points"], "table"),
    ],
    "defect": [
        ("cad_defect_to_cad", "cadmap", ["mesh", "labels"], "table"),
    ],
    "visibility": [
        ("cad_visible_faces", "cadmap", ["mesh"], "indices"),
    ],
}


#: ``tools/chain_fuzz.py`` の ``TYPE_CHECKS`` へ足すことを提案する述語
#: (**配線は親が行う。ここは提案の置き場で、import しても副作用は無い**)。
#: mesh = ``(V (nv,3) float, F (nf,3) int)`` のタプル。GPU backend を持つ op は
#: torch.Tensor を返す約束があるので、``pose`` の述語と同じく **型ではなく形**で
#: 判定する。
SUGGESTED_TYPE_CHECK = {
    "mesh": lambda v: isinstance(v, (tuple, list)) and len(v) == 2
    and len(getattr(v[0], "shape", ())) == 2 and tuple(v[0].shape)[1:] == (3,)
    and len(getattr(v[1], "shape", ())) == 2 and tuple(v[1].shape)[1:] == (3,),
}

#: ``tools/chain_fuzz.py`` の ``make_generators()`` へ足すことを提案する種。
#: **3 種を必ず混ぜる**: 閉じた凸包 / 閉じた直方体(巻きが厳密に外向き)/
#: 開いた平面パッチ(miss と裏面の経路を通す)。片方だけだと ``cull_backfaces``
#: と miss の分岐が一度も踏まれない。
def _suggested_mesh_generator(rng):
    import numpy as np
    r = rng.random()
    if r < 0.5:
        import meshrepair
        return meshrepair.convex_hull(rng.random((60, 3)) * 10.0)
    if r < 0.8:
        h = 1.0 + rng.random(3) * 3.0
        V = np.array([[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
                      [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]], float) * h
        F = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7],
                      [0, 1, 5], [0, 5, 4], [3, 7, 6], [3, 6, 2],
                      [0, 4, 7], [0, 7, 3], [1, 2, 6], [1, 6, 5]], np.int64)
        return V, F
    a, b = 1.0 + 3.0 * rng.random(2)
    V = np.array([[-a, -b, 0.0], [a, -b, 0.0], [a, b, 0.0], [-a, b, 0.0]])
    return V, np.array([[0, 2, 1], [0, 3, 2]], np.int64)


def _suggested_labels_generator(rng):
    """2-D 整数ラベル画像(欠陥領域 2-3 個 + 背景 0)。

    **これが無いと ``cad_defect_to_cad`` は永久に実行されない**(実測)。
    ``labels`` を出す既存 op は 7 つあるが、``label_components`` /
    ``vol_label`` / ``vol_watershed`` は **(D,H,W) の 3-D**、``region_growing`` /
    ``euclidean_cluster`` / ``plane_segmentation`` / ``segment_rigid_motions``
    は **(N,) の 1-D** で、**2-D のラベル画像を産む op が 1 つも無い**。
    その結果 1200 連鎖で ``cad_defect_to_cad`` は 2 回しか引かれず、2 回とも
    ``labels must be a 2-D (H, W) label image, got (160,)`` で fail-closed し、
    **一度も実行されないまま「発見ゼロ」に見えた**。
    (同じ穴は既存の ``illuminant_from_dichromatic_planes`` も踏んでいるはずで、
    あちらは専用 arg builder で自前のラベルを作って回避している。)

    ★ 注意: この種を入れると ``vol_region_props``(3-D ラベルを期待)に 2-D が
    渡る組が生まれ、CONTRACT が出る可能性がある。それは**回帰ではなく発見**で、
    どちらの型が正典かを決めるのは親の仕事。
    """
    import numpy as np
    h = int(rng.integers(24, 49))
    w = int(rng.integers(24, 49))
    lab = np.zeros((h, w), np.int32)
    for k in range(1, int(rng.integers(2, 4))):
        r0 = int(rng.integers(0, h - 6))
        c0 = int(rng.integers(0, w - 6))
        lab[r0:r0 + int(rng.integers(3, 7)), c0:c0 + int(rng.integers(3, 7))] = k
    return lab


SUGGESTED_GENERATOR = {"mesh": _suggested_mesh_generator,
                       "labels": _suggested_labels_generator}

#: 非有限を **docstring で契約している** op(``chain_fuzz.NONFINITE_BY_CONTRACT``
#: へ足す必要がある)。実測: これを足さないと ``cad_pixel_to_surface`` は
#: 「当たらない画素は NaN」という文書化済みの返りのせいで毎回 NONFINITE 判定に
#: なり、pool にも trace にも入らず**実行されていないように見える**。
#:   * ``cad_pixel_to_surface`` — miss の ``bary``/``point``/``depth`` が NaN。
#:   * ``cad_defect_to_cad`` — 当たり 0 の領域の ``centroid``/``depth_mean`` が NaN。
#: ``cad_surface_to_pixel`` と ``cad_visible_faces`` は非有限を返さない。
NONFINITE_BY_CONTRACT = {"cad_pixel_to_surface", "cad_defect_to_cad"}


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


OPSCADMAP = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSCADMAP.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し(ops3d / opsmath / opsoptics / opsinterferometry
#: と同じ一級機構)。
#:
#: **現在は空 — 意図的に**。cadmap の 4 op はすべて宣言型そのもの(dict /
#: list of dict / ndarray)を素で返す。空にしておくと :func:`call` は :func:`get`
#: と同じ値を返し、連鎖ファザーの TYPEMISS 検査が**素の返りをそのまま**宣言と
#: 突き合わせる = 検証が最も厳しい。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable、素の返り型)。宣言型が欲しければ :func:`call`。"""
    return OPSCADMAP[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSCADMAP[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSCADMAP[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSCADMAP.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opscadmap: {len(OPSCADMAP)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
