"""規制実行のエンベロープと追記監査ログ / Regulated execution envelope and audit log.

研究用の演算本体や pipeline 定義には監査情報を混ぜず、明示された
:class:`ValidationProfile` の外側でだけ記録する。  The research execution path stays
data-only; records are created only by an explicitly selected validation profile.
"""
from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import datetime as _dt
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import threading
import uuid
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np


SCHEMA_ID = "fullseye.execution-record/v1"
GENESIS_RECORD_HASH = "0" * 64
SHA256_HEX_LENGTH = 64
DEFAULT_BLAS_THREADS = 1
AUDIT_FILE_MODE = 0o600
MAX_RANDOM_SEED = 2 ** 64 - 1
EXECUTION_STATUSES = frozenset({"succeeded", "failed", "cancelled"})

# 実行結果を変え得る既存の環境変数 / Existing environment overrides that can change results.
EXECUTION_ENVIRONMENT_VARIABLES = (
    "FULLSEYE_DEVICE",
    "FULLSEYE_FAST",
    "FULLSEYE_ON_ERROR",
    "FULLSEYE_STRICT",
    "FULLSEYE_BLAS_THREADS",
)

# これらは乱数を使うため seed 宣言を必須にする / These operators use random sampling.
# 演算側に固定 seed があるものも含め、規制記録では seed 方針を暗黙にしない。
# Operators with an internal fixed seed are included so the validation record never leaves
# the random-source policy implicit.
STOCHASTIC_OPERATOR_NAMES = frozenset({
    "aug_shot_noise",
    "aug_read_noise",
    "aug_cutout",
    "aug_fixed_pattern",
    "bootstrap_std_error",
    "add_noise_distribution",
    "add_noise_white",
    "hx_add_noise_contour",
    "img_to_counts",
    "r2_smallest_circle",
    "tb_cutout",
    "tb_dynsys_correlation_dimension",
    "tb_elastic_deform",
    "tb_jitter",
    "tb_pc_density_equalize",
    "tb_pc_poisson_disk",
    "tb_quantize",
    "tb_random_dropout",
    "tb_random_rotation",
    "tb_random_scale",
    "tb_sensor_capture",
    "tb_shape_perturb",
})

_ROOT = Path(__file__).resolve().parent
_PATH_LOCKS: dict[str, threading.RLock] = {}
_PATH_LOCKS_GUARD = threading.Lock()


class ValidationProfileError(ValueError):
    """規制プロファイル違反 / A regulated validation-profile violation."""


class AuditWriteError(RuntimeError):
    """監査追記を確定できなかった / The audit append could not be committed."""


class AuditIntegrityError(ValueError):
    """監査連鎖またはチェックポイントの不一致 / Audit-chain or checkpoint mismatch."""


def _require_sha256(value: Any, label: str) -> None:
    """完全な小文字 SHA-256 を検査する / Validate a complete lowercase SHA-256 digest."""
    if (not isinstance(value, str) or len(value) != SHA256_HEX_LENGTH
            or any(c not in "0123456789abcdef" for c in value)):
        raise ValueError(f"{label} must be a complete lowercase SHA-256 digest")


