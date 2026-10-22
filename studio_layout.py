"""Qt-free work-mode and panel-layout state for Studio."""

from dataclasses import dataclass, field, replace
from functools import partial
import json


PANELS = {
    "operators": {"name": "処理を選ぶ", "aliases": ["operator", "operations", "処理", "検索"]},
    "pipeline": {"name": "処理手順と調整", "aliases": ["stage list", "stages", "knobs", "pipeline", "段階", "つまみ"]},
    "display": {"name": "表示と分析", "aliases": ["display range", "histogram", "inspector", "problems", "ヒストグラム", "検査", "問題"]},
    "program": {"name": "コード", "aliases": ["code", "code pane", "program", "プログラム"]},
    "variables": {"name": "変数とオブジェクト", "aliases": ["variables", "objects", "watch", "変数"]},
    "compare": {"name": "段階の前後比較", "aliases": ["compare", "stage in out", "before after", "比較"]},
    "ab": {"name": "A/B 比較", "aliases": ["a/b", "ab compare", "result compare", "結果比較"]},
    "result": {"name": "結果画像", "aliases": ["result", "result view", "image", "画像", "graphics"]},
}


@dataclass(frozen=True)
class WorkMode:
    id: str
    label: str
    visible: frozenset[str]
    large: str
    collapsed: frozenset[str] = frozenset()


MODES = {
    "build": WorkMode("build", "処理を組む", frozenset({"operators", "pipeline", "program", "result"}), "result"),
    "compare": WorkMode("compare", "結果を比べる", frozenset({"ab", "pipeline", "result"}), "ab", frozenset({"pipeline"})),
    "inspect": WorkMode("inspect", "数値を調べる", frozenset({"result", "display", "variables"}), "display", frozenset({"pipeline"})),
    "code": WorkMode("code", "コードにする", frozenset({"program", "result"}), "program"),
}


def _flags_for(mode_id):
    mode = _mode(mode_id)
    return {panel: {"visible": panel in mode.visible, "collapsed": panel in mode.collapsed}
            for panel in PANELS}


@dataclass
class LayoutState:
    mode: str = "build"
    panels: dict = field(default_factory=lambda: _flags_for("build"))
    overrides: dict = field(default_factory=dict)
    focus_image: bool = False
    previous: dict | None = None


def _mode(mode_id):
    if mode_id not in MODES:
        raise ValueError("unknown work mode: %r" % mode_id)
    return MODES[mode_id]


def _panel(panel_id):
    if panel_id not in PANELS:
        raise ValueError("unknown panel id: %r" % panel_id)
    return panel_id


def apply_mode(state, mode_id):
    _mode(mode_id)
    flags = _flags_for(mode_id)
    for panel, values in state.overrides.get(mode_id, {}).items():
        _panel(panel)
        flags[panel].update(values)
    return replace(state, mode=mode_id, panels=flags, focus_image=False, previous=None)


def toggle_focus_image(state):
    if state.focus_image:
        return replace(state, panels={k: dict(v) for k, v in state.previous.items()},
                       focus_image=False, previous=None)
    previous = {k: dict(v) for k, v in state.panels.items()}
    flags = {panel: {"visible": panel == "result", "collapsed": False} for panel in PANELS}
    return replace(state, panels=flags, focus_image=True, previous=previous)


def set_override(state, panel, visible=None, collapsed=None):
    _panel(panel)
    if visible is None and collapsed is None:
        return state
    overrides = {mode: {key: dict(value) for key, value in values.items()}
                 for mode, values in state.overrides.items()}
    values = overrides.setdefault(state.mode, {}).setdefault(panel, {})
    if visible is not None:
        values["visible"] = bool(visible)
    if collapsed is not None:
        values["collapsed"] = bool(collapsed)
    answer = replace(state, overrides=overrides)
    return apply_mode(answer, state.mode)


def find_panels(query):
    needle = str(query).strip().casefold()
    if not needle:
        return list(PANELS)
    return [panel for panel, info in PANELS.items()
            if any(needle in text.casefold() for text in [panel, info["name"], *info["aliases"]])]


def _to_json(state):
    data = {"mode": state.mode, "panels": state.panels, "overrides": state.overrides,
            "focus_image": state.focus_image, "previous": state.previous}
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def _from_json(value):
    try:
        data = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid layout JSON") from exc
    mode = data.get("mode", "build")
    _mode(mode)
    overrides = data.get("overrides", {})
    for override_mode, values in overrides.items():
        _mode(override_mode)
        for panel in values:
            _panel(panel)
    state = LayoutState(mode=mode, overrides=overrides)
    state = apply_mode(state, mode)
    supplied = data.get("panels", {})
    for panel, values in supplied.items():
        _panel(panel)
        state.panels[panel].update({key: bool(val) for key, val in values.items()
                                    if key in {"visible", "collapsed"}})
    previous = data.get("previous")
    if previous is not None:
        for panel in previous:
            _panel(panel)
    return replace(state, focus_image=bool(data.get("focus_image", False)), previous=previous)


# Keep the deliberately small public API names without making generic ``to_json`` /
# ``from_json`` look like facade operations to the reachability name heuristic.
to_json = partial(_to_json)
from_json = partial(_from_json)
