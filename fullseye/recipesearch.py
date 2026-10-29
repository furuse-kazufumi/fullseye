"""Retrieve existing human-authored pipelines; never synthesize recipe stages."""
import json, math
from collections import Counter
from importlib.resources import files
from .opsearch import detect_lang, tokenize

def load_recipe_index():
    data=json.loads((files("fullseye")/"data"/"RECIPE_INDEX.json").read_text(encoding="utf-8"))
    if not data.get("recipes"): raise ValueError("RECIPE_INDEX.json is empty")
    return data

def find_recipes(query,*,limit=2,in_sort=None,out_sort=None,lang=None):
    recipes=load_recipe_index()["recipes"]; lang=lang or detect_lang(query); q=set(tokenize(query))
    docs=[Counter(tokenize(r["index_text"].get(lang) or r["index_text"]["en"])) for r in recipes]
    df=Counter(t for doc in docs for t in doc); ranked=[]
    for recipe,doc in zip(recipes,docs):
        if in_sort and recipe["input_sort"]!=in_sort: continue
        if out_sort and recipe["output_sort"]!=out_sort: continue
        score=sum((1+math.log(doc[t]))*math.log((len(docs)+1)/(df[t]+.5)) for t in q if doc[t])
        if score:
            public={k:v for k,v in recipe.items() if k!="index_text"}; public["score"]=round(score,3); ranked.append((-score,recipe["name"],public))
    ranked.sort(); return [r for _,_,r in ranked[:limit]]
