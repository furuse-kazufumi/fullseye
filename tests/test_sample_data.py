# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""sample_data fail-closed regressions (offline: the opener is monkeypatched).

* the decompressed size of an archive member is capped (``MAX_EXTRACT_BYTES``);
* an archive entry without ``sha256_out`` is rejected by the manifest check,
  never counts as verified, and its download is refused.
"""
import hashlib
import io
import os
import tarfile

import pytest

import sample_data as SD


def _tar_gz_bytes(member: str, data: bytes) -> bytes:
    bio = io.BytesIO()
    with tarfile.open(fileobj=bio, mode="w:gz") as tf:
        ti = tarfile.TarInfo(member)
        ti.size = len(data)
        tf.addfile(ti, io.BytesIO(data))
    return bio.getvalue()


class _Resp:
    def __init__(self, payload: bytes):
        self._b = io.BytesIO(payload)

    def read(self, n):
        return self._b.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _opener_for(payload: bytes):
    def opener(req):
        return _Resp(payload)
    return opener


def _install(monkeypatch, tmp_path, entry: dict):
    monkeypatch.setenv("FULLSEYE_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(SD, "MANIFEST", SD.MANIFEST + [entry])
    monkeypatch.setattr(SD, "_BY_ID", {**SD._BY_ID, entry["id"]: entry})


def _entry(payload: bytes, data: bytes, **override) -> dict:
    e = dict(
        id="t-archive", name="test archive", category="mesh", fmt="ply",
        url="https://example.invalid/t.tar.gz", archive="tar.gz",
        member="t/inner.ply", dest="t_inner.ply",
        sha256=hashlib.sha256(payload).hexdigest(),
        sha256_out=hashlib.sha256(data).hexdigest(),
        bytes=len(payload), license="test", commercial="yes", access="direct",
        source_page="https://example.invalid/", attribution="", doc="",
    )
    e.update(override)
    return e


def test_tar_member_extracts_and_verifies(monkeypatch, tmp_path):
    data = b"ply\n" + b"x" * 5000
    payload = _tar_gz_bytes("t/inner.ply", data)
    _install(monkeypatch, tmp_path, _entry(payload, data))
    p = SD.download("t-archive", yes=True, quiet=True, _opener=_opener_for(payload))
    assert os.path.exists(p) and open(p, "rb").read() == data
    assert SD.verify("t-archive") is True


def test_decompressed_size_is_capped(monkeypatch, tmp_path):
    """A tiny .tar.gz that inflates past MAX_EXTRACT_BYTES is refused and
    leaves nothing behind (no .part, no target)."""
    data = b"\0" * 200_000                                    # compresses to ~ nothing
    payload = _tar_gz_bytes("t/inner.ply", data)
    assert len(payload) < 2000
    _install(monkeypatch, tmp_path, _entry(payload, data))
    monkeypatch.setattr(SD, "MAX_EXTRACT_BYTES", 50_000)
    with pytest.raises(ValueError, match="MAX_EXTRACT_BYTES"):
        SD.download("t-archive", yes=True, quiet=True, _opener=_opener_for(payload))
    target = os.path.join(SD.data_dir(), "t_inner.ply")
    assert not os.path.exists(target) and not os.path.exists(target + ".part")
    assert SD.verify("t-archive") is False


def test_extract_cap_is_multiple_of_transfer_cap():
    assert SD.MAX_EXTRACT_BYTES >= SD._MAX_BYTES


def test_archive_entry_without_sha256_out_is_fail_closed(monkeypatch, tmp_path):
    data = b"ply\n" + b"y" * 100
    payload = _tar_gz_bytes("t/inner.ply", data)
    e = _entry(payload, data, sha256_out=None)
    _install(monkeypatch, tmp_path, e)
    # 1. the shipped-manifest validator refuses such an entry
    with pytest.raises(ValueError, match="sha256_out"):
        SD._validate_manifest()
    # 2. a file that merely exists is NOT "verified"
    target = os.path.join(SD.data_dir(), "t_inner.ply")
    os.makedirs(SD.data_dir(), exist_ok=True)
    with open(target, "wb") as w:
        w.write(data)
    assert SD.verify("t-archive") is False
    os.remove(target)
    # 3. downloading it is refused and the extracted file is removed
    with pytest.raises(ValueError, match="sha256_out"):
        SD.download("t-archive", yes=True, quiet=True, _opener=_opener_for(payload))
    assert not os.path.exists(target)


def test_shipped_manifest_pins_sha256_out_on_every_archive_entry():
    for e in SD.MANIFEST:
        if e["archive"] is not None:
            assert e.get("sha256_out"), e["id"]
