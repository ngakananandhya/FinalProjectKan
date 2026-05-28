import os
import json
import sys
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import calculate_taste, taste_map, df_final, cosine_sim

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(BASE_DIR, 'data', 'cleaned_mustika_rasa_full.json'), encoding='utf-8') as f:
    json_recipes = json.load(f)

# print(f"Total resep loaded: {len(json_recipes)}")
# print("Contoh title:", json_recipes[5]['title_original'])

def search_recipe(query):
    from input_parser import normalize_query

    # Normalisasi input user (ejaan lama → modern)
    query_normalized = normalize_query(query).upper()

    # Normalisasi juga judul di database untuk perbandingan
    results = []
    for recipe in json_recipes:
        title_normalized = normalize_query(recipe['title_original']).upper()
        if title_normalized == query_normalized:
            results.append(recipe)

    return results

def display_taste(recipe_id, ingredients_text):
    """
    Tampilkan dimensi rasa resep.
    """
    taste = calculate_taste(ingredients_text, recipe_id=recipe_id)
    print("\n\nDimensi Rasa:")
    for dim, score in taste.items():
        bar = "█" * int(score * 5)
        print(f" {dim:<8}: {score:.2f}  {bar}")

def display_similar(recipe_id, top_n=5):
    """
    Tampilkan resep serupa berdasarkan TF-IDF cosine similarity.
    """
    idx_list = df_final[df_final['id'] == recipe_id].index.tolist()
    if not idx_list:
        print("\n\nResep tidak ditemukan di index similarity.")
        return

    idx = idx_list[0]
    scores = sorted(enumerate(cosine_sim[idx]), key=lambda x: x[1], reverse=True)
    scores = [s for s in scores if s[0] != idx][:top_n]

    print(f"\n\nResep Serupa:")
    for i, score in scores:
        ref = df_final.iloc[i]
        region = ref['region'] if pd.notna(ref['region']) else '—'
        print(f"- {ref['recipe_name']:<40} sim={score:.3f} | asal: {region}")

def display_recipe(recipe):
    """
    Tampilkan detail lengkap satu resep.
    """
    print(f"\n{recipe['title_original']}")
    print(f"Asal Daerah : {recipe['region'] or '—'}")
    print(f"Kategori    : {recipe['category'] or '—'}")

    # Bahan-bahan
    print("\n\nBahan-bahan:")
    for group in recipe['ingredient_groups']:
        # Tampilkan nama group kalau lebih dari satu group
        if len(recipe['ingredient_groups']) > 1:
            print(f"\n  [{group['group_name'].upper()}]")
        for ing in group['ingredients']:
            qty  = ing['quantity']
            unit = ing['unit'] or ''
            name = ing['item_normalized']

            from input_parser import normalize_qty_display
            qty_display = normalize_qty_display(qty, unit)
            print(f" - {name}: {qty_display} {unit.strip()}")
    # Instruksi
    print("\n\nCara Memasak:")
    for i, step in enumerate(recipe['instructions'], 1):
        print(f" {i}. {step}")

        # Dimensi rasa
    ingredients_str = ' '.join([
        ing['item_normalized']
        for group in recipe['ingredient_groups']
        for ing in group['ingredients']
    ])
    display_taste(recipe['recipe_id'], ingredients_str)

    # Resep serupa
    display_similar(recipe['recipe_id'])

def search_by_region(region_query):
    """
    Cari semua resep dari region tertentu.
    Tampilkan daftar dulu, user bisa pilih untuk lihat detail.
    """
    from input_parser import normalize_query

    from input_parser import normalize_region

    # Coba alias dulu
    region_resolved = normalize_region(region_query.lower())
    if region_resolved:
        query_normalized = region_resolved.lower()
    else:
        query_normalized = normalize_query(region_query).lower()

    results = []
    for recipe in json_recipes:
        region = recipe.get('region', '')
        if not region:
            continue
        if normalize_query(region).lower() == query_normalized:
            results.append(recipe)

    if not results:
        print(f"❌ Tidak ada resep dari region '{region_query}'.")
        return

    # Tampilkan daftar
    print(f"\nResep dari {region_query} ({len(results)} resep):\n")
    for i, r in enumerate(results, 1):
        print(f"   {i:3d}. {r['title_original'].strip()}")

    # User pilih
    print(f"\n\nKetik nomor untuk lihat detail, atau 0 untuk skip:")
    try:
        choice = int(input("   Pilihan: "))
        if choice == 0:
            return
        if 1 <= choice <= len(results):
            display_recipe(results[choice - 1])
        else:
            print(" ❌ Nomor tidak valid.")
    except ValueError:
        print(" ❌ Input tidak valid.")

def display_konversi():
    """
    Tampilkan tabel konversi ukuran rumah tangga dari Mustika Rasa.
    """
    from input_parser import UNIT_TO_GRAM, UNIT_BAHAN_TO_GRAM

    print("TABEL KONVERSI UKURAN RUMAH TANGGA")
    print("(Sumber: Mustika Rasa)")

    print("\n\nKONVERSI UMUM:\n")
    unit_display = {
        "sendok teh":   "Sendok teh (sdt)",
        "sendok makan": "Sendok makan (sdm)",
        "gelas":        "Gelas (gls)",
        "cangkir":      "Cangkir (tjk)",
        "ons":          "Ons",
        "liter":        "Liter",
        "kilogram":     "Kilogram (kg)",
        "gram":         "Gram (g)",
    }
    for unit, label in unit_display.items():
        gram = UNIT_TO_GRAM.get(unit)
        if gram:
            print(f"1 {label:<25} = {gram} ml/g")

    print("\nKONVERSI SPESIFIK PER BAHAN:\n")
    # Kelompokkan per unit
    from collections import defaultdict
    grouped = defaultdict(list)
    for (unit, bahan), gram in sorted(UNIT_BAHAN_TO_GRAM.items()):
        grouped[unit].append((bahan, gram))

    for unit, items in sorted(grouped.items()):
        print(f"   [{unit.upper()}]")
        for bahan, gram in items:
            print(f"1 {unit} {bahan:<25} = {gram}g")
        print()



# UPDATE TEST
if __name__ == "__main__":
    results = search_recipe("SAMBAL TERONG GORENG")
    for r in results:
        display_recipe(r)

# if __name__ == "__main__":
#     results = search_recipe("NASI GORENG")
#     print(f"Ditemukan: {len(results)} resep")
#     for r in results:
#         print(f"  - {r['title_original']}")