import json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_every_indexed_recipe_validates_for_mcp():
    from fullseye.mcp.catalog import Catalog
    from fullseye.mcp.server import validate_pipeline
    data=json.loads((ROOT/"fullseye/data/RECIPE_INDEX.json").read_text(encoding="utf-8"))
    cat=Catalog.load()
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
    base=subprocess.run(["git","show","e1c87bff11:recipes.py"],cwd=ROOT,capture_output=True,check=True,text=True,encoding="utf-8").stdout.replace("\r\n","\n")
    assert current==base, "This change must index existing recipes, not edit their source."

def test_committed_recall_report_matches_measurement():
    report=json.loads((ROOT/"docs/recipe_retrieval_report.json").read_text(encoding="utf-8"))
    assert report["recall_at_2"]==sum(r["hit"] for r in report["queries"])/len(report["queries"])
