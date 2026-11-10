# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""push の前に、手元の Linux(Windows なら WSL2)で GitHub CI と同じ全数を回す。

## なぜ要るか(2026-11-10)

2026-11-09〜10 に「CI で落ちる → 直して push → また落ちる」の往復が 4 回あった(1 回 1.5 時間)。
落ちた原因は 空の表明・所要時間の記録・記録値のずれ・Linux のファイル権限と lock の違い ——
**どれも Linux で全数を回せば手元で見つかった**。PR の CI は軽い確認(関係するテスト + 必ず回す門 +
numpy だけの構成)に絞るので、全数は push の前に手元で回し、master と夜間の GitHub で回す。

## 使い方

    py -3.11 tools/ci_local.py                 # Windows: HEAD を WSL2 で全数(初回は環境を作る)
    py -3.11 tools/ci_local.py --ref origin/master -n 12
    python3 tools/ci_local.py                  # Linux: 同じ(WSL を介さない)
    py -3.11 tools/ci_local.py --only core     # numpy+scipy だけの構成の確認だけ

結果は要約 ``summary.md``(PR の本文に貼れる形)と JUnit・ログを ``--out`` に書く
(既定は一時ディレクトリの ``fullseye-ci-local/<時刻>-<commit>``)。終了コードは全部通れば 0。

## 何を検査するか

* **commit そのもの**を検査する。作業木の未 commit の変更は検査しない(要約に件数と名前を書く)。
  検査する木は Linux 側の別の clone(``$FULLSEYE_CI_LOCAL_DIR/repo``、既定 ``~/fullseye-ci-local``)で、
  毎回 ``git checkout --detach`` + ``git clean -fdx`` する。Windows の作業木を ``/mnt/c`` 越しに読まない
  理由は 2 つ: 遅い(9P 越し)ことと、``core.autocrlf=true`` の作業木は CRLF で権限ビットも無く、
  Linux の CI と同じ木にならないこと。
* 段は**落ちやすくて軽いものから順に、直列で**回す(同時には走らせない)。2026-11-09〜10 の #294・#295 で
  落ちた門は 3 本で 1 分かからないのに、片の中に混ざって 30〜45 分後まで赤にならなかった。
  1. ruff —— ci.yml の ``lint`` ジョブの ``ruff check .``。
  2. ``tools/regen_all.py --check`` —— ci.yml の shard 1 の最後の段。
  3. 門 —— ``tools/ci_always_run.txt``(PR で必ず回す門。無い commit では ``FALLBACK_GATES``)。
  4. core —— ci.yml の ``core-minimal`` ジョブ(numpy+scipy だけの editable install、smoke、wheel を
     sdist から建てて配布物の側で op を数える、packaging の不変条件、wheel からの MCP / fs_apply)。
  5. full suite —— ci.yml の ``test`` ジョブ(py3.11、optional backend 全部入り)と同じ依存と環境変数で、
     pytest-xdist で並列に回す。**門も外さない**(確かめる範囲を減らさない。二重に回る分は要約に出す)。
  1〜4 のどれかが落ちたらそこで止めて要約を書く(``--keep-going`` で最後まで回す)。
* 環境変数は**継承しない**(``env -i`` 相当)。手元の ``FULLSEYE_*_DATA`` や ``~/.cache/fullseye`` の
  実データが見えると CI と違う分岐を通るので、HOME も run ごとの空のディレクトリにする。
  入れるのは GitHub の runner と ci.yml が与えるもの: ``CI=true`` ``GITHUB_ACTIONS=true``
  ``PYTHONUTF8=1`` ``QT_QPA_PLATFORM=offscreen`` ``LANG=C.UTF-8`` ``TZ=UTC`` と、full suite だけ
  ``FULLSEYE_REQUIRE_OPTIONAL=1`` ``FULLSEYE_FIGURES=off``。PYTHONPATH は無し、pytest は
  ``python -m pytest`` でなく ``pytest`` で起動する(cwd が sys.path に入らない = CI と同じ)。
  ★``CI=1`` ではなく ``CI=true``: ``os.environ.get("CI") == "1"`` で分岐する PoC があり、GitHub では偽になる。

## CI と違うところ(要約にも書く)

* 並列(xdist)。CI の片の中は直列。並列でだけ出る順序依存は夜間の order-shuffle が見る型の失敗。
* ``--cov`` は既定で付けない(``--cov`` で付ける)。py3.11 だけ(3.12 / 3.14 は master で GitHub が回す)。
* BLAS のスレッド数を ``CPU 数 / 並列数`` に絞る(付けないと 24 並列 × 24 スレッドで詰まる)。
* 依存の版は venv を作った時点のもの。CI は毎回その日の最新を入れるので、``--refresh-hours``
  (既定 24)より古い venv は ``pip install -U --upgrade-strategy eager`` で揃え直す。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

