"""studio_search(Studio 案 ①: 目的検索を「適用できる / 前処理が必要 / その他」に分ける)の門。

真値は 3 つ: (1) 検索そのものは ``fullseye.opsearch.search_ops`` の順位、(2) 型の宣言は索引の in/out と
``opassist`` の producers / consumers、(3) 値から型を推す規則は ``studio.inspect_result`` の kind。
いずれも自分の出力を自分で検算しない(索引・台帳・Studio の別経路で数える)。
"""
import numpy as np
import pytest

import api
import opassist
import studio_search as ss
from fullseye import opsearch

_RNG = np.random.default_rng(20261020)


def _region():
    """小さな点が散った二値の領域(0/1 の bool)。"""
    m = np.zeros((48, 48), bool)
    m[8:30, 8:30] = True
    m[40, 40] = m[3, 44] = m[44, 3] = True
    return m


def _image():
    return _RNG.random((48, 48))


@pytest.fixture(autouse=True)
def _fresh():
    ss.clear_caches()
    yield
    ss.clear_caches()


def _names(res, group):
    return [e["name"] for e in res[group]]


# --------------------------------------------------------------------------- #
# 型の推定                                                                     #
# --------------------------------------------------------------------------- #
def _samples():
    rgb = _RNG.random((12, 12, 3))
    lab = np.zeros((20, 20), np.int32)
    lab[2:8, 2:8], lab[10:18, 10:18], lab[2:6, 12:18] = 1, 2, 3
    return {
        "mask_bool": (_region(), "mask"),
        "mask_float01": (_region().astype(float), "mask"),
        "labels": (lab, "labels2d"),
        "image_float": (_image(), "image2d"),
        "image_uint8_photo": (_RNG.integers(0, 256, (32, 32)).astype(np.uint8), "image2d"),
        "complex_image": (_image() + 1j * _image(), "cimage"),
        "rgb": (rgb, "rgbimage"),
        "rgba": (_RNG.random((12, 12, 4)), "rgba"),
        "flow": (_RNG.random((2, 12, 12)), "flow2d"),
        "signal": (_RNG.random(64), "signal"),
        "points": (_RNG.random((30, 3)), "points"),
        "volume": (_RNG.random((6, 7, 8)), "voxel"),
        "contour": ({"cs": [np.zeros((4, 2))]}, "contour"),
        "table": ({"distance": np.arange(5.0), "t": np.arange(5.0)}, "table"),
        "scalar": (3.5, "scalar"),
        "number_list": ([1.0, 2.0, 3.0], "signal"),
        "text": ("abc", "text"),
    }


def test_current_sort_of_samples():
    s = _samples()
    assert len(s) == 17
    for name, (val, want) in s.items():
        assert ss.current_sort_of(val) == want, name


def test_current_sort_of_unknown_is_none():
    assert ss.current_sort_of(None) is None
    assert ss.current_sort_of(np.zeros((0, 3))) is None
    assert ss.current_sort_of(object()) is None
    assert ss.current_sort_of([]) is None


#: 型 -> studio.inspect_result の kind として許されるもの。
#: inspect_result は見せ方の分類で型より粗い(ラベル画像も点群も「image」、体積は「color」)ので、
#: 「この型なら、この kind に出るはず」という**含意**で照合する(逆向きは一意でない)。
_KIND_OF_SORT = {
    "mask": {"region"}, "labels2d": {"image"}, "image2d": {"image"}, "cimage": {"image"},
    "rgbimage": {"color"}, "rgba": {"color"}, "flow2d": {"flow2d"}, "signal": {"series"},
    "points": {"image"}, "voxel": {"color"}, "contour": {"contour"}, "table": {"table"},
    "scalar": {"feature"}, "text": {"object"},
}


def test_current_sort_agrees_with_inspect_result():
    studio = pytest.importorskip("studio")
    checked = 0
    for name, (val, want) in _samples().items():
        if name == "number_list":
            continue                       # inspect_result は 1 要素の list を feature と読む(長さ 3 は tuple 扱い)
        kind = studio.inspect_result(val)["kind"]
        got = ss.current_sort_of(val)
        assert got == want
        assert kind in _KIND_OF_SORT[got], "%s: sort %s but inspect_result kind %s" % (name, got, kind)
        checked += 1
    assert checked == 16


def test_probe_mapping_gate_detects_a_wrong_mapping():
    """門自体を壊して確かめる: 二値配列を image2d と答える偽の推定は、この表で検出される。"""
    studio = pytest.importorskip("studio")
    val = _region()
    assert studio.inspect_result(val)["kind"] == "region"
    assert studio.inspect_result(val)["kind"] not in _KIND_OF_SORT["image2d"]


