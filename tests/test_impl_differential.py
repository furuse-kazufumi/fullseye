# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""同じ処理の別実装どうしの門(differential testing、2026-11-03)。

golden(過去の自分の出力)と比べる門は「昨日と同じか」しか問わない。ここは**実装どうし**を
同じ入力・同じつまみで走らせ、次の 4 つを見る(表と測り方は ``tools/impl_differential.py``、
結果は ``docs/IMPL_DIFFERENTIAL.md``)。

1. **組の数が表と同じ**: 語幹が同じで接頭辞だけ違う組が増えた・減ったら赤。新しい組は測って、
   一致しなければ理由を書くまで通さない(「理由の無い食い違いが増えたら赤」)。
2. **一致した組は今も一致する**: 実装どうしの内部差が ``TOL_MATCH`` 未満(golden ではなく、その場で
   両方を走らせる)。つまみを揃えた点(``ALIGNED``)も同じ。
3. **一致しない組には理由がある**、一致した組には理由が無い(古い理由が残ると、次に食い違ったときに
   理由があるように見える)。一致しない組が今になって一致したら表が古い —— 測り直す。
4. **差がきっかり 0 の組は内訳が書いてある**(同じ下位関数を呼んでいるだけか、独立だが自明か)。
   「異常に良い一致」を独立な実装の一致と書かない。

optional 依存(cv2 / skimage / torch / kornia)が無い組は skip(``requires_backend``。CI の py3.11 は
全部入っているので skip は失敗になる)。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import impl_differential as D  # noqa: E402
import impl_differential_table as T  # noqa: E402
from conftest import requires_backend  # noqa: E402



@pytest.fixture(autouse=True)
def _cpu_device(monkeypatch):
    """突き合わせは CPU で測る。★モジュールの先頭で ``os.environ`` を書くと、収集の時点で
    プロセス全体の device が cpu に固定され、同じ shard の ``device="cuda"`` を試すテスト
    (test_fallback_policy の遮断器)が GPU 経路に入らず落ちた(2026-11-04、PR #241 の CI)。
    このファイルのテストの間だけ効くように monkeypatch で置く。"""
    monkeypatch.setenv("FULLSEYE_DEVICE", "cpu")


DATA = D.load_json()
PAIRS = {(p["a"], p["b"]): p for p in DATA["pairs"]}
INDEX = {o["name"]: o for o in D.load_index()}

#: OP_INDEX の ``requires`` → import 名。xkor_ / dl_ は torch に加えて kornia を要る。
_REQ = {"cv2": "cv2", "skimage": "skimage", "torch": "torch"}


def _need(*names):
    mods = set()
    for n in names:
        o = INDEX.get(n, {})
        for r in o.get("requires") or []:
            if r in _REQ:
                mods.add(_REQ[r])
        if n.startswith("xkor_"):
            mods.add("kornia")
    if mods:
        requires_backend(*sorted(mods))


# --------------------------------------------------------------------------- 1. 組の数
def test_groups_match_the_measured_table():
    """語幹の組が増えた・減ったら、測り直して表を更新するまで赤。"""
    groups = D.find_groups()
    tb, impl = D.split_groups(groups)
    assert impl == DATA["impl_groups"], (
        "実装どうしの組が表と違う(足された / 消えた組): %s。"
        "`py -3.11 tools/impl_differential.py --measure` で測り直し、一致しない組には "
        "tools/impl_differential_table.py に理由を書く" % sorted(set(impl) ^ set(DATA["impl_groups"])))
    assert sorted(tb) == sorted(DATA["bridge_groups"]), sorted(set(tb) ^ set(DATA["bridge_groups"]))
    assert DATA["counts"]["impl_pairs"] == sum(len(D.pairs_of(m)) for m in impl.values())


def test_count_floor():
    """数え方が黙って縮んでいないか(接頭辞の表を誤って削ると組が消える)。床は 2026-11-03 の実測。"""
    assert DATA["counts"]["impl_pairs"] >= 55
    assert DATA["counts"]["bridge_groups"] >= 150


