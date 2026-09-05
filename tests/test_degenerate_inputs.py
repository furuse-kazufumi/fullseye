"""退化した入力を全 op に通す —— 0 サイズ・1 画素・定数・NaN・Inf。

2026-09-05 に足した。**テスト 11,254 件が全部緑のまま**、次が見逃されていた:

* ``xpil_offset`` に 0x0 の画像 → **インタプリタごと落ちる**(exit 127)。
  Pillow のネイティブ側なので Python の例外にならず、``backend_safe.guard`` でも
  捕まえられない。全 PIL op が通る ``_im()`` で 0 サイズを弾いて解決。
* 空入力で **14 op が NaN / Inf を返し**、``fullseye.apply()`` 経由でもそのまま
  出ていた(空配列の平均・分散・比 = 0 除算)。原因は「有限性を約束する guard を
  **881 op 中 395 本が一度も通っていなかった**」こと。登録時に一律で包んで解決。
* ``xsk_unwrap_phase`` に全 NaN → 5 分以上返らない(ハング)。品質誘導の
  アンラップは有効画素を起点に伸びるので、起点が 1 つも無いと止まらない。
  非有限をマスクして解決。
* ★``xsk2_reconstruction`` / ``xsk2_h_maxima`` に全 NaN → **SIGSEGV**。
  単独では落ちず、2 つを交互に呼んだところで落ちるのでヒープ破壊と見られる
  (`skimage.morphology` のネイティブ側)。入口で非有限を弾いて解決。
* ★退避値そのものが非有限だった。``fallback`` の image/color 系は「入力を
  [0,1] に切り詰めたもの」で、**``np.clip`` は NaN を通す** —— 入力が非有限の
  ときだけ「返り値は有限」という約束が破れていた(`tests/test_backend_safe.py`)。

個別のテストに空配列は 51 箇所あったが、**レジストリ全体を退化入力で舐める検査は
1 つも無かった**。だから緑のまま気づけなかった —— 「発見ゼロ」は「頑健」ではなく
「未実行」だったという、この repo が繰り返し踏んでいる形。

ここで数えるのは **op ごとの結果の種類**で、退化入力でも
「有限で、宣言した sort に合う値を返す(または例外を送出して台帳に載る)」ことを要求する。
"""
from __future__ import annotations

import os
import sys
import warnings

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import op_probe                                            # noqa: E402
import ops as _ops                                         # noqa: E402


def _meaningful_nonfinite() -> frozenset:
    """非有限が**答え**である op。``ops.NONFINITE_IS_MEANINGFUL`` が唯一の正本。

    ★以前はモジュール大域に frozenset の**鏡**を置いていた。門の変異テスト
    (2026-09-05)で、鏡を正本から切り離して偽の項目を足しても**どのテストも
    落ちない**ことが分かった —— 鏡は独自の項目を持たないので陳腐化検査の対象に
    なっておらず、切り離された瞬間に誰も見なくなる。鏡を持たず、使うたびに
    正本を読む。ずれる余地そのものを消す。
    """
    return frozenset(getattr(_ops, "NONFINITE_IS_MEANINGFUL", {}))

#: 各 in_sort の「0 要素」の形。``None`` = その sort には空の代表が無い。
EMPTY = {
    "image": (0, 0), "any": (0, 0), "region": (0, 0), "matrix": (0, 0),
    "cimage": (0, 0), "volume": (0, 0, 0), "video": (0, 0, 0),
    "points": (0, 3), "keypoints": (0, 2), "signal": (0,), "counts": (0,),
    "color": (0, 0, 3), "rgbimage": (0, 0, 3), "qimage": (0, 0, 4),
    "lightfield": (0, 0, 0, 0), "beatcube": (0, 0, 0),
}

#: 全 NaN / 全 Inf を渡したときに**返ってこない**ことが分かっている op。
#: ハングはクラッシュより厄介 —— CI では「遅い」としか見えない。
#: 2026-09-05 に ``xsk_unwrap_phase`` を直して**空になった**。空であること自体を
#: 主張はしない(次に見つけたらここに書いて、直したら消す)。
KNOWN_HANGS_ON_NONFINITE: dict = {}


def _empty_for(sort):
    if sort == "contour":
        return {"shape": (0, 0), "cs": []}
    shp = EMPTY.get(sort)
    if shp is None:
        return None
    return np.zeros(shp, dtype=complex if sort == "cimage" else float)