# --------------------------------------------------------------------------- #
# 3 群への分け方                                                               #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("query", ["小さい領域を消す", "remove small regions"])
def test_region_input_puts_region_ops_in_applicable(query):
    res = ss.search_grouped(query, _region())
    assert res["current_sort"] == "mask"
    assert len(res["applicable"]) >= 3
    assert "remove_small" in _names(res, "applicable")
    assert "fill_up_shape" in _names(res, "applicable") or "sk_remove_holes" in _names(res, "applicable")
    assert "remove_small" not in _names(res, "needs_preprocessing")
    # 画像だけの op は前処理が要る: 橋は空でなく、区間の端が型で繋がる
    need = {e["name"]: e for e in res["needs_preprocessing"]}
    assert "sk_area_opening" in need, sorted(need)
    e = need["sk_area_opening"]
    assert e["fit"] == "bridge" and 1 <= len(e["bridge"]) <= 2


@pytest.mark.parametrize("query", ["小さい領域を消す", "remove small regions"])
def test_image_input_flips_the_groups(query):
    res = ss.search_grouped(query, _image())
    assert res["current_sort"] == "image2d"
    assert "sk_area_opening" in _names(res, "applicable")
    assert "remove_small" in _names(res, "needs_preprocessing")
    assert "remove_small" not in _names(res, "applicable")
    br = {e["name"]: e["bridge"] for e in res["needs_preprocessing"]}["remove_small"]
    assert br == ["otsu"]                  # 画像 -> 領域は大津の二値化が最短(レジストリの 1 手)


def test_contour_query_with_region_and_image():
    reg = ss.search_grouped("輪郭", _region())
    assert "gen_contour_region_xld" in _names(reg, "applicable")
    assert "select_shape_xld" in _names(reg, "needs_preprocessing")
    assert {e["name"]: e["bridge"] for e in reg["needs_preprocessing"]}["select_shape_xld"] == ["gen_contour_region_xld"]
    img = ss.search_grouped("輪郭", _image())
    assert "xpil_contour" in _names(img, "applicable")
    assert "xmh_bwperim" in _names(img, "needs_preprocessing")
    assert "xmh_bwperim" in _names(reg, "applicable")        # 同じ op が型で群を替える


def test_no_current_value_is_all_other_in_search_order():
    for q in ("小さい領域を消す", "remove small regions", "輪郭"):
        ref = opsearch.search_ops(q, 20)
        res = ss.search_grouped(q, None)
        assert res["applicable"] == [] and res["needs_preprocessing"] == []
        assert [e["name"] for e in res["other"]] == [o["name"] for o in ref["ops"]]
        assert [e["score"] for e in res["other"]] == [o["score"] for o in ref["ops"]]
        assert len(res["other"]) > 5
        assert {e["fit"] for e in res["other"]} == {"unknown"}


def test_current_sort_argument_overrides_the_value():
    res = ss.search_grouped("remove small regions", _image(), current_sort="mask")
    assert res["current_sort"] == "mask"
    assert "remove_small" in _names(res, "applicable")


def test_groups_keep_search_score_order():
    res = ss.search_grouped("remove small regions", _region())
    for g in ("applicable", "needs_preprocessing", "other"):
        sc = [e["score"] for e in res[g]]
        assert sc == sorted(sc, reverse=True), g
    total = sum(len(res[g]) for g in ("applicable", "needs_preprocessing", "other"))
    assert total == len(opsearch.search_ops("remove small regions", 20)["ops"]) == 20


def test_row_fields_and_why():
    res = ss.search_grouped("remove small regions", _region(), lang="en")
    assert res["lang"] == "en"
    rows = res["applicable"] + res["needs_preprocessing"] + res["other"]
    assert len(rows) == 20
    for e in rows:
        assert set(e) >= {"name", "label", "in_sort", "out_sort", "score", "why", "bridge", "tier", "fit"}
        assert e["label"] and e["why"], e["name"]
        assert set(e["why"]) <= {"name", "alias", "summary", "synonym", "context", "meta"}
    rs = {e["name"]: e for e in res["applicable"]}["remove_small"]
    assert "name" in rs["why"] and rs["in_sort"] == "region" and rs["out_sort"] == "region"
    # ja の問い合わせでは表示名が日本語の要約になる
    ja = ss.search_grouped("小さい領域を消す", _region())
    assert ja["lang"] == "ja" and any(ord(c) > 0x3000 for c in ja["applicable"][0]["label"])


