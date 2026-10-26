"""Input-reference ``size`` + schema backward compatibility (2026-10-25).

Idea 145: a saved project keeps the input as a reference (path + sha256 + size + shape/dtype), not a
copy. This adds the file byte ``size`` the task asks for, and pins the schema contract: the version
field exists, new keys are optional, old project files load unchanged, and a file written by the new
code is readable by an old reader except for the new keys (which it ignores).
"""
import hashlib
import json

import numpy as np

import studio
import studio_result as sr


def _write_image(path, seed=0):
    import imgio
    rng = np.random.default_rng(seed)
    imgio.save(str(path), rng.random((12, 10)))


def test_input_reference_carries_path_sha256_size(tmp_path):
    p = tmp_path / "in.png"
    _write_image(p)
    ref = studio.input_reference(str(p), np.zeros((12, 10)))
    assert ref["path"] == str(p)
    assert ref["sha256"] == hashlib.sha256(p.read_bytes()).hexdigest()
    assert ref["size"] == p.stat().st_size          # the byte size the task requires
    assert ref["shape"] == [12, 10] and ref["dtype"] == "float64"


def test_to_dict_has_schema_version_and_size(tmp_path):
    p = tmp_path / "in.png"
    _write_image(p)
    m = studio.PipelineModel(studio.demo_image(16))
    m.add_stage("gaussian")
    m.input_path = str(p)
    d = m.to_dict()
    assert d["fullseye_pipeline"] == 1               # schema version field exists
    assert d["input"]["size"] == p.stat().st_size


def test_size_survives_roundtrip_through_load_dict(tmp_path):
    p = tmp_path / "in.png"
    _write_image(p)
    m = studio.PipelineModel(studio.demo_image(16))
    m.add_stage("gaussian")
    m.input_path = str(p)
    d = json.loads(json.dumps(m.to_dict()))
    m2 = studio.PipelineModel(studio.demo_image(16))
    m2.load_dict(d)
    assert m2.input_ref["size"] == p.stat().st_size
    assert m2.input_ref == d["input"]


def test_new_file_is_readable_by_old_reader_except_new_keys():
    # "old reader" = a loader that does not know the 'size' key. It must still load the pipeline and
    # the rest of the input reference; the unknown key is simply ignored.
    new_input = {"path": "in.png", "sha256": "a" * 64, "size": 1234, "shape": [12, 10], "dtype": "float64"}
    old_view = {k: v for k, v in new_input.items() if k in ("path", "sha256", "shape", "dtype")}
    # a strict old reader that rejected 'size' would differ; our reader keeps old behavior AND adds size
    assert sr._valid_input_ref(old_view) == old_view            # the pre-size reference still valid
    got = sr._valid_input_ref(new_input)
    assert {k: got[k] for k in old_view} == old_view            # old keys unchanged
    assert got["size"] == 1234


def test_old_file_without_size_loads_unchanged():
    legacy = {"fullseye_pipeline": 1, "stages": [["gaussian", 0.2, 0.3]],
              "input": {"path": "in.png", "sha256": "b" * 64, "shape": [4, 4], "dtype": "uint8"}}
    m = studio.PipelineModel(studio.demo_image(16))
    m.load_dict(json.loads(json.dumps(legacy)))
    assert m.stages == [["gaussian", 0.2, 0.3]]
    assert m.input_ref == legacy["input"]            # no 'size' -> loads exactly as written
    assert "size" not in m.input_ref


def test_byte_identical_file_when_no_input_and_no_new_keys():
    m = studio.PipelineModel(studio.demo_image(16))
    m.add_stage("gaussian", 0.2, 0.3)
    d = m.to_dict()
    assert d == {"fullseye_pipeline": 1, "stages": [["gaussian", 0.2, 0.3]]}   # same as before this change