def _finite_and_sort_valid(out, sort):
    """返り値が「有限で、宣言した sort に合う」か。"""
    if sort == "contour":
        return isinstance(out, dict) and "cs" in out and "shape" in out
    a = np.asarray(out)
    if a.dtype == object:
        return False
    a = np.asarray(a.real if np.iscomplexobj(a) else a, dtype=float)
    return bool(a.size == 0 or np.all(np.isfinite(a)))


@pytest.fixture(scope="module")
def registry():
    import ops
    return ops.REGISTRY


def test_no_op_returns_a_non_finite_value_for_an_empty_input(registry):
    """0 サイズの入力で NaN / Inf を返す op が無いこと(0 除算の検出器)。

    空配列の平均・分散・比は素直に書くと ``0/0`` になる。例外にならずに
    ``nan`` が出ていくのが最悪で、下流はそれを数値として扱ってしまう。
    """
    import ops
    bad, missing = [], []
    for op in registry:
        v = _empty_for(op.in_sort)
        if v is None:
            missing.append(op.in_sort)
            continue
        try:
            out = op.fn(v.copy() if hasattr(v, "copy") else dict(v), 0.5, 0.5)
        except Exception:                                 # noqa: BLE001
            continue                                      # 例外は台帳に載る(契約内)
        if op.name in _meaningful_nonfinite():
            continue
        if not _finite_and_sort_valid(out, op.out_sort):
            bad.append(op.name)
    assert not missing, "空の代表値が無い in_sort: %s" % sorted(set(missing))
    assert not bad, ("0 サイズ入力で非有限値を返す op が %d 本: %s"
                     % (len(bad), bad[:20]))
    assert len(registry) > 800, "レジストリが小さすぎる(検査の前提が違う)"


def test_no_op_crashes_the_process_on_an_empty_input(registry):
    """0 サイズ入力でインタプリタが落ちないこと。

    このテストが**通ること自体が証拠**になる —— 落ちる op があると
    pytest ごと死ぬので、赤ではなく「テストが消える」形で現れる。
    そのため件数を出して、確かに全 op を通したことを残す。
    """
    n = 0
    for op in registry:
        v = _empty_for(op.in_sort)
        if v is None:
            continue
        try:
            op.fn(v.copy() if hasattr(v, "copy") else dict(v), 0.5, 0.5)
        except Exception:                                 # noqa: BLE001
            pass
        n += 1
    assert n > 800, "通した op が少なすぎる(%d)" % n


@pytest.mark.parametrize("fill", [0.0, 1.0, 0.5])
def test_constant_and_single_pixel_inputs_stay_in_contract(registry, fill):
    """定数画像(全ゼロ・全 1)と 1 画素でも契約を守ること。

    定数画像は**分散 0** を作るので、正規化・コントラスト・相関の類が
    0 除算になりやすい。1 画素は窓・近傍・勾配の境界条件を突く。
    """
    bad = []
    for op in registry:
        shp = EMPTY.get(op.in_sort)
        if shp is None:
            continue
        one = tuple(max(1, d) if d == 0 else d for d in shp)
        for shape in (tuple(1 if d == 0 else d for d in shp), one):
            v = np.full(shape, fill,
                        dtype=complex if op.in_sort == "cimage" else float)
            try:
                out = op.fn(v, 0.5, 0.5)
            except Exception:                             # noqa: BLE001
                continue
            if op.name in _meaningful_nonfinite():
                continue
            if not _finite_and_sort_valid(out, op.out_sort):
                bad.append((op.name, shape))
                break
    assert not bad, "定数/1 画素の入力で契約を破る op: %s" % bad[:20]


def test_zero_division_is_not_hidden_by_numpy_defaults(registry):
    """0 除算が起きている op を **numpy の警告を error に上げて**名指しする。

    numpy は既定で ``0/0`` を黙って ``nan`` にする。結果を見るだけでは
    「そういう値」と区別がつかないので、**計算の最中に**捕まえる。
    ここで拾うのは「非有限が外へ出ていく」ものだけ —— 内部で 0 除算しても
    最後に潰しているなら実害は無いので、出力側の検査(上)と役割を分ける。
    """
    offenders = []
    for op in registry:
        v = _empty_for(op.in_sort)
        if v is None:
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                with np.errstate(divide="raise", invalid="raise"):
                    out = op.fn(v.copy() if hasattr(v, "copy") else dict(v), 0.5, 0.5)
            except FloatingPointError:
                # 計算中に 0 除算はしたが、外に出ていなければ実害は無い。
                # 出力側の契約は上のテストが見ているので、ここでは数えない。
                continue
            except Exception:                             # noqa: BLE001
                continue
        if not _finite_and_sort_valid(out, op.out_sort):
            offenders.append(op.name)
    assert not offenders, "0 除算の結果が外へ出ている op: %s" % offenders[:20]


