#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""動く 3-D(fs.viewer_anim3d_tab)の作例を 8 言語にする翻訳の層(ViEW2026 の入口ページ用)。

    py -3.11 tools/anim3d_i18n.py --check interactive_anim3d_viewer       # 門だけ(書かない)
    py -3.11 tools/anim3d_i18n.py --missing interactive_anim3d_viewer     # 未訳を JSON で(標準出力)
    py -3.11 tools/anim3d_i18n.py --missing interactive_anim3d_viewer --json-out todo.json
    py -3.11 tools/anim3d_i18n.py --build interactive_anim3d_viewer \\
        --out docs/view2026/anim3d/interactive_anim3d_viewer.html          # 8 言語の HTML を書く
    py -3.11 tools/anim3d_i18n.py --demo                                  # 走るサンプル(一時フォルダ)
    py -3.11 tools/anim3d_i18n.py --missing build_waves_anim3d --viewer-id interference   # tools/build_* も同じ
    py -3.11 tools/anim3d_i18n.py --check build_x_anim3d --script-arg=--seed --script-arg=3 # main(argv) に渡す

作例の名前は ``examples/<名前>.py`` → ``examples_3d/<名前>.py`` → ``tools/<名前>.py``(名前が ``build_`` で
始まるものだけ。``tools/build_*_anim3d.py`` のような題材の生成器)の順に探す。

作例の build スクリプトは **書き換えない**。作例は文字列を ``fs.viewer_text(ja, en)`` の 2 言語で書くので、
その ``main()`` を走らせ、``fs.write_viewer`` に渡った仕様(spec)を横取りする(作例自身の検査はそのまま走る)。
仕様の中の ja/en だけの文字列の辞書をすべて見つけ、翻訳表から zh / tw / ko / de / hi / fr を埋めて
8 言語の仕様にし、``write_viewer(..., lang=LANGS, detect_lang=True)`` で書く
(``?lang=xx`` が最優先、無ければブラウザの言語)。

