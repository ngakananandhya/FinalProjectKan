import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
from input_parser import (
    normalize_query,
    normalize_region,
    fuzzy_match_recipe,
    fuzzy_match_region,
    normalize_qty_display,
    UNIT_TO_GRAM,
    UNIT_BAHAN_TO_GRAM,
    INGREDIENT_UNIT_OVERRIDE
)

# Initialize
tfidf = TfidfVectorizer()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

df_recipes = pd.read_csv(os.path.join(BASE_DIR, 'data', 'df_recipes.csv'))
df_ing = pd.read_csv(os.path.join(BASE_DIR, 'data', 'df_ingredient_recipes.csv'))

# print("DF RECIPES COLUMNS:", df_recipes.columns)
# print("DF ING COLUMNS:", df_ing.columns)

# Group ingredients per recipe
df_grouped = df_ing.groupby('recipe_id')['ingredient_normalized_name'] \
    .apply(lambda x: ' '.join(x.astype(str))) \
    .reset_index()

# Merge ke recipes
df_final = df_recipes.merge(df_grouped, left_on='id', right_on='recipe_id')

# Ambil kolom yang kita butuh
df_final = df_final[['id', 'title_original', 'region_clean', 'ingredient_normalized_name']]

# Rename biar clean
df_final.columns = ['id', 'recipe_name', 'region', 'ingredients']


df_final['recipe_name_normalized'] = df_final['recipe_name'].apply(
    lambda x: normalize_query(x).upper()
)

# Fit & transform
tfidf_matrix = tfidf.fit_transform(df_final['ingredients'])

# print("Shape TF-IDF:", tfidf_matrix.shape)

# COSINE SIMILARITY
cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
# print("Cosine sim shape:", cosine_sim.shape)

# INI PERLU DIUPGRADE STANDARISASINYA, CARI JURNAL!
taste_map = {
    # PEDAS
    "cabai":            {"pedas": 3,   "asam": 0.5},
    "cabai rawit":      {"pedas": 4,   "asam": 0.5},
    "cabai merah":      {"pedas": 2,   "manis": 0.5},
    "cabai hijau":      {"pedas": 2,   "asam": 0.5},
    "lada":             {"pedas": 2,   "gurih": 0.5},
    "lada halus":       {"pedas": 2,   "gurih": 0.5},
    "lada putih":       {"pedas": 1.5, "gurih": 0.5},
    "jahe":             {"pedas": 1.5, "gurih": 0.5, "asam": 0.3},
    "kencur":           {"pedas": 0.5, "gurih": 1,   "asam": 0.3},
    "lengkuas":         {"pedas": 0.5, "gurih": 1,   "asam": 0.3},

    # MANIS
    "gula":             {"manis": 3},
    "gula merah":       {"manis": 4,   "gurih": 0.5},
    "gula pasir":       {"manis": 3},
    "gula jawa":        {"manis": 4,   "gurih": 0.5},
    "gula halus":       {"manis": 3},
    "kecap":            {"manis": 2,   "gurih": 1,   "asam": 0.3},
    "vanili":           {"manis": 1.5},
    "daun pandan":      {"manis": 1,   "gurih": 0.3},
    "kelapa muda":      {"manis": 1.5, "gurih": 0.5},

    # GURIH
    "santan":           {"gurih": 3,   "manis": 0.5},
    "santan kental":    {"gurih": 3.5, "manis": 0.5},
    "kelapa":           {"gurih": 2,   "manis": 0.5},
    "kelapa setengah tua": {"gurih": 2.5, "manis": 0.3},
    "bawang merah":     {"gurih": 1,   "manis": 0.3, "pedas": 0.5},
    "bawang putih":     {"gurih": 1,   "pedas": 0.5},
    "kemiri":           {"gurih": 2.5, "pedas": 0.3},
    "terasi":           {"gurih": 3,    "asam": 0.3},
    "kunyit":           {"gurih": 1,   "pedas": 0.3},
    "ketumbar":         {"gurih": 1.5, "pedas": 0.3},
    "jintan":           {"gurih": 1.5, "pedas": 0.5},
    "serai":            {"gurih": 0.5, "asam": 0.3},
    "daun salam":       {"gurih": 0.5, "asam": 0.3},
    "daun jeruk purut": {"gurih": 0.5, "asam": 0.5},
    "daun bawang":      {"gurih": 1,   "pedas": 0.3},
    "seledri":          {"gurih": 1,   "pedas": 0.3},
    "minyak kelapa":    {"gurih": 1,   "manis": 0.3},
    "mentega":          {"gurih": 1.5, "manis": 0.5},
    "margarin":         {"gurih": 1,   "manis": 0.3},
    "telur ayam":       {"gurih": 1.5, "manis": 0.3},
    "telur":            {"gurih": 1.5, "manis": 0.3},
    "kuning telur":     {"gurih": 2,   "manis": 0.5},
    "daging":           {"gurih": 2,   "asam": 0.3},
    "ayam":             {"gurih": 2,   "asam": 0.3},
    "tempe":            {"gurih": 1.5, "asam": 0.5},
    "tahu":             {"gurih": 1,   "asam": 0.3},

    # ASAM
    "asam jawa":        {"asam": 4,    "manis": 0.5},
    "asam":             {"asam": 3.5,  "gurih": 0.3},
    "belimbing":        {"asam": 3,    "manis": 0.5},
    "jeruk":            {"asam": 2,    "manis": 0.3},
    "jeruk nipis":      {"asam": 3,    "pedas": 0.3, "manis": 0.3},
    "cuka":             {"asam": 3,    "pedas": 0.3},
    "tomat":            {"asam": 2,    "manis": 0.5, "gurih": 0.3},
}


