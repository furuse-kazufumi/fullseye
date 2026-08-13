"""Sample-pipeline library: every recipe resolves, is sort-coherent, and runs."""
import numpy as np

import api
import recipes


def _img(n=48):
    y, x = np.mgrid[0:n, 0:n]
    return np.clip(0.5 + 0.3 * np.sin(x / 7.0) * np.cos(y / 9.0), 0, 1)


def test_all_recipes_valid():
    assert recipes.validate() == []          # every op exists and sorts chain
    assert len(recipes.RECIPES) >= 15


def test_lookup_helpers():
    nm = recipes.names()[0]
    assert recipes.get(nm)["name"] == nm
    assert isinstance(recipes.stages(nm), list)
    assert recipes.get("no such recipe") is None


def test_every_recipe_runs_on_an_image():
    f = _img()
    for r in recipes.RECIPES:
        out = api.run_pipeline(f, recipes.stages(r["name"]))
        # image/region -> array; count/measure -> float
        assert out is not None, r["name"]
        if r["task"] == "measure":
            assert isinstance(out, float)