def _require_text(value: Any, label: str) -> None:
    """空でない文字列を検査する / Validate a non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")


def utc_now() -> _dt.datetime:
    """timezone-aware UTC を返す / Return a timezone-aware UTC timestamp."""
    return _dt.datetime.now(_dt.timezone.utc)


@dataclass(frozen=True)
class ValidationProfile:
    """CPU の認定実行条件 / Approved CPU-only execution conditions.

    ``seed`` は乱数を使う op では必須である。現行 registry の乱数 op は knob から
    seed を固定するか固定 seed を内蔵しており、この値はその規制上の宣言を記録する。
    ``seed`` is mandatory for stochastic operators; current registry operators derive or embed
    deterministic seeds, and this field records the approved seed declaration.
    """

    profile_id: str = "gxp-cpu-v1"
    seed: int | None = None
    blas_threads: int = DEFAULT_BLAS_THREADS
    prohibited_environment: tuple[str, ...] = EXECUTION_ENVIRONMENT_VARIABLES

    def __post_init__(self) -> None:
        _require_text(self.profile_id, "ValidationProfile.profile_id")
        if self.seed is not None and (isinstance(self.seed, bool) or not isinstance(self.seed, int)):
            raise TypeError("ValidationProfile.seed must be an integer or None")
        if self.seed is not None and not 0 <= self.seed <= MAX_RANDOM_SEED:
            raise ValueError(f"ValidationProfile.seed must be between 0 and {MAX_RANDOM_SEED}")
        if isinstance(self.blas_threads, bool) or not isinstance(self.blas_threads, int):
            raise TypeError("ValidationProfile.blas_threads must be an integer")
        if self.blas_threads != DEFAULT_BLAS_THREADS:
            raise ValueError(
                f"ValidationProfile.blas_threads must be {DEFAULT_BLAS_THREADS} for the CPU v1 profile")
        if not isinstance(self.prohibited_environment, tuple):
            raise TypeError("ValidationProfile.prohibited_environment must be a tuple")
        if any(not isinstance(name, str) or not name for name in self.prohibited_environment):
            raise ValueError("ValidationProfile.prohibited_environment entries must be non-empty strings")
        if len(set(self.prohibited_environment)) != len(self.prohibited_environment):
            raise ValueError("ValidationProfile.prohibited_environment must not contain duplicates")
        missing = sorted(set(EXECUTION_ENVIRONMENT_VARIABLES) - set(self.prohibited_environment))
        if missing:
            raise ValueError(
                "ValidationProfile.prohibited_environment cannot omit required variables: "
                + ", ".join(missing))


@dataclass(frozen=True)
class ExecutionContext:
    """実行者・session・run・時計・profile / Actor, session, run, clock, and profile."""

    principal: str
    session: str
    validation_profile: ValidationProfile | None = None
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_run_id: str | None = None
    utc_time_source: Callable[[], _dt.datetime] = field(default=utc_now, repr=False, compare=False)

    def __post_init__(self) -> None:
        for label, value in (("principal", self.principal), ("session", self.session),
                             ("run_id", self.run_id)):
            _require_text(value, f"ExecutionContext.{label}")
        if self.parent_run_id is not None and (
                not isinstance(self.parent_run_id, str) or not self.parent_run_id.strip()):
            raise ValueError("ExecutionContext.parent_run_id must be None or a non-empty string")
        if not callable(self.utc_time_source):
            raise TypeError("ExecutionContext.utc_time_source must be callable")

    def now(self) -> str:
        """時計を canonical UTC 文字列にする / Format the supplied clock as canonical UTC."""
        value = self.utc_time_source()
        if not isinstance(value, _dt.datetime) or value.tzinfo is None:
            raise ValueError("ExecutionContext.utc_time_source must return a timezone-aware datetime")
        return value.astimezone(_dt.timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class ArtifactRef:
    """データを含まない完全ハッシュ参照 / A full-hash reference containing no payload."""

    medium: str
    sha256: str
    size: int
    artifact_type: str
    storage_id: str

    def __post_init__(self) -> None:
        for label, value in (("medium", self.medium), ("artifact_type", self.artifact_type),
                             ("storage_id", self.storage_id)):
            _require_text(value, f"ArtifactRef.{label}")
        _require_sha256(self.sha256, "ArtifactRef.sha256")
        if isinstance(self.size, bool) or not isinstance(self.size, int) or self.size < 0:
            raise ValueError("ArtifactRef.size must be >= 0")


@dataclass(frozen=True)
class SoftwareInventory:
    """実行ソフトウェアと計算機の在庫 / Software and compute-host inventory."""

    fullseye_version: str
    source_digest: str
    source_dirty: bool
    python_version: str
    dependencies: dict[str, str]
    operating_system: str
    cpu: str
    gpu: str
    blas_threads: int

    def __post_init__(self) -> None:
        for label, value in (
                ("fullseye_version", self.fullseye_version), ("python_version", self.python_version),
                ("operating_system", self.operating_system), ("cpu", self.cpu), ("gpu", self.gpu)):
            _require_text(value, f"SoftwareInventory.{label}")
        _require_sha256(self.source_digest, "SoftwareInventory.source_digest")
        if not isinstance(self.source_dirty, bool):
            raise TypeError("SoftwareInventory.source_dirty must be a boolean")
        if (not isinstance(self.dependencies, dict)
                or any(not isinstance(k, str) or not isinstance(v, str)
                       for k, v in self.dependencies.items())):
            raise TypeError("SoftwareInventory.dependencies must map strings to strings")
        if isinstance(self.blas_threads, bool) or not isinstance(self.blas_threads, int):
            raise TypeError("SoftwareInventory.blas_threads must be an integer")


@dataclass(frozen=True)
class ExecutionRecord:
    """1 回の成功・失敗・取消を表す記録 / One successful, failed, or cancelled execution."""

    run_id: str
    parent_run_id: str | None
    child_run_ids: tuple[str, ...]
    principal: str
    session: str
    profile_id: str
    started_at: str
    finished_at: str
    inputs: tuple[ArtifactRef, ...]
    stages: tuple[dict[str, Any], ...]
    normalized_parameters: dict[str, Any]
    outputs: tuple[ArtifactRef, ...]
    status: str
    device: str
    degraded_events: tuple[dict[str, Any], ...]
    environment: dict[str, str | None]
    software: SoftwareInventory
    error_type: str | None
    error_message_sha256: str | None
    previous_record_hash: str = GENESIS_RECORD_HASH

    def __post_init__(self) -> None:
        for label, value in (("run_id", self.run_id), ("principal", self.principal),
                             ("session", self.session), ("profile_id", self.profile_id),
                             ("started_at", self.started_at), ("finished_at", self.finished_at),
                             ("device", self.device)):
            _require_text(value, f"ExecutionRecord.{label}")
        if self.parent_run_id is not None:
            _require_text(self.parent_run_id, "ExecutionRecord.parent_run_id")
        if self.status not in EXECUTION_STATUSES:
            raise ValueError(f"ExecutionRecord.status must be one of {sorted(EXECUTION_STATUSES)!r}")
        _require_sha256(self.previous_record_hash, "ExecutionRecord.previous_record_hash")
        if self.error_message_sha256 is not None:
            _require_sha256(self.error_message_sha256, "ExecutionRecord.error_message_sha256")
        if self.status == "succeeded" and (self.error_type is not None or self.error_message_sha256 is not None):
            raise ValueError("a succeeded ExecutionRecord cannot contain an error")
        if self.status != "succeeded" and not self.error_type:
            raise ValueError("a failed or cancelled ExecutionRecord must contain error_type")
        if not isinstance(self.software, SoftwareInventory):
            raise TypeError("ExecutionRecord.software must be SoftwareInventory")


@dataclass(frozen=True)
class AuditCheckpoint:
    """末尾削除も検知する外部アンカー / External anchor that also detects tail deletion."""

    record_count: int
    head_hash: str

    def __post_init__(self) -> None:
        if isinstance(self.record_count, bool) or not isinstance(self.record_count, int) or self.record_count < 0:
            raise ValueError("AuditCheckpoint.record_count must be >= 0")
        _require_sha256(self.head_hash, "AuditCheckpoint.head_hash")


@dataclass(frozen=True)
class AuditVerification:
    """監査検証の結果 / Result of audit verification."""

    checkpoint: AuditCheckpoint
    run_ids: tuple[str, ...]


def _json_value(value: Any) -> Any:
    """JSON 値を厳密に正規化する / Strictly normalize a value for canonical JSON."""
    if dataclasses.is_dataclass(value):
        return {f.name: _json_value(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, Mapping):
        out = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical JSON object keys must be strings")
            out[key] = _json_value(item)
        return out
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, np.generic):
        return _json_value(value.item())
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not np.isfinite(value):
            raise ValueError("canonical JSON refuses NaN and infinity")
        return value
    raise TypeError(f"canonical JSON does not support {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    """RFC 8259 の決定的 UTF-8 JSON を返す / Return deterministic RFC 8259 UTF-8 JSON."""
    return json.dumps(_json_value(value), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def canonical_json(value: Any) -> str:
    """canonical JSON の文字列版 / Text form of :func:`canonical_json_bytes`."""
    return canonical_json_bytes(value).decode("utf-8")


def _feed_artifact(h: Any, value: Any) -> int:
    """型付きバイト列を hash に送る / Feed a typed byte representation into a hash."""
    if hasattr(value, "to_dense") and not isinstance(value, np.ndarray):
        value = value.to_dense()
    if isinstance(value, np.ndarray):
        arr = np.asarray(value)
        header = canonical_json_bytes({"dtype": arr.dtype.str, "shape": list(arr.shape)})
        h.update(b"array\0" + len(header).to_bytes(8, "big") + header)
        if arr.dtype.kind == "O":
            total = len(header)
            for item in arr.flat:
                total += _feed_artifact(h, item)
            return total
        raw = np.ascontiguousarray(arr).tobytes(order="C")
        h.update(len(raw).to_bytes(8, "big") + raw)
        return len(header) + len(raw)
    if isinstance(value, Mapping):
        h.update(b"map\0" + len(value).to_bytes(8, "big"))
        total = 0
        for key in sorted(value, key=lambda x: str(x)):
            total += _feed_artifact(h, str(key))
            total += _feed_artifact(h, value[key])
        return total
    if isinstance(value, (list, tuple)):
        h.update(b"seq\0" + len(value).to_bytes(8, "big"))
        return sum(_feed_artifact(h, item) for item in value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        h.update(b"bytes\0" + len(raw).to_bytes(8, "big") + raw)
        return len(raw)
    if isinstance(value, np.generic):
        value = value.item()
    if value is None or isinstance(value, (str, bool, int, float, complex)):
        raw = repr(value).encode("utf-8")
        h.update(type(value).__name__.encode("ascii") + b"\0" + len(raw).to_bytes(8, "big") + raw)
        return len(raw)
    raise TypeError(f"artifact hashing does not support {type(value).__name__}")


def artifact_ref(value: Any, *, medium: str = "memory", storage_id: str | None = None) -> ArtifactRef:
    """値を露出せず完全 SHA-256 参照にする / Build a full SHA-256 reference without payload data."""
    h = hashlib.sha256()
    size = _feed_artifact(h, value)
    digest = h.hexdigest()
    if isinstance(value, np.ndarray):
        artifact_type = f"ndarray:{value.dtype.str}:{'x'.join(map(str, value.shape))}"
    else:
        artifact_type = type(value).__name__
    return ArtifactRef(medium=medium, sha256=digest, size=size, artifact_type=artifact_type,
                       storage_id=storage_id or f"sha256:{digest}")


def _run_git(*args: str) -> bytes:
    """この checkout の git 出力を得る / Read git metadata for this checkout."""
    try:
        return subprocess.run(("git", *args), cwd=_ROOT, check=True, capture_output=True,
                              timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return b""


@lru_cache(maxsize=1)
def _source_state() -> tuple[str, bool]:
    """HEAD と差分から source digest を作る / Hash HEAD plus working-tree changes."""
    head = _run_git("rev-parse", "HEAD").strip()
    status = _run_git("status", "--porcelain=v1", "-z", "--untracked-files=all")
    diff = _run_git("diff", "--no-ext-diff", "--binary", "HEAD", "--", ".")
    h = hashlib.sha256()
    for part in (head, status, diff):
        h.update(len(part).to_bytes(8, "big"))
        h.update(part)
    # 未追跡ファイルは status の名前だけでなく内容も含める / Include untracked contents, not only names.
    untracked = _run_git("ls-files", "--others", "--exclude-standard", "-z").split(b"\0")
    for raw_name in sorted(name for name in untracked if name):
        h.update(hashlib.sha256(raw_name).digest())
        try:
            h.update(hashlib.sha256((_ROOT / os.fsdecode(raw_name)).read_bytes()).digest())
        except OSError:
            h.update(b"unreadable")
    return h.hexdigest(), bool(status)


@lru_cache(maxsize=1)
def _fullseye_version() -> str:
    try:
        import tomllib
        return str(tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"])
    except (OSError, KeyError, TypeError, ValueError):
        try:
            return importlib.metadata.version("fullseye")
        except importlib.metadata.PackageNotFoundError:
            return "unknown"


@lru_cache(maxsize=1)
def _dependencies() -> dict[str, str]:
    """全 distribution の版を得る / Inventory every installed distribution version."""
    rows = {}
    for dist in importlib.metadata.distributions():
        name = dist.metadata.get("Name")
        if name:
            rows[str(name).lower().replace("_", "-")] = str(dist.version)
    return dict(sorted(rows.items()))


def software_inventory(blas_threads: int) -> SoftwareInventory:
    """現在の実行 inventory を作る / Build the current execution inventory."""
    digest, dirty = _source_state()
    cpu = platform.processor().strip() or platform.machine().strip() or "unknown"
    return SoftwareInventory(
        fullseye_version=_fullseye_version(), source_digest=digest, source_dirty=dirty,
        python_version=platform.python_version(), dependencies=_dependencies(),
        operating_system=platform.platform(), cpu=cpu, gpu="disabled-by-profile",
        blas_threads=int(blas_threads),
    )


def _record_hash(record_value: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(record_value)).hexdigest()


def _checkpoint_ok(checkpoint: AuditCheckpoint) -> None:
    if checkpoint.record_count < 0:
        raise ValueError("AuditCheckpoint.record_count must be >= 0")
    if len(checkpoint.head_hash) != SHA256_HEX_LENGTH:
        raise ValueError("AuditCheckpoint.head_hash must be a complete SHA-256 digest")


def verify_audit_file(path: str | os.PathLike[str], *, checkpoint: AuditCheckpoint | None = None,
                      expected_run_ids: Sequence[str] | None = None) -> AuditVerification:
    """JSONL の canonical 形と連鎖を検証する / Verify canonical JSONL and its hash chain.

    連鎖単独では正しい末尾の切り落としを識別できないため、その検知には以前に保管した
    ``checkpoint`` を渡す。  A chain alone cannot distinguish a valid truncated tail; pass a
    previously retained checkpoint to detect that case.
    """
    source = Path(path)
    try:
        raw = source.read_bytes()
    except OSError as exc:
        raise AuditIntegrityError(f"audit file could not be read: {type(exc).__name__}") from exc
    return _verify_audit_bytes(raw, checkpoint=checkpoint, expected_run_ids=expected_run_ids)


def _verify_audit_bytes(raw: bytes, *, checkpoint: AuditCheckpoint | None = None,
                        expected_run_ids: Sequence[str] | None = None) -> AuditVerification:
    """既に読んだ JSONL bytes を検証する / Verify JSONL bytes already read under a lock."""
    if raw and not raw.endswith(b"\n"):
        raise AuditIntegrityError("audit file does not end with a complete JSONL record")
    lines = raw.splitlines()
    previous = GENESIS_RECORD_HASH
    run_ids: list[str] = []
    for index, line in enumerate(lines, 1):
        try:
            envelope = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AuditIntegrityError(f"audit record {index} is not valid UTF-8 JSON") from exc
        if canonical_json_bytes(envelope) != line:
            raise AuditIntegrityError(f"audit record {index} is not canonical JSON")
        if set(envelope) != {"record", "record_hash", "schema"} or envelope.get("schema") != SCHEMA_ID:
            raise AuditIntegrityError(f"audit record {index} has an unknown envelope schema")
        record_value = envelope.get("record")
        if not isinstance(record_value, dict):
            raise AuditIntegrityError(f"audit record {index} has no record object")
        if record_value.get("previous_record_hash") != previous:
            raise AuditIntegrityError(f"audit record {index} breaks previous_record_hash")
        actual = _record_hash(record_value)
        if envelope.get("record_hash") != actual:
            raise AuditIntegrityError(f"audit record {index} hash does not match its content")
        run_id = record_value.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            raise AuditIntegrityError(f"audit record {index} has no run_id")
        if run_id in run_ids:
            raise AuditIntegrityError(f"audit record {index} reuses run_id {run_id!r}")
        run_ids.append(run_id)
        previous = actual
    actual_checkpoint = AuditCheckpoint(len(lines), previous)
    if checkpoint is not None:
        _checkpoint_ok(checkpoint)
        if actual_checkpoint != checkpoint:
            raise AuditIntegrityError("audit file does not match the trusted checkpoint")
    if expected_run_ids is not None and tuple(run_ids) != tuple(expected_run_ids):
        raise AuditIntegrityError("audit run IDs do not match the expected ordered run IDs")
    return AuditVerification(actual_checkpoint, tuple(run_ids))


def _path_lock(path: Path) -> threading.RLock:
    key = os.path.normcase(str(path.resolve()))
    with _PATH_LOCKS_GUARD:
        return _PATH_LOCKS.setdefault(key, threading.RLock())


@contextlib.contextmanager
def _exclusive_stream(path: Path):
    """process 間でも追記を直列化する / Serialize appends across processes."""
    stream = path.open("a+b", buffering=0)
    locked = False
    try:
        stream.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        locked = True
        yield stream
    finally:
        if locked:
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        stream.close()


class AuditSink:
    """1 行ずつ追記・flush・fsync する JSONL sink / Append, flush, and fsync one JSONL record."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self._path = Path(path)
        self._lock = _path_lock(self._path)
        if self._path.is_symlink() or (self._path.exists() and not self._path.is_file()):
            raise ValueError("AuditSink path must be a regular file")

    def checkpoint(self) -> AuditCheckpoint:
        """現在の信頼アンカーを返す / Return the current trusted anchor."""
        with self._lock:
            if not self._path.exists():
                return AuditCheckpoint(0, GENESIS_RECORD_HASH)
            return verify_audit_file(self._path).checkpoint

    def append(self, record: ExecutionRecord) -> tuple[str, AuditCheckpoint]:
        """連鎖を再確認して 1 件だけ確定する / Recheck the chain and commit exactly one record."""
        with self._lock:
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                existed = self._path.exists()
                with _exclusive_stream(self._path) as stream:
                    stream.seek(0)
                    verified = _verify_audit_bytes(stream.read())
                    if record.run_id in verified.run_ids:
                        raise AuditWriteError(f"audit append refused duplicate run_id {record.run_id!r}")
                    before = verified.checkpoint
                    linked = dataclasses.replace(record, previous_record_hash=before.head_hash)
                    record_value = _json_value(linked)
                    digest = _record_hash(record_value)
                    envelope = {"record": record_value, "record_hash": digest, "schema": SCHEMA_ID}
                    line = canonical_json_bytes(envelope) + b"\n"
                    stream.seek(0, os.SEEK_END)
                    stream.write(line)
                    os.fsync(stream.fileno())
                if not existed:
                    try:
                        os.chmod(self._path, AUDIT_FILE_MODE)
                    except OSError:
                        pass
            except OSError as exc:
                raise AuditWriteError(f"audit append failed: {type(exc).__name__}") from exc
            after = AuditCheckpoint(before.record_count + 1, digest)
            return digest, after