def tokenize_ingredients(ingredients_text):
    """
    Tokenisasi ingredients string dengan longest match.
    Prioritaskan bahan multi-kata sebelum single-kata.
    Return: list of ingredient names yang ada di taste_map.
    """
    # Urutkan taste_map keys dari terpanjang ke terpendek
    sorted_keys = sorted(taste_map.keys(), key=lambda x: len(x), reverse=True)

    text   = ingredients_text.lower().strip()
    result = []

    while text:
        text = text.strip()
        if not text:
            break

        matched = False
        for key in sorted_keys:
            if text.startswith(key):
                result.append(key)
                text = text[len(key):]
                matched = True
                break

        if not matched:
            # Tidak ada match — skip satu kata
            parts = text.split(' ', 1)
            text  = parts[1] if len(parts) > 1 else ''

    return result

def calculate_taste(ingredients_text, recipe_id=None):
    score        = {"pedas": 0, "manis": 0, "gurih": 0, "asam": 0}
    total_weight = {"pedas": 0, "manis": 0, "gurih": 0, "asam": 0}

    ingredients = tokenize_ingredients(ingredients_text)

    for ing in ingredients:
        # Ambil quantity weight
        qty_weight = 1.0
        if recipe_id is not None:
            ing_rows = df_ing[
                (df_ing['recipe_id'] == recipe_id) &
                (df_ing['ingredient_normalized_name'] == ing)
            ]
            if not ing_rows.empty:
                row  = ing_rows.iloc[0]
                qty  = row['ingredient_quantity']
                unit = str(row['ingredient_unit']).lower().strip()

                if pd.notna(qty) and unit != 'nan':
                    try:
                        qty = float(qty)
                    except (ValueError, TypeError):
                        qty = None
                    if qty is not None:
                        if (unit, ing) in UNIT_BAHAN_TO_GRAM:
                            gram = UNIT_BAHAN_TO_GRAM[(unit, ing)]
                        elif ing in INGREDIENT_UNIT_OVERRIDE and unit in INGREDIENT_UNIT_OVERRIDE[ing]:
                            gram = INGREDIENT_UNIT_OVERRIDE[ing][unit]
                        elif unit in UNIT_TO_GRAM:
                            gram = UNIT_TO_GRAM[unit]
                        else:
                            gram = None

                        if gram is not None:
                            qty_weight = min(qty * gram, 500) / 100.0

        for t, base_score in taste_map[ing].items():
            score[t]        += base_score * qty_weight
            total_weight[t] += qty_weight

    # Normalisasi per dimensi berdasarkan total qty_weight
    result = {}
    for t in score:
        if total_weight[t] > 0:
            result[t] = round(score[t] / total_weight[t], 2)
        else:
            result[t] = 0.0

    return result

def get_recipe_ingredients(recipe_id):
    """
    Ambil semua bahan beserta kuantitas dari df_ing
    untuk ditampilkan di output.
    Return: list of dict {name, qty, unit}
    """
    rows = df_ing[df_ing['recipe_id'] == recipe_id]
    result = []

    for _, row in rows.iterrows():
        qty  = row['ingredient_quantity']
        unit = row['ingredient_unit']

        # cast qty ke float kalau bisa
        try:
            qty = float(qty) if pd.notna(qty) else None
        except (ValueError, TypeError):
            qty = None

        result.append({
            "name": row['ingredient_normalized_name'],
            "qty":  qty,
            "unit": unit if pd.notna(unit) else None
        })

    return result

def apply_adaptation(recipe_ingredients, adaptations, recipe_taste):
    """
    Hitung kuantitas bahan setelah disesuaikan berdasarkan saran adaptasi.
    Return: list of dict {name, qty_original, qty_adjusted, unit, changed}
    """
    # Kumpulkan bahan mana yang perlu diubah dan berapa persen
    changes = {}  # {ingredient_name: pct_multiplier}

    for a in adaptations:
        if 'diff' not in a:
            continue

        taste   = a['taste']
        action  = a['action']
        current = recipe_taste[taste]

        if current <= 0:
            continue

        # Hitung multiplier
        pct = min(round((abs(a['diff']) / current) * 100), 100) / 100.0
        diff = a['diff']

        if action == 'decrease':
            multiplier = 1.0 - pct
        else:
            multiplier = 1.0 + pct

        # Cari bahan di resep yang berkontribusi ke dimensi ini
        relevant = get_taste_ingredients(
            ' '.join([i['name'] for i in recipe_ingredients]),
            taste
        )

        for ing_name in relevant:
            # Kalau satu bahan relevan ke beberapa dimensi, ambil yang terbesar
            if ing_name not in changes:
                changes[ing_name] = (multiplier, taste, diff)
            else:
                existing_mult, existing_dim, existing_diff = changes[ing_name]

                # Hitung bobot konflik: abs(diff) × skor bahan di dimensi itu
                ing_profile    = taste_map.get(ing_name, {})
                weight_new     = abs(diff)     * ing_profile.get(taste, 0)
                weight_existing= abs(existing_diff) * ing_profile.get(existing_dim, 0)

                if weight_new > weight_existing:
                    changes[ing_name] = (multiplier, taste, diff)

    # Apply ke semua bahan
    result = []
    for ing in recipe_ingredients:
        name         = ing['name']
        qty_original = ing['qty']
        unit         = ing['unit']

         # Cari match — exact dulu, lalu partial
        matched_key = None
        if name in changes:
            matched_key = name
        else:
            for key in changes:
                if key in name or name in key:
                    matched_key = key
                    break

        if matched_key and qty_original is not None:
            multiplier, _, _ = changes[matched_key]
            qty_adjusted     = round(qty_original * multiplier, 2)
            changed          = qty_adjusted != qty_original
        else:
            qty_adjusted = qty_original
            changed      = False

        result.append({
            "name":         name,
            "qty_original": qty_original,
            "qty_adjusted": qty_adjusted,
            "unit":         unit,
            "changed":      changed
        })

    return result



