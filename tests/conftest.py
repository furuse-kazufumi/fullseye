"""Shared fixtures + a per-sort input battery for imgevolve's test suite.

The library had no automated tests before this suite. These tests encode the
*contracts* every operator must honour (determinism, finiteness, declared sort,
value domain) plus correctness anchors and evolution-honesty invariants.
"""
from __future__ import annotations

import contextlib
import json
import os
import sys
import warnings
from pathlib import Path

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

# conftest の import 時点なら、まだ pytest 用の環境変数で利用者の場所を差し
# 替えていない。この控えは終了時の実物比較専用で、試験中に os.environ が変わって
# も本物の Start Menu / Desktop / %LOCALAPPDATA% を見失わない。
# Capture the user's paths before the session fixture redirects the process.
# These are used only for read-only before/after checks of the real locations.
_REAL_ENV = {name: os.environ.get(name) for name in
             ("APPDATA", "LOCALAPPDATA", "USERPROFILE", "PUBLIC", "ProgramData")}


# --------------------------------------------------------------------------- #
# ★利用者の Windows 登録をセッション全体で一時フォルダへ逃がす。                 #
# --------------------------------------------------------------------------- #
# `APPDATA` だけを差し替えても、SHGetKnownFolderPath / GetFolderPath は
# OneDrive 等の実 Desktop / Start Menu を返す。また、子プロセスは conftest の
# monkeypatch を知らない。そこで、すべてのテストと子プロセスに渡る環境変数を
# 1 箇所で設定し、Python と PowerShell の既知フォルダー取得にも明示的な試験用
# 上書きを渡す。HKCU の Apps & features は test-only のキーに切り替える。
#
# APPDATA alone is insufficient because Windows known-folder APIs ignore it.
# This one session fixture redirects both the environment and the Python /
# PowerShell known-folder shims inherited by every child process.  The actual
# Apps & features key is never named by product code during a test session.
_STUDIO_SETTINGS_ENV = "FULLSEYE_STUDIO_SETTINGS"
_INSTALLER_ISOLATION_ENV = (
    "APPDATA", "LOCALAPPDATA", "USERPROFILE", "FULLSEYE_LEDGER",
    "FULLSEYE_CACHE_DIR", _STUDIO_SETTINGS_ENV, "FULLSEYE_TEST_ISOLATION",
    "FULLSEYE_TEST_DESKTOP", "FULLSEYE_TEST_PROGRAMS",
    "FULLSEYE_TEST_LOCALAPPDATA", "FULLSEYE_ISOLATED_UNINSTALL_KEY",
)


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
FULL_REGISTRY_BACKENDS = ("torch", "kornia", "mahotas", "pywt", "cv2.xfeatures2d")


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


@pytest.fixture(autouse=True)
def _no_leftover_value_helper_threads():
    """変数の欄・ウォッチが利用者のコード(``__repr__``・式)のために起こしたスレッドが、時間切れの後も残っている間は、
    新しいスレッドを起こさない(``studio_pyedit_values.stray_threads``。2026-11-13 第 2 回レビュー R5)。わざと止まらない
    式を使う試験の残りが、同じワーカーの次の試験を「表示していません」にしないよう、試験の前に終わるのを待つ。"""
    mod = sys.modules.get("studio_pyedit_values")
    if mod is not None and hasattr(mod, "stray_threads"):
        import time
        end = time.monotonic() + 10.0
        while mod.stray_threads() and time.monotonic() < end:
            time.sleep(0.02)
    yield


