"""Keep the checked-in pytest-split baseline useful as the suite evolves."""

import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_duration_baseline_covers_at_least_95_percent_of_collected_tests(request):
    durations = json.loads((ROOT / ".test_durations").read_text(encoding="utf-8"))
    collected = {item.nodeid for item in request.session.items}
    covered = collected & durations.keys()
    ratio = len(covered) / len(collected)
    assert ratio >= 0.95, (
        f".test_durations covers {len(covered)}/{len(collected)} collected tests "
        f"({ratio:.1%}); refresh it with pytest --store-durations"
    )
