# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""**何も写っていないフレーム**が、明るさを少し変えただけで別物に化けないことを検査する。

2026-09-16、codex に書かせた第 2 実装が `auto_threshold` で `constant_half` と
`single_pixel` の 2 つだけ食い違った(差はきっかり 1.0 = 二値出力の全反転)。他 11 種の
構造探針は厳密一致だったので争点が 1 点に絞れ、そこを実測して **4 つの不具合**が出た:

* `dyn_threshold` / `adaptive_gauss_thresh` / `local_threshold` ——
  ``v > filter(v) + offset`` は既定(offset=0)では「1 ULP でも明るければ前景」を
  意味する。一様な面でも ``uniform_filter`` の積算順序で結果が最下位 1 ビット下に
  丸まることがあり、そのとき**面の全画素が前景**になった(c=0.05 で 576/576、
  c=0.06 で 0/576)。
* `std_filter` / `deviation_image` / `texture_laws` ——
  ``E[x^2]-E[x]^2`` の桁落ちで一様画像にも 1e-15 級の偽分散が残り、``sqrt`` が
  それを 3e-8 へ 8 桁持ち上げて ``_norm`` の床を越え、**全画素 1.0**(最大テクスチャ)
  になった。同じ不具合は GPU 経路 ``accel.py`` では既に直っていて、**CPU 経路
  ——つまり既定——だけが直っていなかった**。
* `kirsch_dir` / `robinson_dir` / `frei_dir` —— 一様面ではコンパス応答が厳密に 0 に
  なるはずだが 2e-15 級の屑が残り、``argmax`` / ``arctan2`` が**その屑の大小で方向を
  決めていた**。明るさを 0.49 から 0.51 に変えるだけで方向マップが別物になる。
* `xkor_laplacian` / `xkor_dog` —— kornia は float32 なので一様画像にゼロ和カーネルを
  当てても 1e-7 級の屑が残る。``_norm`` の床が ``1e-8`` = **屑より下**にあったため、
  屑が床を跨ぐたびに出力が 0 と全面 1.0 の間で反転した。

**なぜ門が要るか。** どれも「たまに出る」形の壊れ方である。明るさ 0.50 では正しく、
0.51 で全面誤検出になる —— 検査の現場では**再現しない誤報**として現れ、原因に辿り
着けない。数値テストは通ってしまう(平均や相関を見るテストは一様入力を使わない)ので、
**一様入力を明示的に掃く門**でしか守れない。

