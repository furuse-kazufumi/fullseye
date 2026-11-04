"""MCP の op カード(``fullseye/data/OP_CARDS.json``)の呼び出し例が、**その op を受け付ける入口**を書いていること。

2026-11-03 の完成度監査(A-2): ``tools/gen_mcp_data.py`` は全 op に一律 ``fullseye.apply(value, name, 0.5, 0.5)``
と書いていた。台帳 op(約 2,665 件)は ``fullseye.apply`` が KeyError(「typed-ledger operator ... run it with
fullseye.op_run」)で拒む。実測: ``fullseye.apply(np.linspace(0, 1, 256), "bandpass", 0.5, 0.5, on_error="raise")``。
``fullseye_op_cards`` だけが誤った呼び方を LLM に渡していた。

門は 2 段:

1. **全カード**の機械的な検査(実行しない): 入口(``entry``)が op の階層(``fullseye.list_ops``)と合う、
   ``op_run`` の呼び方の引数が ``opassist.param_spec`` の必須引数と一致する、ヘッダの件数が中身と一致する。
2. **入口ごとの標本を実際に実行**: カードの ``call`` の文字列の ``<...>`` に代表入力を入れて ``eval`` する。
   「入口違い」(apply が台帳 op を拒む KeyError、op_run の「not in any ledger」、引数名の不一致の TypeError)は
   0 件。代表入力が op に合わず op の中で落ちるもの(入口は正しい)は数えて報告し、合格の件数に床を置く
   (床が無いと、全部が「op の中で落ちた」でも通ってしまう)。

全件の実行は重い(台帳だけで約 150 秒)ので CI では標本だけ。全件は
``tests/test_op_card_calls_execute_2026_11_03.py`` の ``run_card`` を使って手で回す(報告に結果を残す)。
"""
from __future__ import annotations

import json
import os
import re
import warnings

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARDS = os.path.join(ROOT, "fullseye", "data", "OP_CARDS.json")
_PH = re.compile(r"<[^<>]+>")


def _cards() -> list:
    with open(CARDS, encoding="utf-8") as f:
        d = json.load(f)
    assert d["n_ops"] == len(d["ops"]) >= 3000, (d["n_ops"], len(d["ops"]))
    by = {e: sum(1 for c in d["ops"] if c.get("entry") == e) for e in ("apply", "op_run")}
    assert d.get("n_by_entry") == by, (d.get("n_by_entry"), by)
    assert by["apply"] >= 900 and by["op_run"] >= 2500, by
    return d["ops"]


def _tiers() -> dict:
    import fullseye
    t: dict = {}
    for row in fullseye.list_ops(include_ledger=True, include_algo=True):
        t.setdefault(row["name"], set()).add(row.get("tier"))
    return t


# ---------------------------------------------------------------- 1. 機械的な検査(全件)

def test_every_card_names_the_entry_that_accepts_the_op():
    """★カードの台帳(OP_CARDS.json)は全 backend のある環境で作る。レジストリの中身は backend で
    変わる(kornia → xkor_*、mahotas → xmh_*、torch → dl_*、opencv-contrib → xcv3_* が無ければ
    登録されない)ので、満杯でない環境では**この環境に居ない op のカードは確かめられない**。
    2026-11-04 の master(run 41724324673)の py3.12 で 26 枚が ``tiers=[]`` で「入口違い」に
    数えられた。居る op のカードは全部確かめ、居ない分は ``requires_full_registry`` で明示する
    (完全環境の py3.11 では skip ではなく失敗 —— そこでは居ない op のカードは本物の入口違い)。
    """
    import opassist
    from conftest import FULL_REGISTRY_BACKENDS, _have_backend, requires_full_registry
    full = all(_have_backend(b) for b in FULL_REGISTRY_BACKENDS)
    tiers = _tiers()
    bad, absent = [], []
    for c in _cards():
        name, entry, call = c["name"], c.get("entry"), c.get("call", "")
        t = tiers.get(name, set())
        if not t and not full:
            absent.append(name)
            continue
        if entry == "apply":
            ok = bool(t & {"registry", "nary"}) and call.startswith("fullseye.apply(") and (", %r, 0.5, 0.5" % name) in call
        elif entry == "op_run":
            ok = ("ledger" in t and not (t & {"registry", "nary"}) and opassist._ledger_entry(name)[1] is not None
                  and call.startswith("fullseye.op_run(%r" % name))
        else:
            ok = False
        if not ok:
            bad.append("%s: entry=%r tiers=%s call=%s" % (name, entry, sorted(map(str, t)), call))
    assert not bad, "%d 枚のカードが入口を間違えている:\n%s" % (len(bad), "\n".join(bad[:30]))
    if absent:
        print("レジストリが満杯でないので確かめていないカード %d 枚: %s" % (len(absent), ", ".join(absent)))
        requires_full_registry()


