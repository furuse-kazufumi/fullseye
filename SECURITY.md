# Security Policy

**Language:** [English](SECURITY.md) · [日本語](SECURITY.ja.md)

## Supported versions

Security fixes are provided only for the latest minor release line published on PyPI. Users of older release lines should upgrade before requesting a security fix.

## Reporting a vulnerability

Use GitHub Private vulnerability reporting: open the repository's **Security** tab and choose **Report a vulnerability**, or go directly to [the private advisory form](https://github.com/furuse-kazufumi/fullseye/security/advisories/new).

Do not open a public issue containing vulnerability details. If the private reporting button is unavailable, open a public issue that asks only for a private communication channel. Do not include technical details, reproduction steps, logs, or exploit material in that issue.

Please include:

- the affected Fullseye version;
- the operating system and Python version;
- the affected entry point, such as the Python API, CLI, MCP server, or Studio;
- a minimal reproduction; and
- the security impact you expect.

## Response targets

The following are best-effort targets, not guarantees. Fullseye is a small project maintained in spare time.

- Acknowledgement within 7 days.
- Initial assessment within 14 days.
- For a confirmed issue, a fix or mitigation plan aimed for within 90 days.
- Coordinated disclosure through a GitHub Security Advisory.

## In scope

Security boundaries maintained by this repository are in scope, including:

- the MCP server started with `python -m fullseye.mcp`;
- Fullseye Studio, the desktop GUI; and
- code that reads files, including image and raster, volume and medical-image, mesh and point-cloud readers, and XML, JSON, pipeline, or definition loaders.

Examples include a crafted input file causing code execution or path traversal, a parser consuming unbounded memory or CPU, or an MCP request escaping its documented path, process, network, time, memory, or output limits.

## Out of scope

- Python code that a user writes and runs is outside Fullseye's security boundary. This includes Python run from Studio, such as the Python Editor (which runs a script in a subprocess) and the Program pane when it runs Python (which runs inside the Studio process): such code has the user's own privileges. Code that runs without the user asking for it, for example because a file or project was merely opened, or without the confirmation Studio asks for, is in scope.
- Vulnerabilities in optional third-party dependencies themselves should be reported upstream. However, please report when Fullseye's declared lower bound permits a dependency version with a known vulnerability.
- Results that are only numerically incorrect, without a security impact, belong in the [normal bug tracker](https://github.com/furuse-kazufumi/fullseye/issues).

## Related documents

- [MCP server boundaries, resource limits, and fail-closed behaviour](docs/MCP.md)
- [Supported file-format inventory](docs/FILE_FORMATS.md)
- [Hardening findings and regression gates](docs/HARDENING.en.md)
- [Dependency-audit allowlist](docs/security/pip_audit_allowlist.json)
- [CycloneDX SBOM](docs/sbom/fullseye.cdx.json), regenerated with `py -3.11 tools/gen_sbom.py`
