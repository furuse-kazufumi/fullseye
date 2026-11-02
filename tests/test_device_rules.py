"""``device="auto"`` の実測規則の門 / Gates for the measured device rule (no GPU needed)."""
from __future__ import annotations

import json
import tomllib
from pathlib import Path

import numpy as np
import pytest

import api
import device_policy
from tools import gen_device_rules as gen

ROOT = Path(__file__).resolve().parents[1]
RULES = json.loads((ROOT / "fullseye" / "data" / "DEVICE_RULES.json").read_text(encoding="utf-8"))
SMALL = (64, 64)
HUGE = (4096, 4096)


@pytest.fixture
def gpu_box(monkeypatch):
    """CUDA が在る機械のふり。規則の分岐だけを見る(実 GPU には触らない)。"""
    monkeypatch.delenv("FULLSEYE_DEVICE", raising=False)
    monkeypatch.setattr(api, "cuda_available", lambda: True)


def test_table_is_regenerated_from_the_committed_logs():
    assert gen.build() == RULES


def test_table_covers_the_gpu_ops_it_was_measured_on():
    """表が空や一部だけに縮むと、規則は黙って効かなくなる(全部 GPU に戻る)。件数に床を置く。"""
    assert len({r["op"] for r in gen.read_logs("sweep_gpu.jsonl")}) >= 85
    assert len(RULES["ops"]) >= 85
    assert sum(r["min_pixels"] > 0 for r in RULES["ops"].values()) >= 50
    assert set(RULES["ops"]) <= api._gpu_op_names()
    assert set(RULES["batch"]) >= {"point", "separable", "nonseparable", "morphology", "frequency", "iterative"}
    assert RULES["pipeline"]["min_pixels"] > 0


def test_no_measured_point_stays_on_the_cpu_where_the_gpu_wins():
    """★採用条件: 表が CPU に残す点は、測った全点で CPU が GPU に負けていない(揺れの幅を除く)。"""
    cpu = {(r["op"], r["side"], r["a"]): r for r in gen.read_logs("sweep_cpu.jsonl") if r["status"] == "ok"}
    gpu = {(r["op"], r["side"], r["a"]): r for r in gen.read_logs("sweep_gpu.jsonl") if r["status"] == "ok"}
    checked = 0
    for key, g in gpu.items():
        op, side, _a = key
        if key not in cpu or device_policy.route([op], (side, side), rules=RULES) != "cpu":
            continue
        checked += 1
        assert gen.cpu_not_worse(cpu[key]["wall_s"], g["wall_s"]), key
    assert checked >= 50                         # 空を通さない


def test_no_measured_pipeline_stays_on_the_cpu_where_the_gpu_wins():
    cpu = {(r["pipeline"], r["variant"], r["side"]): r for r in gen.read_logs("pipe_cpu.jsonl")
           if r["status"] == "ok" and r["n"] == 1}
    gpu = {(r["pipeline"], r["variant"], r["side"]): r for r in gen.read_logs("gpipe.jsonl")
           if r["status"] == "ok" and r["n"] == 1}
    assert len(gpu) >= 30
    for key, g in gpu.items():
        if key[2] ** 2 < RULES["pipeline"]["min_pixels"] and key in cpu:
            assert gen.cpu_not_worse(cpu[key]["wall_s"], g["wall_s"]), key


def test_small_image_stays_on_cpu_and_large_goes_to_gpu(gpu_box):
    op = min(RULES["ops"], key=lambda o: -RULES["ops"][o]["min_pixels"])
    assert api.resolve_device("auto", stages=(op,), shape=SMALL) == "cpu"
    side = int(RULES["ops"][op]["min_pixels"] ** 0.5) + 1
    assert api.resolve_device("auto", stages=(op,), shape=(side, side)) == "cuda"


def test_explicit_device_and_environment_outrank_the_rule(gpu_box, monkeypatch):
    op = next(iter(RULES["ops"]))
    assert api.resolve_device("cuda", stages=(op,), shape=SMALL) == "cuda"
    assert api.resolve_device("cpu", stages=(op,), shape=HUGE) == "cpu"
    monkeypatch.setenv("FULLSEYE_DEVICE", "cuda")
    assert api.resolve_device("auto", stages=(op,), shape=SMALL) == "cuda"
    monkeypatch.setenv("FULLSEYE_DEVICE", "cpu")
    assert api.resolve_device("auto", stages=(op,), shape=HUGE) == "cpu"
    monkeypatch.setenv("FULLSEYE_DEVICE", "auto")
    assert api.resolve_device("auto", stages=(op,), shape=SMALL) == device_policy.route([op], SMALL)


def test_without_workload_auto_keeps_its_public_meaning(gpu_box):
    assert api.resolve_device("auto") == "cuda"


def test_broken_table_means_the_previous_behaviour(monkeypatch, tmp_path):
    op = next(iter(RULES["ops"]))
    for text in ("{not json", json.dumps({"schema": 2})):
        bad = tmp_path / "rules.json"
        bad.write_text(text, encoding="utf-8")
        monkeypatch.setattr(device_policy, "_PATH", str(bad))
        monkeypatch.setattr(device_policy, "_CACHE", [])
        assert device_policy.route([op], SMALL) == "cuda"


def test_cannot_judge_means_the_previous_behaviour():
    """大きさ不明・未測定の GPU 経路は GPU のまま(黙って CPU へ倒さない)。"""
    op = next(iter(RULES["ops"]))
    assert device_policy.route(["no_such_op"], SMALL, rules=RULES) == "cuda"
    assert device_policy.route([op], None, rules=RULES) == "cuda"
    assert device_policy.route([op, "new_gpu_op"], SMALL, rules=RULES, accelerated={op, "new_gpu_op"}) == "cuda"


def test_cpu_only_stage_does_not_block_the_pipeline_rule():
    op = next(iter(RULES["ops"]))
    assert device_policy.route([op, "clahe"], SMALL, rules=RULES, accelerated={op}) == "cpu"


def test_batch_lowers_or_keeps_the_threshold():
    for op, row in RULES["ops"].items():
        assert device_policy._op_threshold(RULES, op, 16) <= row["min_pixels"]


def test_apply_auto_routes_small_to_cpu_and_large_to_the_accel_path(gpu_box, monkeypatch):
    calls = []

    def fake(op, v, a, b, device):
        calls.append(op.name)
        return v

    monkeypatch.setattr(api, "_try_accel", fake)
    op = max(RULES["ops"], key=lambda o: RULES["ops"][o]["min_pixels"])
    side = int(RULES["ops"][op]["min_pixels"] ** 0.5)
    im = np.linspace(0, 1, 16).reshape(4, 4)
    api.apply(im, op, device="auto")
    assert calls == []
    assert side > 4
    api.apply(np.zeros((side + 1, side + 1)), op, device="auto")
    assert calls == [op]


def test_rule_module_and_table_ship_in_the_wheel():
    cfg = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["setuptools"]
    assert "device_policy" in cfg["py-modules"]
    assert "data/DEVICE_RULES.json" in cfg["package-data"]["fullseye"]
