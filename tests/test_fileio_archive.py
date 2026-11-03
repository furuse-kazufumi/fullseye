from __future__ import annotations

import hashlib
import io
import os
import stat
import tarfile
import zipfile
from pathlib import Path

import pytest

import fileio


TRUTH = {"a.txt": b"alpha\n", "nested/b.bin": bytes(range(32))}


@pytest.mark.parametrize("fmt", ["zip", "tar", "tar.gz", "tar.xz"])
def test_archive_create_extract_roundtrip_is_bit_exact_and_independently_readable(fmt, tmp_path):
    first = fileio.archive_create(TRUTH, fmt, deterministic=True)
    second = fileio.archive_create(TRUTH, fmt, deterministic=True)
    assert hashlib.sha256(first).digest() == hashlib.sha256(second).digest()
    assert fileio.archive_probe(first) == fmt
    rows = fileio.archive_list(first)
    assert {row["name"] for row in rows} == set(TRUTH)
    assert {row["size"] for row in rows} == {len(value) for value in TRUTH.values()}

    if fmt == "zip":
        with zipfile.ZipFile(io.BytesIO(first)) as archive:
            independent = {name: archive.read(name) for name in archive.namelist()}
    else:
        with tarfile.open(fileobj=io.BytesIO(first), mode="r:*") as archive:
            independent = {member.name: archive.extractfile(member).read()
                           for member in archive.getmembers() if member.isfile()}
    assert independent == TRUTH

    dest = tmp_path / "out"
    assert set(fileio.archive_extract(first, dest)) == set(TRUTH)
    assert {name: (dest / name).read_bytes() for name in TRUTH} == TRUTH


def test_tar_bz2_list_and_extract(tmp_path):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:bz2") as archive:
        for name, data in TRUTH.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    payload = buf.getvalue()
    assert fileio.archive_probe(payload) == "tar.bz2"
    assert {row["name"] for row in fileio.archive_list(payload)} == set(TRUTH)
    dest = tmp_path / "bz2"
    assert set(fileio.archive_extract(payload, dest)) == set(TRUTH)
    assert {name: (dest / name).read_bytes() for name in TRUTH} == TRUTH


def test_archive_path_input_root_and_member_selection(tmp_path):
    root = tmp_path / "root"
    (root / "inside").mkdir(parents=True)
    (root / "inside" / "a.txt").write_bytes(b"A")
    payload = fileio.archive_create(root / "inside", "zip", root=root)
    archive_path = tmp_path / "data.zip"
    archive_path.write_bytes(payload)
    assert fileio.archive_probe(archive_path) == "zip"
    dest = tmp_path / "selected"
    assert fileio.archive_extract(archive_path, dest, members=["inside/a.txt"]) == ["inside/a.txt"]
    assert (dest / "inside" / "a.txt").read_bytes() == b"A"

    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"outside")
    with pytest.raises(ValueError, match="outside root"):
        fileio.archive_create(outside, "zip", root=root)


@pytest.mark.parametrize("member", ["../escape.txt", "/absolute.txt", r"C:\drive.txt"])
def test_archive_extract_rejects_zip_slip(member, tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr(member, b"escape")
    dest = tmp_path / "out"
    with pytest.raises(ValueError, match="unsafe"):
        fileio.archive_extract(buf.getvalue(), dest)
    assert not dest.exists()


def test_archive_extract_rejects_zip_and_tar_links(tmp_path):
    zip_buf = io.BytesIO()
    info = zipfile.ZipInfo("link")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(zip_buf, "w") as archive:
        archive.writestr(info, "target")
    with pytest.raises(ValueError, match="links are forbidden"):
        fileio.archive_extract(zip_buf.getvalue(), tmp_path / "zip")

    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode="w") as archive:
        link = tarfile.TarInfo("link")
        link.type = tarfile.SYMTYPE
        link.linkname = "target"
        archive.addfile(link)
    with pytest.raises(ValueError, match="links are forbidden"):
        fileio.archive_extract(tar_buf.getvalue(), tmp_path / "tar")


def test_archive_extract_rejects_member_count_and_expanded_size_limits(tmp_path):
    payload = fileio.archive_create(TRUTH, "zip")
    with pytest.raises(ValueError, match="selected members; limit is 1"):
        fileio.archive_extract(payload, tmp_path / "many", max_members=1)
    with pytest.raises(ValueError, match="declared extracted size"):
        fileio.archive_extract(payload, tmp_path / "large", max_total_bytes=1)


def test_archive_extract_rejects_compression_ratio_over_one_to_one_thousand(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr("bomb.bin", b"\0" * (4 * 1024 * 1024))
    with pytest.raises(ValueError, match="1:1000 compression-ratio"):
        fileio.archive_extract(buf.getvalue(), tmp_path / "bomb")


def test_archive_extract_rejects_tar_xz_compression_bomb(tmp_path):
    data = b"\0" * (4 * 1024 * 1024)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:xz") as archive:
        info = tarfile.TarInfo("bomb.bin")
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    with pytest.raises(ValueError, match="1:1000 compression-ratio"):
        fileio.archive_extract(buf.getvalue(), tmp_path / "tar-xz-bomb")


def test_archive_extract_requires_empty_destination_and_leaves_no_partial_output(tmp_path):
    payload = fileio.archive_create(TRUTH, "zip")
    dest = tmp_path / "occupied"
    dest.mkdir()
    (dest / "keep.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError, match="not empty"):
        fileio.archive_extract(payload, dest)
    assert (dest / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_7z_absence_is_an_explicit_refusal(monkeypatch):
    monkeypatch.setenv("FULLSEYE_7Z", "disabled")
    with pytest.raises(ImportError, match="7-Zip is not installed"):
        fileio.archive_list(b"7z\xbc\xaf\x27\x1c" + b"\0" * 32)


@pytest.mark.skipif(fileio._sevenzip_executable() is None, reason="7-Zip is not installed")
def test_7z_create_list_extract_and_determinism(tmp_path):
    first = fileio.archive_create(TRUTH, "7z", deterministic=True)
    second = fileio.archive_create(TRUTH, "7z", deterministic=True)
    assert hashlib.sha256(first).digest() == hashlib.sha256(second).digest()
    assert fileio.archive_probe(first) == "7z"
    assert {row["name"] for row in fileio.archive_list(first)} == set(TRUTH)
    dest = tmp_path / "out7z"
    fileio.archive_extract(first, dest)
    assert {name: (dest / name).read_bytes() for name in TRUTH} == TRUTH


def test_rar_creation_is_explicitly_unsupported():
    with pytest.raises(ValueError, match="RAR creation is unsupported"):
        fileio.archive_create(TRUTH, "rar")


def test_archive_create_rejects_empty_input():
    with pytest.raises(ValueError, match="must not be empty"):
        fileio.archive_create({}, "zip")


@pytest.mark.skipif(not os.environ.get("FULLSEYE_RAR_TEST_ARCHIVE") or
                    fileio._sevenzip_executable() is None,
                    reason="set FULLSEYE_RAR_TEST_ARCHIVE to a local RAR fixture and install 7-Zip")
def test_local_rar_fixture_lists_and_extracts(tmp_path):
    fixture = Path(os.environ["FULLSEYE_RAR_TEST_ARCHIVE"])
    rows = fileio.archive_list(fixture)
    assert rows and any(not row["is_dir"] for row in rows)
    extracted = fileio.archive_extract(fixture, tmp_path / "rar")
    assert extracted and all((tmp_path / "rar" / name).exists() for name in extracted)
