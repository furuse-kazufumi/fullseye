"""sample_data.py — opt-in downloader for large sample datasets (NOT bundled).

Design decision (2026-08-28): the fullseye wheel ships only this manifest — a few
kilobytes of *pointers* — never the sample meshes / volumes themselves.  The user
opts in to fetch each dataset **from its original source**, so:

  * the Apache-2.0 / commercial wheel never REDISTRIBUTES third-party data — the
    source's terms (CC-BY attribution, research-only clauses, ...) apply to the
    user's own download, not to us;
  * the wheel stays small;
  * sample code may reference a wide catalog, because pointing to a URL is a
    factual reference, not redistribution.

Honest caveats encoded as fields:

  * ``access="gated"`` — the source requires registration / EULA, or its terms
    forbid automated fetching (e.g. MVTec).  These are NEVER auto-downloaded; the
    tool prints the source page + manual instructions.  Respecting a source's
    *access* terms is a separate obligation from *redistribution*.
  * ``access="info"`` — no stable direct URL pinned yet; the entry is a pointer to
    the source page only.
  * ``commercial`` — does the *source* licence clear commercial use?  ``"yes"`` /
    ``"no"`` / ``"check"`` (read the source page).  Note: running a dataset
    locally and *publishing a rendered image of it* are different questions.

Security (fail-closed):

  * URL scheme allowlist: ``https`` only.  ``file://`` is allowed **only** when
    ``FULLSEYE_SAMPLES_ALLOW_FILE=1`` (used by the offline test).
  * a pinned ``sha256`` is verified before a download is accepted; mismatch
    => the partial file is deleted and an error raised.
  * archive extraction is path-traversal / zip-slip safe: only the *named* member
    is written, to a destination proven to resolve under the samples dir.
  * nothing is fetched without explicit opt-in (``download(..., yes=True)`` /
    CLI ``--yes``).  Without it the tool only prints what *would* be fetched.
"""
from __future__ import annotations

import hashlib
import os
import posixpath
import shutil
import sys
import tempfile

# ---------------------------------------------------------------------------
# manifest — curated, honest.  Only entries whose source URL and licence I am
# confident about are marked access="direct"; the rest are "info"/"gated".
# sha256/bytes are pinned from a real fetch so `verify` is meaningful.
# ---------------------------------------------------------------------------
_STANFORD = "https://graphics.stanford.edu/pub/3Dscanrep"