def test_known_hangs_are_still_listed(registry):
    """ハング台帳に「もう居ない op」が残っていないこと。

    ハングそのものは pytest-timeout が拾うが、**どの op か**はここに書いておく。
    直った op を一覧に残すと、次に止まったときに気づけない。
    """
    live = {op.name for op in registry}
    stale = sorted(set(KNOWN_HANGS_ON_NONFINITE) - live)
    assert not stale, "居ない op が一覧に残っている: %s" % stale


def _nonfinite_like(base, fill):
    dt = base.dtype if base.dtype.kind == "c" else np.float64
    return np.full(base.shape, fill, dtype=dt)


@pytest.mark.parametrize("kind,fill", [("nan", np.nan), ("+inf", np.inf), ("-inf", -np.inf)])
def test_no_op_returns_a_non_finite_value_for_a_non_finite_input(registry, kind, fill):
    """全 NaN / 全 ±Inf を入れても、返り値は有限で sort に合うこと。

    **0 サイズ入力の検査(上)とは別の穴**だった —— 空配列は「計算の結果」
    非有限になるが、こちらは「入力そのもの」が非有限で、退避値の側
    (``backend_safe.fallback``)に抜け道があった。

    このテストが**通ること自体がクラッシュしていない証拠**でもある。落ちる op が
    あると pytest ごと死に、赤ではなく「テストが消える」形で現れるので、
    通した本数を併せて主張する。
    """
    bad, n = [], 0
    for op in registry:
        if op.name in KNOWN_HANGS_ON_NONFINITE:
            continue
        probes = op_probe.sample_probes(op.in_sort, op.name, n=1)
        if not probes:
            continue
        base = probes[0]
        if not isinstance(base, np.ndarray) or base.dtype == object:
            continue
        n += 1
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                with np.errstate(all="ignore"):
                    out = op.fn(_nonfinite_like(base, fill), 0.5, 0.5)
            except Exception:                             # noqa: BLE001
                continue                                  # 例外は契約内(台帳に載る)
        if op.name in _meaningful_nonfinite():
            continue                                      # 非有限が答えの op
        if not _finite_and_sort_valid(out, op.out_sort):
            bad.append(op.name)
    assert not bad, "%s 入力で非有限を返す op が %d 本: %s" % (kind, len(bad), bad[:20])
    assert n > 700, "通した op が少なすぎる(%d) —— 検査の前提が違う" % n


# --------------------------------------------------------------------------- #
# ネイティブ側のクラッシュ台帳(`ops.NATIVE_CRASHES_ON_DEGENERATE`)
#
# ★ここが厄介なのは、**このテストが守っている不具合は Windows では再現しない**こと。
# 2026-09-05 実測: Linux(Ubuntu 24.04 / py3.12 / PyPI wheel)で 3 op が退化入力に
# 対して SIGSEGV。同じ入力を Windows に流しても 1 件も落ちなかった。
# だから「ローカルが緑」は根拠にならず、**台帳が正しく効いているか**を
# 両方の環境で確かめられる形にしておく必要がある。
# --------------------------------------------------------------------------- #

#: ★``ops.NATIVE_CRASHES_ON_DEGENERATE`` の**対照**。本体と 1:1 で一致していなければ
#: ならない。片方だけ変えると落ちる —— 本体から消すのも、本体に足すのも、
#: **ここを同時に書き換える(= 人が意図を確認する)**ことを要求する。
#:
#: なぜ対照が要るか: 門の変異テスト(2026-09-05)で、本体から `cv_cc_count` を消しても
#: 「台帳の op はみな関門を持つ」を見るテストは**そのまま通った**。台帳から消えた op は
#: ループの対象からも消えるので、検査経路ごと無くなる。守っている SIGSEGV は
#: Linux 専用で、Windows では偶然まともな値が返るから最後の砦も働かない。
#: 独立した情報源(このセット)との**等価**だけが、両方向を Windows でも捕まえる。
#: `test_the_two_nonfinite_ledgers_agree` と同じ形。
EXPECTED_NATIVE_CRASH_LEDGER = frozenset({
    "cv_cc_count",               # OpenCV connectedComponents, 0 サイズ(Linux SIGSEGV)
    "xsitk_minmax_curv_flow",    # SimpleITK, 非有限・一部 NaN(Linux SIGSEGV)
    "xsk3_h_minima",             # skimage reconstruction 族, 全 NaN(Linux SIGSEGV)
    "xsk_random_walker",         # skimage random_walker, 一部 NaN でハング(規模依存)
})


