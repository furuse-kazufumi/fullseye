# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""``fullseye.validation_kit`` —— 手元のデータで能力を確かめ、集計値だけを出す道具の門。

The validation kit must (1) get the numbers right against a known truth, (2) never
write pixels, file names or paths into its JSON, and (3) refuse broken input instead
of aggregating a partial set.

★この試験ファイルには op の名前を書かない(``tools/gen_maturity.py`` が ``tests/``
の op 名を数えるので、書くと成熟度台帳の事実が動く)。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import fullseye.validation_kit as VK  # noqa: E402

SECRET = "confidential_part_7731"


def _disks(n_obj: int, size: int = 96, seed: int = 0) -> np.ndarray:
    """互いに離れた明るい円板を n_obj 個置いた灰色画像(真値 = n_obj)。"""
    rng = np.random.default_rng(seed)
    img = 0.1 + 0.02 * rng.random((size, size))
    yy, xx = np.mgrid[0:size, 0:size]
    centres = [(16 + 32 * (k // 3), 16 + 32 * (k % 3)) for k in range(n_obj)]
    for cy, cx in centres:
        img[(yy - cy) ** 2 + (xx - cx) ** 2 < 64] = 0.9
    return img


def _manifest(tmp_path, counts, truths=None, dark=False):
    d = tmp_path / SECRET
    d.mkdir()
    lines = ["file,truth"]
    for i, c in enumerate(counts):
        img = _disks(c, seed=i)
        if dark:
            img = 1.0 - img
        name = "%s_%02d.npy" % (SECRET, i)
        np.save(d / name, img)
        lines.append("%s,%s" % (name, (truths or counts)[i]))
    m = d / "truth.csv"
    m.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(m)


def test_known_counts_are_measured_exactly(tmp_path):
    res = VK.run_kit("blob-count", _manifest(tmp_path, [1, 3, 5, 9]))
    m = res["metrics"]
    assert m["n"] == 4 and res["inputs"]["count"] == 4
    assert m["mean_abs_error"] == 0.0 and m["max_abs_error"] == 0.0
    assert m["exact_match_rate"] == 1.0
    assert res["capability"] == "blob-and-region"
    assert all(re.fullmatch(r"[0-9a-f]{64}", h) for h in res["inputs"]["sha256"])


def test_errors_against_a_wrong_truth_are_signed_and_scaled(tmp_path):
    """真値を 1 つずらすと、符号つきの誤差と絶対値がその通りに出る(比率だけの試験にしない)。"""
    res = VK.run_kit("blob-count", _manifest(tmp_path, [2, 4], truths=[3, 4]))
    m = res["metrics"]
    assert m["mean_signed_error"] == pytest.approx(-0.5)
    assert m["mean_abs_error"] == pytest.approx(0.5)
    assert m["max_abs_error"] == pytest.approx(1.0)
    assert m["exact_match_rate"] == pytest.approx(0.5)
    assert m["mean_abs_relative_error"] == pytest.approx((1 / 3) / 2)


def test_dark_objects_need_invert(tmp_path):
    res = VK.run_kit("blob-count", _manifest(tmp_path, [3, 6], dark=True), {"invert": True})
    assert res["metrics"]["exact_match_rate"] == 1.0
    assert res["parameters"]["invert"] is True


def test_the_json_carries_no_names_paths_or_pixels(tmp_path):
    """★本体。出力に、ファイル名・ディレクトリ名・画素の並びが 1 つも無いこと。"""
    man = _manifest(tmp_path, [2, 3, 4])
    out = tmp_path / "result.json"
    r = subprocess.run([sys.executable, "-m", "fullseye.validation_kit", "run", "blob-count",
                        "--manifest", man, "--out", str(out)],
                       cwd=ROOT, capture_output=True, text=True, errors="replace",
                       env=dict(os.environ, PYTHONPATH=ROOT))
    assert r.returncode == 0, r.stderr
    text = out.read_text(encoding="utf-8")
    assert SECRET not in text and str(tmp_path) not in text
    assert ".npy" not in text and "truth.csv" not in text
    d = json.loads(text)
    assert set(d) == {"kit_schema", "kit", "capability", "unit", "parameters",
                      "fullseye_version", "fullseye_commit", "environment", "inputs",
                      "metrics", "privacy"}
    assert set(d["environment"]) == {"python", "numpy", "os", "machine"}
    # 長い数値の並び(画素の漏れ)が無い: リストはハッシュ列だけ
    lists = [v for v in d["inputs"].values() if isinstance(v, list)]
    assert lists == [d["inputs"]["sha256"]]


def test_no_hashes_option(tmp_path):
    res = VK.run_kit("blob-count", _manifest(tmp_path, [1]), hashes=False)
    assert res["inputs"]["sha256"] is None and res["metrics"]["std_error"] is None


@pytest.mark.parametrize("body, needle", [
    ("name,value\nx,1\n", "header"),
    ("file,truth\n", "no data rows"),
    ("file,truth\nmissing.npy,1\n", "file not found"),
    ("file,truth\n,1\n", "empty file"),
    ("file,truth\nIMG,abc\n", "not a number"),
    ("file,truth\nIMG,nan\n", "not finite"),
])
def test_broken_manifests_are_refused(tmp_path, body, needle):
    np.save(tmp_path / "img.npy", _disks(1))
    m = tmp_path / "truth.csv"
    m.write_text(body.replace("IMG", "img.npy"), encoding="utf-8")
    with pytest.raises(VK.KitError, match=needle):
        VK.run_kit("blob-count", str(m))


def test_bad_images_and_unknown_names_are_refused(tmp_path):
    np.save(tmp_path / "a.npy", np.full((8, 8), np.nan))
    np.save(tmp_path / "b.npy", np.zeros(5))
    for name in ("a.npy", "b.npy"):
        m = tmp_path / ("%s.csv" % name)
        m.write_text("file,truth\n%s,1\n" % name, encoding="utf-8")
        with pytest.raises(VK.KitError):
            VK.run_kit("blob-count", str(m))
    with pytest.raises(VK.KitError, match="unknown kit"):
        VK.run_kit("no-such-kit", str(m))
    with pytest.raises(VK.KitError, match="no parameter"):
        VK.run_kit("blob-count", str(m), {"threshold": 0.5})


def test_every_kit_names_a_real_capability():
    with open(os.path.join(ROOT, "docs", "maturity.json"), encoding="utf-8") as fh:
        caps = {r["id"] for r in json.load(fh)["capabilities"]}
    assert VK.KITS, "kit が 1 つも無い"
    for k in VK.KITS.values():
        assert k.capability in caps, k.name


def test_the_cli_lists_kits_and_returns_2_on_bad_input(tmp_path):
    env = dict(os.environ, PYTHONPATH=ROOT)
    r = subprocess.run([sys.executable, "-m", "fullseye.validation_kit", "list"],
                       cwd=ROOT, capture_output=True, text=True, env=env)
    assert r.returncode == 0 and "blob-count" in r.stdout
    r = subprocess.run([sys.executable, "-m", "fullseye.validation_kit", "run", "blob-count",
                        "--manifest", str(tmp_path / "absent.csv")],
                       cwd=ROOT, capture_output=True, text=True, env=env)
    assert r.returncode == 2 and "manifest not found" in r.stderr
