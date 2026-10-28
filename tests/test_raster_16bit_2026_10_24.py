"""16 bit カラー画像の読みが 8 bit に黙って切り詰められないこと(2026-10-24)。

再現: imageio の Pillow プラグインは 16 bit の RGB / RGBA の PNG を **uint8** で返す。
``raster.read_raster`` はその imageio を先に使っていたので、OpenCV があっても 16 bit RGB PNG が
uint8 で返っていた(dtype も値も違うのに例外なし)。同じ切り詰めが兄弟の読み口にもあった:

* ``video.iter_frames`` / ``read_frames`` — 16 bit RGB の PNG を imageio で読み、uint8 を
  uint16 に引き伸ばして返していた(最大 237/65535 ずれ)。
* ``imgevolve._imread`` (CLI の入力) — ``cv2.IMREAD_COLOR`` / ``IMREAD_GRAYSCALE`` は
  16 bit を 8 bit に落とす(``IMREAD_ANYDEPTH`` が無い)。

合格条件は「深さを保って同じ値を返す」か「理由つきで断る」のどちらか。uint8 で返すのは不合格。
PNG はテストの中で zlib だけで組み立てる(書き手のバックエンドに依存しない)。
"""
from __future__ import annotations

import os
import struct
import sys
import zlib

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import raster  # noqa: E402

try:
    import cv2  # noqa: F401
    HAVE_CV2 = True
except Exception:  # pragma: no cover - OpenCV は通常入っている
    HAVE_CV2 = False

#: PNG の色型 -> チャネル数(0 = 灰, 2 = RGB, 4 = 灰 + α, 6 = RGBA)
_PNG_CHANNELS = {0: 1, 2: 3, 4: 2, 6: 4}


def _write_png16(path, arr: np.ndarray) -> None:
    """uint16 の配列を 16 bit PNG に書く(zlib と struct だけ。フィルタ 0)。"""
    a = np.asarray(arr, np.uint16)
    ch = 1 if a.ndim == 2 else a.shape[2]
    ctype = {1: 0, 3: 2, 2: 4, 4: 6}[ch]
    h, w = a.shape[:2]
    rows = a.reshape(h, w * ch).astype(">u2").tobytes()
    stride = w * ch * 2
    raw = b"".join(b"\x00" + rows[y * stride:(y + 1) * stride] for y in range(h))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", w, h, 16, ctype, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def _sample(ch, seed=0):
    """8 bit に落とすと必ず値が変わる 16 bit の値(下位バイトに中身がある)。"""
    rng = np.random.default_rng(seed)
    shape = (6, 9) if ch == 1 else (6, 9, ch)
    a = rng.integers(0, 65536, size=shape, dtype=np.uint16)
    a.flat[0] = 0x1234                               # 下位バイトが 0 でない画素を必ず含める
    return a


def _png(tmp_path, ch, name=None):
    a = _sample(ch)
    p = tmp_path / (name or "c%d.png" % ch)
    _write_png16(p, a)
    head = p.read_bytes()[:26]
    assert head[24] == 16 and _PNG_CHANNELS[head[25]] == ch    # 書いた PNG 自体の確認
    return str(p), a


# ---- 宣言されたビット深度の読み -------------------------------------------------- #
def test_declared_bits_reads_png_ihdr_and_tiff_tag(tmp_path):
    p, _ = _png(tmp_path, 3)
    assert raster._declared_bits_per_sample(p) == 16
    assert raster._declared_bits_per_sample(str(tmp_path / "missing.png")) is None
    (tmp_path / "junk.png").write_bytes(b"not a png at all, really not")
    assert raster._declared_bits_per_sample(str(tmp_path / "junk.png")) is None
    tifffile = pytest.importorskip("tifffile")
    t = tmp_path / "x.tif"
    tifffile.imwrite(str(t), _sample(3))
    assert raster._declared_bits_per_sample(str(t)) == 16
    t8 = tmp_path / "x8.tif"
    tifffile.imwrite(str(t8), (_sample(3) >> 8).astype(np.uint8))
    assert raster._declared_bits_per_sample(str(t8)) == 8


# ---- raster.read_raster ------------------------------------------------------- #
@pytest.mark.parametrize("ch", [1, 2, 3, 4])
def test_read_raster_keeps_16bit_png_or_refuses(tmp_path, ch):
    p, a = _png(tmp_path, ch)
    try:
        arr, meta = raster.read_raster(p)
    except ValueError as e:
        assert "16" in str(e) and "bit" in str(e)
        assert not HAVE_CV2 or ch == 2, "OpenCV があるのに 16 bit PNG を読めない: %s" % e
        return
    assert arr.dtype == np.uint16, "16 bit PNG が %s で返った(切り詰め)" % arr.dtype
    if ch == 2:                                      # 灰 + α は OpenCV が BGRA に展開する
        assert arr.shape[:2] == a.shape[:2]
        return
    assert arr.shape == a.shape and np.array_equal(arr, a)
    assert meta["src_dtype"] == "uint16"


@pytest.mark.skipif(not HAVE_CV2, reason="OpenCV が無い環境は拒否の試験で見る")
@pytest.mark.parametrize("ch", [3, 4])
def test_read_raster_16bit_colour_with_opencv_is_exact(tmp_path, ch):
    """OpenCV があるなら 16 bit RGB / RGBA は必ず値ごと読める(α は最後のチャネル)。"""
    p, a = _png(tmp_path, ch)
    arr, meta = raster.read_raster(p)
    assert arr.dtype == np.uint16 and np.array_equal(arr, a)
    f, m2 = raster.read_raster(p, keep_dtype=False)
    assert np.allclose(f, a / 65535.0, atol=1e-15) and m2["normalized"]


