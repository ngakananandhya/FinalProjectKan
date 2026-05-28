import re
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Konversi unit + bahan spesifik dari Mustika Rasa
UNIT_BAHAN_TO_GRAM = {
    # SDM
    ("sdm", "beras"):               10,
    ("sdm", "havermout"):           4,
    ("sdm", "susu"):                8,
    ("sdm", "air"):                 8,
    # SDM
    ("sdm", "tepung hunkwee"):      7,
    ("sdm", "tepung terigu"):       6,
    ("sdm", "maizena"):             6,
    ("sdm", "tepung beras"):        5,
    ("sdm", "cacao"):               4,
    ("sdm", "kopi"):                3,
    ("sdm", "gula pasir"):          8,
    ("sdm", "gula pasir halus"):    5,
    ("sdm", "gula merah halus"):    8,
    ("sdm", "gula merah"):          8,
    ("sdm", "soda kue"):            10,
    ("sdm", "tepung susu"):         5,
    ("sdm", "margarin"):            9,
    ("sdm", "minyak goreng"):       9,
    ("sdm", "kacang kering"):       10,
    ("sdm", "garam"):               10,
    ("sdm", "mentega"):             15,
    # GLS
    ("gls", "tepung hunkwee"):      160,
    ("gls", "tepung terigu"):       140,
    ("gls", "maizena"):             140,
    ("gls", "tepung beras"):        125,
    ("gls", "cacao"):               100,
    ("gls", "kopi"):                65,
    ("gls", "gula pasir"):          190,
    ("gls", "gula jawa halus"):     200,
    ("gls", "gula pasir halus"):    125,
    ("gls", "beras"):               200,
    ("gls", "tepung susu"):         25,
    ("gls", "margarin"):            220,
    ("gls", "minyak goreng"):       220,
    ("gls", "kacang kering"):       240,
}

UNIT_TO_GRAM = {
    "kilogram": 1000, "kg": 1000,
    "gram": 1, "gr": 1, "g": 1, "ggm": 1,
    "ons": 100,
    "liter": 1000, "ml": 2, "milliliter": 1, "desiliter": 100,
    "gelas": 240, "glass": 240, "cangkir": 200, "cup": 200,
    "tjingkir": 200, "tjangkir": 200, "cangkir kecil": 120,
    "sendok makan": 10, "tablespoon": 10, "tbsp": 10, "sdm": 10,
    "sendok teh": 3, "teaspoon": 3, "tsp": 3, "sdt": 3,
    "sendok": 10, "sendok takar": 10,
    "kati": 625, "pon": 500,
    "buah": 50, "butir": 5, "biji": 5,
    "siung": 5, "lembar": 2, "helai": 2, "helaian": 2,
    "potong": 30, "iris": 10, "kerat": 10,
    "ruas": 10, "ruas jari": 10, "ruas sedang": 10,
    "batang": 20, "tangkai": 5, "ikat": 50,
    "ekor": 100, "mata": 5,
    "genggam": 30, "pucuk": 10, 
}

# Override per bahan spesifik
INGREDIENT_UNIT_OVERRIDE = {
    "cabai rawit":  {"buah": 2},
    "cabai merah":  {"buah": 15},
    "cabai hijau":  {"buah": 15},
    "cabai":        {"buah": 10},
    "bawang merah": {"buah": 10},
    "bawang putih": {"siung": 5},
    "kemiri":       {"buah": 3,   "butir": 3},
    "telur ayam":   {"buah": 55,  "butir": 55},
    "telur":        {"buah": 55,  "butir": 55},
    "kelapa":       {"buah": 400, "butir": 400},
    "tomat":        {"buah": 80},
}

# Unit kata tanpa nilai numerik
UNIT_KATA = {
    "secukupnya", "sedikit", "sesuai selera", "seperlunya",
    "menurut selera", "sck"
}

