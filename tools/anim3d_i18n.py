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
通常は 8 言語の仕様にし、``write_viewer(..., lang=LANGS, detect_lang=True)`` で書く。
作例が ``ANIM3D_I18N_LANGS = ("ja", "en")`` を明示した場合だけ、翻訳表を要求せず ja/en の仕様をそのまま書く
(既存作例は従来どおり 8 言語)。
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
import base64
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

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pocviewer as pv  # noqa: E402
import annotate  # noqa: E402

LANGS = pv.LANGS
NEW_LANGS = tuple(l for l in LANGS if l not in ("ja", "en"))       # 表で埋める 6 言語
TABLES = ROOT / "tools" / "anim3d_i18n_tables"
EXAMPLE_DIRS = ("examples", "examples_3d")
#: 作例の外で探す生成器: ``tools/build_*.py``(題材の動く 3-D、``main(argv)`` を持ち write_viewer で書く)。
BUILDER_DIR, BUILDER_PREFIX = "tools", "build_"
RASTER_REFERENCE_FONT = "meiryo.ttc"
# Portable comparison may absorb a few relief-PNG values that cross one
# quantizer boundary through platform libm differences.  A broad or systematic
# change is still a changed page, so the allowance is page-wide and small.
MAX_PORTABLE_QUANTIZED_DRIFT = 8

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
            requested = getattr(mod, "ANIM3D_I18N_LANGS", None)
            if requested is not None:
                requested = tuple(requested)
                if requested != ("ja", "en"):
                    raise ValueError("ANIM3D_I18N_LANGS は ('ja', 'en') だけ指定できる: %r" % (requested,))
                for spec in got:
                    spec["_anim3d_i18n_langs"] = list(requested)
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


def requested_languages(spec: dict) -> tuple[dict, tuple[str, ...]]:
    """Return a clean spec and its explicitly requested publication languages."""
    clean = copy.deepcopy(spec)
    langs = tuple(clean.pop("_anim3d_i18n_langs", LANGS))
    if langs not in (tuple(LANGS), ("ja", "en")):
        raise ValueError("公開言語は 8 言語または ja/en だけ: %r" % (langs,))
    return clean, langs


def prepare(spec: dict, table: dict) -> tuple[dict, tuple[str, ...]]:
    """Apply the translation gate only when the source requests all eight languages."""
    clean, langs = requested_languages(spec)
    if langs == ("ja", "en"):
        return clean, langs
    return translate(clean, table), langs


def build(example: str, out: str | os.PathLike, table: dict | None = None, viewer_id: str | None = None,
          argv: list[str] | None = None) -> str:
    """作例を走らせ、門を通し、要求言語(?lang → ブラウザの言語)の HTML を ``out`` に書く。"""
    spec = pick_spec(capture_specs(example_script(example), argv), viewer_id)
    ready, langs = prepare(spec, table if table is not None else load_table(example))
    return pv.write_viewer(ready, out, list(langs), detect_lang=True)


# --------------------------------------------------------------------------- commit 済みページの門
_DATA_MARKER = "const D = "


def _embedded_data(html: str) -> tuple[dict, int, int]:
    """Return the viewer's embedded JSON and its half-open span in ``html``."""
    start = html.find(_DATA_MARKER)
    if start < 0:
        raise ValueError("viewer の埋め込み JSON(const D) が無い")
    start += len(_DATA_MARKER)
    data, used = json.JSONDecoder().raw_decode(html[start:])
    if not isinstance(data, dict):
        raise ValueError("viewer の埋め込み JSON(const D) が object でない")
    return data, start, start + used


def _png_shape(encoded: str) -> tuple[int, ...]:
    """Read one grayscale/RGB PNG shape from its signature and IHDR."""
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("pane frames の PNG が正しい base64 でない") from exc
    if len(raw) < 33 or raw[:8] != b"\x89PNG\r\n\x1a\n" or raw[12:16] != b"IHDR":
        raise ValueError("pane frames の PNG header が壊れている")
    width, height, colour = (int.from_bytes(raw[16:20], "big"), int.from_bytes(raw[20:24], "big"), raw[25])
    if width < 1 or height < 1 or colour not in (0, 2):
        raise ValueError("pane frames の PNG IHDR が未対応")
    return (height, width, 3) if colour == 2 else (height, width)


