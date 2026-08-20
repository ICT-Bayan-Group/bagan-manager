import json
from collections import defaultdict

def generate_multi_category_config(jadwal_data, matches_file, output_file):
    with open(matches_file, 'r', encoding='utf-8') as f:
        matches = json.load(f)
    
    # 1. Map ID ke data pertandingan (kategori & babak)
    id_to_match = {m['id']: m for m in matches}
    
    # 2. Map ID ke info tanggal dari jadwal
    id_to_jadwal = {}
    for slot in jadwal_data:
        for mid in slot.get('nomor_pertandingan', []):
            id_to_jadwal[mid] = {'tanggal': slot['tanggal']}
            
    # 3. Kumpulkan konfigurasi unik
    configs = {}
    for mid, j_info in id_to_jadwal.items():
        if mid in id_to_match:
            match = id_to_match[mid]
            key = (match['kategori'], j_info['tanggal'], match['babak'])
            
            if key not in configs:
                # Venue otomatis berdasarkan kategori
                venue = "DOME" if match['kategori'] == "GANDA PUTRA" else "HEVINDO ARENA"
                configs[key] = {
                    "kategori": match['kategori'],
                    "tanggal": j_info['tanggal'],
                    "jam_mulai": "08:00",
                    "jam_selesai": "12:00",
                    "babak": match['babak'],
                    "venue": venue,
                    "lapangan": ["Court-1"]
                }
                
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(list(configs.values()), f, indent=4, ensure_ascii=False)

# Data jadwal yang Anda berikan
jadwal_data = [...] # (Masukkan list jadwal Anda di sini)

generate_multi_category_config(jadwal_data, 'matches.json', 'final_multi_config.json')