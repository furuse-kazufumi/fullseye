# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""公式 CommonRoad drivability-checker で solution XML を採点し、drivecommonroad.cr_checker_result が読む JSON を書く(Linux / WSL 用)。

採点器(commonroad-drivability-checker)は Linux でしか動かないので、Windows 側の repo はこのスクリプトが書いた JSON を
``drivecommonroad.cr_checker_result`` で読む。各検査は個別に呼び、例外(採点器は不合格を例外で返す)は False + 理由として記録する。

Usage:
    python3 check_solution_json.py <scenario.xml> <solution.xml> <out.json>

出力 JSON: ``{"scenario", "solution", "valid", "goal_reached", "feasible", "obstacle_collision", "boundary_collision",
"checker_version", "details": {<check>: {"ok", "message"}}, "n_states", "benchmark_id", "feasibility": {pp_id: {...}}}``。
``valid`` は ``solution_checker.valid_solution`` の戻り値(個別検査の and ではなく、採点器自身の判定)。終了コードは valid なら 0、
そうでなければ 1、引数・読み込みの失敗は 2。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _version(mod) -> str:
    v = getattr(mod, "__version__", None)
    if v:
        return str(v)
    try:
        from importlib.metadata import version
        return version("commonroad-drivability-checker")
    except Exception:  # noqa: BLE001
        return "unknown"


def main(argv) -> int:
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2
    scenario_path, solution_path, out_path = (Path(a) for a in argv[1:4])
    if not scenario_path.is_file() or not solution_path.is_file():
        print("scenario or solution file not found", file=sys.stderr)
        return 2
    from commonroad.common.file_reader import CommonRoadFileReader
    from commonroad.common.solution import CommonRoadSolutionReader
    import commonroad_dc
    from commonroad_dc.feasibility import solution_checker as sc

    scenario, pps = CommonRoadFileReader(str(scenario_path)).open(lanelet_assignment=True)
    solution = CommonRoadSolutionReader.open(str(solution_path))
    details = {}

    def run(name, fn, *args):
        try:
            r = fn(*args)
            details[name] = {"ok": True, "result": bool(r), "message": ""}
            return bool(r)
        except Exception as ex:  # noqa: BLE001 — 採点器は不合格を例外で返す
            details[name] = {"ok": False, "result": None, "message": "%s: %s" % (type(ex).__name__, ex)}
            return None

    solved = run("solved_all_problems", sc.solved_all_problems, pps, solution)
    goal = run("goal_reached", sc.goal_reached, scenario, pps, solution)
    starts = run("starts_at_correct_state", sc.starts_at_correct_state, solution, pps)
    obs = run("obstacle_collision", sc.obstacle_collision, scenario, pps, solution)
    bnd = run("boundary_collision", sc.boundary_collision, scenario, pps, solution)
    ego = run("ego_collision", sc.ego_collision, scenario, pps, solution)

    feasibility = {}
    feasible_all = None
    try:
        results = sc.solution_feasible(solution, scenario.dt, pps)
        feasible_all = True
        for pp_id, (feasible, inputs, traj) in results.items():
            feasibility[str(pp_id)] = {"feasible": bool(feasible), "n_reconstructed_inputs": len(inputs.state_list),
                                       "first_infeasible_transition": None if feasible else len(inputs.state_list) - 1}
            feasible_all = feasible_all and bool(feasible)
        details["solution_feasible"] = {"ok": True, "result": feasible_all, "message": ""}
    except Exception as ex:  # noqa: BLE001
        details["solution_feasible"] = {"ok": False, "result": None, "message": "%s: %s" % (type(ex).__name__, ex)}

    valid = False
    try:
        valid, _ = sc.valid_solution(scenario, pps, solution)
        valid = bool(valid)
        details["valid_solution"] = {"ok": True, "result": valid, "message": ""}
    except Exception as ex:  # noqa: BLE001
        details["valid_solution"] = {"ok": False, "result": None, "message": "%s: %s" % (type(ex).__name__, ex)}

    pp_sol = solution.planning_problem_solutions[0]
    out = {
        "scenario": str(scenario.scenario_id), "solution": solution_path.name, "benchmark_id": solution.benchmark_id,
        "valid": valid,
        "goal_reached": goal is True,
        "feasible": feasible_all is True,
        # 採点器は衝突を例外で返す: 例外 = 衝突あり、False が返れば衝突なし
        "obstacle_collision": obs is None,
        "boundary_collision": bnd is None,
        "ego_collision": ego is None,
        "solved_all_problems": solved is True,
        "starts_at_correct_state": starts is True,
        "n_states": len(pp_sol.trajectory.state_list),
        "checker_version": "commonroad-drivability-checker %s" % _version(commonroad_dc),
        "details": details, "feasibility": feasibility,
    }
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("scenario", "valid", "goal_reached", "feasible", "obstacle_collision", "boundary_collision")}))
    return 0 if valid else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
