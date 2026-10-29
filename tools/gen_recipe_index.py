"""Build the MCP recipe index solely from existing, human-written examples."""
from __future__ import annotations
import ast, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def _line_numbers(path):
    tree=ast.parse(path.read_text(encoding="utf-8"))
    value=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="RECIPES" for t in n.targets))
    return {next(v.value for k,v in zip(n.keys,n.values) if isinstance(k,ast.Constant) and k.value=="name"):n.lineno for n in value.elts}

def build():
    sys.path.insert(0,str(ROOT)); import api, recipes
    rows=json.loads((ROOT/"fullseye/data/OP_SEARCH.json").read_text(encoding="utf-8"))["ops"]
    by_name={r["n"]:r for r in rows}; lines=_line_numbers(ROOT/"recipes.py"); out=[]
    langs=("ja","en","zh","tw","ko","de","hi")
    for r in recipes.RECIPES:
        sort="image"; stages=[]; terms={lang:[] for lang in langs}
        for name,a,b in r["stages"]:
            op=api.find_op(name)
            if op is None or op.in_sort not in (sort,"any"):
                raise RuntimeError(f"invalid recipe {r['name']}: {name} after {sort}")
            sort=op.out_sort; stages.append({"op":name,"a":a,"b":b})
            summaries=by_name.get(name,{}).get("s",{})
            for lang in langs:
                text=summaries.get(lang) or summaries.get("en") or summaries.get("ja")
                if text: terms[lang].append(text)
        out.append({"name":r["name"],"task":r["task"],"input_sort":"image","output_sort":sort,
                    "stages":stages,"when":r["note"],"image":r.get("image"),
                    "source":{"path":"recipes.py","line":lines[r["name"]]},
                    "index_text":{lang:" ".join([r["name"],r["task"],r["note"],*texts]) for lang,texts in terms.items()}})
    poc=sorted((ROOT/"examples").glob("poc_*.py")); gate=json.loads((ROOT/"studio_lite/gates/recipes_gate.json").read_text(encoding="utf-8")); docs=list((ROOT/"docs").rglob("*.md"))
    return {"schema_version":1,"recipes":out,"inventory":[
      {"source":"recipes.py RECIPES","found":len(recipes.RECIPES),"included":len(out),"excluded":0,"reason":None},
      {"source":"examples/poc_*.py","found":len(poc),"included":0,"excluded":len(poc),"reason":"PoC programs are arbitrary Python; a linear MCP pipeline cannot be extracted statically without guessing."},
      {"source":"studio_lite/gates/recipes_gate.json","found":len(gate.get("recipes",[])),"included":0,"excluded":len(gate.get("recipes",[])),"reason":"Execution gates duplicate selected built-in recipes and are not distinct examples."},
      {"source":"docs/**/*.md","found":len(docs),"included":0,"excluded":len(docs),"reason":"Documentation contains prose and snippets, not a statically unambiguous inventory of MCP stages."}]}

if __name__=="__main__":
    target=ROOT/"fullseye/data/RECIPE_INDEX.json"; target.write_text(json.dumps(build(),ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n"); print(target)
