"""Coverage recipes (fullseye/recipebook): every family has one, every recipe really runs.

Gates (none of them may be loosened to make a recipe pass — fix the recipe, or the op):

1. **Floor**: at least ``FLOOR_RECIPES`` coverage recipes (the index also carries recipes.py's 25).
2. **Family coverage**: every docs/ops family is the ``family`` of at least one recipe, and that family
   really holds one of the recipe's stage ops (a recipe cannot claim a family it does not touch).
3. **Types connect**: zero type cuts — each stage's input sort (OP_GRAPH ``inputs[j]``) equals the sort the
   referenced stage declared as output. At run time the values are also checked against chain_fuzz's
   ``TYPE_CHECKS`` predicates for those sorts (a declaration that lies is caught here, not downstream).
4. **e2e**: each recipe runs on two sample variants without an exception, every stage returns something,
   the final output is not degenerate (no numbers / no finite number / constant), the output moves when
   the input moves (a constant answer is not a measurement), and every ``expect`` truth gate holds on
   both variants.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

os.environ.setdefault("FULLSEYE_DEVICE", "cpu")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fullseye  # noqa: E402,F401  (puts the engine modules on sys.path)
from fullseye import recipebook as rb  # noqa: E402

#: 依頼の床は 100 本。実数(2026-11-03: 218)から少し下に置き、黙って減るのを止める。
FLOOR_RECIPES = 210

# A recipe may opt out of the "output moves with the input" check only with a written reason
# (e.g. the op returns a pass/fail verdict that is legitimately the same on both variants).
STATIC_OK = {r["name"]: r["static_ok"] for r in rb.RECIPES if r.get("static_ok")}


def _type_checks():
    try:
        from chain_fuzz import TYPE_CHECKS
    except Exception:  # noqa: BLE001
        return {}
    return TYPE_CHECKS


TYPE_CHECKS = _type_checks()


def test_recipe_floor():
    assert len(rb.RECIPES) >= FLOOR_RECIPES, (len(rb.RECIPES), FLOOR_RECIPES)


def test_every_family_has_a_recipe():
    fams = rb.families()
    assert len(fams) >= 50, "docs/ops families went missing: %d" % len(fams)
    have = {r["family"] for r in rb.RECIPES}
    missing = sorted(set(fams) - have)
    assert not missing, "families without a recipe: %s" % missing
    unknown = sorted(have - set(fams))
    assert not unknown, "recipes name families that docs/ops does not have: %s" % unknown


@pytest.mark.parametrize("name", rb.names())
def test_recipe_is_well_formed(name):
    r = rb.get(name)
    for key in ("name", "family", "task", "task_class", "input_sort", "sample", "stages", "note"):
        assert key in r, (name, key)
    assert r["task_class"] in rb.TASK_CLASSES, (name, r["task_class"])
    assert r["stages"], name
    assert r["sample"] in rb.SAMPLES, (name, r["sample"])
    fam_ops = rb.op_families()
    for st in r["stages"]:
        assert rb.edge(st["op"]) is not None, (name, st["op"], "not in OP_GRAPH")
        if st.get("call") == "raw":      # 台帳の入口を迂回するのは、壊れていると書いた段だけ
            assert len(st.get("call_reason", "")) >= 20, (name, st["op"], "say why fs.ledger cannot be used")
    touched = set().union(*(fam_ops.get(st["op"], set()) for st in r["stages"]))
    assert r["family"] in touched, (name, r["family"], sorted(touched))
    assert len(r["note"]) >= 20, (name, "write what the recipe is for and why these stages")


@pytest.mark.parametrize("name", rb.names())
def test_recipe_types_connect(name):
    r = rb.get(name)
    bad = [row for row in rb.connections(r) if not row[4]]
    assert not bad, "%s: type cuts (stage, arg, got, want): %s" % (name, [row[:4] for row in bad])


def _check_stage_types(r, outs):
    """宣言の出力型と実際の値(chain_fuzz の述語)。述語の無い型は見ない。"""
    lies = []
    for i, st in enumerate(r["stages"], 1):
        e = rb.edge(st["op"])
        o = e.get("output")
        pred = TYPE_CHECKS.get(o) or TYPE_CHECKS.get(rb.norm_sort(o))
        if pred is not None and o not in ("any", "poly"):
            try:
                ok = bool(pred(outs[i]))
            except Exception:  # noqa: BLE001
                ok = False
            if not ok:
                lies.append((i, st["op"], o, type(outs[i]).__name__, getattr(outs[i], "shape", None)))
    return lies


def _run_variant(r, variant):
    s = rb.sample(r, variant)
    out, outs = rb.run(r, s["value"], s["aux"])
    for i in range(1, len(r["stages"]) + 1):
        v = outs[i]
        assert v is not None, (r["name"], "stage %d returned None" % i)
        if isinstance(v, np.ndarray):
            assert v.size > 0, (r["name"], "stage %d returned an empty array" % i)
    return s, out, outs


@pytest.mark.parametrize("name", rb.names())
def test_recipe_runs_end_to_end(name):
    r = rb.get(name)
    s0, out0, outs0 = _run_variant(r, 0)
    s1, out1, outs1 = _run_variant(r, 1)
    lies = _check_stage_types(r, outs0)
    assert not lies, "%s: declared out sort does not match the value (stage, op, sort, type, shape): %s" % (name, lies)
    for v, out in ((0, out0), (1, out1)):
        why = rb.degeneracy(out)
        assert why is None, "%s (variant %d): %s" % (name, v, why)
    if name not in STATIC_OK:
        f0, f1 = rb.fingerprint(out0), rb.fingerprint(out1)
        same = f0.shape == f1.shape and np.allclose(f0, f1, rtol=1e-9, atol=1e-12)
        assert not same, "%s: output does not change between two different inputs" % name
    for v, (s, out, outs) in enumerate(((s0, out0, outs0), (s1, out1, outs1))):
        bad = rb.check_expect(r, out, outs, s["truth"])
        assert not bad, "%s (variant %d): %s" % (name, v, bad)


# --- recipes.py (the 25 Studio sample pipelines) under the same e2e rules -------------------------
import recipes as _legacy  # noqa: E402

#: recipes.py の見本の標本。FA の 5 本は同梱の物理標本(真値は tests/test_fa_samples.py が画素で照合)、
#: 他は合成の 2 種。「Segment — blob / coin」は remove_small(0.3)が半径 6〜8 px の小物を全部消す
#: (硬貨の大きさの物を想定した見本)ので、大きい円盤の標本で回す。
_LEGACY_SAMPLE = {"Segment — blob / coin": "disk_image"}


@pytest.mark.parametrize("name", _legacy.names())
def test_legacy_recipe_runs_end_to_end(name):
    import api
    import sample_images
    r = _legacy.get(name)
    if r.get("image"):
        inputs = [sample_images.load(r["image"])]
    else:
        gen = rb.SAMPLES[_LEGACY_SAMPLE.get(name, "blobs_image")]
        inputs = [gen(0)["value"], gen(1)["value"]]
    outs = [api.run_pipeline(im, _legacy.stages(name)) for im in inputs]
    for v, out in enumerate(outs):
        why = rb.degeneracy(out)
        assert why is None, "%s (input %d): %s" % (name, v, why)
    if len(outs) == 2:
        f0, f1 = rb.fingerprint(outs[0]), rb.fingerprint(outs[1])
        assert not (f0.shape == f1.shape and np.allclose(f0, f1)), "%s: output does not move with the input" % name
    legacy = {"name": name, "family": "2d", "input_sort": "image",
              "stages": [{"op": op, "a": a, "b": b} for op, a, b in r["stages"]]}
    assert rb.type_cuts(legacy) == 0, (name, rb.connections(legacy))


_MCP_NAMES = [r["name"] for r in rb.RECIPES if rb.is_mcp_runnable(r)]


@pytest.fixture(scope="module")
def mcp():
    from fullseye.mcp.catalog import Catalog
    from fullseye.mcp.handles import HandleStore
    return Catalog.load(), HandleStore(roots=[])


def test_mcp_runnable_floor():
    """MCP でそのまま走るレシピの数(2026-11-03: 58)。黙って python 扱いに落ちるのを止める。"""
    assert len(_MCP_NAMES) >= 55, len(_MCP_NAMES)


@pytest.mark.parametrize("name", _MCP_NAMES)
def test_mcp_runnable_recipe_runs_through_mcp_pipeline(name, mcp):
    """runner = mcp のレシピは、MCP の fullseye_pipeline に渡して実際に走り、Python の runner と同じ答えになる。"""
    from fullseye.mcp.server import call_tool
    cat, store = mcp
    r = rb.get(name)
    s = rb.sample(r, 0)
    h = store.put(np.asarray(s["value"], float), sort=r["input_sort"], provenance=[{"synthetic": True}])["handle"]
    want, _ = rb.run(r, s["value"], s["aux"])        # 先に: MCP の pipeline は終わると照合の見本を外す
    args = {"handle": h, "stages": rb.mcp_stages(r)}
    if {st["op"] for st in r["stages"]} & {"ncc_locate", "shape_locate"}:
        # 照合の op は MCP では template_handle で見本を受ける(標本はスレッドに登録している)。
        import ops
        tpl = ops._MATCH_CTX.get("template")
        assert tpl is not None, (name, "the sample must register its template")
        args["template_handle"] = store.put(np.asarray(tpl, float), sort="image",
                                            provenance=[{"synthetic": True}])["handle"]
    res = call_tool("fullseye_pipeline", args, cat, store)
    assert res.get("isError") is False, (name, res["content"][0]["text"][:600])
    sc = res["structuredContent"]
    # 最終段の値は stages[-1]["value_handle"] が指す(配列でない値でも handle に入る)。
    last = sc["stages"][-1]
    got = store.get(last.get("value_handle") or sc["handle"])[1]
    f_got, f_want = rb.fingerprint(got), rb.fingerprint(want)
    assert f_got.shape == f_want.shape and np.allclose(f_got, f_want, rtol=1e-9, atol=1e-9), name


def test_every_recipe_has_a_japanese_note():
    """ja の検索文は英語の名前・説明と op の要約だけだと、日本語の問いで族の当たりが 10/30 だった
    (2026-11-03 実測、目隠し問い合わせ)。手書きの日本語の名前と説明を全レシピに付ける。"""
    NOTES_JA = rb.notes_ja()
    want = set(rb.names()) | set(_legacy.names())
    assert set(NOTES_JA) == want, (sorted(want - set(NOTES_JA))[:5], sorted(set(NOTES_JA) - want)[:5])
    short = [k for k, v in NOTES_JA.items() if len(v) < 10 or not any(ord(c) > 0x3000 for c in v)]
    assert not short, short[:5]


def test_static_ok_reasons_are_written():
    for name, why in STATIC_OK.items():
        assert isinstance(why, str) and len(why) >= 20, name
