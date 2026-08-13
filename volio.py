"""Volumetric / medical volume readers and writers (the 3-D *import* side).

This module widens the data formats Fullseye can ingest to the volumetric world —
CT / MRI / PET stacks, microscopy z-stacks, and depth-cube ("evis") data — turning
each into the plain ``(D, H, W)`` float64 array the existing ``volume`` operator
sort already speaks. The ``vol_*`` ops in :mod:`ops` (``vol_gaussian`` /
``vol_median`` / ``vol_erode`` / ``vol_dilate`` / ``vol_threshold`` / ``vol_mip`` /
``vol_slice`` / ``vol_count``) consume exactly that array, so a volume read here
flows straight in::

    import volio, ops
    vol, meta = volio.read_volume("study/CT")          # a DICOM folder
    smoothed  = ops.RT["vol_gaussian"](vol, 0.5, 0.0)  # the existing 3-D op
    mip       = ops.RT["vol_mip"](vol, 0.0, 0.0)       # volume -> 2-D image

Formats (dispatched by extension / by "is a directory"):

  * **DICOM** — Digital Imaging and Communications in Medicine, *PS3.10* (file
    set) / *PS3.3* (image module). A directory or a ``.dcm`` file is read as a
    **series** (all slices stacked) via SimpleITK's GDCM ``ImageSeriesReader``; a
    genuinely single-file DICOM falls back to ``sitk.ReadImage``.
  * **NIfTI-1** (``.nii`` / ``.nii.gz``) — Neuroimaging Informatics Technology
    Initiative file format (NIH).
  * **NRRD** (``.nrrd`` / ``.nhdr``) — Nearly Raw Raster Data (Teem / 3D Slicer).
  * **MetaImage** (``.mha`` / ``.mhd`` + ``.raw``) — ITK's MetaIO format.
  * **Analyze 7.5** (``.hdr`` + ``.img``) — Mayo Clinic Analyze format.
    (NIfTI/NRRD/MetaImage/Analyze all go through SimpleITK.)
  * **Volumetric TIFF** (``.tif`` / ``.tiff``) — Adobe *TIFF 6.0*; a multi-page /
    3-D TIFF is treated as ``(D, H, W)``. A 2-D TIFF is refused here — that is
    ordinary raster I/O and belongs in :mod:`imgio`, not this module.
  * **Headerless raw** (``.raw`` / ``.vol`` / ``.img`` with no sidecar) — requires
    explicit ``shape=(D, H, W)`` and ``dtype=`` because the bytes carry no
    dimensions; the file size is checked against ``prod(shape) * itemsize``.
  * **NumPy** (``.npy`` / ``.npz``) — a saved 3-D array (``.npz`` needs ``key=``
    unless it holds exactly one array).

Values are kept **raw**: a CT volume comes back in its native Hounsfield units,
never crushed into ``[0, 1]``. The ``vol_*`` ops operate on these values directly;
if you want a normalised volume that is an explicit, separate step (e.g.
``imgio.normalize(vol)``), because normalisation destroys medical intensity
semantics and is not always wanted.

Provenance is public for every format cited above; no proprietary or GPL parser is
required — SimpleITK (Apache-2.0) and tifffile (BSD) are the only backends, and
both are optional (a machine without them can still import this module; only the
affected reader raises a clear "pip install" error).

Honest limitations (nothing here claims more than a real round-trip test proves):

  * **Axis order.** ``spacing_mm`` is returned as ``(sz, sy, sx)`` so it lines up
    with the ``(D, H, W)`` array axes. ``origin`` and ``direction`` are returned in
    the file's own world ``(x, y, z)`` frame exactly as ITK reports them (they are
    *not* reordered); a non-axial acquisition therefore comes back in the file's
    native index order together with its direction-cosine matrix, rather than
    being resampled to an axial grid. Resampling to a canonical orientation is out
    of scope.
  * **Single component only.** RGB / vector / segmentation-label volumes and
    4-D (time-series / multi-channel) data are refused — this module returns a
    scalar 3-D field. A single 2-D slice is likewise refused as "not a volume".
  * **Multi-frame DICOM** (one file holding the whole stack) is read by
    ``sitk.ReadImage`` when a lone ``.dcm`` is passed; per-frame functional-group
    spacing is honoured only to the extent GDCM exposes it.
  * **Non-finite voxels are rejected** (NaN / Inf) — the ``vol_*`` ops would
    propagate them and silently corrupt a whole downstream pipeline.
  * TIFF spacing is not read from resolution tags (defaults to unit spacing);
    raw / NumPy inputs carry no geometry (unit spacing, zero origin, identity
    direction).

Every reader is fail-closed on untrusted input: the projected float64 size is
capped (``MAX_VOLUME_BYTES``) and checked *before* allocation, raw byte counts are
validated exactly, ``.npy`` / ``.npz`` are loaded with ``allow_pickle=False``, and
backend exceptions are wrapped into a ``ValueError`` / ``FileNotFoundError`` that
names the path — never a partially decoded volume.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

__all__ = [
    "read_volume", "write_volume", "list_dicom_series", "VolumeMeta",
    "VOLUME_FORMATS", "MAX_VOLUME_BYTES",
    "SITK_FORMATS", "DICOM_FORMATS", "TIFF_FORMATS", "RAW_FORMATS", "NUMPY_FORMATS",
]

# ---- introspectable format tables ------------------------------------------ #
#: NIfTI / NRRD / MetaImage / Analyze — everything read through SimpleITK.
SITK_FORMATS = (".nii", ".nii.gz", ".nrrd", ".nhdr", ".mha", ".mhd", ".hdr")
#: DICOM single-file extensions (a *directory* is also accepted as a series).
DICOM_FORMATS = (".dcm", ".dicom")
#: Volumetric (multi-page) TIFF.
TIFF_FORMATS = (".tif", ".tiff")
#: Headerless raw cubes — need explicit ``shape=`` + ``dtype=``. ``.img`` is raw
#: only when it has no Analyze ``.hdr`` sidecar (otherwise it is read as Analyze).
RAW_FORMATS = (".raw", ".vol", ".img")
#: Saved NumPy arrays.
NUMPY_FORMATS = (".npy", ".npz")

#: Every extension :func:`read_volume` recognises (a directory reads as DICOM too).
VOLUME_FORMATS = tuple(sorted(set(
    SITK_FORMATS + DICOM_FORMATS + TIFF_FORMATS + RAW_FORMATS + NUMPY_FORMATS)))

#: Refuse a volume whose float64 representation would exceed this many bytes.
#: 4 GiB = 512 M voxels; checked against the header *before* any allocation so an
#: untrusted or decompression-bomb file cannot exhaust memory.
MAX_VOLUME_BYTES = 4 * (1 << 30)


@dataclass
class VolumeMeta:
    """Geometry + provenance carried alongside a volume.

    ``spacing_mm`` is ordered ``(sz, sy, sx)`` to match the ``(D, H, W)`` array
    axes. ``origin`` (3,) and ``direction`` (3, 3) are in the file's world
    ``(x, y, z)`` frame as reported by ITK — see the module's "Honest limitations".
    ``dtype`` is the *original* on-disk dtype (values are never rescaled).
    ``n_series`` / ``modality`` are filled in for DICOM when known.
    """
    spacing_mm: tuple = (1.0, 1.0, 1.0)
    origin: np.ndarray = field(default_factory=lambda: np.zeros(3, np.float64))
    direction: np.ndarray = field(default_factory=lambda: np.eye(3, dtype=np.float64))
    dtype: str = ""
    n_series: Optional[int] = None
    modality: Optional[str] = None
    source_format: str = ""


# ---- low-level helpers ----------------------------------------------------- #
def _suffix(path: str) -> str:
    """Lower-cased extension, treating ``.nii.gz`` as a single suffix."""
    low = os.path.basename(str(path)).lower()
    if low.endswith(".nii.gz"):
        return ".nii.gz"
    return os.path.splitext(low)[1]


def _missing(human: str, pip_name: str, err: Exception) -> ImportError:
    return ImportError("%s is required for this volume format — `pip install %s` (%s)"
                       % (human, pip_name, err))


def _sitk():
    """SimpleITK, or a clear install error (all of DICOM / NIfTI / NRRD / MetaImage
    / Analyze are read through it)."""
    try:
        import SimpleITK as sitk
    except Exception as e:  # pragma: no cover - only when the extra is absent
        raise _missing("SimpleITK", "SimpleITK", e) from None
    return sitk


def _tifffile():
    """tifffile, or a clear install error (volumetric TIFF)."""
    try:
        import tifffile
    except Exception as e:  # pragma: no cover - only when the extra is absent
        raise _missing("tifffile", "tifffile", e) from None
    return tifffile


def _bad_read(path: str, err: Exception) -> ValueError:
    return ValueError("%s: could not be read as a volume (%s: %s)"
                      % (path, type(err).__name__, err))


def _bad_write(path: str, err: Exception) -> ValueError:
    return ValueError("%s: could not write volume (%s: %s)"
                      % (path, type(err).__name__, err))


def _check_voxel_budget(nvox: int, src: str) -> None:
    """Refuse a volume whose float64 form would exceed ``MAX_VOLUME_BYTES``,
    *before* it is allocated."""
    nvox = int(nvox)
    nbytes = nvox * 8
    if nbytes > MAX_VOLUME_BYTES:
        raise ValueError("%s: a %d-voxel volume needs %d bytes as float64, over the "
                         "%d-byte cap (volio.MAX_VOLUME_BYTES) — refusing before allocation"
                         % (src, nvox, nbytes, MAX_VOLUME_BYTES))


def _to_finite_f64(arr, src: str) -> np.ndarray:
    """Coerce to contiguous float64 and reject NaN/Inf (a poisoned voxel would
    corrupt every downstream ``vol_*`` result)."""
    vol = np.ascontiguousarray(arr, dtype=np.float64)
    if not np.isfinite(vol).all():
        n = int((~np.isfinite(vol)).sum())
        raise ValueError("%s: volume has %d non-finite voxel(s) (NaN/Inf) — refusing "
                         "(the vol_* ops would propagate them)" % (src, n))
    return vol


# ---- SimpleITK image -> (vol, meta) ---------------------------------------- #
def _meta_from_sitk(img, dtype: str, src_fmt: str,
                    n_series: Optional[int], modality: Optional[str]) -> "VolumeMeta":
    spacing = tuple(float(s) for s in img.GetSpacing())      # (sx, sy, sz)
    origin = np.asarray(img.GetOrigin(), np.float64)         # (ox, oy, oz)
    direction = np.asarray(img.GetDirection(), np.float64)
    if direction.size == 9:
        direction = direction.reshape(3, 3)
    else:                                                    # 2-D image safety net
        direction = np.eye(3, dtype=np.float64)
    if len(spacing) == 3:
        spacing_mm = (spacing[2], spacing[1], spacing[0])    # -> (sz, sy, sx)
    else:
        spacing_mm = (1.0, 1.0, 1.0)
    return VolumeMeta(spacing_mm=spacing_mm, origin=origin, direction=direction,
                      dtype=dtype, n_series=n_series, modality=modality,
                      source_format=src_fmt)


def _finish_sitk(img, src: str, src_fmt: str = "sitk",
                 n_series: Optional[int] = None, modality: Optional[str] = None):
    """A decoded SimpleITK image -> validated ``(vol, meta)``."""
    sitk = _sitk()
    if img.GetNumberOfComponentsPerPixel() != 1:
        raise ValueError("%s: multi-component (RGB / vector) volume is out of scope — "
                         "this module returns a scalar 3-D field" % src)
    arr = sitk.GetArrayFromImage(img)                        # (z, y, x) for a 3-D scalar
    if arr.ndim == 2:
        raise ValueError("%s: this is a single 2-D slice, not a volume — pass the DICOM "
                         "directory (or a 3-D file) to read the whole stack" % src)
    if arr.ndim != 3:
        raise ValueError("%s: expected a 3-D volume, got a %d-D array "
                         "(4-D time-series / multi-channel is out of scope)" % (src, arr.ndim))
    _check_voxel_budget(arr.size, src)
    vol = _to_finite_f64(arr, src)
    meta = _meta_from_sitk(img, str(arr.dtype), src_fmt, n_series, modality)
    return vol, meta


def _read_single_sitk(path: str, src_fmt: str = "sitk", n_series: Optional[int] = None):
    """Header-first single-file read: check the voxel budget from the header, then
    decode. Used for NIfTI/NRRD/MetaImage/Analyze and single-file DICOM."""
    sitk = _sitk()
    reader = sitk.ImageFileReader()
    reader.SetFileName(str(path))
    try:
        reader.ReadImageInformation()
    except Exception as e:
        raise _bad_read(str(path), e) from None
    size = reader.GetSize()                                  # (x, y[, z])
    if size:
        _check_voxel_budget(int(np.prod(size, dtype=np.int64)), str(path))
    modality = None
    try:
        modality = (reader.GetMetaData("0008|0060").strip() or None)   # (0008,0060) Modality
    except Exception:
        modality = None
    try:
        img = reader.Execute()
    except Exception as e:
        raise _bad_read(str(path), e) from None
    return _finish_sitk(img, str(path), src_fmt=src_fmt, n_series=n_series, modality=modality)


# ---- DICOM ----------------------------------------------------------------- #
def _series_ids(directory: str):
    sitk = _sitk()
    try:
        return list(sitk.ImageSeriesReader.GetGDCMSeriesIDs(str(directory)))
    except Exception:
        return []


def list_dicom_series(path: str):
    """Return the DICOM Series Instance UIDs present in a folder (or in the folder
    containing a ``.dcm`` file). Empty list if the folder holds no DICOM series.

    Pass one of these UIDs as ``series_id=`` to :func:`read_volume` to disambiguate
    a study directory that stores several series side by side.
    """
    p = str(path)
    d = p if os.path.isdir(p) else (os.path.dirname(os.path.abspath(p)) or ".")
    if not os.path.isdir(d):
        raise FileNotFoundError(d)
    return _series_ids(d)


def _read_series(files, src: str, n_series: Optional[int]):
    sitk = _sitk()
    files = list(files)
    if not files:
        raise ValueError("%s: DICOM series has no files" % src)
    # Budget from the first slice's (x, y) size x slice count, before Execute().
    try:
        fr = sitk.ImageFileReader()
        fr.SetFileName(files[0])
        fr.ReadImageInformation()
        sz = fr.GetSize()
    except Exception:
        sz = None
    if sz:
        per_slice = int(np.prod(tuple(sz[:2]), dtype=np.int64))
        _check_voxel_budget(per_slice * len(files), src)
    reader = sitk.ImageSeriesReader()
    reader.SetFileNames(files)
    try:
        reader.MetaDataDictionaryArrayUpdateOn()
        reader.LoadPrivateTagsOn()
    except Exception:
        pass
    try:
        img = reader.Execute()
    except Exception as e:
        raise _bad_read(src, e) from None
    modality = None
    try:
        modality = (reader.GetMetaData(0, "0008|0060").strip() or None)
    except Exception:
        modality = None
    return _finish_sitk(img, src, src_fmt="dicom", n_series=n_series, modality=modality)


def _read_dicom_dir(directory: str, series_id: Optional[str]):
    d = str(directory)
    ids = _series_ids(d)
    if not ids:
        raise ValueError("%s: no DICOM series found in this directory" % d)
    if series_id is None:
        if len(ids) > 1:
            raise ValueError("%s: %d DICOM series are present — choose one via "
                             "series_id=<uid>. Available: %s" % (d, len(ids), ", ".join(ids)))
        series_id = ids[0]
    elif series_id not in ids:
        raise ValueError("%s: series_id %r not found. Available: %s"
                         % (d, series_id, ", ".join(ids)))
    sitk = _sitk()
    files = sitk.ImageSeriesReader.GetGDCMSeriesFileNames(d, series_id)
    return _read_series(files, d, n_series=len(ids))


def _read_dicom_file(path: str, series_id: Optional[str]):
    """A ``.dcm`` path: read the whole series it belongs to (so pointing at any
    slice yields the volume); fall back to a single-file read if it stands alone."""
    sitk = _sitk()
    p = str(path)
    d = os.path.dirname(os.path.abspath(p)) or "."
    uid = series_id
    if uid is None:
        try:
            fr = sitk.ImageFileReader()
            fr.SetFileName(p)
            fr.ReadImageInformation()
            uid = (fr.GetMetaData("0020|000e").strip() or None)   # (0020,000E) SeriesInstanceUID
        except Exception:
            uid = None
    files = []
    if uid:
        try:
            files = list(sitk.ImageSeriesReader.GetGDCMSeriesFileNames(d, uid))
        except Exception:
            files = []
    n_series = len(_series_ids(d)) or 1
    if len(files) > 1:
        return _read_series(files, p, n_series=n_series)
    return _read_single_sitk(p, src_fmt="dicom", n_series=n_series)


# ---- TIFF ------------------------------------------------------------------ #
def _read_tiff(path: str):
    tf = _tifffile()
    p = str(path)
    try:
        with tf.TiffFile(p) as t:
            shp = tuple(int(s) for s in t.series[0].shape)
    except Exception as e:
        raise _bad_read(p, e) from None
    if len(shp) == 2:
        raise ValueError("%s: this TIFF is a single 2-D image, not a volume — 2-D raster "
                         "I/O is out of scope here (use imgio.load for that)" % p)
    if len(shp) != 3:
        raise ValueError("%s: TIFF series has shape %r; only a 3-D (D, H, W) volume is "
                         "supported (4-D / RGB stacks are out of scope)" % (p, shp))
    _check_voxel_budget(int(np.prod(shp, dtype=np.int64)), p)
    try:
        arr = np.asarray(tf.imread(p))
    except Exception as e:
        raise _bad_read(p, e) from None
    if arr.ndim != 3:
        raise ValueError("%s: TIFF decoded to a %d-D array, expected a 3-D volume"
                         % (p, arr.ndim))
    vol = _to_finite_f64(arr, p)
    return vol, VolumeMeta(dtype=str(arr.dtype), source_format="tiff")


# ---- headerless raw -------------------------------------------------------- #
def _read_raw(path: str, shape, dtype):
    p = str(path)
    if shape is None or dtype is None:
        raise ValueError("%s: a headerless raw volume needs explicit shape=(D, H, W) and "
                         "dtype= — the file carries no dimensions" % p)
    try:
        shp = tuple(int(s) for s in shape)
    except (TypeError, ValueError):
        raise ValueError("%s: shape must be an iterable of 3 ints (D, H, W), got %r"
                         % (p, (shape,))) from None
    if len(shp) != 3 or any(s <= 0 for s in shp):
        raise ValueError("%s: shape must be 3 positive ints (D, H, W), got %r" % (p, shp))
    dt = np.dtype(dtype)
    nvox = int(np.prod(shp, dtype=np.int64))
    _check_voxel_budget(nvox, p)                             # float64 output cap first
    expected = nvox * dt.itemsize
    size = os.path.getsize(p)
    if size != expected:
        raise ValueError("%s: raw file is %d bytes, but shape %r as %s is %d bytes "
                         "(%d voxels x %d) — size mismatch, refusing"
                         % (p, size, shp, dt.name, expected, nvox, dt.itemsize))
    arr = np.fromfile(p, dtype=dt)
    if arr.size != nvox:
        raise ValueError("%s: raw read %d values, expected %d" % (p, arr.size, nvox))
    vol = _to_finite_f64(arr.reshape(shp), p)
    return vol, VolumeMeta(dtype=dt.name, source_format="raw")


# ---- NumPy ----------------------------------------------------------------- #
def _read_npy(path: str):
    p = str(path)
    try:
        arr = np.load(p, mmap_mode="r", allow_pickle=False)
    except Exception as e:
        raise _bad_read(p, e) from None
    if arr.ndim != 3:
        raise ValueError("%s: .npy holds a %d-D array; a volume must be 3-D (D, H, W)"
                         % (p, arr.ndim))
    _check_voxel_budget(int(arr.size), p)
    vol = _to_finite_f64(np.array(arr), p)
    return vol, VolumeMeta(dtype=str(arr.dtype), source_format="npy")


def _read_npz(path: str, key):
    p = str(path)
    try:
        npz = np.load(p, allow_pickle=False)
    except Exception as e:
        raise _bad_read(p, e) from None
    try:
        keys = list(npz.files)
        if not keys:
            raise ValueError("%s: .npz contains no arrays" % p)
        if key is None:
            if len(keys) != 1:
                raise ValueError("%s: .npz holds %d arrays %r — pass key= to choose one"
                                 % (p, len(keys), keys))
            key = keys[0]
        elif key not in keys:
            raise ValueError("%s: key %r not in .npz (have %s)" % (p, key, ", ".join(keys)))
        arr = np.asarray(npz[key])
    finally:
        npz.close()
    if arr.ndim != 3:
        raise ValueError("%s: array %r in .npz is %d-D; a volume must be 3-D (D, H, W)"
                         % (p, key, arr.ndim))
    _check_voxel_budget(int(arr.size), p)
    vol = _to_finite_f64(arr, p)
    return vol, VolumeMeta(dtype=str(arr.dtype), source_format="npz")


# ---- public reader --------------------------------------------------------- #
def read_volume(path: str, series_id: Optional[str] = None,
                shape=None, dtype=None, key: Optional[str] = None):
    """Read a volumetric file -> ``(vol, meta)``.

    *vol* is a ``(D, H, W)`` float64 array with **raw** intensities (CT Hounsfield
    units, MRI signal, etc. are not rescaled). *meta* is a :class:`VolumeMeta`.

    The format is chosen from the path: a **directory** (or a ``.dcm`` file) reads
    as a DICOM series; ``.nii/.nii.gz/.nrrd/.nhdr/.mha/.mhd/.hdr`` go through
    SimpleITK; ``.tif/.tiff`` read a multi-page TIFF; ``.raw/.vol/.img`` (no
    sidecar) need ``shape=(D, H, W)`` and ``dtype=``; ``.npy/.npz`` load a saved
    3-D array (``.npz`` also takes ``key=``).

    ``series_id`` picks one series from a multi-series DICOM directory (list them
    with :func:`list_dicom_series`); if a directory holds several series and none
    is chosen, a ``ValueError`` lists the available UIDs.

    Raises ``FileNotFoundError`` for a missing path, and ``ValueError`` for an
    unsupported extension, an over-budget size, a raw size mismatch, a 2-D "not a
    volume" input, or a non-finite voxel — never a partially decoded volume.
    """
    p = str(path)
    if os.path.isdir(p):
        return _read_dicom_dir(p, series_id)
    if not os.path.exists(p):
        raise FileNotFoundError(p)

    suf = _suffix(p)
    if suf in DICOM_FORMATS:
        return _read_dicom_file(p, series_id)
    if suf in (".nii", ".nii.gz", ".nrrd", ".nhdr", ".mha", ".mhd", ".hdr"):
        return _read_single_sitk(p, src_fmt="sitk")
    if suf == ".img":
        # Analyze .img is read via its .hdr sidecar; a lone .img is headerless raw.
        hdr = p[:-4] + ".hdr"
        if os.path.isfile(hdr):
            return _read_single_sitk(hdr, src_fmt="analyze")
        return _read_raw(p, shape, dtype)
    if suf in TIFF_FORMATS:
        return _read_tiff(p)
    if suf in (".raw", ".vol"):
        return _read_raw(p, shape, dtype)
    if suf == ".npy":
        return _read_npy(p)
    if suf == ".npz":
        return _read_npz(p, key)
    raise ValueError("unsupported volume format %r for %s — read_volume handles %s "
                     "(or a DICOM directory)" % (suf, p, ", ".join(VOLUME_FORMATS)))


# ---- writers --------------------------------------------------------------- #
def _write_sitk(path: str, vol: np.ndarray, meta: Optional["VolumeMeta"]) -> None:
    sitk = _sitk()
    img = sitk.GetImageFromArray(np.ascontiguousarray(vol))   # (D,H,W) -> image, depth=D
    if meta is not None:
        try:
            sp = tuple(float(s) for s in meta.spacing_mm)     # (sz, sy, sx)
            if len(sp) == 3:
                img.SetSpacing((sp[2], sp[1], sp[0]))          # -> ITK (sx, sy, sz)
        except Exception:
            pass
        try:
            o = np.asarray(meta.origin, np.float64).ravel()
            if o.size >= 3:
                img.SetOrigin((float(o[0]), float(o[1]), float(o[2])))
        except Exception:
            pass
        try:
            d = np.asarray(meta.direction, np.float64).reshape(3, 3)
            img.SetDirection(tuple(float(x) for x in d.ravel()))
        except Exception:
            pass
    try:
        sitk.WriteImage(img, str(path))
    except Exception as e:
        raise _bad_write(str(path), e) from None


def _write_tiff(path: str, vol: np.ndarray) -> None:
    tf = _tifffile()
    try:
        tf.imwrite(str(path), np.ascontiguousarray(vol))
    except Exception as e:
        raise _bad_write(str(path), e) from None


def write_volume(path: str, vol, meta: Optional["VolumeMeta"] = None) -> None:
    """Write a ``(D, H, W)`` volume, format chosen from the extension.

    ``.nii/.nii.gz/.nrrd/.nhdr/.mha/.mhd/.hdr`` are written through SimpleITK,
    carrying ``meta``'s spacing / origin / direction so ``read_volume`` round-trips
    the geometry; ``.tif/.tiff`` write a multi-page TIFF via tifffile; ``.npy`` and
    ``.npz`` save the array with NumPy (the ``.npz`` key is ``"volume"``).

    The array is written in its own dtype (RGB / multi-component volumes are not
    supported). DICOM *series* writing and headerless raw writing are intentionally
    out of scope (they need per-slice tags / an external sidecar) and raise
    ``ValueError``. A non-finite voxel is refused.
    """
    p = str(path)
    v = np.asarray(vol)
    if v.ndim != 3:
        raise ValueError("%s: write_volume needs a 3-D (D, H, W) array, got a %d-D array"
                         % (p, v.ndim))
    if not np.isfinite(np.asarray(v, np.float64)).all():
        raise ValueError("%s: refusing to write a volume with non-finite (NaN/Inf) voxels" % p)

    suf = _suffix(p)
    if suf in (".nii", ".nii.gz", ".nrrd", ".nhdr", ".mha", ".mhd", ".hdr"):
        _write_sitk(p, v, meta)
    elif suf in TIFF_FORMATS:
        _write_tiff(p, v)
    elif suf == ".npy":
        np.save(p, v)
    elif suf == ".npz":
        np.savez(p, volume=v)
    elif suf in DICOM_FORMATS:
        raise ValueError("%s: DICOM series writing is out of scope for write_volume — "
                         "write NIfTI / NRRD / MetaImage instead" % p)
    elif suf in (".raw", ".vol", ".img"):
        raise ValueError("%s: headerless raw writing is out of scope (dimensions would be "
                         "lost) — write NIfTI / NRRD / MetaImage / .npy instead" % p)
    else:
        raise ValueError("unsupported write format %r for %s — write_volume handles "
                         ".nii/.nii.gz/.nrrd/.nhdr/.mha/.mhd/.hdr, .tif/.tiff, .npy, .npz"
                         % (suf, p))
