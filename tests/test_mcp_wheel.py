# -*- coding: utf-8 -*-
"""MCP サーバを **wheel から** 動かす門(配布物の側で数える)。

0.1.11 の MCP は索引 ``docs/OP_INDEX.json`` と知識層 ``docs/ops/**/*.md`` をリポジトリ
相対で読んでいた。checkout のテストは全部緑、``pip install fullseye`` した環境からは
``CatalogError`` で止まる —— 門が事故の起きない場所にだけ立っていた
([[feedback_gate_must_stand_where_the_accident_happens]])。だからここでは

1. wheel を**実際に建てて**、別の venv に **wheel だけ**(+ numpy / scipy)入れ、
2. **リポジトリの外の cwd** から ``python -m fullseye.mcp`` を起動し、
3. 実 stdio で initialize → tools/list → 検索 → 引き当て → 被覆 を往復して、
4. **件数を checkout と突き合わせる**(索引 1,939 / ノート 1,939。「返った」だけでは
   空の索引でも通る —— [[feedback_ran_is_not_meaningful_output]])。

重い(wheel の build 1〜2 分 + venv)ので **opt-in**: ``FULLSEYE_WHEEL_GATE=1``。
CI では core-minimal ジョブが既に建てた wheel と venv を ``FULLSEYE_WHEEL_PYTHON`` で
使い回す(建て直さない)。手元で建てるなら::

    $env:FULLSEYE_WHEEL_GATE = "1"; py -3.11 -m pytest tests/test_mcp_wheel.py -q

    # 既に建てた wheel / venv を使い回す
    $env:FULLSEYE_WHEEL_FILE = "dist\\fullseye-0.2.0-py3-none-any.whl"
    $env:FULLSEYE_WHEEL_PYTHON = "C:\\scratch\\wv\\Scripts\\python.exe"
"""
from __future__ import annotations

import glob
import io
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE = os.environ.get("FULLSEYE_WHEEL_GATE") == "1"

pytestmark = pytest.mark.skipif(
    not GATE, reason="FULLSEYE_WHEEL_GATE=1 で有効(wheel を建てて別 venv に入れる。数分かかる)")


# --------------------------------------------------------------------------- #
# 転送のヘルパ(fullseye を import しない —— この検査は配布物の側に立つ)             #
# --------------------------------------------------------------------------- #
def _frame(msg: dict) -> bytes:
    body = json.dumps(msg, ensure_ascii=False).encode("utf-8")
    return b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body


def _read_message(stream: io.BytesIO):
    length = None
    while True:
        line = stream.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        k, _, v = line.decode("ascii", "replace").partition(":")
        if k.strip().lower() == "content-length":
            length = int(v.strip())
    if length is None:
        raise AssertionError("Content-Length の無いフレーム")
    return json.loads(stream.read(length).decode("utf-8"))


def _parse_all(buf: bytes) -> tuple[list[dict], bytes]:
    stream = io.BytesIO(buf)
    out = []
    while True:
        pos = stream.tell()
        msg = _read_message(stream)
        if msg is None:
            return out, buf[pos:]
        out.append(msg)


def _req(i, method, **params):
    return {"jsonrpc": "2.0", "id": i, "method": method, "params": params}


def _call(i, tool, **args):
    return _req(i, "tools/call", name=tool, arguments=args)


def _run(args, **kw) -> subprocess.CompletedProcess:
    p = subprocess.run(args, capture_output=True, **kw)
    assert p.returncode == 0, "%s\n--- stdout ---\n%s\n--- stderr ---\n%s" % (
        args, p.stdout.decode("utf-8", "replace")[-1500:], p.stderr.decode("utf-8", "replace")[-3000:])
    return p


def _clean_env() -> dict:
    """リポジトリが見えない環境。PYTHONPATH に checkout が入っていると wheel 側の欠落が
    隠れる(ci_wheel_check と同じ理由)。"""
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