# ---- ci.yml と揃える(変えたら ci.yml の該当行も見る) ----------------------------------------
#: ci.yml `test` ジョブの extras と追加パッケージ(+ 並列用の pytest-xdist)。
FULL_EXTRAS = "opencv,skimage,pil,wavelets,gui,video,volume,gltf,lidar,pcd,xlsx,export-verify"
FULL_EXTRA_PKGS = ["pytest", "pytest-cov", "pytest-split", "matplotlib", "sympy", "ziglang",
                   "hypothesis", "pytest-timeout", "pytest-xdist"]
#: ci.yml `test` ジョブの「Optional backends (py3.11 only)」。
TORCH_INDEX = "https://download.pytorch.org/whl/cpu"
TORCH_PKGS = ["torch>=2.13"]
OPTIONAL_PKGS = ["kornia>=0.9", "mahotas>=1.4"]
OPENCV_CONTRIB = "opencv-contrib-python>=4.8.1.78"
#: ci.yml の各ジョブ先頭の「pip と証明書を更新」。
PIP_BOOTSTRAP = ["pip>=26.2.2", "certifi>=2026.10.19"]
BUILD_PIN = "build==1.6.1"
#: CI の runner が入れる apt パッケージ(Qt offscreen と CJK フォント 2 本)。
APT_PKGS = ["libegl1", "libgl1", "libxkbcommon-x11-0", "libdbus-1-3",
            "fonts-noto-cjk", "fonts-ipafont-gothic"]
#: ci.yml `lint` ジョブ。
RUFF_PIN = "ruff>=0.4"
#: ``tools/ci_always_run.txt`` が無い commit で回す門(2026-11-10 の版の写し)。
FALLBACK_GATES = [
    "tests/test_vacuous_assertions.py", "tests/test_type_alias_ledger.py",
    "tests/test_test_durations_is_fresh.py", "tests/test_provenance_naming.py",
    "tests/test_no_invalid_escape_sequences.py", "tests/test_svd_full_matrices.py", "tests/test_fssystem.py",
    "tests/test_docs_liquid_safe.py", "tests/test_no_stray_root_images_2026_11_01.py",
    "tests/test_review_fixes_lib2_2026_10_07.py",
]
#: 依存の定義を変えたら上げる(venv を作り直す合図)。
SPEC_VERSION = "1"

#: ci.yml の「Optional backends」の最後の確認と同じ。
VERIFY_FULL = ("import torch, kornia, mahotas, cv2; print(torch.__version__, cv2.__version__);"
               " assert hasattr(cv2, 'xfeatures2d')")
PHASE_ORDER = ("ruff", "regen_all --check", "門", "core (numpy+scipy)", "full suite")
DEFAULT_DISTRO = os.environ.get("FULLSEYE_CI_LOCAL_DISTRO", "Ubuntu-24.04")


