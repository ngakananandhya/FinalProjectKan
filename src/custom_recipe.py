import os
import sys
import numpy as np
import pandas as pd


sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import (
    df_final, tfidf, tfidf_matrix, cosine_sim,
    taste_map, baseline, df_ing,
    calculate_taste, adapt_taste, generate_explanation,
    get_taste_ingredients, get_cooccurrence_insight,
    get_relevant_references, apply_adaptation,
    UNIT_TO_GRAM, UNIT_BAHAN_TO_GRAM, INGREDIENT_UNIT_OVERRIDE
)
from input_parser import parse_recipe_input, normalize_qty_display


def calculate_taste_from_list(ingredient_list):
    """
    Hitung taste profile dari list bahan hasil parsing.
    Mirip calculate_taste tapi input-nya list dict, bukan string + recipe_id.
    """
    score        = {"pedas": 0, "manis": 0, "gurih": 0, "asam": 0}
    total_weight = {"pedas": 0, "manis": 0, "gurih": 0, "asam": 0}

    for ing in ingredient_list:
        name = ing['name']
        if name not in taste_map:
            continue

        # Hitung qty_weight
        qty  = ing['qty']
        unit = (ing['unit'] or '').lower().strip()

        qty_weight = 1.0
        if qty is not None and unit and unit not in {"secukupnya", "sedikit",
                                                      "sesuai selera", "sck"}:
            # Prioritas 1: lookup bahan+unit spesifik dari Mustika Rasa
            if (unit, name) in UNIT_BAHAN_TO_GRAM:
                gram = UNIT_BAHAN_TO_GRAM[(unit, name)]
            # Prioritas 2: override per bahan
            elif name in INGREDIENT_UNIT_OVERRIDE and unit in INGREDIENT_UNIT_OVERRIDE[name]:
                gram = INGREDIENT_UNIT_OVERRIDE[name][unit]
            # Prioritas 3: fallback umum
            elif unit in UNIT_TO_GRAM:
                gram = UNIT_TO_GRAM[unit]
            else:
                gram = None

            if gram is not None:
                qty_weight = min(qty * gram, 500) / 100.0

        for t, base_score in taste_map[name].items():
            score[t]        += base_score * qty_weight
            total_weight[t] += qty_weight

    result = {}
    for t in score:
        if total_weight[t] > 0:
            result[t] = round(score[t] / total_weight[t], 2)
        else:
            result[t] = 0.0

    return result


def find_similar_recipes(ingredient_list, top_n=5):
    """
    Cari resep serupa dari database menggunakan TF-IDF transform (Opsi B).
    """
    # Buat string bahan dari input user
    ing_str    = ' '.join([i['name'] for i in ingredient_list])

    # Transform pakai tfidf yang sudah di-fit (tidak re-fit)
    user_vec   = tfidf.transform([ing_str])

    # Hitung cosine similarity antara resep user vs semua resep di database
    from sklearn.metrics.pairwise import cosine_similarity
    sim_scores = cosine_similarity(user_vec, tfidf_matrix).flatten()

    # Urutkan dari tertinggi
    top_idx    = sim_scores.argsort()[::-1][:top_n]

    results = []
    for idx in top_idx:
        ref = df_final.iloc[idx]
        results.append({
            "idx":    idx,
            "name":   ref['recipe_name'],
            "region": ref['region'] if pd.notna(ref['region']) else '—',
            "sim":    round(sim_scores[idx], 3)
        })

    return results


