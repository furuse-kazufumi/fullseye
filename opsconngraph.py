# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsconngraph —— 結合グラフ(connectome)解析 op の統一レジストリ。

実体は ``conngraph.py``(23 op / 5 カテゴリ)。台帳の役目は 3 つ:
docs/ops へノートを出す・連鎖ファザーに食わせる・宣言型と素の返りを橋渡しする。

使い方::

    import opsconngraph
    opsconngraph.list_ops("stats")
    q = opsconngraph.call("graph_modularity", W, labels)

## なぜ族を分けたか(2026-09-20)

コネクトーム(神経の結合表)は重みつき有向グラフで、この repo の画像・点群・
信号のどの族にも収まらない。「connectome platform」の第 1 陣として、閉形式の
グラフ統計 + 帰無モデル + reservoir 計算 + Studio で見られる出口を 1 族にまとめた。
``opsmath``(一般の行列演算)に相乗りしなかったのは、隣接行列の意味論
(行 = pre、列 = post、対角 = 自己結合、NaN = 不明)が一般行列には無く、
混ぜると「行列の固有値」と「グラフのスペクトル」が同じ台帳で別の答えを
出すことになるから。

## 型語彙: 新語は 2 つ(``conn_graph`` / ``synapse_table``)。その判断の記録

基準はこの repo 共通の 1 つ ——「混ぜたときに例外ではなく、もっともらしく
間違った数値が出るか」。加えて**生産者と消費者が族の中に両方いるか**。

* ``conn_graph`` = float64 の n×n 正方行列、``W[i, j]`` = i → j の重み、NaN 禁止。
  既存の ``matrix``(任意の 2-D 配列)の述語には**当たってしまう**。だが逆向きに
  見ると: 一般の (m, p) 行列を媒介中心性やモジュラリティに渡しても、正方なら
  例外は出ず**「グラフの統計」がもっともらしく返る**(行と列が同じ集合を指して
  いないのに)。既存の ``graph`` 種は ``ops3d.knn_graph``(点群 → 近傍グラフ)
  1 op が産むだけで、隣接行列を**受ける**側が族の外に無い。ここでは
  生産者 5(``graph_from_synapses`` / ``graph_degree_preserving_shuffle`` /
  ``graph_binarize`` / ``reservoir_from_graph`` + 種)と消費者 17 が族の中に
  閉じ、出口(``points`` / ``image2d`` / ``table``)も持たせた。
* ``synapse_table`` = float64 の m×3(pre_id, post_id, count)。``points``
  ((N, 3) の xyz)と**形が同じ**なのが分ける理由そのもの: 点群を
  ``graph_from_synapses`` に渡すと座標が id として読まれ、例外なしに
  「もっともらしい隣接行列」が出る。id は 0 始まりの整数を float で持つ
  (CSV をそのまま渡せるように)。
* 分けなかった型: ノードごとの列は ``signal``(1-D float)、成分ラベルは
  ``labels``(1-D 整数)、次数表と辺の線分は ``table``(列名 → 配列の dict)、
  スカラは ``measurement``、reservoir の入出力は ``matrix``、配置は ``points``、
  隣接行列の絵は ``image2d`` —— いずれも既存の述語どおりで、混ぜても
  「型として正しい」ものはそのまま既存語彙に載せる。
* ``rgbvideo``(2026-09-20、activity カテゴリで 1 語追加)= float の (F, H, W, 3) 色動画。
  既存の ``video`` は (T, H, W) の灰色 1 チャネルで、``videops`` / ``motionmag`` が
  ndim == 3 を要求する。(F, H, W, 3) を ``video`` に載せると、時間フィルタが最後の軸を
  幅と読んで例外なしに「処理した動画」を返す側なので分ける。産むのは
  ``points_activity_video`` だけ、受ける op は無い(展示と Studio へ渡す出口)。