def test_op_run_cards_list_exactly_the_required_arguments():
    import opassist
    bad, n = [], 0
    for c in _cards():
        if c.get("entry") != "op_run":
            continue
        n += 1
        spec = opassist.param_spec(c["name"])
        want_data = [sp.get("sort") or sp["name"] for sp in spec if sp["kind"] == "data" and sp.get("required")]
        want_kw = [sp["name"] for sp in spec if sp["kind"] != "data" and sp.get("required")]
        inner = c["call"][len("fullseye.op_run("):-1]
        parts = [p.strip() for p in inner.split(", ")][1:]       # 先頭は op 名
        got_data = [p[1:-1] for p in parts if p.startswith("<")]
        got_kw = [p.split("=", 1)[0] for p in parts if "=" in p]
        if got_data != want_data or got_kw != want_kw or "knobs" in c:
            bad.append("%s: data %s != %s / kw %s != %s" % (c["name"], got_data, want_data, got_kw, want_kw))
    assert n >= 2500, n
    assert not bad, "\n".join(bad[:30])


def test_no_card_keeps_the_old_uniform_apply_call():
    old = [c["name"] for c in _cards() if "fullseye.apply(value," in c.get("call", "")]
    assert not old, old[:20]


# ---------------------------------------------------------------- 2. 実行(入口ごとの標本)

_WRONG_ENTRY = (
    (KeyError, re.compile(r"typed-ledger operator|unknown operator|not registered", re.I)),
    (ValueError, re.compile(r"not in any ledger", re.I)),
    (TypeError, re.compile(r"missing \d+ required|unexpected keyword argument|got multiple values", re.I)),
)


def _fill(call: str, values: list) -> tuple[str, dict]:
    """``<...>`` を左から順に変数 ``_v0, _v1, ...`` に置き換え、``eval`` 用の名前空間を返す。"""
    ns: dict = {}
    k = [0]

    def sub(_m):
        i = k[0]
        k[0] += 1
        ns["_v%d" % i] = values[i]
        return "_v%d" % i

    return _PH.sub(sub, call), ns


def _inputs_for(card: dict):
    """カードの ``<...>`` の数だけ代表入力を返す。作れなければ ``None``(数えて報告する)。"""
    n_ph = len(_PH.findall(card["call"]))
    if card["entry"] == "op_run":
        import opassist
        args, auto_kw = opassist.sample_input(card["name"])
        if any(a is None for a in args):
            return None
        kws = [m.group(1) for m in re.finditer(r"(\w+)=<[^<>]+>", card["call"])]
        if any(auto_kw.get(k) is None for k in kws):
            return None
        vals = list(args) + [auto_kw[k] for k in kws]
        return vals if len(vals) == n_ph else None
    import op_probe
    rng = np.random.default_rng(20261103)
    sorts = _PH.findall(card["call"])
    vals = []
    for s in sorts:
        s = s[1:-1]
        v = op_probe.sample_input(s, rng, structured=True)
        if v is None:
            return None
        vals.append(v)
    if card["name"] in ("ncc_locate", "shape_locate"):     # template は場面の切り出し
        vals[-1] = np.ascontiguousarray(vals[0][8:24, 8:24])
    return vals


def run_card(card: dict) -> tuple[str, str]:
    """カードの ``call`` を文字列のまま実行する。返り値 ``(status, detail)``。

    status: ``ok`` / ``wrong_entry``(門で 0 件)/ ``op_failed_on_sample``(入口は正しく、代表入力が op に合わない)/
    ``no_sample``(代表入力が作れない)/ ``missing_dependency``(optional 依存が無い環境)。
    """
    import fullseye
    vals = _inputs_for(card)
    if vals is None:
        return "no_sample", ""
    expr, ns = _fill(card["call"], vals)
    ns["fullseye"] = fullseye
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out = eval(expr, ns)  # noqa: S307 - 生成物の 1 行(自前の repo の中身)を実行する門
    except fullseye.MissingBackendError as exc:
        return "missing_dependency", str(exc)[:120]
    except Exception as exc:  # noqa: BLE001 - 種類で分ける
        if type(exc).__name__ == "MissingDependencyError":
            return "missing_dependency", str(exc)[:120]
        for typ, rx in _WRONG_ENTRY:
            if isinstance(exc, typ) and rx.search(str(exc)):
                return "wrong_entry", "%s: %s" % (type(exc).__name__, str(exc)[:200])
        return "op_failed_on_sample", "%s: %s" % (type(exc).__name__, str(exc)[:120])
    if card["entry"] == "op_run":
        assert isinstance(out, tuple) and len(out) == 2, "op_run は (result, notes) を返す"
    return "ok", ""


def _sample(entry: str, step: int) -> list:
    rows = [c for c in _cards() if c.get("entry") == entry]
    return rows[::step]