def parse_ingredient_input(raw_text):
    """
    Parse satu baris input bahan dari user.
    Contoh input:
      "gula merah 2 sendok makan"
      "2 sendok makan kecap manis"
      "kecap manis secukupnya"
      "ayam"
    Return: {"name": ..., "qty": ..., "unit": ...}
    """
    text = raw_text.strip().lower()

    # 1. Cari angka (int atau float)
    qty       = None
    qty_match = re.search(r'\b(\d+(?:[.,]\d+)?)\b', text)
    if qty_match:
        qty_str = qty_match.group(1).replace(',', '.')
        qty     = float(qty_str)
        # Hapus angka dari text
        text = text[:qty_match.start()] + text[qty_match.end():]
        text = text.strip()

    # 2. Cari unit — terpanjang dulu
    unit      = None
    all_units = sorted(
        list(UNIT_TO_GRAM.keys()) + list(UNIT_KATA),
        key=lambda x: len(x),
        reverse=True
    )
    for u in all_units:
        # Cek sebagai whole word agar 'g' tidak match 'bawang'
        pattern = r'\b' + re.escape(u) + r'\b'
        if re.search(pattern, text):
            unit = u
            text = re.sub(pattern, '', text).strip()
            break

    # 3. Sisanya adalah nama bahan
    name = ' '.join(text.split())

    return {
        "name": name,
        "qty":  qty,
        "unit": unit
    }


def parse_recipe_input(raw_input):
    """
    Parse seluruh input resep dari user.
    Input: string multi-bahan dipisah koma.
    Return: list of {"name", "qty", "unit"}
    """
    lines   = [l.strip() for l in raw_input.split(',') if l.strip()]
    results = []

    for line in lines:
        parsed = parse_ingredient_input(line)
        if parsed['name']:
            results.append(parsed)

    return results

# Kamus normalisasi ejaan lama (Van Ophuijsen) → ejaan modern
# Dibangun berdasarkan kata-kata nyata di dataset Mustika Rasa
EJAAN_MAP = {
    # Frekuensi tinggi
    "djagung":    "jagung",
    "sajur":      "sayur",
    "ajam":       "ayam",
    "katjang":    "kacang",
    "atjar":      "acar",
    "hidjau":     "hijau",
    "rudjak":     "rujak",
    "buntjis":    "buncis",
    "pentjok":    "pencok",
    "petjel":     "pecel",
    "ketjap":     "kecap",
    "tjah":       "cah",
    "djukut":     "jukut",
    "terantjam":  "terancan",
    "djenang":    "jenang",
    "bajam":      "bayam",
    "bidji":      "biji",
    "tjara":      "cara",
    "ritja":      "rica",
    "djalar":     "jalar",
    "djantung":   "jantung",
    "pepaja":     "pepaya",
    "djamur":     "jamur",
    "tjuka":      "cuka",
    "ontjom":     "oncom",
    "djipang":    "jipang",
    "tjampur":    "campur",
    "djadja":     "jaja",
    "kaju":       "kayu",
    "penju":      "penyu",
    "pandjang":   "panjang",
    "djengkol":   "jengkol",
    "djeruk":     "jeruk",
    "wadjik":     "wajik",
    "tjendol":    "cendol",
    "kantjah":    "kancah",
    "djakarta":   "jakarta",
    "ketjambah":  "kecambah",
    "taotjo":     "tauco",
    "widjen":     "wijen",
    "surabaja":   "surabaya",
    "peletjing":  "pelencing",
    "tjendawan":  "cendawan",
    "kentjur":    "kencur",
    "tjumi":      "cumi",
    "batjem":     "bacem",
    "badjak":     "bajak",
    "pletjong":   "plecong",
    "matjan":     "macan",
    "djahe":      "jahe",
    "djongkong":  "jongkong",
    "tjutjur":    "cucur",
    "tjoklat":    "coklat",
    "kedju":      "keju",
    "djeroan":    "jeroan",
    "kretjek":    "krecek",
    "atjeh":      "aceh",
    "tjirebon":   "cirebon",
    "minjak":     "minyak",
    "tautjo":     "tauco",
    "djambu":     "jambu",
    "djawa":      "jawa",
    "djae":       "jahe",
    "gadjah":     "gajah",
    "radjang":    "rajang",
    "radjungan":  "rajungan",
    "mudjair":    "mujair",
    "gedjrot":    "gejrot",
    "badjigur":   "bajigur",
    "tjakalang":  "cakalang",
    "papaja":     "pepaya",
    "sajuran":    "sayuran",
    "idjo":       "ijo",
    "tjereme":    "cerme",
    "serikaja":   "srikaya",
    "srikaja":    "srikaya",
    "tjengkir":   "cengkir",
    "tjeriping":  "ceriping",
    "tjelempungan": "celempungan",
    "tjemplon":   "cemplon",
    "tjenil":     "cenil",
    "tjimplung":  "cimplung",
    "tjotot":     "cotot",
    "tjukok":     "cucuk",
    "tjao":       "cao",
    "tjintjao":   "cincao",
    "patjar":     "pacar",
    "tjandil":    "candil",
    "djubleg":    "jubleg",
    "djadah":     "jadah",
    "sudji":      "suji",
    "kodja":      "koja",
    "tjoan":      "coan",
    "tjap":       "cap",
    "kuntji":     "kunci",
    "tjina":      "cina",
    "sambel": "sambal",
    "sanbel": "sambal",
}


