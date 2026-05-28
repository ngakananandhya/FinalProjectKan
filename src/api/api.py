from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import recommend_api, baseline, df_final
from custom_recipe import recommend_custom_api
from search import search_recipe, json_recipes
from input_parser import normalize_query, normalize_region

app = FastAPI(title="Culinary Bridge AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# REQUEST MODELS
# =============================================================================
class NamaRequest(BaseModel):
    query: str

class WilayahRequest(BaseModel):
    region: str

class AdaptasiRequest(BaseModel):
    recipe_name: str
    target_region: str

class CustomRequest(BaseModel):
    recipe_name: str
    ingredients: str
    target_region: str

class DetailRequest(BaseModel):
    title: str

# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/regions")
def get_regions():
    return {"regions": sorted(baseline.keys())}

@app.post("/api/cari/nama")
def cari_nama(req: NamaRequest):
    results = search_recipe(req.query)
    if not results:
        return {"found": False, "results": []}
    return {
        "found": True,
        "results": [
            {
                "title":    r["title_original"],
                "region":   r.get("region") or "—",
                "category": r.get("category") or "—",
                "id":       r["recipe_id"],
            }
            for r in results
        ]
    }

@app.post("/api/cari/wilayah")
def cari_wilayah(req: WilayahRequest):
    from input_parser import normalize_query, normalize_region
    query = normalize_query(req.region).lower()

    results = []
    for recipe in json_recipes:
        region = recipe.get("region", "")
        if not region:
            continue
        if normalize_query(region).lower() == query:
            results.append({
                "title":  recipe["title_original"],
                "region": recipe.get("region") or "—",
                "id":     recipe["recipe_id"],
            })

    if not results:
        return {"found": False, "region": req.region, "results": []}
    return {"found": True, "region": req.region, "results": results}

@app.post("/api/cari/detail")
def cari_detail(req: NamaRequest):
    results = search_recipe(req.query)
    if not results:
        return {"found": False}
    
    import io
    from contextlib import redirect_stdout
    from search import display_recipe

    r = results[0]
    f = io.StringIO()
    with redirect_stdout(f):
        display_recipe(r)
    
    return {
        "found": True,
        "output": f.getvalue(),
        "title": r["title_original"],
        "region": r.get("region") or "—",
    }

@app.post("/api/adaptasi")
def adaptasi(req: AdaptasiRequest):
    return recommend_api(
        recipe_name=req.recipe_name,
        target_region=req.target_region
    )

@app.post("/api/custom")
def custom(req: CustomRequest):
    return recommend_custom_api(
        recipe_name=req.recipe_name,
        raw_ingredients=req.ingredients,
        target_region=req.target_region
    )