MANIFEST = [
    # ---- meshes: public domain / CC0 (clearly commercial-safe) ----
    dict(
        id="triceratops", name="Triceratops horridus (skeleton)",
        category="mesh", fmt="glb",
        url=("https://3d-api.si.edu/content/document/3d_package:"
             "d8c623be-4ebc-11ea-b77f-2e728ce88125/resources/"
             "Triceratops_horridus_Marsh_1889-150k-4096.glb"),
        archive=None, member=None, dest="triceratops.glb",
        sha256="cd8525c7371d14876bcdefe3f579d216bf597db892c2de6ed597da86bf1a98b3",
        bytes=14395048,
        license="CC0-1.0", commercial="yes", access="direct",
        source_page="https://3d.si.edu/object/3d/triceratops-horridus-marsh-1889:d8c623be-4ebc-11ea-b77f-2e728ce88125",
        attribution="Smithsonian Institution (CC0)",
        doc="150k-face dinosaur skeleton; try render_beauty, ambient_occlusion, decimate_qem.",
    ),
    # ---- meshes: Stanford 3D Scanning Repository (research courtesy) ----
    dict(
        id="bunny", name="Stanford Bunny",
        category="mesh", fmt="ply",
        url=_STANFORD + "/bunny.tar.gz",
        archive="tar.gz", member="bunny/reconstruction/bun_zipper.ply",
        dest="bunny.ply",
        sha256="a5720bd96d158df403d153381b8411a727a1d73cff2f33dc9b212d6f75455b84",
        bytes=4894286,
        license="Stanford 3DSR (research courtesy)", commercial="check",
        access="direct",
        source_page="https://graphics.stanford.edu/data/3Dscanrep/",
        attribution="Stanford Computer Graphics Laboratory",
        doc="Classic 35k-vert test mesh; try laplacian_smooth, curvature, render_beauty.",
    ),
    dict(
        id="dragon", name="Stanford Dragon",
        category="mesh", fmt="ply",
        url=_STANFORD + "/dragon/dragon_recon.tar.gz",
        archive="tar.gz", member="dragon_recon/dragon_vrip.ply",
        dest="dragon.ply",
        sha256="74ac1d90989c9b1732edee82d57e9ce71452144cf4355f108d8c9c616d28d02f",
        bytes=11197764,
        license="Stanford 3DSR (research courtesy)", commercial="check",
        access="direct",
        source_page="https://graphics.stanford.edu/data/3Dscanrep/",
        attribution="Stanford Computer Graphics Laboratory",
        doc="High-detail 566k-face mesh; good stress test for decimate_qem / AO.",
    ),
    dict(
        id="armadillo", name="Stanford Armadillo",
        category="mesh", fmt="ply",
        url=_STANFORD + "/armadillo/Armadillo.ply.gz",
        archive="gz", member=None, dest="armadillo.ply",
        sha256="8b9b56cc36e66d54429b1e1e75bd89e833645bfe0dc7c1afd1205877a7356a3f",
        bytes=3874291,
        license="Stanford 3DSR (research courtesy)", commercial="check",
        access="direct",
        source_page="https://graphics.stanford.edu/data/3Dscanrep/",
        attribution="Stanford Computer Graphics Laboratory",
        doc="Articulated figure; try vertex_normals, symmetry3d, render_beauty.",
    ),
    # ---- asteroid: public domain, but no stable direct URL pinned here ----
    dict(
        id="itokawa", name="25143 Itokawa (Hayabusa / Gaskell shape model)",
        category="mesh", fmt="stl",
        url=None, archive="gz", member=None, dest="itokawa.stl",
        sha256="6c0a6f2f158b95e33df35d3ab939a70e18701e840ca8106edc50711cea4a1967",
        bytes=1248214,
        license="Public Domain (JAXA/NASA PDS)", commercial="yes", access="info",
        source_page="https://sbn.psi.edu/pds/resource/itokawashape.html",
        attribution="Gaskell/JAXA Hayabusa mission (public domain)",
        doc="49152-face rubble-pile asteroid; try occupancy->mesh, curvature. "
            "Fetch the STL form from the source page, place at the dest, then `verify`.",
    ),
    # ---- wider catalog (pointers only; user fetches under source terms) ----
    dict(
        id="google-scanned", name="Google Scanned Objects (colourful GLBs)",
        category="mesh", fmt="glb", url=None, archive=None, member=None,
        dest="google_scanned/", sha256=None, bytes=None,
        license="CC-BY-4.0", commercial="yes", access="info",
        source_page="https://app.gazebosim.org/GoogleResearch/fuel/collections/Scanned%20Objects%20by%20Google%20Research",
        attribution="Google Research — Google Scanned Objects (CC BY 4.0)",
        doc="1000+ textured everyday objects; ideal for colourful textured rendering.",
    ),
    dict(
        id="open-scivis", name="Open SciVis Datasets (volumes: foot, tooth, bonsai...)",
        category="volume", fmt="raw", url=None, archive=None, member=None,
        dest="scivis/", sha256=None, bytes=None,
        license="per-dataset (see source)", commercial="check", access="info",
        source_page="https://klacansky.com/open-scivis-datasets/",
        attribution="Open SciVis Datasets (per-dataset provenance on source page)",
        doc="Classic CT/simulation volumes; try marching_cubes, vol_watershed, render_beauty.",
    ),
    dict(
        id="mvtec-ad", name="MVTec Anomaly Detection (registration required)",
        category="image", fmt="png", url=None, archive=None, member=None,
        dest="mvtec/", sha256=None, bytes=None,
        license="CC BY-NC-SA 4.0 (non-commercial)", commercial="no", access="gated",
        source_page="https://www.mvtec.com/company/research/datasets/mvtec-ad",
        attribution="MVTec Software GmbH",
        doc="Industrial defect images. Non-commercial + registration: NOT auto-downloaded.",
    ),
]

_BY_ID = {e["id"]: e for e in MANIFEST}

_KNOWN_ARCHIVES = {None, "gz", "tar.gz", "zip"}
_KNOWN_ACCESS = {"direct", "gated", "info"}
_MAX_BYTES = 512 * 1024 * 1024  # 512 MB hard cap per file