def build_region_baseline(df_final):
    # ✅ TAMBAHAN: hitung region yang memenuhi threshold
    MIN_RECIPES = 6
    valid_regions = set(
        df_final['region'].value_counts()[
            df_final['region'].value_counts() >= MIN_RECIPES
        ].index
    )

    region_scores = {}

    for _, row in df_final.iterrows():
        region = row['region']
        if pd.isna(region):
            continue

        # ✅ TAMBAHAN: skip kalau tidak masuk valid_regions
        if region not in valid_regions:
            continue

        taste = calculate_taste(row['ingredients'], recipe_id=row['id'])

        if region not in region_scores:
            region_scores[region] = {"pedas": 0, "manis": 0, "gurih": 0, "asam": 0, "count": 0}

        for t in ["pedas", "manis", "gurih", "asam"]:
            region_scores[region][t] += taste[t]

        region_scores[region]["count"] += 1

    # hitung rata-rata — sisa kode tetap sama
    baseline = {}
    for region, val in region_scores.items():
        count = val["count"]
        baseline[region] = {
            "pedas": round(val["pedas"] / count, 2),
            "manis": round(val["manis"] / count, 2),
            "gurih": round(val["gurih"] / count, 2),
            "asam":  round(val["asam"]  / count, 2)
        }

    return baseline

def build_cooccurrence(df_final, min_recipes=6):
    """
    Hitung frekuensi kemunculan pasangan bahan per region.
    Output: {region: {(ing_a, ing_b): frequency_ratio}}
    frequency_ratio = jumlah resep yang punya pair ini / total resep region
    """
    from itertools import combinations

    # Hanya region yang memenuhi threshold
    valid_regions = set(
        df_final['region'].value_counts()[
            df_final['region'].value_counts() >= min_recipes
        ].index
    )

    cooccurrence = {}

    for region in valid_regions:
        region_recipes = df_final[df_final['region'] == region]
        total = len(region_recipes)
        pair_count = {}

        for _, row in region_recipes.iterrows():
            ingredients = row['ingredients'].split()
            # hanya bahan yang ada di taste_map
            relevant = [i for i in ingredients if i in taste_map]
            # buat semua kombinasi pair
            for pair in combinations(sorted(relevant), 2):
                pair_count[pair] = pair_count.get(pair, 0) + 1

        # konversi ke ratio
        cooccurrence[region] = {
            pair: round(count / total, 3)
            for pair, count in pair_count.items()
        }

    return cooccurrence

def get_cooccurrence_insight(ingredients_text, source_region, target_region, handled_ingredients=None):
    """
    Bandingkan pair bahan dari resep dengan pola co-occurrence
    source region vs target region.
    """
    from itertools import combinations

    ingredients = ingredients_text.split()
    relevant = [i for i in ingredients if i in taste_map]
    recipe_pairs = list(combinations(sorted(relevant), 2))

    if not recipe_pairs:
        return []

    source_co = cooccurrence.get(source_region, {})
    target_co = cooccurrence.get(target_region, {})

    insights = []

    for pair in recipe_pairs:
        source_ratio = source_co.get(pair, 0)
        target_ratio = target_co.get(pair, 0)
        diff = source_ratio - target_ratio

        # hanya flagging pair yang perbedaannya signifikan
        if diff > 0.1:
            # skip kalau KEDUANYA sudah ditangani adaptation
            if handled_ingredients:
                ing_a, ing_b = pair
                if ing_a in handled_ingredients and ing_b in handled_ingredients:
                    continue

            insights.append({
                "pair": pair,
                "source_ratio": source_ratio,
                "target_ratio": target_ratio,
                "diff": round(diff, 3)
            })

    # urutkan dari perbedaan terbesar
    insights.sort(key=lambda x: x['diff'], reverse=True)

    # Deduplikasi pair
    seen_pairs = set()
    unique_insights = []
    for ins in insights:
        pair_key = tuple(sorted(ins['pair']))
        if pair_key not in seen_pairs:
            seen_pairs.add(pair_key)
            unique_insights.append(ins)

    return unique_insights[:3]


baseline = build_region_baseline(df_final)
cooccurrence = build_cooccurrence(df_final)

adaptation_map = {
    "pedas": {
        "increase": "Tambahkan cabai",
        "decrease": "Kurangi cabai"
    },
    "manis": {
        "increase": "Tambahkan gula",
        "decrease": "Kurangi gula"
    },
    "gurih": {
        "increase": "Tambahkan santan atau kelapa",
        "decrease": "Kurangi santan"
    }
}

