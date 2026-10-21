"""Studio slice 8: deterministic folder batch application."""
import csv
from pathlib import Path

import numpy as np
import pytest

import imgio
import studio_batch as batch


def _images(tmp_path, count=5):
    root = tmp_path / "inputs"; root.mkdir()
    files = []
    for index in range(count):
        path = root / ("part_%03d.png" % index)
        imgio.save(str(path), np.full((4, 5), index, np.uint8)); files.append(path.resolve())
    (root / "broken.png").write_bytes(b"not an image")
    (root / "notes.txt").write_text("ignore", encoding="utf-8")
    return root, files


def test_listing_and_preview_are_deterministic(tmp_path):
    root, files = _images(tmp_path)
    listed = batch.list_inputs(root)
    assert listed == [root.resolve() / "broken.png", *files]
    assert batch.preview_pick(listed, "first") == listed[0]
    assert batch.preview_pick(listed, "middle") == listed[3]
    assert batch.preview_pick(listed, "last") == listed[-1]
    assert batch.preview_pick(listed, files[1]) == files[1]
    with pytest.raises(ValueError, match="not in the input set"):
        batch.preview_pick(listed, root / "notes.txt")


def test_output_policies_and_recursive_mirroring(tmp_path):
    root, _ = _images(tmp_path, 1)
    nested = root / "sub"; nested.mkdir()
    source = nested / "deep.png"; imgio.save(str(source), np.ones((2, 2), np.uint8))
    out = tmp_path / "out"
    target = batch.output_path(source, root, out, "skip")
    assert target == out.resolve() / "sub" / "deep.png"
    target.parent.mkdir(parents=True); target.write_bytes(b"old")
    assert batch.output_path(source, root, out, "overwrite") == target
    assert batch.output_path(source, root, out, "suffix").name == "deep_1.png"
    assert source.resolve() in batch.list_inputs(root, recursive=True)
    with pytest.raises(ValueError, match="unknown"):
        batch.output_path(source, root, out, "rename")


def test_skip_never_runs_or_writes_existing_target(tmp_path):
    root, files = _images(tmp_path, 1)
    out = tmp_path / "out"; out.mkdir()
    target = out / files[0].name; target.write_bytes(b"keep")
    plan = batch.BatchPlan(files, out, "skip", folder=root)
    called = []
    result = batch.run_batch(plan, lambda path: called.append(path),
                             should_stop=lambda: False, on_progress=lambda *_: None)
    assert called == []
    assert target.read_bytes() == b"keep"
    assert result.statuses[files[0]] == "skipped"


def test_failure_continues_numeric_csv_and_suffix(tmp_path):
    root, files = _images(tmp_path, 3)
    broken = root.resolve() / "broken.png"
    ordered = batch.list_inputs(root)
    out = tmp_path / "out"
    (out / files[0].name).parent.mkdir(parents=True)
    (out / files[0].name).write_bytes(b"occupied")
    progress = []

    def run_one(path):
        if path == broken:
            raise OSError("cannot decode")
        value = int(path.stem.rsplit("_", 1)[1])
        return {"final_image": np.full((3, 3), value, np.uint8),
                "numeric": {"regions": value + 2}}

    result = batch.run_batch(batch.BatchPlan(ordered, out, "suffix", folder=root), run_one,
                             should_stop=lambda: False,
                             on_progress=lambda *args: progress.append(args))
    assert result.done == 3
    assert result.failed == [(broken, "cannot decode")]
    assert (out / "part_000_1.png").is_file()
    assert len(progress) == 4
    with (out / "summary.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["status"] for row in rows] == ["failed", "ok", "ok", "ok"]
    assert rows[1]["regions"] == "2"
    assert rows[0]["error"] == "cannot decode"


def test_stop_after_two_completed_files(tmp_path):
    root, files = _images(tmp_path, 5)
    progress = []
    result = batch.run_batch(
        batch.BatchPlan(files, tmp_path / "out", "overwrite", folder=root),
        lambda path: {"final_image": np.zeros((2, 2), np.uint8), "numeric": {}},
        should_stop=lambda: len(progress) >= 2,
        on_progress=lambda *args: progress.append(args))
    assert result.done == 2
    assert result.stopped
    assert progress[-1][3] == "stopped"


def test_fail_closed_validation_and_summary(tmp_path):
    root, files = _images(tmp_path, 1)
    with pytest.raises(ValueError, match="does not exist"):
        batch.list_inputs(tmp_path / "missing")
    empty = tmp_path / "empty"; empty.mkdir()
    with pytest.raises(ValueError, match="no files"):
        batch.list_inputs(empty)
    with pytest.raises(ValueError, match="input set"):
        batch.BatchPlan(files, files[0], folder=root)
    with pytest.raises(ValueError, match="unknown"):
        batch.BatchPlan(files, tmp_path / "out", "mystery", folder=root)
    plan = batch.BatchPlan(files, root / "results", folder=root)
    assert plan.summary() == "対象 1 画像、出力先 results/、同名: 上書きしない"


def test_dialog_plan_and_worker_submission_use_one_generation(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtWidgets
    import studio

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    root, files = _images(tmp_path, 2)
    win, model = studio.build_window()
    win._actions["batch_apply"].trigger(); app.processEvents()
    fields = win._batch_dialog_fields
    fields["folder"].setText(str(root)); fields["output"].setText(str(tmp_path / "out"))
    fields["patterns"].setText("part_*.png")
    plan = win._batch_plan_from_dialog()
    assert plan.files == files
    assert plan.policy == "skip"
    before = win._run_controller.generation
    generation = win._start_batch_async(plan)
    assert generation == before + 1
    assert win._batch_generation == generation
    assert win._run_snapshots[generation]["generation"] == generation
    frozen = win._run_snapshots[generation]["stages"]
    model.add_stage("invert", 0.5, 0.5)
    assert win._run_snapshots[generation]["stages"] == frozen
    win.quiesce()
    win.close_guard = lambda: True; win.close(); app.processEvents()
