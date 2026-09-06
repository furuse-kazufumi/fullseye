# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsshapestat —— fullseye の形態統計 op の統一レジストリ。

実体は ``shapestats.py``(16 op / 5 カテゴリ)。台帳の役目は 3 つ:

1. **docs/ops へノートを出す**(``tools/opdocs.py`` の :data:`LEDGER_DIMS`)。
2. **連鎖ファザーに食わせる**(``typed_catalog.catalog()``)。載せないと
   「発見ゼロ」に見えるが実際には**一度も実行されていない**。
3. 宣言型と素の返りの橋渡し(:data:`RESULT_ADAPTERS`。この族は空)。

**登録面は 6 つある**(2026-09-06 に 1 つ増えたことが判明): この台帳 /
``tools/opdocs.LEDGER_DIMS`` / ``typed_catalog`` の登録と PARAM_HINTS /
``chain_fuzz.TYPE_CHECKS`` の述語 / ``opassist._LEDGERS`` / ``pyproject`` の
py-modules。どれか 1 つ落とすと静かな穴になる。
"""
import shapestats

_MOD = {"shapestats": shapestats}

# --------------------------------------------------------------------------- #
# 型語彙: **新語を 2 つ作る**。その判断の記録。
# --------------------------------------------------------------------------- #
# 基準はこの repo 共通の 1 つだけ ——
# 「混ぜたときに例外ではなく、もっともらしく間違った数値が出るか」。
# それに加えて、**その型の生産者と消費者が族の中に両方いるか**(片方しか
# いない型を作ると、プールが空のまま op が永久に未実行になる)。
#
#   * ``shapeset`` = ``(K, N, 3)`` の形の群。既存の型では表せない ——
#     ``voxel`` の述語(3 次元配列)には当たってしまうが、voxel は
#     ``(D, H, W)`` の濃度場で、これを K 個体 x N 点 x 3 座標と読み替えると
#     GPA が例外なしに無意味な平均を返す。生産者 ``shape_synth_family``、
#     消費者 ``generalized_procrustes`` / ``shape_mean`` / ``shape_pca`` が
#     族内に揃っているので、プールは空にならない。
#
#   * ``shapemodel`` = ``shape_pca`` の返す辞書。``table``(list か dict)にも
#     当たるが、``table`` プールには ``fit_zernike`` の係数表なども入る。
#     それを ``shape_reconstruct`` に渡すと KeyError で**うるさく落ちる**ので
#     「静かに間違う」条件は満たさない —— が、その代わり族の 5 op がほぼ全て
#     例外で終わり、ファザーの検査面としては死ぬ。**型を分ける理由は
#     「嘘を防ぐ」だけでなく「実際に走らせる」でもある**。生産者
#     ``shape_pca``、消費者 4 つが族内にいる。
#
#   * それ以外は既存の型で足りる: 形は ``points``(N,3)、変換は ``matrix``、
#     スコア列と偏差列は ``signal``(1-D)、距離は ``measurement``。
#     正中面を ``points`` と名乗らせなかったのは、(2,3) が形の述語に当たって
#     しまい、面を形として平均する連鎖が例外なしに通るため。
#
# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 合成 —— 真値を持つ形の群。族の入口(これが無いとプールが空になる)。
    "synth": [
        ("shape_synth_family", "shapestats", [], "shapeset"),
        ("shape_perturb", "shapestats", ["points"], "points"),
    ],
    # Procrustes —— 位置・向き・大きさを取り除く。
    "procrustes": [
        ("procrustes_fit", "shapestats", ["points", "points"], "matrix"),
        ("procrustes_align", "shapestats", ["points", "points"], "points"),
        ("procrustes_distance", "shapestats", ["points", "points"], "measurement"),
        ("generalized_procrustes", "shapestats", ["shapeset"], "shapeset"),
        ("shape_mean", "shapestats", ["shapeset"], "points"),
    ],
    # 統計形状モデル —— 群集平均と、そこからのずれ。
    "model": [
        ("shape_pca", "shapestats", ["shapeset"], "shapemodel"),
        ("shape_project", "shapestats", ["shapemodel", "points"], "signal"),
        ("shape_reconstruct", "shapestats", ["shapemodel", "signal"], "points"),
        ("shape_mahalanobis", "shapestats", ["shapemodel", "points"], "measurement"),
        ("shape_explained_variance", "shapestats", ["shapemodel"], "signal"),
        ("shape_synthesize", "shapestats", ["shapemodel"], "points"),
    ],
    # 左右対称性 —— ランドマークの対から正中面を出し、符号つきで測る。
    "symmetry": [
        ("mirror_plane_from_pairs", "shapestats", ["points"], "matrix"),
        ("landmark_asymmetry", "shapestats", ["points"], "signal"),
    ],
    # 面までの距離 —— 1-D の profile_deviation に対する 3-D 版。
    "deviation": [
        ("signed_surface_distance", "shapestats", ["points", "points"], "signal"),
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


OPSSHAPESTAT = _build()

#: 宣言 out 型と素の返りの橋渡し。**意図的に空** —— 16 op すべてが宣言どおりの
#: 値を 1 つだけ返す(実測で確認済み)。タプルを返す op も、旗で返り型が変わる
#: op もこの族には無い。将来足すなら、旗ではなく常にタプルを返す形にして
#: ここに ``_first`` を登録すること(``opsastrostack`` にその理由がある)。
RESULT_ADAPTERS = {}


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSSHAPESTAT.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


def get(name):
    """op 名 → 実体(callable、素の返り型)。"""
    return OPSSHAPESTAT[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSSHAPESTAT[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSSHAPESTAT[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSSHAPESTAT.items() if m["func"] is None]


if __name__ == "__main__":
    print("opsshapestat: %d ops / %d categories"
          % (len(OPSSHAPESTAT), len(categories())))
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
    for cat in categories():
        print("  %-11s %s" % (cat, ", ".join(list_ops(cat))))
