from fullseye import opsearch


def _plan_signature(result):
    return [([*plan["ops"]], plan["weight"]) for plan in result.get("plans", [])]


def _search_meta(result):
    return result.get("search") or result["partial"]


def test_planner_budget_is_independent_of_machine_speed(monkeypatch):
    constraints = {
        "query": "corner landmarks for tracking product pose",
        "max_depth": 3,
        "k": 5,
        "executable_only": False,
    }
    normal = opsearch.plan("image", "feature", constraints=constraints)

    tick = -0.0001

    def slow_machine_clock():
        nonlocal tick
        tick += 0.0001
        return tick

    monkeypatch.setattr(opsearch.time, "monotonic", slow_machine_clock)
    slow = opsearch.plan("image", "feature", constraints=constraints)

    assert _plan_signature(slow) == _plan_signature(normal)
    assert slow["search"]["expanded"] == normal["search"]["expanded"]
    assert normal["search"]["deterministic"] is True
    assert slow["search"]["deterministic"] is True


def test_expansion_cap_is_deterministic_across_clocks(monkeypatch):
    constraints = {
        "query": "corner landmarks for tracking product pose",
        "max_depth": 3,
        "k": 5,
        "executable_only": False,
        "max_expansions": 1000,
    }
    normal = opsearch.plan("image", "feature", constraints=constraints)

    tick = -0.01

    def much_slower_clock():
        nonlocal tick
        tick += 0.01
        return tick

    monkeypatch.setattr(opsearch.time, "monotonic", much_slower_clock)
    slow = opsearch.plan("image", "feature", constraints=constraints)

    assert _plan_signature(slow) == _plan_signature(normal)
    assert _search_meta(normal)["expanded"] == _search_meta(slow)["expanded"] == 1000
    assert _search_meta(normal)["limit_reached"] == "max_expansions"
    assert _search_meta(slow)["limit_reached"] == "max_expansions"
    assert _search_meta(normal)["deterministic"] is True
    assert _search_meta(slow)["deterministic"] is True


def test_wall_clock_fuse_is_visible_in_successful_mcp_response(monkeypatch):
    from fullseye.mcp.catalog import Catalog
    from fullseye.mcp.server import call_tool

    calls = 0

    def stalled_machine_clock():
        nonlocal calls
        calls += 1
        return 0.0 if calls <= 100 else 61.0

    monkeypatch.setattr(opsearch.time, "monotonic", stalled_machine_clock)
    response = call_tool(
        "fullseye_plan",
        {"have": "image", "want": "feature", "goal": "cv_good_features"},
        Catalog.load(),
    )
    result = response["structuredContent"]

    assert result["ok"] is True
    assert result["search"]["limit_reached"] == "timeout_ms"
    assert result["search"]["deterministic"] is False
    assert result["partial"] == result["search"]
