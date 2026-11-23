"""規制実行 envelope の正負試験 / Positive and negative tests for the regulated envelope."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pytest

import api
import fullseye as fs


FIXED_TIME = datetime(2026, 11, 23, 3, 4, 5, tzinfo=timezone.utc)
INPUT = np.arange(64, dtype=np.float64).reshape(8, 8) / 63.0


def _context(run_id: str, *, seed=7, profile=True) -> fs.ExecutionContext:
    """固定時刻の文脈 / Build a context with a fixed UTC clock."""
    validation_profile = fs.ValidationProfile(seed=seed) if profile else None
    return fs.ExecutionContext(
        principal="operator-17",
        session="session-4",
        validation_profile=validation_profile,
        run_id=run_id,
        utc_time_source=lambda: FIXED_TIME,
    )


def _records(path):
    """試験内だけで JSONL を読む / Read JSONL only inside tests."""
    return [json.loads(line)["record"] for line in path.read_text(encoding="utf-8").splitlines()]


def test_no_profile_preserves_behavior_and_creates_no_record(tmp_path):
    sink_path = tmp_path / "not-created.jsonl"
    got = fs.apply(INPUT, "identity", execution_context=_context("plain", profile=False),
                   audit_sink=fs.AuditSink(sink_path))
    assert np.array_equal(got, INPUT)
    assert not sink_path.exists()


def test_success_failure_and_cancellation_each_write_exactly_one_record(tmp_path, monkeypatch):
    path = tmp_path / "audit.jsonl"
    sink = fs.AuditSink(path)

    got = fs.apply(INPUT, "identity", execution_context=_context("success"), audit_sink=sink)
    assert np.array_equal(got, INPUT)

    with pytest.raises(KeyError):
        fs.apply(INPUT, "definitely_not_an_operator", execution_context=_context("failure"),
                 audit_sink=sink)

    original = api._apply_unrecorded

    def cancel(*_args, **_kwargs):
        raise KeyboardInterrupt("operator cancelled")

    monkeypatch.setattr(api, "_apply_unrecorded", cancel)
    with pytest.raises(KeyboardInterrupt):
        fs.apply(INPUT, "identity", execution_context=_context("cancelled"), audit_sink=sink)
    monkeypatch.setattr(api, "_apply_unrecorded", original)

    records = _records(path)
    assert [record["status"] for record in records] == ["succeeded", "failed", "cancelled"]
    assert [record["run_id"] for record in records] == ["success", "failure", "cancelled"]
    assert sink.checkpoint().record_count == 3


def test_pipeline_writes_one_record_with_normalized_stages(tmp_path):
    path = tmp_path / "pipeline.jsonl"
    got = fs.run_pipeline(
        INPUT,
        [("identity", {"a": 0.2}), {"op": "invert", "b": 0.8}],
        execution_context=_context("pipeline"),
        audit_sink=fs.AuditSink(path),
    )
    assert np.array_equal(got, 1.0 - INPUT)
    [record] = _records(path)
    assert record["status"] == "succeeded"
    assert record["stages"] == [
        {"a": 0.2, "b": 0.5, "index": 0, "name": "identity"},
        {"a": 0.5, "b": 0.8, "index": 1, "name": "invert"},
    ]


def test_audit_failure_prevents_result_from_being_returned(monkeypatch):
    ran = []

    class BrokenSink:
        def append(self, _record):
            raise OSError("injected write failure")

    original = api._apply_unrecorded

    def marked(*args, **kwargs):
        ran.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(api, "_apply_unrecorded", marked)
    with pytest.raises(fs.AuditWriteError, match="audit append failed"):
        fs.apply(INPUT, "identity", execution_context=_context("write-failure"),
                 audit_sink=BrokenSink())
    assert ran == [True]


def test_stochastic_operator_rejects_none_seed_and_records_failure(tmp_path):
    path = tmp_path / "seed.jsonl"
    with pytest.raises(fs.ValidationProfileError, match="requires ValidationProfile.seed"):
        fs.apply(INPUT, "add_noise_white", execution_context=_context("seed-none", seed=None),
                 audit_sink=fs.AuditSink(path))
    [record] = _records(path)
    assert record["status"] == "failed"
    assert record["error_type"] == "ValidationProfileError"


def test_profile_forces_raise_nonfinite_cpu_environment_and_blas(tmp_path, monkeypatch):
    path = tmp_path / "policy.jsonl"
    sink = fs.AuditSink(path)
    with pytest.raises(Exception, match="NaN or infinity"):
        fs.apply(np.full((4, 4), np.nan), "identity", allow_nonfinite=True,
                 on_error="fallback", execution_context=_context("nonfinite"), audit_sink=sink)
    with pytest.raises(fs.ValidationProfileError, match="device='cpu' only"):
        fs.apply(INPUT, "identity", device="cuda", execution_context=_context("gpu"), audit_sink=sink)
    monkeypatch.setenv("FULLSEYE_FAST", "1")
    with pytest.raises(fs.ValidationProfileError, match="environment overrides"):
        fs.apply(INPUT, "identity", execution_context=_context("environment"), audit_sink=sink)
    records = _records(path)
    assert [row["status"] for row in records] == ["failed", "failed", "failed"]
    assert all(row["device"] == "cpu" for row in records)
    assert all(row["normalized_parameters"]["on_error"] == "raise" for row in records)
    assert all(row["software"]["blas_threads"] == 1 for row in records)


def test_same_input_and_profile_produce_same_output_hash(tmp_path):
    hashes = []
    outputs = []
    for index in range(2):
        path = tmp_path / f"repeat-{index}.jsonl"
        outputs.append(fs.apply(INPUT, "add_noise_white", a=0.3, b=0.2,
                                execution_context=_context(f"repeat-{index}"),
                                audit_sink=fs.AuditSink(path)))
        hashes.append(_records(path)[0]["outputs"][0]["sha256"])
    assert np.array_equal(outputs[0], outputs[1])
    assert hashes[0] == hashes[1]


def test_record_contains_hashes_not_image_data_or_input_path(tmp_path):
    audit_path = tmp_path / "privacy.jsonl"
    input_path = "C:/secret/patient-0042/image-17.dcm"
    fs.apply(input_path, "identity", execution_context=_context("privacy"),
             audit_sink=fs.AuditSink(audit_path))
    text = audit_path.read_text(encoding="utf-8")
    assert input_path not in text
    assert "patient-0042" not in text
    [record] = _records(audit_path)
    assert len(record["inputs"][0]["sha256"]) == 64
    assert record["inputs"][0]["storage_id"].startswith("sha256:")
    assert "data" not in record["inputs"][0]


def _three_record_chain(path):
    sink = fs.AuditSink(path)
    for index in range(3):
        fs.apply(INPUT + index * 0.0, "identity", execution_context=_context(f"run-{index}"),
                 audit_sink=sink)
    return sink.checkpoint(), path.read_bytes().splitlines(keepends=True)


def test_verifier_detects_one_byte_change(tmp_path):
    path = tmp_path / "byte.jsonl"
    checkpoint, lines = _three_record_chain(path)
    lines[0] = lines[0].replace(b"operator-17", b"operator-18", 1)
    path.write_bytes(b"".join(lines))
    with pytest.raises(fs.AuditIntegrityError):
        fs.verify_audit_file(path, checkpoint=checkpoint)


def test_verifier_detects_record_deletion_including_tail(tmp_path):
    path = tmp_path / "delete.jsonl"
    checkpoint, lines = _three_record_chain(path)
    path.write_bytes(b"".join(lines[:-1]))
    with pytest.raises(fs.AuditIntegrityError, match="trusted checkpoint"):
        fs.verify_audit_file(path, checkpoint=checkpoint)


def test_verifier_detects_record_reordering(tmp_path):
    path = tmp_path / "order.jsonl"
    checkpoint, lines = _three_record_chain(path)
    lines[0], lines[1] = lines[1], lines[0]
    path.write_bytes(b"".join(lines))
    with pytest.raises(fs.AuditIntegrityError):
        fs.verify_audit_file(path, checkpoint=checkpoint)


def test_verifier_detects_record_from_another_run(tmp_path):
    path = tmp_path / "main.jsonl"
    checkpoint, lines = _three_record_chain(path)
    other = tmp_path / "other.jsonl"
    fs.apply(INPUT, "identity", execution_context=_context("foreign-run"),
             audit_sink=fs.AuditSink(other))
    foreign = other.read_bytes().splitlines(keepends=True)[0]
    path.write_bytes(lines[0] + foreign + lines[2])
    with pytest.raises(fs.AuditIntegrityError):
        fs.verify_audit_file(path, checkpoint=checkpoint)


def test_canonical_json_is_stable_and_refuses_nonfinite():
    assert fs.canonical_json({"z": 1, "a": [True, "日本語"]}) == '{"a":[true,"日本語"],"z":1}'
    with pytest.raises(ValueError, match="NaN and infinity"):
        fs.canonical_json({"bad": float("nan")})
