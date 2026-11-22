# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""信頼できない JSON を深さ制限つきで読む共通層。

Shared depth-limited loader for untrusted JSON, independent of Python's recursion limit.
"""
from __future__ import annotations

import itertools
import json
import re
from typing import Any

__all__ = ["MAX_JSON_DEPTH"]

#: 配列と辞書を合わせた JSON の入れ子の上限。MCP・定義ファイル・パラメータ束で共有する。
#: Maximum combined array/object nesting, shared by MCP, definitions, and parameter bundles.
MAX_JSON_DEPTH = 64

_JSON_STRING = re.compile(rb'"(?:[^"\\]|\\[\s\S])*"')
_NOT_BRACKET = re.compile(rb"[^\[\]{}]+")
_DEPTH_STEP = [0] * 256
_DEPTH_STEP[ord("[")] = _DEPTH_STEP[ord("{")] = 1
_DEPTH_STEP[ord("]")] = _DEPTH_STEP[ord("}")] = -1


def _json_depth(body: str | bytes) -> int:
    """文字列内の括弧を除く最大の入れ子を返す。Return maximum JSON nesting."""
    raw = body.encode("utf-8", "surrogatepass") if isinstance(body, str) else body
    brackets = _NOT_BRACKET.sub(b"", _JSON_STRING.sub(b"", raw))
    return max(itertools.accumulate(map(_DEPTH_STEP.__getitem__, brackets)), default=0)


def _check_json_depth(body: str | bytes, *, max_depth: int = MAX_JSON_DEPTH, label: str = "JSON") -> None:
    """上限超過を解析前に断る。Reject input above *max_depth* before parsing."""
    raw = body.encode("utf-8", "surrogatepass") if isinstance(body, str) else body
    # 開き括弧の総数が上限以下なら最大深さも上限以下。Skip the scan for shallow input.
    if raw.count(b"[") + raw.count(b"{") > max_depth and _json_depth(raw) > max_depth:
        raise ValueError("%s nesting is deeper than the limit of %d levels" % (label, max_depth))


def _loads_limited(body: str | bytes, *, max_depth: int = MAX_JSON_DEPTH, label: str = "JSON", **kwargs: Any):
    """深さを先に検査する。Validate depth before parsing and hide raw ``RecursionError``."""
    _check_json_depth(body, max_depth=max_depth, label=label)
    try:
        return json.loads(body, **kwargs)
    except RecursionError as exc:
        raise ValueError("%s nesting is too deep" % label) from exc