def normalize_rasters(html: str) -> str:
    """Replace only anim3d pane-frame pixels and their content-addressed keys.

    Array metadata (including shape), all 3-D arrays, numbers and strings remain
    exact.  Raster keys are renamed in first pane occurrence order.
    """
    data, start, end = _embedded_data(html)
    arrays = data.get("arrays")
    tabs = data.get("tabs")
    if not isinstance(arrays, dict) or not isinstance(tabs, list):
        raise ValueError("viewer の arrays/tabs の形が違う")
    raster_keys = []
    for tab in tabs:
        if not isinstance(tab, dict) or tab.get("kind") != "anim3d":
            continue
        panes = tab.get("panes", [])
        if not isinstance(panes, list):
            raise ValueError("anim3d panes が list でない")
        for pane in panes:
            key = pane.get("frames") if isinstance(pane, dict) else None
            if not isinstance(key, str) or key not in arrays:
                raise ValueError("anim3d pane frames の配列が無い")
            if key not in raster_keys:
                raster_keys.append(key)

    for index, old_key in enumerate(raster_keys):
        rec = arrays.get(old_key)
        if not isinstance(rec, dict) or not isinstance(rec.get("shape"), list):
            raise ValueError("pane frames の配列 record/shape が無い")
        shape = rec["shape"]
        if rec.get("t") == "png":
            payload = rec.get("png")
            if not isinstance(payload, list) or len(shape) not in (3, 4) or len(payload) != shape[0]:
                raise ValueError("pane frames の PNG 件数または shape が違う")
            expected = tuple(shape[1:])
            if any(_png_shape(item) != expected for item in payload):
                raise ValueError("pane frames の PNG IHDR と shape が違う")
            rec["png"] = ["<RASTER>" for _ in payload]
        elif "b64" in rec:
            if not isinstance(rec["b64"], str):
                raise ValueError("pane frames の b64 が文字列でない")
            rec["b64"] = "<RASTER>"
        else:
            raise ValueError("pane frames の pixel payload が無い")

        new_key = "K%d" % index
        if new_key in arrays and new_key != old_key:
            raise ValueError("pane frames の正規化 key %s が既存配列と衝突した" % new_key)
        for tab in tabs:
            if isinstance(tab, dict) and tab.get("kind") == "anim3d":
                for pane in tab.get("panes", []):
                    if isinstance(pane, dict) and pane.get("frames") == old_key:
                        pane["frames"] = new_key
        arrays[new_key] = arrays.pop(old_key)

    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return html[:start] + encoded + html[end:]


def _portable_data(html: str) -> tuple[dict, str, str, list[tuple[str, str]]]:
    """Canonicalise array keys in deterministic first-reference order."""
    data, start, end = _embedded_data(html)
    data = copy.deepcopy(data)
    arrays = data.get("arrays")
    if not isinstance(arrays, dict):
        raise ValueError("viewer arrays is not an object")
    names: dict[str, str] = {}
    refs: list[tuple[str, str]] = []

    def visit(value, path):
        if isinstance(value, dict):
            for key, child in value.items():
                if not (path == "$" and key == "arrays"):
                    visit(child, path + "." + key)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, "%s[%d]" % (path, index))
        elif isinstance(value, str) and value in arrays and value not in names:
            names[value] = "K%d" % len(names)
            refs.append((value, path))

    visit(data, "$")
    for key in sorted(arrays):
        if key not in names:
            names[key] = "K%d" % len(names)
            refs.append((key, "$.arrays(unreferenced)"))

    def rename(value, root=False):
        if isinstance(value, dict):
            return {k: rename(v) for k, v in value.items() if not (root and k == "arrays")}
        if isinstance(value, list):
            return [rename(v) for v in value]
        return names.get(value, value) if isinstance(value, str) else value

    result = rename(data, True)
    result["arrays"] = {names[key]: arrays[key] for key, _ in refs}
    return result, html[:start], html[end:], refs


