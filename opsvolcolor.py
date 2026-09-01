# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsvolcolor — fullseye **ボクセルのラベル色分け** op の統一レジストリ。

動機は fullseye 自身の空白の実測(2026-09-02)。``volops.vol_label`` で 3-D 連結成分は
取れ、``volops.vol_region_props`` で成分ごとの定量値も取れるのに、**色を付ける手段が
2-D にしか無かった**(``imgio.colorize_labels`` は ``(H, W)`` 前提)。結果として
ボリュームを見る手順は「1 枚ずつ切ってから色を付ける」しかなく、その順序では
**スライスごとにラベル番号が振り直されるので同じ部品が層ごとに別の色になる**。
実測(16 球・``(24, 48, 48)`` の参照ファントム、seed=0):24 スライス中 **20 スライス**
で色が変わり、(成分, スライス) の変化は 108 組中 62 件、16 成分すべてが一度は変わる。
先にボリュームで色を付けてから切ると 3 つとも **0**。この差がこの族の存在理由で、
``vol_label_color_flicker`` がその差を**数える** op として台帳に載っている。

来歴は公開文献・公開実装のみ(``docs/PROVENANCE.md`` の naming rule に従い、特定の
製品・企業を動機にも名前にも使わない): ``scipy.ndimage.label``(Rosenfeld & Pfaltz,
JACM 1966 の N 次元版)/ Demantké *et al.*, ISPRS Laser Scanning 2011(共分散固有値
による linearity / planarity / isotropy)/ Porter & Duff, SIGGRAPH 1984(``over``
合成)/ Lorensen & Cline, SIGGRAPH 1987(marching cubes、``render3d`` 経由)。

既存資産との棲み分け(**再実装せず import して合成**):

  * **ラベリング本体**は ``volops.vol_label``。本モジュールは 1 度もラベリングしない
    (``vol_label_color_flicker`` が比較のために呼ぶだけ)。
  * **表面積と Wadell 球形度**は ``volops.vol_region_props``。成分ごとに marching
    cubes を回すので成分数に比例した Python ループが要る。``vol_label_shape_stats``
    は**線形時間で出せる量だけ**に絞った姉妹で、共通の 5 キー
    (``label`` / ``voxel_count`` / ``volume`` / ``centroid`` / ``bbox``)は
    **定義も値も厳密に一致**する(``tests/test_volcolor.py`` が固定)。
    球形度で選別したいときは ``vol_select_labels(labels, props=vol_region_props(...))``
    と**あちらの props を渡す** ―― 渡さずに ``min_sphericity`` を指定すると
    「キーが無い」で ValueError になる(既定値で埋めて一件も落ちないフィルタを
    黙って作らない)。
  * **2-D の色分け**は ``imgio.colorize_labels``。パレットは**同じ乱数列**で、
    ``vol_colorize_labels`` の出力は同じ配列に対する ``imgio.colorize_labels`` と
    ``np.array_equal`` で一致する(テストで固定)。片側だけ配色を変える改変は落ちる。
  * **メッシュ表示**は ``render3d``(``marching_cubes`` / ``render_mesh``)。
    ``vol_labels_to_meshes`` は成分ごとの bbox 部分体に marching cubes をかけて
    **色を添えて返すだけ**で、ラスタライズはしない。
  * **単純な z スライス送り / MPR / 再構成**は ``volprobe`` / ``volio`` /
    ``recon3d`` の担当。ここの ``vol_label_slice_rgb`` / ``vol_label_mpr_rgb`` は
    **色付きボリューム専用**(入力が ``(D, H, W, 3)``)で、グレーボリュームは扱わない。

使い方::

    import opsvolcolor
    opsvolcolor.list_ops("colorize")
    opsvolcolor.get("vol_colorize_labels")(labels, seed=0)
    opsvolcolor.call("vol_select_labels", labels, min_volume=50.0)   # 宣言型 labels
