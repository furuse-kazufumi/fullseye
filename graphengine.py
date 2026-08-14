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
    def add(self, node_id: str, op: str, inputs, a: float = 0.5, b: float = 0.5):
        """Add a node ``op`` consuming ``inputs`` (node ids and/or external input
        names, e.g. ``"$in"``). A single-input REGISTRY op uses ``inputs[0]``; a
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
        """Return a list of problem dicts (unknown op / arity mismatch); empty = OK.
        Raises on structural errors (cycle / dangling ref) via topological_order."""
        self.topological_order()
        RT, nary = self._tables()
        probs = []
        for n, spec in self.nodes.items():
            op, k = spec["op"], len(spec["inputs"])
            if op in nary:
                if k != nary[op].arity:
                    probs.append({"node": n, "severity": "error",
                                  "msg": "op %r needs %d inputs, got %d" % (op, nary[op].arity, k)})
            elif op in RT:
                if k != 1:
                    probs.append({"node": n, "severity": "error",
                                  "msg": "single-input op %r got %d inputs" % (op, k)})
            else:
                probs.append({"node": n, "severity": "error", "msg": "unknown op %r" % op})
        return probs

    # -- execution ----------------------------------------------------------- #
    def _eval(self, RT, nary, op, args, a, b):
        if op in nary:
            return nary[op].fn(list(args), a, b)
        if op in RT:
            return RT[op](args[0], a, b)
        raise ValueError("unknown op %r" % op)

    def run(self, inputs, terminal: str | None = None):
        """Evaluate the graph. ``inputs`` is a single array (bound to ``"$in"``) or a
        ``{name: array}`` dict. Returns a ``{node_id: array}`` cache, or — when
        *terminal* is given — that single node's output. Raises ``ValueError`` if a
        required external input is missing."""
        import numpy as np
        RT, nary = self._tables()
        if isinstance(inputs, dict):
            cache = {str(k): np.asarray(v) for k, v in inputs.items()}
        else:
            cache = {"$in": np.asarray(inputs)}
        missing = self._external() - set(cache)
        if missing:
            raise ValueError("missing external input(s): %s" % ", ".join(sorted(missing)))
        for nid in self.topological_order():
            spec = self.nodes[nid]
            args = [cache[i] for i in spec["inputs"]]
            cache[nid] = self._eval(RT, nary, spec["op"], args, spec["a"], spec["b"])
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
        """Emit a standalone Python function reproducing the graph via ``fullseye``."""
        lines = ["import fullseye, imgops_nary",
                 "_NARY = {o.name: o for o in imgops_nary.build_nary()}", "",
                 "def %s(**inputs):" % (self.name if self.name.isidentifier() else "graph"),
                 "    v = dict(inputs)"]
        for nid in self.topological_order():
            s = self.nodes[nid]
            args = "[%s]" % ", ".join("v[%r]" % i for i in s["inputs"])
            lines.append(
                "    v[%r] = (_NARY[%r].fn(%s, %s, %s) if %r in _NARY "
                "else fullseye.RT[%r](v[%r], %s, %s))"
                % (nid, s["op"], args, s["a"], s["b"], s["op"],
                   s["op"], s["inputs"][0], s["a"], s["b"]))
        lines.append("    return v")
        return "\n".join(lines)
