"""CI-resident op probe: every registry op runs on structured inputs through the facade.

Counts THREE things separately (memory rule: coverage must distinguish "ran /
refused every time / could not build an argument"), because a single success
number lets a permanently broken op hide inside "861/861 callable":

* ``fallback`` — the op body raised and the ledger recorded it (``backend_safe``);
* ``raised``   — a core op without a guard raised through the facade;
* ``degenerate`` — the op ran but returned its input unchanged or a constant on a
  structured, non-constant input.

Every degenerate op must be listed in ``docs/OP_PROBE_ALLOWLIST.json`` with a
reason a reviewer verified (knob 0.5 = "no transform", no holes in the probe mask,
no template set, contract says constant …). A NEW degenerate op, or a fallback /
raise on the probe inputs, fails this test — that is the point.

This is the permanent form of the 2026-09-02 "runtime degeneracy" audit
(``out/robustness-audit-2026-09-02/probe_runtime_degeneracy.py``), run on every CI.
"""
import json
import os
import warnings

import numpy as np
import pytest

import api
import backend_safe as bs
import ops

HERE = os.path.dirname(os.path.abspath(__file__))
ALLOWLIST = os.path.join(HERE, "..", "docs", "OP_PROBE_ALLOWLIST.json")


def _img(n=48):
    y, x = np.mgrid[0:n, 0:n]
    g = np.clip(0.5 + 0.3 * np.sin(x / 5.0) * np.cos(y / 7.0), 0, 1)
    g[10:20, 25:40] = 0.9
    g[30:42, 8:18] = 0.1
    return g


def _img_bank(n=48):
    """スイート全体が使っている ``conftest.image_bank()['normal']`` と同じ式。

    ★2 枚目を足した理由(2026-09-05 実測): この門は**正しい場所に立っていた**のに、
    探針が 1 枚だったせいで ``xsitk_huang_thresh`` が**どのノブでも必ず失敗する**
    状態を 1 度も報告しなかった。実測:

    ==================  ================  ==================
    入力                相異なる値        Huang(全ノブ)
    ==================  ================  ==================
    sin/cos(元の探針)   1,989             4/4 成功
    勾配+円+市松        2,260             **4/4 失敗**
    ==================  ================  ==================

    値の個数はほぼ同じで、違うのは**構造**だけ。
    「自分が思いついた入力で確かめた」は「確かめた」ではない(規律 2)。
    """
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    grad = xx / (n - 1)
    disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.4) ** 2) < (n * 0.18) ** 2
    checker = ((xx.astype(int) // 6 + yy.astype(int) // 6) % 2) * 0.15
    noise = 0.03 * np.random.default_rng(20260812).standard_normal((n, n))
    return np.clip(0.35 * grad + 0.45 * disk + checker + noise, 0.0, 1.0)


#: 構造の違う探針。**どれか 1 つでも失敗したら失敗**として扱う。
_IMAGE_MAKERS = (("sincos", _img), ("bank", _img_bank))

#: ノブも 1 点では足りない(範囲の端で初めて壊れる op がある)。
_KNOBS = ((0.5, 0.5), (0.15, 0.85))


def _inputs(maker):
    g = maker()
    return {
        "image": g,
        "region": (g > 0.55).astype(np.float64),
        "color": np.stack([g, np.roll(g, 5, 0), np.roll(g, 9, 1)], -1),
        "volume": np.stack([np.roll(maker(24), k, 0) for k in range(10)], 0),
    }


def _probe():
    banks = [(label, _inputs(maker)) for label, maker in _IMAGE_MAKERS]
    out = {}
    for op in ops.REGISTRY:
        if banks[0][1].get(op.in_sort) is None:
            out[op.name] = ("uncallable", op.in_sort)
            continue
        verdicts = []
        failure = None
        for label, ins in banks:
            v = ins[op.in_sort]
            for a, b in _KNOBS:
                bs.clear_fallbacks()
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        res = api.apply(v, op.name, a, b, on_error="fallback")
                except Exception as e:              # noqa: BLE001 - guard の無い core op
                    failure = failure or ("raised", "[%s a=%s b=%s] %s: %s"
                                          % (label, a, b, type(e).__name__, e))
                    continue
                fb = bs.fallbacks()
                if fb:
                    failure = failure or ("fallback", "[%s a=%s b=%s] %s"
                                          % (label, a, b, fb[0]["error"]))
                    continue
                tag = "ok"
                if isinstance(res, np.ndarray) and res.size > 1:
                    if res.shape == v.shape and np.array_equal(res, v):
                        tag = "identity"
                    elif np.all(res == res.flat[0]):
                        tag = "constant"
                verdicts.append(tag)
        if failure is not None:
            out[op.name] = failure
            continue
        # 退化の判定は**全探針で退化**のときだけ(1 枚でまともに動くなら退化ではない)。
        if verdicts and all(t == "identity" for t in verdicts):
            out[op.name] = ("identity", op.in_sort)
        elif verdicts and all(t == "constant" for t in verdicts):
            out[op.name] = ("constant", op.in_sort)
        else:
            out[op.name] = ("ok", op.in_sort)
    return out


@pytest.fixture(scope="module")
def probe():
    return _probe()


@pytest.fixture(scope="module")
def allow():
    with open(ALLOWLIST, encoding="utf-8") as f:
        return json.load(f)


def test_probe_reaches_most_of_the_registry(probe):
    n_call = sum(1 for t, _ in probe.values() if t != "uncallable")
    assert n_call >= 0.7 * len(probe), (n_call, len(probe))


def test_no_op_falls_back_or_raises_on_the_structured_probe(probe):
    bad = {k: v for k, v in probe.items() if v[0] in ("fallback", "raised")}
    assert not bad, "ops that FAIL on the structured probe inputs (dead or broken):\n" + \
        "\n".join("  %s: %s" % (k, v[1]) for k, v in sorted(bad.items()))


def test_every_degenerate_op_is_allowlisted_with_a_reason(probe, allow):
    degenerate = {k: v[0] for k, v in probe.items() if v[0] in ("identity", "constant")}
    listed = allow["ops"]
    new = {k: t for k, t in degenerate.items() if k not in listed}
    assert not new, ("NEW degenerate ops (identity/constant on a structured input). Verify each "
                     "with other knobs/inputs and add it to docs/OP_PROBE_ALLOWLIST.json with the "
                     "reason, or fix it:\n" + "\n".join("  %s: %s" % kv for kv in sorted(new.items())))
    for k, entry in listed.items():
        assert isinstance(entry.get("reason"), str) and len(entry["reason"]) > 10, k


def test_allowlist_has_no_stale_entries(probe, allow):
    """An allowlisted op that is no longer degenerate (fixed, or removed) must be dropped,
    so the list stays an honest picture rather than a growing waiver."""
    degenerate = {k for k, v in probe.items() if v[0] in ("identity", "constant")}
    stale = [k for k in allow["ops"] if k not in degenerate and k in probe]
    gone = [k for k in allow["ops"] if k not in probe]
    assert not stale and not gone, {"no_longer_degenerate": stale, "not_in_registry": gone}
