# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pip-audit の例外台帳(docs/security/pip_audit_allowlist.json)の門(2026-10-24)。

例外は「見なかったことにする」ではなく「期限までに見直す決定」。期限が切れた行は
CI を落とす。依存を誰も触らない週でも気づけるように、ネットワーク無しで毎回見る。
あわせて、門が CI に配線されていること(経路が通っていること)も見る。
"""
import datetime as dt
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pip_audit_gate as G  # noqa: E402


def _write(tmp_path, entries):
    p = tmp_path / "allow.json"
    p.write_text(json.dumps({"entries": entries}), encoding="utf-8")
    return p


def _entry(**kw):
    e = {"id": "GHSA-c678-jfcj-6jmf", "package": "torch", "reason": "r", "expires": "2027-01-01"}
    e.update(kw)
    return e


def test_the_committed_ledger_is_valid_and_not_expired():
    entries = G.load_allowlist()
    # 空の台帳は正当(免除が要らなくなった状態)なので件数は求めない。中身の欠けだけを数える。
    blank = [e for e in entries if not (e["package"].strip() and e["reason"].strip())]
    assert not blank, "package / reason が空の行: %r" % blank


def test_an_expired_entry_fails(tmp_path):
    p = _write(tmp_path, [_entry(expires="2026-10-23")])
    with pytest.raises(G.AllowlistError, match="expired"):
        G.load_allowlist(p, today=dt.date(2026, 10, 24))


def test_expiry_day_itself_still_passes(tmp_path):
    p = _write(tmp_path, [_entry(expires="2026-10-24")])
    assert len(G.load_allowlist(p, today=dt.date(2026, 10, 24))) == 1


def test_a_waiver_too_far_ahead_fails(tmp_path):
    p = _write(tmp_path, [_entry(expires="2030-01-01")])
    with pytest.raises(G.AllowlistError, match="more than"):
        G.load_allowlist(p, today=dt.date(2026, 10, 24))


@pytest.mark.parametrize("bad", [
    {"reason": ""},                      # 理由の無い例外
    {"expires": "next year"},            # 日付でない期限
    {"id": "not-an-id"},                 # 識別子でない
    {"aliases": ["CVE-2025-2148", "CVE-2025-2148"]},   # 二重
])
def test_malformed_entries_fail(tmp_path, bad):
    p = _write(tmp_path, [_entry(**bad)])
    with pytest.raises(G.AllowlistError):
        G.load_allowlist(p, today=dt.date(2026, 10, 24))


def test_missing_ledger_fails_closed(tmp_path):
    with pytest.raises(G.AllowlistError):
        G.load_allowlist(tmp_path / "absent.json")


def test_every_id_and_alias_becomes_an_ignore_flag():
    entries = [_entry(aliases=["PYSEC-2025-189", "CVE-2025-2148"])]
    assert G.ignore_args(entries) == [
        "--ignore-vuln", "GHSA-c678-jfcj-6jmf",
        "--ignore-vuln", "PYSEC-2025-189",
        "--ignore-vuln", "CVE-2025-2148"]


def test_declared_requirements_cover_every_extra():
    """監査の対象を pyproject から組み立てる —— extra を足したら自動で監査に入る。"""
    import tomllib
    with open(os.path.join(ROOT, "pyproject.toml"), "rb") as f:
        project = tomllib.load(f)["project"]
    reqs = set(G.declared_requirements())
    for r in project["dependencies"]:
        assert r in reqs
    for group, items in project["optional-dependencies"].items():
        for r in items:
            assert r in reqs, "extra %s の %s が監査の対象に入っていない" % (group, r)
    assert len(reqs) >= 30, "対象が %d 件しかない(読み方が壊れていないか)" % len(reqs)


def test_resolve_refuses_an_empty_result(monkeypatch, tmp_path):
    """解決結果が空なら「0 件の脆弱性」で通さない(空を通す門にしない)。"""
    class _P:
        returncode = 0
        stdout = stderr = ""

    def fake_run(cmd, **kw):
        report = cmd[cmd.index("--report") + 1]
        with open(report, "w", encoding="utf-8") as f:
            json.dump({"install": [{"metadata": {"name": "pip", "version": "26.0"}}]}, f)
        return _P()
    monkeypatch.setattr(G.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="empty"):
        G.resolve(["pip"], None, None)


def test_ci_runs_the_gate_and_does_not_swallow_it():
    """門がある ≠ 経路が通る。ci.yml が deps の監査を `|| true` 無しで呼んでいること。"""
    with open(os.path.join(ROOT, ".github", "workflows", "ci.yml"), encoding="utf-8") as f:
        ci = f.read()
    assert "tools/pip_audit_gate.py --python-version 3.11 --manylinux-glibc" in ci, "CI が依存の監査を回していない"
    swallowed = [ln.strip() for ln in ci.splitlines()
                 if ("pip-audit" in ln or "pip_audit_gate" in ln) and "|| true" in ln]
    assert not swallowed, "監査の失敗を握り潰す形が残っている: %s" % swallowed


def test_manylinux_ladder_covers_every_rung_down_to_2014():
    # 2026-10-24: 2_28 / 2_17 / 2014 だけ渡して、2_27 の wheel しか無い nvidia-cudnn-cu13 が落ちた。
    tags = G.manylinux_ladder("2.39", "x86_64")
    assert tags[0] == "manylinux_2_39_x86_64" and tags[-1] == "manylinux2014_x86_64"
    assert "manylinux_2_27_x86_64" in tags and "manylinux_2_17_x86_64" in tags
    assert len(tags) == 39 - 17 + 1 + 1
    for bad in ("3.1", "2.16", "abc", "2"):
        try:
            G.manylinux_ladder(bad, "x86_64")
        except ValueError:
            continue
        raise AssertionError(bad)