# --------------------------------------------------------------------------- 3. 理由の表
def test_every_mismatch_has_a_reason_and_no_match_has_one():
    missing = [k for k, p in PAIRS.items() if p["class"] != "一致" and k not in T.REASONS]
    assert not missing, "理由の無い食い違い(中身を読んで tools/impl_differential_table.py の REASONS へ): %s" % missing
    stale = [k for k in T.REASONS if k not in PAIRS or PAIRS[k]["class"] == "一致"]
    assert not stale, "一致した / 存在しない組に理由が残っている(消す): %s" % stale
    bad_kind = [k for k, (kind, _t) in T.REASONS.items() if kind not in T.KINDS]
    assert not bad_kind, bad_kind


def test_every_group_has_a_merge_verdict():
    stems = {p["stem"] for p in DATA["pairs"]}
    assert stems == set(T.MERGE_VERDICT), sorted(stems ^ set(T.MERGE_VERDICT))
    assert all(v in T.VERDICTS for v, _ in T.MERGE_VERDICT.values())


def test_no_unexplained_failures_or_unverified():
    """測った環境で「片方が落ちる」「未検証」は 0(どちらかが出たら原因を書くか直す)。"""
    bad = [k for k, p in PAIRS.items() if p["class"] in ("片方が落ちる", "未検証")]
    assert not bad, bad
    br = [b["op"] for b in DATA["bridges"] if b["result"] not in ("一致", "標本外")]
    assert not br, br


# --------------------------------------------------------------------------- 4. 異常に良い一致
def test_exact_zero_pairs_are_explained():
    """差がきっかり 0 の組は、同じ下位関数か(SHARED_BACKEND)、独立だが自明か(TRIVIAL_MATCH)を書く。"""
    zero = [k for k, p in PAIRS.items() if p.get("exact_zero")]
    unexplained = [k for k in zero if k not in T.SHARED_BACKEND and k not in T.TRIVIAL_MATCH]
    assert not unexplained, "差 0 の内訳が無い(同じ関数を呼んでいるだけではないか確かめる): %s" % unexplained
    stale = [k for k in list(T.SHARED_BACKEND) + list(T.TRIVIAL_MATCH) if k not in zero]
    assert not stale, stale


def test_skeleton_numpy_twin_matches_skimage():
    """skeleton は skimage を呼ぶ(sk_skeleton と独立でない)。無い環境で落ちる先の numpy 双子が
    skimage と同じ答えであることを、ここで独立に確かめる。"""
    requires_backend("skimage")
    import numpy_twins
    import op_probe
    from skimage import morphology
    rng = np.random.default_rng(3)
    for v in (op_probe.structured_region(48), rng.random((48, 48)) > 0.5, rng.random((31, 17)) > 0.3):
        m = np.asarray(v) > 0.5
        assert np.array_equal(numpy_twins.skeletonize(m), morphology.skeletonize(m))


# --------------------------------------------------------------------------- 2. 生で突き合わせる
def _live_worst(x, y):
    """``measure_pair`` と同じ入力・つまみ・比べ方で、0〜1 の最悪値をその場で測る。"""
    ox = INDEX[x]
    worst = 0.0
    for v in D.inputs_for(ox["in_sort"]).values():
        for a, b in D.KNOBS:
            s, _ = D.compare_outputs(D.run_op(x, v, a, b), D.run_op(y, v, a, b), ox["out_sort"])
            worst = max(worst, s)
    return worst


MATCHED = sorted(k for k, p in PAIRS.items() if p["class"] == "一致")
DIFFERENT = sorted(k for k, p in PAIRS.items() if p["class"] in ("近い", "違う"))


@pytest.mark.parametrize("pair", MATCHED, ids=["%s~%s" % k for k in MATCHED])
def test_matched_pairs_still_match(pair):
    x, y = pair
    _need(x, y)
    w = _live_worst(x, y)
    assert w < D.TOL_MATCH, "%s と %s が食い違うようになった(内部差 %.3g ≥ %g)。どちらかが変わった —— " \
        "不具合なら直し、意図した変更なら測り直して理由を書く" % (x, y, w, D.TOL_MATCH)