def adapt_taste(recipe_taste, target_baseline):
    result = []

    for t in ["pedas", "manis", "gurih", "asam"]:
        diff = recipe_taste[t] - target_baseline[t]

        # Tentukan level confidence
        if abs(diff) > 0.6:
            level = "HIGH"
        elif abs(diff) > 0.3:
            level = "MEDIUM"
        else:
            continue  # skip kalau perbedaan kecil

        # Increase / Decrease
        if diff > 0:
            action = "decrease"
        else:
            action = "increase"

        result.append({
            "taste": t,
            "action": action,
            "diff": round(diff, 2),
            "level": level
        })

    # 🔥 RULE TAMBAHAN 1: BALANCING PEDAS
    if recipe_taste["pedas"] - target_baseline["pedas"] > 0.6 :
        result.append({
            "taste": "balance",
            "action": "soften",
            "note": "Untuk menyeimbangkan rasa pedas, bisa tambahkan gula atau santan",
            "level": "HIGH"
        })

    # 🔥 RULE TAMBAHAN 2: BALANCING ASAM
    if recipe_taste["asam"] - target_baseline["asam"] > 0.6 :
        result.append({
            "taste": "balance",
            "action": "soften",
            "note": "Untuk mengurangi rasa asam, bisa tambahkan gula atau santan",
            "level": "MEDIUM"
        })

    # 🔥 RULE TAMBAHAN 3: UNDERPOWERED DISH
    total_intensity = sum(recipe_taste.values())
    if total_intensity < 1:
        result.append({
            "taste": "overall",
            "action": "enhance",
            "note": "Rasa cenderung ringan, bisa ditingkatkan dengan bumbu utama seperti cabai, gula, atau santan",
            "level": "LOW"
        })

    return result

def get_taste_ingredients(ingredients_text, taste_dim, avoid_dims=None, target_region=None):
    """
    Cari bahan yang sudah ada di resep dan berkontribusi ke dimensi rasa tertentu.
    Filter bahan yang berkontribusi signifikan ke dimensi yang sedang dikurangi.
    Ranking berdasarkan co-occurrence di region target.
    """
    CONFLICT_THRESHOLD = 0.5  # skor minimum untuk dianggap konflik

    ingredients = ingredients_text.split()
    candidates = []

    for ing in ingredients:
        if ing not in taste_map:
            continue
        if taste_dim not in taste_map[ing]:
            continue

        # Opsi B: filter kalau berkontribusi signifikan ke dimensi yang dikurangi
        if avoid_dims:
            conflict = False
            for dim in avoid_dims:
                if taste_map[ing].get(dim, 0) >= CONFLICT_THRESHOLD:
                    conflict = True
                    break
            if conflict:
                continue

        candidates.append(ing)

    # Ranking berdasarkan co-occurrence di region target
    if target_region and candidates:
        region_co = cooccurrence.get(target_region, {})

        def co_score(ing):
            total = 0
            for pair, ratio in region_co.items():
                if ing in pair:
                    total += ratio
            return total

        candidates.sort(key=co_score, reverse=True)

    # Deduplikasi sambil pertahankan urutan
    seen = set()
    unique = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique
def get_substitution_from_cooccurrence(ingredients_text, taste_dim, target_region):
    """
    Kalau tidak ada bahan di resep untuk dimensi tertentu,
    cari dari co-occurrence region target.
    """
    region_co = cooccurrence.get(target_region, {})
    
    # Kumpulkan semua bahan yang muncul di co-occurrence region target
    candidate_ingredients = set()
    for pair in region_co:
        candidate_ingredients.update(pair)
    
    # Filter yang punya dimensi rasa yang kita cari
    result = []
    for ing in candidate_ingredients:
        if ing in taste_map and taste_dim in taste_map[ing]:
            result.append((ing, region_co.get(tuple(sorted([ing, ing])), 0)))
    
    # Urutkan berdasarkan frekuensi di region target
    result.sort(key=lambda x: x[1], reverse=True)
    
    return [ing for ing, _ in result[:3]]

def get_quantity_reference(ingredient_name, similar_scores, target_region):
    """
    Cari referensi takaran bahan dari:
    A. Resep serupa (top 3 cosine sim)
    B. Resep dari region target
    Hanya rata-rata unit yang sama.
    """
    def avg_qty_by_unit(recipe_ids):
        from collections import defaultdict
        unit_qtys = defaultdict(list)

        for rid in recipe_ids:
            rows = df_ing[
                (df_ing['recipe_id'] == rid) &
                (df_ing['ingredient_normalized_name'] == ingredient_name)
            ]
            for _, row in rows.iterrows():
                unit = row['ingredient_unit']
                qty  = row['ingredient_quantity']
                if pd.notna(unit) and pd.notna(qty):
                    try:
                        unit_qtys[str(unit)].append(float(qty))
                    except (ValueError, TypeError):
                        pass

        if not unit_qtys:
            return None

        # Ambil unit yang paling sering muncul
        dominant_unit = max(unit_qtys, key=lambda u: len(unit_qtys[u]))
        avg = round(sum(unit_qtys[dominant_unit]) / len(unit_qtys[dominant_unit]), 2)
        return f"{avg} {dominant_unit}"

    result = {}

    # A. Dari resep serupa
    similar_ids = [df_final.iloc[i]['id'] for i, _ in similar_scores[:3]]
    ref_similar = avg_qty_by_unit(similar_ids)
    if ref_similar:
        result['similar'] = ref_similar

    # B. Dari resep region target
    region_ids = df_final[df_final['region'] == target_region]['id'].tolist()
    ref_region = avg_qty_by_unit(region_ids)
    if ref_region:
        result['region'] = ref_region

    return result

