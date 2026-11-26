# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""2026-07-28 modern と initialize-era legacy の実 stdio 往復。

Every fixture starts the real MCP subprocess and uses the specification's
newline-delimited stdio framing.  Assertions name every required field so an empty
version table or a partly implemented discovery result cannot pass vacuously.

各 fixture は本物の MCP subprocess を起動し、仕様どおり改行区切り stdio で往復する。
必須 field を個別に表明し、版一覧を空にする・discover の項目を消す破壊で必ず落ちる門にする。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from fullseye.mcp import server as S


ROOT = Path(__file__).resolve().parents[1]


def _meta(version: object = "2026-07-28", *, capabilities: object = None) -> dict:
    meta = {S.PROTOCOL_VERSION_META: version}
    if capabilities is not None:
        meta[S.CLIENT_CAPABILITIES_META] = capabilities
    return meta


def _request(request_id: int, method: str, params: dict | None = None) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}


def _modern_request(request_id: int, method: str, **params) -> dict:
    params["_meta"] = _meta(capabilities={})
    return _request(request_id, method, params)


def _exchange(*messages: dict) -> tuple[dict[int, dict], str]:
    """Run one real stdio process / 実 stdio process 1 本で順番に往復する。"""
    payload = b"".join(json.dumps(message, ensure_ascii=False).encode("utf-8") + b"\n"
                       for message in messages)
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONPATH=str(ROOT))
    done = subprocess.run(
        [sys.executable, "-P", "-m", "fullseye.mcp"], input=payload, cwd=ROOT, env=env,
        capture_output=True, timeout=180, check=False)
    stderr = done.stderr.decode("utf-8", "replace")
    assert done.returncode == 0, stderr[-2000:]
    lines = done.stdout.splitlines()
    replies = [json.loads(line) for line in lines]
    assert len(lines) == len(replies)  # stdout contains JSON-RPC only / stdout は JSON-RPC 専用
    return {reply["id"]: reply for reply in replies}, stderr


@pytest.fixture(scope="module")
def modern_workflow():
    return _exchange(
        _modern_request(1, "server/discover"),
        _modern_request(2, "tools/list"),
        _modern_request(3, "tools/list"),
        _modern_request(4, "tools/call", name="fullseye_find_ops",
                        arguments={"query": "gaussian", "limit": 1}),
    )


@pytest.fixture(scope="module")
def modern_rejections():
    return _exchange(
        _request(10, "tools/list", {"_meta": _meta("1900-01-01", capabilities={})}),
        _request(11, "tools/list", {"_meta": _meta()}),
        _request(12, "tools/list", {"_meta": _meta(20260728, capabilities={})}),
        _modern_request(13, "ping"),
        _modern_request(14, "tools/call", name="fullseye_find_ops", arguments={}),
        _modern_request(15, "tools/call", name="does_not_exist", arguments={}),
    )


@pytest.fixture(scope="module")
def legacy_workflow():
    return _exchange(
        _request(20, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                     "clientInfo": {"name": "dual-era-test", "version": "0"}}),
        _request(21, "tools/list"),
        _request(22, "tools/call", {"name": "fullseye_find_ops",
                                     "arguments": {"query": "gaussian", "limit": 1}}),
        _request(23, "ping"),
        _request(24, "initialize", {"protocolVersion": "2025-11-25", "capabilities": {},
                                     "clientInfo": {"name": "dual-era-test", "version": "0"}}),
        _request(25, "initialize", {"protocolVersion": "1900-01-01", "capabilities": {},
                                     "clientInfo": {"name": "dual-era-test", "version": "0"}}),
    )


@pytest.fixture(scope="module")
def interleaved_workflow():
    notification = {"jsonrpc": "2.0", "method": "notifications/initialized",
                    "params": {"_meta": _meta(capabilities={})}}
    return _exchange(
        _request(30, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                     "clientInfo": {"name": "dual-era-test", "version": "0"}}),
        _modern_request(31, "tools/list"),
        notification,
        _request(32, "ping"),
    )