@pytest.mark.parametrize("ch", [3, 4])
def test_read_raster_refuses_when_no_reader_keeps_depth(tmp_path, monkeypatch, ch):
    """OpenCV が無く imageio(Pillow)しか無いなら、uint8 で返さず理由つきで断る。"""
    p, a = _png(tmp_path, ch)
    monkeypatch.setattr(raster, "_cv2", lambda: None)
    try:
        arr, _ = raster.read_raster(p)
    except ValueError as e:
        msg = str(e)
        assert "16-bit" in msg and "8 bit" in msg and p in msg
        return
    # imageio が将来 16 bit RGB を保てるようになったなら、値が同じであること
    assert arr.dtype == np.uint16 and np.array_equal(arr, a)


def test_read_raster_8bit_png_unchanged(tmp_path):
    """8 bit の PNG は従来どおり(imageio で uint8)。"""
    iio = pytest.importorskip("imageio.v2")
    a = (_sample(3) >> 8).astype(np.uint8)
    p = str(tmp_path / "eight.png")
    iio.imwrite(p, a)
    arr, meta = raster.read_raster(p)
    assert arr.dtype == np.uint8 and np.array_equal(arr, a)


@pytest.mark.parametrize("ch", [3, 4])
def test_read_raster_16bit_tiff_keeps_values(tmp_path, ch):
    tifffile = pytest.importorskip("tifffile")
    a = _sample(ch)
    t = str(tmp_path / ("c%d.tif" % ch))
    tifffile.imwrite(t, a)
    arr, meta = raster.read_raster(t)
    assert arr.dtype == np.uint16 and np.array_equal(arr, a)


@pytest.mark.skipif(not HAVE_CV2, reason="needs OpenCV")
def test_read_raster_opencv_fallback_keeps_alpha_last(tmp_path, monkeypatch):
    """imageio が読めずに OpenCV へ落ちる経路で RGBA の α が先頭に来ない(``[:, :, ::-1]`` は ARGB)。"""
    import cv2
    a = (_sample(4) >> 8).astype(np.uint8)
    p = str(tmp_path / "rgba8.png")
    cv2.imwrite(p, a[:, :, [2, 1, 0, 3]])
    import imageio.v2 as iio

    def boom(*_a, **_k):
        raise RuntimeError("imageio unavailable")

    monkeypatch.setattr(iio, "imread", boom)
    arr, _ = raster.read_raster(p)
    assert np.array_equal(arr, a)


# ---- video.iter_frames / read_frames ------------------------------------------ #
@pytest.mark.parametrize("ch", [3, 4])
def test_video_read_frames_16bit_png_keeps_or_refuses(tmp_path, ch):
    video = pytest.importorskip("video")
    p, a = _png(tmp_path, ch)
    try:
        fr = video.read_frames(p, gray=False, dtype="uint16")
    except (RuntimeError, ValueError) as e:
        assert not HAVE_CV2, "OpenCV があるのに断った: %s" % e
        return
    assert fr.dtype == np.uint16 and fr.shape == (1,) + a.shape[:2] + (3,)
    assert np.array_equal(fr[0], a[:, :, :3]), "16 bit RGB PNG のコマが 8 bit 精度に落ちた"
    f64 = video.read_frames(p, gray=False)
    assert np.allclose(f64[0], a[:, :, :3] / 65535.0, atol=1e-15)


def test_video_refuses_16bit_png_without_depth_keeping_reader(tmp_path, monkeypatch):
    video = pytest.importorskip("video")
    p, _ = _png(tmp_path, 3)
    monkeypatch.setattr(raster, "_cv2", lambda: None)
    with pytest.raises(RuntimeError, match="16-bit"):
        video.read_frames(p, gray=False, dtype="uint16")


def test_video_16bit_png_start_skips_the_single_frame(tmp_path):
    video = pytest.importorskip("video")
    p, _ = _png(tmp_path, 3)
    if not HAVE_CV2:
        pytest.skip("needs OpenCV")
    assert list(video.iter_frames(p, gray=False, start=1)) == []


# ---- imgevolve._imread (CLI の入力) ------------------------------------------- #
@pytest.mark.skipif(not HAVE_CV2, reason="imgevolve CLI は OpenCV 前提")
def test_imgevolve_imread_keeps_16bit_precision(tmp_path):
    import cv2
    import imgevolve
    p, a = _png(tmp_path, 3)
    col = imgevolve._imread(p, "color")
    assert col.shape == a.shape
    assert np.abs(col - a / 65535.0).max() < 1e-12, "16 bit PNG を 8 bit に落として /255 していた"
    g = imgevolve._imread(p, "gray")
    want = cv2.cvtColor(np.ascontiguousarray(a), cv2.COLOR_RGB2GRAY) / 65535.0
    # libpng の灰色化と cvtColor は丸めが数 LSB 違う(実測 4/65535)。8 bit 時代の誤差は ~1/255
    assert np.abs(g - want).max() < 2e-4
    assert not np.allclose(g * 255.0, np.round(g * 255.0)), "灰色が 1/255 刻み = 8 bit に落ちている"
    r = imgevolve._imread(p, "region")
    assert set(np.unique(r)) <= {0.0, 1.0} and np.array_equal(r, (want > 0.5).astype(float))
    a8 = (a >> 8).astype(np.uint8)                   # 8 bit は従来どおり /255
    p8 = str(tmp_path / "eight.png")
    cv2.imwrite(p8, a8[:, :, ::-1])
    assert np.abs(imgevolve._imread(p8, "color") - a8 / 255.0).max() < 1e-15
