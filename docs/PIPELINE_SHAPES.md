# Typed DAG execution

`fullseye_plan` returns an executable DAG. Bind each `have:<sort>` reference to a typed handle, validate the DAG, then pass the same stages and bindings to `fullseye_pipeline`. The operator graph is the sole source of type and topology facts.
