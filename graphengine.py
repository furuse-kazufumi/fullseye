"""DAG pipeline runtime for Fullseye operators (facade layer).

:class:`~engine.FullseyeEngine` runs a *linear* op chain; ``FullseyeGraph`` runs a
directed acyclic graph, so a pipeline can **branch** (one result feeding several
downstream ops) and **merge** (an n-ary op combining two branches, e.g. a
difference of a raw and a blurred image, or a stereo pair through ``add_image`` /
``abs_diff_image``). It composes the same operators the linear engine and the
evolution registry use (single-input REGISTRY ops via ``RT`` + the 2-input n-ary
ops in :mod:`imgops_nary`), so it stays a pure runtime over the existing catalog and
never touches the evolution genome.

    g = FullseyeGraph()
    g.add("blur", "gaussian", ["$in"], a=0.6)
    g.add("edge", "sobel_amp", ["blur"])
    g.add("resid", "abs_diff_image", ["$in", "blur"])   # merge: 2 inputs
    out = g.run(frame)                 # {node_id: array}; g.run(frame, terminal="edge") -> one array

External inputs are named (default ``"$in"``); pass a single array for the default
input or a ``{name: array}`` dict for several (stereo, before/after, ...).
"""
from __future__ import annotations


class FullseyeGraph:
    """A directed-acyclic graph of Fullseye operators (branch + merge)."""

    def __init__(self, name: str = "graph"):
        self.name = str(name)
        self.nodes: dict = {}          # id -> {op, inputs, a, b}
        self._order: list = []         # insertion order (tie-break for topo sort)

    # -- construction -------------------------------------------------------- #
    def add(self, node_id: str, op: str, inputs="$in", a: float = 0.5, b: float = 0.5):
        """Add a node ``op`` consuming ``inputs`` (node ids and/or external input
        names, e.g. ``"$in"``; default ``"$in"`` = the array handed to :meth:`run`, so a
        first single-input node is ``add("n1", "gaussian")``). A single-input REGISTRY op uses ``inputs[0]``; a
        2-input :mod:`imgops_nary` op (``add_image``/``abs_diff_image``/``union2``…)
        consumes all inputs. Returns self for chaining."""
        node_id = str(node_id)
        if node_id in self.nodes:
            raise ValueError("duplicate node id %r" % node_id)
        if node_id.startswith("$"):
            raise ValueError("node id may not start with '$' (reserved for inputs)")
        ins = [str(i) for i in (inputs if isinstance(inputs, (list, tuple)) else [inputs])]
        if not ins:
            raise ValueError("node %r has no inputs" % node_id)
        self.nodes[node_id] = {"op": str(op), "inputs": ins,
                               "a": float(a), "b": float(b)}
        self._order.append(node_id)
        return self

    # -- op tables (lazy) ---------------------------------------------------- #
    @staticmethod
    def _tables():
        import api  # facade RT + n-ary catalog
        nary = {o.name: o for o in __import__("imgops_nary").build_nary()}
        return api.RT, nary

    # -- validation / ordering ---------------------------------------------- #
    def _external(self):
        """Names referenced as inputs but not produced by a node (external inputs)."""
        produced = set(self.nodes)
        refs = {i for n in self.nodes.values() for i in n["inputs"]}
        return refs - produced

    def topological_order(self) -> list:
        """Node ids in a valid evaluation order (raises on a cycle or a dangling
        reference to a non-existent, non-external input)."""
        produced = set(self.nodes)
        ext = self._external()
        indeg = {n: 0 for n in self.nodes}
        children: dict = {n: [] for n in self.nodes}
        for n, spec in self.nodes.items():
            for i in spec["inputs"]:
                if i in produced:
                    indeg[n] += 1
                    children[i].append(n)
                elif i not in ext:                       # cannot happen, but explicit
                    raise ValueError("node %r references unknown input %r" % (n, i))
        ready = [n for n in self._order if indeg[n] == 0]
        order, seen = [], 0
        while ready:
            n = ready.pop(0)
            order.append(n)
            seen += 1
            for c in children[n]:
                indeg[c] -= 1
                if indeg[c] == 0:
                    ready.append(c)
        if seen != len(self.nodes):
            raise ValueError("graph has a cycle")
        return order

    def validate(self) -> list:
        """Return a list of problem dicts (unknown op / arity mismatch / sort mismatch /
        non-finite knob); empty = OK. Raises on structural errors (cycle / dangling ref)
        via topological_order.

        Sorts are threaded through the graph in topological order the same way
        ``FullseyeEngine`` threads a chain (``engine._thread_sort``: an op whose
        ``out_sort`` is ``"any"`` keeps the incoming sort). External inputs carry no
        declared sort, so the first op reading one is not checked; every edge between
        two nodes is. 2026-10-11: there was no sort check at all, so
        ``otsu -> blob_count -> vol_gaussian`` validated clean and ran."""
        import math

        import api
        import engine
        order = self.topological_order()
        RT, nary = self._tables()
        probs = []
        sorts: dict = {}                     # node id -> sort it outputs (None = unknown)
        for n in order:
            spec = self.nodes[n]
            op, k = spec["op"], len(spec["inputs"])
            for label in ("a", "b"):
                if not math.isfinite(spec[label]):
                    probs.append({"node": n, "severity": "error",
                                  "msg": "knob %s of %r is non-finite (%r)" % (label, op, spec[label])})
            in_sorts = [sorts.get(i) for i in spec["inputs"]]
            if op in nary:
                nop = nary[op]
                if k != nop.arity:
                    probs.append({"node": n, "severity": "error",
                                  "msg": "op %r needs %d inputs, got %d" % (op, nop.arity, k)})
                    sorts[n] = None
                    continue
                for jj, (got, want) in enumerate(zip(in_sorts, nop.in_sorts)):
                    if got is not None and not engine._compatible(got, want):
                        probs.append({"node": n, "severity": "error", "kind": "sort_mismatch",
                                      "msg": "input %d of %r (%s) is %r but the op takes %r"
                                             % (jj, op, spec["inputs"][jj], got, want)})
                out = nop.out_sort
                sorts[n] = in_sorts[0] if (out == "any" and in_sorts[0] is not None) else out
            elif op in RT:
                if k != 1:
                    probs.append({"node": n, "severity": "error",
                                  "msg": "single-input op %r got %d inputs" % (op, k)})
                o = api.find_op(op)
                got = in_sorts[0] if in_sorts else None
                if o is None:
                    sorts[n] = None
                    continue
                if got is not None and not engine._compatible(got, o.in_sort):
                    probs.append({"node": n, "severity": "error", "kind": "sort_mismatch",
                                  "msg": "op %r takes %r but its input %r outputs %r"
                                         % (op, o.in_sort, spec["inputs"][0], got)})
                sorts[n] = engine._thread_sort(got, o)
            else:
                probs.append({"node": n, "severity": "error", "msg": "unknown op %r" % op})
                sorts[n] = None
        return probs

    # -- execution ----------------------------------------------------------- #
    def _eval(self, nary, op, args, a, b, coerce, on_error):
        """One node through the facade's runner (``api.apply``): dtype contract (uint8
        ``/255``), knob check (clamped + recorded, or refused under ``on_error="raise"``)
        and the fallback guard -- the same path ``fullseye.apply`` / ``run_pipeline`` take.
        2026-10-11: nodes called ``RT`` / ``NaryOp.fn`` directly, so a uint8 frame gave a
        different answer than ``fullseye.apply`` and a knob of 7 ran unchecked."""
        import api
        if op in nary:
            return api.apply(list(args), op, a, b, coerce=coerce, on_error=on_error)
        return api.apply(args[0], op, a, b, coerce=coerce, on_error=on_error)

    def run(self, inputs, terminal: str | None = None, on_error: str | None = None):
        """Evaluate the graph. ``inputs`` is a single array (bound to ``"$in"``) or a
        ``{name: array}`` dict. Returns a ``{node_id: array}`` cache, or -- when
        *terminal* is given -- that single node's output. Raises ``ValueError`` if a
        required external input is missing. An empty graph returns the inputs cache
        unchanged (``{"$in": array}``) -- nothing ran, nothing was invented.

        :meth:`validate` runs first: any error (unknown op, wrong arity, sort mismatch,
        non-finite knob) raises ``ValueError`` **before any node runs**. Each node then
        runs through ``fullseye.apply`` (``on_error`` as there; ``None`` reads
        ``FULLSEYE_ON_ERROR``); like ``run_pipeline``, only nodes that read external
        inputs coerce them (``api._coerce_input``)."""
        import numpy as np
        _, nary = self._tables()
        if isinstance(inputs, dict):
            cache = {str(k): np.asarray(v) for k, v in inputs.items()}
        else:
            cache = {"$in": np.asarray(inputs)}
        missing = self._external() - set(cache)
        if missing:
            raise ValueError("missing external input(s): %s" % ", ".join(sorted(missing)))
        errors = [p for p in self.validate() if p["severity"] == "error"]
        if errors:
            raise ValueError("graph %r refused before running: %s"
                             % (self.name, "; ".join("%s: %s" % (p["node"], p["msg"]) for p in errors)))
        ext = self._external()
        for nid in self.topological_order():
            spec = self.nodes[nid]
            args = [cache[i] for i in spec["inputs"]]
            coerce = all(i in ext for i in spec["inputs"])
            cache[nid] = self._eval(nary, spec["op"], args, spec["a"], spec["b"], coerce, on_error)
        if terminal is not None:
            if terminal not in cache:
                raise ValueError("no such node %r" % terminal)
            return cache[terminal]
        return cache

    # -- serialization / codegen -------------------------------------------- #
    def to_dict(self) -> dict:
        return {"fullseye_graph": 1, "name": self.name,
                "nodes": [{"id": n, **s} for n, s in
                          ((n, self.nodes[n]) for n in self._order)]}

    @classmethod
    def from_dict(cls, d: dict) -> "FullseyeGraph":
        g = cls(d.get("name", "graph"))
        for nd in d["nodes"]:
            g.add(nd["id"], nd["op"], nd["inputs"], nd.get("a", 0.5), nd.get("b", 0.5))
        return g

    def to_python(self) -> str:
        """Emit a standalone Python function reproducing the graph via ``fullseye.apply``
        (the same runner :meth:`run` uses). The function name goes through
        ``engine._py_ident``, so a graph named ``class`` / ``1x`` still compiles."""
        import engine
        _, nary = self._tables()
        ext = self._external()
        lines = ["import fullseye", "",
                 "def %s(**inputs):" % engine._py_ident(self.name),
                 "    v = dict(inputs)"]
        for nid in self.topological_order():
            s = self.nodes[nid]
            if s["op"] in nary:
                arg = "[%s]" % ", ".join("v[%r]" % i for i in s["inputs"])
            else:
                arg = "v[%r]" % s["inputs"][0]
            coerce = all(i in ext for i in s["inputs"])
            lines.append("    v[%r] = fullseye.apply(%s, %r, %r, %r, coerce=%r)"
                         % (nid, arg, s["op"], s["a"], s["b"], coerce))
        lines.append("    return v")
        return "\n".join(lines)