def _validate_manifest():
    """fail-closed sanity check of the shipped manifest (catches typos early)."""
    seen = set()
    for e in MANIFEST:
        i = e["id"]
        if i in seen:
            raise ValueError("duplicate sample id %r" % i)
        seen.add(i)
        if e["archive"] not in _KNOWN_ARCHIVES:
            raise ValueError("%s: unknown archive %r" % (i, e["archive"]))
        if e["access"] not in _KNOWN_ACCESS:
            raise ValueError("%s: unknown access %r" % (i, e["access"]))
        if e["access"] == "direct" and not e.get("url"):
            raise ValueError("%s: access=direct requires a url" % i)
        d = e["dest"]
        if d.startswith("/") or d.startswith("\\") or ".." in d.replace("\\", "/").split("/"):
            raise ValueError("%s: unsafe dest %r" % (i, d))


_validate_manifest()


# ---------------------------------------------------------------------------
# paths
# ---------------------------------------------------------------------------
def data_dir() -> str:
    """Absolute samples directory (``$FULLSEYE_DATA_DIR`` or a per-user data dir)."""
    env = os.environ.get("FULLSEYE_DATA_DIR")
    if env:
        base = env
    elif os.name == "nt":
        root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        base = os.path.join(root, "fullseye", "samples")
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~/Library/Application Support"),
                            "fullseye", "samples")
    else:
        root = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
        base = os.path.join(root, "fullseye", "samples")
    return os.path.abspath(base)


def open_dir() -> str:
    """Create the samples folder if needed and open it in the OS file manager.

    Returns the path (with a note appended if it could not be auto-opened).
    """
    d = data_dir()
    os.makedirs(d, exist_ok=True)
    import subprocess
    try:
        if os.name == "nt":
            os.startfile(d)  # type: ignore[attr-defined]  # noqa: E501 (Windows only)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", d])
        else:
            subprocess.Popen(["xdg-open", d])
    except Exception as ex:  # headless / no file manager: still return the path
        return "%s  (could not auto-open: %s)" % (d, ex)
    return d


def _target(entry) -> str:
    """Absolute path for *entry*'s local file, proven to stay under data_dir()."""
    root = data_dir()
    p = os.path.abspath(os.path.join(root, entry["dest"]))
    # containment guard (defence in depth; manifest is also validated).
    if os.path.commonpath([root, p]) != root:
        raise ValueError("dest escapes samples dir: %r" % entry["dest"])
    return p


# ---------------------------------------------------------------------------
# public read-only API
# ---------------------------------------------------------------------------
def catalog() -> list:
    """The manifest (list of entry dicts)."""
    return [dict(e) for e in MANIFEST]


def entry(sample_id: str) -> dict:
    if sample_id not in _BY_ID:
        raise KeyError("unknown sample %r (have: %s)"
                       % (sample_id, ", ".join(sorted(_BY_ID))))
    return dict(_BY_ID[sample_id])


def local_path(sample_id: str):
    """Path to the downloaded file, or ``None`` if not present."""
    e = _BY_ID.get(sample_id)
    if e is None or e["dest"].endswith("/"):
        return None
    p = _target(e)
    return p if os.path.exists(p) else None


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(sample_id: str) -> bool:
    """True iff the local file exists and matches the pinned sha256.

    Returns False (never raises) when the file is missing.  An entry with no
    pinned sha256 counts as verified once the file simply exists.
    """
    e = entry(sample_id)
    p = local_path(sample_id)
    if p is None:
        return False
    if not e.get("sha256"):
        return True
    return _sha256(p) == e["sha256"]


# ---------------------------------------------------------------------------
# download (opt-in, fail-closed)
# ---------------------------------------------------------------------------
def _allowed_schemes():
    s = {"https"}
    if os.environ.get("FULLSEYE_SAMPLES_ALLOW_FILE") == "1":
        s.add("file")
    return s


def _safe_member_extract(fileobj, member_name: str, out_path: str):
    """Write a single archive member to *out_path* with a traversal guard."""
    norm = posixpath.normpath(member_name.replace("\\", "/"))
    if norm.startswith("/") or norm.startswith("../") or norm == ".." or "/../" in norm:
        raise ValueError("unsafe archive member %r" % member_name)
    with open(out_path, "wb") as w:
        shutil.copyfileobj(fileobj, w)


