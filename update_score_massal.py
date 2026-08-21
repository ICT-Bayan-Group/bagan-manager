import os
import sys
import json
import sqlite3
import subprocess
import pandas as pd

DB_PATH = 'skor.db'
MATCHES_PATH = 'matches.json'
GENERATE_SCRIPT = 'generate_main.py'

def process_single_score(match_id, kategori, skor_p1, skor_p2, winner, conn, all_matches):
    """
    Memproses logika update skor tunggal pada DB & struktur bracket memory
    """
    match_id_str = str(match_id)
    skor_p1 = int(skor_p1)
    skor_p2 = int(skor_p2)

    cursor = conn.cursor()
    cursor.execute('''
        SELECT skor_p1, skor_p2 FROM tabel_skor 
        WHERE match_id = ? AND kategori = ?
    ''', (match_id_str, kategori))
    existing = cursor.fetchone()

    # Cek idempotensi (jika skor sama persis, abaikan)
    if existing and existing[0] == skor_p1 and existing[1] == skor_p2:
        return False 

    # Simpan / Update SQLite
    conn.execute('''
        INSERT OR REPLACE INTO tabel_skor (kategori, match_id, skor_p1, skor_p2, winner)
        VALUES (?, ?, ?, ?, ?)
    ''', (kategori, match_id_str, skor_p1, skor_p2, winner))
    conn.commit()

    # Update Logika Bagan di Memory (matches.json)
    if all_matches:
        curr = next((
            m for m in all_matches 
            if str(m['id']) == match_id_str and str(m['kategori']).strip().lower() == str(kategori).strip().lower()
        ), None)
        
        if curr:
            curr['skor_akhir'] = f"{skor_p1} - {skor_p2}"
            curr['pemenang'] = winner
            
            next_target = curr.get('pemenang_ke')
            if next_target and next_target != "JUARA":
                try:
                    t_id = int(str(next_target).upper().replace('M', ''))
                    target = next((
                        m for m in all_matches 
                        if m['id'] == t_id and str(m['kategori']).strip().lower() == str(kategori).strip().lower()
                    ), None)
                    
                    if target:
                        if target['p1'] != winner and target['p2'] != winner:
                            if target['p1'] in ["TBD", ""]:
                                target['p1'] = winner
                            else:
                                target['p2'] = winner
                except ValueError:
                    pass
    return True


def process_mass_score_excel(file_input):
    """
    Menerima path file Excel (.xlsx/.xls) atau file-like object dari Flask upload.
    """
    try:
        df = pd.read_excel(file_input)
        required_columns = ['kategori', 'match_id', 'skor_p1', 'skor_p2']
        
        for col in required_columns:
            if col not in df.columns:
                return {
                    "status": "error", 
                    "message": f"Kolom wajib '{col}' tidak ditemukan di Excel!"
                }

        all_matches = []
        if os.path.exists(MATCHES_PATH):
            with open(MATCHES_PATH, 'r', encoding='utf-8') as f:
                all_matches = json.load(f)

        updated_count = 0

        with sqlite3.connect(DB_PATH) as conn:
            for _, row in df.iterrows():
                # Lewati jika ada kolom kosong atau skor seri
                if pd.isna(row['skor_p1']) or pd.isna(row['skor_p2']) or pd.isna(row['kategori']) or pd.isna(row['match_id']):
                    continue
                
                kat = str(row['kategori']).strip()
                m_id = row['match_id']
                s1 = int(row['skor_p1'])
                s2 = int(row['skor_p2'])

                if s1 == s2:
                    continue

                curr_match = next((
                    m for m in all_matches 
                    if str(m['id']) == str(m_id) and str(m['kategori']).strip().lower() == kat.lower()
                ), None)

                if not curr_match:
                    continue

                p1 = curr_match.get('p1', '')
                p2 = curr_match.get('p2', '')
                winner = p1 if s1 > s2 else p2

                is_changed = process_single_score(m_id, curr_match['kategori'], s1, s2, winner, conn, all_matches)
                if is_changed:
                    updated_count += 1

        # Jika ada perubahan, simpan matches.json & regenerasi jadwal
        if updated_count > 0:
            with open(MATCHES_PATH, 'w', encoding='utf-8') as f:
                json.dump(all_matches, f, indent=4)

            try:
                subprocess.run([sys.executable, GENERATE_SCRIPT], check=True)
            except Exception as gen_err:
                print(f"⚠️ Gagal mengeksekusi {GENERATE_SCRIPT}: {gen_err}")

        return {
            "status": "success",
            "updated_count": updated_count,
            "message": f"✅ Berhasil memperbarui {updated_count} pertandingan dari Excel!"
        }

    except Exception as e:
        return {"status": "error", "message": f"❌ Error saat memproses Excel: {str(e)}"}


# Executable CLI Mode
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Penggunaan via CLI: python update_score_massal.py <path_file_excel.xlsx>")
        sys.exit(1)

    excel_file = sys.argv[1]
    if not os.path.exists(excel_file):
        print(f"File '{excel_file}' tidak ditemukan!")
        sys.exit(1)

    print(f"Memproses update skor massal dari: {excel_file} ...")
    result = process_mass_score_excel(excel_file)
    print(result["message"])