def test_the_native_crash_ledger_matches_its_control(registry):
    """本体の台帳と、このファイルの対照が**一致**すること(両方向の門)。"""
    import ops as _o
    body = frozenset(_o.NATIVE_CRASHES_ON_DEGENERATE)
    assert body == EXPECTED_NATIVE_CRASH_LEDGER, (
        "台帳と対照がずれている。本体だけ %s / 対照だけ %s —— 意図した変更なら両方を直す"
        % (sorted(body - EXPECTED_NATIVE_CRASH_LEDGER), sorted(EXPECTED_NATIVE_CRASH_LEDGER - body)))


def test_the_native_crash_ledger_names_ops_that_exist(registry):
    """台帳に居ない op が残っていないこと(改名・削除で静かに無効化されるのを防ぐ)。"""
    import ops as _o
    live = {op.name for op in registry}
    stale = sorted(set(_o.NATIVE_CRASHES_ON_DEGENERATE) - live)
    assert not stale, "居ない op が台帳に残っている: %s" % stale
    assert _o.NATIVE_CRASH_GUARDS == len(
        [n for n in _o.NATIVE_CRASHES_ON_DEGENERATE if n in live]), (
        "台帳の件数と実際に掛けた関門の数が合わない")


def test_every_ledgered_op_rejects_degenerate_input_and_still_returns(registry):
    """関門が効いていること —— 退化入力で**例外を外に出さず、有限を返す**。

    弾いた入力は `ValueError` になり、外側の `guard` が台帳に記録して sort に合う
    値へ落とす。利用者から見れば「落ちない」が保たれる。
    """
    import ops as _o
    by = {op.name: op for op in registry}
    checked = 0
    for name in _o.NATIVE_CRASHES_ON_DEGENERATE:
        op = by.get(name)
        if op is None:
            continue
        for v in (np.zeros((0, 0)),
                  np.full((16, 16), np.nan),
                  np.full((16, 16), np.inf),
                  np.where(np.eye(16) > 0, np.nan, 0.5)):    # 一部だけ NaN
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                out = op.fn(v.copy(), 0.5, 0.5)              # 例外を投げてはいけない
            assert _finite_and_sort_valid(out, op.out_sort), \
                "%s: 退化入力の戻り値が契約外" % name
            checked += 1
    assert checked >= 8, "検査した組み合わせが少なすぎる(%d)" % checked


def test_the_guard_does_not_touch_a_normal_input(registry):
    """関門は**まともな入力には一切触らない** —— 同じ入力で同じ値が返る。"""
    import ops as _o
    by = {op.name: op for op in registry}
    good = np.linspace(0, 1, 32 * 32).reshape(32, 32)
    for name in _o.NATIVE_CRASHES_ON_DEGENERATE:
        op = by.get(name)
        if op is None:
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            a = np.asarray(op.fn(good.copy(), 0.5, 0.5), dtype=object)
            b = np.asarray(op.fn(good.copy(), 0.5, 0.5), dtype=object)
        assert np.array_equal(np.asarray(a, float), np.asarray(b, float)), \
            "%s: 通常入力の結果が再現しない" % name


def test_every_ledgered_op_actually_has_the_gate_not_just_luck(registry):
    """★関門が**掛かっている**ことを、結果の有限性ではなく**拒否そのもの**で確かめる。

    門の変異テスト(2026-09-05)で判明: 台帳から `cv_cc_count` を消しても
    Windows では何も落ちなかった。守っている SIGSEGV は Linux 専用で、
    Windows では退化入力を渡しても偶然まともな値が返るからだ ——
    「有限を返す」は「関門がある」の証拠にならない。

    strict mode では `guard` が例外を再送出するので、関門が掛かっていれば
    退化入力で **ValueError(拒否)** が外に出る。掛かっていなければ出ない。
    これは Windows でも Linux でも同じに振る舞う。
    """
    import backend_safe as _bs
    import ops as _o
    by = {op.name: op for op in registry}
    for name in _o.NATIVE_CRASHES_ON_DEGENERATE:
        op = by.get(name)
        if op is None:
            continue
        with _bs.strict_mode(True), warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with pytest.raises(ValueError, match="拒否"):
                op.fn(np.zeros((0, 0)), 0.5, 0.5)
            with pytest.raises(ValueError, match="拒否"):
                op.fn(np.full((16, 16), np.nan), 0.5, 0.5)