def generate_explanation(adaptations, recipe_taste, target_baseline, target_region, ingredients_text="", similar_scores=None, df_similar=None):
    if not adaptations:
        return "Rasa sudah sesuai dengan preferensi wilayah target."

    explanation = ""

    # Kumpulkan dimensi rasa yang sedang dikurangi
    dims_to_decrease = [
        a['taste'] for a in adaptations
        if 'action' in a and a['action'] == 'decrease'
    ]

    for a in adaptations:
        # HANDLE SPECIAL RULE (tanpa diff)
        if "diff" not in a:
            explanation += f"- {a['note']} ({a['level']})\n"
            continue

        # NORMAL RULE
        taste = a["taste"]
        action = a["action"]
        diff = a["diff"]
        level = a["level"]

        current = recipe_taste[taste]
        target = target_baseline[taste]

        if taste == "pedas":
            ingredient = "cabai"
        elif taste == "manis":
            ingredient = "gula"
        elif taste == "gurih":
            ingredient = "santan atau kelapa"
        elif taste == "asam":
            ingredient = "asam jawa atau jeruk"
        else:
            ingredient = "bumbu tambahan"

        
        if action == "increase":
            # Cari bahan di resep yang sudah berkontribusi ke dimensi ini
            existing = get_taste_ingredients(
                ingredients_text, taste,
                avoid_dims=dims_to_decrease,
                target_region=target_region
            )
            
            if existing:
                bahan_text  = " atau ".join(existing)
                source_note = "(sudah ada di resep)"
                qty_ref     = ""
                subs        = []
            else:
                subs = get_substitution_from_cooccurrence(ingredients_text, taste, target_region)
                if subs:
                    bahan_text = " atau ".join(subs)
                else:
                    bahan_text = ingredient
                    subs       = []
                source_note = "(bahan baru — tidak ada di resep asli)"

            # Cari referensi takaran
            qty_ref = ""
            if similar_scores is not None:
                for candidate in (subs if subs else [ingredient]):
                    refs = get_quantity_reference(candidate, similar_scores, target_region)
                    if refs:
                        ref_lines = []
                        if 'similar' in refs:
                            ref_lines.append(f"resep serupa: {candidate} rata-rata {refs['similar']}")
                        if 'region' in refs:
                            ref_lines.append(f"resep {target_region}: {candidate} rata-rata {refs['region']}")
                        if ref_lines:
                            qty_ref = "\n     📖 Referensi takaran — " + " | ".join(ref_lines)
                        break

            # Hitung persentase
            if current > 0:
                pct = min(round((abs(diff) / current) * 100), 100)
                if pct < 25:
                    pct_text = "sekitar seperempat atau kurang"
                elif pct < 50:
                    pct_text = "sekitar seperempat hingga setengah"
                elif pct < 75:
                    pct_text = "sekitar setengah hingga tiga perempat"
                else:
                    pct_text = "sekitar tiga perempat atau lebih"
                amount_text = f" — {pct_text} dari jumlah semula"
            else:
                amount_text = ""

            explanation += (
                f"- {taste.upper()} saat ini {current} → target {target} "
                f"(+{abs(diff)} | {level}) → Tambahkan {bahan_text} {source_note}{amount_text}{qty_ref}\n"
            )

        else:
            # Cari bahan di resep yang berkontribusi ke dimensi ini
            existing = get_taste_ingredients(
                ingredients_text, taste,
                target_region=target_region
            )
            
            if existing:
                bahan_text = " atau ".join(existing)
                source_note = ""
            else:
                bahan_text = ingredient
                source_note = ""

            # Hitung persentase
            if current > 0:
                pct = min(round((abs(diff) / current) * 100), 100)
                if pct < 25:
                    pct_text = "sekitar seperempat atau kurang"
                elif pct < 50:
                    pct_text = "sekitar seperempat hingga setengah"
                elif pct < 75:
                    pct_text = "sekitar setengah hingga tiga perempat"
                else:
                    pct_text = "sekitar tiga perempat atau lebih"
                amount_text = f" — {pct_text} dari jumlah semula"
            else:
                amount_text = ""

            explanation += (
                f"- {taste.upper()} saat ini {current} → target {target} "
                f"(-{abs(diff)} | {level}) → Kurangi {bahan_text}{source_note}{amount_text}\n"
            )

    return explanation

def get_relevant_references(scores, adaptations, base_taste, top_n=5):
    """
    Dari daftar resep serupa, filter hanya yang relevan
    dengan dimensi yang disesuaikan.
    scores = list of (idx, similarity_score) dari cosine_sim
    """
    # Dimensi yang disesuaikan
    adapted_dims = [
        a['taste'] for a in adaptations
        if 'diff' in a
    ]

    if not adapted_dims:
        return []

    result = []

    for i, sim_score in scores:
        ref         = df_final.iloc[i]
        ref_taste   = calculate_taste(ref['ingredients'], recipe_id=ref['id'])
        relevant    = False
        dim_notes   = []

        for dim in adapted_dims:
            diff = ref_taste[dim] - base_taste[dim]
            # Resep serupa relevan kalau taste-nya berbeda signifikan
            if abs(diff) > 0.3:
                # Cek arah — harus searah dengan saran adaptasi
                action = next(
                    (a['action'] for a in adaptations
                     if a.get('taste') == dim and 'action' in a),
                    None
                )
                ref_direction   = "lebih tinggi" if diff > 0 else "lebih rendah"
                saran_direction = "increase" if diff > 0 else "decrease"

                # Skip kalau berlawanan arah dengan saran
                if action and action != saran_direction:
                    continue

                dim_notes.append(
                    f"{dim}={ref_taste[dim]:.2f} ({ref_direction} dari resep ini {base_taste[dim]:.2f})"
                )
                relevant = True

        if relevant:
            result.append({
                "name":      ref['recipe_name'],
                "region":    ref['region'] if pd.notna(ref['region']) else '—',
                "sim":       round(sim_score, 3),
                "taste":     ref_taste,
                "dim_notes": dim_notes
            })

    return result[:top_n]

