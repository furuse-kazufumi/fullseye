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


#: レジストリの**中身そのもの**に依存する検査が要求する backend 一式。
#:
#: 2026-09-05 実測: mahotas が無いだけで `xmh_bwperim` / `xmh_majority` が
#: レジストリから消え、op 名を直書きしたギャラリーと、レジストリから指紋を取る
#: docs の drift 検査が落ちた。**op 集合が環境で変わる**のに、不変条件の側が
#: 固定を仮定していた形。揃っていないなら skip、揃っている CI の py3.11 では実行。
FULL_REGISTRY_BACKENDS = ("torch", "kornia", "mahotas", "cv2.xfeatures2d")


def requires_full_registry() -> None:
    """レジストリの op 集合が**満杯**であることを要求する検査で呼ぶ。"""
    requires_backend(*FULL_REGISTRY_BACKENDS)


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


# --------------------------------------------------------------------------- #
# ★2026-09-14 追加。ここまで探針バンクは 6 sort しか無く、**901 op のうち 151 本
# (16.8 %)が契約ゲート 3 本(例外を投げない / 非有限を出さない / 決定的)を
# 一度も実行されていなかった** —— `PROBELESS_OPS_BUDGET = 151` というラチェットで
# 本数だけ凍結し、「本来の直しは BANKS を全 in_sort へ広げること」と自分で書いて
# あった。その本来の直しをここで入れる。
#
# 形の出どころは推測ではない: `backends_bridge._EMPTY_OF` が 12 sort すべての
# **正準の最小値**を宣言しており(そこが sort の定義そのもの)、`problems.py` の
# `_points_stack` / `_signal_stack` などが実データの作り方を持っている。
# 各バンクは既存の作法に合わせ、**普通の値・定数 0・定数 1・退化形**を混ぜる
# (定数と退化形が「走った」と「意味のある出力」を分ける
#  —— [[feedback_ran_is_not_meaningful_output]])。
# --------------------------------------------------------------------------- #
def points_bank(m: int = 96) -> dict[str, np.ndarray]:
    """(N, 3) 点群。球面(法線が全方向)+ 平面(法線が一定)= 曲率の異なる 2 領域。"""
    rng = _rng()
    half = m // 2
    v = rng.standard_normal((half, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True).clip(1e-12)
    sphere = v * 3.0 + 5.0
    plane = np.column_stack([rng.uniform(0, 10, m - half),
                             rng.uniform(0, 10, m - half),
                             np.zeros(m - half)])
    # ★`normal` は **kNN グラフが連結**でなければならない。最初は球面と平面を
    #   別々に置いたが、k=8 では 2 つの塊が繋がらず `tb_geodesic_distances` が
    #   68 個の `inf` を返した —— これは op の欠陥ではなく、docstring が
    #   「source と繋がっていない連結成分の点は inf」と**明記している正しい答え**。
    #   非連結は探針の意図として別名(`two_clusters`)で持ち、`normal` は繋げる。
    #   **op の正解を「非有限を出すな」のゲートで殴らない。**
    bridge = np.column_stack([np.linspace(0, 5, 12), np.linspace(0, 5, 12),
                              np.linspace(0, 3, 12)])
    return {
        "normal": np.vstack([sphere, plane, bridge]),   # 2 領域を橋でつなぐ = 連結
        "plane_only": plane,                       # 法線が一定 = 曲率ゼロ
        "two_clusters": np.vstack([plane, plane + 500.0]),   # わざと非連結にする探針
        "coincident": np.zeros((8, 3)),            # 全点が同じ場所(距離が全部 0)
        "single": np.zeros((1, 3)),                # 近傍が作れない
        "collinear": np.column_stack([np.arange(8.0), np.zeros(8), np.zeros(8)]),
    }


def signal_bank(m: int = 128) -> dict[str, np.ndarray]:
    """1-D 波形。減衰振動 + 高調波。"""
    t = np.linspace(0, 8 * np.pi, m)
    return {
        "normal": np.sin(t) * np.exp(-t / (6 * np.pi)) + 0.3 * np.sin(3.1 * t),
        "const0": np.zeros(m),
        "const1": np.ones(m),
        "impulse": np.eye(1, m, m // 2).ravel(),
        "tiny2": np.array([0.0, 1.0]),             # 差分・平滑の下限
    }


def counts_bank(m: int = 64) -> dict[str, np.ndarray]:
    """光子計数ヒストグラム(非負整数)。背景 + ピーク。"""
    k = np.arange(m)
    peak = np.exp(-((k - m * 0.4) ** 2) / (2 * 3.0 ** 2))
    return {
        "normal": (40 * peak + 5).astype(np.int64),
        "const0": np.zeros(m, np.int64),
        "flat": np.full(m, 7, np.int64),           # 背景だけ(ピークが無い)
        "tiny2": np.array([0, 3], np.int64),
    }


def matrix_bank(n: int = 6) -> dict[str, np.ndarray]:
    """一般の 2-D 数値行列。**特異・不良条件を必ず入れる**(擬似逆行列や条件数の
    op は、そこで初めて壊れるか壊れないかが分かれる)。"""
    rng = _rng()
    a = rng.standard_normal((n, n))
    ill = np.diag(np.logspace(0, -12, n))           # 条件数 1e12(有限だが極端)
    # ★**厳密に特異な行列は置かない。** 最初 `np.ones((n,n))`(階数 1)を入れたら
    #   `tb_mat_cond` が `inf` を返して「非有限を出さない」ゲートが落ちた —— が、
    #   特異行列の条件数が無限大なのは**数学的に正しい答え**であって欠陥ではない。
    #   ゲートに免除機構は無いので、**正解が非有限になる入力を渡さない**のが筋
    #   (ゲートを緩めると、本当に壊れている非有限まで通ってしまう)。
    #   「特異に近い」は `ill_conditioned` が既に担っている。
    #   同じ理由で **全ゼロ行列も置けない**(ゼロ行列は特異なので条件数は `inf`)。
    #   定数入力の探針としての役目は `near_zero`(極小だが可逆)が引き継ぐ。
    return {
        "normal": a,
        "ill_conditioned": ill,
        "near_zero": np.eye(n) * 1e-12,             # 定数に近いが可逆(条件数 1)
        "tiny2": np.array([[1.0, 2.0], [3.0, 4.0]]),
        "tall": rng.standard_normal((n * 2, n)),    # 正方でない
    }


def keypoints_bank() -> dict[str, np.ndarray]:
    """(N, 2) 像面上の点。**空**が正準の最小値(`_EMPTY_OF` が (0,2))。"""
    return {
        "normal": np.array([[3.0, 4.0], [10.0, 12.0], [20.0, 7.0], [31.0, 31.0]]),
        "empty": np.zeros((0, 2)),
        "single": np.array([[5.0, 5.0]]),
        "coincident": np.zeros((4, 2)),
    }


def rgbimage_bank(n: int = 32) -> dict[str, np.ndarray]:
    """(H, W, 3) の色画像。`color_bank` と同じ形だが、鏡面分離などの op が
    見るのは**ハイライトの有無**なので、飽和した明点を混ぜる。"""
    g = image_bank(n)["normal"]
    base = np.clip(np.stack([g, 0.7 * g + 0.1, 1 - g], -1), 0, 1)
    hot = base.copy()
    hot[n // 3:n // 3 + 4, n // 3:n // 3 + 4, :] = 1.0      # 飽和ハイライト
    return {
        "normal": base,
        "highlight": hot,
        "const0": np.zeros((n, n, 3)),
        "const1": np.ones((n, n, 3)),
        "grey": np.repeat(g[:, :, None], 3, axis=2),        # 彩度ゼロ
    }


BANKS = {
    "image": image_bank,
    "region": region_bank,
    "color": color_bank,
    "contour": contour_bank,
    "volume": volume_bank,
    "any": image_bank,
    # ★新規(2026-09-14): ここまで探針が無く、契約ゲートを一度も通っていなかった
    # 5 sort = 101 op。残る 6 sort(video / qimage / cimage / lightfield /
    # beatcube = 50 op)は形が複素・4-D で退化形の設計に手間が要るため、
    # **一度に全部入れて切り分け不能にしない**よう次の段で足す。
    "points": points_bank,          # 56 op
    "signal": signal_bank,          # 27 op
    "counts": counts_bank,          #  8 op
    "matrix": matrix_bank,          #  4 op
    "keypoints": keypoints_bank,    #  2 op
    "rgbimage": rgbimage_bank,      #  6 op
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