横取りの間、``write_viewer`` は **要求されたパスに書かない**(一時フォルダに同じ名前で書いてそのパスを返す)。
``tools/build_*`` は既定で ``docs/anim3d/*.html`` を書くので、そのまま走らせると翻訳の確認だけで木が変わる。
それ以外の書き込みも塞ぐため、走らせる前後で ``git status`` の対象ファイルの中身を比べ、変わっていれば
止める(fail-closed。git の無い場所では比べない)。

翻訳表は作例ごとに 1 つ: ``tools/anim3d_i18n_tables/<作例名>.json``::

    {"_": "説明", "example": "<作例名>",
     "strings": {"<en の文字列そのもの>": {"ja": "<訳した時点の ja>", "zh": ..., "tw": ..., "ko": ...,
                                          "de": ..., "hi": ..., "fr": ...}}}

キーは en の文字列そのもの(en が変われば別の文字列 = 未訳)。``ja`` は訳した時点の日本語の控えで、
作例の ja が変われば「古い訳」として未訳と同じに扱う。

★fail-closed の門(1 つでも落ちれば何も書かない。理由を全部並べて止まる):
  * 表に無い文字列 / 6 言語のどれかが空 / ja の控えが今の ja と違う(古い訳)
  * 訳の中の **数値トークンの多重集合** が en と違う(整数・小数・指数、直後の単位 m / mm / µm / s / % /
    fps / MB … を含めて比べる。例: en "1.2 s" に対して "1.2 秒" は落ちる —— 数字・単位の古い訳を出さない)
  * en に在る **op 名・コード片**(``fs.xxx``・`` `…` ``・``name()``・snake_case・camelCase)が訳に
    そのまま残っていない
  * 表にあって仕様に無い文字列は「使われていない訳」として警告だけ出す(落とさない)。

数の穴のある文字列(``"光線 %d"`` を f-string で埋めたもの)は、埋めた後の文字列ごとに 1 行になる
(``"Ray 1"``・``"Ray 2"``…)。数字が変われば en が変わり、未訳として止まる。
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pocviewer as pv  # noqa: E402

LANGS = pv.LANGS
NEW_LANGS = tuple(l for l in LANGS if l not in ("ja", "en"))       # 表で埋める 6 言語
TABLES = ROOT / "tools" / "anim3d_i18n_tables"
EXAMPLE_DIRS = ("examples", "examples_3d")
#: 作例の外で探す生成器: ``tools/build_*.py``(題材の動く 3-D、``main(argv)`` を持ち write_viewer で書く)。
BUILDER_DIR, BUILDER_PREFIX = "tools", "build_"

#: 数値トークン: 整数・小数・指数 + 直後(空白 0〜1 個)の単位。符号は付けない(「2-10 cm」の - は範囲)。
#: 英字・_ に続く数字(``anim3d``・``uint16`` のような名前の一部)は数えない(コード片の門が見る)。
_UNITS = r"(?:µm|um|nm|mm|cm|km|ms|µs|kHz|MHz|Hz|fps|rad|deg|MB|KB|kB|GB|px|m|s|%|°)"
_NUM = re.compile(r"(?<![0-9.A-Za-z_])(\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)(?:[  ]?(" + _UNITS + r")(?![A-Za-zµ]))?")
#: op 名・コード片(en に在れば、訳にも同じ綴りで残すこと)。
_CODE = [re.compile(r"`[^`]+`"),
         re.compile(r"\bfs\.[A-Za-z_][\w.]*(?:\(\))?"),
         re.compile(r"\b[A-Za-z_]\w*\(\)"),
         re.compile(r"\b[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+\b"),
         re.compile(r"\b[a-z]+[A-Z][A-Za-z0-9]*\b")]


class GateError(ValueError):
    """門に落ちた(``problems`` に理由を全部)。"""

    def __init__(self, problems: list[str]) -> None:
        self.problems = list(problems)
        super().__init__("anim3d_i18n の門に落ちた(%d 件、何も書いていない):\n  %s"
                         % (len(problems), "\n  ".join(problems)))


# --------------------------------------------------------------------------- 文字列の取り出し
def num_tokens(s: str) -> Counter:
    """数値トークンの多重集合(``"1.2 s"`` → ``{"1.2s": 1}``)。"""
    return Counter(n + (u or "") for n, u in _NUM.findall(s))


def code_tokens(s: str) -> Counter:
    """op 名・コード片の多重集合。重なる候補(``fs.a_b`` と ``a_b``)は長い方だけ数える。"""
    spans: list[tuple[int, int]] = []
    for rx in _CODE:
        for m in rx.finditer(s):
            if not any(a <= m.start() and m.end() <= b for a, b in spans):
                spans = [(a, b) for a, b in spans if not (m.start() <= a and b <= m.end())]
                spans.append((m.start(), m.end()))
    return Counter(s[a:b] for a, b in spans)


def is_text(d: Any) -> bool:
    """言語ごとの文字列の辞書か(鍵が LANGS の部分集合で ja と en を含み、値が全部 str)。"""
    return (isinstance(d, dict) and d and set(d) <= set(LANGS) and "ja" in d and "en" in d
            and all(isinstance(v, str) for v in d.values()))


def iter_texts(obj: Any, where: str = "spec") -> Iterator[tuple[str, dict]]:
    """仕様の中の文字列の辞書を全部(場所つき)。numpy 配列などは辿らない。"""
    if is_text(obj):
        yield where, obj
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from iter_texts(v, "%s.%s" % (where, k))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from iter_texts(v, "%s[%d]" % (where, i))


def needs(d: dict) -> list[str]:
    """表で埋めるべき言語(既に作例が書いた言語は埋めない)。"""
    return [l for l in NEW_LANGS if not str(d.get(l, "")).strip()]


# --------------------------------------------------------------------------- 表と門
def table_path(example: str) -> Path:
    return TABLES / (example + ".json")


def load_table(example: str, path: Path | None = None) -> dict:
    p = path or table_path(example)
    if not p.is_file():
        return {"_": "", "example": example, "strings": {}}
    t = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(t.get("strings"), dict):
        raise GateError(["%s: strings が dict でない" % p])
    return t


def check_entry(en: str, ja: str, tr: dict | None, langs: list[str]) -> list[str]:
    """1 つの文字列の訳の問題(空なら合格)。"""
    if tr is None:
        return ["未訳"]
    bad = []
    if tr.get("ja") != ja:
        bad.append("古い訳(ja の控え %r ≠ 今の ja %r)" % (tr.get("ja"), ja))
    ref_n, ref_c = num_tokens(en), code_tokens(en)
    for l in langs:
        v = tr.get(l)
        if not isinstance(v, str) or not v.strip():
            bad.append("%s: 訳が空" % l)
            continue
        got = num_tokens(v)
        if got != ref_n:
            bad.append("%s: 数値トークンが en と違う(en のみ %s / %s のみ %s)"
                       % (l, sorted((ref_n - got).elements()), l, sorted((got - ref_n).elements())))
        lost = ref_c - code_tokens(v)
        lost = Counter({k: n for k, n in lost.items() if v.count(k) < ref_c[k]})
        if lost:
            bad.append("%s: op 名・コード片が訳に無い %s" % (l, sorted(lost.elements())))
    return bad


def audit(spec: dict, table: dict) -> tuple[list[dict], list[str]]:
    """(問題のある文字列の一覧, 使われていない訳の en) を返す。"""
    problems, used = [], set()
    seen: set[tuple[str, str]] = set()
    for where, d in iter_texts(spec):
        langs = needs(d)
        if not langs:
            continue
        en, ja = d["en"], d["ja"]
        used.add(en)
        if (en, ja) in seen:
            continue
        seen.add((en, ja))
        why = check_entry(en, ja, table["strings"].get(en), langs)
        if why:
            problems.append({"where": where, "en": en, "ja": ja, "why": why})
    unused = sorted(set(table["strings"]) - used)
    return problems, unused


def translate(spec: dict, table: dict) -> dict:
    """門を通してから 8 言語の仕様を返す(元の仕様は変えない)。落ちれば :class:`GateError`。"""
    problems, _ = audit(spec, table)
    if problems:
        raise GateError(["%s %r: %s" % (p["where"], p["en"], "; ".join(p["why"])) for p in problems])
    out = copy.deepcopy(spec)
    for _, d in iter_texts(out):
        tr = table["strings"].get(d["en"])
        for l in needs(d):
            d[l] = tr[l]
    left = [w for w, d in iter_texts(out) if needs(d)]
    if left:                                                         # 門を抜けたのに埋まらない = 層の故障
        raise AssertionError("埋まらなかった文字列: %s" % left)
    return out


def missing_json(example: str, spec: dict, table: dict) -> dict:
    """訳す作業用: 未訳・古い訳・門に落ちた訳を、表にそのまま貼れる形で。"""
    problems, unused = audit(spec, table)
    todo = {}
    for p in problems:
        old = table["strings"].get(p["en"], {})
        todo[p["en"]] = {"ja": p["ja"], **{l: old.get(l, "") for l in NEW_LANGS}, "_why": p["why"]}
    return {"example": example, "table": table_path(example).relative_to(ROOT).as_posix(),
            "missing": len(todo), "unused": unused, "strings": todo}


# --------------------------------------------------------------------------- 作例を走らせて仕様を横取り
def example_script(example: str) -> Path:
    """作例の名前からスクリプトを探す(examples → examples_3d → tools/build_*)。"""
    if not re.fullmatch(r"[A-Za-z0-9_]+", example or ""):
        raise ValueError("作例の名前は英数字と _ だけ(パスや拡張子は付けない): %r" % (example,))
    for sub in EXAMPLE_DIRS:
        p = ROOT / sub / (example + ".py")
        if p.is_file():
            return p
    if example.startswith(BUILDER_PREFIX):
        p = ROOT / BUILDER_DIR / (example + ".py")
        if p.is_file():
            return p
    raise FileNotFoundError("作例 %s が %s / %s/%s*.py に無い"
                            % (example, " / ".join(EXAMPLE_DIRS), BUILDER_DIR, BUILDER_PREFIX))


def _tree_state(root: Path) -> dict | None:
    """``git status`` に出るファイルの中身の指紋(git が無い・repo でなければ None = 比べない)。"""
    import hashlib
    import subprocess
    try:
        r = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "-z"], capture_output=True,
                           stdin=subprocess.DEVNULL, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    state = {}
    for rec in r.stdout.decode("utf-8", "replace").split("\0"):
        if len(rec) < 4:
            continue
        rel = rec[3:]
        if "__pycache__" in rel.split("/"):                          # import が書くバイトコードは生成物でない
            continue
        f = root / rel
        if f.is_file():
            state[rel] = hashlib.sha256(f.read_bytes()).hexdigest()
        else:
            state[rel] = rec[:2]                                      # 消えた・ディレクトリ
    return state


def capture_specs(script: Path, argv: list[str] | None = None, quiet: bool = True) -> list[dict]:
    """作例の ``main(argv)`` を走らせ、``write_viewer`` に渡った仕様を全部返す(作例の検査もそのまま走る)。

    ``write_viewer`` は要求されたパスでなく一時フォルダに同じ名前で書き、そのパスを返す
    (``tools/build_*`` は既定で ``docs/anim3d`` に書くため)。走らせる前後で木(``git status`` の対象)が
    変われば止める。``main`` が 0 以外を返すか例外なら止める(壊れた作例から ViEW 版を作らない)。
    """
    import shutil

    import fullseye as fs
    got: list[dict] = []
    orig_pv, orig_fs = pv.write_viewer, fs.write_viewer
    scratch = tempfile.mkdtemp(prefix="anim3d_i18n_")
    before = _tree_state(ROOT)

    def spy(spec, path, lang="ja", *a, **k):
        got.append(spec)
        to = os.path.join(scratch, "%02d_%s" % (len(got), os.path.basename(os.fspath(path)) or "viewer.html"))
        return orig_pv(spec, to, lang, *a, **k)

    name = "_anim3d_i18n_" + script.stem
    mspec = importlib.util.spec_from_file_location(name, script)
    mod = importlib.util.module_from_spec(mspec)
    buf = io.StringIO()
    pv.write_viewer = fs.write_viewer = spy
    try:
        with (contextlib.redirect_stdout(buf) if quiet else contextlib.nullcontext()):
            mspec.loader.exec_module(mod)
            if not hasattr(mod, "main"):
                raise RuntimeError("%s に main() が無い" % script.name)
            rc = mod.main(list(argv or []))
    except SystemExit as exc:
        rc = exc.code
    except Exception:
        sys.stderr.write(buf.getvalue())
        raise
    finally:
        pv.write_viewer, fs.write_viewer = orig_pv, orig_fs
        shutil.rmtree(scratch, ignore_errors=True)
    after = _tree_state(ROOT) if before is not None else None
    if before is not None and after != before:
        changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        raise RuntimeError("%s を走らせたら木が変わった(翻訳の確認で repo に書かない): %s"
                           % (script.name, changed))
    if rc not in (0, None):
        sys.stderr.write(buf.getvalue())
        raise RuntimeError("%s の main() が %r を返した(作例の検査に落ちた)" % (script.name, rc))
    if not got:
        raise RuntimeError("%s は write_viewer を呼ばなかった" % script.name)
    return got


def pick_spec(specs: list[dict], viewer_id: str | None) -> dict:
    if viewer_id:
        hit = [s for s in specs if s.get("id") == viewer_id]
        if len(hit) != 1:
            raise ValueError("id %r の仕様が %d 個(候補 %s)" % (viewer_id, len(hit), [s.get("id") for s in specs]))
        return hit[0]
    if len(specs) != 1:
        raise ValueError("仕様が %d 個ある —— --viewer-id で選ぶ(候補 %s)" % (len(specs), [s.get("id") for s in specs]))
    return specs[0]


def build(example: str, out: str | os.PathLike, table: dict | None = None, viewer_id: str | None = None,
          argv: list[str] | None = None) -> str:
    """作例を走らせ、門を通し、8 言語(?lang → ブラウザの言語)の HTML を ``out`` に書く。"""
    spec = pick_spec(capture_specs(example_script(example), argv), viewer_id)
    spec8 = translate(spec, table if table is not None else load_table(example))
    return pv.write_viewer(spec8, out, list(LANGS), detect_lang=True)


# --------------------------------------------------------------------------- commit 済みページの門
def first_diff_offset(a: bytes, b: bytes) -> int:
    """最初に違うバイトの位置(片方が他方の前置なら短い方の長さ)。64 KiB の塊で粗く、次に 1 バイトずつ。"""
    n, i, step = min(len(a), len(b)), 0, 65536
    while i < n and a[i:i + step] == b[i:i + step]:
        i += step
    while i < n and a[i] == b[i]:
        i += 1
    return i


def describe_page_mismatch(committed: str, rebuilt: str, page, example: str, ctx: int = 200) -> str | None:
    """commit 済みのページ(``committed``)と今の生成器 + 翻訳表で作り直したページ(``rebuilt``)を比べ、同じなら None、
    違えば **短い** 説明文を返す(sha256 → 最初に違うバイトの位置 → その前後 ``ctx`` 文字を両側 → 違う行の数。
    作り直したページは一時フォルダに書いてパスを添える)。

    ページは数 MB なので ``assert html == want`` にしてはいけない —— pytest の assertion rewriting が 2 本の文字列を
    difflib に通し、CI で 10 分の timeout に当たった(2026-10-25、イトカワ run 40215975176・レンズ系 PR #153)。
    門は :func:`check_same_page` を 1 行呼ぶ。
    """
    import hashlib
    import itertools

    a, b = committed.encode("utf-8"), rebuilt.encode("utf-8")
    ha, hb = hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest()
    if ha == hb:
        return None
    off = first_diff_offset(a, b)
    lo = max(0, off - ctx)
    side_a = a[lo:off + ctx].decode("utf-8", errors="replace")
    side_b = b[lo:off + ctx].decode("utf-8", errors="replace")
    n_lines = sum(1 for x, y in itertools.zip_longest(committed.splitlines(), rebuilt.splitlines()) if x != y)
    name = os.path.basename(str(page))
    out = os.path.join(tempfile.gettempdir(), name.replace(".html", "") + ".rebuilt.html")
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write(rebuilt)
    return ("commit 済みの %s が今の生成器 + 翻訳表の 8 言語版と違う —— "
            "py -3.11 tools/anim3d_i18n.py --build %s --out %s で作り直す。\n"
            "  sha256 committed=%s rebuilt=%s\n"
            "  bytes committed=%d rebuilt=%d, 違う行 %d 本, 最初に違うバイト offset=%d\n"
            "  committed[%d:%d]=%r\n  rebuilt  [%d:%d]=%r\n  作り直したページ: %s"
            % (name, example, str(page).replace(chr(92), "/"), ha[:16], hb[:16], len(a), len(b), n_lines, off,
               lo, off + ctx, side_a, lo, off + ctx, side_b, out))


def check_same_page(committed: str, rebuilt: str, page, example: str) -> None:
    """commit 済みのページが作り直しとバイト一致しなければ、:func:`describe_page_mismatch` の短い文で ``AssertionError``。

    テストでの使い方(巨大な文字列の ``==`` を書かない)::

        want = I18N.pv._build_html(I18N.translate(spec, table), list(I18N.LANGS), detect_lang=True)
        I18N.check_same_page(html, want, PAGE, BUILDER)
    """
    msg = describe_page_mismatch(committed, rebuilt, page, example)
    if msg is not None:
        raise AssertionError(msg)


# --------------------------------------------------------------------------- 走るサンプル
def demo() -> int:
    """見本(interactive_anim3d_viewer)を 8 言語にし、わざと壊した表 3 通りが止まることを見せる。"""
    ex = "interactive_anim3d_viewer"
    spec = pick_spec(capture_specs(example_script(ex)), None)
    table = load_table(ex)
    n = len({d["en"] for _, d in iter_texts(spec)})
    with tempfile.TemporaryDirectory() as d:
        path = pv.write_viewer(translate(spec, table), os.path.join(d, ex + ".html"), list(LANGS), detect_lang=True)
        html = Path(path).read_text(encoding="utf-8")
        print("書いた: %s 相当(%.0f KB、8 言語、文字列 %d 本、?lang → navigator.language)"
              % (ex + ".html", os.path.getsize(path) / 1e3, n))
        assert "function pickLang" in html
    some = next(iter(table["strings"]))
    num_key = next(k for k in table["strings"] if num_tokens(k))
    s2 = copy.deepcopy(table["strings"])
    tok = _NUM.search(s2[num_key]["de"]).group(1)
    s2[num_key]["de"] = s2[num_key]["de"].replace(tok, str(int(float(tok)) + 7), 1)
    cases = {"未訳(1 行消す)": {k: v for k, v in table["strings"].items() if k != some},
             "数値の不一致(de の数字を 1 つ変える)": s2}
    for label, strings in cases.items():
        try:
            translate(spec, dict(table, strings=strings))
        except GateError as exc:
            print("止まった —— %s: %s" % (label, exc.problems[0][:110]))
        else:
            raise AssertionError("壊した表が通ってしまった: %s" % label)
    # op 名の欠落: 見本の文字列に op 名は無いので、op 名入りの 1 行で門を見せる
    en = "Drawn with fs.viewer_anim3d_tab (bodies[*]['alpha'] = 0.3)."
    good = {"ja": "fs.viewer_anim3d_tab で描画(bodies[*]['alpha'] = 0.3)。",
            "ko": "fs.viewer_anim3d_tab 로 그림(bodies[*]['alpha'] = 0.3)."}
    assert not check_entry(en, good["ja"], good, ["ko"])
    why = check_entry(en, good["ja"], dict(good, ko="뷰어로 그림(bodies[*]['alpha'] = 0.3)."), ["ko"])
    assert why and "op 名" in why[0], why
    print("止まった —— op 名の欠落(ko から fs.viewer_anim3d_tab を消す): %s" % why[0])
    print("\nPASS")
    return 0


# --------------------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 epilog="例: py -3.11 tools/anim3d_i18n.py --build interactive_anim3d_viewer "
                                        "--out docs/view2026/anim3d/interactive_anim3d_viewer.html")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--build", metavar="EXAMPLE",
                   help="8 言語の HTML を --out に書く(門に落ちれば書かない)。EXAMPLE は examples / examples_3d"
                        " の作例名か tools/build_* の名前")
    g.add_argument("--check", metavar="EXAMPLE", help="門だけ(書かない)。落ちれば exit 1")
    g.add_argument("--missing", metavar="EXAMPLE", help="未訳・古い訳・門に落ちた訳を JSON で書き出す(訳す作業用)")
    g.add_argument("--demo", action="store_true", help="走るサンプル: 見本を 8 言語にし、壊した表が止まるのを見せる")
    ap.add_argument("--out", help="--build の出力 HTML")
    ap.add_argument("--json-out", help="--missing の書き出し先(省略は標準出力)")
    ap.add_argument("--table", help="翻訳表(省略は tools/anim3d_i18n_tables/<EXAMPLE>.json)")
    ap.add_argument("--viewer-id", help="作例が複数の仕様を書くとき、使う仕様の id")
    ap.add_argument("--script-arg", action="append", default=[], metavar="ARG",
                    help="作例の main(argv) に渡す引数(繰り返せる。- で始まる値は --script-arg=--seed の形で)")
    a = ap.parse_args(argv)
    if a.demo:
        return demo()
    ex = a.build or a.check or a.missing
    table = load_table(ex, Path(a.table) if a.table else None)
    if a.build and not a.out:
        ap.error("--build には --out が要る")
    try:
        spec = pick_spec(capture_specs(example_script(ex), a.script_arg), a.viewer_id)
        if a.missing:
            js = json.dumps(missing_json(ex, spec, table), ensure_ascii=False, indent=1)
            if a.json_out:
                Path(a.json_out).write_text(js + "\n", encoding="utf-8")
                print("wrote %s" % a.json_out)
            else:
                print(js)
            return 0
        _, unused = audit(spec, table)
        for u in unused:
            print("警告: 使われていない訳 %r" % u, file=sys.stderr)
        spec8 = translate(spec, table)
        n = len({d["en"] for _, d in iter_texts(spec8)})
        if a.check:
            print("ok: %s の文字列 %d 本が 8 言語そろい、数値・コード片も en と一致" % (ex, n))
            return 0
        path = pv.write_viewer(spec8, a.out, list(LANGS), detect_lang=True)
        print("wrote %s (%.2f MB, 8 言語, 文字列 %d 本)" % (path, os.path.getsize(path) / 1e6, n))
        return 0
    except GateError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