def test_server_discover_has_the_complete_non_vacuous_contract(modern_workflow):
    replies, _stderr = modern_workflow
    result = replies[1]["result"]
    required = {"resultType", "supportedVersions", "capabilities", "ttlMs", "cacheScope"}
    assert required <= set(result)
    assert result["resultType"] == "complete"
    assert S.MODERN_VERSIONS and result["supportedVersions"] == list(S.MODERN_VERSIONS)
    assert "2026-07-28" in result["supportedVersions"]
    assert result["capabilities"]["tools"] == {}
    assert isinstance(result["ttlMs"], (int, float)) and not isinstance(result["ttlMs"], bool)
    assert result["cacheScope"] in {"public", "private"}
    info = result["_meta"][S.SERVER_INFO_META]
    assert info["name"] == "fullseye" and isinstance(info["version"], str) and info["version"]


def test_dual_era_client_probe_selects_modern_and_continues(modern_workflow):
    replies, _stderr = modern_workflow
    assert "error" not in replies[1]
    assert replies[2]["result"]["resultType"] == "complete"


def test_modern_tools_list_is_cacheable_nonempty_and_deterministic(modern_workflow):
    replies, _stderr = modern_workflow
    first, second = replies[2]["result"], replies[3]["result"]
    for result in (first, second):
        assert result["resultType"] == "complete"
        assert isinstance(result["ttlMs"], (int, float)) and not isinstance(result["ttlMs"], bool)
        assert result["cacheScope"] in {"public", "private"}
        assert result["tools"]
    assert [tool["name"] for tool in first["tools"]] == [tool["name"] for tool in second["tools"]]


def test_modern_tools_call_completes_with_content(modern_workflow):
    replies, _stderr = modern_workflow
    result = replies[4]["result"]
    assert result["resultType"] == "complete"
    assert result["isError"] is False
    assert result["content"] and result["content"][0]["type"] == "text"


def test_unsupported_modern_version_lists_the_single_source_of_truth(modern_rejections):
    replies, _stderr = modern_rejections
    error = replies[10]["error"]
    assert error["code"] == -32022
    assert error["message"] == "Unsupported protocol version"
    assert error["data"] == {"supported": list(S.MODERN_VERSIONS), "requested": "1900-01-01"}


def test_modern_metadata_is_required_and_typed(modern_rejections):
    replies, _stderr = modern_rejections
    assert replies[11]["error"]["code"] == -32602
    assert S.CLIENT_CAPABILITIES_META in replies[11]["error"]["message"]
    assert replies[12]["error"]["code"] == -32602
    assert S.PROTOCOL_VERSION_META in replies[12]["error"]["message"]


def test_removed_modern_ping_is_method_not_found(modern_rejections):
    replies, _stderr = modern_rejections
    assert replies[13]["error"]["code"] == -32601


def test_modern_tool_argument_errors_are_results_but_unknown_tools_are_protocol_errors(modern_rejections):
    replies, _stderr = modern_rejections
    invalid = replies[14]["result"]
    assert invalid["resultType"] == "complete" and invalid["isError"] is True
    assert invalid["content"]
    assert replies[15]["error"]["code"] == -32602


def test_legacy_2025_06_18_keeps_its_wire_shape_and_methods(legacy_workflow):
    replies, _stderr = legacy_workflow
    assert replies[20]["result"]["protocolVersion"] == "2025-06-18"
    for request_id in (20, 21, 22, 23):
        assert "resultType" not in replies[request_id]["result"]
    assert replies[21]["result"]["tools"]
    assert replies[22]["result"]["content"] and replies[22]["result"]["isError"] is False
    assert replies[23]["result"] == {}


def test_legacy_negotiates_2025_11_25_and_counteroffers_it_for_unknown_versions(legacy_workflow):
    replies, _stderr = legacy_workflow
    assert S.LEGACY_VERSIONS[-1] == "2025-11-25"
    assert replies[24]["result"]["protocolVersion"] == "2025-11-25"
    assert replies[25]["result"]["protocolVersion"] == S.LEGACY_VERSIONS[-1]


def test_each_request_selects_its_era_and_notifications_get_no_reply(interleaved_workflow):
    replies, stderr = interleaved_workflow
    assert set(replies) == {30, 31, 32}
    assert replies[30]["result"]["protocolVersion"] == "2025-06-18"
    assert replies[31]["result"]["resultType"] == "complete"
    assert replies[32]["result"] == {}
    assert "era=modern" in stderr and "era=legacy" in stderr


def test_rejections_are_audited_on_stderr_not_stdout(modern_rejections):
    replies, stderr = modern_rejections
    assert replies  # parsed stdout proves protocol purity / parse 済み stdout が protocol 純度の証拠
    assert "reject era=modern" in stderr
    assert "-32022" in stderr and "-32601" in stderr
