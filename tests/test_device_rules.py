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
from conftest import requires_backend

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
    # torch が無いと accel の経路が無く、torch のある環境で作った出荷表と食い違う(2026-11-04 master py3.12/3.14)
    requires_backend("torch")
    assert gen.build() == RULES


def test_table_covers_the_gpu_ops_it_was_measured_on():
    """表が空や一部だけに縮むと、規則は黙って効かなくなる(全部 GPU に戻る)。件数に床を置く。"""
    # torch が無いと accel の経路が無く、torch のある環境で作った出荷表と食い違う(2026-11-04 master py3.12/3.14)
    requires_backend("torch")
    assert len({r["op"] for r in gen.read_logs("sweep_gpu.jsonl")}) >= 85
    assert len(RULES["ops"]) >= 85
    assert sum(r["min_pixels"] > 0 for r in RULES["ops"].values()) >= 50
    assert set(RULES["ops"]) <= api._gpu_op_names()
    assert set(RULES["batch"]) >= {"point", "separable", "nonseparable", "morphology", "frequency", "iterative"}
    # 鎖の規則は「測った全点で試した」記録を持つ。試した点・CPU に回した点が空なら、採否は判断ではない。
    pipe = RULES["pipeline"]
    assert pipe["rule"] == "min_stage"
    assert pipe["measured_points"] >= 80
    assert pipe["points_on_cpu"] >= 1
    assert pipe["adopted"] == (not pipe["violations"])


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
    """★採用条件(鎖): 表が CPU に回す鎖の測定点で、CPU が GPU に負けた点が無い(1 枚・16 枚とも)。"""
    points = gen.pipeline_points()
    chains = gen._chains()
    accelerated = api._gpu_op_names()
    assert len(points) >= 80
    for (name, variant, side, n), (cpu_s, gpu_s) in points.items():
        stages = chains[name][variant]
        if device_policy.route(stages, (side, side), n, rules=RULES, accelerated=accelerated) == "cpu":
            assert gen.cpu_not_worse(cpu_s, gpu_s), (name, variant, side, n)


def test_rejected_pipeline_rule_names_measured_losses():
    """不採用の理由は実測の負けでなければならない(ログから数え直す。理由の無い不採用 = 規則の消失を拒む)。"""
    pipe = RULES["pipeline"]
    points = gen.pipeline_points()
    trial = dict(RULES, pipeline={"rule": "min_stage", "adopted": True})
    accelerated = api._gpu_op_names()
    for name, variant, side, n, cpu_s, gpu_s in pipe["violations"]:
        c, g = points[(name, variant, side, n)]
        assert (round(c, 6), round(g, 6)) == (cpu_s, gpu_s)
        assert not gen.cpu_not_worse(c, g)
        stages = gen._chains()[name][variant]
        assert device_policy.route(stages, (side, side), n, rules=trial, accelerated=accelerated) == "cpu"
    if not pipe["adopted"]:
        assert pipe["violations"]
        # 不採用の表では鎖は GPU のまま(規則の無かったときの挙動)
        stages = gen._chains()["scratch_surface"]["all"]
        assert device_policy.route(stages, SMALL, rules=RULES, accelerated=accelerated) == "cuda"


def _single_accel_ops():
    """単独の呼び出しで選ばれる手書き GPU 経路の op(鎖の枠だけの領域の解析の族 = use="pipeline" は除く)。"""
    import gpu_route
    return [o for o in RULES["ops"] if getattr(gpu_route.route(o, "single"), "kind", None) == "accel"]


def test_small_image_stays_on_cpu_and_large_goes_to_gpu(gpu_box):
    op = min(_single_accel_ops(), key=lambda o: -RULES["ops"][o]["min_pixels"])
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
    """GPU 経路の無い段は鎖の判断から外れる(規則が採用されている表で見る。採否は上の門が見る)。"""
    op = max(RULES["ops"], key=lambda o: RULES["ops"][o]["min_pixels"])
    adopted = dict(RULES, pipeline={"rule": "min_stage", "adopted": True})
    assert device_policy.route([op, "clahe"], SMALL, rules=adopted, accelerated={op}) == "cpu"
    assert device_policy.route([op, "clahe"], SMALL, rules=adopted, accelerated={op, "clahe"}) == "cuda"
    assert device_policy.route(["clahe", "kirsch_amp"], SMALL, rules=adopted, accelerated={op}) == "cuda"


def test_batch_lowers_or_keeps_the_threshold():
    for op, row in RULES["ops"].items():
        assert device_policy._op_threshold(RULES, op, 16) <= row["min_pixels"]


def test_apply_auto_routes_small_to_cpu_and_large_to_the_accel_path(gpu_box, monkeypatch):
    calls = []

    def fake(op, v, a, b, device):
        calls.append(op.name)
        return v

    monkeypatch.setattr(api, "_try_accel", fake)
    op = max(_single_accel_ops(), key=lambda o: RULES["ops"][o]["min_pixels"])
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


def test_before_after_on_the_shipped_table():
    """★採用条件の実測(after < before): 出荷する表で CPU に回る点を、規則なし(cuda)と規則あり(auto)で
    同じプロセスで測った 2 回目(``before_after_2.jsonl``、表の材料には入れていない)。全点を測り切っていて、
    揺れの幅(10 % と 50 µs)を超えて遅くなった点が無い。"""
    # torch が無いと accel の経路が無く、torch のある環境で作った出荷表と食い違う(2026-11-04 master py3.12/3.14)
    requires_backend("torch")
    from tools.bench_gpu_crossover import BA_KNOBS, BA_SIDES, sweep_ops
    rows = gen.read_logs("before_after_2.jsonl")
    accelerated = api._gpu_op_names()
    import gpu_route
    # 鎖の枠だけの手書き経路(GPU_ACCEL_USE.json の use="pipeline")は、単独の呼び出しを規則表でなく採用の門が
    # CPU に決める(before も after も同じ CPU の道)。測る点から外し、代わりに単独で CPU になることを決定的に見る。
    chain_only = {op for op, _kind in sweep_ops() if gpu_route.route(op, "single") is None}
    assert len(chain_only) >= 13
    for op in chain_only:
        assert gpu_route.route(op, "pipeline").kind == "accel", op
    expected = {(op, side, a) for op, _kind in sweep_ops() for side in BA_SIDES for a in BA_KNOBS
                if op not in chain_only
                and device_policy.route([op], (side, side), rules=RULES, accelerated=accelerated) == "cpu"}
    measured = {(r["name"], r["side"], r["a"]) for r in rows if r["kind"] == "op"}
    assert len(expected) >= 300
    assert measured == expected
    assert len(rows) >= len(expected)          # 空の rows で下の表明が素通りしない
    for r in rows:
        assert gen.cpu_not_worse(r["after_s"], r["before_s"]), (r["kind"], r["name"], r["side"], r.get("a"))
    assert sum(r["after_s"] for r in rows) < sum(r["before_s"] for r in rows)
    assert {r["kind"] for r in rows} == {"op", "pipeline", "cold"}
