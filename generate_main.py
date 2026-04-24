import json
from datetime import datetime, timedelta
import os

def load_json(filename):
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except Exception as e:
        return []

def save_json(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def parse_time_flexible(date_str, time_str):
    # 1. Bersihkan spasi di awal/akhir
    date_str = date_str.strip() if date_str else ""
    time_str = time_str.strip() if time_str else ""

    # 2. Jika tanggal kosong, jangan dipaksakan parse (return None)
    if not date_str or not time_str:
        return None

    # 3. Pastikan jam punya format HH:MM:SS
    if len(time_str.split(':')) == 2:
        time_str += ":00"
    
    # Gabungkan
    full_str = f"{date_str} {time_str}"
    
    # 4. Coba parse dengan format yang didukung simulator (Strip spasi ganda juga)
    full_str = " ".join(full_str.split()) 
    
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(full_str, fmt)
        except ValueError:
            continue
            
    return None

def generate_schedule():
    configs = load_json('config.json')
    matches = load_json('matches.json')
    
    if not configs or not matches:
        print("❌ Data config atau matches kosong.")
        return

    # 1. BUAT KOTAK-KOTAK SLOT DARI CONFIG (Hanya C1 & C2)
    slots_by_category = {}
    for config in configs:
        kat = config['kategori'].strip().lower()
        babak = config['babak'].strip().lower()
        key = (kat, babak)
        
        if key not in slots_by_category:
            slots_by_category[key] = []
            
        start_time = parse_time_flexible(config['tanggal'], config['jam_mulai'])
        end_time = parse_time_flexible(config['tanggal'], config['jam_selesai'])
        
        curr = start_time
        while curr < end_time:
            for court in config['lapangan']:
                slots_by_category[key].append({
                    "tanggal": config['tanggal'],
                    "jam": curr.strftime("%H:%M:%S"),
                    "venue": config['venue'],
                    "court": court.strip()
                })
            curr += timedelta(minutes=30)
            
    # 2. ISI KOTAK SLOT DENGAN PERTANDINGAN
    final_schedule = []
    player_occupancy = {}
    
    matches_grouped = {}
    for m in matches:
        if m['p1'] == "BYE" or m['p2'] == "BYE": continue
            
        kat = m['kategori'].strip().lower()
        babak = m['babak'].strip().lower()
        key = (kat, babak)
        if key not in matches_grouped: matches_grouped[key] = []
        matches_grouped[key].append(m)
        
    print("\n=== LAPORAN PENGISIAN JADWAL ===")
    for key, cat_matches in matches_grouped.items():
        kat_nama, babak_nama = key
        available_slots = slots_by_category.get(key, [])
        
        print(f"{kat_nama.upper()} ({babak_nama.upper()}): {len(cat_matches)} Partai -> Tersedia {len(available_slots)} Slot Lapangan")
        
        for i, match in enumerate(cat_matches):
            if i < len(available_slots):
                cell = available_slots[i]
                
                time_key = f"{cell['tanggal']}_{cell['jam']}"
                players = [match['p1'], match['p2']]
                conflict = any(p in player_occupancy.get(time_key, []) for p in players)
                
                final_schedule.append({
                    "match_id": match['id'],
                    "jam": cell['jam'],
                    "tanggal": cell['tanggal'],
                    "venue": cell['venue'],
                    "court": cell['court'],
                    "kategori": match['kategori'],
                    "babak": match['babak'],
                    "partai": f"{match['p1']} vs {match['p2']}",
                    "status": "CONFLICT" if conflict else "OK"
                })
                
                if time_key not in player_occupancy: player_occupancy[time_key] = []
                player_occupancy[time_key].extend(players)
            else:
                print(f"KEKURANGAN LAPANGAN! Match M.{match['id']} TIDAK kebagian jadwal.")
                
    save_json(final_schedule, 'schedule.json')
    print(f"\n SELESAI! {len(final_schedule)} partai masuk ke schedule.json")


def process_byes(matches):
    changed = False
    for m in matches:
        p1 = m.get('p1', 'TBD')
        p2 = m.get('p2', 'TBD')
        pemenang_ke = m.get('pemenang_ke')

        # LOGIKA UTAMA: 
        # Jika p2 adalah BYE dan p1 bukan TBD, maka pemenangnya p1
        winner = None
        if p2 == "BYE" and p1 != "TBD":
            winner = p1
        # Sebaliknya, jika p1 adalah BYE, pemenangnya p2
        elif p1 == "BYE" and p2 != "TBD":
            winner = p2

        # Jika ditemukan pemenang otomatis karena BYE
        if winner and pemenang_ke and pemenang_ke != "JUARA":
            # Ambil ID pertandingan berikutnya (contoh: "M65" jadi 65)
            next_id = int(str(pemenang_ke).replace("M", "").strip())
            
            for target in matches:
                if target['id'] == next_id:
                    # Aturan penempatan di babak selanjutnya:
                    # Jika ID match sekarang GANJIL -> Masuk ke P1 di match depan
                    # Jika ID match sekarang GENAP  -> Masuk ke P2 di match depan
                    if m['id'] % 2 != 0:
                        if target['p1'] != winner:
                            target['p1'] = winner
                            changed = True
                    else:
                        if target['p2'] != winner:
                            target['p2'] = winner
                            changed = True
                    break
    return matches, changed

if __name__ == "__main__":
    generate_schedule()