@pytest.mark.parametrize("pair", DIFFERENT, ids=["%s~%s" % k for k in DIFFERENT])
def test_different_pairs_have_not_silently_converged(pair):
    """「違う / 近い」と書いた組が一致するようになったら、表(と理由)が古い。"""
    x, y = pair
    _need(x, y)
    w = _live_worst(x, y)
    assert w >= D.TOL_MATCH, "%s と %s が一致するようになった(%.3g)—— 測り直して理由を消す" % (x, y, w)


ALIGNED = [(x, y, kx, ky, e) for (x, y), pts in sorted(T.ALIGNED.items()) for kx, ky, e in pts]


@pytest.mark.parametrize("x,y,kx,ky,expect", ALIGNED,
                         ids=["%s~%s@%s" % (x, y, "%g,%g" % kx) for x, y, kx, _ky, _e in ALIGNED])
def test_aligned_knobs_reduce_the_difference_to_the_stated_cause(x, y, kx, ky, expect):
    """「差はつまみの写し方だけ」の検算。揃えれば差は期待の量(量子化の 1/255、定数倍、丸め)に収まる。"""
    _need(x, y)
    q = D.aligned_score(x, kx, y, ky, expect)
    assert q <= expect[1], "%s%s と %s%s: %s = %.3g > %g" % (x, kx, y, ky, expect[0], q, expect[1])


def test_aligned_points_are_for_pairs_that_differ():
    """揃えた点は「違う」組の原因の検算。一致した組に置いても何も確かめない。"""
    for key in T.ALIGNED:
        assert key in PAIRS and PAIRS[key]["class"] != "一致", key


# --------------------------------------------------------------------------- tb_ の橋渡し
BRIDGE_OK = sorted(b["op"][3:] for b in DATA["bridges"] if b["result"] == "一致")


def test_bridge_samples_still_map_knobs_as_documented():
    """``tb_X`` のつまみ k = 0 / 3/7 / 1 が、台帳の関数の既定の 1/4・1・2 倍(範囲表は lo + (hi−lo)k)に写る。"""
    bad = []
    for stem in BRIDGE_OK:
        r = D.check_tb_bridge(stem)
        if r["result"] not in ("一致", "未検証"):
            bad.append((stem, r))
    assert not bad, bad
    assert len(BRIDGE_OK) >= 120


# --------------------------------------------------------------------------- 直した不具合の回帰
@pytest.mark.parametrize("shape", [(48, 48), (4, 4), (3, 7)])
@pytest.mark.parametrize("a", [0.0, 0.25, 0.5, 1.0])
def test_xkor_gaussian_is_the_scipy_gaussian(shape, a):
    """2026-11-03 まで xkor_gaussian は 5x5 固定で σ を打ち切っていた。今は scipy の
    ``gaussian_filter(σ, mode="reflect", truncate=4)`` そのもの(float32 の丸めまで)。"""
    requires_backend("torch", "kornia")
    from scipy import ndimage
    v = np.random.default_rng(7).random(shape)
    got = D.run_op("xkor_gaussian", v, a, 0.5)
    want = ndimage.gaussian_filter(v, 0.3 + 2.7 * a, mode="reflect", truncate=4.0)
    np.testing.assert_allclose(got, want, rtol=0, atol=1e-6)


def test_xkor_unsharp_window_follows_sigma():
    """xkor_unsharp も同じ 5x5 の欠陥だった。強さ 1・σ = 0.5 + 2b の unsharp mask と一致する。"""
    requires_backend("torch", "kornia")
    from scipy import ndimage
    v = np.random.default_rng(8).random((40, 36))
    for b in (0.0, 0.5, 1.0):
        s = 0.5 + 2.0 * b
        want = np.clip(2 * v - ndimage.gaussian_filter(v, s, mode="reflect", truncate=4.0), 0, 1)
        np.testing.assert_allclose(D.run_op("xkor_unsharp", v, 0.3, b), want, rtol=0, atol=1e-6)


# --------------------------------------------------------------------------- 生成物
def test_markdown_is_generated_from_the_json():
    with open(D.MD_PATH, encoding="utf-8") as f:
        on_disk = f.read()
    assert on_disk == D.render_md(DATA), "docs/IMPL_DIFFERENTIAL.md が古い: py -3.11 tools/impl_differential.py"
