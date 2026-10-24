"""Known-vulnerability gate for the dependencies a user actually installs (pip-audit).

Until 2026-10-24 the CI ran ``pip-audit ... || true`` inside the lint job, whose
environment holds ruff and pip-audit only.  The dependencies a user gets from
``pip install fullseye[...]`` were never audited, and the step could not fail.

This tool closes both gaps:

* ``deps`` (default) resolves **every** requirement declared in ``pyproject.toml``
  (core + all extras) plus the CI-only test packages for one target platform with
  ``pip install --dry-run --report`` (nothing is installed; pip reads the wheel
  metadata only), pins the result and runs ``pip-audit --strict --no-deps
  --disable-pip`` on it against OSV (the same database the dependency floors in
  ``pyproject.toml`` were chosen from).  Any finding fails, except the ones written down with a
  reason and an expiry date in ``docs/security/pip_audit_allowlist.json``.
* ``tools`` audits the CI's own build tools (pip / setuptools / wheel / build) as
  installed in the running interpreter.  The CI runs it as a warning only: an
  upstream CVE in the runner's pip is not a defect of this package.

The allowlist is validated first in both modes: an expired or malformed entry
fails the run (``tests/test_pip_audit_allowlist.py`` checks the same thing on
every test run, so an expiry is noticed even when nobody touches dependencies).

Usage::

    python tools/pip_audit_gate.py                   # deps, for this interpreter's platform
    python tools/pip_audit_gate.py --python-version 3.11
        --platform manylinux_2_28_x86_64 --platform manylinux_2_17_x86_64
        --platform manylinux2014_x86_64          # Linux, from any host (wheels only)
    python tools/pip_audit_gate.py tools             # the build tools (warning in CI)
    python tools/pip_audit_gate.py --check-allowlist # ledger only (no network)
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = ROOT / "docs" / "security" / "pip_audit_allowlist.json"
PYPROJECT = ROOT / "pyproject.toml"

#: Packages the CI test job installs on top of the extras (``ci.yml`` install lines).
#: They run on contributors' machines too, so they are audited with the rest.
CI_TEST_REQUIREMENTS = (
    "pytest", "pytest-cov", "pytest-split", "pytest-xdist", "pytest-randomly",
    "pytest-timeout", "hypothesis", "matplotlib", "sympy", "ziglang",
    "opencv-contrib-python>=4.8.1.78",
)

#: Build / install tools.  Audited separately (``tools`` mode) and never pinned
#: into the ``deps`` audit: what a user has here is their installer, not ours.
TOOL_PACKAGES = ("pip", "setuptools", "wheel", "build")

_ID = re.compile(r"^(GHSA(-[23456789cfghjmpqrvwx]{4}){3}|PYSEC-\d{4}-\d+|CVE-\d{4}-\d{4,}|OSV-\d{4}-\d+)$")
_REQUIRED = ("id", "package", "reason", "expires")
#: An exception is a decision to re-examine, not a permanent waiver.
MAX_HORIZON_DAYS = 366


class AllowlistError(ValueError):
    """The exception ledger is malformed or has expired entries."""


def load_allowlist(path: Path = ALLOWLIST, today: _dt.date | None = None) -> list[dict]:
    """Return the validated entries of the exception ledger.

    Raises :class:`AllowlistError` for a malformed ledger, an entry without a
    reason, an expiry that has passed (``expires < today``) or one more than
    :data:`MAX_HORIZON_DAYS` ahead (a waiver nobody will ever revisit).
    """
    today = today or _dt.date.today()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AllowlistError(f"{path}: cannot read the ledger: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise AllowlistError(f"{path}: expected an object with an 'entries' list")
    problems: list[str] = []
    seen: set[str] = set()
    for i, e in enumerate(data["entries"]):
        where = f"entries[{i}]"
        if not isinstance(e, dict):
            problems.append(f"{where}: not an object")
            continue
        missing = [k for k in _REQUIRED if not isinstance(e.get(k), str) or not e[k].strip()]
        if missing:
            problems.append(f"{where}: missing/empty {missing}")
            continue
        where = f"{where} ({e['id']})"
        ids = [e["id"], *e.get("aliases", [])]
        for vid in ids:
            if not isinstance(vid, str) or not _ID.match(vid):
                problems.append(f"{where}: not an OSV/GHSA/PYSEC/CVE id: {vid!r}")
            elif vid in seen:
                problems.append(f"{where}: id listed twice: {vid}")
            else:
                seen.add(vid)
        try:
            exp = _dt.date.fromisoformat(e["expires"])
        except ValueError:
            problems.append(f"{where}: expires is not YYYY-MM-DD: {e['expires']!r}")
            continue
        if exp < today:
            problems.append(f"{where}: expired on {exp} — re-examine the risk, then fix, "
                            "re-date with a new reason, or remove the entry")
        elif (exp - today).days > MAX_HORIZON_DAYS:
            problems.append(f"{where}: expires {exp} is more than {MAX_HORIZON_DAYS} days ahead")
    if problems:
        raise AllowlistError(f"{path}:\n  " + "\n  ".join(problems))
    return data["entries"]


def ignore_args(entries: list[dict]) -> list[str]:
    """``--ignore-vuln`` arguments for every id and alias in the ledger."""
    out: list[str] = []
    for e in entries:
        for vid in (e["id"], *e.get("aliases", [])):
            out += ["--ignore-vuln", vid]
    return out


def declared_requirements(pyproject: Path = PYPROJECT) -> list[str]:
    """Core dependencies + every optional extra + the CI test packages (deduplicated)."""
    with open(pyproject, "rb") as f:
        project = tomllib.load(f)["project"]
    reqs: list[str] = list(project.get("dependencies", []))
    for group in project.get("optional-dependencies", {}).values():
        reqs += group
    reqs += CI_TEST_REQUIREMENTS
    seen: set[str] = set()
    out = []
    for r in reqs:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def _name(req_line: str) -> str:
    return re.split(r"[<>=!~\[; ]", req_line, maxsplit=1)[0].strip().lower().replace("_", "-")


def resolve(requirements: list[str], platforms: list[str] | None, python_version: str | None) -> list[str]:
    """Pin *requirements* the way pip would install them, without installing.

    Returns ``name==version`` lines (build tools and this project removed).
    """
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "report.json"
        cmd = [sys.executable, "-m", "pip", "install", "--dry-run", "--ignore-installed",
               "--disable-pip-version-check", "--report", str(report)]
        if platforms or python_version:
            # pip only allows a foreign target for wheels (no sdist build on this host).
            # pip does not widen a manylinux tag to the older ones, so pass each tag.
            cmd += ["--only-binary=:all:", "--target", str(Path(tmp) / "unused")]
            for tag in platforms or ():
                cmd += ["--platform", tag]
            if python_version:
                cmd += ["--python-version", python_version]
        cmd += requirements
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError("pip could not resolve the declared dependencies:\n"
                               + proc.stdout[-4000:] + proc.stderr[-4000:])
        installed = json.loads(report.read_text(encoding="utf-8"))["install"]
    pins = []
    for item in installed:
        meta = item["metadata"]
        name = meta["name"].lower().replace("_", "-")
        if name in TOOL_PACKAGES or name == "fullseye":
            continue
        # A local version label (+cpu) is not on PyPI; the advisory data is keyed
        # by the public version.
        pins.append(f"{name}=={meta['version'].split('+', 1)[0]}")
    if not pins:
        raise RuntimeError("the resolver returned nothing to audit — refusing to pass an empty audit")
    return sorted(pins)


def run_pip_audit(pins: list[str], entries: list[dict], label: str) -> int:
    """Audit *pins* (no resolution, strict); return pip-audit's exit status."""
    with tempfile.TemporaryDirectory() as tmp:
        req = Path(tmp) / f"{label}.txt"
        req.write_text("\n".join(pins) + "\n", encoding="utf-8")
        cmd = [sys.executable, "-m", "pip_audit", "-r", str(req), "--no-deps", "--disable-pip",
               "--strict", "--vulnerability-service", "osv", "--progress-spinner", "off",
               "--desc", "on", *ignore_args(entries)]
        print(f"[pip-audit gate] {label}: auditing {len(pins)} pinned packages "
              f"({len(entries)} ledger exceptions)", flush=True)
        return subprocess.run(cmd).returncode


