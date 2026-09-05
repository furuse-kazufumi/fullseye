"""``a`` / ``b`` のノブが本当に効いているかを、実測で数える。

op の説明には「``a`` が σ を 0.3〜3.0 に振る」のように**ノブが何を振るか**が
書いてある。書いてあることと**実際に動くか**は別で、0.1.3 の `sk_frangi`
(4 通りの設定で出力がビット一致していた)以来、同じ型の不具合が繰り返し出る。
ここはそれを op 名で数える。

**入力の作り方で数が変わる。** 2026-09-05 の実測:

=====================================================  ======
入力の作り方                                           候補数
=====================================================  ======
全 op に 28x28 の乱数 1 枚                                425
説明の主張と突き合わせ                                    108
構造のある画像を足す                                       98
sort ごとに正しい入力を作る                                29
**+ op 名で種を固定 + 1 op あたり 4 本(本ファイル)**       17
=====================================================  ======

425 → 17 はハーネスの粗が落ちただけで、コードは 1 行も変わっていない。
**測り方が雑なうちは、出てきた数は不具合の数ではない。**

最後の 29 → 17 で落ちたのは 2 種類:

* **入力を変えても出力が変わらない op** —— ノブ以前に動いていない。別の
  バグで `tests/test_backends_typed_liveness.py` が扱う。ここでは判別に使う
  だけで台帳にはしない: ``count_channels`` のように**定数を返すのが正しい**
  op が混じるので、これ自体は不具合の集合にならない。
* **共有の乱数を op の並び順に消費していたせいの揺れ** —— op を 1 つ足す
  だけで以降の入力が全部ずれ、効かないはずのノブが「効く」に化けていた
  (実測 4〜5 件)。いまは ``op_probe.sample_probes`` が **op 名から種を作る**
  ので、並び順にも実行回数にも依らない。

判定は端点 0.0 / 1.0 を必ず含めて振る(中間 2 点だけだと丸めで一致する)。

**ここが数えるのは「嘘」であって「死んだノブの総数」ではない。** 実測の全体像
(2026-09-05)は ノブ 1,762 個中、効くもの 719・「未使用」と正直に書いてあるもの
1,017・**説明は「振る」なのに効かないもの 26**(うち 7 は入力にも反応しない op)。
効かないノブでも説明が正直なら、この検査は通る —— 「本来は効くべきなのに
未使用のまま」を見つけるのは設計の問いで、機械には出せない。
そちらは docs/KNOWN_ISSUES.md が引き続き一覧になる。
"""
from __future__ import annotations

import hashlib
import os
import re
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import op_probe                                           # noqa: E402

#: 説明が「振る」と書いているのに、どの入力でも動かないノブ。
#: **この集合は縮む方向にしか動かしてはいけない**(直したら消す)。
#: 一件ずつの背景は docs/KNOWN_ISSUES.md #12〜#26。
KNOWN_DEAD_KNOBS = {
    ("erosion_circle", "b"), ("gray_erosion", "b"),
    ("mean_image", "b"),
    ("sp_local_max_sub_pix", "a"), ("sp_local_min_sub_pix", "a"),
    ("xcv3_sift_count", "a"), ("xcv_grabcut", "a"), ("xsk_orb_count", "a"),
    ("tb_beamform_delay_sum", "a"), ("tb_env_studio", "a"), ("tb_mat_pinv", "a"),
    ("tb_spectrogram", "a"), ("tb_wetness", "b"),
    ("tb_specular_diffuse_split", "a"), ("tb_specular_diffuse_split", "b"),
    # 種の二重定義(ruff F601)を直して**op が生き返った**あと、初めて
    # 「ノブが効かない」が本物の指摘として見えるようになった 2 件
    ("tb_specular_coefficient_map", "a"), ("tb_specular_coefficient_map", "b"),
    ("tb_tcspc_background_subtract", "a"),
}


SWEEP = (0.0, 0.35, 0.7, 1.0)

_UNUSED_BOTH = re.compile(
    r"(``a``\s*,?\s*``b``|``a``\s*(と|and)\s*``b``|a\s*,\s*b|a\s*と\s*b)"
    r"[^。\n]{0,14}(未使用|使われ|unused)|調整点は無く|no tunable")
_CLAIM = {"a": re.compile(r"``a``\s*(が|は|を|→|->|drives)"),
          "b": re.compile(r"``b``\s*(が|は|を|→|->|drives)")}
_UNUSED = {"a": re.compile(r"``a``[^。\n]{0,10}(未使用|使われて|unused)"),
           "b": re.compile(r"``b``[^。\n]{0,10}(未使用|使われて|unused)")}


def _fingerprint(x):
    """出力の指紋。contour(dict)は点数と各輪郭の座標和で代表させる。"""
    if isinstance(x, dict):
        cs = x.get("cs", [])
        a = np.asarray([float(len(cs))]
                       + [float(np.sum(np.asarray(c, dtype=float))) for c in cs[:8]]
                       + [float(np.size(np.asarray(c))) for c in cs[:8]])
    elif isinstance(x, (list, tuple)):
        a = np.asarray([float(len(x))]
                       + [float(np.sum(np.asarray(e, dtype=float))) for e in x[:8]])
    else:
        a = np.asarray(x, dtype=np.float64)
        a = np.nan_to_num(a, nan=-7.0, posinf=-8.0, neginf=-9.0)
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()[:12]


def _call(op, v, a, b):
    return op.fn(v.copy() if hasattr(v, "copy") else v, a, b)