@pytest.fixture(scope="session", autouse=True)
def _isolate_windows_installer_state(tmp_path_factory):
    """登録先を一時フォルダへ替え、本物の既知フォルダーと HKCU Uninstall を隔離する。"""
    old = {name: os.environ.get(name) for name in _INSTALLER_ISOLATION_ENV}
    root = tmp_path_factory.mktemp("windows_installer_isolation")
    ini = root / "settings" / "studio.ini"
    ledger = root / "local" / "Fullseye" / "setup" / "install_ledger.json"
    os.environ[_STUDIO_SETTINGS_ENV] = str(ini)
    os.environ["FULLSEYE_LEDGER"] = str(ledger)
    os.environ["FULLSEYE_CACHE_DIR"] = str(root / "local" / "fullseye")
    previous_uninstall_key = None
    if sys.platform == "win32":
        appdata = root / "roaming"
        local = root / "local"
        profile = root / "userprofile"
        desktop = profile / "Desktop"
        programs = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        for path in (appdata, local, profile, desktop, programs):
            path.mkdir(parents=True, exist_ok=True)
        isolated_key = r"Software\FullseyeTest\pytest_session"
        os.environ.update({
            "APPDATA": str(appdata),
            "LOCALAPPDATA": str(local),
            "USERPROFILE": str(profile),
            "FULLSEYE_TEST_ISOLATION": "1",
            "FULLSEYE_TEST_DESKTOP": str(desktop),
            "FULLSEYE_TEST_PROGRAMS": str(programs),
            "FULLSEYE_TEST_LOCALAPPDATA": str(local),
            "FULLSEYE_ISOLATED_UNINSTALL_KEY": isolated_key,
        })
        # 同一プロセスで collection 済みのモジュールにも反映する。子プロセスは
        # 上の環境変数を読んで同じ値を module import 時に選ぶ。
        from fullseye import shortcuts
        previous_uninstall_key = shortcuts.UNINSTALL_KEY
        shortcuts.UNINSTALL_KEY = isolated_key
    try:
        yield root
    finally:
        if previous_uninstall_key is not None:
            from fullseye import shortcuts
            shortcuts.UNINSTALL_KEY = previous_uninstall_key
        for name, value in old.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        drop_fullseye_test_regkey()


def drop_fullseye_test_regkey():
    """試験用レジストリキー HKCU\\Software\\FullseyeTest を、子キーごと消す(Windows 以外では何もしない)。

    テストの後始末が親キーを残すと、空の Software\\FullseyeTest が利用者の実レジストリに居座る(2026-11-12 のレビューで実測)。
    この名前空間はテスト専用(本番コードは許さない)なので、残っていれば全部消してよい。"""
    if sys.platform != "win32":
        return
    import winreg

    def rec(parent, name):
        try:
            k = winreg.OpenKey(parent, name, 0, winreg.KEY_ALL_ACCESS)
        except OSError:
            return
        with k:
            while True:
                try:
                    sub = winreg.EnumKey(k, 0)
                except OSError:
                    break
                rec(k, sub)
        try:
            winreg.DeleteKey(parent, name)
        except OSError:
            pass
    rec(winreg.HKEY_CURRENT_USER, r"Software\FullseyeTest")


# --------------------------------------------------------------------------- #
# ★本物の Fullseye の登録(デスクトップ・スタートメニュー・HKCU の Uninstall・setup フォルダ)を試験が触らないことの見張り #
# --------------------------------------------------------------------------- #
# 2026-11-12(3 回目の独立レビュー): インストーラの試験(.cmd 経由で uninstall を呼ぶ物)が、環境変数を一時フォルダへ向けても
# デスクトップだけは SHGetKnownFolderPath で**本物**を引き、本物の ``Fullseye Studio.lnk`` と ``Uninstall\\Fullseye`` を消す
# 対象に入れていた(実際に、利用者のデスクトップの ``Fullseye Studio.lnk`` が消えた)。個々の試験の注意では防げないので、
# 試験群を回す前後で本物の一覧を取り、**差があれば失敗**させる(Windows だけ。fullseye は import しない)。
_FS_FILE_NAMES = {"fullseye studio.lnk", "fullseye-uninstall.cmd", "fullseye.ico", "fullseye-studio.desktop",
                  "fullseye-auto-shortcuts.json"}