def test_synonym_facet_is_reported():
    res = ss.search_grouped("ノイズ除去", None)
    assert len(res["other"]) >= 5
    assert any("synonym" in e["why"] for e in res["other"]), [e["why"] for e in res["other"]]


# --------------------------------------------------------------------------- #
# 橋(前処理の列)                                                             #
# --------------------------------------------------------------------------- #
def test_bridges_are_type_consistent_single_input_and_at_most_two():
    ix = {r["n"]: r for r in opsearch.load_index()["rows"]}
    n_checked = 0
    for q in ("小さい領域を消す", "輪郭", "remove noise", "edge", "point cloud"):
        for cur_val in (_region(), _image(), _RNG.random(32), _RNG.random((20, 3))):
            res = ss.search_grouped(q, cur_val)
            cur = ss.canonical_sort(res["current_sort"])
            for e in res["needs_preprocessing"]:
                br = e["bridge"]
                assert 1 <= len(br) <= 2 and e["name"] not in br
                first_in = ss.canonical_sort(ix[br[0]]["i"])
                assert first_in == cur, (q, e["name"], br)
                for a, b in zip(br, br[1:]):
                    assert ss.canonical_sort(ix[a]["o"]) == ss.canonical_sort(ix[b]["i"])
                tgt = ss.canonical_sort(e["in_sort"].split("×")[0].strip())
                assert ss.canonical_sort(ix[br[-1]]["o"]) == tgt
                assert all("×" not in ix[b]["i"] for b in br)          # 複数入力の op は橋にしない
                n_checked += 1
    assert n_checked > 40


def test_bridge_ledger_steps_agree_with_opassist():
    """橋の最後の op は、台帳なら opassist.producers(その出力型) に載っている(別経路の照合)。"""
    ix = {r["n"]: r for r in opsearch.load_index()["rows"]}
    ledger = set(opassist.known_ops())
    n = 0
    for q in ("輪郭", "remove small regions", "distance"):
        for e in ss.search_grouped(q, _image())["needs_preprocessing"]:
            last = e["bridge"][-1]
            if last in ledger:
                out = ix[last]["o"]
                assert last in opassist.producers(out), (last, out)
                n += 1
    assert n >= 1


def test_no_bridge_means_other():
    res = ss.search_grouped("輪郭", _region())
    assert len(res["other"]) >= 1
    assert len(res["needs_preprocessing"]) >= 1
    for e in res["other"]:
        assert e["bridge"] == [] and e["fit"] in ("none", "no_input")
    for e in res["needs_preprocessing"]:
        assert e["bridge"]


# --------------------------------------------------------------------------- #
# 実測(accepted_sorts)は上位 k 件にだけ・覚える                               #
# --------------------------------------------------------------------------- #
def _counting_accepted(monkeypatch):
    calls = []
    real = opassist.accepted_sorts

    def counted(name, *a, **k):
        calls.append(name)
        return real(name, *a, **k)
    monkeypatch.setattr(opassist, "accepted_sorts", counted)
    return calls


@pytest.mark.parametrize("k", [3, 8, 20])
def test_accepted_sorts_calls_never_exceed_k(monkeypatch, k):
    calls = _counting_accepted(monkeypatch)
    res = ss.search_grouped("輪郭", _image(), k=k)
    n_rows = len(res["applicable"] + res["needs_preprocessing"] + res["other"])
    assert n_rows == k
    assert len(calls) <= k
    assert len(calls) == len(set(calls))
    if k == 20:
        assert len(calls) >= 1                      # 数える仕掛けが生きている(空振りでない)


def test_accepted_sorts_is_cached_per_op(monkeypatch):
    calls = _counting_accepted(monkeypatch)
    ss.search_grouped("輪郭", _image(), k=20)
    n1 = len(calls)
    assert n1 >= 1
    ss.search_grouped("輪郭", _image(), k=20)
    assert len(calls) == n1                         # 2 回目は覚えを使う


def test_measured_polymorphism_moves_an_op_to_applicable(monkeypatch):
    """宣言は table でも、実測で image2d を通す op は applicable(fit=measured)。実測を差し替えて確かめる。"""
    base = ss.search_grouped("輪郭", _image())
    declared_table = [e for e in base["needs_preprocessing"] + base["other"] if e["tier"] == "ledger"]
    assert declared_table
    target = declared_table[0]["name"]
    ss.clear_caches()
    real = opassist.accepted_sorts
    monkeypatch.setattr(opassist, "accepted_sorts",
                        lambda n, *a, **k: dict(real(n, *a, **k), image2d="works") if n == target else real(n, *a, **k))
    res = ss.search_grouped("輪郭", _image())
    row = {e["name"]: e for e in res["applicable"]}[target]
    assert row["fit"] == "measured"


