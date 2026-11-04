# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""敵対的検証 2026-11-05(io 担当)の回帰テスト。

各テストは「書いたものが戻るか」を、真値(書いた値そのもの)、仕様の不変量
(FITS 4.0 / MRC2014 / teem NRRD / CommonMark / OME)、または独立実装
(astropy / mrcfile / pynrrd / openpyxl / 自前の float32 丸め)と比べる。
"""
from __future__ import annotations

import io
import math
import re
import struct

import numpy as np
import pytest

import fileio
import mesh
import ops
import raster
import imgio
from fullseye import jsonio, mdio


# --------------------------------------------------------------------------- #
# I4  FITS: 整数の BZERO 規約(int8 / uint64)を整数のまま正確に                #
# --------------------------------------------------------------------------- #
def _fits_with_bzero(bitpix, bzero, stored):
    cards = [fileio._fits_card("SIMPLE", True), fileio._fits_card("BITPIX", bitpix),
             fileio._fits_card("NAXIS", 2), fileio._fits_card("NAXIS1", stored.shape[1]),
             fileio._fits_card("NAXIS2", stored.shape[0]), fileio._fits_card("BZERO", bzero),
             fileio._fits_card("BSCALE", 1), b"END".ljust(80)]
    head = b"".join(cards)
    head += b" " * (-len(head) % 2880)
    body = stored.tobytes()
    return head + body + b"\0" * (-len(body) % 2880)


def test_i4_fits_uint64_bzero_2_63_is_exact():
    want = np.array([[0, 2**63 + 1, 2**64 - 1]], dtype=np.uint64)
    stored = np.array([[-(2**63), 1, 2**63 - 1]], dtype=">i8")      # value - 2**63 (FITS 4.0 Table 11)
    got, meta = fileio.astro_fits_read(_fits_with_bzero(64, 2**63, stored))
    assert got.dtype == np.uint64
    assert got.tolist() == want.tolist()
    # our writer, round trip
    back, _ = fileio.astro_fits_read(fileio.astro_fits_write(want, header={}))
    assert back.dtype == np.uint64 and back.tolist() == want.tolist()


def test_i4_fits_int8_bzero_minus_128_is_int8():
    want = np.array([[-128, -1, 0, 127]], dtype=np.int8)
    stored = (want.astype(np.int16) + 128).astype(">u1")
    got, _ = fileio.astro_fits_read(_fits_with_bzero(8, -128, stored))
    assert got.dtype == np.int8
    assert got.tolist() == want.tolist()
    back, meta = fileio.astro_fits_read(fileio.astro_fits_write(want, header={}))
    assert back.dtype == np.int8 and back.tolist() == want.tolist()
    assert meta["bzero"] == -128


def test_i4_fits_uint64_matches_astropy():
    fits = pytest.importorskip("astropy.io.fits")
    want = np.array([[0, 2**63 + 1, 2**64 - 1]], dtype=np.uint64)
    buf = io.BytesIO()
    fits.PrimaryHDU(want).writeto(buf)
    got, _ = fileio.astro_fits_read(buf.getvalue())
    assert got.dtype == np.uint64 and got.tolist() == want.tolist()
    with fits.open(io.BytesIO(fileio.astro_fits_write(want, header={}))) as hdul:
        assert hdul[0].data.tolist() == want.tolist()


# --------------------------------------------------------------------------- #
# I5  FITS: ヘッダの float は往復する桁で、float は float のまま                #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("value", [0.30000000000000004, 1 / 3, 5.0, -2.5e-300, 1e16,
                                   123456789.12345679, 6.02214076e23])
def test_i5_fits_header_float_round_trips(value):
    img = np.zeros((2, 2), np.float32)
    _, meta = fileio.astro_fits_read(fileio.astro_fits_write(img, header={"CRVAL1": value}))
    got = meta["wcs"]["CRVAL1"]
    assert isinstance(got, float)
    assert got == value


def test_i5_fits_float_card_fits_fixed_field_when_possible():
    card = fileio._fits_card("CRVAL1", 0.30000000000000004).decode("ascii")
    assert card[10:30].strip() == "0.30000000000000004"        # cols 11-30, right-justified
    assert card[29] != " "


# --------------------------------------------------------------------------- #
# I6  FITS: 自由書式の文字列(引用符が 11 桁目より後)                         #
# --------------------------------------------------------------------------- #
def test_i6_fits_free_format_string():
    img = fileio.astro_fits_write(np.zeros((2, 2), np.float32), header={"CTYPE1": "RA---TAN"})
    raw = bytearray(img)
    idx = raw.find(b"CTYPE1  = 'RA---TAN'")
    assert idx >= 0
    raw[idx:idx + 80] = b"CTYPE1  =    'RA---TAN' / free-format string".ljust(80)
    _, meta = fileio.astro_fits_read(bytes(raw))
    assert meta["wcs"]["CTYPE1"] == "RA---TAN"


# --------------------------------------------------------------------------- #
# I7  MRC: NVERSION (word 28) = 20140                                          #
# --------------------------------------------------------------------------- #
def _mrc_meta():
    return {"voxel_size": [1.5, 2.0, 2.5], "voxel_unit": "angstrom",
            "origin": [0, 0, 0], "origin_unit": "angstrom"}


def test_i7_mrc_writes_nversion():
    raw = fileio.em_mrc_write(np.zeros((2, 3, 4), np.float32), meta=_mrc_meta())
    assert struct.unpack_from("<i", raw, 27 * 4)[0] == 20140


def test_i7_mrc_passes_mrcfile_validate(tmp_path):
    mrcfile = pytest.importorskip("mrcfile")
    p = tmp_path / "a.mrc"
    p.write_bytes(fileio.em_mrc_write(np.arange(24, dtype=np.float32).reshape(2, 3, 4), meta=_mrc_meta()))
    out = io.StringIO()
    assert mrcfile.validate(str(p), print_file=out), out.getvalue()


# --------------------------------------------------------------------------- #
# I8  NRRD: teem の型名の別名                                                  #
# --------------------------------------------------------------------------- #
_TEEM_TYPES = {   # teem nrrd format spec, "type" field: every spelling -> dtype
    "signed char": "i1", "int8": "i1", "int8_t": "i1",
    "uchar": "u1", "unsigned char": "u1", "uint8": "u1", "uint8_t": "u1",
    "short": "i2", "short int": "i2", "signed short": "i2", "signed short int": "i2",
    "int16": "i2", "int16_t": "i2",
    "ushort": "u2", "unsigned short": "u2", "unsigned short int": "u2", "uint16": "u2", "uint16_t": "u2",
    "int": "i4", "signed int": "i4", "int32": "i4", "int32_t": "i4",
    "uint": "u4", "unsigned int": "u4", "uint32": "u4", "uint32_t": "u4",
    "longlong": "i8", "long long": "i8", "long long int": "i8", "signed long long": "i8",
    "signed long long int": "i8", "int64": "i8", "int64_t": "i8",
    "ulonglong": "u8", "unsigned long long": "u8", "unsigned long long int": "u8",
    "uint64": "u8", "uint64_t": "u8",
    "float": "f4", "double": "f8",
}


def test_i8_nrrd_every_teem_type_name():
    assert len(_TEEM_TYPES) == 40      # 3+4+6+5+4+4+7+5+2 spellings in the spec
    failures = []
    for name, code in _TEEM_TYPES.items():
        dt = np.dtype(code)
        a = np.arange(3, dtype=dt)
        canonical = {"f4": "float", "f8": "double"}.get(code, dt.name)
        raw = fileio.nrrd_write(a, meta={"space_directions": [[1.0]], "space_unit": "mm"}, encoding="raw")
        raw = raw.replace(f"type: {canonical}\n".encode(), f"type: {name}\n".encode())
        try:
            got, _ = fileio.nrrd_read(raw)
        except ValueError as exc:
            failures.append((name, str(exc)))
            continue
        if got.dtype != dt or got.tolist() != a.tolist():
            failures.append((name, str(got.dtype)))
    assert failures == []


# --------------------------------------------------------------------------- #
# I9  NRRD: space (LPS / RAS ...) を保持して往復                                #
# --------------------------------------------------------------------------- #
def _nrrd_geom(**extra):
    return {"space_directions": np.eye(3).tolist(), "space_unit": "mm", **extra}


def test_i9_nrrd_space_is_kept_and_distinguishes_lps_from_ras():
    a = np.zeros((2, 2, 2), np.uint8)
    p = fileio.nrrd_write(a, meta=_nrrd_geom(), encoding="raw")
    lps = p.replace(b"space dimension: 3", b"space: left-posterior-superior")
    ras = p.replace(b"space dimension: 3", b"space: RAS")
    _, m1 = fileio.nrrd_read(lps)
    _, m2 = fileio.nrrd_read(ras)
    assert m1["space"] == "left-posterior-superior"
    assert m2["space"] == "right-anterior-superior"


def test_i9_nrrd_space_round_trips_through_writer():
    a = np.arange(8, dtype=np.int16).reshape(2, 2, 2)
    p = fileio.nrrd_write(a, meta=_nrrd_geom(space="LPS"), encoding="gzip")
    assert b"space: left-posterior-superior\n" in p
    assert b"space dimension" not in p          # the spec: space and space dimension are exclusive
    got, meta = fileio.nrrd_read(p)
    assert meta["space"] == "left-posterior-superior" and np.array_equal(got, a)
    with pytest.raises(ValueError):
        fileio.nrrd_write(a, meta=_nrrd_geom(space="no-such-space"), encoding="raw")
    with pytest.raises(ValueError):            # RAST is 4-D, the vectors are 3-D
        fileio.nrrd_write(a, meta=_nrrd_geom(space="RAST"), encoding="raw")


def test_i9_nrrd_space_matches_pynrrd(tmp_path):
    nrrd = pytest.importorskip("nrrd")
    a = np.arange(8, dtype=np.int16).reshape(2, 2, 2)
    fn = tmp_path / "a.nrrd"
    fn.write_bytes(fileio.nrrd_write(a, meta=_nrrd_geom(space="RAS"), encoding="raw"))
    _data, header = nrrd.read(str(fn))
    assert header["space"] == "right-anterior-superior"


# --------------------------------------------------------------------------- #
# I10 / I11  OME-TIFF: 長さ 1 の軸 / XML の Type と dtype                       #
# --------------------------------------------------------------------------- #
def _ome_meta(axes, shape):
    meta = {"axes": axes, "physical_size_x": 0.5, "physical_size_x_unit": "um",
            "physical_size_y": 0.25, "physical_size_y_unit": "um"}
    if "Z" in axes:
        meta.update(physical_size_z=2.0, physical_size_z_unit="um")
    if "C" in axes:
        meta["channel_names"] = ["c%d" % i for i in range(shape[axes.index("C")])]
    return meta


@pytest.mark.parametrize("axes,shape", [("ZYX", (1, 3, 4)), ("CYX", (1, 3, 4)),
                                        ("TZYX", (1, 2, 3, 4)), ("TCZYX", (2, 1, 1, 3, 4))])
def test_i10_ome_singleton_axes_round_trip(axes, shape):
    pytest.importorskip("tifffile")
    a = np.arange(int(np.prod(shape)), dtype=np.uint16).reshape(shape)
    meta = _ome_meta(axes, shape)
    got, back = fileio.ome_tiff_read(fileio.ome_tiff_write(a, meta=meta))
    assert got.shape == shape and back["axes"] == axes
    assert np.array_equal(got, a)
    if "Z" in axes:
        assert back["physical_size_z"] == 2.0
    if "C" in axes:
        assert back["channel_names"] == meta["channel_names"]


def test_i11_ome_xml_type_must_match_pixels():
    pytest.importorskip("tifffile")
    a = np.arange(12, dtype=np.uint16).reshape(3, 4)
    raw = fileio.ome_tiff_write(a, meta=_ome_meta("YX", a.shape))
    assert raw.count(b'Type="uint16"') == 1
    forged = raw.replace(b'Type="uint16"', b'Type="int16" ')    # same length: offsets stay valid
    with pytest.raises(ValueError, match="Type"):
        fileio.ome_tiff_read(forged)
    got, _ = fileio.ome_tiff_read(raw)
    assert got.dtype == np.uint16


# --------------------------------------------------------------------------- #
# I12  volio.write_volume: 不正な幾何は書かずに拒否                             #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad", [
    {"spacing_mm": (0.0, 1.0, 1.0)}, {"spacing_mm": (-1.0, 1.0, 1.0)},
    {"spacing_mm": (float("nan"), 1.0, 1.0)}, {"spacing_mm": (1.0, 1.0)},
    {"direction": np.zeros((3, 3))}, {"direction": np.eye(2)},
    {"origin": np.array([float("nan"), 0.0, 0.0])}, {"origin": np.zeros(2)},
])
@pytest.mark.parametrize("suffix", [".nrrd", ".nii.gz"])
def test_i12_write_volume_rejects_bad_geometry(tmp_path, bad, suffix):
    pytest.importorskip("SimpleITK")
    import volio
    meta = volio.VolumeMeta(spacing_mm=(2.0, 1.0, 0.5))
    for key, value in bad.items():
        setattr(meta, key, value)
    p = tmp_path / ("v" + suffix)
    with pytest.raises(ValueError):
        volio.write_volume(str(p), np.zeros((2, 3, 4)), meta)
    assert not p.exists()


def test_i12_write_volume_good_geometry_round_trips(tmp_path):
    pytest.importorskip("SimpleITK")
    import volio
    d = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    meta = volio.VolumeMeta(spacing_mm=(2.0, 1.0, 0.5), origin=np.array([1.0, 2.0, 3.0]), direction=d)
    p = tmp_path / "v.nrrd"
    volio.write_volume(str(p), np.zeros((2, 3, 4)), meta)
    _v, back = volio.read_volume(str(p))
    assert back.spacing_mm == (2.0, 1.0, 0.5)
    assert np.allclose(back.direction, d) and np.allclose(back.origin, [1, 2, 3])


# --------------------------------------------------------------------------- #
# I13 / I14  mesh.py の OFF の同次座標と OBJ のタブ                              #
# --------------------------------------------------------------------------- #
def test_i13_4off_divides_by_w():
    text = "4OFF\n3 1 0\n2 0 0 2\n0 4 0 2\n0 0 6 2\n3 0 1 2\n"
    V, F = fileio.mesh_read_off(text)
    assert np.array_equal(V, [[1, 0, 0], [0, 2, 0], [0, 0, 3]])
    with pytest.raises(ValueError):                       # w = 0 is a point at infinity
        fileio.mesh_read_off("4OFF\n3 1 0\n1 0 0 0\n0 1 0 1\n0 0 1 1\n3 0 1 2\n")


def test_i14_obj_tab_separated_records():
    text = "v\t0 0 0\nv\t1\t0\t0\nv 0 1 0\nf\t1 2\t3\n"
    V, F = fileio.mesh_read_obj(text)
    assert np.array_equal(V, [[0, 0, 0], [1, 0, 0], [0, 1, 0]])
    assert F.tolist() == [[0, 1, 2]]


# --------------------------------------------------------------------------- #
# I15  mesh_write_obj: 頂点法線を正しく書き、OFF/PLY と同じ入力を受ける           #
# --------------------------------------------------------------------------- #
def _parse_obj_normals(text):
    vn = [list(map(float, ln.split()[1:])) for ln in text.splitlines() if ln.startswith("vn ")]
    faces = [[tuple(int(x) for x in tok.split("//")) for tok in ln.split()[1:]]
             for ln in text.splitlines() if ln.startswith("f ")]
    return np.asarray(vn), faces


def _corner_normals(vn, faces):
    """(n_faces, 3, 3): the unit normal each face corner references."""
    return np.asarray([[vn[n - 1] for _v, n in f] for f in faces])


def test_i15_obj_normals_are_area_weighted_vertex_normals():
    V = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], float)
    F = np.array([[0, 2, 1], [0, 1, 3]])
    vn, faces = _parse_obj_normals(fileio.mesh_write_obj((V, F)))
    assert len(faces) == 2 and vn.shape == (4, 3)
    cross = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    want = np.zeros_like(V)                       # independent: sum of incident cross products
    for k, face in enumerate(F):
        want[face] += cross[k]
    want /= np.linalg.norm(want, axis=1)[:, None]
    assert [[v for v, _n in f] for f in faces] == (F + 1).tolist()
    assert np.allclose(_corner_normals(vn, faces), want[F], atol=1e-15)


def test_i15_obj_accepts_what_off_and_ply_accept():
    V = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [5, 5, 5]], float)   # vertex 3 unreferenced
    F = np.array([[0, 1, 2]])
    text = fileio.mesh_write_obj((V, F))
    vn, faces = _parse_obj_normals(text)
    assert vn.shape == (3, 3) and np.allclose(_corner_normals(vn, faces), [[[0, 0, 1]] * 3])
    back_v, back_f = fileio.mesh_read_obj(text)
    assert np.array_equal(back_v, V) and np.array_equal(back_f, F)
    fileio.mesh_write_off((V, F))
    # both sides of one triangle: the vertex normals cancel, each corner uses its face normal
    V2, F2 = V[:3], np.array([[0, 1, 2], [0, 2, 1]])
    text2 = fileio.mesh_write_obj((V2, F2))
    vn2, faces2 = _parse_obj_normals(text2)
    assert np.allclose(_corner_normals(vn2, faces2), [[[0, 0, 1]] * 3, [[0, 0, -1]] * 3])
    back_v2, back_f2 = fileio.mesh_read_obj(text2)
    assert np.array_equal(back_v2, V2) and np.array_equal(back_f2, F2)
    fileio.mesh_write_off((V2, F2))


# --------------------------------------------------------------------------- #
# I16  mesh_write_ply: 整数の属性は整数型で                                       #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("binary", [False, True])
def test_i16_ply_integer_attribute_is_exact(binary):
    V = np.zeros((3, 3))
    attrs = {"label": np.array([2**31 - 1, -(2**31), 7], np.int32),
             "count": np.array([0, 2**32 - 1, 5], np.uint32),
             "small": np.array([-128, 0, 127], np.int8)}
    text = fileio.mesh_write_ply({"vertices": V, "attributes": attrs}, binary=binary)
    head = (text if isinstance(text, str) else text.decode("latin-1")).split("end_header")[0]
    assert "property int label" in head and "property uint count" in head and "property char small" in head
    back = fileio.mesh_read_ply(text)["attributes"]
    assert sorted(back) == sorted(attrs)
    assert back["label"].tolist() == attrs["label"].tolist()
    assert back["count"].tolist() == attrs["count"].tolist()
    assert back["small"].tolist() == attrs["small"].tolist()
    assert back["label"].dtype.kind == "i" and back["count"].dtype.kind == "u"


def test_i16_ply_int64_beyond_ply_types_is_refused():
    V = np.zeros((2, 3))
    with pytest.raises(ValueError, match="PLY"):
        fileio.mesh_write_ply({"vertices": V, "attributes": {"t": np.array([2**53 + 1, 7], np.int64)}},
                              binary=False)
    ok = fileio.mesh_write_ply({"vertices": V, "attributes": {"t": np.array([5, 7], np.int64)}}, binary=True)
    assert fileio.mesh_read_ply(ok)["attributes"]["t"].tolist() == [5, 7]


# --------------------------------------------------------------------------- #
# I17  jsonio: binary でも元の float の dtype に戻す                              #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("readable", [False, True])
@pytest.mark.parametrize("values", [[[0.1, 0.2]], [[np.nan, 1.0]]])
def test_i17_jsonio_float32_keeps_dtype(readable, values):
    a = np.array(values, np.float32)
    got, sort = jsonio.from_json(jsonio.to_json(a, "image", readable=readable))
    assert sort == "image" and got.dtype == np.float32
    assert np.array_equal(got, a, equal_nan=True)


def test_i17_jsonio_forged_float32_that_does_not_fit_is_refused():
    env = jsonio.to_jsonable(np.array([[0.1, 0.2]], np.float64), "image")
    env["payload"]["dtype"] = "float32"
    with pytest.raises(ValueError):
        jsonio.from_jsonable(env)


# --------------------------------------------------------------------------- #
# I18  mdio.extract_json: CommonMark の fence                                  #
# --------------------------------------------------------------------------- #
def _env():
    return mdio.json_block(np.array([1.0, 2.0]), "signal")


@pytest.mark.parametrize("prefix", [
    "```\n```\n\n",                                   # empty fence
    "```file.py\nprint(1)\n```\n\n",                 # info string with a dot
    '```python title="a.py"\nprint(1)\n```\n\n',     # info string with attributes
    "~~~\n```\nx\n~~~\n\n",                          # tilde fence holding a backtick line
    "````md\n```json\n{\"fullseye_sort\": 1\n```\n````\n\n",   # longer fence holds a shorter one
    "  ```\n  code\n  ```\n\n",                     # indented (<= 3 spaces) fence
])
def test_i18_extract_json_after_other_fences(prefix):
    got = mdio.extract_json(prefix + _env())
    assert len(got) == 1
    value, sort = got[0]
    assert sort == "signal" and value.tolist() == [1.0, 2.0]


def test_i18_extract_json_tilde_and_long_fence_envelopes():
    body = _env().split("\n", 1)[1].rsplit("\n", 1)[0]          # the JSON text between the fences
    md = "~~~json\n" + body + "\n~~~\n\n`````\n" + body + "\n`````\n"
    assert [s for _v, s in mdio.extract_json(md)] == ["signal", "signal"]


# --------------------------------------------------------------------------- #
# I19  xlsxio: '=' 始まりの文字列は数式にしない(CWE-1236)                       #
# --------------------------------------------------------------------------- #
def test_i19_xlsx_strings_are_never_formulas(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    from fullseye import xlsxio
    p = tmp_path / "r.xlsx"
    rows = [{"name": "=1+1", "file": '=HYPERLINK("http://x","y")', "p": "+1", "m": "-2", "a": "@SUM(A1)"}]
    xlsxio.save_xlsx_report([("=HEAD()", rows, "table"), ("=1", 2.5, "scalar")], str(p), title="=T()")
    ws = openpyxl.load_workbook(str(p)).active
    cells = [c for row in ws.iter_rows() for c in row if c.value is not None]
    assert len(cells) >= 12
    assert [c.coordinate for c in cells if c.data_type == "f"] == []
    texts = {c.value for c in cells}
    assert {"=1+1", '=HYPERLINK("http://x","y")', "+1", "-2", "@SUM(A1)", "=HEAD()", "=T()"} <= texts
    # the raw sheet XML must carry no <f> element (formula) at all
    import zipfile
    with zipfile.ZipFile(str(p)) as z:
        sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "<f>" not in sheet and "<f " not in sheet


# --------------------------------------------------------------------------- #
# I21  C 出力のノブは float32 で往復する桁                                       #
# --------------------------------------------------------------------------- #
_C_LIT = re.compile(r"(-?[0-9.]+(?:e[-+]?[0-9]+)?)f\b")


def test_i21_c_literals_are_float32_exact():
    A = 0.3921566                     # 100/255 lies between float32(A) and the old "%.6f" literal
    cases = {"threshold": (A, 0.5), "gaussian": (0.123456789, 0.5), "gamma": (0.987654321, 0.1),
             "scale_clip": (0.333333333, 0.777777777), "unsharp": (0.1111111119, 0.9999999)}
    want_vals = {"threshold": [A], "gaussian": [0.3 + 2.7 * 0.123456789], "gamma": [0.5 + 1.5 * 0.987654321],
                 "scale_clip": [0.5 + 1.5 * 0.333333333, 0.777777777 - 0.5],
                 "unsharp": [1.5 * 0.1111111119, 0.5 + 1.5 * 0.9999999]}
    seen = 0
    for name, (a, b) in cases.items():
        stmt = ops._c(name)(a, b)
        lits = [float(x) for x in _C_LIT.findall(stmt)]
        assert len(lits) == len(want_vals[name]), stmt
        assert np.array_equal(np.float32(lits), np.float32(want_vals[name])), stmt
        seen += 1
    assert seen == 5
    # the decision the threshold makes on a float32 pixel matches Python's
    pix = np.float32(100 / 255)
    lit = np.float32(float(_C_LIT.findall(ops._c("threshold")(A, 0.5))[0]))
    assert (pix > lit) == (pix > np.float32(A))


def test_i21_c_literal_is_valid_c_for_integral_values():
    stmt = ops._c("threshold")(1.0, 0.5)
    assert re.search(r"[0-9]\.[0-9]*f|e[-+]?[0-9]+f", stmt), stmt     # never "1f"


# --------------------------------------------------------------------------- #
# I22  write_pfm: scale を丸めない                                               #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("scale", [-1.0, -1e-07, 1e-07, 2.5e-07, -1.23456789, 3.0e12])
def test_i22_pfm_scale_round_trips(tmp_path, scale):
    p = tmp_path / "s.pfm"
    a = np.arange(6, dtype=np.float32).reshape(2, 3)
    raster.write_pfm(str(p), a, scale=scale)
    got, s = raster.read_pfm(str(p))
    assert s == abs(scale)
    assert np.array_equal(got, a)


# --------------------------------------------------------------------------- #
# I23  imgio.save_ply: float64 を丸めない                                        #
# --------------------------------------------------------------------------- #
def test_i23_save_ply_is_exact(tmp_path):
    P = np.array([[352145.123456789, 4123456.98765, 12.345678901],
                  [1.2345678901234567, -0.000123456789, 1e-9]])
    p = tmp_path / "a.ply"
    imgio.save_ply(str(p), P)
    assert np.array_equal(mesh.read_points(str(p)), P)
    imgio.save_ply(str(p), P, colors=np.array([[0, 0.5, 1], [1, 1, 1]]))
    got, C = mesh.read_points(str(p), with_colors=True)
    assert np.array_equal(got, P)


# --------------------------------------------------------------------------- #
# I24 / I25  CSV: 欠測のある大きい整数列 / UTF-8 BOM                               #
# --------------------------------------------------------------------------- #
_META = {"source": "t", "generated_at": "2026-11-05T00:00:00+09:00", "coordinate_meaning": "none"}


def test_i24_csv_big_int_column_with_blank_is_exact():
    big = 2**60 + 1
    text = fileio.table_write_csv({"t": np.array([big, None, 3], dtype=object)},
                                  units={"t": "ns"}, meta=_META)
    assert '\n1152921504606846977\n' in text
    col = fileio.table_read_csv(text)["columns"]["t"]
    assert np.ma.isMaskedArray(col)
    assert col.mask.tolist() == [False, True, False]
    assert int(col[0]) == big and int(col[2]) == 3
    assert col.dtype == np.int64


def test_i24_csv_small_int_column_with_blank_stays_float_nan():
    text = fileio.table_write_csv({"t": np.array([1, None, 3], dtype=object)}, units={"t": "s"}, meta=_META)
    col = fileio.table_read_csv(text)["columns"]["t"]
    assert col.dtype == np.float64 and np.isnan(col[1]) and col[0] == 1.0


@pytest.mark.parametrize("as_bytes", [False, True])
def test_i25_csv_utf8_bom_is_not_part_of_the_column_name(as_bytes):
    text = "﻿" + fileio.table_write_csv({"x": [1.0]}, units={"x": "mm"}, meta=_META)
    data = text.encode("utf-8") if as_bytes else text
    table = fileio.table_read_csv(data)
    assert list(table["columns"]) == ["x"] and table["units"] == {"x": "mm"}


# --------------------------------------------------------------------------- #
# I26  write_points が書ける空の .xyz を read_points が読む                        #
# --------------------------------------------------------------------------- #
def test_i26_empty_xyz_round_trips(tmp_path):
    p = tmp_path / "e.xyz"
    mesh.write_points(str(p), np.zeros((0, 3)))
    got = mesh.read_points(str(p))
    assert got.shape == (0, 3)
    p.write_bytes(b"")                       # a 0-byte file is still not a point cloud
    with pytest.raises(ValueError):
        mesh.read_points(str(p))


# --------------------------------------------------------------------------- #
# 追加(時間枠の探針で見つけた本物): Windows の予約名の取りこぼし                #
# --------------------------------------------------------------------------- #
_RESERVED = ["COM0", "LPT0.txt", "COM¹.txt", "lpt³", "CONIN$", "CONOUT$", "con.txt", "COM9"]


@pytest.mark.parametrize("name", _RESERVED)
def test_archive_extract_refuses_every_windows_reserved_name(tmp_path, name):
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("dir/" + name, b"payload")
    with pytest.raises(ValueError, match="Windows"):
        fileio.archive_extract(buf.getvalue(), str(tmp_path / "out"))
    assert not (tmp_path / "out" / "dir").exists()


@pytest.mark.parametrize("fmt", ["zip", "tar", "tar.gz", "tar.xz"])
@pytest.mark.parametrize("name", ["data/CON.txt", "data/COM0", "CONOUT$"])
def test_archive_create_refuses_reserved_names_in_any_component(fmt, name):
    with pytest.raises(ValueError):
        fileio.archive_create({name: b"x"}, fmt)


def test_e57_precision_is_what_the_docstring_says():
    """pye57 writes cartesian / intensity as E57 single: float32 round trip, the pose in double."""
    pytest.importorskip("pye57")
    assert "float32" in fileio.e57_write.__doc__
    P = np.array([[0.125, 1.5, -2.0], [0.1, 0.2, 0.3]])
    shift = [352145.123456789, 4123456.98765, 12.345678901]
    back = fileio.e57_read(fileio.e57_write({"points": P, "pose": {"rotation": [1, 0, 0, 0],
                                                                    "translation": shift}}))
    assert np.array_equal(back["points"], P.astype(np.float32).astype(np.float64))
    assert back["pose"]["translation"].tolist() == shift