def real_install_snapshot(env: dict | None = None) -> dict:
    """Fullseye 登録の一覧を読むだけで取る。``env=None`` は必ず利用者の実物を読む。"""
    snap: dict = {}
    if sys.platform != "win32":
        return snap
    import winreg
    e = _REAL_ENV if env is None else env

    def entry(p):
        try:
            st = os.stat(p)
            return (p, st.st_size, st.st_mtime_ns)
        except OSError:
            return (p, None, None)

    desk = set()
    if env is None:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as k:
                desk.add(winreg.QueryValueEx(k, "Desktop")[0])
        except OSError:
            pass
    for name, sub in (("USERPROFILE", "Desktop"), ("PUBLIC", "Desktop")):
        if e.get(name):
            desk.add(os.path.join(e[name], sub))
    out = []
    for d in sorted(desk):
        try:
            with os.scandir(d) as it:
                out += [entry(e.path) for e in it if e.name.lower() in _FS_FILE_NAMES]
        except OSError:
            pass
    snap["desktop"] = sorted(out)
    menus = []
    for base in (e.get("APPDATA"), e.get("ProgramData")):
        if not base:
            continue
        root = os.path.join(base, "Microsoft", "Windows", "Start Menu", "Programs")
        for dp, dn, fn in os.walk(root):
            menus += [entry(os.path.join(dp, n)) for n in fn + dn if n.lower() in _FS_FILE_NAMES or n.lower() == "fullseye"]
    snap["start_menu"] = sorted(menus)
    keys = []
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall") as u:
            i = 0
            while True:
                try:
                    name = winreg.EnumKey(u, i)
                except OSError:
                    break
                i += 1
                vals = {}
                try:
                    with winreg.OpenKey(u, name) as k:
                        for v in ("DisplayName", "UninstallString"):
                            try:
                                vals[v] = str(winreg.QueryValueEx(k, v)[0])
                            except OSError:
                                pass
                except OSError:
                    pass
                if "fullseye" in name.lower() or "fullseye" in vals.get("DisplayName", "").lower():
                    keys.append((name, vals.get("DisplayName"), vals.get("UninstallString")))
    except OSError:
        pass
    snap["uninstall_keys"] = sorted(keys, key=str)
    local = e.get("LOCALAPPDATA")
    setup = None                            # None = フォルダが無い / [] = 在るが空(「空で新しく作られた」を検出するため区別する)
    if local:
        d = os.path.join(local, "Fullseye", "setup")
        try:
            with os.scandir(d) as it:
                setup = sorted(entry(e.path) for e in it)
        except OSError:
            setup = None
    snap["setup_folder"] = setup
    return snap


def snapshot_diff(before: dict, after: dict) -> list:
    """2 つの一覧の違いを文の一覧にする(同じなら空)。"""
    out = []
    for k in sorted(set(before) | set(after)):
        b, a = before.get(k), after.get(k)
        if b != a:
            if (b is None) != (a is None):
                out.append("%s: %s -> %s" % (k, "absent" if b is None else "present", "absent" if a is None else "present"))
                continue
            sb, sa = set(map(str, b or [])), set(map(str, a or []))
            out.append("%s: removed=%s added=%s" % (k, sorted(sb - sa), sorted(sa - sb)))
    return out


@pytest.fixture(scope="session", autouse=True)
def _real_fullseye_registration_is_untouched():
    before = real_install_snapshot()
    yield
    diff = snapshot_diff(before, real_install_snapshot())
    if diff:
        pytest.fail("the test run changed the REAL Fullseye registration (Desktop / Start menu / HKCU Uninstall / setup folder): "
                    + " | ".join(diff), pytrace=False)


@pytest.fixture(autouse=True)
def _real_fullseye_registration_is_unchanged_after_each_test(request):
    """本物が変われば、その直後の nodeid を添えて失敗させる。"""
    before = real_install_snapshot()
    yield
    diff = snapshot_diff(before, real_install_snapshot())
    if diff:
        pytest.fail("the test changed the REAL Fullseye registration after %s (Desktop / Start menu / "
                    "HKCU Uninstall / setup folder): %s" % (request.node.nodeid, " | ".join(diff)), pytrace=False)


#: api の遮断器(プロセスで 1 つの集合)。開けたまま残すと、同じワーカーで後に走るテストの
#: GPU / 速い双子の経路が黙って閉じる(1.0 前の修正 2026-11-05 t8-flake: T6 が median_image で落ちた)。
_API_BREAKERS = ("_GPU_OPEN", "_FAST_OPEN")


@contextlib.contextmanager
def _api_breakers_restored():
    """抜けるときに api の遮断器を入ったときの中身へ戻す(api を読んでいなければ何もしない)。"""
    api = sys.modules.get("api")
    saved = {k: set(getattr(api, k)) for k in _API_BREAKERS if hasattr(api, k)} if api is not None else {}
    try:
        yield
    finally:
        api = sys.modules.get("api")
        if api is not None:
            for k in _API_BREAKERS:
                cur = getattr(api, k, None)
                if isinstance(cur, set):
                    cur.clear()
                    cur.update(saved.get(k, ()))


@pytest.fixture(autouse=True)
def _isolate_api_breakers():
    """テストが開けた遮断器を次のテストへ持ち越さない(中で開けて中で確かめるのは従来どおり)。"""
    with _api_breakers_restored():
        yield


