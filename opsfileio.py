# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0.
"""Typed ledger for in-memory file-format readers and writers."""
from __future__ import annotations

import fileio

_CATALOG = {
    "table": [
        ("table_write_csv", ["table"], "text"),
        ("table_read_csv", ["text"], "table"),
    ],
}


def _build():
    result = {}
    for category, entries in _CATALOG.items():
        for name, inputs, output in entries:
            fn = getattr(fileio, name, None)
            doc = fn.__doc__.strip().splitlines()[0] if fn is not None and fn.__doc__ else ""
            result[name] = {"category": category, "module": "fileio", "in": inputs,
                            "out": output, "func": fn, "doc": doc}
    return result


OPSFILEIO = _build()


def call(name, *args, **kwargs):
    return OPSFILEIO[name]["func"](*args, **kwargs)


def list_ops(category=None):
    return [name for name, info in OPSFILEIO.items()
            if category is None or info["category"] == category]


def categories():
    return list(_CATALOG)


def get(name):
    return OPSFILEIO[name]["func"]


def info(name):
    return OPSFILEIO[name]


def missing():
    return [name for name, info in OPSFILEIO.items() if info["func"] is None]
