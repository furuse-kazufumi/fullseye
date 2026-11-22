# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""利用者が選んだ JSON を、共通の量・深さ・値の規則で読む。Strict untrusted JSON reader."""
from __future__ import annotations

import json
import os
from typing import Any

from json_safety import MAX_JSON_DEPTH, _check_json_depth

__all__ = ["DEFAULT_MAX_JSON_BYTES", "UntrustedJSONError", "loads_untrusted", "read_untrusted"]

#: 利用者が選ぶ pipeline / definition JSON の上限(bytes)。出荷物の最大 pipeline JSON は
#: examples/data/ai_inspection_recipes_2026_11_08.json の 872,019 bytes、definition JSON は 0 件。
#: 2 MiB は最大実測値の約 2.4 倍を許しつつ、巨大ファイルを解析前に止める。
#: User-selected pipeline/definition JSON byte limit; 2 MiB leaves about 2.4x measured headroom.
DEFAULT_MAX_JSON_BYTES = 2 * 1024 * 1024


class UntrustedJSONError(ValueError):
    """JSON の量・深さ・値の安全上限に反した。An untrusted-JSON safety rule was violated."""


def _reject_constant(name: str) -> Any:
    """JSON 外の非有限定数を断る。Reject Python's non-standard JSON constants."""
    raise UntrustedJSONError("JSON constant %s is not allowed" % name)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """同じ object key を後勝ちにしない。Reject duplicate object keys."""
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise UntrustedJSONError("duplicate key %r in JSON object" % key)
        out[key] = value
    return out


def loads_untrusted(body: str | bytes, *, label: str = "JSON",
                    max_bytes: int = DEFAULT_MAX_JSON_BYTES,
                    max_depth: int = MAX_JSON_DEPTH):
    """信頼しない JSON を量・深さ・有限値・一意 key の検査後に読む。Load untrusted JSON strictly.

    ``JSONDecodeError`` と ``UnicodeDecodeError`` は、呼び元が行・列を表示できるようそのまま返す。
    """
    raw = body.encode("utf-8") if isinstance(body, str) else body
    if len(raw) > max_bytes:
        raise UntrustedJSONError("%s is %d bytes; limit is %d bytes" % (label, len(raw), max_bytes))
    try:
        _check_json_depth(raw, max_depth=max_depth, label=label)
    except ValueError as exc:
        raise UntrustedJSONError(str(exc)) from None
    try:
        return json.loads(body, parse_constant=_reject_constant, object_pairs_hook=_unique_object)
    except RecursionError as exc:
        raise UntrustedJSONError("%s nesting is too deep" % label) from exc


def read_untrusted(path, *, label: str | None = None,
                   max_bytes: int = DEFAULT_MAX_JSON_BYTES,
                   max_depth: int = MAX_JSON_DEPTH):
    """*path* から上限 + 1 byte だけ読み UTF-8 JSON として検査する。Read a bounded UTF-8 JSON file."""
    path = os.fspath(path)
    shown = label or path
    with open(path, "rb") as fh:
        raw = fh.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise UntrustedJSONError("%s is larger than the limit of %d bytes" % (shown, max_bytes))
    text = raw.decode("utf-8")
    return loads_untrusted(text, label=shown, max_bytes=max_bytes, max_depth=max_depth)
