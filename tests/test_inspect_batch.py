# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fullseye.inspect_batch — フォルダを一括で 前処理→計測→判定→集計→レポート(検査ワークフロー層 #1)。

tmp_path に合成画像(.npy = cv2 無しでも読める)を書いて回す。恒等式:
決定的順序 / 各行に hash・計測・verdict / spec 違反だけ ng / 壊れた 1 枚は error で続行 /
.md・.jsonl・.xlsx の書き分け(openpyxl 無しは xlsx を skip)/ 系列が EWMA に流れ in_control が付く /
監査ログは追記 / 0 枚は fail-closed。
"""
import json
import os

import numpy as np
import pytest

import fullseye as fs
from fullseye.inspect_batch import inspect_batch, as_verdict

SPEC = {"mean": {"min": 0.2, "max": 0.6}, "bright": {"nominal": 400.0, "tol": 60.0}}


def _measure(im):
    return {"mean": float(im.mean()), "bright": float((im > 0.5).sum()), "grade": "A"}


def _plate(defect=False, seed=0):
    """64x64、中央 20x20 の明部(=400 px)。defect で明部が 30x30(=900 px)になる。"""
    rng = np.random.default_rng(seed)
    im = 0.30 + 0.02 * rng.standard_normal((64, 64))
    k = 15 if defect else 10
    im[32 - k:32 + k, 32 - k:32 + k] = 0.9
    return np.clip(im, 0, 1)


@pytest.fixture
def folder(tmp_path):
    d = tmp_path / "lot"
    d.mkdir()
    for i in range(5):
        np.save(d / ("part_%02d.npy" % i), _plate(seed=i))
    np.save(d / "part_05.npy", _plate(defect=True, seed=5))          # 欠陥 1 枚
    (d / "part_06.npy").write_bytes(b"not an npy file")               # 壊れた 1 枚
    (d / "notes.txt").write_text("ignored", encoding="utf-8")         # 拾わない
    return d


def test_rows_are_in_deterministic_order_with_hash_measurements_and_verdict(folder):
    out = inspect_batch(folder, None, measure=_measure, spec=SPEC)
    names = [os.path.basename(r["path"]) for r in out["rows"]]
    assert names == ["part_%02d.npy" % i for i in range(7)]           # sorted、.txt は無視
    good = out["rows"][0]
    assert len(good["hash"]) == 16 and all(c in "0123456789abcdef" for c in good["hash"])
    assert set(good["measurements"]) == {"mean", "bright", "grade"}
    assert good["verdict"]["status"] == "ok" and good["elapsed_ms"] >= 0
    # 同じ入力なら同じ hash(bit 列との突き合わせ)
    again = inspect_batch(folder, None, measure=_measure, spec=SPEC)
    assert [r["hash"] for r in again["rows"]] == [r["hash"] for r in out["rows"]]


def test_only_the_defective_image_is_ng_and_the_broken_file_is_error_without_stopping(folder):
    out = inspect_batch(folder, None, measure=_measure, spec=SPEC)
    status = {os.path.basename(r["path"]): r["verdict"]["status"] for r in out["rows"]}
    assert status["part_05.npy"] == "ng" and status["part_06.npy"] == "error"
    assert all(status["part_%02d.npy" % i] == "ok" for i in range(5))
    ng = out["rows"][5]
    assert ng["verdict"]["result"]["violations"][0]["key"] == "bright"
    assert "error" in out["rows"][6] and out["rows"][6]["measurements"] == {}
    assert out["summary"] == {"n": 7, "ok": 5, "ng": 1, "error": 1, "unjudged": 0}


def test_on_error_raise_stops_at_the_broken_file(folder):
    with pytest.raises(ValueError):
        inspect_batch(folder, None, measure=_measure, spec=SPEC, on_error="raise")


def test_series_and_spc_come_from_the_numeric_columns(folder):
    out = inspect_batch(folder, None, measure=_measure, spec=SPEC)
    assert set(out["series"]) == {"mean", "bright"}                     # grade(文字列)は列にしない
    assert out["series"]["bright"].shape == (6,)                        # error 行は列に入れない
    assert out["series"]["bright"][5] == 900.0
    assert set(out["spc"]) == {"mean", "bright"}
    assert isinstance(out["spc"]["bright"]["in_control"], bool)
    assert out["spc"]["bright"]["n"] == 6 and out["spc"]["bright"]["target"] == pytest.approx(np.mean([400] * 5 + [900]))


def test_without_spec_rows_are_unjudged_and_as_verdict_refuses(folder):
    out = inspect_batch(folder, None, measure=_measure)
    assert out["summary"]["unjudged"] == 6 and out["summary"]["error"] == 1
    assert out["rows"][0]["verdict"] is None
    with pytest.raises(ValueError):
        as_verdict(out["rows"][0])


def test_as_verdict_returns_a_verdict_the_plc_exit_accepts(folder):
    import device
    out = inspect_batch(folder, None, measure=_measure, spec=SPEC)
    io = device.DigitalIO(backend="memory")
    for row, want in ((out["rows"][0], "ok"), (out["rows"][5], "ng"), (out["rows"][6], "error")):
        v = as_verdict(row)
        assert device.signal_verdict(io, v) == want


def test_recipe_is_applied_before_measure(folder):
    seen = {}

    def measure(im):
        seen["shape"] = im.shape
        return {"mean": float(im.mean())}

    out = inspect_batch(folder, ["gaussian"], measure=measure, spec={"mean": {"min": 0, "max": 1}})
    assert seen["shape"] == (64, 64) and out["summary"]["ok"] == 6


def test_md_and_jsonl_reports_and_audit_log(folder, tmp_path):
    md = tmp_path / "lot.md"
    jl = tmp_path / "lot.jsonl"
    audit = tmp_path / "audit.jsonl"
    out = inspect_batch(folder, None, measure=_measure, spec=SPEC, report_path=md,
                        audit_path=audit, title="Lot 42")
    assert out["report_path"] == str(md)
    text = md.read_text(encoding="utf-8")
    assert text.startswith("# Lot 42") and "part_05.npy" in text and "ng" in text
    assert "series: bright" in text and "EWMA" in text

    inspect_batch(folder, None, measure=_measure, spec=SPEC, report_path=jl)
    lines = [json.loads(x) for x in jl.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(lines) == 7 and all(env["fullseye_sort"] == "table" for env in lines)
    recs = fs.from_json_lines(jl.read_text(encoding="utf-8"))
    assert recs[5][0]["status"] == "ng" and recs[6][0]["status"] == "error"

    # 監査ログは追記: 2 回回せば 14 行、各行に時刻・hash・recipe・violations
    inspect_batch(folder, None, measure=_measure, spec=SPEC, audit_path=audit, title="Lot 42")
    entries = fs.from_json_lines(audit.read_text(encoding="utf-8"))
    assert len(entries) == 14
    rec = entries[5][0]
    assert rec["batch"] == "Lot 42" and rec["time"].endswith("+00:00") and rec["recipe"] == []
    assert rec["violations"][0]["key"] == "bright" and len(rec["hash"]) == 16


def test_xlsx_report_when_openpyxl_is_present(folder, tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    p = tmp_path / "lot.xlsx"
    inspect_batch(folder, None, measure=_measure, spec=SPEC, report_path=p, title="Lot 42")
    ws = openpyxl.load_workbook(str(p))["Report"]
    vals = [c.value for row in ws.iter_rows() for c in row if c.value is not None]
    assert ws["A1"].value == "Lot 42"
    assert "part_05.npy" in vals and "ng" in vals and 900.0 in vals


@pytest.mark.parametrize("bad", ["lot.csv", "lot"])
def test_unknown_report_extension_is_refused(folder, tmp_path, bad):
    with pytest.raises(ValueError):
        inspect_batch(folder, None, measure=_measure, report_path=tmp_path / bad)


def test_empty_folder_and_broken_spec_fail_closed(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ValueError):
        inspect_batch(empty, None, measure=_measure)
    np.save(tmp_path / "one.npy", _plate())
    with pytest.raises(ValueError):
        inspect_batch([tmp_path / "one.npy"], None, measure=_measure, spec={"mean": {"mx": 1}})
    with pytest.raises(ValueError):
        inspect_batch([tmp_path / "one.npy"], None, measure=_measure, on_error="ignore")


def test_explicit_path_list_keeps_the_given_order(tmp_path):
    a, b = tmp_path / "b.npy", tmp_path / "a.npy"
    np.save(a, _plate()); np.save(b, _plate())
    out = inspect_batch([a, b], None, measure=_measure)
    assert [os.path.basename(r["path"]) for r in out["rows"]] == ["b.npy", "a.npy"]


def test_facade_exposes_the_workflow_layer():
    assert fs.inspect_batch is inspect_batch and fs.as_verdict is as_verdict
    assert {"inspect_batch", "as_verdict", "judge"} <= set(fs.__all__)