"""
import volcolor

_MOD = {"volcolor": volcolor}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
#   既存語彙の再利用: labels / voxel / rgbimage / matrix / table
#   新語彙: rgbvolume
#
# --------------------------------------------------------------------------
# 既存語彙をそのまま使った判断(新語を作らなかったもの)
# --------------------------------------------------------------------------
#   * labels  — 入口も出口もこれ。``volops.vol_label`` (out="labels") から直結し、
#     ``vol_select_labels`` は **labels -> labels**(ふるいにかけても型は同じ)。
#     ★ ただし既存 `labels` 述語は ``ndim >= 1`` で **2-D のラベル画像と 3-D の
#       ラベルボリュームが同居している**。本モジュールの 11 op は 2-D を渡されると
#       全部 ValueError になる(fail-closed)ので、**取り違えが黙って通ることは
#       無い**。危険なのは逆で、2-D の種しか無いプールでは 1 度も実行されないまま
#       「発見ゼロ」に見える —— opsphoton が counts で踏んだ罠と同じ形である。
#       配線側で 3-D ラベル種を必ず注ぐこと(下の「親が配線するとき」参照)。
#   * voxel   — ``vol_label_overlay`` が重ねる元のグレーボリューム、および
#     ``vol_label_color_flicker`` が受ける 2 値ボリューム。どちらも (D,H,W) の
#     既存 voxel 語彙そのもので、新語を作る理由が無い。
#   * rgbimage — 断面と投影の返り (H,W,3)。既存の rgbimage 消費 op(鏡面分離・
#     色変換・保存)がそのまま意味を持って使える。**ここが rgbvolume 語彙の出口**
#     なので、新語彙が袋小路にならない。
#   * matrix  — ``vol_label_palette`` の返り (n+1, 3)。2-D の実行列そのもの。
#   * table   — 形状統計 / 凡例 / ちらつき測定 / 色付きメッシュの集合。
#     ★ 「色付きメッシュの集合」に新語彙を作らなかったのは**実測の結果**である。
#       最初は `colormeshes` を足すつもりだったが、既存の table 消費 op を全部
#       洗って ``vol_labels_to_meshes`` の返りを渡したところ(2026-09-02 実測、
#       ops3d / ops1d / opsmath / opsoptics / opslightfield / opsphoton /
#       opsacoustics / opsinterferometry / opscadmap を横断)、table を食う op は
#       **3 件(abcd_matrix / wavefront_stats / istft)しかなく、3 件とも
#       ValueError で fail-closed**だった。つまり「混ぜると黙って間違う」条件を
#       満たさない。満たさないものに語彙を足すと、消費者ゼロの新語彙 = 袋小路が
#       1 つ増えるだけである(``docs/OP_COMBINATION_MATRIX.md`` の判断基準)。
#       なお個々のメッシュを ``mesh`` sort として下流へ流したいときは
#       ``[(m["vertices"], m["faces"]) for m in result]`` と剥がす —— 色を
#       捨てる操作なので、adapter で暗黙にはやらない。
#
# --------------------------------------------------------------------------
# 新語彙 1 つと、その理由(実測に基づく)
# --------------------------------------------------------------------------
#   * rgbvolume — **(D, H, W, 3) の色付きボリューム**。既存 `lightfield` の述語は
#     ``ndim == 4`` だけなので、色ボリュームは **lightfield を完全に満たす**。
#     実測(2026-09-02、``(8, 16, 16, 3)`` の色ボリュームを lightfield の op へ):
#       - ``lf_refocus`` / ``lf_subaperture`` / ``lf_epi`` / ``lf_depth_from_focus``
#         の **4 op が例外も NaN も出さず** (16, 3) の有限な結果を返す
#         (それぞれ「再フォーカス像」「部分開口像」「EPI」「深度」を名乗る)。
#         z 軸を角度軸 V、y 軸を角度軸 U として読んだ、意味の無い有限値である。
#       - ``lf_all_in_focus`` だけは引数不足で TypeError(型の話ではない)。
#     逆向き(ライトフィールドを ``vol_label_slice_rgb`` へ)は shape[3] != 3 で
#     fail-closed する。**安全なのは片側だけ**なので、実行時チェックには頼れない。
#     zscan を video から分けたのと同じ判断。
#     入口 = ``vol_colorize_labels`` (labels -> rgbvolume) と ``vol_label_overlay``
#     (voxel + labels -> rgbvolume)、出口 = ``vol_label_slice_rgb`` /
#     ``vol_label_mpr_rgb`` (-> rgbimage)。産む 2・食う 2 で袋小路にならない。
_CATALOG = {
    "palette": [
        # n_labels は必須スカラ。生成器は要らない(PARAM_HINTS で束縛する)
        ("vol_label_palette", "volcolor", [], "matrix"),
    ],
    "colorize": [
        ("vol_colorize_labels", "volcolor", ["labels"], "rgbvolume"),
        ("vol_label_overlay", "volcolor", ["voxel", "labels"], "rgbvolume"),
    ],
    "slice": [
        ("vol_label_slice_rgb", "volcolor", ["rgbvolume"], "rgbimage"),
        ("vol_label_mpr_rgb", "volcolor", ["rgbvolume"], "rgbimage"),
    ],
    "measure": [
        ("vol_label_shape_stats", "volcolor", ["labels"], "table"),
        ("vol_label_legend", "volcolor", ["labels"], "table"),
    ],
    "select": [
        # (labels_out, kept_ids) を返す。本体は labels なので adapter で剥がす
        ("vol_select_labels", "volcolor", ["labels"], "labels"),
    ],
    "render": [
        ("vol_labels_to_meshes", "volcolor", ["labels"], "table"),
        ("vol_label_volume_render", "volcolor", ["labels"], "rgbimage"),
    ],
    "diagnose": [
        ("vol_label_color_flicker", "volcolor", ["voxel"], "table"),
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


OPSVOLCOLOR = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSVOLCOLOR.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し(ops3d / ops1d / opsmath と同じ一級機構)。
#:
#: 1 件だけ。``vol_select_labels`` は ``(labels_out, kept_ids)`` を返す ――
#: 残った id は「何が落ちたか」を語る一級の情報なので**関数側では削らない**
#: (``ops3d`` が ``vol_label`` の ``(labels, n)`` に対して取ったのと同じ判断)。
#: 台帳の型を名乗る :func:`call` 側でだけ正典の並び(labels)を取り出す。
#:
#: 他の 10 op は宣言型そのもの(ndarray / list / dict)を素で返す設計にしてある。
#: とくに ``vol_label_legend`` は「表 + 画像」ではなく**表だけ**を返し、絵は
#: 呼び手が描く —— adapter を減らすためではなく、1 op = 1 量のほうが連鎖の
#: 型検査が厳しくなるからである。
RESULT_ADAPTERS = {
    "vol_select_labels": lambda r: r[0] if isinstance(r, tuple) else r,
}


def get(name):
    """op 名 → 実体(callable、素の返り型)。宣言型が欲しければ :func:`call`。"""
    return OPSVOLCOLOR[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSVOLCOLOR[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSVOLCOLOR[name]


def compatible(name):
    """name の出力種別を入力に取れる後続 op(op × op の連結候補)を列挙。"""
    out = OPSVOLCOLOR[name]["out"]
    return [n for n, m in OPSVOLCOLOR.items() if out in m["in"]]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSVOLCOLOR.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsvolcolor: {len(OPSVOLCOLOR)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
    for c in categories():
        print(f"  [{c}] {', '.join(list_ops(c))}")