def normalize_query(query):
    """
    Normalisasi input user:
    1. Lowercase
    2. Strip whitespace
    3. Replace kata ejaan lama per kata (whole word match)
    """
    words = query.strip().lower().split()
    normalized = []
    for word in words:
        # Bersihkan tanda baca di sekitar kata
        clean = word.strip('()[].,!?')
        normalized.append(EJAAN_MAP.get(clean, clean))
    return ' '.join(normalized)


# Alias dan singkatan region — hanya untuk 41 region yang ada di baseline
REGION_ALIAS = {
    # Yogyakarta — banyak variasi historis dan populer
    "yogya":          "Yogyakarta",
    "jogja":          "Yogyakarta",
    "jogjakarta":     "Yogyakarta",
    "yogyakarta":     "Yogyakarta",
    "djogja":         "Yogyakarta",
    "djokdja":        "Yogyakarta",
    "djogjakarta":    "Yogyakarta",
    "ygy":            "Yogyakarta",

    # Jakarta
    "jakarta":        "Jakarta",
    "jkt":            "Jakarta",
    "jkrt":           "Jakarta",
    "jaksel":         "Jakarta",
    "jakpus":         "Jakarta",
    "jakbar":         "Jakarta",
    "jaktim":         "Jakarta",
    "jakut":          "Jakarta",

    # Banten
    "banten":         "Banten",
    "btn":            "Banten",

    # Bandung
    "bandung":        "Bandung",
    "bdg":            "Bandung",
    "kota kembang":   "Bandung",

    # Surabaya
    "surabaya":       "Surabaya",
    "sby":            "Surabaya",
    "suroboyo":       "Surabaya",

    # Bali
    "bali":           "Bali",
    "bal":            "Bali",


    # Jawa Tengah
    "jawa tengah":    "Jawa Tengah",
    "jateng":         "Jawa Tengah",

    # Jawa Timur
    "jawa timur":     "Jawa Timur",
    "jatim":          "Jawa Timur",

    # Jawa Barat
    "jawa barat":     "Jawa Barat",
    "jabar":          "Jawa Barat",

    # Malang
    "malang":         "Malang",
    "mlg":            "Malang",

    # Solo
    "solo":           "Solo (Surakarta)",
    "surakarta":      "Solo (Surakarta)",
    "sala":           "Solo (Surakarta)",


    # Padang
    "padang":         "Padang",
    "pdg":            "Padang",
    "minang":         "Padang",

    # Sumatera Barat
    "sumatera barat": "Sumatera Barat",
    "sumbar":         "Sumatera Barat",

    # Sumatera Selatan
    "sumatera selatan": "Sumatera Selatan",
    "sumsel":         "Sumatera Selatan",
    "palembang":      "Palembang",

    # Sumatera Utara
    "sumatera utara": "Sumatera Utara",
    "sumut":          "Sumatera Utara",
    "medan":          "Sumatera Utara",
    "batak":          "Batak",
    "tapanuli":       "Tapanuli",

    # Aceh
    "aceh":           "Aceh",
    "banda aceh":     "Aceh",
    "nanggroe":       "Aceh",

    # Kalimantan
    "kalimantan":     "Kalimantan",
    "kalsel":         "Kalimantan",
    "banjarmasin":    "Banjarmasin",
    "banjar":         "Banjarmasin",

    # Sulawesi Selatan
    "sulawesi selatan": "Sulawesi Selatan",
    "sulsel":         "Sulawesi Selatan",
    "makassar":       "Makassar",
    "ujung pandang":  "Makassar",
    "bugis":          "Bugis",
    "toraja":         "Toraja",

    # Sulawesi Utara
    "sulawesi utara": "Sulawesi Utara",
    "sulut":          "Sulawesi Utara",
    "manado":         "Manado",
    "minahasa":       "Manado",

    # Maluku & Papua
    "maluku":         "Maluku & Papua",
    "ambon":          "Ambon",
    "papua":          "Papua",
    "irian":          "Papua",

    # Lombok & Nusa Tenggara
    "lombok":         "Lombok",
    "sumbawa":        "Sumbawa",
    "timor":          "Timor",
    "flores":         "Flores",
    "ntt":            "Timor",
    "ntb":            "Lombok",

    # Kota-kota lain di baseline
    "rembang":        "Rembang",
    "purwokerto":     "Purwokerto",
    "banyumas":       "Banyumas",
    "wonosobo":       "Wonosobo",
    "tegal":          "Tegal",
    "madiun":         "Madiun",
    "madura":         "Madura",
    "brebes":         "Brebes",
    "cianjur":        "Cianjur",
    "cirebon":        "Cirebon",
    "bogor":          "Bogor",
    "sukabumi":       "Sukabumi",
    "lampung":        "Lampung",
    "manado":         "Manado",
    "gorontalo":      "Manado",
    "ambon":          "Ambon",
    "ternate":        "Maluku & Papua",
}

