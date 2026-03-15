import json
import math
import glob
import os

# --- FUNGSI 1: GENERATOR STRUKTUR ---
def generate_bracket(players, kategori):
    n = len(players)
    if n == 0: return []
    
    power = math.ceil(math.log2(n))
    num_slots = 2**power
    full_players = players + ["BYE"] * (num_slots - n)
    
    matches_per_round = []
    temp_slots = num_slots
    while temp_slots > 1:
        temp_slots //= 2
        matches_per_round.append(temp_slots)
        
    round_offsets = [1]
    for i in range(len(matches_per_round) - 1):
        round_offsets.append(round_offsets[i] + matches_per_round[i])
        
    all_matches = []
    current_match_id = 1
    
    for r_idx, num_matches in enumerate(matches_per_round):
        if num_matches == 1: round_name = "FINAL"
        elif num_matches == 2: round_name = "SEMI FINAL"
        elif num_matches == 4: round_name = "PEREMPAT FINAL"
        else: round_name = f"R{num_matches * 2}"
        
        for m_idx in range(num_matches):
            this_id = current_match_id
            
            if num_matches == 1: side = "CENTER"
            elif m_idx < num_matches // 2: side = "LEFT"
            else: side = "RIGHT"
                
            if r_idx < len(matches_per_round) - 1:
                target_id = round_offsets[r_idx + 1] + math.floor(m_idx / 2)
                pemenang_ke = f"M{target_id}"
            else:
                pemenang_ke = "JUARA"
                
            p1 = full_players[m_idx * 2] if r_idx == 0 else "TBD"
            p2 = full_players[m_idx * 2 + 1] if r_idx == 0 else "TBD"
            
            all_matches.append({
                "id": this_id,
                "p1": p1,
                "p2": p2,
                "kategori": kategori,
                "babak": round_name,
                "side": side,
                "pemenang_ke": pemenang_ke
            })
            current_match_id += 1
            
    return all_matches

# --- FUNGSI 2: LOGIKA MAJUKAN BYE ---
def auto_advance_byes(matches):
    """Memajukan pemain yang lawannya BYE di Babak 1"""
    changed = True
    while changed: # Ulangi jika ada perubahan (untuk BYE beruntun)
        changed = False
        for m in matches:
            p1, p2 = m['p1'], m['p2']
            target_match_id_str = m['pemenang_ke']
            
            winner = None
            if p2 == "BYE" and p1 != "TBD": winner = p1
            elif p1 == "BYE" and p2 != "TBD": winner = p2
            
            if winner and target_match_id_str != "JUARA":
                target_id = int(target_match_id_str.replace("M", ""))
                for target_match in matches:
                    if target_match['id'] == target_id:
                        # Masukkan ke P1 jika ID asal ganjil, P2 jika genap
                        if m['id'] % 2 != 0:
                            if target_match['p1'] != winner:
                                target_match['p1'] = winner
                                changed = True
                        else:
                            if target_match['p2'] != winner:
                                target_match['p2'] = winner
                                changed = True
                        break
    return matches

def main():
    print("=== GENERATOR BAGAN KIRI-KANAN + AUTO BYE ===")
    semua_pertandingan = []
    
    file_teams = glob.glob("teams_*.json")
    if not file_teams:
        print("Tidak ditemukan file teams_*.json!")
        return

    for nama_file in file_teams:
        kategori_raw = nama_file.replace("teams_", "").replace(".json", "")
        nama_kategori = kategori_raw.replace("_", " ").upper()
        
        try:
            with open(nama_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                list_peserta = data.get('nama_tim', [])
                
                if list_peserta:
                    print(f"Memproses: {nama_kategori} ({len(list_peserta)} Peserta)")
                    partai = generate_bracket(list_peserta, nama_kategori)
                    # Jalankan auto-advance khusus untuk kategori ini
                    partai = auto_advance_byes(partai)
                    semua_pertandingan.extend(partai)
        except Exception as e:
            print(f" Error pada {nama_file}: {e}")

    # Simpan hasil akhir
    with open('matches.json', 'w', encoding='utf-8') as f:
        json.dump(semua_pertandingan, f, indent=4)
    print("\n✅ BERHASIL! matches.json siap digunakan.")

if __name__ == "__main__":
    main()