# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""橋渡し op(``tb_*``)が**実際に仕事をしている**ことの検査。

``backends_typed`` は台帳 op を進化の ``ops.REGISTRY`` へ橋渡しする。ランナーは
fail-soft で、例外や sort 不一致のときは ``_fallback`` が「中身は無いが sort として
妥当な値」(``zeros((2,2,2))`` 等)を返す。これは下流を守る正しい設計だが、
**op が構造的に一度も成功しない場合、その op は候補枠を占めたまま定数を返し続ける**。
しかも例外もログも出ないので、外からはまったく気づけない。

2026-09-02 の実測でこの状態の op が **7 件**見つかった。原因は 2 系統:

* ``box_sdf`` / ``sphere_sdf`` —— 座標を要素ごとに処理する op に点群 (N,3) を
  渡すと (N,) が返り、宣言 ``volume``(3 次元)の検査に落ちる。
* ``region_growing`` / ``euclidean_cluster`` / ``plane_segmentation`` ——
  **点ごとの (N,) ラベル**を返すのに、型名 ``labels`` は 3-D のラベル体積も
  指しており ``TYPE_TO_SORT['labels'] = 'volume'`` に写る。

いずれも ``tools/chain_fuzz`` の ``TYPE_CHECKS['labels']`` が 1/2/3 次元すべてを
許す**緩い**述語なのでファザーからは見えず、厳しい側(進化の sort 契約)だけが
弾いていた。「発見ゼロ」でなく「**成功ゼロ**」だったという、同じ形の見落としである。
"""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import ops  # noqa: E402

cf = pytest.importorskip("chain_fuzz", reason="tools/chain_fuzz.py が読めない")
import backends_typed as bt  # noqa: E402

from conftest import requires_backend


#: **どんな入力でも定数しか返せない**ことが分かっていて、まだ直していない op。
#: 黙って許すのではなく、op 名と「なぜ直せないか」を書いて数を固定する。
KNOWN_DEAD_BRIDGES = {
    "tb_indices_to_labels":
        "reprconv の 'labels' は **1 次元**(indices_to_labels((5,)) -> (3,))なのに、"
        "TYPE_TO_SORT は 'labels' を 3-D の volume へ写す。実測 0/60。"
        "点群セグメンテーション 3 op と違って**点が手元に無い**ので体積へ焼く材料が"
        "無く、1-D を 3-D に仕立てるのは捏造になる。正しい直し方は台帳の型語彙を"
        "『体積のラベル』と『列のラベル』に分けることだが、新しい型に消費 op が"
        "無いと袋小路の型が増える(この repo が繰り返し踏んできた形)ので"
        "単独では入れない。",
}

# 2026-09-05: ``tb_specular_coefficient_map`` と ``tb_specular_diffuse_split`` を
# ここから外した。**op は壊れていなかった —— 壊れていたのは種の方**だった。
#
# 旧・台帳はこう書いていた: 「上流が dichromatic_render のような順方向モデルの
# 出力を供給したときだけ成功する」。診断は正しく、``chain_fuzz`` にはその
# ``dichromatic_render`` の種が**実在していた**(長い理由コメントつき)。ところが
# 同じ ``make_generators()`` の中に ``"rgbimage"`` がもう 1 つあり、辞書は後勝ちなので
# **一様乱数の方が勝って、意図のある種が黙って死んでいた**。
# 二色性の条件を満たす絵が一度も渡らないので、op は永久に拒否し続けていた。
#
# 見つけたのは ruff の ``F601``(dictionary key literal repeated)。この repo で
# 静的解析を CI に入れる根拠がこれ —— テストは 11,254 件が緑のまま、
# 「種が死んでいる」を 1 件も教えてくれなかった。
# 同じ重複があと 3 組あった(``radius`` / ``leader_line`` / ``("sphere_sdf","R")``)。

#: **入力をそのまま返し続ける** op。``_fallback`` は ``in_sort == out_sort`` のとき
#: ``np.asarray(v)`` を返す —— 情報を保つ正しい判断だが、**永久に失敗している op が
#: 恒等写像の顔で候補枠に居座る**ことも意味する。定数ゼロの指紋では捕まらないので
#: 別に数える(私が最初に書いた検査はこれを見落としていた)。
KNOWN_IDENTITY_BRIDGES = {}   # 2026-09-05 に空になった(上の注記を参照)

#: **設計上、入力をそのまま返すのが正しい** op。恒等 = 故障ではない例。
IDENTITY_BY_CONTRACT = {
    "tb_create_funct_1d_array":
        "docstring に『返る配列が関数そのもの』と明記された検証 + float64 化の op"
        "(HALCON create_funct_1d_array)。恒等であることが仕様。",
}


def _sample_for(sort, rng):
    """その in_sort が実際に運ぶ値を 1 つ作る(生成器は chain_fuzz が正本)。"""
    gens = cf.make_generators()
    by_sort = {
        "points": "points", "volume": "voxel", "image": "image2d",
        "signal": "signal", "matrix": "matrix", "cimage": "cimage",
        "lightfield": "lightfield", "counts": "counts", "rgbimage": "rgbimage",
        "video": "video", "qimage": "qimage", "beatcube": "beatcube",
        "keypoints": "keypoints",
    }
    key = by_sort.get(sort)
    return None if key is None else gens[key](rng)


def _is_constant_fallback(outs):
    """``_fallback`` の指紋: 常に同じ**小さい**形で、かつ中身が全部ゼロ。"""
    shapes = {np.shape(r) for r in outs}
    tiny = shapes <= {(2, 2, 2), (2, 2), (1, 3), (2,)}
    allzero = all(not np.any(np.asarray(r)) for r in outs)
    return tiny and allzero


def _live_report(trials=8, seed=0):
    rng = np.random.default_rng(seed)
    dead, live, skipped = [], [], []
    for op in ops.REGISTRY:
        if not op.name.startswith("tb_"):
            continue
        probe = _sample_for(op.in_sort, rng)
        if probe is None:
            skipped.append(op.name)
            continue
        outs = []
        for _ in range(trials):
            v = _sample_for(op.in_sort, rng)
            try:
                outs.append(op.fn(v, float(rng.random()), float(rng.random())))
            except Exception:                            # noqa: BLE001
                pass
        if not outs or _is_constant_fallback(outs):
            dead.append(op.name)
        else:
            live.append(op.name)
    return live, dead, skipped


def test_no_new_bridge_op_is_a_constant_fallback():
    """``tb_*`` が定数しか返さない状態を新しく増やさない。

    fail-soft は下流を守るためのもので、**op が永久に失敗していることを隠す**
    ためのものではない。ここで数を固定しておかないと、台帳に型を足すたびに
    静かに増えていく。
    """
    requires_backend('torch')
    live, dead, skipped = _live_report()
    assert live, "橋渡し op が 1 つも生きていない(検査の前提が壊れている)"
    new = sorted(set(dead) - set(KNOWN_DEAD_BRIDGES))
    assert not new, (
        "定数しか返さない橋渡し op(新規): %s\n"
        "宣言した out_sort に合う値を返せていない = 候補枠を占めたまま何も"
        "計算していない。" % new)


def _identity_report(trials=3, seed=11):
    """``in_sort == out_sort`` の tb_ op のうち、毎回**入力と bit 一致**を返すもの。"""
    rng = np.random.default_rng(seed)
    out = []
    for op in ops.REGISTRY:
        if not op.name.startswith("tb_") or op.in_sort != op.out_sort:
            continue
        if _sample_for(op.in_sort, rng) is None:
            continue
        same = 0
        for a, b in ((0.2, 0.3), (0.5, 0.5), (0.8, 0.9))[:trials]:
            v = _sample_for(op.in_sort, rng)
            try:
                r = op.fn(v, a, b)
            except Exception:                            # noqa: BLE001
                continue
            va, ra = np.asarray(v), np.asarray(r)
            if (va.shape == ra.shape and va.dtype == ra.dtype
                    and np.array_equal(va, ra)):
                same += 1
        if same == trials:
            out.append(op.name)
    return out


def test_no_new_bridge_op_is_a_pass_through():
    """同 sort の op が「入力をそのまま返し続ける」状態を新しく増やさない。

    定数ゼロの検査ではこれは**捕まらない** —— ``_fallback`` は同 sort のとき
    入力を通すので、故障が恒等写像の顔をする。最初に書いた検査はここを
    見落としていて、レジストリ全体を実測して初めて 4 件見つかった。
    """
    ident = _identity_report()
    known = set(KNOWN_IDENTITY_BRIDGES) | set(IDENTITY_BY_CONTRACT)
    new = sorted(set(ident) - known)
    assert not new, (
        "入力をそのまま返し続ける橋渡し op(新規): %s\n"
        "仕様としての恒等なら IDENTITY_BY_CONTRACT へ、故障なら "
        "KNOWN_IDENTITY_BRIDGES へ理由つきで記録すること。" % new)


def test_known_identity_bridges_are_still_identity():
    """直ったのに一覧へ残り続けない。"""
    ident = set(_identity_report())
    stale = sorted(set(KNOWN_IDENTITY_BRIDGES) - ident)
    assert not stale, ("KNOWN_IDENTITY_BRIDGES に残っているが実際は変換している: %s"
                       " — 直ったなら一覧から消すこと" % stale)


def test_known_dead_bridges_are_still_dead():
    """直ったのに一覧へ残り続けない(KNOWN_LEDGER_GAPS と同じ規律)。"""
    live, dead, _ = _live_report()
    stale = sorted(set(KNOWN_DEAD_BRIDGES) & set(live))
    assert not stale, ("KNOWN_DEAD_BRIDGES に残っているが実際は動いている: %s"
                       " — 直ったなら一覧から消すこと" % stale)


def test_the_two_sdf_primitives_build_a_real_field():
    """``box_sdf`` / ``sphere_sdf`` が点群から実際の距離場を作る(回帰)。

    2026-09-02 まで 40 通りの点群すべてで ``zeros((2,2,2))`` を返していた。
    """
    rng = np.random.default_rng(3)
    by = {o.name: o for o in ops.REGISTRY}
    for name in ("tb_box_sdf", "tb_sphere_sdf"):
        op = by[name]
        r = np.asarray(op.fn(_sample_for("points", rng), 0.5, 0.5))
        assert r.ndim == 3 and min(r.shape) >= 4, f"{name}: 形が {r.shape}"
        assert np.any(r != 0), f"{name}: 定数ゼロのまま"
        assert float(r.max()) > 0.0, f"{name}: 形状の外側が出ていない"


def test_keypoint_bridges_are_alive_after_the_sort_split():
    """像面上の (N,2) を扱う 4 op が実際に計算する(回帰)。

    2026-09-02 まで ``keypoints`` は ``points`` sort に畳まれており、
    ``_sort_ok`` が ``shape[1] == 3`` を要求するので **4 op すべてが
    fail-soft に落ちていた** —— 2 件は定数ゼロ、2 件は入力の素通し。
    とくに ``tb_project_points`` が死んでいたということは、進化は
    「3 次元を撮る」という基本的な写像を一度も使えていなかった。
    """
    rng = np.random.default_rng(7)
    by = {o.name: o for o in ops.REGISTRY}
    expect = {
        "tb_project_points": ("points", 2),
        "tb_points_zyx_to_keypoints_uv": ("points", 2),
        "tb_keypoints_uv_to_points": ("keypoints", 3),
        "tb_keypoints_to_image2d": ("keypoints", None),
    }
    for name, (in_sort, ncol) in expect.items():
        assert name in by, f"{name} が登録されていない"
        op = by[name]
        assert op.in_sort == in_sort, f"{name}: in_sort が {op.in_sort}"
        r = np.asarray(op.fn(_sample_for(in_sort, rng), 0.5, 0.5))
        if ncol is None:                                 # 画像を返す op
            assert r.ndim == 2 and min(r.shape) >= 8, f"{name}: 形が {r.shape}"
        else:
            assert r.ndim == 2 and r.shape[1] == ncol, f"{name}: 形が {r.shape}"
            assert r.shape[0] > 1, f"{name}: fallback の 1 行だけが返っている"
        assert np.any(r != 0), f"{name}: 定数ゼロ"


def test_keypoints_sort_is_not_a_dead_end():
    """``keypoints`` sort に産出 op と消費 op の両方があること。

    片方しか無い型を足すのは、この repo が繰り返し踏んできた失敗
    (入口はあるが消費 op が無い袋小路)。sort を足すときの必須条件として固定する。
    """
    producers = [o.name for o in ops.REGISTRY if o.out_sort == "keypoints"]
    consumers = [o.name for o in ops.REGISTRY if o.in_sort == "keypoints"]
    assert producers, "keypoints を産む op が無い(この sort へ到達できない)"
    assert consumers, "keypoints を食う op が無い(袋小路の型になっている)"


def test_shape_and_empty_tables_cover_the_same_sorts():
    """``_SHAPE_OK`` と ``_EMPTY_OF`` が同じ sort を覆っていること。

    片方だけに行を足すと、fail-soft が **sort の契約を破った値**を返す。
    分岐で書いていた頃はこれが目視でしか確かめられず、実際 keypoints が
    どちらにも無いまま 4 op が死んでいた。表にしたので機械で検査できる。
    """
    only_shape = sorted(set(bt._SHAPE_OK) - set(bt._EMPTY_OF))
    only_empty = sorted(set(bt._EMPTY_OF) - set(bt._SHAPE_OK))
    assert not only_shape, f"_EMPTY_OF に無い sort: {only_shape}"
    assert not only_empty, f"_SHAPE_OK に無い sort: {only_empty}"
    # 表が返す「空の値」自体がその sort の形の契約を満たすこと
    for sort, make in bt._EMPTY_OF.items():
        assert bt._sort_ok(make(), sort), f"{sort} の空値が自分の契約を満たさない"


def test_point_segmentation_bridges_produce_a_label_volume():
    """点群セグメンテーション 3 op が**ラベル体積**を返す(回帰)。

    区分けが 2 つ以上出ること(= 実際に分割している)まで見る。全部同じ値なら
    「動いてはいるが何も分けていない」で、定数ゼロとほとんど変わらない。
    """
    rng = np.random.default_rng(5)
    by = {o.name: o for o in ops.REGISTRY}
    for name in ("tb_region_growing", "tb_plane_segmentation"):
        op = by[name]
        seen = set()
        for _ in range(6):
            r = np.asarray(op.fn(_sample_for("points", rng), 0.5, 0.5))
            assert r.ndim == 3, f"{name}: 体積でない {r.shape}"
            seen.add(int(np.unique(r).size))
        assert max(seen) >= 2, f"{name}: 区分けが 1 種類しか出ない {seen}"


def test_label_volume_helper_keeps_unassigned_distinct_from_empty():
    """未割当(-1)と空ボクセルを混ぜない。

    どちらも 0 にすると「分割されなかった点」と「点が無い場所」が同じ値になり、
    下流のラベル op が存在しない領域を数える。ラベルは 1 起点へ持ち上げる。
    """
    P = np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0], [0.5, 0.5, 0.5]])
    vol = bt._point_labels_to_volume(P, np.array([-1, 0, 1]), res=4)
    assert vol.shape == (4, 4, 4)
    assert float(vol.max()) == 2.0, "ラベル 1 が 2 へ持ち上がっていない"
    assert float(vol[0, 0, 0]) == 0.0, "未割当が空ボクセルと同じ 0 になっていない"
    assert int((vol > 0).sum()) == 2, "空ボクセルにラベルが漏れている"


#: ``TYPE_TO_SORT`` の写像のうち、**その型の代表値が写り先 sort の形の契約を
#: 満たさない**もの。症状(死んだ橋渡し op)ではなく**原因**を直接固定する。
KNOWN_BROKEN_TYPE_TO_SORT = {
    ("keypoints", "points"):
        "keypoints は像面上の **(N,2)** だが points sort は ``ndim==2 and "
        "shape[1]==3`` を要求する(``_sort_ok``)。代表値の時点で必ず False。"
        "これが tb_project_points / tb_points_zyx_to_keypoints_uv / "
        "tb_keypoints_uv_to_points / tb_keypoints_to_image2d が死んでいる**唯一の"
        "原因**で、2026-09-02 に全 21 型を代表値で走査して**破れているのはここだけ**"
        "だと確かめた。正しい直し方は keypoints 専用 sort を足すことだが、"
        "その 4 op が points の候補リストから抜けるので ``ops.decode`` が動く"
        "(docs/WAVE0_STABLE_SLOTS.md の north-star)。pin の取り直しを伴う判断なので"
        "単独では入れない。",
    ("labels", "volume"):
        "型名 'labels' が **1-D(点ごと)/ 2-D(ラベル画像)/ 3-D(ラベル体積)**の"
        "3 通りを指しており、volume sort は 3-D しか通さない。実測 12 回中 2 回失敗"
        "(種 ``_labels`` が 2-D を引いたとき)。この写像の曖昧さが、点群"
        "セグメンテーション 3 op が定数ゼロを返し続けていた原因だった —— そちらは"
        "``OUTPUT_ADAPTERS_WITH_INPUT`` で点と一緒に体積へ焼いて解消したが、"
        "**2-D のラベル画像を返す op を橋渡しすると同じことが起きる**。根治は"
        "型語彙を分けること(体積 / 画像 / 列)だが、新しい型に消費 op が無いと"
        "袋小路の型が増える。この検査は『次に誰かが 2-D ラベルを橋渡ししたら"
        "気づける』ための番人として置く。",
}


def test_every_type_to_sort_mapping_holds_for_its_own_seed():
    """型 → sort の写像が、**その型の代表値**で成り立つこと。

    橋渡し op が死ぬのは、たいてい op の問題ではなく写像の問題である。
    症状(定数を返す / 恒等になる)を 1 件ずつ潰すより、写像を直接検査した方が
    原因に近い。種は複数回引く —— ``labels`` のように 2-D と 3-D を混ぜて返す
    生成器があり、1 回だけだと**たまたま通って**見逃す。
    """
    gens = cf.make_generators()
    rng = np.random.default_rng(0)
    broken = {}
    for t, sort in sorted(bt.TYPE_TO_SORT.items()):
        g = gens.get(t)
        if g is None:
            continue                                     # 種の無い型は判定できない
        fails = 0
        for _ in range(12):
            if not bt._sort_ok(g(rng), sort):
                fails += 1
        if fails:
            broken[(t, sort)] = f"12 回中 {fails} 回、代表値が sort の契約を満たさない"
    new = {k: v for k, v in broken.items() if k not in KNOWN_BROKEN_TYPE_TO_SORT}
    assert not new, (
        "型 -> sort の写像が代表値で破れている(新規): %s\n"
        "この写像で橋渡しされた op は、実行しても sort の検査に落ちて "
        "_fallback に化ける(例外もログも出ない)。" % new)


def test_known_broken_mappings_are_still_broken():
    """直ったのに一覧へ残り続けない。"""
    gens = cf.make_generators()
    rng = np.random.default_rng(1)
    stale = []
    for (t, sort), _why in KNOWN_BROKEN_TYPE_TO_SORT.items():
        g = gens.get(t)
        if g is None:
            continue
        if all(bt._sort_ok(g(rng), sort) for _ in range(12)):
            stale.append((t, sort))
    assert not stale, ("KNOWN_BROKEN_TYPE_TO_SORT に残っているが実際は成り立つ: %s"
                       " — 直ったなら一覧から消すこと" % stale)


def test_label_volume_helper_rejects_mismatched_lengths():
    """fail-closed: 点数とラベル数が違うものは黙って切り詰めない。"""
    P = np.zeros((5, 3))
    with pytest.raises(ValueError):
        bt._point_labels_to_volume(P, np.zeros(4))
    with pytest.raises(ValueError):
        bt._point_labels_to_volume(np.zeros((5, 2)), np.zeros(5))


# --------------------------------------------------------------------------- #
# 型が変わる op の素通し / 退化した返り / rgbimage のチャンネル数(2026-09-02)  #
# --------------------------------------------------------------------------- #
# 上の恒等検査(``_identity_report``)は **in_sort == out_sort** の op しか見ない。
# ところが ``_fallback`` は表(``_EMPTY_OF``)に無い out_sort に対して
# ``np.asarray(v)`` = 入力そのものを返すので、**型が変わる op** が失敗すると
# 入力が別の sort の顔をして下流へ流れる。実測 2026-09-02: ``tb_quaternion_to_rgb``
# (qimage → rgbimage)は乱数の (H,W,4) を渡すと quatimage 側の番人(非純四元数の
# 拒否)が必ず働き、そのたびに **4 チャンネルの入力がそのまま rgbimage として**
# 返っていた。恒等検査は sort が違うので見ず、定数ゼロの検査は中身が乱数なので
# 見ず、形の検査(``_SHAPE_OK``)には rgbimage の行が無くて 4 チャンネルが通った。
# 3 つの検査の隙間にちょうど落ちる形だったので、その 3 つを op ごとに置く。
#
# 検査は **op 1 件 = テスト 1 件**(parametrize)にし、直せない/直さない op は
# 理由つきの xfail(strict)にする。直った瞬間に XPASS で赤くなるので、一覧が
# 古びたまま残らない(KNOWN_* 辞書と同じ規律を pytest の機構で行う)。

#: 型が変わるのに**入力をそのまま返す**ことが分かっていて、まだ直していない op。
#: 既定語彙では 0 件(tb_quaternion_to_rgb は表に行を足して解消)。
#: ``IMGEVOLVE_WIDE_VOCAB=1`` では ``tb_lf_from_mla``(image → lightfield)が
#: 6/6 で素通し(lightfield / histcube に ``_EMPTY_OF`` の行が無い)— 既定語彙の
#: 外なのでここでは数えない。表に行を足す判断は sort の所有者に委ねる。
KNOWN_CROSS_SORT_PASS_THROUGH = {}

#: **設計上**入力をそのまま返す型変換 op(恒等 = 故障ではない)。空。
CROSS_SORT_IDENTITY_BY_CONTRACT = {}

#: 構造のある入力に対して**毎回定数**を返すことが分かっていて、まだ直していない
#: op。``KNOWN_DEAD_BRIDGES``(fallback の指紋 = 小さい形の全ゼロ)は自動で含める。
#: ここに書くのは、fallback ではなく **op 自身が走った上で**定数になるもの。
KNOWN_DEGENERATE_BRIDGES = {
    "tb_euclidean_cluster":
        "op は走っている(16^3 のラベル体積が返る)が、中身が**全ゼロ** —— 種の点群"
        "(160 点、一辺 ~10 の箱、点間隔 ~0.4)に対して束縛 ``tol=0.5``(PARAM_HINTS)"
        "と ``min_size`` の相対スケール(既定 10 の 1/4〜2 倍 = 3〜20)では 1 点も"
        "クラスタに入らず、全点が未割当(-1)→ 体積は 0 のまま。実測 2026-09-02: "
        "tol=0.5/min_size=3 で 3 点、tol=1.0/min_size=3 で 28 点しか付かず、"
        "min_size>=10 では常に 0 点。既存の定数検査は fallback の**小さい形**しか"
        "見ないので (16,16,16) の全ゼロを見逃していた。直すなら tol の束縛か"
        "min_size の範囲(点群の所有者の判断)。",
}

#: **設計上**、構造のある入力から定数を返してよい op(縮約 reducer)。
#: out_sort=feature(スカラー)は size==1 で自動的に対象外なので、ここに書くのは
#: 配列を返すのに定数が正解の op だけ。空。
REDUCERS_BY_CONTRACT = {}

#: torch が要る橋渡し op。**torch 不在の写しであって、op の欠陥ではない**。
#:
#: torch が無いと `torch_lazy` が ImportError を投げ、fail-soft が全ゼロを返す。
#: 「毎回定数」判定はそれを掴むが、それは環境の話なので、torch 不在なら skip する。
#: 逆に torch が**在る**環境では必ず実行される(`requires_backend` は
#: `FULLSEYE_REQUIRE_OPTIONAL=1` の CI で skip を失敗に変える)。
#:
#: 2026-09-05 実測: Linux(torch 不在)でこの検査に引っかかったのはこの 1 本だけ。
TORCH_BACKED_BRIDGES = {"tb_points_to_voxel"}

_GENS = None


def _gens():
    global _GENS
    if _GENS is None:
        _GENS = cf.make_generators()
    return _GENS


_SORT_TO_GEN = {
    "points": "points", "volume": "voxel", "image": "image2d",
    "signal": "signal", "matrix": "matrix", "cimage": "cimage",
    "lightfield": "lightfield", "counts": "counts", "rgbimage": "rgbimage",
    "video": "video", "qimage": "qimage", "beatcube": "beatcube",
    "keypoints": "keypoints",
}

_RUN_CACHE = {}


def _runs(op, trials=6, seed=23):
    """op を種で *trials* 回走らせ ``[(入力, 返り), ...]`` を返す(例外は除く)。

    3 つの検査が同じ実行結果を見るので op ごとに 1 度だけ走らせて共有する。
    """
    if op.name in _RUN_CACHE:
        return _RUN_CACHE[op.name]
    rng = np.random.default_rng(seed)
    gen = _gens()[_SORT_TO_GEN[op.in_sort]]
    outs = []
    for _ in range(trials):
        v = gen(rng)
        try:
            r = op.fn(v, float(rng.random()), float(rng.random()))
        except Exception:                                # noqa: BLE001
            continue
        outs.append((np.asarray(v), np.asarray(r)))
    _RUN_CACHE[op.name] = outs
    return outs


def _bridge_ops():
    return [o for o in ops.REGISTRY
            if o.name.startswith("tb_") and o.in_sort in _SORT_TO_GEN]


def _params(candidates, known, by_contract=()):
    """op → ``pytest.param``。既知の故障は理由つき strict xfail、仕様上の例外は skip。"""
    out = []
    for o in candidates:
        marks = ()
        if o.name in known:
            marks = pytest.mark.xfail(reason=known[o.name], strict=True)
        elif o.name in by_contract:
            marks = pytest.mark.skip(reason=by_contract[o.name])
        out.append(pytest.param(o, id=o.name, marks=marks))
    return out


def _is_constant(a):
    a = np.asarray(a)
    return a.size > 1 and np.unique(a).size == 1


@pytest.mark.parametrize(
    "op", _params([o for o in _bridge_ops() if o.in_sort != o.out_sort],
                  KNOWN_CROSS_SORT_PASS_THROUGH, CROSS_SORT_IDENTITY_BY_CONTRACT))
def test_cross_sort_bridge_never_returns_its_input(op):
    """型が変わる op が、1 回でも**入力と bit 一致**を返してはならない。

    同 sort なら「情報を保つ」恒等もありうるが、sort が違うのに同じ配列が返るのは
    定義上 **型の嘘**(in_sort の値に out_sort の札を付けて流している)。
    ``_fallback`` が表に無い out_sort で ``np.asarray(v)`` を返すのがその経路で、
    tb_quaternion_to_rgb はこれで 3/6 回、4 チャンネルを rgbimage として返していた。
    """
    runs = _runs(op)
    assert runs, f"{op.name}: 6 回とも例外(fail-soft が効いていない)"
    leaked = [i for i, (v, r) in enumerate(runs)
              if v.shape == r.shape and v.dtype == r.dtype and np.array_equal(v, r)]
    assert not leaked, (
        f"{op.name} ({op.in_sort} -> {op.out_sort}): 試行 {leaked} で入力がそのまま"
        f"返った = in_sort の値に out_sort の札を付けて流している。仕様上の恒等なら"
        f" CROSS_SORT_IDENTITY_BY_CONTRACT、故障なら KNOWN_CROSS_SORT_PASS_THROUGH へ"
        f"理由つきで記録すること。")


@pytest.mark.parametrize(
    "op", _params(_bridge_ops(),
                  dict(KNOWN_DEAD_BRIDGES, **KNOWN_DEGENERATE_BRIDGES),
                  REDUCERS_BY_CONTRACT))
def test_bridge_output_is_not_constant_for_structured_input(op):
    """構造のある(定数でない)入力に対して**毎回**定数の配列を返してはならない。

    ``_is_constant_fallback`` は fallback の**小さい形**だけを指紋にするので、
    op が走った上で (16,16,16) の全ゼロを返す ``tb_euclidean_cluster`` のような
    ものは通っていた。形を問わず「中身に 1 種類の値しか無い」を見る。
    スカラー(feature)は size==1 なので対象外。1 回でも構造のある返りがあれば
    合格(条件が厳しい op と永久に退化している op は別)。
    """
    if op.name in TORCH_BACKED_BRIDGES:
        requires_backend("torch")
    runs = _runs(op)
    assert runs, f"{op.name}: 6 回とも例外(fail-soft が効いていない)"
    judged = [(v, r) for v, r in runs if not _is_constant(v) and np.asarray(r).size > 1]
    if not judged:
        pytest.skip(f"{op.name}: 返りがスカラーか、種が定数だった")
    degenerate = all(_is_constant(r) for _v, r in judged)
    assert not degenerate, (
        f"{op.name} ({op.in_sort} -> {op.out_sort}): {len(judged)} 回すべて定数"
        f"(形 {sorted({r.shape for _v, r in judged})}、値 "
        f"{sorted({float(np.asarray(r).ravel()[0].real) for _v, r in judged})})。"
        f"縮約が仕様なら REDUCERS_BY_CONTRACT、故障なら KNOWN_DEGENERATE_BRIDGES へ。")


@pytest.mark.parametrize(
    "op", _params([o for o in _bridge_ops() if o.out_sort == "rgbimage"], {}))
def test_rgbimage_bridge_returns_exactly_three_channels(op):
    """rgbimage を宣言する op の返りは**必ず (H,W,3)**。fallback も含めて。

    ``_SHAPE_OK`` に rgbimage の行が無かった間、(H,W,4) の四元数画像がそのまま
    rgbimage として通っていた。表に行を足したので、ここは「行がある」ことと
    「その行が効いている」ことの両方を op の実行で確かめる。
    """
    assert "rgbimage" in bt._SHAPE_OK and "rgbimage" in bt._EMPTY_OF
    runs = _runs(op)
    assert runs, f"{op.name}: 6 回とも例外"
    bad = [r.shape for _v, r in runs if not (r.ndim == 3 and r.shape[2] == 3)]
    assert not bad, f"{op.name}: rgbimage 宣言なのに形 {bad} が返った"


def test_every_cross_sort_out_sort_has_an_empty_value():
    """型が変わる op の out_sort には、必ず ``_EMPTY_OF`` の行があること(原因側の固定)。

    行が無い sort へ写す op は、失敗すると ``_fallback`` が入力を素通しする。
    症状(素通し)を op ごとに捕まえる上の検査と対で、こちらは**表の欠け**を直接見る。
    既定語彙で 0 件になっていることを固定する(wide 語彙の lightfield / histcube は
    所有者判断で残っている — モジュール上部の KNOWN_CROSS_SORT_PASS_THROUGH 参照)。
    """
    missing = sorted({o.out_sort for o in ops.REGISTRY
                      if o.name.startswith("tb_") and o.in_sort != o.out_sort
                      and o.out_sort != "feature" and o.out_sort not in bt._EMPTY_OF})
    assert not missing, (
        f"_EMPTY_OF に行が無い out_sort: {missing} — この sort へ写す tb_ op は"
        f"失敗時に入力を素通しする(型の嘘)。")


def test_quaternion_to_rgb_bridge_fails_soft_to_an_rgbimage_not_its_input():
    """回帰: 非純四元数(番人が拒否する入力)でも 4 チャンネルを返さない。

    2026-09-02 まで乱数の (16,16,4) を渡すと (16,16,4) が bit 一致で返っていた。
    """
    by = {o.name: o for o in ops.REGISTRY}
    op = by["tb_quaternion_to_rgb"]
    q = np.random.default_rng(0).random((16, 16, 4))
    r = np.asarray(op.fn(q, 0.5, 0.5))
    assert r.ndim == 3 and r.shape[2] == 3, f"rgbimage でない形 {r.shape}"
    assert not (r.shape == q.shape and np.array_equal(r, q)), "入力の素通し"


# --- bridge outputs must be finite and deterministic -------------------------- #
# The evolution scores tb_* outputs; a NaN/Inf poisons the holdout and a
# nondeterministic op makes scores irreproducible. These were never enforced on
# the bridges (conftest has no input bank for points/signal/matrix/video/qimage/…,
# so the universal contracts in test_op_contracts skip all 139 bridge ops — they
# "passed" by running zero times). Measure them here over the fuzzer's own
# generators plus degenerate inputs and knob extremes.

#: tb_* ops whose HONEST answer includes a non-finite value — not a bug, documented
#: in the op. Anything not listed that returns NaN/Inf is a real defect.
KNOWN_NONFINITE_BY_CONTRACT = {
    "tb_mat_cond":
        "spectral condition number s_max/s_min; an exactly singular matrix "
        "(e.g. the all-zeros probe) has s_min=0, so inf is the correct answer "
        "(mathops.mat_cond returns inf, does not raise — 'how conditioned is it?' "
        "has that honest answer).",
    "tb_geodesic_distances":
        "shortest-path distance on a kNN graph; when the knob maps k down to ~2 "
        "the graph disconnects and unreachable points are inf by definition "
        "(geodesic3d docstring: 不達は inf). A finite fill would be a fabricated "
        "distance.",
}


def _finite_battery(gk):
    """Generator samples (3 seeds) + degenerate zeros/ones of the same shape."""
    g = _gens()[gk]
    out = []
    for seed in (1, 7, 29):
        try:
            out.append(g(np.random.default_rng(seed)))
        except Exception:                                # noqa: BLE001
            continue
    if out:
        a = np.asarray(out[0])
        if a.dtype != object:
            out.append(np.zeros_like(a))
            try:
                out.append(np.ones_like(a))
            except Exception:                            # noqa: BLE001
                pass
    return out


_FINITE_KNOBS = [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0), (0.15, 0.85), (0.0, 1.0), (1.0, 0.0)]


def _bridge_nonfinite_report():
    """tb_* ops that return a NaN/Inf anywhere in the battery."""
    bad = set()
    for op in _bridge_ops():
        gk = _SORT_TO_GEN[op.in_sort]
        for v in _finite_battery(gk):
            for a, b in _FINITE_KNOBS:
                try:
                    r = np.asarray(op.fn(np.array(v, copy=True), a, b))
                except Exception:                        # noqa: BLE001 - fail-soft path, covered elsewhere
                    continue
                if r.dtype != object and np.issubdtype(r.dtype, np.number) \
                        and r.size and not np.all(np.isfinite(r)):
                    bad.add(op.name)
    return bad


def test_no_bridge_op_returns_nonfinite_except_by_contract():
    """A bridge op that returns NaN/Inf on any battery input is a defect, unless its
    honest answer is non-finite (then list it in KNOWN_NONFINITE_BY_CONTRACT with the
    reason). Also fails if a listed op has stopped producing non-finite (stale).
    """
    bad = _bridge_nonfinite_report()
    known = set(KNOWN_NONFINITE_BY_CONTRACT)
    new = sorted(bad - known)
    stale = sorted(known - bad)
    assert not new, ("bridge ops returning NaN/Inf (fix, or document in "
                     "KNOWN_NONFINITE_BY_CONTRACT): %s" % new)
    assert not stale, ("KNOWN_NONFINITE_BY_CONTRACT entries that are now finite "
                       "(remove them): %s" % stale)


def test_bridge_ops_are_deterministic():
    """Same input + knobs twice -> identical output (the evolution's scoring is
    reproducible only if every op is)."""
    nondet = []
    for op in _bridge_ops():
        gk = _SORT_TO_GEN[op.in_sort]
        batt = _finite_battery(gk)[:2]                   # first gen sample + zeros is enough
        for v in batt:
            for a, b in ((0.5, 0.5), (0.15, 0.85)):
                try:
                    r1 = np.asarray(op.fn(np.array(v, copy=True), a, b))
                    r2 = np.asarray(op.fn(np.array(v, copy=True), a, b))
                except Exception:                        # noqa: BLE001
                    continue
                if r1.shape != r2.shape or not np.array_equal(r1, r2, equal_nan=True):
                    nondet.append(op.name)
                    break
            else:
                continue
            break
    assert not nondet, "nondeterministic bridge ops: %s" % sorted(set(nondet))


def test_every_ledger_entry_names_a_live_bridge_op():
    """★台帳に**居ない op 名**が残っていないこと(4 台帳まとめて)。

    2026-09-05 の門の変異テストで判明: `_params()` 経由の台帳
    (`KNOWN_DEAD_BRIDGES` / `KNOWN_BROKEN_TYPE_TO_SORT` /
    `KNOWN_CROSS_SORT_PASS_THROUGH` / `KNOWN_DEGENERATE_BRIDGES`)は
    **実在する op を先に列挙してから台帳と突き合わせる**ので、台帳側の
    タイポ・改名後の残骸・出鱈目な名前は**どの parametrize ノードにも結び付かず**、
    検証経路そのものが存在しなかった。「本物を消す」方向は strict xfail が拾うが、
    「偽物が残る」方向は誰も見ていなかった。

    ここで両方向が揃う。
    """
    live = {o.name for o in _bridge_ops()}
    ledgers = {
        "KNOWN_DEAD_BRIDGES": KNOWN_DEAD_BRIDGES,
        # KNOWN_BROKEN_TYPE_TO_SORT は (type, sort) の組が鍵で op 名ではない ——
        # 陳腐化は test_broken_type_to_sort_ledger_is_current が別に見ている
        "KNOWN_CROSS_SORT_PASS_THROUGH": KNOWN_CROSS_SORT_PASS_THROUGH,
        "KNOWN_DEGENERATE_BRIDGES": KNOWN_DEGENERATE_BRIDGES,
        "KNOWN_NONFINITE_BY_CONTRACT": KNOWN_NONFINITE_BY_CONTRACT,
        "KNOWN_IDENTITY_BRIDGES": KNOWN_IDENTITY_BRIDGES,
    }
    stale = {k: sorted(set(v) - live) for k, v in ledgers.items() if set(v) - live}
    assert not stale, "台帳に居ない op 名が残っている(改名・削除・タイポ): %s" % stale
    assert len(live) > 100, "橋渡し op が少なすぎる(%d) —— 検査の前提が違う" % len(live)