def find_recipe(query):
    """
    Cari resep dengan 3 level: partial match, per kata, suggestions.
    Return dict:
    {
        "status": "found" | "not_found",
        "idx": int,              # kalau found
        "recipe_name": str,      # kalau found
        "suggestions": list,     # kalau not_found
        "notification": str,     # pesan opsional (fuzzy match, banyak hasil)
    }
    """
    query_normalized = normalize_query(query).upper()
    if 'recipe_name_normalized' not in df_final.columns:
        df_final['recipe_name_normalized'] = df_final['recipe_name'].apply(
            lambda x: normalize_query(x).upper()
        )

    # Level 1: partial match query penuh
    words_in_query = query_normalized.split()
    if len(words_in_query) == 1:
        # Single word: pakai word boundary agar "AYAM" tidak match "BAYAM"
        pattern = r'\b' + query_normalized + r'\b'
        idx = df_final[
            df_final['recipe_name_normalized'].str.contains(
                pattern, case=False, na=False, regex=True
            )
        ].index
    else:
        # Multi-word: substring biasa
        idx = df_final[
            df_final['recipe_name_normalized'].str.contains(
                query_normalized, case=False, na=False
            )
        ].index

    # Level 2: partial match per kata
    if len(idx) == 0:
        words = [w for w in query_normalized.split() if len(w) >= 3]
        word_freq = {}
        for word in words:
            pattern = r'\b' + word + r'\b'
            word_freq[word] = df_final['recipe_name_normalized'].str.contains(
                pattern, case=False, na=False, regex=True
            ).sum()

        words_sorted = sorted(words, key=lambda w: word_freq[w])
        for word in words_sorted:
            if word_freq[word] == 0:
                continue
            pattern = r'\b' + word + r'\b'
            idx = df_final[
                df_final['recipe_name_normalized'].str.contains(
                    pattern, case=False, na=False, regex=True
                )
            ].index
            if len(idx) > 0:
                break

        # Validasi threshold 100%
        if len(idx) > 0:
            validated = []
            for i in idx:
                norm = df_final.iloc[i]['recipe_name_normalized']
                matched_words = sum(
                    1 for w in words
                    if re.search(r'\b' + w + r'\b', norm, re.IGNORECASE)
                )
                if matched_words >= len(words):
                    validated.append(i)
            idx = pd.Index(validated) if validated else pd.Index([])

    # Level 3: tidak ketemu → kumpulkan suggestions
    # Level 3a: fuzzy auto-match (score >= 80)
    if len(idx) == 0:
        matched, score, action = fuzzy_match_recipe(
            query_normalized,
            df_final['recipe_name_normalized'].tolist()
        )
        if action == 'match':
            # Length ratio check: hindari match query panjang ke nama pendek
            len_query   = len(query_normalized.replace(" ", ""))
            len_matched = len(matched.replace(" ", ""))
            length_ratio = min(len_query, len_matched) / max(len_query, len_matched)

            if length_ratio >= 0.6:  # panjang tidak boleh beda lebih dari 40%
                fuzzy_idx = df_final[
                    df_final['recipe_name_normalized'] == matched
                ].index
                if len(fuzzy_idx) > 0:
                    return {
                        "status":       "found",
                        "idx":          int(fuzzy_idx[0]),
                        "recipe_name":  df_final.iloc[fuzzy_idx[0]]['recipe_name'],
                        "notification": f"Menampilkan hasil untuk: {df_final.iloc[fuzzy_idx[0]]['recipe_name']} (kemiripan {score:.0f}%)",
                    }

    # Level 3b: tidak ketemu → kumpulkan suggestions
    if len(idx) == 0:
        suggestion_idxs = []
        seen = set()
    if len(idx) == 0:
        suggestion_idxs = []
        seen = set()

        words = [w for w in query_normalized.split() if len(w) >= 3]
        for word in words:
            partial = df_final[
                df_final['recipe_name_normalized'].str.contains(
                    word, case=False, na=False
                )
            ].index.tolist()
            for i in partial:
                if i not in seen:
                    seen.add(i)
                    suggestion_idxs.append(i)

        from rapidfuzz import process as fuzz_process
        all_names = df_final['recipe_name_normalized'].tolist()
        fuzzy_results = fuzz_process.extract(query_normalized, all_names, limit=5)
        for matched_name, score, _ in fuzzy_results:
            if score >= 50:
                fidx = df_final[
                    df_final['recipe_name_normalized'] == matched_name
                ].index
                for i in fidx:
                    if i not in seen:
                        seen.add(i)
                        suggestion_idxs.append(i)

        suggestions = []
        for i in suggestion_idxs[:10]:
            ref = df_final.iloc[i]
            suggestions.append({
                "title":  ref['recipe_name'],
                "region": ref['region'] if pd.notna(ref['region']) else '—',
                "idx":    i,
            })

        return {"status": "not_found", "suggestions": suggestions}

    # Terlalu banyak hasil → tampilkan suggestions
    if len(idx) > 5:
        suggestions = []
        for i in idx[:10]:
            ref = df_final.iloc[i]
            suggestions.append({
                "title":  ref['recipe_name'],
                "region": ref['region'] if pd.notna(ref['region']) else '—',
                "idx":    i,
            })
        return {"status": "not_found", "suggestions": suggestions}

    # hasil → auto-pick pertama + notifikasi
    notification = None
    if len(idx) > 1:
        notification = f"Ditemukan {len(idx)} resep dengan nama mengandung '{query}'. Menampilkan: {df_final.iloc[idx[0]]['recipe_name']}"

    chosen_idx = idx[0]
    return {
        "status":       "found",
        "idx":          int(chosen_idx),
        "recipe_name":  df_final.iloc[chosen_idx]['recipe_name'],
        "notification": notification,
    }

