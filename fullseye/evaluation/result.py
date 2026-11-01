# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Structured PoC gate results with byte-compatible legacy printing.

The base implementation is the typed accumulator used by
``examples/poc_simcal_telecentric.py`` (lines 111--116 before P0-A): append every
gate, print it immediately, and defer the exit decision.  The other local gate
forms differed only in status words, indentation, argument order, and whether they
kept names or failures.  :class:`GateStyle` makes those differences explicit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, MutableSequence, Sequence


@dataclass(frozen=True)
class GateResult:
    """One measured acceptance decision.

    ``assert`` remains appropriate for program invariants.  Measurement acceptance
    belongs here so all failures can be reported after figures and tables are saved.
    """

    name: str
    passed: bool
    measured: Any = None
    expected: Any = None
    tolerance: Any = None
    relation: str = ""
    detail: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("GateResult.name must be a non-empty string")
        if not isinstance(self.passed, bool):
            raise TypeError("GateResult.passed must be bool")
        if not isinstance(self.relation, str) or not isinstance(self.detail, str):
            raise TypeError("GateResult.relation and detail must be strings")

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "measured": self.measured,
            "expected": self.expected,
            "tolerance": self.tolerance,
            "relation": self.relation,
            "detail": self.detail,
        }


@dataclass
class CaseResult:
    """All evaluation outputs for one PoC case."""

    case: str
    gates: list[GateResult] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    artifacts: list[Any] = field(default_factory=list)
    seed: int | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.case, str) or not self.case:
            raise ValueError("CaseResult.case must be a non-empty string")
        self.gates = list(self.gates)
        if not all(isinstance(gate, GateResult) for gate in self.gates):
            raise TypeError("CaseResult.gates must contain GateResult values")
        self.metrics = dict(self.metrics)
        self.artifacts = list(self.artifacts)
        self.provenance = dict(self.provenance)

    @property
    def passed(self) -> bool:
        """True only when at least one gate exists and every gate passes."""
        return bool(self.gates) and all(gate.passed for gate in self.gates)

    @property
    def failures(self) -> list[GateResult]:
        return [gate for gate in self.gates if not gate.passed]

    def extend(self, gates: Iterable[GateResult]) -> None:
        values = list(gates)
        if not all(isinstance(gate, GateResult) for gate in values):
            raise TypeError("CaseResult.extend expects GateResult values")
        self.gates.extend(values)


@dataclass(frozen=True)
class GateStyle:
    """Exact rendering differences retained from local PoC gate functions."""

    indent: str = "   "
    pass_word: str = "ok"
    fail_word: str = "NG"
    detail_prefix: str = " — "
    always_detail_prefix: bool = False

    def render(self, name: str, passed: bool, detail: str) -> str:
        word = self.pass_word if passed else self.fail_word
        suffix = self.detail_prefix + detail if detail or self.always_detail_prefix else ""
        return f"{self.indent}[{word}] {name}{suffix}"


class GateAdapter:
    """Collect :class:`GateResult` values while preserving legacy stdout exactly.

    ``all_names`` and ``failed_names`` accept the existing PoC lists.  This is the
    selected ``poc_simcal_telecentric`` accumulator with its local formatting moved
    into :class:`GateStyle`; no exit text or exit policy is invented here.
    """

    def __init__(
        self,
        *,
        style: GateStyle = GateStyle(),
        printer: Callable[[str], None] | None = print,
        all_names: MutableSequence[str] | None = None,
        failed_names: MutableSequence[str] | None = None,
        results: MutableSequence[GateResult] | None = None,
    ) -> None:
        self.style = style
        self.printer = printer
        self.all_names = all_names
        self.failed_names = failed_names
        self.results: MutableSequence[GateResult] = results if results is not None else []

    def __call__(
        self,
        name: str,
        passed: bool,
        detail: str = "",
        *,
        measured: Any = None,
        expected: Any = None,
        tolerance: Any = None,
        relation: str = "",
    ) -> GateResult:
        result = GateResult(
            name=name,
            passed=bool(passed),
            measured=measured,
            expected=expected,
            tolerance=tolerance,
            relation=relation,
            detail=detail,
        )
        self.results.append(result)
        if self.all_names is not None:
            self.all_names.append(name)
        if not result.passed and self.failed_names is not None:
            self.failed_names.append(name)
        if self.printer is not None:
            self.printer(self.style.render(name, result.passed, detail))
        return result

    @property
    def failures(self) -> list[GateResult]:
        return [gate for gate in self.results if not gate.passed]

    def case_result(
        self,
        case: str,
        *,
        metrics: Mapping[str, Any] | None = None,
        artifacts: Sequence[Any] = (),
        seed: int | None = None,
        provenance: Mapping[str, Any] | None = None,
    ) -> CaseResult:
        return CaseResult(
            case=case,
            gates=list(self.results),
            metrics=dict(metrics or {}),
            artifacts=list(artifacts),
            seed=seed,
            provenance=dict(provenance or {}),
        )
