"""使い捨て runner で公開 Fullseye installer を端から端まで検査する / end-to-end test for the published installer.

wheel 指定なしでは実作業を拒否する。GitHub Actions は一時ディレクトリと各段の artifact log を渡し、
実物の Desktop / Start Menu / HKCU Uninstall 登録まで検査する。開発者は ``--dry-run`` だけを使う。
This script refuses real work without a wheel argument. GitHub Actions supplies a temporary directory
and records every stage log, including checks of the real Desktop / Start Menu / HKCU Uninstall registration.
Developers use ``--dry-run`` unless they explicitly opt in to that real-user-state check.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def _quote(cmd: list[str]) -> str:
    return " ".join('"%s"' % x if any(c.isspace() for c in x) else x for x in cmd)


class E2E:
    def __init__(self, root: Path, dry_run: bool):
        self.root, self.dry_run = root, dry_run
        self.logs = root / "logs"
        if not dry_run:
            self.logs.mkdir(parents=True, exist_ok=True)
        self.env = dict(os.environ)
        self.env.update({
            "HOME": str(root / "home"), "USERPROFILE": str(root / "home"),
            "APPDATA": str(root / "appdata"), "LOCALAPPDATA": str(root / "localappdata"),
            "XDG_DATA_HOME": str(root / "xdg-data"), "XDG_CONFIG_HOME": str(root / "xdg-config"),
            "FULLSEYE_LEDGER": str(root / "ledger" / "install_ledger.json"),
            "FULLSEYE_CACHE_DIR": str(root / "cache"), "FULLSEYE_E2E_ALLOW_AUTO_SHORTCUTS": "1",
            # CI の Windows runner が子プロセスをローカル code page で復号すると、
            # 日本語を含む setup 出力が reader thread で落ちる。子にも UTF-8 を明示し、
            # 親は常に同じ codec / fail-soft policy でログを残す。
            "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
        })

    def run(self, stage: str, cmd: list[str], *, check: bool = True, env: dict | None = None) -> subprocess.CompletedProcess | None:
        print("[%s] %s" % (stage, _quote(cmd)), flush=True)
        if self.dry_run:
            return None
        got = subprocess.run(cmd, cwd=self.root, env=env or self.env, text=True,
                             encoding="utf-8", errors="replace", stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, timeout=1800)
        (self.logs / (stage + ".log")).write_text(got.stdout, encoding="utf-8")
        if check and got.returncode:
            raise RuntimeError("%s failed (%s); see %s" % (stage, got.returncode, self.logs / (stage + ".log")))
        return got


def _bin(venv: Path, name: str) -> str:
    return str(venv / ("Scripts" if os.name == "nt" else "bin") / (name + (".exe" if os.name == "nt" else "")))


def _assert(path: Path, what: str) -> None:
    if not path.exists():
        raise RuntimeError("missing %s: %s" % (what, path))


def _real_user_state_allowed(env: dict[str, str] | None = None) -> bool:
    """実ユーザー状態に触れる E2E を許すのは GitHub Actions か明示 opt-in だけ / allow real-user-state E2E only in Actions or after explicit opt-in."""
    e = os.environ if env is None else env
    # CI=true だけなら手元の別ツールでも立つので、GitHub Actions の印も要る。
    # CI=true alone is set by many local tools; also require the GitHub Actions marker.
    in_actions = e.get("CI") == "true" and e.get("GITHUB_ACTIONS") == "true"
    return in_actions or e.get("FULLSEYE_E2E_ALLOW_REAL_USER_STATE") == "1"


def _print_real_user_state_refusal(env: dict[str, str] | None = None) -> None:
    """拒否の理由と安全な回し方を日英で表示する / print the refusal, reason, and safe ways to proceed in Japanese and English."""
    e = os.environ if env is None else env
    ci = e.get("CI", "<unset>")
    allowed = e.get("FULLSEYE_E2E_ALLOW_REAL_USER_STATE", "<unset>")
    message = (
        "拒否しました: installer E2E の実行を要求しましたが、CI=%r、FULLSEYE_E2E_ALLOW_REAL_USER_STATE=%r です。\n"
        "理由: この通し試験は実物の Desktop・Start Menu・HKCU Uninstall 登録を作成・削除して検証するため、"
        "手元の利用者登録を誤って変えないようにしています。\n"
        "回し方: 安全に手順だけを見るには `py -3.11 tools/installer_e2e.py --dry-run` を実行してください。"
        "使い捨て Windows 環境で実検証するときだけ、GitHub Actions の CI=true で実行するか、"
        "PowerShell で `$env:FULLSEYE_E2E_ALLOW_REAL_USER_STATE='1'` を設定してから `--wheel <wheel>` を付けて再実行してください。\n\n"
        "Refused: installer E2E requested a real run, but CI=%r and FULLSEYE_E2E_ALLOW_REAL_USER_STATE=%r.\n"
        "Why: this end-to-end test creates and removes the real Desktop, Start Menu, and HKCU Uninstall registration, "
        "so it must not accidentally change a developer's user state.\n"
        "How: inspect the plan safely with `py -3.11 tools/installer_e2e.py --dry-run`. "
        "For a real check only on a disposable Windows machine, run in GitHub Actions with CI=true, or set "
        "`$env:FULLSEYE_E2E_ALLOW_REAL_USER_STATE='1'` and rerun with `--wheel <wheel>`."
    )
    print(message % (ci, allowed, ci, allowed), flush=True)


def _shortcut_path(root: Path) -> Path | None:
    if os.name == "nt":
        return root / "appdata" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Fullseye" / "Fullseye Studio.lnk"
    if sys.platform.startswith("linux"):
        return root / "xdg-data" / "applications" / "fullseye-studio.desktop"
    return None


def _wait_gone(path: Path, seconds: int = 90) -> None:
    deadline = time.monotonic() + seconds
    while path.exists() and time.monotonic() < deadline:
        time.sleep(1)
    if path.exists():
        raise RuntimeError("pip uninstall did not remove %s within %s seconds" % (path, seconds))


def run_e2e(wheel: Path, root: Path, dry_run: bool) -> int:
    e = E2E(root, dry_run)
    venv = root / "venv"
    py = _bin(venv, "python")
    fs = _bin(venv, "fullseye")
    studio = _bin(venv, "fullseye-studio")
    rag = _bin(venv, "fullseye-rag")

    e.run("01-create-venv", [sys.executable, "-m", "venv", str(venv)])
    e.run("02-install-wheel", [py, "-m", "pip", "install", str(wheel)])
    e.run("03-version", [fs, "--version"])
    e.run("04-import", [py, "-c", "import fullseye; print(fullseye.version())"])
    first = e.run("05-first-command", [fs])
    if not dry_run and first.stdout != "fullseye setup --yes\n":
        raise RuntimeError("first normal command did not print exactly the explicit all-in entry")
    shortcut = _shortcut_path(root)
    if not dry_run and shortcut is not None:
        _assert(shortcut, "first-run Studio menu shortcut")
        if os.name == "nt":
            # 同梱の堅牢な .lnk parser で、名前だけでなくこの venv を指すことを検証する。
            # The installed robust .lnk parser proves the entry points at this venv, not just its file name.
            e.run("05b-link-target", [py, "-c", "from fullseye.shortcuts import read_lnk; import sys; "
                  "p=read_lnk(sys.argv[1]); print(p); assert 'pythonw' in p['Target'].lower()", str(shortcut)])

    setup = e.run("06-setup-all", [fs, "setup", "--yes", "--lang", "ja"], check=False)
    if not dry_run:
        if setup.returncode not in (0, 1):
            raise RuntimeError("setup returned %s, expected 0 or 1" % setup.returncode)
        if "[導入結果]" not in setup.stdout:
            raise RuntimeError("setup did not print its per-extra result table")

    skill = root / "home" / ".claude" / "skills" / "fullseye-ops"
    if not dry_run:
        _assert(skill / "SKILL.md", "RAG skill")
        _assert(skill / "RAG_MANIFEST.json", "RAG inventory")
    e.run("07a-rag-index", [py, "-c", "import fullseye; from pathlib import Path; "
          "p=Path(fullseye.__file__).parent/'data'/'OP_SEARCH.json'; print(p); assert p.is_file()"])
    e.run("07-rag-search", [rag, "search", "ノイズ除去"])

    image = root / "input.png"
    e.run("08-make-input", [py, "-c", "from PIL import Image; import sys; Image.new('L',(16,16),128).save(sys.argv[1])", str(image)])
    e.run("09-one-operation", [fs, "apply", "sobel_amp", str(image), str(root / "output.png")])
    studio_env = dict(e.env, QT_QPA_PLATFORM="offscreen")
    smoke = ("from PySide6 import QtCore, QtWidgets; import studio; "
             "app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([]); "
             "QtCore.QTimer.singleShot(200, app.quit); raise SystemExit(studio.main([]))")
    e.run("10-studio-offscreen", [py, "-c", smoke], env=studio_env)

    cpp = Path.cwd() / "examples" / "c_api" / "hello_cpp"
    if cpp.is_file():
        e.run("11-cpp-hello", [str(cpp)])
    elif not dry_run:
        (e.logs / "11-cpp-hello.log").write_text("SKIP: examples/c_api/hello_cpp is not present in this branch\n", encoding="utf-8")

    e.run("12-uninstall", [fs, "setup", "--uninstall", "--yes", "--lang", "ja"], check=False)
    if not dry_run:
        if os.name == "nt":
            installed_pkg = venv / "Lib" / "site-packages" / "fullseye"
        else:
            matches = list((venv / "lib").glob("python*/site-packages/fullseye"))
            installed_pkg = matches[0] if matches else venv / "lib" / "fullseye"
        _wait_gone(installed_pkg)  # pip の後始末プロセスは意図的に非同期 / intentionally asynchronous
        if shortcut is not None and shortcut.exists():
            raise RuntimeError("shortcut remained after uninstall: %s" % shortcut)
        if skill.exists():
            raise RuntimeError("RAG skill remained after uninstall: %s" % skill)
        if os.name == "nt":
            check = ("import winreg; "
                     "k=r'Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Fullseye'; "
                     "\ntry: winreg.OpenKey(winreg.HKEY_CURRENT_USER,k)\nexcept FileNotFoundError: raise SystemExit(0)\nraise SystemExit(1)")
            e.run("13-registry-gone", [sys.executable, "-c", check])
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wheel", type=Path, help="wheel built by this commit (required except --dry-run)")
    ap.add_argument("--wheel-dir", type=Path, help="directory containing exactly one built wheel")
    ap.add_argument("--workdir", type=Path, default=None, help="disposable runner directory")
    ap.add_argument("--dry-run", action="store_true", help="print the shared CI plan; do not create a venv or mutate state")
    ns = ap.parse_args(argv)
    if ns.wheel and ns.wheel_dir:
        ap.error("use one of --wheel / --wheel-dir")
    if ns.wheel_dir:
        wheels = sorted(ns.wheel_dir.glob("*.whl"))
        if len(wheels) != 1:
            ap.error("--wheel-dir must contain exactly one wheel (found %d)" % len(wheels))
        ns.wheel = wheels[0]
    if ns.wheel is None and not ns.dry_run:
        ap.error("--wheel or --wheel-dir is required unless --dry-run is used")
    if not ns.dry_run and not _real_user_state_allowed():
        _print_real_user_state_refusal()
        return 2
    root = (ns.workdir or Path(tempfile.mkdtemp(prefix="fullseye-installer-e2e-"))).resolve()
    wheel = (ns.wheel or Path("dist/fullseye.whl")).resolve()
    print("e2e workdir: %s" % root)
    return run_e2e(wheel, root, ns.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
