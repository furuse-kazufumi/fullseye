"""op の契約を、**入力を機械に作らせて**確かめる(property-based testing)。

手で書くテストは「思いついた入力」しか通らない。2026-09-05 の実測がその証拠で、
テスト 11,254 件が緑のまま、0 サイズ入力でのプロセス死・14 op の NaN 流出・
全 NaN でのハングが残っていた —— **個別のテストに空配列は 51 箇所あったのに、
レジストリ全体を退化入力で舐める検査が 1 つも無かった**から。

`tests/test_degenerate_inputs.py` は「私が思いついた退化」を固定で流す。
ここはその先で、**Hypothesis に入力を探させる**。落ちたときに縮約された
最小反例が出るのが効くところで、「512x512 のこの絵で落ちる」ではなく
「(1,2) の [[0.0, 1.0]] で落ちる」まで削ってから見せてくれる。

検査するのは 1 つだけ —— **op は契約を破らない**:

* 例外は投げてよい(``backend_safe`` が台帳に記録して sort の fallback へ落とす)
* 返すなら**有限**で、**宣言した out_sort に合う形**
* プロセスを殺さない(ここが緑であること自体が証拠。落ちる op があれば
  pytest ごと死ぬので、赤ではなく「テストが消える」形で現れる)

op も Hypothesis に選ばせるので、**実行のたびに違う組み合わせ**を試す。
1 回の CI で全 op を尽くすのではなく、回を重ねて空間を舐める設計。
失敗例は ``.hypothesis/`` に残り、次回は真っ先に再試行される。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from hypothesis.extra import numpy as hnp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import ops  # noqa: E402

#: image / region を取る op に絞る —— 2-D の絵は Hypothesis で素直に作れて、
#: レジストリの大半(881 中 647)を占める。他の sort は形が特殊なので
#: `op_probe.sample_probes` の固定種で見る(test_op_knob_liveness.py)。
_IMAGE_OPS = [o for o in ops.REGISTRY if o.in_sort in ("image", "region", "any")]

#: 画像は [0,1] の有限値という契約。**幅か高さが 1 の細長い絵**も作らせる ——
#: 窓・近傍・勾配の境界条件はそこで壊れる。
_IMAGES = hnp.arrays(
    dtype=np.float64,
    shape=hnp.array_shapes(min_dims=2, max_dims=2, min_side=1, max_side=12),
    elements=st.floats(min_value=0.0, max_value=1.0,
                       allow_nan=False, allow_infinity=False, width=64),
)


def _contract_ok(out, out_sort):
    """返り値が「有限で、宣言した sort に合う」か。"""
    if out_sort == "contour":
        return isinstance(out, dict) and "cs" in out and "shape" in out
    a = np.asarray(out)
    if a.dtype == object:
        return False
    a = np.asarray(a.real if np.iscomplexobj(a) else a, dtype=float)
    if a.size and not np.all(np.isfinite(a)):
        return False
    if out_sort == "region":
        return bool(a.size == 0 or np.all((a == 0.0) | (a == 1.0)))
    return True


@settings(max_examples=250, deadline=None,
          suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large])
@given(idx=st.integers(min_value=0, max_value=max(0, len(_IMAGE_OPS) - 1)), img=_IMAGES)
def test_an_op_either_raises_or_returns_a_finite_sort_valid_value(idx, img):
    """どの op に何を渡しても、**黙って契約を破らない**。

    落ちたときは Hypothesis が入力を縮約するので、失敗メッセージの配列が
    そのまま最小再現になる。
    """
    op = _IMAGE_OPS[idx]
    try:
        out = op.fn(img.copy(), 0.5, 0.5)
    except Exception:                                     # noqa: BLE001 - 例外は契約内
        return
    assert _contract_ok(out, op.out_sort), (
        "%s(in=%s out=%s) が契約を破った: shape=%r 入力 shape=%r\n入力=%r"
        % (op.name, op.in_sort, op.out_sort, np.shape(out), img.shape, img))


@settings(max_examples=150, deadline=None,
          suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large])
@given(idx=st.integers(min_value=0, max_value=max(0, len(_IMAGE_OPS) - 1)),
       img=_IMAGES,
       a=st.floats(min_value=0.0, max_value=1.0),
       b=st.floats(min_value=0.0, max_value=1.0))
def test_the_knobs_cannot_break_the_contract_either(idx, img, a, b):
    """``a`` / ``b`` を [0,1] のどこに置いても契約が保たれる。

    ノブは進化アルゴリズムが**端まで振る**ので、0.0 と 1.0 の近傍で
    窓幅 0・σ 0・除数 0 が生まれやすい。
    """
    op = _IMAGE_OPS[idx]
    try:
        out = op.fn(img.copy(), a, b)
    except Exception:                                     # noqa: BLE001
        return
    assert _contract_ok(out, op.out_sort), (
        "%s が a=%r b=%r で契約を破った: shape=%r 入力 shape=%r"
        % (op.name, a, b, np.shape(out), img.shape))


def test_the_property_test_actually_covers_the_registry():
    """性質検査が空回りしていないこと(母数を出す)。

    `@given` が 0 件の op を回していても pytest は緑になる —— それでは
    「発見ゼロ」が「未実行」の言い換えになる。
    """
    assert len(_IMAGE_OPS) > 500, (
        "image/region を取る op が %d 本しか見えない(検査の前提が違う)"
        % len(_IMAGE_OPS))