def download(sample_id: str, *, yes: bool = False, quiet: bool = False,
             _opener=None) -> str:
    """Fetch *sample_id* into :func:`data_dir`.  Returns the local path.

    Without ``yes=True`` nothing is fetched — the tool only prints what *would*
    be downloaded (name / source / licence / size).  ``access`` other than
    ``"direct"`` is never auto-fetched.
    """
    import urllib.request

    e = entry(sample_id)

    def say(*a):
        if not quiet:
            print(*a)

    # non-direct: print guidance, never touch the network.
    if e["access"] != "direct":
        say("[%s] %s" % (e["id"], e["name"]))
        say("  licence : %s  (commercial: %s)" % (e["license"], e["commercial"]))
        say("  access  : %s - not auto-downloaded." % e["access"])
        say("  source  : %s" % e["source_page"])
        if e.get("attribution"):
            say("  cite    : %s" % e["attribution"])
        say("  note    : %s" % e["doc"])
        return ""

    target = _target(e)
    if os.path.exists(target) and verify(sample_id):
        say("[%s] already present and verified: %s" % (e["id"], target))
        return target

    size = ("%.1f MB" % (e["bytes"] / 1e6)) if e.get("bytes") else "unknown size"
    say("[%s] %s  (%s)" % (e["id"], e["name"], size))
    say("  source : %s" % e["url"])
    say("  licence: %s  (commercial: %s)" % (e["license"], e["commercial"]))
    if e.get("attribution"):
        say("  cite   : %s" % e["attribution"])
    if not yes:
        say("  -> re-run with --yes to download from the source above.")
        return ""

    scheme = (e["url"].split(":", 1)[0] or "").lower()
    if scheme not in _allowed_schemes():
        raise ValueError("refusing URL scheme %r (allowed: %s)"
                         % (scheme, ", ".join(sorted(_allowed_schemes()))))

    os.makedirs(os.path.dirname(target), exist_ok=True)
    opener = _opener or urllib.request.urlopen
    tmp = target + ".part"
    h = hashlib.sha256()
    total = 0
    try:
        req = urllib.request.Request(e["url"], headers={"User-Agent": "fullseye-sample-data"})
        with opener(req) as resp, open(tmp, "wb") as w:
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                total += len(chunk)
                if total > _MAX_BYTES:
                    raise ValueError("download exceeds %d-byte cap" % _MAX_BYTES)
                h.update(chunk)
                w.write(chunk)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise

    if e.get("sha256") and h.hexdigest() != e["sha256"]:
        os.remove(tmp)
        raise ValueError("[%s] sha256 mismatch (got %s, expected %s) - deleted."
                         % (e["id"], h.hexdigest(), e["sha256"]))
    if not e.get("sha256"):
        say("  ! no pinned sha256 for this entry - integrity not verified.")

    # unpack the single wanted member / decompress, then atomically place.
    arch = e["archive"]
    try:
        if arch is None:
            os.replace(tmp, target)
        elif arch == "gz":
            import gzip
            with gzip.open(tmp, "rb") as g:
                _safe_member_extract(g, e["dest"], target)
            os.remove(tmp)
        elif arch == "tar.gz":
            import tarfile
            with tarfile.open(tmp, "r:gz") as tf:
                m = tf.getmember(e["member"])
                if not m.isfile():
                    raise ValueError("member %r is not a regular file" % e["member"])
                src = tf.extractfile(m)
                if src is None:
                    raise ValueError("cannot read member %r" % e["member"])
                _safe_member_extract(src, e["member"], target)
            os.remove(tmp)
        elif arch == "zip":
            import zipfile
            with zipfile.ZipFile(tmp) as zf:
                with zf.open(e["member"]) as src:
                    _safe_member_extract(src, e["member"], target)
            os.remove(tmp)
        else:  # pragma: no cover - guarded by _validate_manifest
            raise ValueError("unknown archive %r" % arch)
    except Exception:
        for p in (tmp, target):
            if os.path.exists(p):
                os.remove(p)
        raise

    say("  -> %s" % target)
    return target
