import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_every_indexed_recipe_validates_for_mcp():
    from fullseye.mcp.catalog import Catalog
    from fullseye.mcp.server import validate_pipeline
    data=json.loads((ROOT/"fullseye/data/RECIPE_INDEX.json").read_text(encoding="utf-8"))
    cat=Catalog.load()
    assert len(data["recipes"]) >= 25, "the recipe index shrank (or is empty) — every recipe must stay indexed"
    for recipe in data["recipes"]:
        result=validate_pipeline(recipe["stages"],recipe["input_sort"],cat)
        assert result["valid"], (recipe["name"],result)

def test_find_ops_returns_at_most_two_ready_pipelines():
    from fullseye.mcp.catalog import Catalog
    from fullseye.mcp.server import call_tool
    result=call_tool("fullseye_find_ops",{"query":"count holes in backlit plate"},Catalog.load())
    recipes=result["structuredContent"]["recipes"]
    assert 0 < len(recipes) <= 2
    assert all(r["stages"] and r["source"]["path"] for r in recipes)
    assert "recipe:" in result["content"][0]["text"]

def test_recipe_sources_are_unchanged_from_feature_base():
    current=(ROOT/"recipes.py").read_text(encoding="utf-8").replace("\r\n","\n")
    # sha256 of recipes.py at the feature base e1c87bff11 (LF). A pinned digest, not `git show`: CI clones are shallow.
    assert hashlib.sha256(current.encode("utf-8")).hexdigest()=="b6fcb605c61067e8684e1566910bc82f787af05ee7d5db7a52642d7ecfaca802", "This change must index existing recipes, not edit their source."

def test_committed_recall_report_matches_measurement():
    report=json.loads((ROOT/"docs/recipe_retrieval_report.json").read_text(encoding="utf-8"))
    assert report["recall_at_2"]==sum(r["hit"] for r in report["queries"])/len(report["queries"])