@pytest.fixture(autouse=True)
def _studio_run_workers_are_quiesced_after_each_test(request):
    """Studio の実行ワーカーの QThread を、走ったまま次のテストへ持ち越さない(2026-11-26)。

    1.2.0 で Apply / Run がワーカーのスレッドで走るようになり(#364)、窓を閉じずに終わる
    テストが走ったままの QThread を残した。全テストが通った後、プロセスの終了時に Qt が
    ``QThread: Destroyed while thread '' is still running`` で abort する(Linux CI の
    full suite = exit 134、Windows = exit 127)。

    各テストの後に、残っている Studio の窓ごとに本体の ``quiesce``(停止を要求し、上限付きで
    待ち、GUI スレッドで退役させる —— 窓を閉じる時と同じ道)を呼ぶ。窓は閉じない:
    module scope の fixture が窓を次のテストへ渡すことがあり、閉じる必要も無い(スレッドが
    残らなければ abort は起きない)。上限内に止まらないワーカーは捨てずに、そのテストを
    失敗させる(fail-closed)。PySide6 を読んでいないテストでは何もしない。
    """
    yield
    qtw = sys.modules.get("PySide6.QtWidgets")
    if qtw is None:
        return
    app = qtw.QApplication.instance()
    if app is None:
        return
    stuck = 0
    for w in list(app.topLevelWidgets()):
        quiesce = getattr(w, "quiesce", None)
        if callable(quiesce) and getattr(w, "_run_controller", None) is not None:
            if not quiesce(timeout_ms=5000):
                stuck += 1
    if stuck:
        pytest.fail("%s left %d Studio window(s) whose run worker did not stop within 5 s"
                    % (request.node.nodeid, stuck), pytrace=False)


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
    # ★点群は**連結なものと非連結なものの両方**を置く。`tb_geodesic_distances` が
    #   不達を `inf` で表すのは契約どおりで、`ops.NONFINITE_IS_MEANINGFUL` に
    #   「1.0 に潰すと『届かない』が『近い』に化ける」と宣言済み。
    #   ここで一度 `normal` をわざと連結にして有限性ゲートを緑にしかけたが、
    #   それは**欠陥を隠す方向**だった —— 直すべきは門が台帳を見ていないこと。
    #   `normal` は橋でつないだ現実的な形、`two_clusters` は非連結を撃つ探針。
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


def feature_bank(n: int = 6) -> dict[str, float]:
    """スカラの feature。**素の float**(``backends_typed._sort_ok`` の契約)。

    ★2026-09-17 に足した。それまで 2-D 台帳に **feature を入力に取る op が 1 本も
    無かった**ので探針も要らなかったが、戻りの橋 ``feature_to_img`` が入って要る
    ようになった。0・負・極端な桁・非有限を必ず置く —— 特徴量は「面積」「長さ」の
    ような正の量から「相関」「歪度」のような符号つきまで混ざる sort で、
    片側だけの探針では符号の扱いを一度も試さないことになる。
    """
    return {
        "zero": 0.0,
        "unit": 1.0,
        "small": 1e-6,
        "negative": -1.5,
        "large": 1.0e4,
        "nonfinite": float("inf"),
    }