def normalize_region(query):
    """
    Normalisasi input region dari user.
    1. Lowercase + strip
    2. Cek alias dict
    3. Return nama region yang valid, atau None
    """
    q = query.strip().lower()
    return REGION_ALIAS.get(q, None)

def fuzzy_match_region(query, valid_regions, threshold_auto=80, threshold_suggest=60):
    """
    Fuzzy match region input ke daftar region valid.
    Return: (matched_region, score, action)
    action: 'match' (langsung pakai), 'suggest' (tanya user), 'none' (tidak ketemu)
    """
    from rapidfuzz import process

    result = process.extractOne(query, valid_regions)
    if result is None:
        return None, 0, 'none'

    matched, score, _ = result

    if score >= threshold_auto:
        return matched, score, 'match'
    elif score >= threshold_suggest:
        return matched, score, 'suggest'
    else:
        return None, score, 'none'


def fuzzy_match_recipe(query, recipe_names, threshold_auto=80, threshold_suggest=60):
    """
    Fuzzy match nama resep input ke daftar nama resep di database.
    """
    from rapidfuzz import process

    result = process.extractOne(query, recipe_names)
    if result is None:
        return None, 0, 'none'

    matched, score, _ = result

    if score >= threshold_auto:
        return matched, score, 'match'
    elif score >= threshold_suggest:
        return matched, score, 'suggest'
    else:
        return None, score, 'none'

# TEST
if __name__ == "__main__":
    tests = [
        "ajam goreng",
        "sajur asam",
        "katjang hidjau",
        "rudjak buah",
        "petjel lele",
        "djagung manis",
        "ketjap manis",
        "AJAM BETUTU",
    ]
    print("=== TEST NORMALISASI EJAAN ===")
    for t in tests:
        print(f"  '{t}' → '{normalize_query(t)}'")

def normalize_qty_display(qty, unit):
    """
    Normalisasi kuantitas ke angka yang lebih natural untuk ditampilkan.
    Unit cacahan → kelipatan 0.5
    Unit volume/berat → kelipatan 0.25
    Lalu konversi ke representasi pecahan.
    """
    if qty is None:
        return "secukupnya"

    UNIT_CACAHAN = {
        "buah", "biji", "butir", "ekor", "siung", "lembar",
        "helai", "helaian", "potong", "iris", "ikat", "batang",
        "tangkai", "mata", "pucuk", "ruas", "ruas jari",
        "ruas sedang", "genggam", "piece", "clove", "leaf",
        "stalk", "bunch", "slice", "segment"
    }

    unit_clean = (unit or "").lower().strip()

    # Tentukan kelipatan berdasarkan jenis unit
    if unit_clean in UNIT_CACAHAN:
        step = 0.5
    else:
        step = 0.25

    # Bulatkan ke kelipatan terdekat
    rounded = round(round(qty / step) * step, 2)

    # Pastikan tidak nol
    if rounded == 0:
        rounded = step

    # Konversi ke representasi pecahan
    FRACTION_MAP = {
        0.25: "1/4",
        0.5:  "1/2",
        0.75: "3/4",
    }

    whole = int(rounded)
    decimal = round(rounded - whole, 2)

    if decimal == 0:
        display = str(whole)
    elif whole == 0:
        display = FRACTION_MAP.get(decimal, str(rounded))
    else:
        frac = FRACTION_MAP.get(decimal, str(decimal))
        display = f"{whole}{frac}"

    return display


if __name__ == "__main__":
    tests = [
        'bawang merah',
        'bawang merah 5 buah',
        '200 gram santan',
        'garam secukupnya',
        'daun jeruk purut 3 lembar',
    ]
    for t in tests:
        result = parse_ingredient_input(t)
        print(f'  {t:<30} → name={result["name"]:<20} qty={str(result["qty"]):<8} unit={result["unit"]}')