門は壊して確かめてある: 許容幅を 0 にすると、直す前の 4 op すべてがここで落ちる。
"""
from __future__ import annotations

import numpy as np
import pytest

import fullseye as fs

#: 一様入力を掃く刻み。不具合はどれも「隣り合う明るさで答えが反転する」形だったので、
#: 粗い刻みでは素通りする(0.50 は正しく 0.51 が壊れていた)。
LEVELS = [round(0.01 * i, 2) for i in range(101)]

#: **一様な面に何も無いと答えるべき op**。適応的しきい値は「周囲より明るい画素」を
#: 探すので一様面では空、局所分散・ゼロ和カーネルは一様面で数学的に厳密に 0 になる。
MUST_BE_EMPTY = [
    "dyn_threshold", "adaptive_gauss_thresh", "local_threshold",
    "std_filter", "deviation_image", "texture_laws",
    "xkor_laplacian", "xkor_dog", "log",
    # **書かれている動作を実装が達成できていなかった 2 本**。`hx_lowlands` の docstring は
    # 「画像全体が平坦だと ``v < mean`` を満たす画素が無く空になる」と明記していたが、
    # 定数配列の ``mean()`` は積算の丸めで 1 ULP 大きくなることがあり、そのとき
    # **全画素が窪地**になった(一様 0.06 で 576/576、一様 0.04 では 0/576)。
    "hx_lowlands", "hx_char_threshold",
]

#: **零和作用素**(二階微分)は、画像全体の明るさを一律に足しても答えを変えてはいけない。
#: 直したのはこの性質のほうで、空フレームはその一番極端な場合にすぎない ——
#: `scipy.ndimage.gaussian_laplace` はガウシアンを 4σ で打ち切るので離散カーネルの
#: 総和が 0 にならず、一様面に `-1.92e-4 x c` の応答が出ていた(丸め屑ではなく c に
#: 比例する系統的な偏り)。実測 2026-09-16: `log` は明るさを +0.2 しただけで
#: 最大 2.9e-3 変わり、一様画像では**全画素 1.0** を返していた。
DC_INVARIANT = ["log", "laplace_of_gauss", "laplace"]

#: 屑として許す上限。実信号(16-bit の量子化幅 1.5e-5)よりはるかに下、
#: float32 の丸め屑(1e-7)よりわずかに上。
DUST = 1e-6


def _apply(op, img):
    return np.asarray(fs.apply(img.copy(), op, a=0.5, b=0.5), np.float64)


@pytest.mark.parametrize("op", MUST_BE_EMPTY)
def test_a_uniform_frame_never_becomes_a_full_frame_detection(op):
    """一様な面を入れて、**どの明るさでも**出力が屑以下であること。

    直す前はここで落ちた —— 例えば `std_filter` は一様 0.51 で全画素 1.0 を返した。
    """
    try:
        _apply(op, np.full((24, 24), 0.5))
    except Exception as e:                      # 依存が無い環境(kornia 等)は飛ばす
        pytest.skip(f"{op} を呼べない: {type(e).__name__}")
    worst, worst_c = 0.0, None
    for c in LEVELS:
        out = _apply(op, np.full((24, 24), float(c)))
        assert np.isfinite(out).all(), f"{op}: 一様 {c} で非有限が出た"
        m = float(np.max(np.abs(out)))
        if m > worst:
            worst, worst_c = m, c
    assert worst <= DUST, (
        f"{op}: 一様な面なのに最大 {worst:.3g} を返した(明るさ {worst_c})。"
        f"空フレームが全面検出に化けている")


@pytest.mark.parametrize("op", MUST_BE_EMPTY)
def test_the_fix_did_not_make_the_op_blind(op):
    """**陰性対照**: 屑を消したせいで本物の信号まで消えていないこと。

    「一様面で 0 を返す」だけなら ``return zeros`` で満たせてしまう。片方だけの門は
    op を殺したまま緑になる。
    """
    try:
        _apply(op, np.full((24, 24), 0.5))
    except Exception as e:
        pytest.skip(f"{op} を呼べない: {type(e).__name__}")
    # **明暗の両方**を置く。明るい塊しか無い画像だと、暗い側を取る op
    # (`hx_char_threshold` は「暗い文字」を取る)が何も返さず、直したせいで盲目に
    # なったのか元からそうなのか区別できない —— 実際この門はそれで一度落ちた。
    img = np.full((48, 48), 0.50)
    img[8:20, 8:20] = 0.85                      # はっきりした明るい塊
    img[28:40, 28:40] = 0.12                    # はっきりした暗い塊
    out = _apply(op, img)
    assert float(np.max(out)) > 0.1, (
        f"{op}: はっきりした塊があるのに最大 {float(np.max(out)):.3g} —— "
        f"屑を消すつもりで信号まで消している")


def test_a_uniform_frame_stays_stable_when_brightness_shifts_slightly():
    """隣り合う明るさで答えが**反転しない**こと(壊れ方の本体はこれ)。

    絶対値でなく「隣との差」を見るので、op が一様面で何を返すかの規約には踏み込まない
    —— 反転だけを禁じる。固定しきい値の op(0.5 で切る)はここに入れない。
    """
    #: 方向マップは一様面で「勾配なし」の既定値(argmax 族は 0、arctan2 族は 0.5)を
    #: 返すべきで、**明るさを変えただけで別の方向に飛んではいけない**。直す前は
    #: `kirsch_dir` が 0.4286 -> 0 -> 0.2857 と動いた(同点を丸め屑が破っていた)。
    ops = ["dyn_threshold", "std_filter", "deviation_image",
           "kirsch_dir", "robinson_dir", "frei_dir"]
    for op in ops:
        prev = None
        for c in LEVELS:
            out = _apply(op, np.full((24, 24), float(c)))
            v = float(np.max(np.abs(out)))
            if prev is not None:
                assert abs(v - prev) <= DUST, (
                    f"{op}: 一様面の出力が明るさ {c} で {prev:.3g} -> {v:.3g} と跳んだ。"
                    f"再現しない誤報になる")
            prev = v


def test_the_gate_would_have_caught_the_old_formulas():
    """**門を壊して確かめる。** 直す前の式をここで再現し、この門の判定基準
    (``DUST``)が実際にそれを落とすことを示す。

    「新しいコードで緑」だけでは、門が何かを守っている証拠にならない —— 常に真を
    返す門も緑になる。落とせるものを 1 つ持っておく。
    """
    from scipy import ndimage

    # (1) 旧 `_std_filter`: E[x^2]-E[x]^2 を平均を引かずに計算 -> sqrt が屑を増幅
    caught_std = False
    for c in LEVELS:
        v = np.full((24, 24), float(c))
        m = ndimage.uniform_filter(v, 7)
        m2 = ndimage.uniform_filter(v * v, 7)
        r = np.sqrt(np.maximum(m2 - m * m, 0.0))
        mx = float(np.max(np.abs(r)))
        old = r / mx if mx > 1e-8 else r         # 旧 `_norm`(床 1e-8)
        if float(np.max(np.abs(old))) > DUST:
            caught_std = True
            break
    assert caught_std, "旧 std の式を再現できていない(門が何も守っていない恐れ)"

    # (2) 旧 `_dyn_threshold`: v > filter(v) + 0 -> 1 ULP の丸めで全面前景
    caught_dyn = False
    for c in LEVELS:
        v = np.full((24, 24), float(c))
        old = (v > ndimage.uniform_filter(v, 7)).astype(np.float64)
        if float(np.max(old)) > DUST:
            caught_dyn = True
            break
    assert caught_dyn, "旧 dyn_threshold の式を再現できていない"


@pytest.mark.parametrize("op", DC_INVARIANT)
def test_a_second_derivative_ignores_the_overall_brightness(op):
    """**零和作用素は直流に応じてはいけない。** 明るさを一律に足して答えが変わらないこと。

    空フレームの門(上)だけでは足りない —— 一様面で 0 を返しても、実画像では明るさに
    応じた偏りが残りうる。ゼロ交差の位置までずれるので、これは検出結果そのものを歪める。
    """
    rng = np.random.default_rng(5)
    x = np.clip(rng.random((32, 32)) * 0.3 + 0.15, 0, 1)
    try:
        base = _apply(op, x)
    except Exception as e:
        pytest.skip(f"{op} を呼べない: {type(e).__name__}")
    for k in (0.1, 0.2, 0.5):
        shifted = _apply(op, x + k)
        d = float(np.max(np.abs(shifted - base)))
        assert d <= 1e-9, (
            f"{op}: 明るさを一律 +{k} しただけで答えが最大 {d:.3g} 変わった。"
            f"二階微分は直流に応じてはいけない(離散カーネルの総和が 0 でない疑い)")
