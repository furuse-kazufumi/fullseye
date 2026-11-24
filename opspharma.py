"""Typed ledger for synthetic pharmaceutical vial inspection ops."""
import vialops

_MOD = {"vialops": vialops}

_CATALOG = {
    "synth": [("vial_spin_stop_sequence", "vialops", [], "video")],
    "track": [("track_moving_particles", "vialops", ["video"], "table")],
}


def _build():
    result = {}
    for category, entries in _CATALOG.items():
        for name, module, inputs, output in entries:
            fn = getattr(_MOD[module], name)
            result[name] = {"category": category, "module": module, "in": inputs,
                            "out": output, "func": fn,
                            "doc": fn.__doc__.strip().splitlines()[0]}
    return result


OPSPHARMA = _build()


def list_ops(category=None):
    return [name for name, info in OPSPHARMA.items() if category is None or info["category"] == category]


def get(name):
    return OPSPHARMA[name]["func"]


def call(name, *args, **kwargs):
    result = get(name)(*args, **kwargs)
    return RESULT_ADAPTERS[name](result) if name in RESULT_ADAPTERS else result


def _frames(result):
    return result[0]


RESULT_ADAPTERS = {"vial_spin_stop_sequence": _frames}
