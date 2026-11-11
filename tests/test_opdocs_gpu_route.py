"""op ノートの GPU 欄が gpu_route と食い違わない門 / The op notes' GPU line agrees with gpu_route.

★2026-11-03: 鎖の中だけの手書き経路(領域の解析の族 13 op)まで「``device="cuda"`` で高速経路」と書いていた
(単独の呼び出しは apply が CPU で走らせる)。許可リスト(shadow、500 op 超)と native は「なし」と書いていた。
ノートの ``gpu:`` 欄と本文の GPU の行を、apply / run_pipeline / MCP が使う唯一の選び手 ``gpu_route`` から
数え直して突き合わせる(生成器の記録と、ディスクの上のノートの両方)。
"""
from __future__ import annotations

import collections
import pathlib
import re

import gpu_route
from tools import opdocs
from conftest import requires_backend

ROOT = pathlib.Path(__file__).resolve().parents[1]
RECS = opdocs._records()[0]


def _expected(name):
    """gpu_route から直接(opdocs の関数を通さずに)場面を決める。"""
    single = gpu_route.route(name, "single")
    pipe = gpu_route.route(name, "pipeline")
    if single is not None:
        return single.kind, "single"
    if pipe is not None:
        return pipe.kind, "chain"
    return None


def test_records_follow_gpu_route():
    # torch が無いと accel の経路が無く、torch のある環境で作った出荷表と食い違う(2026-11-04 master py3.12/3.14)
    requires_backend("torch")
    seen = set()
    kinds = collections.Counter()
    for rec in RECS:
        if rec["name"] in seen:
            continue
        seen.add(rec["name"])
        info = rec["gpu_route"]
        got = None if info is None else (info["kind"], "single" if info["use"] == "single" else "chain")
        assert got == _expected(rec["name"]), rec["name"]
        kinds[got] += 1
    # 空を通さない(種類と場面ごとに床)
    assert kinds[("accel", "single")] >= 100
    assert kinds[("accel", "chain")] >= 13
    assert kinds[("shadow", "single")] + kinds[("shadow", "chain")] >= 500
    assert kinds[("shadow", "chain")] >= 100
    assert kinds[("native", "single")] + kinds[("native", "chain")] >= 14


def _notes():
    for path in (ROOT / "docs" / "ops").rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        fm = text.split("---", 2)[1]
        op = re.search(r"^op: (.+)$", fm, re.M)
        gpu = re.search(r"^gpu: (.+)$", fm, re.M)
        if op and gpu:
            yield path, op.group(1).strip(), gpu.group(1).strip(), text


def test_notes_on_disk_say_the_same_as_gpu_route():
    status = {}
    for rec in RECS:
        status.setdefault(rec["name"], rec["gpu_status"])
    checked = collections.Counter()
    for path, op, gpu, text in _notes():
        if op not in status:
            continue
        want = opdocs.gpu_status_text(opdocs.gpu_route_of(op))
        if gpu != status[op]:
            continue                                  # 同名の 2 本目(族違い)は「なし」を書く規則
        assert gpu == want, (path, gpu, want)
        line = next((ln for ln in text.splitlines() if ln.startswith("- **GPU**")), "")
        if gpu.startswith("鎖の中だけ"):
            assert "高速経路" not in line and "鎖の中だけ" in line, path
            checked["chain"] += 1
        elif gpu.startswith("native"):
            assert "device=" in line and "GPU に送らない" in line, path
            checked["native"] += 1
        elif gpu.startswith("あり"):
            checked["single"] += 1
        else:
            assert "なし" in line, path
    assert checked["chain"] >= 100 and checked["native"] >= 14 and checked["single"] >= 500


def test_every_gpu_line_has_all_translations():
    import json
    table = json.loads(pathlib.Path(opdocs.I18N_PATH).read_text(encoding="utf-8"))
    langs = [lang for lang in table["languages"] if lang != "ja"]
    assert len(langs) >= 5
    for src in opdocs.GPU_LINES.values():
        row = table["strings"].get(src)
        assert row is not None, src
        for lang in langs:
            assert row.get(lang) and (("{a0}" in row[lang]) == ("{a0}" in src)), (lang, src[:40])