# --------------------------------------------------------------------------- #
# wheel を建てて別 venv に入れる(module で 1 回)                                 #
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def wheel_python(tmp_path_factory) -> str:
    """wheel だけを入れた venv の python。``FULLSEYE_WHEEL_PYTHON`` があればそれを使う。

    session scope: ``tests/test_abi_wheel.py`` が同じ fixture を import して使い回す
    (wheel の build と venv は 1 回でよい —— venv は読むだけで書き換えない)。"""
    given = os.environ.get("FULLSEYE_WHEEL_PYTHON")
    if given:
        given = os.path.abspath(given)
        assert os.path.exists(given), "FULLSEYE_WHEEL_PYTHON が無い: %s" % given
        return given
    tmp = tmp_path_factory.mktemp("wheelgate")
    whl = os.environ.get("FULLSEYE_WHEEL_FILE")
    if not whl:
        dist = str(tmp / "dist")
        _run([sys.executable, "-m", "build", "--wheel", "-o", dist], cwd=ROOT, env=_clean_env(), timeout=900)
        found = glob.glob(os.path.join(dist, "fullseye-*.whl"))
        assert len(found) == 1, found
        whl = found[0]
    whl = os.path.abspath(whl)
    assert os.path.exists(whl), whl
    venv = str(tmp / "wv")
    _run([sys.executable, "-m", "venv", venv], timeout=300)
    vpy = os.path.join(venv, "Scripts", "python.exe")
    if not os.path.exists(vpy):
        vpy = os.path.join(venv, "bin", "python")
    _run([vpy, "-m", "pip", "install", "-q", "numpy", "scipy", whl], env=_clean_env(), timeout=900)
    return vpy


@pytest.fixture(scope="session")
def outside(tmp_path_factory) -> str:
    """リポジトリの外の cwd。"""
    return str(tmp_path_factory.mktemp("outside_repo"))


def _checkout_counts() -> tuple[int, int]:
    """checkout 側の正本の件数(突き合わせ先)。"""
    with open(os.path.join(ROOT, "docs", "OP_INDEX.json"), encoding="utf-8") as f:
        n_index = json.load(f)["n_ops"]
    with open(os.path.join(ROOT, "fullseye", "data", "OP_NOTES.json"), encoding="utf-8") as f:
        n_notes = json.load(f)["n_ops"]
    return n_index, n_notes


# --------------------------------------------------------------------------- #
# 検査                                                                         #
# --------------------------------------------------------------------------- #
def test_the_venv_really_is_the_wheel_and_not_the_checkout(wheel_python, outside):
    """門の前提を壊して確かめる: wheel 側から docs/ が**見えない**こと。見えていたら
    以下の検査は checkout を測っていて、wheel の欠落に盲目になる。"""
    code = ("import os, fullseye.mcp.catalog as C;"
            "print(os.path.isdir(C.OPS_DOCS), os.path.exists(C.OP_INDEX), C.ROOT)")
    p = _run([wheel_python, "-c", code], cwd=outside, env=_clean_env(), timeout=300)
    seen_docs, seen_index, root = p.stdout.decode("utf-8", "replace").split()[:3]
    assert (seen_docs, seen_index) == ("False", "False"), (
        "wheel の venv から checkout の docs/ が見えている(ROOT=%s)。PYTHONPATH か cwd か "
        "editable install が混ざっている —— この門は配布物を測れていない" % root)
    assert os.path.abspath(ROOT) not in os.path.abspath(root)


def test_the_wheel_carries_the_catalog_data_files(wheel_python, outside):
    """package-data の 2 ファイルが wheel に**中身ごと**入っていること(0 バイトの
    ファイルがあっても「在る」は通る —— サイズと件数を見る)。"""
    code = ("import json; from importlib.resources import files;"
            "d = files('fullseye') / 'data';"
            "i = json.loads((d / 'OP_INDEX.json').read_text(encoding='utf-8'));"
            "n = json.loads((d / 'OP_NOTES.json').read_text(encoding='utf-8'));"
            "print(i['n_ops'], len(i['ops']), n['n_ops'], n['n_notes'], len(n['notes']))")
    p = _run([wheel_python, "-c", code], cwd=outside, env=_clean_env(), timeout=300)
    n_ops, n_rows, n_note_ops, n_notes, n_note_keys = map(int, p.stdout.split())
    want_index, want_notes = _checkout_counts()
    assert n_ops == n_rows == want_index, (n_ops, n_rows, want_index)
    assert n_note_ops == n_note_keys == want_notes and n_notes >= n_note_ops, (n_note_ops, n_notes, want_notes)
    assert n_ops > 1900 and n_note_ops > 1900


