# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""``fullseye setup`` — 対話的な初期設定(環境を調べ、1 問ずつ聞いて、やったことと次の一手を出す)。

``pip install fullseye`` の後に「何をすれば使えるのか」が分からない、という声への答え。標準ライブラリだけで動く
(``input()`` と ``subprocess``)。

* まず環境を調べて表示する(doctor): Python / fullseye / Qt / 任意依存 / Claude Code の RAG skill と MCP。
* 次に 1 問ずつ聞く(Enter で既定): 用途 → Studio の登録 → 足りない依存 → AI 連携 → (最後に)Studio を開くか。
  pip は**実行するコマンドを見せてから**走らせる。黙って入れない。
* ``--yes`` は全部既定で無人実行(窓は開かない)、``--dry-run`` は何も変えず予定だけ表示。
  標準入力が端末でなく ``--yes`` / ``--dry-run`` も無いときは、質問せず案内だけ出して終了コード 0
  (CI やパイプで止まらない)。
* 表示は日本語 / 英語(ロケールで選び、``--lang`` か環境変数 ``FULLSEYE_LANG`` で上書き)。
"""
from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

from fullseye.license_policy import STRONG_COPYLEFT_EXTRAS

# (extra 名, import 名, pip の配布名, 説明 ja, 説明 en) — pyproject の extras と対応。
PROBES = [
    ("gui", "PySide6", "PySide6-Essentials", "Studio の画面(標準で導入)", "Studio GUI (installed by default)"),
    ("opencv", "cv2", "opencv-python", "OpenCV 系の op / 画像 I/O", "OpenCV ops / image I/O"),
    ("skimage", "skimage", "scikit-image", "scikit-image 系の op", "scikit-image ops"),
    ("pil", "PIL", "Pillow", "Pillow(画像の読み書き)", "Pillow (image read/write)"),
    ("wavelets", "pywt", "PyWavelets", "ウェーブレット", "wavelets"),
    ("gpu", "torch", "torch", "GPU / torch 系", "GPU / torch ops"),
    ("kornia", "kornia", "kornia", "torch 画像演算", "torch image ops"),
    ("cupy", "cupy", "cupy-cuda12x", "CUDA 配列", "CUDA arrays"),
    ("video", "imageio", "imageio", "動画入出力", "video I/O"),
    ("volume", "SimpleITK", "SimpleITK", "医用ボリューム入力", "volumetric import"),
    ("xlsx", "openpyxl", "openpyxl", "Excel レポート", "Excel reports"),
    ("gi", "mitsuba", "mitsuba", "大域照明レンダリング", "global-illumination rendering"),
    ("extra", "SimpleITK", "SimpleITK", "医用画像・追加画像処理", "medical imaging / extra image ops"),
    ("mahotas", "mahotas", "mahotas", "追加画像処理", "extra image ops"),
    ("handpose", "mediapipe", "mediapipe", "手の姿勢推定", "hand-pose estimation"),
    ("e57", "pye57", "pye57", "E57 点群入出力", "E57 point-cloud I/O"),
    ("astropy", "astropy", "astropy", "天文 FITS 検証", "astronomy/FITS verification"),
    ("plyfile", "plyfile", "plyfile", "PLY 検証用 reader", "PLY verification reader"),
]
# importlib.metadata で取れないとき(checkout 直読みなど)の代替。
_FALLBACK_REQ = {
    "opencv": ["opencv-python>=4.8.1.78"],
    "wavelets": ["PyWavelets>=1.4"],
    "gpu": ["torch>=2.13", "kornia>=0.9", "cupy-cuda12x>=14; platform_system != 'Darwin'"],
    "gi": ["mitsuba>=3.5"],
    "extra": ["mahotas>=1.4", "SimpleITK>=2.2"],
    "handpose": ["mediapipe>=0.10"],
    "volume": ["SimpleITK>=2.2"],
    "e57": ["pye57>=0.4"],
    "export-verify": ["pye57>=0.4", "astropy>=7.0", "plyfile>=1.0"],
}
# 用途ごとの「入れておくと良い」軽い extras(torch / GPU は重いので勧めない。報告だけする)。
RECOMMENDED = {"studio": [], "python": ["opencv", "skimage"], "ai": []}

# ``fullseye setup`` の既定は「可能な限り全部入り」。一括の ``pip install
# fullseye[all]`` は、1 個の OS/Python 非対応 wheel が失敗した時に残りまで巻き込んで
# 止まる。そのため extra ごとに独立した pip を走らせ、成功・失敗・CUDA 不在を最後に表で
# 出す。size_mb は 2026-11-24 に PyPI の各 direct wheel から読んだ最大ダウンロード量の
# 目安(依存先の合計ではない)。
# The groups deliberately isolate failures: one unavailable wheel must not stop later
# extras.  ``size_mb`` is the measured largest direct wheel, not transitive size.
FULL_SETUP_GROUPS = (
    ("opencv", 80), ("wavelets", 5), ("gpu", 540), ("gi", 70),
    ("extra", 55), ("handpose", 45), ("volume", 55), ("e57", 20),
)
# GPL を含む検証専用 extra は、既定の全導入から外して明示指定だけを許す。
# A GPL-bearing verification extra is explicit opt-in, never part of default all-in setup.
RESTRICTED_SETUP_GROUPS = (("export-verify", 30),)

M = {
    "ja": {
        "hdr": "== Fullseye セットアップ ==",
        "env": "[環境]",
        "py": "Python",
        "fs": "fullseye",
        "qt": "Studio(Qt)",
        "qt_ok": "開けます(PySide6 %s)",
        "qt_no_dep": "開けません: 標準依存の PySide6-Essentials が見つかりません(Fullseye を再インストールしてください)",
        "qt_no_display": "PySide6 は有りますが、画面(DISPLAY)がありません",
        "opt": "[任意の依存]",
        "have": "あり",
        "miss": "なし",
        "ai": "[AI 連携]",
        "skill_yes": "Claude Code の RAG skill: 登録済み",
        "skill_no": "Claude Code の RAG skill: 未登録",
        "mcp_yes": "MCP: 登録済み(Claude の設定に fullseye あり)",
        "mcp_no": "MCP: 未登録",
        "sc": "[ショートカット]",
        "sc_yes": "Studio: 登録済み",
        "sc_no": "Studio: 未登録",
        "sc_na": "このOSはメニュー登録に対応していません",
        "q_use": "何に使いますか? 1=Studio で触る  2=Python から使う  3=AI から使う (複数可、既定=全部)",
        "q_sc": "Studio をスタートメニュー(アプリ一覧)に登録しますか?",
        "q_desktop": "デスクトップにも置きますか?",
        "q_dep": "足りない任意依存を可能な限り全部入れますか? (%s)",
        "q_rag": "Claude Code に fullseye の RAG skill を登録しますか? (~/.claude/skills)",
        "q_open": "いま Studio を開きますか?",
        "cmd": "実行するコマンド:",
        "plan": "[予定]",
        "dry": "(--dry-run: 何も変更していません)",
        "done_hdr": "[やったこと]",
        "next_hdr": "[次の一手]",
        "nothing": "(変更なし)",
        "p_dep": "依存を入れる: %s",
        "p_sc": "Studio をメニューに登録する(%s)",
        "p_rag": "RAG skill を登録する(%s)",
        "did_dep": "依存を入れた: %s",
        "fail_dep": "依存の導入に失敗(終了コード %s)。上のコマンドを手で実行してください",
        "did_sc": "Studio を登録: %s",
        "fail_sc": "Studio の登録に失敗: %s",
        "did_rag": "RAG skill を登録: %s",
        "fail_rag": "RAG skill の登録に失敗: %s",
        "did_open": "Studio を起動した",
        "fail_open": "Studio の起動に失敗: %s",
        "skip_yes_open": "(--yes では窓を開きません。開くには fullseye-studio)",
        "mcp_ex": "MCP の設定(Claude Code):",
        "mcp_auto": "Claude Code が見つかったので MCP を登録する",
        "mcp_manual": "Claude Code が見つからないため、MCP の登録コマンドだけを表示する",
        "p_mcp": "MCP を登録する",
        "did_mcp": "MCP を登録した",
        "fail_mcp": "MCP の登録に失敗: %s",
        "pip_hdr": "[依存の導入予定] (各行は独立に実行します。サイズは direct wheel の目安)",
        "result_hdr": "[導入結果]",
        "skip_gpu": "GPU(CUDA)が見つからないため GPU extra を飛ばした",
        "skip_gpl": STRONG_COPYLEFT_EXTRAS["export-verify"]["reason_ja"],
        "gpu_note": "GPU(torch)は CUDA を検出した環境でだけ全部入りに含めます。",
        "next_studio": "Studio を開く: スタートメニューの Fullseye Studio、または  fullseye-studio",
        "next_py": "Python から: import fullseye; fullseye.apply(img, \"sobel_amp\")   (README の Quickstart)",
        "next_ai": "AI から: Claude Code を開いて画像処理の質問をする / fullseye-rag search \"ノイズ除去\"",
        "next_help": "コマンド一覧: fullseye --help    もう一度: fullseye setup",
        "noninter": "標準入力が端末でないため質問しません(案内だけ表示)。対話するには端末で fullseye setup、"
                    "無人なら fullseye setup --yes。",
        "bad": "もう一度入力してください(Enter で既定)",
        "g_head": "Fullseye へようこそ。 全部入れる: fullseye setup --yes",
        "g_title": "使い方の入口(次の 3 手):",
        "g_1": "1. Studio を開く(画面で触る)",
        "g_1b": "   スタートメニューに登録",
        "g_2": "2. Python から 3 行で使う",
        "g_3": "3. AI から使う(Claude Code など)",
        "g_tail": "コマンド一覧: fullseye --help    演算子を探す: fullseye ops --search edge    (English: FULLSEYE_LANG=en)",
    },
    "en": {
        "hdr": "== Fullseye setup ==",
        "env": "[Environment]",
        "py": "Python",
        "fs": "fullseye",
        "qt": "Studio (Qt)",
        "qt_ok": "can open (PySide6 %s)",
        "qt_no_dep": "cannot open: the required PySide6-Essentials is missing (reinstall fullseye)",
        "qt_no_display": "PySide6 is installed but there is no display (DISPLAY)",
        "opt": "[Optional dependencies]",
        "have": "yes",
        "miss": "no",
        "ai": "[AI integration]",
        "skill_yes": "Claude Code RAG skill: registered",
        "skill_no": "Claude Code RAG skill: not registered",
        "mcp_yes": "MCP: registered (fullseye is in the Claude settings)",
        "mcp_no": "MCP: not registered",
        "sc": "[Shortcuts]",
        "sc_yes": "Studio: registered",
        "sc_no": "Studio: not registered",
        "sc_na": "menu shortcuts are not supported on this OS",
        "q_use": "What will you use it for? 1=Studio (GUI)  2=from Python  3=from an AI (several ok; default=all)",
        "q_sc": "Add Studio to the Start menu / application menu?",
        "q_desktop": "Also put it on the desktop?",
        "q_dep": "Install every available optional dependency? (%s)",
        "q_rag": "Register the fullseye RAG skill with Claude Code? (~/.claude/skills)",
        "q_open": "Open Studio now?",
        "cmd": "Command to run:",
        "plan": "[Plan]",
        "dry": "(--dry-run: nothing was changed)",
        "done_hdr": "[What was done]",
        "next_hdr": "[Next steps]",
        "nothing": "(no changes)",
        "p_dep": "install dependencies: %s",
        "p_sc": "register Studio in the menu (%s)",
        "p_rag": "register the RAG skill (%s)",
        "did_dep": "installed dependencies: %s",
        "fail_dep": "dependency install failed (exit code %s). Run the command above by hand",
        "did_sc": "registered Studio: %s",
        "fail_sc": "could not register Studio: %s",
        "did_rag": "registered the RAG skill: %s",
        "fail_rag": "could not register the RAG skill: %s",
        "did_open": "started Studio",
        "fail_open": "could not start Studio: %s",
        "skip_yes_open": "(--yes never opens a window; run fullseye-studio to open it)",
        "mcp_ex": "MCP setup (Claude Code):",
        "mcp_auto": "Claude Code was found; register MCP",
        "mcp_manual": "Claude Code was not found; show the MCP command only",
        "p_mcp": "register MCP",
        "did_mcp": "registered MCP",
        "fail_mcp": "could not register MCP: %s",
        "pip_hdr": "[Dependency plan] (each row runs independently; size is a direct-wheel estimate)",
        "result_hdr": "[Installation results]",
        "skip_gpu": "skipped the GPU extra because CUDA was not detected",
        "skip_gpl": STRONG_COPYLEFT_EXTRAS["export-verify"]["reason_en"],
        "gpu_note": "GPU (torch) is included only when CUDA is detected.",
        "next_studio": "Open Studio: 'Fullseye Studio' in the Start menu, or  fullseye-studio",
        "next_py": "From Python: import fullseye; fullseye.apply(img, \"sobel_amp\")   (README Quickstart)",
        "next_ai": "From an AI: open Claude Code and ask an image-processing question / fullseye-rag search \"remove noise\"",
        "next_help": "All commands: fullseye --help    Run again: fullseye setup",
        "noninter": "stdin is not a terminal, so no questions are asked (guidance only). For the interactive flow run "
                    "fullseye setup in a terminal; for unattended use fullseye setup --yes.",
        "bad": "Please try again (Enter for the default)",
        "g_head": "Welcome to Fullseye. Install everything: fullseye setup --yes",
        "g_title": "Where to start (next 3 steps):",
        "g_1": "1. Open Studio (the GUI)",
        "g_1b": "   Add it to the Start menu",
        "g_2": "2. Use it from Python in 3 lines",
        "g_3": "3. Use it from an AI (Claude Code etc.)",
        "g_tail": "All commands: fullseye --help    Find an operator: fullseye ops --search edge    (Japanese: FULLSEYE_LANG=ja)",
    },
}


# --------------------------------------------------------------------------- 言語
def detect_lang(env: Optional[Dict[str, str]] = None, override: Optional[str] = None) -> str:
    """ja / en。引数 > FULLSEYE_LANG > OS の表示言語 > LANG 系の環境変数。"""
    e = os.environ if env is None else env
    for v in (override, e.get("FULLSEYE_LANG")):
        if v and v.lower()[:2] in ("ja", "en"):
            return v.lower()[:2]
    if sys.platform == "win32" and env is None:
        try:
            import ctypes
            if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0xFF == 0x11:     # LANG_JAPANESE
                return "ja"
            return "en"
        except Exception:
            pass
    for k in ("LC_ALL", "LC_MESSAGES", "LANG"):
        if (e.get(k) or "").lower().startswith("ja"):
            return "ja"
    return "en"


def guidance(lang: str) -> str:
    """引数なしの ``fullseye`` と、非端末の ``fullseye setup`` が出す案内。"""
    m = M[lang]
    exe = sys.executable
    return "\n".join([
        m["g_head"], "", m["g_title"],
        "  " + m["g_1"], "      fullseye-studio",
        "  " + m["g_1b"], "      fullseye-studio --install-shortcuts   (+ --desktop)",
        "  " + m["g_2"], "      import fullseye, numpy as np",
        "      img = np.random.rand(64, 64)",
        "      print(fullseye.apply(img, \"sobel_amp\").shape)",
        "  " + m["g_3"], "      fullseye-rag     |     claude mcp add fullseye -- \"%s\" -P -m fullseye.mcp" % exe,
        "", m["g_tail"], ""])


# --------------------------------------------------------------------------- doctor
def _has(mod: str) -> bool:
    try:
        return importlib.util.find_spec(mod) is not None
    except (ImportError, ValueError):
        return False


def _path_executable(name: str) -> Optional[str]:
    """PATH の絶対ディレクトリだけから実行物を探す(cwd は探索しない) / search absolute PATH entries only."""
    names = [name]
    if sys.platform == "win32" and not Path(name).suffix:
        names += [name + ext.lower() for ext in os.environ.get("PATHEXT", ".EXE;.CMD;.BAT").split(";") if ext]
    for raw in os.environ.get("PATH", "").split(os.pathsep):
        if not raw:
            continue
        base = Path(raw)
        if not base.is_absolute():
            continue
        for candidate_name in names:
            candidate = base / candidate_name
            try:
                if candidate.is_file() and (sys.platform == "win32" or os.access(candidate, os.X_OK)):
                    return str(candidate)
            except OSError:
                pass
    return None


def _ver(dist: str) -> str:
    try:
        return importlib.metadata.version(dist)
    except importlib.metadata.PackageNotFoundError:
        return ""


def _mcp_registered(home: Path) -> bool:
    """Claude Code の設定(~/.claude.json)の mcpServers に fullseye があるか(読めなければ False)。"""
    try:
        data = json.loads((home / ".claude.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False

    def has(d) -> bool:
        return isinstance(d, dict) and any("fullseye" in str(k).lower() for k in (d.get("mcpServers") or {}))
    if has(data):
        return True
    return any(has(v) for v in (data.get("projects") or {}).values())


def collect_env(home: Optional[Path] = None) -> Dict[str, object]:
    """環境の事実を集める(``fullseye doctor`` 相当。何も変更しない)。"""
    home = home or Path.home()
    info: Dict[str, object] = {"python": sys.version.split()[0], "executable": sys.executable,
                               "venv": sys.prefix != getattr(sys, "base_prefix", sys.prefix)}
    try:
        import fullseye
        info["fullseye"] = fullseye.version()
    except Exception as e:      # noqa: BLE001 — 版が取れないことは報告に回す
        info["fullseye"] = "?(%s)" % type(e).__name__
    probes = {}
    for extra, mod, dist, *_ in PROBES:
        probes[extra] = {"installed": _has(mod), "version": _ver(dist) if _has(mod) else ""}
    info["probes"] = probes
    qt = probes["gui"]["installed"]
    display = sys.platform in ("win32", "darwin") or bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
                                                          or os.environ.get("QT_QPA_PLATFORM"))
    info["qt"] = "ok" if qt and display else ("no_display" if qt else "no_dep")
    try:
        from fullseye import rag_setup
        info["skill"] = (rag_setup.default_target() / rag_setup.SKILL_NAME).exists()
    except Exception:           # noqa: BLE001
        info["skill"] = False
    info["mcp"] = _mcp_registered(home)
    info["claude"] = _path_executable("claude") is not None
    try:
        from fullseye import shortcuts as sc
        plat = sc._platform()
        if plat == "win":
            info["shortcut"] = (sc.windows_dirs()["start_menu"] / (sc.APP_NAME + ".lnk")).is_file()
        elif plat == "linux":
            info["shortcut"] = (sc._xdg_data() / "applications" / "fullseye-studio.desktop").is_file()
        else:
            info["shortcut"] = None
    except Exception:           # noqa: BLE001
        info["shortcut"] = None
    return info


def format_report(info: Dict[str, object], lang: str) -> str:
    m = M[lang]
    L = [m["hdr"], "", m["env"],
         "  %-12s %s  (%s%s)" % (m["py"], info["python"], info["executable"], ", venv" if info["venv"] else ""),
         "  %-12s %s" % (m["fs"], info["fullseye"])]
    pr = info["probes"]
    if info["qt"] == "ok":
        L.append("  %-12s %s" % (m["qt"], m["qt_ok"] % (pr["gui"]["version"] or "?")))
    else:
        L.append("  %-12s %s" % (m["qt"], m["qt_no_display"] if info["qt"] == "no_display" else m["qt_no_dep"]))
    L += ["", m["opt"]]
    for extra, _mod, dist, ja, en in PROBES:
        p = pr[extra]
        L.append("  %-14s %-4s %s" % (dist, m["have"] if p["installed"] else m["miss"],
                                      (p["version"] + "  " if p["version"] else "") + (ja if lang == "ja" else en)))
    L += ["", m["ai"], "  " + (m["skill_yes"] if info["skill"] else m["skill_no"]),
          "  " + (m["mcp_yes"] if info["mcp"] else m["mcp_no"]), "", m["sc"]]
    sc = info["shortcut"]
    L.append("  " + (m["sc_na"] if sc is None else (m["sc_yes"] if sc else m["sc_no"])))
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- pip
def requirements_for(extras: Sequence[str]) -> List[str]:
    """extras に対応する任意要件(``opencv-python>=4.8.1.78`` など)。fullseye 自身は入れ直さない。"""
    out: List[str] = []
    try:
        reqs = importlib.metadata.requires("fullseye") or []
    except importlib.metadata.PackageNotFoundError:
        reqs = []
    for x in extras:
        if x in ("gui", "pil"):           # standard dependencies; these remain only as pip compatibility aliases
            continue
        found = []
        for r in reqs:
            if ";" in r:
                spec, marker = r.split(";", 1)
                # Keep platform markers (notably cupy on non-macOS) while making
                # the extra predicate true for this direct pip invocation.
                if re.search(r"\bextra\s*==\s*['\"]%s['\"]" % re.escape(x), marker):
                    clean = re.sub(r"\bextra\s*==\s*['\"]%s['\"]" % re.escape(x),
                                   "python_version >= '0'", marker)
                    found.append(spec.strip() + ";" + clean.strip())
        # editable install は pyproject 編集前の metadata を残しうる。チェックインした
        # fallback も併合し、古い metadata で明示 setup の依存を落とさない。
        # Editable installs can retain metadata from before a local pyproject edit;
        # merge the checked-in fallback so an explicit plan omits no declared package.
        for r in [*found, *_FALLBACK_REQ.get(x, [])]:
            if r not in out:
                out.append(r)
    return out


def pip_command(reqs: Sequence[str]) -> List[str]:
    return [sys.executable, "-m", "pip", "install", *reqs]


_GROUP_PROBES = {
    "opencv": ("opencv",), "wavelets": ("wavelets",),
    "gpu": ("gpu", "kornia", "cupy"), "gi": ("gi",),
    "extra": ("extra", "mahotas"), "handpose": ("handpose",),
    "volume": ("volume",), "e57": ("e57",), "export-verify": ("e57", "astropy", "plyfile"),
}


def cuda_available() -> bool:
    """CUDA を使えるときだけ GPU extra を予定に入れる。

    torch を import して初回セットアップを重くしない。NVIDIA の公式 CLI が応答した
    場合だけ True にするので、判定できない環境で巨大な GPU wheel を始めない。
    Return true only when ``nvidia-smi`` proves a CUDA GPU is usable; do not import torch.
    """
    exe = _path_executable("nvidia-smi")
    if not exe:
        return False
    try:
        return subprocess.run([exe, "--query-gpu=name", "--format=csv,noheader"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              timeout=5, check=False).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def planned_dependency_groups(info: Dict[str, object], *, has_cuda: Optional[bool] = None,
                              include: Sequence[str] = ()) -> List[tuple[str, int, List[str]]]:
    """未導入の全部入り extra を単位で返す / return missing all-in groups without propagating failures."""
    has_cuda = cuda_available() if has_cuda is None else has_cuda
    probes = info.get("probes", {})
    groups = []
    groups_to_consider = FULL_SETUP_GROUPS + tuple(
        group for group in RESTRICTED_SETUP_GROUPS if group[0] in set(include))
    for extra, size_mb in groups_to_consider:
        if extra == "gpu" and not has_cuda:
            continue
        names = _GROUP_PROBES[extra]
        missing = any(not bool((probes.get(name) or {}).get("installed")) for name in names)
        reqs = requirements_for([extra])
        if missing and reqs:
            groups.append((extra, size_mb, reqs))
    return groups


def full_install_ready(info: Optional[Dict[str, object]] = None, *, has_cuda: Optional[bool] = None) -> bool:
    """既定の全部入りが済んでいるか / whether environment-possible extras plus RAG are complete."""
    info = collect_env() if info is None else info
    if planned_dependency_groups(info, has_cuda=has_cuda):
        return False
    return bool(info.get("skill")) and (not info.get("claude") or bool(info.get("mcp")))


def full_install_hint(lang: str, info: Optional[Dict[str, object]] = None) -> str:
    """初回 CLI/Studio に 1 行だけ出す安全な全部入りコマンド / one safe one-line all-in command."""
    if full_install_ready(info):
        return ""
    return "fullseye setup --yes"


def _has_fullseye_mcp_script() -> bool:
    """別便の console script を優先する / prefer the safe console entry point when it is installed."""
    try:
        eps = importlib.metadata.distribution("fullseye").entry_points
        return any(e.group == "console_scripts" and e.name == "fullseye-mcp" for e in eps)
    except importlib.metadata.PackageNotFoundError:
        return False


def mcp_add_command() -> Optional[List[str]]:
    """Claude Code 用の安全な MCP 登録コマンド / never import a cwd ``fullseye/`` directory."""
    claude = _path_executable("claude")
    if not claude:
        return None
    target = ["fullseye-mcp"] if _has_fullseye_mcp_script() else [sys.executable, "-P", "-m", "fullseye.mcp"]
    return [claude, "mcp", "add", "fullseye", "--", *target]


def _default_run(cmd: List[str]) -> int:
    return subprocess.call(cmd)


def _default_launch() -> None:
    exe = sys.executable
    kw: Dict[str, object] = {}
    if sys.platform == "win32":
        w = Path(exe).with_name("pythonw.exe")
        exe = str(w) if w.is_file() else exe
        kw["creationflags"] = 0x00000008 | 0x00000200       # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    from fullseye import shortcuts
    # -P: 作業フォルダ(sys.path[0])を足さない = ホームに置かれた別の studio.py を先に読まない。作業フォルダも setup フォルダ。
    subprocess.Popen([exe, "-P", "-m", "studio"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, cwd=str(shortcuts.launch_workdir()), **kw)


def _default_rag() -> str:
    from fullseye import rag_setup
    dest = rag_setup.install(rag_setup.default_target(), repo=rag_setup.find_repo(), _auto_repo=False)
    from fullseye import shortcuts
    shortcuts.ledger_record("claude_skill", dest)        # 消すときの台帳(推測で消さない)
    return str(dest)


def _default_shortcuts(desktop: bool) -> List[str]:
    from fullseye import shortcuts
    return [str(p) for p in shortcuts.install(desktop=desktop)]


def _stdin_is_terminal() -> bool:
    """標準入力が本物の端末か。Windows では NUL()も isatty() が True を返すので、
    GetConsoleMode で本当のコンソールかを確かめる(NUL を端末と誤認して質問・登録に進まないため)。"""
    if not (sys.stdin and sys.stdin.isatty()):
        return False
    if sys.platform == "win32":
        import ctypes
        import msvcrt
        h = msvcrt.get_osfhandle(sys.stdin.fileno())
        mode = ctypes.c_uint32()
        return bool(ctypes.windll.kernel32.GetConsoleMode(ctypes.c_void_p(h), ctypes.byref(mode)))
    return True


# --------------------------------------------------------------------------- 本体
def main(argv: Optional[Sequence[str]] = None, *, input_fn: Optional[Callable[[str], str]] = None,
         run_fn: Optional[Callable[[List[str]], int]] = None, launch_fn: Optional[Callable[[], None]] = None,
         rag_fn: Optional[Callable[[], str]] = None, shortcuts_fn: Optional[Callable[[bool], List[str]]] = None,
         mcp_fn: Optional[Callable[[List[str]], int]] = None, cuda_fn: Optional[Callable[[], bool]] = None,
         is_tty: Optional[bool] = None, out=None, info: Optional[Dict[str, object]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--uninstall" in argv:           # 後始末は fullseye/uninstall.py(台帳に載った物だけを消す)
        from fullseye import uninstall
        return uninstall.main(argv)
    ap = argparse.ArgumentParser(prog="fullseye setup", description="Interactive first-time setup for Fullseye.")
    ap.add_argument("--uninstall", action="store_true",
                    help="remove what setup created (shortcuts, Claude skill, 'Apps & features' entry); asks about "
                         "settings/cache and pip uninstall. Combine with --yes / --dry-run")
    ap.add_argument("--lang", choices=["ja", "en"], default=None, help="ja / en (default: from the locale)")
    ap.add_argument("--yes", "-y", action="store_true", help="accept every default, unattended (never opens a window)")
    ap.add_argument("--dry-run", "-n", action="store_true", help="show the plan only; change nothing")
    ap.add_argument("--include", action="append", choices=sorted(STRONG_COPYLEFT_EXTRAS), default=[],
                    help="explicitly include a restricted extra (for example: export-verify includes GPL-3.0 plyfile)")
    args = ap.parse_args(argv)
    out = out or sys.stdout
    try:
        out.reconfigure(errors="replace")       # cp932 の端末でも落ちない
    except Exception:       # noqa: BLE001
        pass
    lang = detect_lang(override=args.lang)
    m = M[lang]
    input_fn = input_fn or input
    run_fn = run_fn or _default_run
    launch_fn = launch_fn or _default_launch
    rag_fn = rag_fn or _default_rag
    shortcuts_fn = shortcuts_fn or _default_shortcuts
    mcp_fn = mcp_fn or _default_run
    cuda_fn = cuda_fn or cuda_available
    if is_tty is None:
        try:
            is_tty = _stdin_is_terminal()
        except Exception:       # noqa: BLE001
            is_tty = False

    def say(s: str = "") -> None:
        print(s, file=out)

    info = info or collect_env()
    say(format_report(info, lang))
    auto = args.yes or args.dry_run
    if not is_tty and not auto:
        say(m["noninter"])
        say()
        say(guidance(lang))
        return 0
    interactive = is_tty and not args.yes and not args.dry_run

    def ask(q: str, default: str) -> str:
        if not interactive:
            say("%s  -> %s" % (q, default))
            return default
        try:
            ans = input_fn("%s [%s] " % (q, default)).strip()
        except EOFError:
            return default
        return ans or default

    def yn(q: str, default: bool) -> bool:
        for _ in range(3):
            a = ask(q + (" (Y/n)" if default else " (y/N)"), "Y" if default else "N").lower()
            if a in ("y", "yes", "はい", "ｙ"):
                return True
            if a in ("n", "no", "いいえ", "ｎ"):
                return False
            say(m["bad"])
        return default

    # (1) 用途
    uses: List[str] = []
    for _ in range(3):
        raw = ask(m["q_use"], "1,2,3")
        picked = {"1": "studio", "2": "python", "3": "ai"}
        toks = [t for t in re.split(r"[,\s、]+", raw) if t]
        if toks and all(t in picked for t in toks):
            uses = [picked[t] for t in dict.fromkeys(toks)]
            break
        say(m["bad"])
    uses = uses or ["studio", "python", "ai"]

    plat_ok = info["shortcut"] is not None
    do_sc = do_desktop = False
    if "studio" in uses and plat_ok:
        do_sc = yn(m["q_sc"], True)
        if do_sc:
            do_desktop = yn(m["q_desktop"], False)

    has_cuda = bool(cuda_fn())
    groups = planned_dependency_groups(info, has_cuda=has_cuda, include=args.include) if "python" in uses else []
    do_pip = False
    if groups:
        say()
        say(m["pip_hdr"])
        for extra, size_mb, reqs in groups:
            cmd = pip_command(reqs)
            shown = " ".join('"%s"' % c if re.search(r"[<>= ;]", c) else c for c in cmd)
            say("  %-14s ~%s MiB  %s" % (extra, size_mb, shown))
        if not has_cuda:
            say("  %-14s %-7s %s" % ("gpu", "skip", m["skip_gpu"]))
        do_pip = yn(m["q_dep"] % ", ".join(x[0] for x in groups), True)
    if "python" in uses and "export-verify" not in args.include:
        # GPL を含む extra は既定から除く理由と明示の戻し方を、実行前にも必ず示す。
        # Explain both the GPL exclusion and the explicit opt-in before any pip command runs.
        say("  export-verify skip    " + m["skip_gpl"])

    do_rag = False
    if "ai" in uses:
        do_rag = (not info["skill"]) and yn(m["q_rag"], True)
    # Tests and embedders must explicitly report Claude Code as present; never let a
    # host executable turn a fake setup run into a real ~/.claude.json mutation.
    mcp_cmd = mcp_add_command() if "ai" in uses and not info["mcp"] and info.get("claude", False) else None

    plan = []
    if do_pip:
        plan.append(m["p_dep"] % ", ".join(x[0] for x in groups))
    if do_sc:
        plan.append(m["p_sc"] % ("menu + desktop" if do_desktop else "menu"))
    if do_rag:
        plan.append(m["p_rag"] % "~/.claude/skills")
    if mcp_cmd:
        plan.append(m["p_mcp"])
    say()
    say(m["plan"])
    for p in plan or [m["nothing"]]:
        say("  - " + p)
    if args.dry_run:
        say(m["dry"])
        return 0

    done: List[str] = []
    failures = 0                        # 失敗した段の数(1 つでもあれば終了コードは 1)
    results: List[tuple[str, str, str]] = []
    if "python" in uses and not has_cuda:
        results.append(("gpu", "skipped", m["skip_gpu"]))
    if "python" in uses and "export-verify" not in args.include:
        results.append(("export-verify", "skipped", m["skip_gpl"]))
    if do_pip:
        for extra, _size_mb, reqs in groups:
            rc = run_fn(pip_command(reqs))
            if rc == 0:
                done.append(m["did_dep"] % extra)
                results.append((extra, "installed", ", ".join(reqs)))
            else:
                done.append(m["fail_dep"] % rc)
                results.append((extra, "failed", "exit code %s" % rc))
                failures += 1
    if do_sc:
        try:
            made = shortcuts_fn(do_desktop)
            done.append(m["did_sc"] % ", ".join(made))
        except Exception as e:      # noqa: BLE001 — 理由を文にして続行
            done.append(m["fail_sc"] % e)
            failures += 1
    if do_rag:
        try:
            done.append(m["did_rag"] % rag_fn())
        except Exception as e:      # noqa: BLE001
            done.append(m["fail_rag"] % e)
            failures += 1
    if mcp_cmd:
        try:
            rc = mcp_fn(mcp_cmd)
            if rc == 0:
                done.append(m["did_mcp"])
                results.append(("mcp", "installed", " ".join(mcp_cmd)))
            else:
                done.append(m["fail_mcp"] % ("exit code %s" % rc))
                results.append(("mcp", "failed", "exit code %s" % rc))
                failures += 1
        except Exception as e:      # noqa: BLE001 -- do not stop other setup steps
            done.append(m["fail_mcp"] % e)
            results.append(("mcp", "failed", str(e)))
            failures += 1

    if "ai" in uses and not info["mcp"]:
        say()
        say(m["mcp_ex"])
        if mcp_cmd:
            say("  " + m["mcp_auto"])
            say("  " + " ".join(mcp_cmd))
        else:
            say("  " + m["mcp_manual"])
            say('  claude mcp add fullseye -- "%s" -P -m fullseye.mcp' % sys.executable)
            say('  {"mcpServers": {"fullseye": {"command": %s, "args": ["-P", "-m", "fullseye.mcp"]}}}'
                % json.dumps(sys.executable))

    if "studio" in uses:
        if args.yes:
            say()
            say(m["skip_yes_open"])
        elif yn(m["q_open"], True):
            try:
                launch_fn()
                done.append(m["did_open"])
            except Exception as e:      # noqa: BLE001
                done.append(m["fail_open"] % e)
                failures += 1

    say()
    if results:
        say(m["result_hdr"])
        say("  %-14s %-10s %s" % ("component", "result", "detail"))
        for name, status, detail in results:
            say("  %-14s %-10s %s" % (name, status, detail))
        say()
    say(m["done_hdr"])
    for d in done or [m["nothing"]]:
        say("  - " + d)
    say()
    say(m["next_hdr"])
    if "studio" in uses:
        say("  - " + m["next_studio"])
    if "python" in uses:
        say("  - " + m["next_py"])
    if "ai" in uses:
        say("  - " + m["next_ai"])
    say("  - " + m["next_help"])
    return 1 if failures else 0         # 0 = 選んだ段が全部できた(または何も選ばなかった)/ 1 = 失敗した段がある


if __name__ == "__main__":
    sys.exit(main())