def _compare_json(a, b, path: str, diffs: list[str], skip_arrays=False) -> None:
    if len(diffs) >= 8:
        return
    if isinstance(a, bool) or isinstance(b, bool):
        same = type(a) is type(b) and a == b
    elif isinstance(a, float) or isinstance(b, float):
        same = (isinstance(a, float) and isinstance(b, float)
                and bool(np.isclose(a, b, rtol=1e-7, atol=1e-12, equal_nan=True)))
    elif type(a) is not type(b):
        diffs.append("%s: type %s != %s" % (path, type(a).__name__, type(b).__name__))
        return
    elif isinstance(a, dict):
        ak, bk = set(a), set(b)
        if skip_arrays:
            ak.discard("arrays"); bk.discard("arrays")
        if ak != bk:
            diffs.append("%s: keys %r != %r" % (path, sorted(ak), sorted(bk)))
        for key in sorted(ak & bk):
            _compare_json(a[key], b[key], path + "." + key, diffs)
        return
    elif isinstance(a, list):
        if len(a) != len(b):
            diffs.append("%s: length %d != %d" % (path, len(a), len(b)))
        for index, (x, y) in enumerate(zip(a, b)):
            _compare_json(x, y, "%s[%d]" % (path, index), diffs)
        return
    else:
        same = a == b
    if not same:
        diffs.append("%s: %r != %r" % (path, a, b))


def compare_pages_portable(committed: str, rebuilt: str) -> list[str]:
    """Return structural differences after applying portable numeric rules."""
    a, ap, az, refs = _portable_data(committed)
    b, bp, bz, _ = _portable_data(rebuilt)
    diffs: list[str] = []
    if ap != bp:
        diffs.append("HTML before const D differs")
    if az != bz:
        diffs.append("HTML after const D differs")
    _compare_json(a, b, "$", diffs, skip_arrays=True)
    aa, ba = a["arrays"], b["arrays"]
    if len(aa) != len(ba):
        diffs.append("$.arrays: count %d != %d" % (len(aa), len(ba)))

    def raster_keys(data):
        return {pane["frames"] for tab in data.get("tabs", []) if isinstance(tab, dict) and tab.get("kind") == "anim3d"
                for pane in tab.get("panes", []) if isinstance(pane, dict) and isinstance(pane.get("frames"), str)}

    def relief_png_keys(data):
        # These PNG samples are q8 displacement values, not font-dependent
        # pictures.  Their lo/hi live beside the array reference on the body.
        return {body["val"] for tab in data.get("tabs", []) if isinstance(tab, dict) and tab.get("kind") == "anim3d"
                for body in tab.get("bodies", []) if isinstance(body, dict)
                and isinstance(body.get("relief_png"), dict) and isinstance(body.get("val"), str)}

    ar, br = raster_keys(a), raster_keys(b)
    aq, bq = relief_png_keys(a), relief_png_keys(b)
    quantized_drift = 0
    quantized_drift_first = None
    for index in range(min(len(aa), len(ba))):
        key = "K%d" % index
        if key not in aa or key not in ba:
            diffs.append("$.arrays.%s: missing record" % key)
            continue
        x, y = aa[key], ba[key]
        label = "array %s at %s" % refs[index]
        if not isinstance(x, dict) or not isinstance(y, dict):
            _compare_json(x, y, "$.arrays." + key, diffs)
            continue
        if x.get("t") != y.get("t") or x.get("shape") != y.get("shape"):
            diffs.append("%s: t/shape %r/%r != %r/%r" % (label, x.get("t"), x.get("shape"), y.get("t"), y.get("shape")))
            continue
        if key in ar or key in br:
            if key not in ar or key not in br:
                diffs.append("%s: pane raster role differs" % label)
            elif x.get("t") == "png" and len(x.get("png", [])) != len(y.get("png", [])):
                diffs.append("%s: PNG count differs" % label)
            continue
        if (key in aq) != (key in bq):
            diffs.append("%s: quantized relief PNG role differs" % label)
            continue
        payload_fields = ({"b64", "lo", "hi"} if x.get("t") in ("q8", "q16") else
                          {"png"} if x.get("t") == "png" else {"b64"})
        _compare_json({k: v for k, v in x.items() if k not in payload_fields},
                      {k: v for k, v in y.items() if k not in payload_fields}, "$.arrays." + key, diffs)
        try:
            av, bv = pv._decode_array(x), pv._decode_array(y)
            finite_a, finite_b = av[np.isfinite(av)], bv[np.isfinite(bv)]
            range_a = float(np.ptp(finite_a)) if finite_a.size else 0.0
            range_b = float(np.ptp(finite_b)) if finite_b.size else 0.0
            scale = max(1.0, range_a, range_b)
            base_tolerance = np.full(av.shape, 1e-6 * scale)
            tolerance = base_tolerance.copy()
            if key in aq:
                # PNG decoding yields integer q8 samples, so the tolerance is
                # expressed in those same samples (not in a 0..1 value unit).
                base_tolerance.fill(0.0)
                tolerance.fill(1.0)
            elif x.get("t") in ("q8", "q16"):
                step = np.maximum(np.abs(pv._quant_step(x)), np.abs(pv._quant_step(y)))
                tolerance += step.reshape((1,) * (av.ndim - 1) + (-1,)) if step.size > 1 else float(step[0])
            if key in aq:
                base_close = np.isclose(av, bv, rtol=0, atol=base_tolerance, equal_nan=True)
                accepted = np.isclose(av, bv, rtol=0, atol=tolerance, equal_nan=True)
                drift = ~base_close & accepted
                count = int(np.count_nonzero(drift))
                if count:
                    quantized_drift += count
                    if quantized_drift_first is None:
                        pos = tuple(map(int, np.argwhere(drift)[0]))
                        quantized_drift_first = "%s%s" % (label, pos)
            bad = ~np.isclose(av, bv, rtol=0, atol=tolerance, equal_nan=True)
            for pos in np.argwhere(bad)[:max(0, 8 - len(diffs))]:
                idx = tuple(map(int, pos))
                diffs.append("%s%s: %r != %r (delta %.6g, tolerance %.6g)" %
                             (label, idx, av[idx], bv[idx], abs(float(av[idx]) - float(bv[idx])), float(tolerance[idx])))
        except Exception as exc:
            diffs.append("%s: cannot decode (%s)" % (label, exc))
    if quantized_drift > MAX_PORTABLE_QUANTIZED_DRIFT:
        diffs.append("quantized arrays differ by one step at %d values (limit %d; first %s)" %
                     (quantized_drift, MAX_PORTABLE_QUANTIZED_DRIFT, quantized_drift_first))
    return diffs[:8]


