"""Public programmatic API (api.py / the `fullseye` facade) — the surface other
projects consume. Ground-truth checks that numpy-in/numpy-out works and that op
resolution matches the CLI."""
import numpy as np
import pytest

import api
import ops


def _img(n=48):
    y, x = np.mgrid[0:n, 0:n]
    return np.clip(0.5 + 0.3 * np.sin(x / 7.0) * np.cos(y / 9.0), 0, 1)


def test_apply_resolves_opname_and_halcon_alias_identically():
    f = _img()
    # gaussian is the op name; gauss_filter is its HALCON alias — both must work
    # and give the same result (same underlying RT entry).
    assert np.allclose(api.apply(f, "gaussian"), api.apply(f, "gauss_filter"))


def test_apply_returns_declared_sort():
    f = _img()
    seg = api.apply(f, "otsu")                      # image -> region
    assert set(np.unique(seg)).issubset({0.0, 1.0})
    n = api.apply(seg, "count_obj")                 # region -> feature
    assert isinstance(n, float)                     # scalar, not an array


def test_apply_output_is_finite_and_in_range_for_image_ops():
    f = _img()
    for name in ("sobel_amp", "gaussian", "clahe", "bilateral", "frei_dir"):
        out = api.apply(f, name)
        assert np.all(np.isfinite(out))
        assert out.min() >= -1e-9 and out.max() <= 1 + 1e-9, name


def test_run_pipeline_shared_and_per_stage():
    f = _img()
    shared = api.run_pipeline(f, ["gaussian", "sobel_amp", "otsu"], a=0.4, b=0.5)
    assert shared.shape == f.shape
    # per-stage knobs (the CLI cannot express this in one call)
    staged = api.run_pipeline(f, [("gaussian", 0.3, 0.5), ("sobel_amp", 0.5, 0.5),
                                  ("otsu", 0.4, 0.5)])
    assert set(np.unique(staged)).issubset({0.0, 1.0})


def test_coerce_binarizes_input_for_region_op():
    # A grayscale array handed to a region-input op is binarised at 0.5 (coerce=True).
    f = _img()
    region_in = [o for o in ops.REGISTRY if o.in_sort == "region"]
    assert region_in, "expected some region-input ops"
    op = next(o for o in region_in if o.out_sort in ("region", "feature"))
    out = api.apply(f, op.name)                     # should not raise on fractional input
    assert out is not None


def test_coerce_bool_region_input_becomes_float_mask():
    # Regression: a bool mask used to bypass coercion entirely (dtype kind "b" was
    # not in "fiu"), so ops received a bool array even though apply() promises a
    # float64 mask — and `-`/`sum` on bool raises or changes meaning.
    mask = np.zeros((24, 24), bool)
    mask[4:12, 5:15] = True
    op = next(o for o in ops.REGISTRY if o.name == "reg_erode")
    got = api._coerce_input(mask, op)
    assert isinstance(got, np.ndarray) and got.dtype == np.float64
    assert set(np.unique(got)).issubset({0.0, 1.0})
    assert np.array_equal(got > 0.5, mask)                 # re-typed, never re-valued
    # and the op result is unchanged by the coercion
    assert np.allclose(api.apply(mask, "reg_erode"),
                       api.apply(mask.astype(np.float64), "reg_erode"))


def test_coerce_two_level_grayscale_region_input_is_left_to_internal_bin():
    # Contract pin: an in-range two-level array ({0.3,0.7}) is NOT rewritten here —
    # every region op binarises at 0.5 itself, so the mask is identical, while the
    # label-reading region ops still see their gray levels.
    mask = np.zeros((24, 24), bool)
    mask[4:12, 5:15] = True
    two = np.where(mask, 0.7, 0.3)
    op = next(o for o in ops.REGISTRY if o.name == "reg_erode")
    assert api._coerce_input(two, op) is two               # passed through untouched
    assert np.allclose(api.apply(two, "reg_erode"),
                       api.apply(mask.astype(np.float64), "reg_erode"))
    labels = api.apply(two, "r3_label_to_region", a=0.0)   # levels survive coercion
    assert np.array_equal(labels > 0.5, ~mask)             # 0.3 is the lowest label
    # 3+ levels or out-of-range values are binarised, as before
    three = np.where(mask, 0.7, 0.3); three[0, 0] = 0.9
    assert set(np.unique(api._coerce_input(three, op))).issubset({0.0, 1.0})