def recommend_custom(recipe_name, raw_ingredients, target_region="Jakarta", top_n=5):
    """
    Rekomendasi adaptasi untuk resep custom dari user.
    """
    print("\nCULINARY BRIDGE AI — Custom Recipe\n")

    # Parse input
    ingredient_list = parse_recipe_input(raw_ingredients)

    if not ingredient_list:
        print("❌ Tidak ada bahan yang berhasil di-parse.")
        return

    from input_parser import normalize_region, fuzzy_match_region

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
            print(f"\nRegion '{target_region}' tidak ditemukan.")
            print(f"   Menampilkan hasil untuk: {matched} (kemiripan {score:.0f}%)\n")
            target_region = matched
        elif action == 'suggest':
            print(f"\n❓ Region '{target_region}' tidak ditemukan.")
            print(f"   Maksud kamu: {matched}? (kemiripan {score:.0f}%)")
            print(f"   Ketik 'ya' untuk lanjut atau 'tidak' untuk batal:")
            confirm = input("   > ").strip().lower()
            if confirm in ['ya', 'y', 'yes']:
                target_region = matched
            else:
                print("   ❌ Dibatalkan.")
                return
        else:
            print(f"❌ Region '{target_region}' tidak tersedia.")
            print(f"   Pilihan: {sorted(baseline.keys())}")
            return

    # Hitung taste
    base_taste = calculate_taste_from_list(ingredient_list)
    target     = baseline[target_region]
    adaptation = adapt_taste(base_taste, target)
    

    # SECTION 1: INFORMASI RESEP
    print(f"\n\nINFORMASI RESEP")
    print(f"{recipe_name}")
    print(f"Resep custom")
    print(f"Profil: Pedas {base_taste['pedas']}  Manis {base_taste['manis']}  "
          f"Gurih {base_taste['gurih']}  Asam {base_taste['asam']}")
    

    # SECTION 2: RESEP ORIGINAL
    print(f"\n\nRESEP ORIGINAL")
    for ing in ingredient_list:
        qty_display = normalize_qty_display(ing['qty'], ing['unit'])
        unit = "" if ing['qty'] is None else (ing['unit'] or "")
        print(f"- {ing['name']:<25} : {qty_display} {unit}")

    # SECTION 3: SARAN PENYESUAIAN
    adapted_dims = [a['taste'] for a in adaptation if 'diff' in a]

    if not adapted_dims:
        print(f"\nProfil rasa sudah sesuai dengan preferensi {target_region}.")
    else:
        print(f"\n\nSARAN PENYESUAIAN → {target_region}")
        print(f"Baseline {target_region}: "
            f"Pedas {target['pedas']}, Manis {target['manis']}, "
            f"Gurih {target['gurih']}, Asam {target['asam']}")
        print()

        # Buat ingredients_text untuk generate_explanation
        ing_text = ' '.join([i['name'] for i in ingredient_list])
        expl     = generate_explanation(
            adaptation, base_taste, target, target_region,
            ingredients_text=ing_text
        )
        for line in expl.strip().split('\n'):
            if line.strip():
                print(f"   {line}")

    # SECTION 4: REFERENSI PENYESUAIAN
    similar = find_similar_recipes(ingredient_list, top_n=top_n)

    print(f"\n\nREFERENSI PENYESUAIAN")

    # A. Baseline wilayah
    print(f"\nA. Baseline Wilayah (data Mustika Rasa):")
    for a in adaptation:
        if 'diff' not in a:
            continue
        dim = a['taste']
        print(f"- {target_region} memiliki rata-rata {dim}={target[dim]:.2f}")
        print(f" Resep ini: {dim}={base_taste[dim]:.2f} "
              f"({'di bawah' if a['action'] == 'increase' else 'di atas'} rata-rata)")

    # B. Resep serupa yang relevan
    print(f"\nB. Resep Serupa dari Database:")
    for ref in similar:
        ref_recipe = df_final.iloc[ref['idx']]
        ref_taste  = calculate_taste(
            ref_recipe['ingredients'],
            recipe_id=ref_recipe['id']
        )
        print(f"- {ref['name']:<40} (sim={ref['sim']}, asal={ref['region']})")

        # Tampilkan dimensi yang relevan
        for dim in adapted_dims:
            diff   = ref_taste[dim] - base_taste[dim]
            action = next(
                (a['action'] for a in adaptation
                 if a.get('taste') == dim and 'action' in a),
                None
            )
            # Hanya tampilkan kalau searah dengan saran
            if abs(diff) > 0.3:
                if action == 'decrease' and diff < 0:
                    direction = "lebih rendah"
                    print(f" → {dim}={ref_taste[dim]:.2f} ({direction} dari resep ini {base_taste[dim]:.2f})")
                elif action == 'increase' and diff > 0:
                    direction = "lebih tinggi"
                    print(f"→ {dim}={ref_taste[dim]:.2f} ({direction} dari resep ini {base_taste[dim]:.2f})")

    # C. Network insight
    ing_text = ' '.join([i['name'] for i in ingredient_list])
    co_insights = get_cooccurrence_insight(
        ing_text,
        source_region=None,
        target_region=target_region,
        handled_ingredients=set()
    )

    if co_insights:
        print(f"\nC. Pola Kombinasi Bahan (Network):")
        for ins in co_insights:
            ing_a, ing_b = ins['pair']
            print(f"- '{ing_a} + {ing_b}' jarang di {target_region} "
                  f"({ins['target_ratio']})")
            print(f" → pertimbangkan untuk disesuaikan")

    # SECTION 5: RESEP SETELAH DISESUAIKAN
    adjusted   = apply_adaptation(ingredient_list, adaptation, base_taste)
    has_changes = any(ing['changed'] for ing in adjusted)

    if has_changes:
        print(f"\n\nRESEP SETELAH DISESUAIKAN")
        for ing in adjusted:
            qty_display = normalize_qty_display(ing['qty_adjusted'], ing['unit'])
            unit = "" if ing['qty_adjusted'] is None else (ing['unit'] or "")
            flag = " ← disesuaikan" if ing['changed'] else ""
            print(f"- {ing['name']:<25} : {qty_display} {unit}{flag}")
    else:
        print(f"\nTidak ada perubahan kuantitas bahan.")

def recommend_custom_api(recipe_name, raw_ingredients, target_region="Jakarta"):
    import io
    from contextlib import redirect_stdout

    f = io.StringIO()
    with redirect_stdout(f):
        recommend_custom(recipe_name, raw_ingredients, target_region=target_region)
    
    return {
        "status": "ok",
        "output": f.getvalue()
    }


# TEST
if __name__ == "__main__":
    recommend_custom(
        recipe_name="Ayam Bakar Madu",
        raw_ingredients="""
            ayam 1 ekor,
            kecap 3 sendok makan,
            gula merah 2 sendok makan,
            2 siung bawang putih,
            jahe secukupnya,
            santan 200 ml,
            cabai rawit 5 buah
        """,
        target_region="jogja"
    )