# --------------------------------------------------------------------------- #
# 0 件・決定性・名前の実在                                                     #
# --------------------------------------------------------------------------- #
def test_unknown_query_gives_zero_results_and_help():
    res = ss.search_grouped("xqzvwk plorfnat", _region())
    assert res["applicable"] == [] and res["needs_preprocessing"] == [] and res["other"] == []
    h = res["help"]
    assert h and h["hint"]
    assert h["categories"] and h["sorts"]
    assert h["unknown_terms"] == ["xqzvwk", "plorfnat"] or set(h["unknown_terms"]) >= {"xqzvwk"}


def test_zero_results_help_offers_nearest_terms_and_ops():
    h = ss.search_zero_results_help("gausian")
    assert len(h["nearest_ops"]) >= 1
    assert any("gaussian" in v or "gauss" in v for v in h["nearest_terms"].get("gausian", []) + h["nearest_ops"]), h
    assert h["categories"] and h["sorts"]
    h2 = ss.search_zero_results_help("remove_smal")
    assert "remove_small" in h2["nearest_ops"]
    en = ss.search_zero_results_help("zzzz", "en")["hint"]
    ja = ss.search_zero_results_help("zzzz", "ja")["hint"]
    assert en != ja


def test_empty_query_is_rejected():
    with pytest.raises(ValueError):
        ss.search_grouped("   ", _region())


def test_deterministic():
    a = ss.search_grouped("remove small regions", _region())
    ss.clear_caches()
    b = ss.search_grouped("remove small regions", _region())
    assert a == b
    assert a == ss.search_grouped("remove small regions", _region())


def test_every_row_name_resolves():
    n = 0
    ledger = set(opassist.known_ops())
    listed = {d["name"]: d for d in api.list_ops(include_ledger=True, include_algo=True)}
    for q in ("小さい領域を消す", "輪郭", "stereo depth", "ノイズ除去"):
        for v in (_region(), None):
            res = ss.search_grouped(q, v)
            for g in ("applicable", "needs_preprocessing", "other"):
                for e in res[g]:
                    # 単入力の 2-D op は find_op、台帳 op は known_ops、複数入力の op(symm_difference 等)は
                    # find_op に無く list_ops の nary 層で引く —— どれにも無い名前は 1 行も出さない
                    ok = api.find_op(e["name"]) is not None or e["name"] in ledger
                    if e["tier"] == "unavailable":
                        # 索引には在るが、この環境では登録されていない(任意の依存が無い殻)。出荷の索引が名前を持つ
                        assert e["name"] not in listed and not ok, e["name"]
                        assert api._shipped_index().get(e["name"]) is not None, e["name"]
                        continue
                    assert (ok or listed.get(e["name"], {}).get("tier") in ("nary", "z_algo")), e["name"]
                    assert e["name"] in listed, e["name"]
                    assert e["tier"] == listed[e["name"]]["tier"], e["name"]
                    n += 1
    assert n >= 100


def test_op_missing_in_this_environment_is_marked_unavailable_not_dropped(monkeypatch):
    """任意の依存が無い環境では、索引に在る op が登録されない(CI の殻で xmh_bwperim が実際にそうだった)。
    その行は落とさず ``tier="unavailable"`` で返し、型の判定は変えない。環境を差し替えて種を与える。"""
    real_find, real_list = api.find_op, api.list_ops
    gone = {"remove_small"}
    monkeypatch.setattr(api, "find_op", lambda n: None if n in gone else real_find(n))
    monkeypatch.setattr(api, "list_ops", lambda *a, **k: [d for d in real_list(*a, **k) if d["name"] not in gone])
    ss.clear_caches()
    res = ss.search_grouped("remove small regions", _region())
    row = {e["name"]: e for e in res["applicable"]}["remove_small"]
    assert row["tier"] == "unavailable" and row["fit"] == "declared"
    assert api._shipped_index().get("remove_small") is not None
    others = [e for e in res["applicable"] if e["name"] != "remove_small"]
    assert len(others) >= 3                      # 他の行は落ちていない(CI の殻では他にも unavailable が混ざりうる)
    assert all(e["fit"] in ("declared", "measured") for e in others)