def test_mcp_serves_the_catalog_from_the_wheel_outside_the_repo(wheel_python, outside):
    """本物のプロセス境界 + リポジトリ外 cwd で、索引と知識層が**件数ごと**返ること。"""
    payload = b"".join([
        _frame(_req(1, "initialize", protocolVersion="2025-06-18", capabilities={},
                    clientInfo={"name": "pytest-wheel", "version": "0"})),
        _frame({"jsonrpc": "2.0", "method": "notifications/initialized"}),
        _frame(_req(2, "tools/list")),
        _frame(_call(3, "fullseye_search_ops", query="gauss", limit=5)),
        _frame(_call(4, "fullseye_search_ops", query="abcd_matrix", limit=5)),
        _frame(_call(5, "fullseye_op_help", name="gaussian")),
        _frame(_call(6, "fullseye_op_help", name="abcd_matrix")),
        _frame(_call(7, "fullseye_catalog_coverage")),
        _frame(_call(8, "fullseye_list_samples")),
    ])
    p = subprocess.run([wheel_python, "-m", "fullseye.mcp"], input=payload, capture_output=True,
                       cwd=outside, env=_clean_env(), timeout=300)
    err = p.stderr.decode("utf-8", "replace")
    assert p.returncode == 0, err[-3000:]
    assert "CatalogError" not in err, err[-3000:]
    msgs, rest = _parse_all(p.stdout)
    assert rest.strip() == b"", "stdout にプロトコル以外のバイト: %r" % rest[:120]
    assert [m["id"] for m in msgs] == [1, 2, 3, 4, 5, 6, 7, 8], [m.get("id") for m in msgs]
    assert all("error" not in m for m in msgs), [m for m in msgs if "error" in m]
    assert msgs[0]["result"]["serverInfo"]["name"] == "fullseye"
    assert b"[fullseye-mcp] ready" in p.stderr, "起動ログが stderr に出ていない"

    tools = {t["name"] for t in msgs[1]["result"]["tools"]}
    assert len(tools) == 8 and all(t.startswith("fullseye_") for t in tools), tools

    # 検索: 2-D レジストリの op と、台帳(optics)の op の両方が索引の層から出る
    s = msgs[2]["result"]["structuredContent"]
    top = [o["name"] for o in s["ops"]]
    assert top[0] == "gauss_filter" and "gaussian" in top[:3], top
    s2 = msgs[3]["result"]["structuredContent"]
    hit = {o["name"]: o for o in s2["ops"]}.get("abcd_matrix")
    assert hit is not None, s2["ops"]
    assert {"index", "ledger", "note"} <= set(hit["sources"]), hit
    assert hit["category"] == "geometric" and hit["dim"] == "optics", hit

    # 引き当て: 本文は同梱 HTML に落ち、落ちたことと在り処を言う
    for i, (name, where) in ((4, ("gaussian", "studio_assets/op_help/gaussian.html")),
                             (5, ("abcd_matrix", "studio_assets/op_help/optics/abcd_matrix.html"))):
        h = msgs[i]["result"]
        assert not h["isError"], h["content"][0]["text"][:300]
        sc = h["structuredContent"]
        assert sc["found"] is True and sc["has_note"] is True, sc
        assert sc["body_format"] == "html" and sc["body_source"] == where, (sc["body_format"], sc["body_source"])
        assert sc["body_chars"] > 500, sc["body_chars"]
        assert "body" not in sc and name in h["content"][0]["text"], "本文(text 側)に op 名が無い"
        assert sc["note_refs"][0].startswith("docs/ops/") and "note_body_unavailable" in sc, sc.keys()
    g = msgs[4]["result"]["structuredContent"]
    assert g["figures"] and g["figures"][0]["source"] == "studio_assets/op_help/fig", g["figures"]
    links = [c for c in msgs[4]["result"]["content"] if c["type"] == "resource_link"]
    assert links and all(c["uri"].startswith("file:///") for c in links)

    # 被覆: 件数を checkout の正本と突き合わせる(「走った」≠「意味のある出力」)
    c = msgs[6]["result"]["structuredContent"]
    want_index, want_notes = _checkout_counts()
    assert c["index_source"].startswith("package:") and c["index_source"].endswith("OP_INDEX.json"), c["index_source"]
    assert c["notes_source"].startswith("package:") and c["notes_source"].endswith("OP_NOTES.json"), c["notes_source"]
    ps = c["per_source"]
    assert ps["index"] == want_index, (ps["index"], want_index)
    assert ps["note"] == want_notes, (ps["note"], want_notes)
    assert ps["registry"] > 500 and ps["ledger"] > 900 and ps["facade"] > 500, ps
    assert c["index_without_note"] == [], c["index_without_note"][:10]
    assert c["note_only"] == 0, c["note_only_names"][:10]

    # 同梱サンプル(handles.py の SAMPLE_DIR も同じ ROOT 解決)
    smp = msgs[7]["result"]["structuredContent"]
    assert smp["samples"], smp
