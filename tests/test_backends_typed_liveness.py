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
    "tb_specular_coefficient_map":
        "二色性反射の分離 op で、『照明に直交する成分の階数が 1』という物理条件を"
        "満たす絵にしか使えない。実測 0/60(乱数の rgbimage は必ず拒否される)。"
        "宣言の誤りではなく到達性の問題 —— 上流が dichromatic_render のような"
        "順方向モデルの出力を供給したときだけ成功する。op 側の番人は正しく働いている。"
        "対比: 同じく物理条件を要求する tb_monogenic_amplitude は **24/60 で成功**"
        "するので一覧に入れていない(『条件が厳しい』と『永久に失敗する』は別)。",
}

#: **入力をそのまま返し続ける** op。``_fallback`` は ``in_sort == out_sort`` のとき
#: ``np.asarray(v)`` を返す —— 情報を保つ正しい判断だが、**永久に失敗している op が
#: 恒等写像の顔で候補枠に居座る**ことも意味する。定数ゼロの指紋では捕まらないので
#: 別に数える(私が最初に書いた検査はこれを見落としていた)。
KNOWN_IDENTITY_BRIDGES = {
    "tb_specular_diffuse_split":
        "tb_specular_coefficient_map と同じ物理条件(照明直交成分の階数 1)を要求し、"
        "乱数の rgbimage では必ず拒否される。in_sort == out_sort なのでこちらは"
        "恒等として現れる。実測 3/3。",
}

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