"""
import conngraph

_MOD = {"conngraph": conngraph}

# --------------------------------------------------------------------------
# 型語彙(上の docstring の判断のとおり)。in は常に list、out は 1 語。
# --------------------------------------------------------------------------
#   * conn_graph    — n×n の重みつき有向隣接行列(新語。理由は docstring)
#   * synapse_table — (m, 3) の (pre_id, post_id, count)(新語。points と同形)
#   * signal / labels / table / measurement / matrix / points / image2d — 既存
#
# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 作る —— シナプス表から隣接行列へ、帰無モデル、二値化。★カテゴリ名は docs/ops/conngraph/<category>/ に
    #   なる: "build" は .gitignore の build/ に当たり、ノート 3 枚が commit されず CI だけ赤になった(2026-09-20)
    "construct": [
        ("graph_from_synapses", "conngraph", ["synapse_table"], "conn_graph"),
        ("graph_degree_preserving_shuffle", "conngraph", ["conn_graph"], "conn_graph"),
        ("graph_binarize", "conngraph", ["conn_graph"], "conn_graph"),
    ],
    # 測る —— ノードごとの列(signal / labels / table)か、グラフ 1 つのスカラ
    "stats": [
        ("graph_degree_table", "conngraph", ["conn_graph"], "table"),
        ("graph_clustering_coefficient", "conngraph", ["conn_graph"], "measurement"),
        ("graph_betweenness", "conngraph", ["conn_graph"], "signal"),
        ("graph_laplacian_spectrum", "conngraph", ["conn_graph"], "signal"),
        ("graph_spectral_radius", "conngraph", ["conn_graph"], "measurement"),
        ("graph_components", "conngraph", ["conn_graph"], "labels"),
        ("graph_modularity", "conngraph", ["conn_graph", "labels"], "measurement"),
        ("graph_rich_club", "conngraph", ["conn_graph"], "measurement"),
        ("graph_motif_count", "conngraph", ["conn_graph"], "measurement"),
    ],
    # 計算する —— 結合行列を reservoir にして読み出す(echo state network)
    "reservoir": [
        ("reservoir_from_graph", "conngraph", ["conn_graph"], "conn_graph"),
        ("reservoir_states", "conngraph", ["conn_graph", "matrix"], "matrix"),
        ("reservoir_encode", "conngraph", ["conn_graph", "matrix"], "matrix"),
        ("ridge_readout", "conngraph", ["matrix", "matrix"], "matrix"),
        ("ridge_predict", "conngraph", ["matrix", "matrix"], "matrix"),
    ],
    # 見る —— Studio で見られる既存の型へ(点群・線分の表・画像)
    "view": [
        ("graph_layout_spectral", "conngraph", ["conn_graph"], "points"),
        ("graph_edges_as_lines", "conngraph", ["conn_graph", "points"], "table"),
        ("graph_adjacency_image", "conngraph", ["conn_graph"], "image2d"),
    ],
    # 活動 —— 状態列 (T, n) を「いつ・どこで点いたか」に読み、座標に載せて回す(2026-09-20)
    "activity": [
        ("graph_activation_latency", "conngraph", ["matrix"], "labels"),
        ("graph_activity_spread", "conngraph", ["matrix", "points", "labels"], "table"),
        ("points_activity_video", "conngraph", ["points", "matrix"], "rgbvideo"),
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


OPSCONNGRAPH = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSCONNGRAPH.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し。**空 — 意図的に**。23 op はすべて宣言型どおり
#: (ndarray / dict / float)を素で返すので、adapter を挟まないほうが連鎖ファザーの
#: 検証が最も厳しい(素の返りをそのまま宣言と突き合わせる)。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable)。"""
    return OPSCONNGRAPH[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、台帳の宣言 out 型どおりの値を返す(adapter 適用)。"""
    result = OPSCONNGRAPH[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSCONNGRAPH[name]


def missing():
    """レジストリに載っているが実体が見つからない op。"""
    return [n for n, m in OPSCONNGRAPH.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsconngraph: {len(OPSCONNGRAPH)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