def test_coerce_int_region_mask_becomes_float():
    # Regression: an int/uint {0,1} mask was left untouched (returned int64) even
    # though apply() promises float64 — the docstring lead ("not already a float64
    # {0,1} mask") did not match the code. It is now re-typed to float64, same values.
    mask = np.zeros((16, 16), np.uint8)
    mask[3:10, 4:12] = 1
    op = next(o for o in ops.REGISTRY if o.name == "reg_erode")
    got = api._coerce_input(mask, op)
    assert isinstance(got, np.ndarray) and got.dtype == np.float64
    assert set(np.unique(got)).issubset({0.0, 1.0})
    assert np.array_equal(got > 0.5, mask > 0)             # re-typed, never re-valued
    # an int label image (values > 1) is still binarised at 0.5, as before
    lbl = np.zeros((16, 16), np.int64); lbl[3:10, 4:12] = 5
    assert set(np.unique(api._coerce_input(lbl, op))).issubset({0.0, 1.0})


def test_unknown_op_raises_keyerror():
    with pytest.raises(KeyError):
        api.apply(_img(), "no_such_operator_xyz")


def test_find_op_and_discovery():
    assert api.find_op("gaussian") is not None
    assert api.find_op("gauss_filter") is not None      # halcon alias
    assert api.find_op("definitely_not_an_op") is None
    names = api.op_names()
    assert "gaussian" in names and len(names) == len(ops.REGISTRY)
    assert all(r["in_sort"] == "region" for r in api.list_ops(sort="region"))


def test_list_ops_general_tier_is_opt_in():
    import algo
    # default: image focus unchanged — no general-algorithm ops leak in
    default_names = {r["name"] for r in api.list_ops()}
    assert not (default_names & set(algo.algo_names()))
    # opt-in: the general tier appears, tagged backend="general" and category "algo:*"
    rows = api.list_ops(include_algo=True)
    algo_rows = [r for r in rows if r.get("backend") == "general"]
    assert {r["name"] for r in algo_rows} == set(algo.algo_names())
    assert all(r["category"].startswith("algo:") for r in algo_rows)
    assert all(r["halcon"] is None and r["provenance"] for r in algo_rows)
    # general rows sort AFTER the image/nary ops (tier "z_algo")
    assert all(r["tier"] == "z_algo" for r in algo_rows)
    assert rows[-len(algo_rows)][ "backend"] == "general"     # tail of the sorted list
    # api.algo_rows() alone matches
    assert {r["name"] for r in api.algo_rows()} == set(algo.algo_names())


def test_fullseye_facade_reexports_api():
    import fullseye
    f = _img()
    assert fullseye.__version__ == api.__version__
    assert np.allclose(fullseye.apply(f, "gaussian"), api.apply(f, "gaussian"))
    assert fullseye.op_names() == api.op_names()


def _assert_listing_matches_the_index(rows, index):
    """一覧(``list_ops``)が、索引が知っている**層**を取りこぼさないこと。

    ★主張は「**層に盲目でないこと**」であって「op の顔ぶれが索引と同じこと」では
    ない。registry の顔ぶれは**入っている optional 依存で変わり、しかも op 単位で
    変わる** —— `backends_r3` は 56 op のうち `xcv3_*` 8 本だけが opencv-contrib を
    要り、モジュールの申告依存は `skimage`(CI に在る)である。そこを完全一致の
    門にしたため 2026-09-25 に **CI で 26 op** ぶん赤になった
    ([[feedback_gate_computed_a_verdict_then_discarded_it]] の
    「手元にある optional 依存が CI に無い」型)。

    見るのは 3 つ、どれも環境で変わらない:

    1. 索引に無い op が一覧に在らない(在れば**索引が古い**)。
    2. **台帳層は完全一致**。台帳は numpy/scipy だけで組める一次モジュールなので、
       欠けたら環境のせいにできない —— この門が本来捕まえたい事故はここで落ちる。
    3. 索引が知っている層は、どれも一覧に現れる(層まるごとの欠落を止める)。
    """
    by_name = {o["name"]: o for o in index["ops"]}
    got = {r["name"] for r in rows}
    extra = sorted(got - set(by_name))
    assert not extra, (
        "索引に無い op が一覧に在る(索引が古い): %d 件 %s" % (len(extra), extra[:5]))

    want_ledger = {n for n, o in by_name.items() if o["tier"] == "ledger"}
    got_ledger = {r["name"] for r in rows if r["tier"] == "ledger"}
    assert got_ledger == want_ledger, (
        "台帳層が索引と食い違う(依存を持たない層なので環境差では説明がつかない): "
        "一覧に無い %s / 索引に無い %s"
        % (sorted(want_ledger - got_ledger)[:5], sorted(got_ledger - want_ledger)[:5]))

    #: 索引の ``color`` は別の op ではなく、レジストリ行に貼り直した札なので数えない。
    want_tiers = {o["tier"] for o in index["ops"]} - {"color"}
    got_tiers = {r["tier"] for r in rows}
    assert want_tiers <= got_tiers, (
        "一覧に現れない層が在る: %s —— 層がまるごと見えないのがこの門の見張るもの"
        % sorted(want_tiers - got_tiers))


