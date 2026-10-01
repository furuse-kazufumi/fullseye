# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""helpstore の門: 書庫は決定的 / 展開した HTML は元とバイト一致 / 危険なパスは拒否 / 版が変われば別の場所に展開する / checkout では展開しない。"""
import io
import os
import tarfile

import pytest

import helpstore as HS


def _tree(tmp_path):
    src = tmp_path / "op_help"
    (src / "optics").mkdir(parents=True)
    (src / "fig").mkdir()
    (src / "a.html").write_text("<p>a</p>" * 50, encoding="utf-8")
    (src / "a.en.html").write_text("<p>A</p>" * 50, encoding="utf-8")
    (src / "optics" / "b.html").write_text("<p>b</p>" * 50, encoding="utf-8")
    (src / "fig" / "a.png").write_bytes(b"\x89PNG not packed")
    (src / "README.md").write_text("not packed", encoding="utf-8")
    return src


def test_the_archive_is_deterministic_and_round_trips(tmp_path, monkeypatch):
    src = _tree(tmp_path)
    n1, _ = HS.pack_archive(str(src), str(tmp_path / "x.tar.xz"))
    n2, _ = HS.pack_archive(str(src), str(tmp_path / "y.tar.xz"))
    assert n1 == n2 == 3                                       # HTML だけ(図と md は入れない)
    assert (tmp_path / "x.tar.xz").read_bytes() == (tmp_path / "y.tar.xz").read_bytes()
    monkeypatch.setenv("FULLSEYE_CACHE_DIR", str(tmp_path / "cache"))
    d = HS._extract(str(tmp_path / "x.tar.xz"))
    for rel in ("a.html", "a.en.html", os.path.join("optics", "b.html")):
        assert (src / rel).read_bytes() == open(os.path.join(d, rel), "rb").read()
    assert not os.path.exists(os.path.join(d, "fig"))
    assert HS._extract(str(tmp_path / "x.tar.xz")) == d          # 2 回目は展開し直さない
    (src / "a.html").write_text("changed", encoding="utf-8")
    HS.pack_archive(str(src), str(tmp_path / "z.tar.xz"))
    assert HS._extract(str(tmp_path / "z.tar.xz")) != d          # 版が変われば別の場所(古い HTML を読まない)


def test_unsafe_members_are_refused(tmp_path, monkeypatch):
    p = tmp_path / "bad.tar.xz"
    with tarfile.open(p, "w:xz") as tf:
        ti = tarfile.TarInfo("../escape.html")
        ti.size = 3
        tf.addfile(ti, io.BytesIO(b"bad"))
    monkeypatch.setenv("FULLSEYE_CACHE_DIR", str(tmp_path / "cache"))
    with pytest.raises(ValueError, match="unsafe path"):
        HS._extract(str(p))
    assert not (tmp_path / "escape.html").exists()


def test_a_checkout_reads_the_directory_without_extracting():
    assert HS._has_html(HS.HELP_DIR), "the checkout should carry the generated help HTML"
    assert HS.html_root() == HS.HELP_DIR
    assert HS.fig_root() == HS.HELP_DIR
