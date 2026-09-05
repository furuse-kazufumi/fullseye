"""Shared fixtures + a per-sort input battery for imgevolve's test suite.

The library had no automated tests before this suite. These tests encode the
*contracts* every operator must honour (determinism, finiteness, declared sort,
value domain) plus correctness anchors and evolution-honesty invariants.
"""
from __future__ import annotations

import os
import sys
import warnings

import numpy as np
import pytest

# imgevolve is a flat project: the package modules live one directory up.
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Backends emit library deprecation/boundary warnings that are not the unit
# under test; silence them so a failing assertion is the only signal.
warnings.filterwarnings("ignore")


# --------------------------------------------------------------------------- #
# ★Studio の設定を**セッション全体で**使い捨て ini へ逃がす。                  #
# --------------------------------------------------------------------------- #
# `QSettings("Fullseye", "Studio")` はネイティブ格納庫(Windows ならレジストリ
# HKCU\Software\Fullseye\Studio)に書く。隔離を**個々のテストファイル**に置いて
# いたので、置き忘れたファイルから利用者の実レジストリが汚れていた。
#
# 2026-09-05 の監査で実害を確認: `recent_files` 10 件のうち 8 件が pytest の
# 一時パス、`system\operator_timeout_ms` などの実値も残っていた。
# (隔離は 3 ファイル中 2 つにしかなく、`test_studio_params.py` が素通しだった。)
#
# 個別に足すのをやめ、**セッション autouse でここに 1 つだけ**置く。
# 環境変数は `studio._settings()` が見る唯一の入口なので、これで全テストが覆われる。
_STUDIO_SETTINGS_ENV = "FULLSEYE_STUDIO_SETTINGS"


# --------------------------------------------------------------------------- #
# ★optional backend が要るテストの宣言。                                       #
# --------------------------------------------------------------------------- #
# CI の注記には長らく「torch/kornia は入れない(**対応テストは graceful skip**)」と
# 書いてあったが、2026-09-05 の実測でそれは**事実ではなかった** —— 対象テストは
# skip せず `ImportError: this operator needs the optional 'torch' backend` で
# 落ちていた(14 件)。注記だけがあって、それを機械で確かめる仕組みが無かった。
#
# ここで宣言を 1 つの入口にまとめる。狙いは **両方向**:
#   * backend が無い環境 → skip(注記を事実にする)
#   * backend が**在るはず**の環境 → skip を許さず失敗させる
#     (`FULLSEYE_REQUIRE_OPTIONAL=1`。CI の py3.11 ジョブがこれを立てる)
# 片方向だけだと、本物の回帰が静かに skip へ化ける
# (`feedback_failsoft_hides_permanently_dead_ops` と同じ形)。
_REQUIRE_OPTIONAL = os.environ.get("FULLSEYE_REQUIRE_OPTIONAL", "") not in ("", "0")


def _have_backend(name: str) -> bool:
    """``"torch"`` のようなモジュール名、``"cv2.xfeatures2d"`` のような属性も見る。"""
    import importlib
    import importlib.util
    root, _, attr = name.partition(".")
    try:
        if importlib.util.find_spec(root) is None:
            return False
    except (ImportError, ValueError):
        return False
    if not attr:
        return True
    try:
        return hasattr(importlib.import_module(root), attr)
    except Exception:                                            # noqa: BLE001
        return False


def requires_backend(*names: str) -> None:
    """optional backend を要求する。無ければ skip、完全環境なら失敗。

    テスト本体の**先頭**で呼ぶ。grep できる形にしてあるのは、
    「どのテストが何に依存しているか」を人が数えられるようにするため。
    """
    missing = [n for n in names if not _have_backend(n)]
    if not missing:
        return
    what = ", ".join(missing)
    if _REQUIRE_OPTIONAL:
        raise AssertionError(
            "optional backend が無い: %s —— しかし FULLSEYE_REQUIRE_OPTIONAL が立って "
            "いる(この環境は全 backend を持っている前提)。**不変条件が実行されて "
            "いない**。CI の install 行か、この宣言のどちらかが間違っている。" % what)
    pytest.skip("optional backend not installed: %s" % what)


