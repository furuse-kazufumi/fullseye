# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsreprconv — fullseye 表現変換 op の統一レジストリ(reprconv.py の台帳)。

動機(2026-09-02)は ``tools/chain_fuzz.py`` の台帳 515 op に対する機械集計。
「単入力かつ in 型 ≠ out 型 = 変換」で数えると変換ペアは 121 種あったが、
**他型へ一歩も出られない型**が 25 個も残っていた(主なもの):

    pairs 0/5 · indices 0/3 · curvature 0/3 · descriptor 0/3 · keypoints 0/2 ·
    normals 0/2 · position 0/2 · pointmap 0/1 · roots 0/1 · flow 0/0 ·
    gaussians 0/0 · score 0/0 · cscalar 0/0 · countrate 0/0 · angle 0/0 ·
    shift 0/0 · rot_scale 0/0 · deformation 0/0 · poly_surface 0/0 ·
    bspline_surface 0/0                                (出る / 来る)

産む op はあるのに食う op が無い型 = **死んだ語彙**。この台帳の 42 op は
そのうち **16 型** に出口を作った(袋小路 25 型 -> 9 型、変換ペア 121 -> 159 種。
実測は ``python opsreprconv.py`` と本モジュール末尾の ``conversion_edges``)。
``gaussians`` と ``score`` については **産む op すら 1 つも無かった**ので入口も
作った(入口と消費側は必ず一緒に、がこの repo の規律 — opsmotionmag の
``video``、opsphoton の ``histcube`` と同じ)。

**残した袋小路 9 型と、埋めなかった理由**(埋めないことも判断である):

* ``poly_surface`` / ``bspline_surface`` —— 当てはめた曲面の係数記録で、
  **唯一の正直な出口は「評価する」こと**。それは既存の ``eval_poly_surface`` /
  ``eval_bspline_surface``(格子 2 枚と一緒に食う 3 入力 op)がすでに持っている。
  単入力の変換を足すなら「係数を table にする」しか無く、それは変換ではなく
  梱包の付け替えで、下流の誰も係数 dict を使わない。
* ``gradient`` / ``hessian`` —— ``vol_gradient`` / ``vol_hessian`` の産物で、
  実体は多成分の体積。出口を作るなら ``flow`` と同じ「大きさ」「向きの色」に
  なるが、**``flow`` で作った 2 op と数値的に同じもの**になる。同じ計算を
  別名で 2 度置くのは語彙を増やしたことにならない(``flow_magnitude`` の
  入力形を広げるほうが筋で、それは既存 op の宣言変更なので担当外)。
* ``pointmap`` —— 既に ``depth`` / ``points`` / ``normalmap`` と相互に行き来する
  経路が別の op 群にある(``depth_to_organized_points`` の逆は
  ``pointmap`` の第 3 成分を取るだけ)。単入力 1 本足すより、既存の
  organized 系の宣言を見直すほうが効く。
* ``roots`` —— 多項式の**順序に意味の無い解集合**。``cpoints``(順序つき閉曲線)へ
  流したくなるが、順序を勝手に付けると周回積分・巻き数が**もっともらしく
  間違う**(``cpoints`` の述語コメントが書いているとおり)。
  型を分けてある意図を壊すので足さない。
* ``axes`` / ``frame`` / ``graph`` —— 産む op が 1 つずつしかなく、いま何が
  入っているかを実測していない。**実測せずに変換を書くのが一番危ない**ので、
  ここは空けたまま報告する。

## 新しい型語彙を 1 つも作っていない(意図的)

opsphoton の ``histcube``、opsmotionmag の ``video``、opsinterferometry の
``zscan`` は「既存型に相乗りさせると**黙って間違った数字**が出る」ことを実測で
示してから型を足した。本モジュールにはその根拠が 1 件も無い —— 42 op すべての
入出力が既存語彙にそのまま収まるので、語を足せば守るものが無いまま連鎖だけが
細る。**足さない理由を書いておくのが台帳の仕事**である。

代わりに本モジュールが持ち込むのは **述語と種**のほうで、下の
``TYPE_CHECK_PROPOSALS`` / ``GENERATOR_PROPOSALS`` に置いてある
(chain_fuzz への配線は親が行う。本モジュールは既存ファイルを一切変更しない)。