def _installed_tools() -> list[str]:
    from importlib import metadata
    pins = []
    for name in TOOL_PACKAGES:
        try:
            pins.append(f"{name}=={metadata.version(name)}")
        except metadata.PackageNotFoundError:
            continue
    return pins


def manylinux_ladder(glibc: str, arch: str) -> list[str]:
    """Every manylinux tag a host with *glibc* (e.g. ``"2.39"``) accepts, newest first.

    pip does not widen a foreign ``--platform`` to older tags, so the gate has to pass the
    whole ladder a real runner would accept.  Passing only a few rungs (2_28 / 2_17 / 2014)
    made torch unresolvable on CI (2026-10-24): its Linux dependency ``nvidia-cudnn-cu13``
    ships only ``manylinux_2_27`` wheels, a rung that was missing.
    """
    try:
        major, minor = (int(x) for x in glibc.split("."))
    except ValueError:
        raise ValueError(f"--manylinux-glibc must look like 2.39, got {glibc!r}") from None
    if major != 2 or not 17 <= minor <= 99:
        raise ValueError(f"--manylinux-glibc must be 2.17 .. 2.99, got {glibc!r}")
    if not arch or not arch.replace("_", "").isalnum():
        raise ValueError(f"--arch must be a wheel arch such as x86_64, got {arch!r}")
    tags = [f"manylinux_2_{m}_{arch}" for m in range(minor, 16, -1)]
    return tags + [f"manylinux2014_{arch}"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("mode", nargs="?", choices=("deps", "tools"), default="deps")
    ap.add_argument("--platform", action="append",
                    help="target wheel platform tag (repeatable), e.g. manylinux_2_28_x86_64")
    ap.add_argument("--manylinux-glibc",
                    help="target glibc, e.g. 2.39; expands to every manylinux tag down to 2_17")
    ap.add_argument("--arch", default="x86_64", help="wheel arch for --manylinux-glibc")
    ap.add_argument("--python-version", help="target Python, e.g. 3.11")
    ap.add_argument("--check-allowlist", action="store_true", help="validate the ledger only")
    ap.add_argument("--write-pins", type=Path, help="also save the resolved pins here")
    args = ap.parse_args(argv)

    try:
        entries = load_allowlist()
    except AllowlistError as exc:
        print(f"[pip-audit gate] {exc}", file=sys.stderr)
        return 2
    print(f"[pip-audit gate] ledger ok: {len(entries)} exception(s)")
    if args.check_allowlist:
        return 0

    if args.mode == "tools":
        pins = _installed_tools()
        if not pins:
            print("[pip-audit gate] no build tools found", file=sys.stderr)
            return 2
        return run_pip_audit(pins, entries, "tools")

    platforms = list(args.platform or [])
    if args.manylinux_glibc:
        platforms += manylinux_ladder(args.manylinux_glibc, args.arch)
    pins = resolve(declared_requirements(), platforms or None, args.python_version)
    if args.write_pins:
        args.write_pins.write_text("\n".join(pins) + "\n", encoding="utf-8")
    return run_pip_audit(pins, entries, "deps")


if __name__ == "__main__":
    sys.exit(main())
