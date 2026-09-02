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
    "tb_keypoints_to_image2d":
        "台帳の in 型は 'keypoints'((N,2))だが TYPE_TO_SORT はこれを 'points' sort へ"
        "写す。points sort は普段 (N,3) の点群を運ぶので、上流が keypoints を産んだ"
        "ときだけ形が合う。**1 つの sort に 2 つの形が同居している**のが根で、"
        "分けるなら sort の追加が要る(= decode の候補リストが動く)。",
}


def _sample_for(sort, rng):
    """その in_sort が実際に運ぶ値を 1 つ作る(生成器は chain_fuzz が正本)。"""
    gens = cf.make_generators()
    by_sort = {
        "points": "points", "volume": "voxel", "image": "image2d",
        "signal": "signal", "matrix": "matrix", "cimage": "cimage",
        "lightfield": "lightfield", "counts": "counts", "rgbimage": "rgbimage",
        "video": "video", "qimage": "qimage", "beatcube": "beatcube",
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


def test_label_volume_helper_rejects_mismatched_lengths():
    """fail-closed: 点数とラベル数が違うものは黙って切り詰めない。"""
    P = np.zeros((5, 3))
    with pytest.raises(ValueError):
        bt._point_labels_to_volume(P, np.zeros(4))
    with pytest.raises(ValueError):
        bt._point_labels_to_volume(np.zeros((5, 2)), np.zeros(5))