## 実測した既存の型の嘘(**修正していない。報告だけ**)

* ``flow`` は **2 つの別物**が同じ型名で同居している。``scene_flow_lk`` は
  **(3, D, H, W)** の密フロー(成分 dz, dy, dx)、``estimate_flow`` /
  ``nearest_neighbor_flow`` / ``smooth_flow`` は **(N, 3)** の散在フロー。
  ``TYPE_CHECKS`` に ``flow`` の述語が無いので**どちらも黙って同じプールに入る**。
* ``curvature`` は **3 つの別物**。``principal_curvatures`` = 2-tuple の (N,) /
  ``vertex_curvature`` = (nv,) / ``curvature_maps`` = **4 本の torch.Tensor**
  のタプル。述語なし。
* ``descriptor`` は配列と dict が混在(``fit_zernike`` は ``{(n,m): 係数}``)。述語なし。
* ``pairs`` の述語は ``lambda v: True`` —— **何も検査していない**。実際
  ``stat_histogram`` は長さ **10 と 11** の 2 本を返し、これは「対」ではない。
* ``keypoints`` の軸は **(u, v) = (列, 行)**(``project_points``)、``points`` の
  軸は **(z, y, x)**(``fuse3d.to_points``)。同じ 3-D 空間の話なのに流儀が違う。

## 使い方

    import opsreprconv
    opsreprconv.list_ops("direction")
    opsreprconv.call("normals_to_angles", normals)
    opsreprconv.roundtrips()          # 往復ペアの宣言(可逆 / 不可逆 / 一方向)