def _log(msg: str) -> None:
    print(f"[ci_local {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _fmt_dur(sec: float) -> str:
    sec = int(round(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h{m:02d}m{s:02d}s" if h else f"{m}m{s:02d}s"


# =============================================================================================
# 外側(Windows / Linux の作業木): 何を検査するかを決め、内側を起動する
# =============================================================================================

def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout.strip()


def _to_wsl(path: Path, distro: str) -> str:
    """Windows のパスを WSL のパスに(``wslpath -u``)。"""
    out = subprocess.run(["wsl.exe", "-d", distro, "--exec", "wslpath", "-u", str(path).replace("\\", "/")],
                         check=True, capture_output=True)
    return out.stdout.decode("utf-8", "replace").strip()


def _host_main(args: argparse.Namespace, passthrough: list[str]) -> int:
    repo = Path(_git(Path.cwd(), "rev-parse", "--show-toplevel"))
    common = Path(_git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    sha = _git(repo, "rev-parse", f"{args.ref}^{{commit}}")
    head = _git(repo, "rev-parse", "HEAD")
    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    subject = _git(repo, "log", "-1", "--format=%s", sha)
    if sha == head:
        dirty = [ln for ln in _git(repo, "status", "--porcelain", "--untracked-files=normal").splitlines() if ln]
        target = f"HEAD({branch})"
    else:
        dirty = []
        target = args.ref
    notes: list[str] = []
    lock = os.environ.get("FULLSEYE_GPU_LOCK")
    if lock and Path(lock).exists():
        try:
            holder = Path(lock).read_text(encoding="utf-8", errors="replace").strip().splitlines()[:1]
        except OSError:
            holder = []
        notes.append("GPU ロックが取られている(GPU の重い処理が並走中の可能性): " + (holder[0] if holder else "?"))

    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(args.out) if args.out else Path(tempfile.gettempdir()) / "fullseye-ci-local" / f"{stamp}-{sha[:10]}"
    out.mkdir(parents=True, exist_ok=True)
    meta = {"sha": sha, "ref": args.ref, "target": target, "branch": branch, "subject": subject,
            "dirty": dirty, "host": platform.platform(), "notes": notes,
            "source_dirty_applies": sha == head}
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    me = Path(__file__).resolve()
    _log(f"検査する commit: {sha[:10]} {subject[:60]} ({target})")
    if dirty:
        _log(f"作業木に未 commit の変更 {len(dirty)} 件(検査しない。要約に書く)")

    inner = ["--inside", "--source", None, "--meta", None, "--out", None, *passthrough]
    if os.name == "nt":
        d = args.distro
        inner[2], inner[4], inner[6] = _to_wsl(common, d), _to_wsl(out / "meta.json", d), _to_wsl(out, d)
        cmd = ["wsl.exe", "-d", d, "--cd", "~", "--exec", "python3", _to_wsl(me, d), *inner]
    else:
        inner[2], inner[4], inner[6] = str(common), str(out / "meta.json"), str(out)
        cmd = [sys.executable, str(me), *inner]
    rc = subprocess.call(cmd)
    summary = out / "summary.md"
    if summary.exists():
        print()
        print(summary.read_text(encoding="utf-8"))
        _log(f"要約: {summary}")
    return rc


# =============================================================================================
# 内側(Linux): 検査する木を揃え、3 段を回し、要約を書く
# =============================================================================================

class Inner:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.state = Path(os.environ.get("FULLSEYE_CI_LOCAL_DIR") or Path.home() / "fullseye-ci-local")
        self.repo = self.state / "repo"
        self.venv_full = self.state / "venv-full"
        self.venv_core = self.state / "venv-core"
        self.out = Path(args.out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.meta = json.loads(Path(args.meta).read_text(encoding="utf-8")) if args.meta else {}
        self.timings: dict[str, float] = {}
        self.results: dict[str, str] = {}
        self.ncpu = os.cpu_count() or 1

    # ---- 共通 ------------------------------------------------------------------------------
    def run(self, cmd: list[str], *, env: dict | None = None, cwd: Path | None = None, log: str | None = None,
            check: bool = True) -> int:
        shown = " ".join(shlex.quote(c) for c in cmd)
        _log(f"$ {shown[:200]}")
        if log:
            with open(self.out / log, "a", encoding="utf-8") as fh:
                fh.write(f"\n$ {shown}\n")
                fh.flush()
                rc = subprocess.call(cmd, env=env, cwd=cwd, stdout=fh, stderr=subprocess.STDOUT)
        else:
            rc = subprocess.call(cmd, env=env, cwd=cwd)
        if check and rc != 0:
            raise RuntimeError(f"exit {rc}: {shown}" + (f"(ログ {self.out / log})" if log else ""))
        return rc

    def base_env(self, venv: Path, home: Path) -> dict:
        """CI の runner が与える環境だけ(手元の環境変数は継承しない)。"""
        tmp = home / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        env = {
            "PATH": f"{venv}/bin:/usr/local/bin:/usr/bin:/bin",
            "HOME": str(home), "TMPDIR": str(tmp), "LANG": "C.UTF-8", "TZ": "UTC",
            "CI": "true", "GITHUB_ACTIONS": "true",
            "PYTHONUTF8": "1", "QT_QPA_PLATFORM": "offscreen",
            "VIRTUAL_ENV": str(venv),
        }
        return env

    def clean_tree(self) -> None:
        """前の段の置き土産を消す(CI は段ごとに別の checkout)。editable の egg-info だけ残す。

        2026-11-10 実測: core の段の ``.wheelenv/`` が残ったまま全数を回し、repo を走査する門
        (tests/test_fssystem.py)が site-packages の写しを「読み手」に数えて落ちた。
        """
        # 追跡ファイルも commit の中身に戻す(regen_all --check が落ちたとき、書き換えた生成物が残る)
        self.run(["git", "-C", str(self.repo), "checkout", "-q", "-f", "--detach", self.meta["sha"]],
                 log="setup.log")
        self.run(["git", "-C", str(self.repo), "clean", "-q", "-f", "-d", "-x", "-e", "*.egg-info"],
                 log="setup.log")

    def fresh_home(self, name: str) -> Path:
        home = self.state / "homes" / name
        shutil.rmtree(home, ignore_errors=True)
        home.mkdir(parents=True)
        return home

    # ---- 検査する木 ------------------------------------------------------------------------
    def sync_repo(self) -> None:
        sha = self.meta["sha"]
        if not (self.repo / ".git").exists():
            self.state.mkdir(parents=True, exist_ok=True)
            self.run(["git", "clone", "-q", "--no-checkout", self.args.source, str(self.repo)], log="setup.log")
        # 改行と権限は Linux の CI と同じに(ここの設定で Windows の autocrlf が入らないようにする)
        self.run(["git", "-C", str(self.repo), "config", "core.autocrlf", "false"])
        self.run(["git", "-C", str(self.repo), "config", "core.filemode", "true"])
        have = subprocess.call(["git", "-C", str(self.repo), "cat-file", "-e", f"{sha}^{{commit}}"],
                               stderr=subprocess.DEVNULL) == 0
        if not have:
            self.run(["git", "-C", str(self.repo), "fetch", "-q", self.args.source, sha], log="setup.log")
        self.run(["git", "-C", str(self.repo), "checkout", "-q", "-f", "--detach", sha], log="setup.log")
        self.run(["git", "-C", str(self.repo), "clean", "-q", "-f", "-d", "-x"], log="setup.log")
        got = subprocess.run(["git", "-C", str(self.repo), "rev-parse", "HEAD"], capture_output=True,
                             text=True).stdout.strip()
        if got != sha:
            raise RuntimeError(f"検査する木が {got} になった(期待 {sha})")

    # ---- venv ------------------------------------------------------------------------------
    def find_python311(self) -> str:
        if self.args.python:
            return self.args.python
        p = shutil.which("python3.11")
        if p:
            return p
        uv = shutil.which("uv") or str(Path.home() / ".local/bin/uv")
        if Path(uv).exists():
            r = subprocess.run([uv, "python", "find", "3.11"], capture_output=True, text=True)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
            self.run([uv, "python", "install", "3.11"], log="setup.log")
            r = subprocess.run([uv, "python", "find", "3.11"], capture_output=True, text=True)
            if r.returncode == 0:
                return r.stdout.strip()
        raise RuntimeError("Python 3.11 が無い(--python で渡すか、uv を入れる)")

    def apt_check(self) -> list[str]:
        missing = [p for p in APT_PKGS
                   if subprocess.call(["dpkg", "-s", p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)]
        if missing:
            _log(f"apt パッケージが足りない: {missing} → sudo -n apt-get install を試す")
            rc = subprocess.call(["sudo", "-n", "apt-get", "install", "-y", "-q", *missing],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if rc != 0:
                return missing
        return []

    def spec_hash(self, which: str) -> str:
        h = hashlib.sha256()
        h.update(f"{SPEC_VERSION}|{which}".encode())
        h.update((self.repo / "pyproject.toml").read_bytes())
        return h.hexdigest()[:16]

    def ensure_venv(self, venv: Path, which: str, env: dict) -> str:
        """venv を用意する。返り値 = 何をしたか(要約用)。"""
        stamp = venv / ".ci_local_stamp.json"
        want = self.spec_hash(which)
        info = json.loads(stamp.read_text()) if stamp.exists() else {}
        age_h = (time.time() - info.get("refreshed", 0)) / 3600
        py = venv / "bin" / "python"
        pip = [str(py), "-m", "pip", "install", "-q"]
        if not py.exists() or self.args.rebuild:
            shutil.rmtree(venv, ignore_errors=True)
            self.run([self.find_python311(), "-m", "venv", str(venv)], log="setup.log")
            action, upgrade = "作った", []
        elif info.get("spec") != want or age_h > self.args.refresh_hours:
            action, upgrade = f"揃え直した(前回 {age_h:.0f} 時間前)", ["-U", "--upgrade-strategy", "eager"]
        else:
            # 依存は据え置き。editable の写像だけは毎回作り直す(clean -fdx で egg-info が消えるため)
            self.run([*pip, "--no-deps", "-e", "."], env=env, cwd=self.repo, log="setup.log")
            # ★再利用のたびに中身を確かめる。2026-11-10 実測: 揃え直しが途中で落ちた venv(cv2 が空)を
            #   stamp だけ見て再利用し、全数の 720 件が「backend が無い」で落ちた。
            if which != "full" or self.run([str(py), "-c", VERIFY_FULL], env=env, log="setup.log", check=False) == 0:
                return f"再利用({age_h:.0f} 時間前に揃えた)"
            action, upgrade = "壊れていたので揃え直した", ["-U", "--upgrade-strategy", "eager"]
        stamp.unlink(missing_ok=True)  # 途中で落ちたら次回は揃え直す
        self.run([*pip, "--upgrade", *PIP_BOOTSTRAP], env=env, log="setup.log")
        if which == "full":
            self.run([*pip, *upgrade, "-e", f".[{FULL_EXTRAS}]", *FULL_EXTRA_PKGS], env=env, cwd=self.repo,
                     log="setup.log")
            self.run([*pip, *upgrade, "--index-url", TORCH_INDEX, *TORCH_PKGS], env=env, log="setup.log")
            self.run([*pip, *upgrade, *OPTIONAL_PKGS], env=env, log="setup.log")
            self.run([str(py), "-m", "pip", "uninstall", "-y", "-q", "opencv-python"], env=env, log="setup.log",
                     check=False)
            # ★--force-reinstall: 揃え直しの道では上の `-e .[opencv]` が opencv-python を入れ直し、その uninstall が
            #   contrib と共有の cv2/ を消す。contrib は「最新なので何もしない」ため cv2 が空になった(2026-11-10 実測)。
            self.run([*pip, "--force-reinstall", "--no-deps", OPENCV_CONTRIB], env=env, log="setup.log")
            self.run([str(py), "-c", VERIFY_FULL], env=env, log="setup.log")
        else:
            self.run([*pip, *upgrade, "-e", "."], env=env, cwd=self.repo, log="setup.log")
            self.run([*pip, *upgrade, BUILD_PIN, "pytest"], env=env, log="setup.log")
        stamp.write_text(json.dumps({"spec": want, "refreshed": time.time()}))
        return action

    def versions(self, venv: Path, env: dict) -> str:
        code = ("import importlib.metadata as m\n"
                "out=[]\n"
                "for n in ['numpy','scipy','opencv-contrib-python','scikit-image','torch','pillow','pytest',"
                "'pytest-xdist','threadpoolctl']:\n"
                "    try: out.append(f'{n} {m.version(n)}')\n"
                "    except Exception: pass\n"
                "print(', '.join(out))")
        r = subprocess.run([str(venv / "bin/python"), "-c", code], env=env, capture_output=True, text=True)
        return r.stdout.strip()

    # ---- 段 --------------------------------------------------------------------------------
    def phase_tests(self) -> None:
        env = self.test_env(self.full_env("full"))
        n = self.args.workers
        junit = self.out / "junit-full.xml"
        cmd = [str(self.venv_full / "bin/pytest"), "-q", "-ra", f"--junitxml={junit}"]
        if n > 1:
            cmd += ["-n", str(n), "--dist", self.args.dist]
        if self.args.cov:
            cmd += ["--cov"]
        cmd += self.args.pytest_args
        t0 = time.time()
        rc = self.run(cmd, env=env, cwd=self.repo, log="full-suite.log", check=False)
        self.timings["full suite"] = time.time() - t0
        self.full_rc = rc
        self.results["full suite"] = "ok" if rc == 0 else f"失敗(exit {rc})"

    def full_env(self, name: str) -> dict:
        env = self.base_env(self.venv_full, self.fresh_home(name))
        if not getattr(self, "_full_ready", False):
            self.setup_notes.append("full venv: " + self.ensure_venv(self.venv_full, "full", env))
            self.versions_full = self.versions(self.venv_full, env)
            self._full_ready = True
        return env

    def test_env(self, env: dict) -> dict:
        env = dict(env, FULLSEYE_REQUIRE_OPTIONAL="1", FULLSEYE_FIGURES="off")
        n = self.args.workers
        self.threads = max(1, self.ncpu // max(1, n))
        if n > 1:
            for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
                env[k] = str(self.threads)
        return env

    def phase_ruff(self) -> None:
        env = self.full_env("ruff")
        ruff = self.venv_full / "bin/ruff"
        if not ruff.exists():
            self.run([str(self.venv_full / "bin/python"), "-m", "pip", "install", "-q", RUFF_PIN], env=env,
                     log="setup.log")
        t0 = time.time()
        rc = self.run([str(ruff), "check", "."], env=env, cwd=self.repo, log="ruff.log", check=False)
        self.timings["ruff"] = time.time() - t0
        self.results["ruff"] = "ok" if rc == 0 else f"失敗(exit {rc}、ruff.log)"

    def gate_files(self) -> tuple[list[str], str]:
        listed = self.repo / "tools" / "ci_always_run.txt"
        if listed.exists():
            names = [ln.split("#", 1)[0].strip() for ln in listed.read_text(encoding="utf-8").splitlines()]
            src = "tools/ci_always_run.txt"
        else:
            names, src = list(FALLBACK_GATES), "ci_local.py の FALLBACK_GATES(ci_always_run.txt の無い commit)"
        names = [n for n in names if n]
        files = [n for n in names if (self.repo / n.split("::", 1)[0]).exists()]
        if not files:
            raise RuntimeError(f"門が 1 本も無い({src})")
        gone = len(names) - len(files)
        return files, f"{src}、{len(files)} 本" + (f"(実在しない {gone} 本を除いた)" if gone else "")

    def phase_gates(self) -> None:
        env = self.test_env(self.full_env("gates"))
        files, src = self.gate_files()
        self.setup_notes.append(f"門: {src}")
        junit = self.out / "junit-gates.xml"
        cmd = [str(self.venv_full / "bin/pytest"), "-q", "-ra", f"--junitxml={junit}"]
        if self.args.workers > 1:
            cmd += ["-n", str(min(self.args.workers, len(files))), "--dist", "load"]
        t0 = time.time()
        rc = self.run(cmd + files, env=env, cwd=self.repo, log="gates.log", check=False)
        self.timings["門"] = time.time() - t0
        jc = self.junit_counts(junit)
        if jc["tests"] == 0:
            rc = rc or 5  # 1 件も走っていない門は通さない
        self.results["門"] = ("ok" if rc == 0 else f"失敗(exit {rc}、gates.log)") + f" — {jc['tests']:,} 件"
        self.gate_files_run = files

    def phase_regen(self) -> None:
        env = self.full_env("regen")
        t0 = time.time()
        rc = self.run([str(self.venv_full / "bin/python"), "tools/regen_all.py", "--check"], env=env,
                      cwd=self.repo, log="regen.log", check=False)
        self.timings["regen_all --check"] = time.time() - t0
        self.results["regen_all --check"] = "ok" if rc == 0 else f"失敗(exit {rc}、regen.log)"

    def phase_core(self) -> None:
        home = self.fresh_home("core")
        env = self.base_env(self.venv_core, home)
        self.setup_notes.append("core venv: " + self.ensure_venv(self.venv_core, "core", env))
        py = str(self.venv_core / "bin/python")
        repo = self.repo
        for junk in (".wheelenv", "dist_check", "ops_editable.json", "ops_wheel.json"):
            p = repo / junk
            shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
        smoke = (
            "import numpy as np, fullseye\n"
            "img = np.zeros((64, 64)); img[16:48, 16:48] = 1.0\n"
            "out = fullseye.run_pipeline(img, ['gaussian', 'sobel_amp', 'otsu'])\n"
            "assert set(np.unique(out)) <= {0.0, 1.0}\n"
            "print('bare-install pipeline smoke ok')\n")
        steps = [
            ("import", [py, "-c", "import fullseye, fsi18n; print('import ok')"]),
            ("op 数", [py, "-c", "import fullseye; n=len(fullseye.op_names()); print(n, 'ops'); assert n > 500"]),
            ("3-D op 数", [py, "-c", "import ops3d, pipeline3d, measure3d; assert len(ops3d.list_ops()) > 200"]),
            ("pipeline smoke", [py, "-c", smoke]),
            ("wheel: editable の op", [py, "tools/ci_wheel_check.py", "--dump", "ops_editable.json"]),
            ("wheel: sdist→wheel", [py, "-m", "build", "-o", "dist_check"]),
            ("wheel: venv", [self.find_python311(), "-m", "venv", ".wheelenv"]),
            ("wheel: 入れる", ["bash", "-c", ".wheelenv/bin/pip install -q numpy scipy dist_check/*.whl"]),
            ("wheel: 配布物の op", [".wheelenv/bin/python", "tools/ci_wheel_check.py", "--dump", "ops_wheel.json"]),
            ("wheel: 比べる", [py, "tools/ci_wheel_check.py", "--compare", "ops_editable.json", "ops_wheel.json"]),
            ("wheel: 大きさ", [py, "-c", "import glob,os,sys; w=glob.glob('dist_check/*.whl')[0]; s=os.path.getsize(w);"
                                     " print('wheel %.1f MB' % (s/1e6)); sys.exit(1 if s > 70e6 else 0)"]),
            ("packaging", [str(self.venv_core / "bin/pytest"), "tests/test_unified_packaging.py",
                           "tests/test_packaging_foundation.py", "-q",
                           f"--junitxml={self.out / 'junit-core-packaging.xml'}"]),
        ]
        t0 = time.time()
        failed = []
        for name, cmd in steps:
            if self.run(cmd, env=env, cwd=repo, log="core.log", check=False) != 0:
                failed.append(name)
                if name.startswith("wheel:"):
                    break
        if not failed:
            wenv = dict(env, FULLSEYE_WHEEL_GATE="1", FULLSEYE_WHEEL_PYTHON=".wheelenv/bin/python")
            cmd = [str(self.venv_core / "bin/pytest"), "tests/test_mcp_wheel.py", "tests/test_abi_wheel.py",
                   "-q", "-ra", f"--junitxml={self.out / 'junit-core-wheel.xml'}"]
            if self.run(cmd, env=wenv, cwd=repo, log="core.log", check=False) != 0:
                failed.append("MCP + fs_apply from the wheel")
        self.timings["core (numpy+scipy)"] = time.time() - t0
        self.results["core (numpy+scipy)"] = "ok" if not failed else "失敗: " + "、".join(failed) + "(core.log)"

    # ---- 要約 ------------------------------------------------------------------------------
    def gate_time_in_full(self, junit: Path) -> float | None:
        """全数の JUnit のうち、門のファイルのテストに掛かった時間の和(二重に回る分)。"""
        files = getattr(self, "gate_files_run", None)
        if not files or not junit.exists():
            return None
        mods = {f.split("::", 1)[0][:-3].replace("/", ".") for f in files}
        total = 0.0
        for case in ET.parse(junit).getroot().iter("testcase"):
            cls = case.get("classname", "")
            if cls in mods or cls.rsplit(".", 1)[0] in mods:
                total += float(case.get("time") or 0)
        return total

    @staticmethod
    def junit_counts(path: Path) -> dict:
        res = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "xfailed": 0, "failed": [],
               "skipped_names": []}
        if not path.exists():
            return res
        root = ET.parse(path).getroot()
        for case in root.iter("testcase"):
            res["tests"] += 1
            name = f"{case.get('classname', '')}::{case.get('name', '')}"
            if case.find("failure") is not None:
                res["failures"] += 1
                res["failed"].append(name)
            elif case.find("error") is not None:
                res["errors"] += 1
                res["failed"].append(name + "(error)")
            elif case.find("skipped") is not None:
                if case.find("skipped").get("type") == "pytest.xfail":
                    res["xfailed"] += 1
                else:
                    res["skipped"] += 1
                    res["skipped_names"].append(name)
        return res

    def write_summary(self, total: float, crash: str | None) -> int:
        m = self.meta
        lines = ["### 手元の全数(Linux)— tools/ci_local.py", ""]
        lines.append(f"- commit: `{m.get('sha', '?')[:12]}` {m.get('subject', '')}")
        lines.append(f"- 検査した対象: {m.get('target', '?')}(commit そのもの。Linux 側の clone で "
                     "`checkout --detach` + `clean -fdx`)")
        dirty = m.get("dirty") or []
        if dirty:
            shown = ", ".join(f"`{d}`" for d in dirty[:15]) + (" ほか" if len(dirty) > 15 else "")
            lines.append(f"- **作業木に未 commit の変更 {len(dirty)} 件 —— 検査していない**: {shown}")
        elif m.get("source_dirty_applies"):
            lines.append("- 作業木: きれい(未 commit の変更なし)")
        else:
            lines.append("- 作業木: HEAD 以外の ref を検査したので作業木の状態は無関係")
        osname = platform.freedesktop_os_release().get("PRETTY_NAME", "Linux") if hasattr(
            platform, "freedesktop_os_release") else "Linux"
        wsl = " (WSL2)" if "microsoft" in platform.release().lower() else ""
        lines.append(f"- 環境: {osname}{wsl}, {self.ncpu} CPU, Python 3.11 venv, "
                     f"xdist `-n {self.args.workers} --dist {self.args.dist}`, BLAS {getattr(self, 'threads', '-')} スレッド"
                     + (", --cov" if self.args.cov else ""))
        if getattr(self, "versions_full", ""):
            lines.append(f"- 版: {self.versions_full}")
        for note in self.setup_notes:
            lines.append(f"- {note}")
        for note in m.get("notes", []):
            lines.append(f"- 注: {note}")
        try:
            load = Path("/proc/loadavg").read_text().split()[:3]
            lines.append(f"- 終了時の load average: {' '.join(load)}")
        except OSError:
            pass
        lines += ["", "| 段 | 結果 | 所要時間 |", "|---|---|---|"]
        jc = self.junit_counts(self.out / "junit-full.xml")
        for phase in PHASE_ORDER:
            if phase not in self.results:
                continue
            res = self.results[phase]
            if phase == "full suite":
                passed = jc["tests"] - jc["failures"] - jc["errors"] - jc["skipped"] - jc["xfailed"]
                res += (f" — {passed:,} passed / {jc['failures']:,} failed / {jc['errors']:,} errors / "
                        f"{jc['skipped']:,} skipped / {jc['xfailed']:,} xfailed(計 {jc['tests']:,})")
            lines.append(f"| {phase} | {res} | {_fmt_dur(self.timings.get(phase, 0))} |")
        lines.append(f"| 合計(準備を含む) | | {_fmt_dur(total)} |")
        dup = self.gate_time_in_full(self.out / "junit-full.xml")
        if dup is not None:
            lines += ["", f"門は全数でも回している(範囲を減らさないため)。全数の中で門のテストに掛かった時間の和 = "
                          f"{_fmt_dur(dup)}(テストごとの和。並列なので壁時計の増分はおよそこれを並列数で割った量)。"]
        skipped = [p for p in PHASE_ORDER if p not in self.results]
        if self.stopped_at and skipped:
            lines += ["", f"**{self.stopped_at} が落ちたので止めた**(回さなかった段: {'、'.join(skipped)}。"
                          "最後まで回すなら --keep-going)。"]
        if crash:
            lines += ["", f"**途中で止まった**: {crash}"]
        gj = self.junit_counts(self.out / "junit-gates.xml")
        if gj["failed"]:
            lines += ["", f"落ちた門({len(gj['failed'])}):", ""] + [f"- `{n}`" for n in gj["failed"][:40]]
        if jc["failed"]:
            lines += ["", f"落ちたテスト({len(jc['failed'])}):", ""]
            lines += [f"- `{n}`" for n in jc["failed"][:80]]
            if len(jc["failed"]) > 80:
                lines.append(f"- ほか {len(jc['failed']) - 80} 件(junit-full.xml)")
        lines += ["", "GitHub CI との違い: 並列(CI の片の中は直列)、py3.11 だけ、"
                  + ("" if self.args.cov else "--cov なし、") + "依存は venv を揃えた時点の版。"]
        text = "\n".join(lines) + "\n"
        (self.out / "summary.md").write_text(text, encoding="utf-8")
        (self.out / "result.json").write_text(json.dumps({
            "meta": m, "timings": self.timings, "results": self.results, "junit": {
                k: v for k, v in jc.items() if k != "skipped_names"}, "skipped": jc["skipped_names"],
            "workers": self.args.workers, "dist": self.args.dist, "total": total, "crash": crash},
            ensure_ascii=False, indent=1), encoding="utf-8")
        ok = not crash and not self.stopped_at and all(v.startswith("ok") for v in self.results.values())
        return 0 if ok else 1

    def main(self) -> int:
        t0 = time.time()
        self.setup_notes: list[str] = []
        self.stopped_at: str | None = None
        crash = None
        try:
            missing = self.apt_check()
            if missing:
                self.setup_notes.append(f"apt パッケージが無い(入れられなかった): {', '.join(missing)}")
            ts = time.time()
            self.sync_repo()
            self.timings["sync"] = time.time() - ts
            only = self.args.only
            plan = [("ruff", "ruff", self.phase_ruff, "ruff"),
                    ("regen", "regen_all --check", self.phase_regen, "regen_all --check"),
                    ("gates", "門", self.phase_gates, "門"),
                    ("core", "core", self.phase_core, "core (numpy+scipy)"),
                    ("tests", "full suite", self.phase_tests, "full suite")]
            for key, label, fn, result_key in plan:
                if (only and key != only) or key in self.args.skip:
                    continue
                self.clean_tree()
                fn()
                if key != "tests" and not self.results[result_key].startswith("ok") and not self.args.keep_going:
                    self.stopped_at = label
                    break
        except Exception as exc:  # noqa: BLE001 — 要約に残して非 0 で終わる
            crash = f"{type(exc).__name__}: {exc}"
            _log(crash)
        return self.write_summary(time.time() - t0, crash)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref", default="HEAD", help="検査する commit(既定 HEAD。作業木の未 commit 変更は含まない)")
    ap.add_argument("--out", help="要約・JUnit・ログの置き場(既定 = 一時ディレクトリ)")
    ap.add_argument("--distro", default=DEFAULT_DISTRO, help="WSL のディストリ(Windows のとき)")
    ap.add_argument("-n", "--workers", type=int, default=int(os.environ.get("FULLSEYE_CI_LOCAL_WORKERS", "12")),
                    help="pytest-xdist の並列数(既定 12。1 で直列)")
    ap.add_argument("--dist", default="worksteal", choices=["load", "loadfile", "loadscope", "worksteal"],
                    help="xdist の配り方(既定 worksteal。load は重いテストが 1 ワーカーに溜まり、"
                         "2026-11-10 の実測で全数が 35m47s → 約 20 分)")
    ap.add_argument("--only", choices=["ruff", "regen", "gates", "core", "tests"], help="1 段だけ回す")
    ap.add_argument("--skip", action="append", default=[], choices=["ruff", "regen", "gates", "core", "tests"],
                    help="この段を飛ばす(何度でも)")
    ap.add_argument("--keep-going", action="store_true",
                    help="前の段(ruff・regen・門・core)が落ちても最後まで回す(全数の結果が要るとき)")
    ap.add_argument("--cov", action="store_true", help="CI と同じく --cov を付ける(遅くなる)")
    ap.add_argument("--rebuild", action="store_true", help="venv を作り直す")
    ap.add_argument("--refresh-hours", type=float, default=24.0,
                    help="これより古い venv は依存をその日の最新に揃え直す(CI は毎回最新を入れる)")
    ap.add_argument("--python", help="venv を作る Python 3.11(既定 = python3.11 か uv)")
    ap.add_argument("--inside", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--source", help=argparse.SUPPRESS)
    ap.add_argument("--meta", help=argparse.SUPPRESS)
    ap.add_argument("pytest_args", nargs="*", help="pytest に渡す追加の引数(`--` の後ろ)")
    args = ap.parse_args(argv)
    if args.inside:
        return Inner(args).main()
    # 外側 → 内側へは、外側だけの引数を除いて渡す
    passthrough: list[str] = []
    skip_next = False
    for i, a in enumerate(argv):
        if skip_next:
            skip_next = False
            continue
        if a in ("--ref", "--out", "--distro"):
            skip_next = True
            continue
        if a.startswith(("--ref=", "--out=", "--distro=")):
            continue
        passthrough.append(a)
    return _host_main(args, passthrough)


if __name__ == "__main__":
    sys.exit(main())
