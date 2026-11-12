"""cr_solution_xml の探針は date を固定して渡す(2026-11-12、#308 の CI で秒またぎの偽陽性)。"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import chain_fuzz  # noqa: E402


def test_cr_solution_xml_probe_pins_the_date():
    builder = chain_fuzz.OP_ARG_BUILDERS["cr_solution_xml"]
    args, kwargs = builder(None, None)
    assert isinstance(kwargs.get("date"), datetime)
    import drivecommonroad as CR
    first = CR.cr_solution_xml(*args, **kwargs)
    second = CR.cr_solution_xml(*args, **kwargs)
    assert first == second
    assert 'date="2026-01-01T00:00:00"' in first