def _assert_the_listing_holds_everything_this_process_has(rows):
    """一覧が、**この処理系が実際に持っている** op を 1 つも落としていないこと。

    索引と違ってこちらは同じプロセスの中の話なので、環境で変わらない。
    ``list_ops`` が絞り込みや並べ替えで静かに落とす事故を、ここで止める。
    """
    reg = {r["name"] for r in rows if r["tier"] == "registry"}
    assert reg == set(api.op_names()), (
        "一覧の registry が、この処理系のレジストリと食い違う: 一覧に無い %s / 余分 %s"
        % (sorted(set(api.op_names()) - reg)[:5], sorted(reg - set(api.op_names()))[:5]))
    nary = {r["name"] for r in rows if r["tier"] == "nary"}
    assert nary == set(api.op_names(include_nary=True)) - set(api.op_names()), (
        "一覧の n-ary が、この処理系の n-ary と食い違う")


def _index():
    import json
    import os
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "docs", "OP_INDEX.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def test_the_listing_reaches_every_tier_the_index_knows():
    """★2026-09-25: ``list_ops()`` は台帳層の 1,238 op を 1 つも返していなかった。

    索引側では 2026-09-15 に塞がれた欠陥で、**Python から呼ぶ一覧だけが取り残されて
    いた**。件数を数えた人が「無い」と結論する形の静かな欠落なので、2 つの入口が
    同じ op を数えることを門にする。
    """
    _assert_listing_matches_the_index(api.list_ops(include_ledger=True), _index())


def test_the_tier_gate_catches_a_listing_that_drops_a_tier():
    """★門を壊して確かめる —— 台帳を外した既定の一覧は、索引と食い違うこと。"""
    with pytest.raises(AssertionError) as e:
        _assert_listing_matches_the_index(api.list_ops(), _index())
    #: ★台帳をまるごと外すと「層が現れない」で落ちる —— この門が見張る事故そのもの。
    assert "層が在る" in str(e.value) or "台帳層" in str(e.value), str(e.value)


def test_the_default_listing_still_holds_the_image_vocabulary():
    """既定は据え置き —— 台帳を既定に混ぜると、パイプラインと進化の語彙が変わる。"""
    tiers = {r["tier"] for r in api.list_ops()}
    assert tiers == {"registry", "nary"}, tiers


def test_the_index_and_the_listing_share_one_ledger_table():
    """台帳の表は 1 つだけ(``api.ledger_rows``)。索引側はそこへ委譲する。"""
    import imgevolve
    assert ({r["name"] for r in imgevolve._ledger_rows(set())}
            == {r["name"] for r in api.ledger_rows()})


def test_the_listing_holds_everything_this_process_has():
    _assert_the_listing_holds_everything_this_process_has(api.list_ops(include_ledger=True))


def test_that_gate_catches_a_listing_that_drops_one_registry_op():
    """★門を壊して確かめる —— レジストリの 1 本を落とした一覧は落ちること。"""
    rows = api.list_ops(include_ledger=True)
    victim = next(r["name"] for r in rows if r["tier"] == "registry")
    with pytest.raises(AssertionError) as e:
        _assert_the_listing_holds_everything_this_process_has(
            [r for r in rows if r["name"] != victim])
    assert victim in str(e.value)


def test_the_tier_gate_survives_an_environment_without_the_heavy_extras(monkeypatch):
    """★CI の環境をここで作って確かめる —— **待たずに**。

    CI は py3.11 にしか torch / kornia / opencv-contrib / mahotas を入れない。
    2026-09-25 の実測では、そのせいで **26 op** が索引にあって一覧に無かった。
    その形を作って、門が**通る**ことを見る(層は欠けていないので通ってよい)。
    """
    index = _index()
    heavy = {o["name"] for o in index["ops"]
             if o["tier"] in ("registry", "color")
             and o["name"].startswith(("dl_", "xkor_", "xcv3_", "xmh_"))}
    assert len(heavy) >= 20, "重い extras の op が %d 本しか見つからない" % len(heavy)
    rows = [r for r in api.list_ops(include_ledger=True) if r["name"] not in heavy]
    _assert_listing_matches_the_index(rows, index)


def test_the_ledger_omission_is_never_excused_as_an_environment_difference():
    """★台帳 1 本を落としたら、環境差の話にせず落ちること。"""
    rows = api.list_ops(include_ledger=True)
    victim = next(r["name"] for r in rows if r["tier"] == "ledger")
    with pytest.raises(AssertionError) as e:
        _assert_listing_matches_the_index([r for r in rows if r["name"] != victim], _index())
    assert "台帳層" in str(e.value) and victim in str(e.value)
