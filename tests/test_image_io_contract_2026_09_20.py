# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""画像 I/O の契約(GenSpark 第 18・19 報 N75〜N79、2026-09-20): 書けない先は 1 文で止める(無言で成功に
見えない)、読めない理由を分ける、uint16 は 16 bit のまま、float は既定 8 bit(文書化)で depth=16 / "float" が無損失、
ppm は灰を 3 ch に、_norm の空ガード、read_wav の不在ファイル文。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

pytest.importorskip("cv2")

import dsp  # noqa: E402
import fullseye as fs  # noqa: E402
import imgio  # noqa: E402
import ops  # noqa: E402

X = np.random.default_rng(0).random((24, 24))


def test_write_refuses_a_missing_directory_instead_of_pretending(tmp_path):
    p = str(tmp_path / "no_dir" / "x.png")
    with pytest.raises(FileNotFoundError, match="directory does not exist"):
        fs.write_image(p, X)
    with pytest.raises(FileNotFoundError, match="directory does not exist"):
        imgio.save(p, X)
    assert not os.path.exists(p) and not os.path.isdir(str(tmp_path / "no_dir"))   # 作りもしない


def test_write_refuses_an_unwritable_extension_naming_the_writable_ones(tmp_path):
    with pytest.raises(OSError, match=r"not a writable image extension.*\.png"):
        fs.write_image(str(tmp_path / "x.qqq"), X)
    with pytest.raises(ValueError, match="no extension"):
        imgio.save(str(tmp_path / "noext"), X)
    assert ".png" in imgio.writable_extensions() and ".ppm" in imgio.writable_extensions()


def test_ppm_takes_a_grey_image_and_reads_back(tmp_path):
    p = str(tmp_path / "g.ppm")
    fs.write_image(p, X)                                        # 以前: cv2.imwrite が False、ファイル無し、無言
    assert os.path.exists(p)
    back = fs.read_image(p)
    assert back.shape == X.shape and np.abs(back - X).max() <= 1 / 510 + 1e-9
    with pytest.raises(ValueError, match="grey format"):
        imgio.save(str(tmp_path / "c.pgm"), np.stack([X] * 3, -1))


def test_read_errors_say_which_kind_of_failure(tmp_path):
    with pytest.raises(FileNotFoundError, match="no such image file"):
        fs.read_image(str(tmp_path / "nope.png"))
    with pytest.raises(IsADirectoryError, match="is a directory"):
        fs.read_image(str(tmp_path))
    junk = tmp_path / "a.qqq"
    junk.write_bytes(b"junk")
    with pytest.raises(ValueError, match="cannot decode"):
        fs.read_image(str(junk))
    with pytest.raises(TypeError):
        imgio.load("")
    with pytest.raises(TypeError):
        imgio.load(None)


def test_uint16_is_written_as_16_bit_and_float_depth_options_are_lossless(tmp_path):
    u16 = np.round(X * 65535).astype(np.uint16)
    fs.write_image(str(tmp_path / "u16.png"), u16)
    back = fs.read_image(str(tmp_path / "u16.png"))
    assert len(np.unique(back)) > 256 and np.abs(back - X).max() < 1e-4       # 以前は >> 8 で 8 bit に潰れた
    fs.write_image(str(tmp_path / "f16.tif"), X, depth=16)
    assert np.abs(fs.read_image(str(tmp_path / "f16.tif")) - X).max() < 1e-4
    fs.write_image(str(tmp_path / "f32.pfm"), X, depth="float")
    assert np.abs(fs.read_image(str(tmp_path / "f32.pfm")) - X).max() < 1e-6
    imgio.save(str(tmp_path / "f32.tif"), X, depth="float")
    assert np.abs(imgio.load(str(tmp_path / "f32.tif")) - X).max() < 1e-6


def test_float_default_is_8_bit_as_documented_and_depth_needs_a_capable_extension(tmp_path):
    fs.write_image(str(tmp_path / "f8.png"), X)
    err = np.abs(fs.read_image(str(tmp_path / "f8.png")) - X).max()
    assert 1e-3 < err <= 1 / 510 + 1e-9                          # 256 段階の量子化(文書どおり)
    assert "quantised to 256 levels by default" in imgio.save.__doc__
    with pytest.raises(ValueError, match="16-bit output needs"):
        fs.write_image(str(tmp_path / "x.jpg"), X, depth=16)
    with pytest.raises(ValueError, match="float output needs"):
        fs.write_image(str(tmp_path / "x.png"), X, depth="float")
    with pytest.raises(ValueError, match="depth must be"):
        imgio.save(str(tmp_path / "x.png"), X, depth=12)


def test_color_and_region_sorts_still_round_trip(tmp_path):
    rgb = np.random.default_rng(2).random((16, 16, 3))
    fs.write_image(str(tmp_path / "c.png"), rgb)
    back = fs.read_image(str(tmp_path / "c.png"), sort="color")
    assert back.shape == (16, 16, 3) and np.abs(back - rgb).max() <= 1 / 510 + 1e-9
    fs.write_image(str(tmp_path / "r.png"), (X > 0.5).astype(np.float64))
    reg = fs.read_image(str(tmp_path / "r.png"), sort="region")
    assert set(np.unique(reg)) <= {0.0, 1.0} and np.array_equal(reg, (X > 0.5).astype(np.float64))


def test_norm_helper_passes_empty_arrays_through():
    for shape in ((0,), (0, 0), (4, 0)):
        out = ops._norm(np.zeros(shape))
        assert out.shape == shape


def test_audio_readers_say_no_such_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="no such file"):
        dsp.read_wav(str(tmp_path / "zz.wav"))
    with pytest.raises(IsADirectoryError):
        dsp.read_audio(str(tmp_path))


def test_colorize_labels_refuses_a_float_image_but_takes_whole_number_labels():
    x = np.random.default_rng(0).random((16, 16))
    with pytest.raises(ValueError, match="whole numbers"):
        imgio.colorize_labels(x)                                 # 以前: astype(int) で全 0 → 真っ黒
    lab = (x > 0.5).astype(np.float64) * 2                       # float だが整数値 = ラベルの契約
    out = imgio.colorize_labels(lab)
    assert out.shape == (16, 16, 3) and out.max() > 0
    assert np.array_equal(imgio.colorize_labels(lab.astype(np.int64)), out)
    with pytest.raises(ValueError, match="integer array"):
        imgio.colorize_labels(np.array([["a"]]))