"""
import reprconv

_MOD = {"reprconv": reprconv}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
# **新語彙ゼロ**。全部が既存型(理由はモジュール docstring)。
_CATALOG = {
    # 方向: normals と pairs の相互変換 + 拡張ガウス像
    "direction": [
        ("normals_to_angles", "reprconv", ["normals"], "pairs"),
        ("angles_to_normals", "reprconv", ["pairs"], "normals"),
        ("normals_to_egi", "reprconv", ["normals"], "image2d"),
    ],
    # 曲率: 形状指数(Koenderink)と統計
    "curvature": [
        ("curvature_to_shape_index", "reprconv", ["curvature"], "pairs"),
        ("shape_index_to_curvature", "reprconv", ["pairs"], "curvature"),
        ("curvature_to_table", "reprconv", ["curvature"], "table"),
    ],
    # 記述子: 行列語彙への梱包(SVD/pinv/cond がそのまま掛かる)
    "descriptor": [
        ("descriptor_to_matrix", "reprconv", ["descriptor"], "matrix"),
        ("matrix_to_descriptor", "reprconv", ["matrix"], "descriptor"),
        ("descriptor_to_table", "reprconv", ["descriptor"], "table"),
    ],
    # 画像座標 <-> 3-D。**軸の約束が op 名に書いてある**
    "keypoint": [
        ("keypoints_uv_to_points", "reprconv", ["keypoints"], "points"),
        ("points_zyx_to_keypoints_uv", "reprconv", ["points"], "keypoints"),
        ("keypoints_to_image2d", "reprconv", ["keypoints"], "image2d"),
        ("keypoints_from_image2d", "reprconv", ["image2d"], "keypoints"),
        ("position_to_points", "reprconv", ["position"], "points"),
        ("points_to_position", "reprconv", ["points"], "position"),
    ],
    # 添字と選択
    "index": [
        ("indices_to_labels", "reprconv", ["indices"], "labels"),
        ("labels_to_indices", "reprconv", ["labels"], "indices"),
        ("select_points", "reprconv", ["points", "indices"], "points"),
    ],
    # 対
    "pairs": [
        ("pairs_to_signal", "reprconv", ["pairs"], "signal"),
        ("pairs_to_image2d", "reprconv", ["pairs"], "image2d"),
        ("pairs_to_table", "reprconv", ["pairs"], "table"),
    ],
    # フロー。**密と散在で型が分かれた**(2026-09-02)。もともと `flow` という
    # 1 つの型名の下に別物が 2 つ同居していて、述語も無かったので**どちらも黙って
    # 同じプールに入っていた**。分割の根拠は実測 ―― 4 つの消費 op に両方の形を
    # 渡すと、密用 2 op は散在を、散在用 2 op は密を、それぞれ名指しで拒否する。
    # **どの 1 つの値も両方を満たせない**ので 1 つの述語では書けない。
    "flow": [
        ("flow_magnitude", "reprconv", ["flow_dense"], "voxel"),
        ("flow_to_rgbimage", "reprconv", ["flow_dense"], "rgbimage"),
        ("flow_speed", "reprconv", ["flow_scattered"], "signal"),
        ("flow_apply", "reprconv", ["points", "flow_scattered"], "points"),
    ],
    # ガウシアン。**入口が無かった型**なので points_to_gaussians が入口
    "gaussians": [
        ("points_to_gaussians", "reprconv", ["points"], "gaussians"),
        ("gaussians_to_points", "reprconv", ["gaussians"], "points"),
        ("gaussians_to_voxel", "reprconv", ["gaussians"], "voxel"),
    ],
    # スコア volume。**入口が無かった型**なので correlation_score が入口
    "score": [
        ("correlation_score", "reprconv", ["voxel", "voxel"], "score"),
        ("score_to_position", "reprconv", ["score"], "position"),
        ("score_to_image2d", "reprconv", ["score"], "image2d"),
    ],
    # 小さな代数。**軸と単位の規律を機械検査するための面**
    "algebra": [
        ("angle_to_matrix", "reprconv", ["angle"], "matrix"),
        ("matrix_to_angle", "reprconv", ["matrix"], "angle"),
        ("rot_scale_to_matrix", "reprconv", ["rot_scale"], "matrix"),
        ("matrix_to_rot_scale", "reprconv", ["matrix"], "rot_scale"),
        ("shift_to_vector", "reprconv", ["shift"], "vector"),
        ("vector_to_shift", "reprconv", ["vector"], "shift"),
        ("cscalar_to_polar", "reprconv", ["cscalar"], "pairs"),
        ("polar_to_cscalar", "reprconv", ["pairs"], "cscalar"),
        ("countrate_to_counts", "reprconv", ["countrate"], "counts"),
        ("counts_to_countrate", "reprconv", ["counts"], "countrate"),
        ("deformation_to_points", "reprconv", ["deformation"], "points"),
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


OPSREPRCONV = _build()


#: 往復の宣言。``tests/test_reprconv.py`` がこの表をそのまま回して検証する
#: —— **表と実装が一致していること自体がテスト対象**なので、片方だけ直すと落ちる。
#:
#: ``exact`` = 往復して ``tol`` 以下 / ``lossy`` = 何が落ちるかを ``lost`` に明記 /
#: ``oneway`` = 逆を**作らない**(統計・射影は情報を捨てるのが仕事で、逆を作ると
#: 「戻せるふり」という別種の嘘になる)。
ROUNDTRIPS = (
    {"forward": "normals_to_angles", "backward": "angles_to_normals",
     "kind": "exact", "tol": 1e-12,
     "note": "方向は厳密に戻る。戻らないのは長さだけ(法線は向き)"},
    {"forward": "curvature_to_shape_index", "backward": "shape_index_to_curvature",
     "kind": "exact", "tol": 1e-12,
     "note": "atan2 形なので臍点・平面でも厳密。戻らないのは (k1,k2) の入力順だけ"},
    {"forward": "descriptor_to_matrix", "backward": "matrix_to_descriptor",
     "kind": "exact", "tol": 0.0, "note": "1-D は (1,n) を経て (n,) へ bit 一致で戻る"},
    {"forward": "keypoints_uv_to_points", "backward": "points_zyx_to_keypoints_uv",
     "kind": "exact", "tol": 0.0, "note": "(u,v) -> (z,y,x) -> (u,v) は bit 一致"},
    {"forward": "points_zyx_to_keypoints_uv", "backward": "keypoints_uv_to_points",
     "kind": "lossy", "lost": "z 列(逆向きでは既定 z=0 が入る)"},
    {"forward": "keypoints_to_image2d", "backward": "keypoints_from_image2d",
     "kind": "lossy",
     "lost": "画素格子への量子化(軸あたり RMS 0.2835 px、理論 1/sqrt(12)=0.2887)"
             " + 8 近傍で融合した点"},
    {"forward": "indices_to_labels", "backward": "labels_to_indices",
     "kind": "exact", "tol": 0.0, "note": "重複と順序を除いて bit 一致"},
    {"forward": "labels_to_indices", "backward": "indices_to_labels",
     "kind": "lossy", "lost": "末尾の背景(長さが max_index+1 に切り詰まる)と元の shape"},
    {"forward": "position_to_points", "backward": "points_to_position",
     "kind": "exact", "tol": 0.0, "note": "N=1 のときだけ"},
    {"forward": "points_to_position", "backward": "position_to_points",
     "kind": "lossy", "lost": "重心まわりの広がり(N 点 -> 1 点)"},
    {"forward": "points_to_gaussians", "backward": "gaussians_to_points",
     "kind": "exact", "tol": 0.0, "note": "中心 mu は bit 一致。sigma/w は往復で消える追加情報"},
    {"forward": "gaussians_to_voxel", "backward": None, "kind": "lossy",
     "lost": "3σ の箱打ち切り(erf(3/√2)³ = 99.192%)+ 中点則の格子求積 + 境界の切り落とし"},
    {"forward": "angle_to_matrix", "backward": "matrix_to_angle",
     "kind": "exact", "tol": 1e-10, "note": "度。(-180, 180] の範囲で"},
    {"forward": "rot_scale_to_matrix", "backward": "matrix_to_rot_scale",
     "kind": "exact", "tol": 1e-10, "note": "度 + 無次元の倍率"},
    {"forward": "shift_to_vector", "backward": "vector_to_shift",
     "kind": "exact", "tol": 0.0, "note": "整数を入れた往復のみ"},
    {"forward": "vector_to_shift", "backward": "shift_to_vector",
     "kind": "lossy", "lost": "最近接整数への丸め残差(各軸 <= 0.5)"},
    {"forward": "cscalar_to_polar", "backward": "polar_to_cscalar",
     "kind": "exact", "tol": 1e-12, "note": "角度は度"},
    {"forward": "countrate_to_counts", "backward": "counts_to_countrate",
     "kind": "exact", "tol": 1e-15, "note": "相対公差。[Hz] x [s] = [counts]"},
    {"forward": "normals_to_egi", "backward": None, "kind": "lossy",
     "lost": "方向の binning(既定 36x18、最頻 bin と真の向きの差 3.7 度)"},
    {"forward": "flow_magnitude", "backward": None, "kind": "oneway",
     "lost": "向き 2 自由度(大きさだけ残る)"},
    {"forward": "flow_to_rgbimage", "backward": None, "kind": "oneway",
     "lost": "dz 成分と、選ばなかった z スライス全部"},
    {"forward": "flow_speed", "backward": None, "kind": "oneway", "lost": "向き 2 自由度"},
    {"forward": "score_to_position", "backward": None, "kind": "oneway",
     "lost": "ピーク以外の全体(1 位置から volume は戻せない)"},
    {"forward": "score_to_image2d", "backward": None, "kind": "oneway",
     "lost": "潰した軸(最大値投影)"},
    {"forward": "curvature_to_table", "backward": None, "kind": "oneway",
     "lost": "各要素の値(統計だけ残る)"},
    {"forward": "descriptor_to_table", "backward": None, "kind": "oneway",
     "lost": "各要素の値"},
    {"forward": "pairs_to_table", "backward": None, "kind": "oneway", "lost": "各要素の値"},
    {"forward": "pairs_to_signal", "backward": None, "kind": "oneway",
     "lost": "列 0(x)。等間隔でない x を持つ対では**位置情報そのもの**"},
    {"forward": "pairs_to_image2d", "backward": None, "kind": "oneway",
     "lost": "bin 幅ぶんの量子化と、正規化で捨てた絶対スケール"},
    {"forward": "deformation_to_points", "backward": None, "kind": "oneway",
     "lost": "TPS の重み w とアフィン項 a"},
)


#: 親が ``tools/chain_fuzz.py`` へ配線するための **TYPE_CHECKS 追加提案**。
#: いま述語が無い型は「宣言 out 型が何であっても TYPEMISS にならない」穴なので、
#: 変換 op を足すと同時に述語を足さないと、**検査面を増やしたつもりで増えない**。
#:
#: ★``flow`` は **1 つの述語では書けない**。密 (3,D,H,W) と散在 (N,3) が同じ型名で
#: 同居しているため、両方を通す述語にすると何も守らず、片方に決めると既存の
#: 4 op のうちどれかが必ず TYPEMISS になる。**分けるのが正しい**(``video`` を
#: ``voxel`` から分けたのと同じ判断)が、それは既存 op の宣言を書き換える作業で
#: 本モジュールの担当外なので、ここでは提案だけ置く。
TYPE_CHECK_PROPOSALS = {
    "position": "lambda v: isinstance(v, (tuple, list, np.ndarray)) "
                "and np.shape(v) == (3,) and not isinstance(v[0], np.ndarray)",
    "curvature": "lambda v: (isinstance(v, np.ndarray) and v.ndim in (1, 2)) "
                 "or (isinstance(v, tuple) and len(v) == 2 "
                 "and all(getattr(x, 'ndim', None) == 1 for x in v))",
    "descriptor": "lambda v: isinstance(v, np.ndarray) and v.ndim in (1, 2)",
    "pairs": "lambda v: (isinstance(v, np.ndarray) and v.ndim == 2 and v.shape[1] == 2) "
             "or (isinstance(v, tuple) and len(v) == 2 "
             "and getattr(v[0], 'shape', None) == getattr(v[1], 'shape', None))",
    "gaussians": "lambda v: isinstance(v, dict) and {'mu', 'sigma', 'w'} <= set(v)",
    "deformation": "lambda v: isinstance(v, dict) and 'ctrl' in v",
    "shift": "lambda v: isinstance(v, (tuple, list)) and len(v) == 3 "
             "and all(isinstance(x, (int, np.integer)) for x in v)",
    "rot_scale": "lambda v: isinstance(v, (tuple, list)) and len(v) == 2 "
                 "and all(isinstance(x, (int, float, np.floating)) for x in v)",
    "angle": "lambda v: isinstance(v, (int, float, np.floating, np.integer))",
    # 分割してから述語を書くべきもの(下の DENSE/SCATTERED は分割後の案)
    "flow_dense": "lambda v: isinstance(v, np.ndarray) and v.ndim == 4 and v.shape[0] == 3",
    "flow_scattered": "lambda v: isinstance(v, np.ndarray) and v.ndim == 2 and v.shape[1] == 3",
}

#: 親が ``tools/chain_fuzz.py`` の ``make_generators()`` へ足すための **種の提案**。
#: 既存の種が無い型は「同じ連鎖の中で先に生成 op が引かれた場合だけ」到達するので、
#: 実測では「一度も実行されないまま発見ゼロ」になる(keypoints で実測済みの罠)。
GENERATOR_PROPOSALS = {
    # (N,2) の主曲率対。**臍点 (k1 == k2) と平面 (0, 0) を必ず混ぜる** ——
    # 除算で書かれた形状指数はそこでだけ NaN を出すので、混ぜないと踏めない
    "curvature": "lambda rng: (lambda k: np.stack([k.max(1), k.min(1)], 1))("
                 "np.concatenate([rng.standard_normal((40, 2)), "
                 "np.repeat(rng.standard_normal((6, 1)), 2, axis=1), np.zeros((2, 2))]))",
    "descriptor": "lambda rng: rng.standard_normal(int(rng.integers(16, 132)))",
    "pairs": "lambda rng: np.stack([np.arange(64.0), rng.standard_normal(64)], 1)",
    "indices": "lambda rng: np.unique(rng.integers(0, 160, size=32))",
    "position": "lambda rng: (float(rng.uniform(0, 15)), float(rng.uniform(0, 15)), "
                "float(rng.uniform(0, 15)))",
    "gaussians": "lambda rng: reprconv.points_to_gaussians(rng.random((64, 3)) * 10.0)",
    "score": "既存の _score_volume をそのまま使う(異方性ガウス山)",
    "cscalar": "lambda rng: complex(rng.standard_normal(), rng.standard_normal())",
    "shift": "lambda rng: tuple(int(x) for x in rng.integers(-4, 5, size=3))",
    "rot_scale": "lambda rng: (float(rng.uniform(-180, 180)), float(rng.uniform(0.2, 5.0)))",
    "deformation": "lambda rng: {'ctrl': rng.random((32, 3)) * 10.0, "
                   "'w': rng.standard_normal((32, 3)) * 0.01, "
                   "'a': rng.standard_normal((4, 3)), 'lam': 0.0}",
    "flow_dense": "lambda rng: np.stack([rng.standard_normal((12, 12, 12)) for _ in range(3)])",
    "flow_scattered": "lambda rng: rng.standard_normal((160, 3)) * 0.1",
}

#: 引数の既定値がプールの固定サイズと噛み合わない op(chain_fuzz の
#: ``OP_PARAM_HINTS`` へ入れるべきもの)。既定のままだと毎回 ValueError になり
#: **一度も実行されないまま「発見ゼロ」に見える**。
#:
#: ``keypoints_to_image2d`` の既定 shape=(64,64) は、``keypoints`` の既存の種
#: (``rng.random((160, 2)) * 32.0``)なら収まるが、``project_points`` の産物は
#: カメラ内部行列しだいで平気で 1000 px を超える。よって shape を種に合わせて
#: 上書きできるようにしておく。
OP_PARAM_HINT_PROPOSALS = {
    ("keypoints_to_image2d", "shape"): "lambda rng: (256, 256)",
    ("gaussians_to_voxel", "shape"): "lambda rng: (16, 16, 16)",
    ("normals_to_egi", "n_az"): "lambda rng: 36",
    ("normals_to_egi", "n_el"): "lambda rng: 18",
}

#: 宣言 out 型と素の返りの橋渡し。**意図的に空** —— 42 op すべてが宣言型
#: そのものを素で返す設計にしてある。空にしておくと :func:`call` は :func:`get`
#: と同じ値を返し、連鎖ファザーの TYPEMISS 検査が**素の返りをそのまま**宣言と
#: 突き合わせる = 検証が最も厳しい。
#:
#: 変換ばかりのモジュールで adapter を置くのは特に危険で、「宣言と実装が
#: ずれていても adapter が吸収する」状態を作ると、**変換の嘘を検出するために
#: 作ったモジュールが変換の嘘を隠す**ことになる。
RESULT_ADAPTERS = {}

#: 文書化済みの非有限を返す op。**空** —— 42 op のどれも非有限を返さない
#: (:func:`reprconv._arr` が入口で非有限を拒否し、どの計算も有限入力から
#: 有限出力しか作らない)。空にしておくと本物の非有限が必ず NONFINITE になる。
NONFINITE_BY_CONTRACT = frozenset()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSREPRCONV.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


def get(name):
    """op 名 → 実体(callable、素の返り型)。宣言型が欲しければ :func:`call`。"""
    return OPSREPRCONV[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSREPRCONV[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSREPRCONV[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSREPRCONV.items() if m["func"] is None]


def roundtrips():
    """往復の宣言表(:data:`ROUNDTRIPS`)を返す。"""
    return ROUNDTRIPS


def conversion_edges():
    """単入力の変換 ``(in, out)`` 一覧。台帳が新設した辺を数えるのに使う。"""
    return sorted({(m["in"][0], m["out"]) for m in OPSREPRCONV.values()
                   if len(m["in"]) == 1 and m["in"][0] != m["out"]})


if __name__ == "__main__":
    print(f"opsreprconv: {len(OPSREPRCONV)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
    edges = conversion_edges()
    print(f"新設した単入力の変換辺: {len(edges)}")
    srcs = sorted({a for a, _ in edges})
    print("出口ができた型:", ", ".join(srcs))
    kinds = {}
    for r in ROUNDTRIPS:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    print("往復の宣言:", ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())))