@pytest.fixture(scope="session", autouse=True)
def _isolate_studio_settings(tmp_path_factory):
    """テストが利用者のレジストリ / plist / 設定 ini に触れないようにする。"""
    prev = os.environ.get(_STUDIO_SETTINGS_ENV)
    ini = tmp_path_factory.mktemp("studio_settings") / "studio.ini"
    os.environ[_STUDIO_SETTINGS_ENV] = str(ini)
    try:
        yield ini
    finally:
        if prev is None:
            os.environ.pop(_STUDIO_SETTINGS_ENV, None)
        else:
            os.environ[_STUDIO_SETTINGS_ENV] = prev


# --------------------------------------------------------------------------- #
# Deterministic input battery, one bank per sort.                             #
# --------------------------------------------------------------------------- #
def _rng():
    return np.random.default_rng(20260812)


def image_bank(n: int = 48) -> dict[str, np.ndarray]:
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    grad = xx / (n - 1)
    disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.4) ** 2) < (n * 0.18) ** 2
    checker = ((xx.astype(int) // 6 + yy.astype(int) // 6) % 2) * 0.15
    normal = np.clip(0.35 * grad + 0.45 * disk + checker + 0.03 * _rng().standard_normal((n, n)), 0, 1)
    single = np.zeros((n, n)); single[n // 2, n // 2] = 1.0
    return {
        "normal": normal,
        "const0": np.zeros((n, n)),
        "const1": np.ones((n, n)),
        "const_mid": np.full((n, n), 0.42),
        "tiny4": (np.arange(16, dtype=np.float64) / 15.0).reshape(4, 4),
        "single_bright": single,
    }


def region_bank(n: int = 48) -> dict[str, np.ndarray]:
    yy, xx = np.mgrid[0:n, 0:n]
    disk = (((yy - n // 2) ** 2 + (xx - n // 2) ** 2) < (n * 0.25) ** 2).astype(np.float64)
    single = np.zeros((n, n)); single[n // 2, n // 2] = 1.0
    return {
        "disk": disk,
        "all0": np.zeros((n, n)),
        "all1": np.ones((n, n)),
        "single_px": single,
        "tiny4": np.array([[1, 0, 0, 1], [0, 1, 1, 0], [0, 0, 1, 1], [1, 1, 0, 0]], np.float64),
    }


def color_bank(n: int = 48) -> dict[str, np.ndarray]:
    g = image_bank(n)["normal"]
    return {
        "normal": np.clip(np.stack([g, 0.7 * g + 0.1, 1 - g], -1), 0, 1),
        "const0": np.zeros((n, n, 3)),
        "const1": np.ones((n, n, 3)),
        "rand": _rng().random((n, n, 3)),
    }


def contour_bank() -> dict[str, dict]:
    sq = np.array([[6.0, 6.0], [6.0, 20.0], [20.0, 20.0], [20.0, 6.0], [6.0, 6.0]])
    return {
        "square": {"shape": (32, 32), "cs": [sq]},
        "empty": {"shape": (32, 32), "cs": []},
        "single_pt": {"shape": (32, 32), "cs": [np.array([[8.0, 8.0]])]},
        "two_pt": {"shape": (32, 32), "cs": [np.array([[2.0, 2.0], [10.0, 10.0]])]},
    }


def volume_bank() -> dict[str, np.ndarray]:
    zz, vy, vx = np.mgrid[0:8, 0:24, 0:24]
    return {
        "normal": np.clip(0.5 + 0.3 * np.sin(vx / 3.0) * np.cos(vy / 4.0) * (zz / 8.0), 0, 1),
        "const0": np.zeros((8, 24, 24)),
        "const1": np.ones((8, 24, 24)),
    }


BANKS = {
    "image": image_bank,
    "region": region_bank,
    "color": color_bank,
    "contour": contour_bank,
    "volume": volume_bank,
    "any": image_bank,
}

KNOBS = [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0), (0.15, 0.85)]


def copy_input(x):
    if isinstance(x, dict):
        return {"shape": x["shape"], "cs": [c.copy() for c in x["cs"]]}
    return np.array(x, copy=True)


def inputs_for(in_sort: str):
    """Yield (name, value) edge inputs matching a sort. Unknown sort -> empty."""
    bank = BANKS.get(in_sort)
    if bank is None:
        return
    for name, val in bank().items():
        yield name, val


@pytest.fixture(scope="session")
def registry():
    import ops
    return ops
