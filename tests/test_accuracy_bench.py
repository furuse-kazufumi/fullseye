"""Smoke test for the accuracy benchmark harness (tiny budget, one problem)."""
import accuracy_bench


def test_bench_problem_runs_and_reports(tmp_path):
    row = accuracy_bench.bench_problem(
        "denoise", str(tmp_path), gens=2, pop=4, seed=0,
        n_train=3, n_holdout=2, size=24, random_samples=10)
    for k in ("trivial", "hand", "random", "champion_holdout", "gap", "beats_null", "unit"):
        assert k in row
    assert isinstance(row["beats_null"], bool)
    assert row["unit"] == "dB PSNR"


def test_to_markdown_renders_table():
    result = {"config": {"gens": 2, "pop": 4, "seed": 0, "n_train": 3, "n_holdout": 2,
                         "size": 24, "random_samples": 10},
              "rows": [{"problem": "denoise", "unit": "dB PSNR", "trivial": 1.0, "hand": 2.0,
                        "random": 0.5, "champion_train": 3.0, "champion_holdout": 2.5,
                        "gap": 0.5, "beats_null": True, "best_baseline": 2.0, "pipeline": "x"}]}
    md = accuracy_bench.to_markdown(result)
    assert "champion vs null" in md and "denoise" in md and "1/1" in md
