"""訳の対訳表(docs/i18n/*.json)に、読み手が見ない場所へ置かれた行が無いこと。

2026-10-24: op_rest.json の最上位に ``optics/acoustic_impedance_mismatch`` と
``optics/material_acoustic`` の本文訳が置かれていた。opdocs は ``bodies`` の中しか
読まないので、訳はあるのに頁は「未訳」のまま出ていた(例外も警告も無い)。
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
I18N = os.path.join(ROOT, "docs", "i18n")

# 表ごとの「読まれる」最上位キー。opdocs が _load_json(path, key) で読む key + 説明行。
ALLOWED = {
    "op_rest.json": {"_", "languages", "bodies"},
    "op_summary.json": {"_", "languages", "summaries"},
    "opdocs.json": {"_", "languages", "strings"},
}


def test_every_entry_sits_where_the_reader_looks():
    for name, keys in ALLOWED.items():
        with open(os.path.join(I18N, name), encoding="utf-8") as f:
            d = json.load(f)
        stray = sorted(set(d) - keys)
        assert not stray, "%s の最上位に読まれない行: %s(%s の中へ)" % (
            name, ", ".join(stray), sorted(keys - {"_", "languages"}))


def test_the_gate_sees_a_stray_entry(tmp_path):
    # 門を壊して確かめる: 最上位に op 名の行があれば検出できること
    d = {"_": "", "languages": [], "bodies": {}, "optics/x": {"fp": "0"}}
    assert sorted(set(d) - ALLOWED["op_rest.json"]) == ["optics/x"]