def recommend(recipe_name, target_region="Jakarta", top_n=5, api_mode=False):
    print("\nCULINARY BRIDGE AI\n")

    # Cari resep
    query_normalized = normalize_query(recipe_name).upper()
    if 'recipe_name_normalized' not in df_final.columns:
        df_final['recipe_name_normalized'] = df_final['recipe_name'].apply(
            lambda x: normalize_query(x).upper()
        )

# Cari resep menggunakan find_recipe()
    search_result = find_recipe(recipe_name)

    if search_result['status'] == 'not_found':
        print(f"\nResep '{recipe_name}' tidak ditemukan di database.")
        suggestions = search_result.get('suggestions', [])
        if suggestions:
            print(f"\n   Resep yang mungkin relevan:\n")
            for num, s in enumerate(suggestions, 1):
                print(f"   {num:2d}. {s['title']:<40} ({s['region']})")
            if not api_mode:
                print(f"\n   Ketik nomor untuk lanjut, atau 0 untuk batal:")
                try:
                    choice = int(input("   > "))
                    if choice == 0:
                        print("Dibatalkan.")
                        return
                    if 1 <= choice <= len(suggestions):
                        idx = pd.Index([suggestions[choice - 1]['idx']])
                    else:
                        print("Nomor tidak valid.")
                        return
                except ValueError:
                    print("Input tidak valid.")
                    return
            else:
                return
        else:
            print(f"   Tidak ada resep yang relevan ditemukan.")
            return
    else:
        idx = pd.Index([search_result['idx']])
        if search_result['notification']:
            print(f"\n{search_result['notification']}")

     # Notifikasi kalau ada banyak match
    if len(idx) > 1:
        print(f"\nDitemukan {len(idx)} resep dengan nama mengandung '{recipe_name}'.")
        print(f"   Menampilkan: {df_final.iloc[idx[0]]['recipe_name']}")
        print(f"   Ketik nama lebih spesifik untuk hasil yang berbeda.\n")

    idx          = idx[0]
    base_recipe  = df_final.iloc[idx]
    base_taste   = calculate_taste(base_recipe['ingredients'], recipe_id=base_recipe['id'])

    # Cek apakah semua taste score = 0
    if all(v == 0 for v in base_taste.values()):
        print(f"\nProfil rasa resep ini tidak dapat dihitung.")
        print(f"   Kemungkinan bahan-bahan tidak ada dalam taste map sistem.")
        print(f"   Adaptasi tidak dapat dijalankan.")
        return
    

    # Level 1: cek alias dict
    region_normalized = normalize_region(target_region.lower())
    if region_normalized:
        target_region = region_normalized
    # Level 2: exact match langsung
    elif target_region in baseline:
        pass
    # Level 3: fuzzy matching
    else:
        matched, score, action = fuzzy_match_region(
            target_region, list(baseline.keys())
        )
        if action == 'match':
            print(f"\n Region '{target_region}' tidak ditemukan.")
            print(f"   Menampilkan hasil untuk: {matched} (kemiripan {score:.0f}%)\n")
            target_region = matched
        elif action == 'suggest':
            if api_mode:
                # API mode: tolak suggest, hanya accept match (≥80%)
                print(f"\nRegion '{target_region}' tidak tersedia.")
                print(f"   Wilayah terdekat: {matched} (kemiripan {score:.0f}%) — terlalu rendah untuk auto-match.")
                print(f"   Gunakan nama wilayah yang lebih spesifik.")
                return
            else:
                print(f"\n Region '{target_region}' tidak ditemukan.")
                print(f"   Maksud kamu: {matched}? (kemiripan {score:.0f}%)")
                print(f"   Ketik 'ya' untuk lanjut atau 'tidak' untuk batal:")
                confirm = input("   > ").strip().lower()
                if confirm in ['ya', 'y', 'yes']:
                    target_region = matched
                else:
                    print("Dibatalkan.")
                    return
        else:
            print(f"Region '{target_region}' tidak tersedia.")
            print(f"   Pilihan: {sorted(baseline.keys())}")
            return

 # Cek apakah resep sudah dari region yang sama
    source_region = base_recipe['region']
    if pd.notna(source_region) and source_region.strip() == target_region.strip():
        print(f"\nResep ini berasal dari {target_region} — sudah sesuai dengan preferensi wilayah target.")
        print(f"   Tidak diperlukan adaptasi.")
        return

    # Warning kalau region tidak diketahui
    if pd.isna(source_region) or source_region.strip() == '—':
        print(f"\n Asal resep tidak diketahui — adaptasi tetap dijalankan berdasarkan profil rasa.")

    target       = baseline[target_region]
    adaptation   = adapt_taste(base_taste, target)
    recipe_ings  = get_recipe_ingredients(base_recipe['id'])
    adjusted     = apply_adaptation(recipe_ings, adaptation, base_taste)

    scores = list(enumerate(cosine_sim[idx]))
    scores = sorted(scores, key=lambda x: x[1], reverse=True)
    scores = scores[1:top_n+1]

    # SECTION 1: INFORMASI RESEP
    print(f"{base_recipe['recipe_name']}")
    region_display = base_recipe['region'] if pd.notna(base_recipe['region']) else '-'
    print(f"Asal: {region_display}")
    print(f"Profil: Pedas {base_taste['pedas']}, Manis {base_taste['manis']}, "
          f"Gurih {base_taste['gurih']}, Asam {base_taste['asam']}")
    
    # SECTION 2: RESEP ORIGINAL
    print(f"\n\nRESEP ORIGINAL")
    for ing in recipe_ings:
        qty_display = normalize_qty_display(ing['qty'], ing['unit'])
        unit = ing['unit'] or ""
        print(f"- {ing['name']:<25} : {qty_display} {unit}".rstrip())

    # SECTION 3: SARAN PENYESUAIAN
    adapted_dims = [a['taste'] for a in adaptation if 'diff' in a]

    if not adapted_dims:
        print(f"\n\nProfil rasa sudah sesuai dengan preferensi {target_region}.")
    else:
        print(f"\n\nSARAN PENYESUAIAN — {target_region}")
        print(f"Baseline {target_region}: "
              f"Pedas {target['pedas']}  Manis {target['manis']}  "
              f"Gurih {target['gurih']}  Asam {target['asam']}")
        print()
        expl = generate_explanation(
            adaptation, base_taste, target, target_region,
            ingredients_text=base_recipe['ingredients'],
            similar_scores=scores
        )
        for line in expl.strip().split('\n'):
            if line.strip():
                print(line)

    # SECTION 4: REFERENSI PENYESUAIAN
    print(f"\n\nREFERENSI PENYESUAIAN")

    # A. Baseline wilayah
    print(f"\nA. Baseline Wilayah (data Mustika Rasa):")
    for a in adaptation:
        if 'diff' not in a:
            continue
        dim   = a['taste']
        n_rec = sum(1 for _, row in df_final.iterrows()
                    if row['region'] == target_region)
        print(f"- {target_region} memiliki rata-rata {dim}={target[dim]:.2f}")
        print(f" Resep ini: {dim}={base_taste[dim]:.2f} "
              f"({'di bawah' if a['action'] == 'increase' else 'di atas'} rata-rata)")

    # B. Resep serupa yang relevan
    relevant_refs = get_relevant_references(scores, adaptation, base_taste)
    if relevant_refs:
        print(f"\nB. Resep Serupa yang Relevan:")
        for ref in relevant_refs:
            print(f"- {ref['name']:<40} (sim={ref['sim']}, asal={ref['region']})")
            for note in ref['dim_notes']:
                print(f" → {note}")

    # C. Network insight
    source_region = base_recipe['region']
    handled_ingredients = set()
    for a in adaptation:
        if 'action' not in a:
            continue
        taste_dim = a.get('taste')
        if taste_dim in ["pedas", "manis", "gurih", "asam"]:
            relevant = get_taste_ingredients(base_recipe['ingredients'], taste_dim)
            handled_ingredients.update(relevant)

    co_insights = get_cooccurrence_insight(
        base_recipe['ingredients'],
        source_region=source_region,
        target_region=target_region,
        handled_ingredients=handled_ingredients
    )

    if co_insights:
        print(f"\nC. Pola Kombinasi Bahan (Network):")
        for ins in co_insights:
            ing_a, ing_b = ins['pair']
            print(f"- '{ing_a} + {ing_b}' dominan di {source_region} "
                  f"({ins['source_ratio']}) tapi jarang di {target_region} "
                  f"({ins['target_ratio']})")
            print(f" → pertimbangkan untuk disesuaikan")

    # SECTION 5: RESEP SETELAH DISESUAIKAN
    has_changes = any(ing['changed'] for ing in adjusted)

    if has_changes:
        print(f"\n\nRESEP SETELAH DISESUAIKAN")
        for ing in adjusted:
            qty_display = normalize_qty_display(ing['qty_adjusted'], ing['unit'])
            unit = ing['unit'] or ""
            flag = "  ← disesuaikan" if ing['changed'] else ""
            print(f"   - {ing['name']:<25} : {qty_display} {unit}{flag}")
    else:
        print(f"\n\nTidak ada perubahan kuantitas bahan.")