def matrix_bank(n: int = 6) -> dict[str, np.ndarray]:
    """一般の 2-D 数値行列。**特異・不良条件を必ず入れる**(擬似逆行列や条件数の
    op は、そこで初めて壊れるか壊れないかが分かれる)。"""
    rng = _rng()
    a = rng.standard_normal((n, n))
    ill = np.diag(np.logspace(0, -12, n))           # 条件数 1e12(有限だが極端)
    # ★**特異行列は必ず置く。** 一度ここから外しかけたが、それは誤りだった ——
    #   `tb_mat_cond` が特異行列で `inf` を返すのは**契約どおり**で、`ops.py` の
    #   `NONFINITE_IS_MEANINGFUL` に「厳密に特異な行列は s_min=0 なので inf が
    #   正しい答え。有限に潰すと『十分に良条件』と読めてしまう」と**既に宣言済み**
    #   だった。落ちていたのは op ではなく、**有限性ゲートがその台帳を見ていない**
    #   こと。探針を削って緑にするのは、欠陥を隠す行為。
    #   (同じ註に 2026-09-05 の教訓が書いてある ——「自分の probe では特異行列を
    #    作っていなかったので tb_mat_cond を取りこぼした」。探針から外すのは
    #    その取りこぼしを**わざと再現する**ことになる。)
    return {
        "normal": a,
        "singular": np.ones((n, n)),               # 階数 1 = 条件数 inf が正しい答え
        "ill_conditioned": ill,
        "near_zero": np.eye(n) * 1e-12,            # 極小だが可逆(条件数 1)
        "zeros": np.zeros((n, n)),                 # 特異。これも inf が正しい
        "tiny2": np.array([[1.0, 2.0], [3.0, 4.0]]),
        "tall": rng.standard_normal((n * 2, n)),   # 正方でない
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


def video_bank(f: int = 12, n: int = 24) -> dict[str, np.ndarray]:
    """(F, H, W) のフレーム列。**帯域内で揺れている領域**が本質の sort なので、
    揺れているもの・揺れていないもの・1 フレームだけ、を分けて置く。"""
    t = np.arange(f)[:, None, None]
    base = image_bank(n)["normal"][None, :, :]
    mask = np.zeros((1, n, n))
    mask[0, n // 4:n // 4 + n // 2, n // 4:n // 4 + n // 2] = 1.0
    return {
        "normal": np.clip(base + 0.2 * mask * np.sin(2 * np.pi * 4.0 * t / f), 0, 1),
        "static": np.repeat(base, f, axis=0),      # 揺れていない(帯域パワー 0)
        "const0": np.zeros((f, n, n)),
        "single_frame": base.copy(),               # 時間方向の差分が取れない
    }


def qimage_bank(n: int = 24) -> dict[str, np.ndarray]:
    """(H, W, 4) 四元数画像。**ノルム 0 の四元数**は正規化・共役が退化する場所。"""
    g = image_bank(n)["normal"]
    q = np.stack([np.ones_like(g), g, 0.5 - g, 0.25 * g], -1)
    return {
        "normal": q,
        "unit": q / np.linalg.norm(q, axis=-1, keepdims=True).clip(1e-12),
        "const0": np.zeros((n, n, 4)),             # ノルム 0(正規化できない)
        "real_only": np.stack([np.ones_like(g)] + [np.zeros_like(g)] * 3, -1),
    }


def cimage_bank(n: int = 24) -> dict[str, np.ndarray]:
    """(H, W) 複素画像。**位相は原点で定義されない**ので 0 を必ず含める。"""
    g = image_bank(n)["normal"]
    return {
        "normal": (g + 1j * (1.0 - g)).astype(np.complex128),
        "real_only": g.astype(np.complex128),
        "const0": np.zeros((n, n), np.complex128),  # 位相が未定義
        "unit_phase": np.exp(2j * np.pi * g),
    }


def lightfield_bank(u: int = 3, v: int = 3, n: int = 16) -> dict[str, np.ndarray]:
    """(U, V, H, W) の 4-D 光場。視差スロープが 0 の場合(全視点が同じ)を含める。"""
    g = image_bank(n)["normal"]
    lf = np.empty((u, v, n, n))
    for i in range(u):
        for j in range(v):
            lf[i, j] = np.roll(g, (i - u // 2, j - v // 2), axis=(0, 1))
    return {
        "normal": lf,
        "no_parallax": np.broadcast_to(g, (u, v, n, n)).copy(),   # スロープ 0
        "const0": np.zeros((u, v, n, n)),
        "single_view": g[None, None, :, :],        # 視差が測れない
    }


def beatcube_bank(c: int = 4, n: int = 16) -> dict[str, np.ndarray]:
    """(C, H, W) 複素のビート立方体(FMCW レーダ)。窓関数・FFT の入口。"""
    g = image_bank(n)["normal"]
    k = np.arange(c)[:, None, None]
    return {
        "normal": (g[None] * np.exp(2j * np.pi * 0.1 * k)).astype(np.complex128),
        "const0": np.zeros((c, n, n), np.complex128),
        "single_chirp": (g[None] + 0j).astype(np.complex128),
        "real_only": np.repeat(g[None], c, axis=0).astype(np.complex128),
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
    # ★第 3 段(2026-09-17): 戻りの橋 ``feature_to_img`` が入るまで、feature を
    # **入力**に取る op は 1 本も無かった(作る op は 125 本ある)。門が「探針の
    # 無い op が 1 本に増えた」と正しく落ちて教えた。
    "feature": feature_bank,        #  1 op
    "keypoints": keypoints_bank,    #  2 op
    "rgbimage": rgbimage_bank,      #  6 op
    # 第 2 段(同日): 複素・4-D の 5 sort = 48 op。これで探針なしはゼロになる。
    "video": video_bank,            # 16 op
    "qimage": qimage_bank,          # 11 op
    "cimage": cimage_bank,          #  9 op
    "lightfield": lightfield_bank,  #  8 op
    "beatcube": beatcube_bank,      #  4 op
}

KNOBS = [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0), (0.15, 0.85)]


def copy_input(x):
    if isinstance(x, dict):
        return {"shape": x["shape"], "cs": [c.copy() for c in x["cs"]]}
    return np.array(x, copy=True)


def inputs_for(in_sort: str, op_name: str | None = None):
    """Yield (name, value) edge inputs matching a sort. Unknown sort -> empty.

    ★``op_name`` を渡すと ``op_probe.OP_PROBE_OVERRIDE`` の **op 専用の探針**を
    優先する(2026-09-15)。``tests/test_backends_typed_liveness._sample_for`` と
    ``tests/test_op_probe_ledger`` は 2026-09-08 から既にそうしていたのに、
    **この関数だけがその知識に繋がっていなかった** —— 2026-09-14 に探針を
    151 op ぶん広げたとき、`tb_normals_to_egi` に sort 既定の探針(位置の雲)が
    届き、「原点が零ベクトルになり拒否される」という**既に書いてある理由**を
    踏み抜いて赤くなった。探針の知識は 1 か所に置き、全部の門が同じものを見る。

    sort 既定は「その sort が運びうる値」の帯を張るので、**override がある op でも
    帯を捨てない** —— 専用探針を先頭に置き、sort 既定を後ろに続ける。
    """
    if op_name:
        try:
            import op_probe

            ovr = op_probe.OP_PROBE_OVERRIDE.get(op_name)
        except Exception:                                    # noqa: BLE001
            ovr = None
        if ovr is not None:
            # ★2026-10-07: ここに ``return`` があり、上の docstring(sort 既定の帯を捨てない)
            #   に反して override のある 10 op は sort 既定の帯を一度も通っていなかった。
            #   sort 既定は「拒否が明示の fail-closed で記録される」ことの検査として通す
            #   (test_op_contracts.KNOWN_FALLS_BACK_ON_EDGE に by-design として載る)。
            yield "override", ovr[0]()
    bank = BANKS.get(in_sort)
    if bank is None:
        return
    for name, val in bank().items():
        yield name, val


@pytest.fixture(scope="session")
def registry():
    import ops
    return ops


# --------------------------------------------------------------------------- #
# ★CI: PR では変更に関係するテストだけ / 片はファイル単位で分ける(2026-11-10)     #
# --------------------------------------------------------------------------- #
# どちらも環境変数があるときだけ働く(手元の `pytest` は何も変わらない)。
#   FULLSEYE_CI_SELECTION=<一覧のファイル>  tools/ci_select_tests.py が書いた一覧に無いテストを外す
#   FULLSEYE_CI_SHARD=k/N                  ファイル単位の LPT で N 片に分け、k 片目だけ残す
#                                          (例外: SPLIT_BY_TEST のファイルはテスト単位。PoC の門)
# 選ぶ規則と、選ばなかったテストを master・毎日の full suite で回す約束は CONTRIBUTING.md の「CI: which tests run where」。
# 一覧が読めない・1 件も当たらないときは**止める**(黙って 0 件で緑にしない)。
@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    selection = os.environ.get("FULLSEYE_CI_SELECTION", "")
    shard = os.environ.get("FULLSEYE_CI_SHARD", "")
    if not selection and not shard:
        return
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_fullseye_ci_select_tests", os.path.join(ROOT, "tools", "ci_select_tests.py"))
    cst = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cst)
    try:
        info = cst.plan_session([it.nodeid for it in items], selection=selection or None,
                                shard=shard or None)
    except (OSError, ValueError) as e:
        raise pytest.UsageError("fullseye CI selection/shard failed (fail-closed): %s" % e)
    keep = set(info.pop("keep"))
    kept = [it for it in items if it.nodeid in keep]
    dropped = [it for it in items if it.nodeid not in keep]
    items[:] = kept
    if dropped:
        config.hook.pytest_deselected(items=dropped)
    unmatched = info.pop("unmatched", [])
    print("\n[fullseye-ci] %s" % json.dumps(info, ensure_ascii=False))
    if unmatched:
        print("[fullseye-ci] %d selection entries matched no collected test (e.g. a script that "
              "is not a parameter of its runner): %s" % (len(unmatched), unmatched[:20]))
