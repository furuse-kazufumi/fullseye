"""規制実行 envelope の正負試験 / Positive and negative tests for the regulated envelope."""

from __future__ import annotations

import base64
import contextlib
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

import api
import execution_record as execution_record
import fsthreads
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


def test_audit_failure_prevents_result_from_being_returned(tmp_path, monkeypatch):
    ran = []

    original = api._apply_unrecorded

    def marked(*args, **kwargs):
        ran.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(api, "_apply_unrecorded", marked)
    sink = fs.AuditSink(tmp_path / "broken.jsonl")
    monkeypatch.setattr(sink, "append", lambda _record: (_ for _ in ()).throw(OSError("injected write failure")))
    with pytest.raises(fs.AuditWriteError, match="audit append failed"):
        fs.apply(INPUT, "identity", execution_context=_context("write-failure"),
                 audit_sink=sink)
    assert ran == [True]


def test_noop_sink_is_rejected_before_an_output_can_be_returned():
    """耐久性を検査できない sink は規制実行に使えない / Reject an unverifiable no-op sink."""
    ran = []

    class NoOpSink:
        def append(self, _record):
            return None

    def operation(*_args, **_kwargs):
        ran.append(True)
        return INPUT

    original = api._apply_unrecorded
    try:
        api._apply_unrecorded = operation
        with pytest.raises(fs.ValidationProfileError, match="durable AuditSink"):
            fs.apply(INPUT, "identity", execution_context=_context("no-op"), audit_sink=NoOpSink())
    finally:
        api._apply_unrecorded = original
    assert ran == []


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


def test_nonfinite_knob_records_the_original_failure_with_safe_audit_value(tmp_path):
    """NaN knob でも失敗を監査する / Audit the original failure when a knob is NaN."""
    path = tmp_path / "nonfinite-knob.jsonl"
    with pytest.raises(ValueError, match="finite"):
        fs.apply(INPUT, "identity", a=float("nan"), execution_context=_context("nonfinite-knob"),
                 audit_sink=fs.AuditSink(path))
    [record] = _records(path)
    assert record["status"] == "failed"
    assert record["error_type"] == "ValueError"
    assert record["stages"][0]["a"] == {"invalid_value": "nonfinite"}


def test_unavailable_blas_control_fails_closed_and_records_no_success(tmp_path, monkeypatch):
    """threadpoolctl が使えない規制実行は拒否する / Reject regulated execution without BLAS control."""
    path = tmp_path / "blas-unavailable.jsonl"

    @contextlib.contextmanager
    def unavailable_threads(_threads):
        yield False

    monkeypatch.setattr(fsthreads, "validation_threads", unavailable_threads)
    with pytest.raises(fs.ValidationProfileError, match="BLAS thread limit"):
        fs.apply(INPUT, "identity", execution_context=_context("blas-unavailable"), audit_sink=fs.AuditSink(path))
    [record] = _records(path)
    assert record["status"] == "failed"
    assert record["outputs"] == []


def test_artifact_ref_rejects_non_string_mapping_keys_without_aliasing():
    """型の異なる mapping key を同じ入力へ潰さない / Refuse mapping keys that could alias by stringification."""
    with pytest.raises(TypeError, match="mapping keys must be strings"):
        fs.artifact_ref({1: "x"})
    string_key = fs.artifact_ref({"1": "x"})
    assert string_key.artifact_type == "dict"


def test_source_state_is_recomputed_for_each_record(monkeypatch):
    """tracked source の変更を次の record が見落とさない / Do not cache tracked-source provenance."""
    tracked_diff = {"value": b"first"}

    def fake_git(*args):
        if args == ("rev-parse", "HEAD"):
            return b"0123456789abcdef\n"
        if args[0] == "diff":
            return tracked_diff["value"]
        return b""

    monkeypatch.setattr(execution_record, "_run_git", fake_git)
    first = execution_record._source_state()
    tracked_diff["value"] = b"second"
    second = execution_record._source_state()
    assert first[0] != second[0]


@pytest.mark.parametrize(
    ("failed_command", "component"),
    [
        (("status", "--porcelain=v1", "-z", "--untracked-files=all"), "status"),
        (("diff", "--no-ext-diff", "--binary", "HEAD", "--", "."), "diff"),
        (("ls-files", "--others", "--exclude-standard", "-z"), "untracked files"),
    ],
    ids=("status", "diff", "untracked-files"),
)
def test_partial_git_provenance_failure_is_rejected(monkeypatch, failed_command, component):
    """HEAD 後の部分取得失敗を空出力と扱わない / Reject partial git provenance failures."""

    def partial_git(*args):
        if args == failed_command:
            return None
        if args == ("rev-parse", "HEAD"):
            return b"0123456789abcdef\n"
        return b""

    monkeypatch.setattr(execution_record, "_run_git", partial_git)
    with pytest.raises(execution_record.SoftwareProvenanceError, match=component):
        execution_record._source_state()


def test_unverifiable_editable_wheel_provenance_rejects_regulated_output(tmp_path, monkeypatch):
    """git の無い editable install は規制 output を確定できない / Reject output without git or a verifiable wheel."""
    path = tmp_path / "unverifiable.jsonl"
    monkeypatch.setattr(execution_record, "_run_git", lambda *_args: b"")
    with pytest.raises(execution_record.SoftwareProvenanceError, match="provenance|wheel RECORD"):
        fs.apply(INPUT, "identity", execution_context=_context("unverifiable-wheel"),
                 audit_sink=fs.AuditSink(path))
    assert not path.exists()


def test_wheel_record_provenance_verifies_payload_for_non_git_execution(tmp_path, monkeypatch):
    """wheel RECORD の対象payloadと改ざんを検査する / Verify wheel payloads and reject tampering."""
    root = tmp_path / "site-packages"
    root.mkdir()
    source = root / "execution_record.py"
    source.write_bytes(b"verified payload")
    payload_hash = base64.urlsafe_b64encode(hashlib.sha256(source.read_bytes()).digest()).rstrip(b"=").decode()

    class WheelDistribution:
        version = "0.9.0"

        def locate_file(self, relative_name):
            return root / Path(relative_name)

        def read_text(self, name):
            assert name == "RECORD"
            return f"execution_record.py,sha256={payload_hash},{source.stat().st_size}\nRECORD,,\n"

    monkeypatch.setattr(execution_record, "_ROOT", root)
    monkeypatch.setattr(execution_record, "__file__", str(source))
    monkeypatch.setattr(execution_record.importlib.metadata, "distribution", lambda _name: WheelDistribution())
    digest, dirty = execution_record._wheel_record_state()
    assert len(digest) == 64
    assert dirty is False

    source.write_bytes(b"tampered payload")
    with pytest.raises(execution_record.SoftwareProvenanceError, match="does not match"):
        execution_record._wheel_record_state()


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