def recommend_api(recipe_name, target_region="Jakarta", top_n=5):
    """
    Wrapper untuk recommend() yang return dict instead of print.
    """
    import io
    from contextlib import redirect_stdout

    # Capture print output
    f = io.StringIO()
    with redirect_stdout(f):
        recommend(recipe_name, target_region=target_region, top_n=top_n, api_mode=True)
    
    output_text = f.getvalue()
    
    return {
        "status": "ok",
        "output": output_text
    }

if __name__ == "__main__":
    import json
    result = recommend_api("rendeng", target_region="Jakarta")
    print(result["output"])




# if __name__ == "__main__":
#     # Test apply_adaptation
#     recipe_id  = "MR_796_01"  # id SAMBAL TERONG GORENG
#     ings       = get_recipe_ingredients(recipe_id)
#     base_taste = calculate_taste(
#         ' '.join([i['name'] for i in ings]),
#         recipe_id=recipe_id
#     )
#     target     = baseline["Jakarta"]
#     adaptation = adapt_taste(base_taste, target)

#     adjusted = apply_adaptation(ings, adaptation, base_taste)

#     print("\n=== ORIGINAL ===")
#     for ing in ings:
#         qty  = ing['qty'] if ing['qty'] is not None else "secukupnya"
#         unit = ing['unit'] or ""
#         print(f"  - {ing['name']}: {qty} {unit}")

#     print("\n=== SETELAH DISESUAIKAN ===")
#     for ing in adjusted:
#         qty  = ing['qty_adjusted'] if ing['qty_adjusted'] is not None else "secukupnya"
#         unit = ing['unit'] or ""
#         flag = " ← disesuaikan" if ing['changed'] else ""
#         print(f"  - {ing['name']}: {qty} {unit}{flag}")