def _knob_live(op, which, v):
    """``which`` を端から端まで振ると出力が変わるか。``None`` = 全点で例外。"""
    outs, ok = set(), False
    for t in SWEEP:
        a, b = (t, 0.5) if which == "a" else (0.5, t)
        try:
            outs.add(_fingerprint(_call(op, v, a, b)))
            ok = True
        except Exception:                                 # noqa: BLE001
            pass
    return (len(outs) > 1) if ok else None


def _claims(doc, which):
    if _UNUSED_BOTH.search(doc) or _UNUSED[which].search(doc):
        return False
    return bool(_CLAIM[which].search(doc))


@pytest.fixture(scope="module")
def audit():
    """全 op を 1 度だけ測る(重いので module スコープ)。"""
    import ops
    dead, lying, blind, unmeasured = set(), set(), set(), []
    for op in ops.REGISTRY:
        doc = (op.doc or op.fn.__doc__ or "")
        # 入力は **op 名から種を作る**(共有の乱数を並び順に消費すると、op を
        # 1 つ足しただけで以降の入力が全部ずれ、結果が実行ごとに揺れる)
        vs = op_probe.sample_probes(op.in_sort, op.name)
        if not vs:
            unmeasured.append((op.name, "in_sort=%s の代表値が作れない" % op.in_sort))
            continue
        # 入力に反応するか(ノブ以前の生死)
        seen = set()
        for v in vs:
            try:
                seen.add(_fingerprint(_call(op, v, 0.5, 0.5)))
            except Exception:                             # noqa: BLE001
                pass
        if len(seen) <= 1:
            blind.add(op.name)
        for which in ("a", "b"):
            res = [_knob_live(op, which, v) for v in vs]
            if all(r is None for r in res):
                unmeasured.append((op.name, "%s: どの入力でも例外" % which))
                continue
            live = any(r is True for r in res)
            if _claims(doc, which) and not live and op.name not in blind:
                dead.add((op.name, which))
            if (not _claims(doc, which)) and live and (
                    _UNUSED_BOTH.search(doc) or _UNUSED[which].search(doc)):
                lying.add((op.name, which))
    return {"dead": dead, "lying": lying, "blind": blind, "unmeasured": unmeasured}


def test_every_in_sort_has_a_representative_value(audit):
    """どの ``in_sort`` にも代表値が作れること。

    ここが埋まっていないと、その sort の op は**測られないまま素通り**する
    (「発見ゼロ」が「未実行」の言い換えになる)。
    """
    assert not audit["unmeasured"], (
        "測れなかった op が %d 件: %s"
        % (len(audit["unmeasured"]), audit["unmeasured"][:10]))


def test_dead_knobs_are_exactly_the_known_set(audit):
    """効かないノブが台帳ちょうどであること。

    新しく増えたら**その名前で**落ちる。直して減った場合も落ちる ——
    台帳から消すのを忘れると、次に壊れたときに気づけなくなるから。
    """
    got = audit["dead"]
    new = sorted(got - KNOWN_DEAD_KNOBS)
    fixed = sorted(KNOWN_DEAD_KNOBS - got)
    assert not new, ("『振る』と書いてあるのに効かないノブ(新規) %d 件: %s\n"
                     "配線するか、説明を『未使用』に直すか、どちらかにする。"
                     % (len(new), new))
    assert not fixed, ("効くようになったノブ %s —— KNOWN_DEAD_KNOBS から消すこと"
                       % fixed)


def test_no_op_claims_a_knob_is_unused_while_it_works(audit):
    """「未使用」と書いてあるのに実際は効く、が無いこと(説明が実装より控えめ)。"""
    assert not audit["lying"], (
        "未使用と書いてあるのに効くノブ: %s" % sorted(audit["lying"]))


def test_input_blind_ops_are_only_used_to_classify(audit):
    """入力に反応しない op は**数えるが、それ自体を不具合とは呼ばない**。

    ``count_channels`` のように「入力が何であれ同じ値を返すのが正しい」op が
    混じるので、この集合を不具合台帳にすると嘘になる。ここで確かめるのは
    **判別器として機能していること**(空でも全部でもない)だけ ——
    空なら :func:`test_dead_knobs_are_exactly_the_known_set` が
    「動いていない op」を「効かないノブ」として数えてしまう。
    """
    import ops
    blind = audit["blind"]
    assert blind, "判別器が 1 件も拾っていない(ノブの数え方が甘くなる)"
    assert len(blind) < len(ops.REGISTRY) // 4, (
        "入力に反応しない op が多すぎる(%d 件) —— 入力の作り方を疑う"
        % len(blind))
    assert not (blind & {n for n, _w in audit["dead"]}), (
        "判別が漏れている: 動いていない op がノブの台帳に混ざっている")


def test_the_audit_actually_exercised_the_registry(audit):
    """検査そのものが空回りしていないこと。

    ``audit`` が 0 件を返すのは「不具合が無い」ではなく「何も測れなかった」
    かもしれない —— 母数を出して、それが registry の規模であることを確かめる。
    """
    import ops
    assert len(ops.REGISTRY) > 800, "レジストリが小さすぎる(検査の前提が違う)"
    # 台帳が空になったら、この検査自体が意味を失っていないか点検する合図
    assert KNOWN_DEAD_KNOBS, (
        "台帳が両方とも空 —— 全部直ったなら、この検査を『0 件のまま維持する』"
        "形に書き換えること(空の集合と比べるだけの検査は事故に弱い)")
