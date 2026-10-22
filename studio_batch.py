"""Qt-free planning and execution for Studio folder batches."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
import os
from pathlib import Path
import time
from typing import Callable, Iterable

import numpy as np


_POLICIES = {"skip", "overwrite", "suffix"}
_POLICY_LABELS = {
    "skip": "上書きしない",
    "overwrite": "上書き",
    "suffix": "連番を付ける",
}


def list_inputs(folder, patterns=("*.png", "*.jpg", "*.jpeg", "*.tif", "*.tiff", "*.bmp"),
                recursive=False):
    """Return matching files in deterministic relative-path order."""
    root = Path(folder).expanduser()
    if not root.is_dir():
        raise ValueError("input folder does not exist: %s" % root)
    pats = tuple(p.strip() for p in patterns if str(p).strip())
    if not pats:
        raise ValueError("at least one input pattern is required")
    found = set()
    for pattern in pats:
        iterator = root.rglob(pattern) if recursive else root.glob(pattern)
        found.update(path.resolve() for path in iterator if path.is_file())
    files = sorted(found, key=lambda path: path.relative_to(root.resolve()).as_posix().casefold())
    if not files:
        raise ValueError("no files match the input patterns")
    return files


def preview_pick(files, which):
    """Pick a representative file by position, or validate an explicit path."""
    items = [Path(path).resolve() for path in files]
    if not items:
        raise ValueError("no input files are available for preview")
    if which == "first":
        return items[0]
    if which == "middle":
        return items[len(items) // 2]
    if which == "last":
        return items[-1]
    selected = Path(which).expanduser().resolve()
    if selected not in items:
        raise ValueError("preview file is not in the input set: %s" % selected)
    return selected


def output_path(src, folder, out_dir, policy):
    """Resolve an output path, mirroring the source's relative subdirectory."""
    if policy not in _POLICIES:
        raise ValueError("unknown same-name policy: %s" % policy)
    source = Path(src).resolve()
    root = Path(folder).resolve()
    output = Path(out_dir).resolve()
    try:
        relative = source.relative_to(root)
    except ValueError as exc:
        raise ValueError("input file is outside the input folder: %s" % source) from exc
    target = output / relative
    if policy != "suffix" or not target.exists():
        return target
    for index in range(1, 1_000_000):
        candidate = target.with_name("%s_%d%s" % (target.stem, index, target.suffix))
        if not candidate.exists():
            return candidate
    raise ValueError("could not allocate a suffixed output name for %s" % target)


@dataclass
class BatchPlan:
    files: list
    out_dir: Path | str
    policy: str = "skip"
    what_to_save: dict = field(default_factory=lambda: {
        "final_image": True, "numeric_csv": True,
    })
    folder: Path | str | None = None

    def __post_init__(self):
        self.files = [Path(path).resolve() for path in self.files]
        if not self.files:
            raise ValueError("the batch has no input files")
        missing = [path for path in self.files if not path.is_file()]
        if missing:
            raise ValueError("input file does not exist: %s" % missing[0])
        if self.policy not in _POLICIES:
            raise ValueError("unknown same-name policy: %s" % self.policy)
        self.out_dir = Path(self.out_dir).expanduser().resolve()
        if any(path == self.out_dir or self.out_dir in path.parents for path in self.files):
            raise ValueError("output folder is inside the selected input set")
        if self.folder is None:
            common = Path(os.path.commonpath([str(path.parent) for path in self.files]))
            self.folder = common.resolve()
        else:
            self.folder = Path(self.folder).expanduser().resolve()
        for path in self.files:
            try:
                path.relative_to(self.folder)
            except ValueError as exc:
                raise ValueError("input file is outside the input folder: %s" % path) from exc
        unknown = set(self.what_to_save) - {"final_image", "numeric_csv"}
        if unknown:
            raise ValueError("unknown output selection: %s" % sorted(unknown)[0])

    def summary(self):
        shown = self.out_dir.name + "/"
        return "対象 %d 画像、出力先 %s、同名: %s" % (
            len(self.files), shown, _POLICY_LABELS[self.policy])


@dataclass(frozen=True)
class BatchResult:
    done: int
    failed: list
    stopped: bool
    elapsed_ms: dict
    numeric_outputs: dict
    statuses: dict = field(default_factory=dict)
    summary_path: Path | None = None


def _numeric_values(result):
    values = result.get("numeric", {}) if isinstance(result, dict) else {}
    if not isinstance(values, dict):
        raise TypeError("numeric output must be a mapping")
    values = {**{key: value for key, value in result.items()
                 if key not in {"final_image", "numeric"}}, **values}
    answer = {}
    for key, value in values.items():
        array = np.asarray(value)
        if array.size == 1 and array.dtype.kind in "biufc":
            answer[str(key)] = array.reshape(()).item()
    return answer


def _save_image(path, value):
    import imgio
    path.parent.mkdir(parents=True, exist_ok=True)
    imgio.save(str(path), np.asarray(value))


def run_batch(plan, run_one: Callable, *, should_stop: Callable, on_progress: Callable):
    """Run every planned file, preserving failures and writing ``summary.csv``."""
    if not isinstance(plan, BatchPlan):
        raise TypeError("plan must be a BatchPlan")
    plan.out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    failed = []
    elapsed = {}
    numeric = {}
    statuses = {}
    done = 0
    stopped = False
    total = len(plan.files)
    for index, source in enumerate(plan.files, 1):
        if should_stop():
            stopped = True
            on_progress(done, total, source, "stopped")
            break
        target = output_path(source, plan.folder, plan.out_dir, plan.policy)
        if (plan.what_to_save.get("final_image", True)
                and plan.policy == "skip" and target.exists()):
            statuses[source] = "skipped"
            elapsed[source] = 0.0
            rows.append((source, "skipped", 0.0, {}, ""))
            on_progress(index, total, source, "skipped")
            continue
        started = time.perf_counter()
        try:
            value = run_one(source)
            if not isinstance(value, dict):
                raise TypeError("run_one must return a dict")
            numbers = _numeric_values(value)
            if plan.what_to_save.get("final_image", True):
                if "final_image" not in value:
                    raise ValueError("run_one did not return final_image")
                _save_image(target, value["final_image"])
            status = "ok"
            error = ""
            numeric[source] = numbers
            done += 1
        except Exception as exc:
            status = "failed"
            error = str(exc)
            numbers = {}
            failed.append((source, error))
        ms = (time.perf_counter() - started) * 1000.0
        statuses[source] = status
        elapsed[source] = ms
        rows.append((source, status, ms, numbers, error))
        on_progress(index, total, source, status)
    columns = (sorted({key for _path, _status, _ms, nums, _err in rows for key in nums})
               if plan.what_to_save.get("numeric_csv", True) else [])
    summary_path = plan.out_dir / "summary.csv"
    with summary_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["file", "status", "ms", *columns, "error"])
        writer.writeheader()
        for source, status, ms, numbers, error in rows:
            row = {"file": str(source), "status": status, "ms": "%.3f" % ms,
                   "error": error}
            row.update({key: numbers[key] for key in columns if key in numbers})
            writer.writerow(row)
    return BatchResult(done, failed, stopped, elapsed, numeric, statuses, summary_path)