@pytest.mark.parametrize("entry,step,min_ok", [
    # 手元の実測(2026-11-03、CPU): apply 97 枚 = ok 96・op の中で落ちる 1 / op_run 134 枚 = ok 57・op の中で
    # 落ちる 24・代表入力なし 53。床はその約 9 割と 7 割(optional 依存の違う CI の版で揺れる分を見込む)。
    ("apply", 10, 85),
    ("op_run", 20, 40),
])
def test_card_calls_run_through_their_entry(entry, step, min_ok, monkeypatch, tmp_path):
    monkeypatch.setenv("FULLSEYE_ON_ERROR", "raise")      # apply の fallback が失敗を隠さないように
    monkeypatch.setenv("FULLSEYE_DEVICE", "cpu")
    monkeypatch.chdir(tmp_path)                            # 書く op が repo を汚さないように
    counts: dict = {}
    wrong = []
    for c in _sample(entry, step):
        st, detail = run_card(c)
        counts[st] = counts.get(st, 0) + 1
        if st == "wrong_entry":
            wrong.append("%s: %s -> %s" % (c["name"], c["call"], detail))
    print(entry, counts)
    assert not wrong, "入口違い:\n" + "\n".join(wrong)
    assert counts.get("ok", 0) >= min_ok, counts


def test_nary_cards_all_run():
    """n 項の 17 枚は全部(リストで渡す形を確かめる)。"""
    cards = [c for c in _cards() if c.get("entry") == "apply" and c["call"].startswith("fullseye.apply([")]
    assert len(cards) >= 15, len(cards)
    res = {c["name"]: run_card(c) for c in cards}
    bad = {k: v for k, v in res.items() if v[0] != "ok"}
    assert not bad, bad


def test_the_audit_repro_bandpass_card_is_op_run_and_runs():
    card = next(c for c in _cards() if c["name"] == "bandpass")
    assert card["entry"] == "op_run"
    assert card["call"] == "fullseye.op_run('bandpass', <signal>, rate=<number>, low=<number>, high=<number>)"
    import fullseye
    expr, ns = _fill(card["call"], [np.random.default_rng(0).random(256), 1000.0, 50.0, 200.0])
    ns["fullseye"] = fullseye
    result, notes = eval(expr, ns)  # noqa: S307
    assert result.shape == (256,) and np.isfinite(result).all()


def test_find_ops_does_not_give_a_pipeline_skeleton_to_ops_mcp_cannot_run():
    """監査 A-2 の後半: MCP で実行できない op に ``fullseye_pipeline(...)`` の骨格を付けていた。"""
    from fullseye.opsearch import _graph, _next_call_skeleton
    edges = {e["op"]: e for e in _graph()["edges"]}
    cards = {c["name"]: c for c in _cards()}
    names = [n for n in ("dem_slope", "bandpass") if n in edges]
    assert names
    for n in names:
        assert not edges[n].get("verified_executable"), n
        nc = _next_call_skeleton({"name": n, "in_sort": cards[n]["in_sort"]})
        assert "fullseye_pipeline" not in nc and "not executable in MCP" in nc, nc
        assert cards[n]["call"] in nc, nc
    # MCP で実行できる op には今まで通り骨格が付く
    ok = next(n for n, e in edges.items() if e.get("verified_executable") and n == "gauss_filter")
    assert "fullseye_pipeline" in _next_call_skeleton({"name": ok, "in_sort": "image"})


def test_every_find_ops_next_call_agrees_with_validate_pipeline():
    """骨格を付けた op は全部 MCP で実行できる、付けなかった op は全部できない(全 edge で数える)。"""
    from fullseye.opsearch import _graph, _next_call_skeleton
    n_pipe = n_py = 0
    bad = []
    for e in _graph()["edges"]:
        nc = _next_call_skeleton({"name": e["op"], "in_sort": (e.get("inputs") or [None])[0]})
        if "fullseye_pipeline" in nc:
            n_pipe += 1
            if not e.get("verified_executable"):
                bad.append(e["op"])
        else:
            n_py += 1
            if e.get("verified_executable"):
                bad.append(e["op"])
    assert n_pipe >= 900 and n_py >= 2000, (n_pipe, n_py)
    assert not bad, bad[:20]


def test_op_run_accepts_an_op_argument_called_name():
    """全件の実行で見つけた: 台帳の ``call(name, ...)`` が op の引数 ``name=`` と衝突していた(21 op)。"""
    import fullseye
    import opassist
    hit = [c["name"] for c in _cards() if c.get("entry") == "op_run"
           and any(sp["name"] == "name" for sp in opassist.param_spec(c["name"]))]
    assert len(hit) >= 15, hit
    result, _notes = fullseye.op_run("example_system", name="singlet")
    assert isinstance(result, dict)
    default, _ = fullseye.op_run("example_system")
    assert set(result) == set(default)