def validation_enabled(context: ExecutionContext | None) -> bool:
    """明示 profile がある時だけ真 / True only for an explicitly selected profile."""
    return context is not None and context.validation_profile is not None


def _safe_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """fallback の値やパスを残さない / Retain fallback facts without values or paths."""
    error = str(event.get("error", ""))
    return {
        "name": str(event.get("name", "?")),
        "source": str(event.get("source", "?")),
        "out_sort": None if event.get("out_sort") is None else str(event.get("out_sort")),
        "error_type": error.split(":", 1)[0] if error else "unknown",
        "sequence": int(event.get("seq", 0)),
    }


def _environment(profile: ValidationProfile) -> dict[str, str | None]:
    values = {name: os.environ.get(name) for name in profile.prohibited_environment}
    present = sorted(name for name, value in values.items() if value is not None)
    if present:
        raise ValidationProfileError(
            "validation profile prohibits execution environment overrides: " + ", ".join(present))
    return values


def _cancelled(exc: BaseException) -> bool:
    return isinstance(exc, (asyncio.CancelledError, KeyboardInterrupt, GeneratorExit))


def execute_recorded(*, context: ExecutionContext | None, audit_sink: Any,
                     stages: list[dict[str, Any]], normalized_parameters: dict[str, Any],
                     inputs: Iterable[Any], requested_device: str,
                     stochastic: bool | Callable[[], bool], operation: Callable[[], Any],
                     degraded_reader: Callable[[], list[dict[str, Any]]],
                     prepare: Callable[[], None] | None = None) -> Any:
    """共通の規制実行境界 / Common regulated execution boundary.

    成功時も ``audit_sink.append`` が返るまで出力を返さない。Failure and cancellation are
    also written exactly once; a successful result is not returned until the append completes.
    """
    if not validation_enabled(context):
        return operation()
    assert context is not None and context.validation_profile is not None
    profile = context.validation_profile
    if audit_sink is None or not callable(getattr(audit_sink, "append", None)):
        raise ValidationProfileError("a validation profile requires an AuditSink-compatible append target")
    started = context.now()
    before_events = degraded_reader()
    input_refs: tuple[ArtifactRef, ...] = ()
    output_refs: tuple[ArtifactRef, ...] = ()
    environment: dict[str, str | None] = {}
    status = "failed"
    error: BaseException | None = None
    result: Any = None
    inventory: SoftwareInventory | None = None
    try:
        input_refs = tuple(artifact_ref(value) for value in inputs)
        environment = _environment(profile)
        if str(requested_device).strip().lower() != "cpu":
            raise ValidationProfileError("validation profile permits device='cpu' only")
        if prepare is not None:
            prepare()
        uses_random = stochastic() if callable(stochastic) else stochastic
        if uses_random and profile.seed is None:
            raise ValidationProfileError("a stochastic operator requires ValidationProfile.seed")
        import fsthreads
        with fsthreads.validation_threads(profile.blas_threads) as applied:
            if fsthreads.available() and not applied:
                raise ValidationProfileError("the requested BLAS thread limit could not be applied")
            inventory = software_inventory(profile.blas_threads)
            result = operation()
        output_refs = (artifact_ref(result),)
        status = "succeeded"
    except BaseException as exc:
        error = exc
        status = "cancelled" if _cancelled(exc) else "failed"
        if inventory is None:
            inventory = software_inventory(profile.blas_threads)
    finished = context.now()
    after_events = degraded_reader()
    previous_sequences = {int(item.get("seq", 0)) for item in before_events}
    degraded = tuple(_safe_event(item) for item in after_events
                     if int(item.get("seq", 0)) not in previous_sequences)
    error_text = "" if error is None else _safe_exception_text(error)
    record = ExecutionRecord(
        run_id=context.run_id, parent_run_id=context.parent_run_id, child_run_ids=(),
        principal=context.principal, session=context.session, profile_id=profile.profile_id,
        started_at=started, finished_at=finished, inputs=input_refs,
        stages=tuple(_json_value(stage) for stage in stages),
        normalized_parameters=_json_value(normalized_parameters), outputs=output_refs,
        status=status, device="cpu", degraded_events=degraded, environment=environment,
        software=inventory, error_type=None if error is None else type(error).__name__,
        error_message_sha256=None if error is None else hashlib.sha256(error_text.encode("utf-8")).hexdigest(),
    )
    try:
        audit_sink.append(record)
    except BaseException as audit_error:
        if isinstance(audit_error, AuditWriteError):
            raise
        raise AuditWriteError(f"audit append failed: {type(audit_error).__name__}") from audit_error
    if error is not None:
        raise error
    return result


def _safe_exception_text(error: BaseException) -> str:
    """例外文は hash 前だけで扱う / Read exception text only for hashing."""
    try:
        return str(error)
    except Exception:
        return "<unprintable>"


__all__ = [
    "SCHEMA_ID", "GENESIS_RECORD_HASH", "EXECUTION_ENVIRONMENT_VARIABLES",
    "STOCHASTIC_OPERATOR_NAMES", "ValidationProfileError", "AuditWriteError",
    "AuditIntegrityError", "ValidationProfile", "ExecutionContext", "ArtifactRef",
    "SoftwareInventory", "ExecutionRecord", "AuditCheckpoint", "AuditVerification",
    "AuditSink", "canonical_json", "canonical_json_bytes", "artifact_ref",
    "software_inventory", "verify_audit_file", "validation_enabled", "execute_recorded",
]
