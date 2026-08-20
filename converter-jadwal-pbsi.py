import json

def format_tgl(tgl_str):
    bulan_map = {
        "Januari": "01", "Februari": "02", "Maret": "03", "April": "04",
        "Mei": "05", "Juni": "06", "Juli": "07", "Agustus": "08",
        "September": "09", "Oktober": "10", "November": "11", "Desember": "12"
    }
    parts = tgl_str.split()
    return f"{parts[2]}-{bulan_map.get(parts[1], '01')}-{parts[0].zfill(2)}"

def generate_schedule(jadwal_file, matches_file, output_file):
    with open(jadwal_file, 'r', encoding='utf-8') as f:
        jadwal_list = json.load(f)
    with open(matches_file, 'r', encoding='utf-8') as f:
        matches_list = json.load(f)

    # 2. Map matches menggunakan KUNCI GABUNGAN: (kategori, id)
    matches_map = {(m['kategori'], m['id']): m for m in matches_list}

    output_data = []
    for entry in jadwal_list:
        tgl_iso = format_tgl(entry.get('tanggal'))
        jam = entry.get('jam', '').replace('.', ':') + ":00"
        
        # Mapping nama kategori agar sinkron dengan matches.json
        kat_input = "GANDA PUTRA" if entry['kelompok'] == "Ganda Putra" else entry['kelompok']
        
        for m_id in entry.get('nomor_pertandingan', []):
            # Cari berdasarkan kategori dan id
            match_data = matches_map.get((kat_input, m_id))
            if match_data:
                output_data.append({
                    "match_id": m_id,
                    "jam": jam,
                    "tanggal": tgl_iso,
                    "kategori": match_data.get('kategori'),
                    "babak": match_data.get('babak'),
                    "partai": f"{match_data.get('p1')} vs {match_data.get('p2')}"
                })
            else:
                print(f"Data tidak ditemukan untuk: {kat_input} ID {m_id}")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
    print(f"Berhasil! {len(output_data)} pertandingan diproses.")

if __name__ == "__main__":
    generate_schedule('jadwal_lengkap.json', 'matches.json', 'new_schedule.json')