def _raster_font_name() -> str:
    """Basename of the actual font selected by annotate for raster labels."""
    font = annotate._font(11)
    return os.path.basename(str(getattr(font, "path", ""))).lower()


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


def check_same_page(committed: str, rebuilt: str, page, example: str) -> str:
    """commit 済みのページが作り直しとバイト一致しなければ、:func:`describe_page_mismatch` の短い文で ``AssertionError``。

    テストでの使い方(巨大な文字列の ``==`` を書かない)::

        want = I18N.pv._build_html(I18N.translate(spec, table), list(I18N.LANGS), detect_lang=True)
        I18N.check_same_page(html, want, PAGE, BUILDER)
    """
    import hashlib

    if hashlib.sha256(committed.encode("utf-8")).digest() == hashlib.sha256(rebuilt.encode("utf-8")).digest():
        return "exact"
    if _raster_font_name() != RASTER_REFERENCE_FONT.lower():
        try:
            differences = compare_pages_portable(committed, rebuilt)
        except ValueError as exc:
            msg = describe_page_mismatch(committed, rebuilt, page, example)
            raise AssertionError("portable page comparison failed: %s\n%s" % (exc, msg)) from exc
        if not differences:
            return "portable"
        raise AssertionError("portable page mismatch:\n  " + "\n  ".join(differences))
    raise AssertionError(describe_page_mismatch(committed, rebuilt, page, example))


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
        clean, langs = requested_languages(spec)
        if langs == tuple(LANGS):
            _, unused = audit(clean, table)
            for u in unused:
                print("警告: 使われていない訳 %r" % u, file=sys.stderr)
        ready, langs = prepare(spec, table)
        n = len({d["en"] for _, d in iter_texts(ready)})
        lang_label = "8 言語" if len(langs) == 8 else "ja/en"
        if a.check:
            print("ok: %s の文字列 %d 本、%s の門を通過" % (ex, n, lang_label))
            return 0
        path = pv.write_viewer(ready, a.out, list(langs), detect_lang=True)
        print("wrote %s (%.2f MB, %s, 文字列 %d 本)" % (path, os.path.getsize(path) / 1e6, lang_label, n))
        return 0
    except GateError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
