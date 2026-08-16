"""Packaging marker so the Studio's runtime assets ship in the wheel.

This directory holds DATA, not code: ``i18n.json`` (localisation), ``op_help/``
(per-operator HTML/Markdown help) and ``sample_images/`` (bundled demo images).
``studio.py`` loads them by path relative to itself
(``os.path.dirname(studio.py)/studio_assets/...``), which resolves to
``site-packages/studio_assets/`` in an installed wheel — but only if these files
are actually shipped. Under the flat top-level layout, a plain data directory is
in no package and setuptools drops it; making ``studio_assets`` a declared package
(this ``__init__``) lets ``[tool.setuptools.package-data]`` carry its files.

Do not import from here; the loader is path-based on purpose (works identically in
an editable checkout and an installed wheel).
"""
