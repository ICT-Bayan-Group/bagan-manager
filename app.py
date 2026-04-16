from flask import Flask, request, jsonify, render_template, make_response, after_this_request
from flask_cors import CORS 
import json
import subprocess
import pandas as pd
import os
import math
import sqlite3
import jwt
import datetime
from functools import wraps

app = Flask(__name__)
# Izinkan semua domain (atau domain tertentu) dan izinkan header 'Authorization'
CORS(app, supports_credentials=True, allow_headers=["Content-Type", "Authorization"])
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SECRET_KEY'] = 'kunci_rahasia_bagan_2026' # Pastikan ini sama di semua fungsi
CONFIG_FILE = 'config.json'

app.config['SECRET_KEY'] = 'iasdhfiuasfuiasyfiusi48756324772345kjh$#@$#fksdjkfg'

# 1. SATPAM VERSI COOKIE
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('adminToken')
        
        # Daftar halaman admin
        halaman_admin = ['/admin', '/pendaftaran', '/manage-categories', '/jadwal', '/run-schedule', '/reset-all']
        
        if not token:
            if request.path in halaman_admin:
                return render_template('login.html', error="Silakan login dahulu.")
            return jsonify({'message': 'Akses ditolak. Token tidak ditemukan!'}), 401
            
        try:
            # 1. Validasi Token
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = data['user']

            # 2. LOGIKA IDLE TIMEOUT: Perbarui durasi cookie setiap ada aktivitas
            @after_this_request
            def refresh_cookie(response):
                # Set durasi baru, misal 1800 detik (30 Menit)
                # Setiap kamu klik menu, durasi 30 menit ini akan dihitung dari awal lagi
                response.set_cookie('adminToken', token, httponly=True, max_age=1800)
                return response

        except Exception:
            if request.path in halaman_admin:
                return render_template('login.html', error="Sesi habis. Silakan login ulang.")
            return jsonify({'message': 'Token tidak valid/kedaluwarsa!'}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

# 2. ENDPOINT LOGIN (Simpan ke Cookie)
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if data and data.get('username') == 'admin' and data.get('password') == '12345':
        token = jwt.encode({
            'user': data['username'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm="HS256")
        
        # Buat response sukses
        resp = make_response(jsonify({'message': 'Login berhasil'}))
        # Simpan token ke Cookie browser (httponly=True membuatnya sangat aman dari hacker)
        resp.set_cookie('adminToken', token, httponly=True) 
        return resp
        
    return jsonify({'message': 'Username atau password salah!'}), 401

# (Lanjutkan dengan rute /get-categories dan /simpan-tim yang juga pakai @token_required)

# 1. Database hanya untuk menyimpan skor (Buku Catatan)
def init_skor_db():
    conn = sqlite3.connect('skor.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tabel_skor (
            kategori TEXT,
            match_id INTEGER,
            skor_p1 INTEGER,
            skor_p2 INTEGER,
            winner TEXT,
            PRIMARY KEY (kategori, match_id)
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return render_template('login.html')
# --------------------------

@app.route('/logout')
def logout():
    resp = make_response(render_template('login.html', error="Anda telah berhasil keluar."))
    # Menghapus cookie dengan cara menimpa isinya dan set durasi ke 0
    resp.set_cookie('adminToken', '', expires=0)
    return resp

@app.route('/admin')
@token_required
def tampil_adminl(current_user):
    return render_template('admin.html')


@app.route('/admin/view-database')
def view_database():
    import sqlite3
    conn = sqlite3.connect('skor.db')
    conn.row_factory = sqlite3.Row  # Supaya data bisa dipanggil pakai nama kolom
    cursor = conn.cursor()
    
    try:
        # Mengambil semua data dari tabel_skor
        rows = cursor.execute('SELECT * FROM tabel_skor ORDER BY kategori, match_id ASC').fetchall()
    except sqlite3.OperationalError:
        rows = [] # Jika tabel belum ada atau kosong
        
    conn.close()
    return render_template('view_database.html', rows=rows)

@app.route('/admin/input-skor')
def input_skor_page():
    if not os.path.exists('matches.json'):
        return "File matches.json tidak ditemukan."
    with open('matches.json', 'r') as f:
        matches = json.load(f)
    categories = sorted(list(set(m['kategori'] for m in matches)))
    return render_template('input_skor.html', categories=categories)


@app.route('/jadwal')
@token_required
def tampil_jadwal(current_user):
    return render_template('jadwal.html')
# --------------------------

@app.route('/stats')
def tampil_stats():
    return render_template('stats_summary.html')

# Rute untuk menampilkan halaman jadwal
@app.route('/lihat-jadwal')
def view_schedule():
    return render_template('lihat_jadwal.html')

@app.route('/skor-pertandingan')
def view_skor_pertandingan():
    return render_template('hasil_skor_pertandingan.html')

@app.route('/simulasi')
def simulasi():
    return render_template('simulator.html')

@app.route('/pendaftaran')
@token_required
def pendaftaran(current_user):
    return render_template('pendaftaran.html')



@app.route('/get-categories', methods=['GET'])
#@token_required
def get_categories():
    try:
        # Mencari file categories.json
        with open('categories.json', 'r') as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        # Jika file tidak ada, kirim daftar kosong agar tidak error
        return jsonify({"categories": []})

@app.route('/get-config', methods=['GET'])
def get_config():
    with open(CONFIG_FILE, 'r') as f:
        return jsonify(json.load(f))
    
@app.route('/get-schedule')
def get_schedule():
    try:
        with open('schedule.json', 'r') as f:
            return jsonify(json.load(f))
    except:
        return jsonify([])


#Simpan config.json sekalian jalankan generate_main.py Untuk menjadikan schedule.json
@app.route('/save-config', methods=['POST'])
def save_config():
    new_config = request.json
    with open(CONFIG_FILE, 'w') as f:
        json.dump(new_config, f, indent=4)
    
    try:
        subprocess.run(["python3", "generate_main.py"], check=True)
        return jsonify({"message": "Config tersimpan dan jadwal otomatis diperbarui!"})
    except Exception as e:
        return jsonify({"message": f"Gagal update jadwal: {str(e)}"}), 500
    

import subprocess

@app.route('/run-bagan', methods=['POST'])
def execute_bagan():
    try:
        # Menjalankan script bagan.py
        result = subprocess.run(["python3", "bagan.py"], capture_output=True, text=True)
        
        if result.returncode == 0:
            return jsonify({"message": "✅ Bagan berhasil dibuat! File matches.json telah diperbarui."})
        else:
            return jsonify({"message": f"❌ Gagal: {result.stderr}"}), 500
    except Exception as e:
        return jsonify({"message": f"❌ Error: {str(e)}"}), 500
    

@app.route('/run-schedule', methods=['POST'])
@token_required
def execute_generate(current_user):
    try:
        # Menjalankan script bagan.py
        result = subprocess.run(["python3", "generate_main.py"], capture_output=True, text=True)
        
        if result.returncode == 0:
            return jsonify({"message": "✅ Penjadwalan berhasil dibuat! File schedule.json telah diperbarui."})
        else:
            return jsonify({"message": f"❌ Gagal: {result.stderr}"}), 500
    except Exception as e:
        return jsonify({"message": f"❌ Error: {str(e)}"}), 500
    

import subprocess

@app.route('/reset-all', methods=['POST'])
@token_required
def reset_all(current_user):
    data = request.json
    password_input = data.get('password')
    
    # Password admin
    ADMIN_PASSWORD = "12345" 

    if password_input != ADMIN_PASSWORD:
        return jsonify({"message": "❌ Password Salah! Akses ditolak."}), 403

    try:
        # Mengeksekusi file reset.py
        # input="RESET" dikirimkan untuk mengisi otomatis prompt konfirmasi di reset.py
        result = subprocess.run(
            ["python3", "reset.py"], 
            input="RESET", 
            capture_output=True, 
            text=True
        )

        if result.returncode == 0:
            return jsonify({
                "message": "✅ Sistem berhasil di-reset melalui eksekusi reset.py.",
                "output": result.stdout
            })
        else:
            # Jika script reset.py mengembalikan error
            return jsonify({
                "message": "❌ Gagal mengeksekusi reset.py",
                "error": result.stderr
            }), 500

    except Exception as e:
        return jsonify({"message": f"❌ Error sistem: {str(e)}"}), 500


@app.route('/upload-matches-excel', methods=['POST'])
def upload_matches_excel():
    if 'file' not in request.files:
        return jsonify({"message": "Tidak ada file yang dipilih"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "Nama file kosong"}), 400

    # Mendukung format .xls dan .xlsx
    if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        try:
            # Membaca file excel menggunakan pandas
            df = pd.read_excel(file)
            
            # Pastikan kolom yang dibutuhkan ada
            required_columns = ['p1', 'p2', 'kategori']
            if not all(col in df.columns for col in required_columns):
                return jsonify({"message": "Kolom harus berisi: p1, p2, kategori"}), 400
            
            # Konversi dataframe ke list of dictionary
            matches = []
            for index, row in df.iterrows():
                matches.append({
                    "id": index + 1,
                    "p1": str(row['p1']),
                    "p2": str(row['p2']),
                    "kategori": str(row['kategori'])
                })
            
            # Simpan ke matches.json
            with open('matches.json', 'w') as f:
                json.dump(matches, f, indent=4)
                
            return jsonify({"message": f"Berhasil mengimpor {len(matches)} partai dari Excel!"})
        
        except Exception as e:
            return jsonify({"message": f"Gagal memproses file: {str(e)}"}), 500
    
    return jsonify({"message": "Format file harus .xls atau .xlsx"}), 400

@app.route('/upload-config-excel', methods=['POST'])
def upload_config_excel():
    file = request.files['file']
    if not (file and file.filename.endswith(('.xlsx', '.xls'))):
        return jsonify({"message": "Format file salah"}), 400

    try:
        df = pd.read_excel(file)
        new_configs = []
        conflicts = []

        # 1. Konversi data Excel ke format list
        for _, row in df.iterrows():
            new_configs.append({
                "kategori": str(row['kategori']),
                "tanggal": str(row['tanggal']).split()[0], # Ambil tanggal saja
                "jam_mulai": str(row['jam_mulai']),
                "jam_selesai": str(row['jam_selesai']),
                "venue": str(row['venue']).strip(),
                "lapangan": [l.strip() for l in str(row['lapangan']).split(',')]
            })

        # 2. Cek Bentrok antar baris di dalam file tersebut
        for i in range(len(new_configs)):
            for j in range(i + 1, len(new_configs)):
                c1 = new_configs[i]
                c2 = new_configs[j]

                # Jika Tanggal, Venue, dan Lapangan ada yang beririsan
                if c1['tanggal'] == c2['tanggal'] and c1['venue'] == c2['venue']:
                    irisan_lapangan = set(c1['lapangan']) & set(c2['lapangan'])
                    if irisan_lapangan:
                        # Cek Irisan Waktu
                        if c1['jam_mulai'] < c2['jam_selesai'] and c2['jam_mulai'] < c1['jam_selesai']:
                            conflicts.append(f"Bentrok: {c1['kategori']} & {c2['kategori']} di {list(irisan_lapangan)}")

        if conflicts:
            return jsonify({
                "message": "Gagal simpan! Ditemukan jadwal bentrok dalam file.",
                "conflicts": conflicts
            }), 400

        # 3. Jika tidak ada bentrok, simpan ke config.json
        with open('config.json', 'w') as f:
            json.dump(new_configs, f, indent=4)
        
        return jsonify({"message": "Jadwal berhasil diimpor tanpa bentrok!"})

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/lihat-bagan')
def lihat_bagan_page():
    return render_template('bagan.html')

@app.route('/get-matches')
def get_matches_data():
    if not os.path.exists('matches.json'):
        return jsonify([])
    
    # A. Baca Struktur dari JSON (Nyawa Bagan)
    with open('matches.json', 'r') as f:
        matches = json.load(f)

    # B. Ambil Skor dari DB (Catatan Skor)
    conn = sqlite3.connect('skor.db')
    conn.row_factory = sqlite3.Row
    skor_rows = conn.execute('SELECT * FROM tabel_skor').fetchall()
    conn.close()

    # C. Tempelkan Skor ke JSON sebelum dikirim ke Browser
    # Kita buat map agar cepat: "KATEGORI_ID" -> Data Skor
    dict_skor = {f"{row['kategori']}_{row['match_id']}": row for row in skor_rows}
    
    for m in matches:
        key = f"{m['kategori']}_{m['id']}"
        if key in dict_skor:
            m['skor_p1'] = dict_skor[key]['skor_p1']
            m['skor_p2'] = dict_skor[key]['skor_p2']
            m['winner'] = dict_skor[key]['winner']
            m['status'] = 'COMPLETED'
        else:
            m['skor_p1'] = 0
            m['skor_p2'] = 0
            m['status'] = 'PENDING'

    return jsonify(matches)

@app.route('/api/get-ready-matches/<kategori>')
def get_ready_matches(kategori):
    try:
        if not os.path.exists('schedule.json'):
            return jsonify([])

        with open('schedule.json', 'r') as f:
            schedules = json.load(f)

        # Gunakan kategori huruf besar agar cocok dengan schedule.json
        kat_upper = kategori.upper()
        
        ready_matches = []
        for s in schedules:
            if s['kategori'].upper() == kat_upper:
                # Pastikan partai bukan TBD atau BYE
                if "TBD" not in s['partai'].upper() and "BYE" not in s['partai'].upper():
                    # Pecah nama pemain
                    sep = ' vs ' if ' vs ' in s['partai'] else ' VS '
                    players = s['partai'].split(sep)
                    
                    ready_matches.append({
                        "id": s['match_id'],
                        "p1": players[0].strip(),
                        "p2": players[1].strip() if len(players) > 1 else "TBD"
                    })
        
        return jsonify(ready_matches)
    except Exception as e:
        print(f"Error: {e}")
        return jsonify([])
 

@app.route('/update-skor', methods=['POST'])
def update_skor():
    data = request.json
    # Perbaikan: Mengambil 'match_id' (dari HTML baru) atau 'id' (dari HTML lama)
    match_id = data.get('match_id') or data.get('id') 
    kategori = data.get('kategori')
    skor_p1 = data.get('skor_p1')
    skor_p2 = data.get('skor_p2')
    winner = data.get('winner')

    if not match_id or not kategori:
        return jsonify({"status": "error", "message": "ID Match atau Kategori tidak ditemukan"}), 400

    # Simpan ke Database SQLite
    conn = sqlite3.connect('skor.db')
    conn.execute('''
        INSERT OR REPLACE INTO tabel_skor (kategori, match_id, skor_p1, skor_p2, winner)
        VALUES (?, ?, ?, ?, ?)
    ''', (kategori, match_id, skor_p1, skor_p2, winner))
    conn.commit()
    conn.close()

    # Update matches.json untuk Bagan
    if os.path.exists('matches.json'):
        with open('matches.json', 'r') as f:
            all_matches = json.load(f)
        
        curr = next((m for m in all_matches if m['id'] == match_id and m['kategori'] == kategori), None)
        if curr:
            next_target = curr.get('pemenang_ke')
            if next_target and next_target != "JUARA":
                t_id = int(str(next_target).replace('M', ''))
                target = next((m for m in all_matches if m['id'] == t_id and m['kategori'] == kategori), None)
                if target:
                    if target['p1'] == "TBD" or target['p1'] == "": target['p1'] = winner
                    else: target['p2'] = winner

            with open('matches.json', 'w') as f:
                json.dump(all_matches, f, indent=4)

        #subprocess.run(["python3", "generate_main.py"], check=True)
    return jsonify({"status": "success", "message": "Skor berhasil diperbarui!"})

# --- RUTE LAINNYA ---

import random # Pastikan import random ada di bagian paling atas file

import random
import math

def get_priority_positions(S):
    """Menghasilkan daftar indeks slot dari yang paling prioritas untuk Seed"""
    # Urutan Standar Internasional untuk Seeding:
    # Top, Bottom, Mid-Bottom, Mid-Top, dst.
    priority = [
        0,                      # Seed 1
        S - 1,                  # Seed 2
        S // 2,                 # Seed 3
        (S // 2) - 1,           # Seed 4
        S // 4,                 # Seed 5
        (3 * S // 4),           # Seed 6
        (3 * S // 4) - 1,       # Seed 7
        (S // 4) - 1,           # Seed 8
        S // 8,                 # Seed 9
        (7 * S // 8),           # Seed 10
        (5 * S // 8),           # Seed 11
        (3 * S // 8),           # Seed 12
        (3 * S // 8) - 1,       # Seed 13
        (5 * S // 8) - 1,       # Seed 14
        (7 * S // 8) - 1,       # Seed 15
        (S // 8) - 1            # Seed 16
    ]
    # Jika S < 16, bersihkan angka yang melebihi kapasitas slot
    return [p for p in priority if p < S]

@app.route('/simpan-tim', methods=['POST'])
def simpan_tim():
    data = request.json
    kategori_name = data.get('kategori')
    raw_teams = data.get('teams', [])
    jumlah_seed = data.get('jumlah_seed', 0) # Ambil angka dari input HTML
    
    n = len(raw_teams)
    if n == 0: return jsonify({"message": "Kosong!"}), 400

    # 1. Tentukan ukuran bagan
    power = math.ceil(math.log2(n))
    num_slots = 2**power
    
    # 2. Siapkan bagan kosong
    final_list = [None] * num_slots
    
    # 3. Ambil Seeded sesuai jumlah yang diinput user
    seeds = raw_teams[:jumlah_seed]
    regulars = raw_teams[jumlah_seed:]
    
    # 4. Ambil daftar indeks prioritas untuk penempatan Seed
    prioritas_slot = get_priority_positions(num_slots)
    
    # 5. Kunci posisi Seeded ke dalam bagan
    for i in range(len(seeds)):
        if i < len(prioritas_slot):
            target_pos = prioritas_slot[i]
            final_list[target_pos] = seeds[i]

    # 6. Gabungkan sisa pemain reguler dengan BYE lalu ACAK
    num_byes = num_slots - n
    pool_acak = regulars + ["BYE"] * num_byes
    random.shuffle(pool_acak)
    
    # 7. Isi sisa slot bagan yang masih kosong (None)
    pool_idx = 0
    for i in range(num_slots):
        if final_list[i] is None:
            final_list[i] = pool_acak[pool_idx]
            pool_idx += 1

    # 8. Simpan ke JSON
    kategori_slug = kategori_name.replace(" ", "_").lower()
    with open(f"teams_{kategori_slug}.json", 'w', encoding='utf-8') as f:
        json.dump({"nama_tim": final_list}, f, indent=4)
        
    # Jalankan bagan.py otomatis
    try: subprocess.run(["python", "bagan.py"])
    except: pass

    subprocess.run(["python3", "bagan.py"], check=True)
        
    return jsonify({"message": f"Berhasil! {jumlah_seed} Seed dikunci, sisanya diacak."})

@app.route('/manage-categories')
@token_required
def manage_categories_page(current_user):
    return render_template('manage_categories.html')

@app.route('/save-categories', methods=['POST'])
def save_categories():
    data = request.json
    try:
        with open('categories.json', 'w') as f:
            json.dump(data, f, indent=4)
        return jsonify({"message": "Daftar kategori berhasil diperbarui!"})
    except Exception as e:
        return jsonify({"message": f"Gagal menyimpan: {str(e)}"}), 500
    

@app.route('/get-category-stats', methods=['GET'])
def get_category_stats():
    if os.path.exists('categories.json'):
        with open('categories.json', 'r') as f:
            categories = json.load(f).get('categories', [])
        
        stats = []
        for cat in categories:
            # Sesuaikan nama file dengan logika simpan_tim
            filename = f"teams_{cat.replace(' ', '_').lower()}.json"
            count = 0
            if os.path.exists(filename):
                with open(filename, 'r') as f_team:
                    team_data = json.load(f_team)
                    all_teams = team_data.get('nama_tim', [])
                    
                    # FILTER: Hanya hitung tim yang namanya bukan "BYE" (case-insensitive)
                    real_teams = [t for t in all_teams if t.strip().upper() != "BYE"]
                    count = len(real_teams)
                    
            stats.append({"name": cat, "count": count})
        return jsonify(stats)
    return jsonify([])

@app.route('/get-initial-round/<kategori>')
def get_initial_round(kategori):
    # Sesuaikan format nama file (spasi jadi underscore, huruf kecil)
    filename = f"teams_{kategori.replace(' ', '_').lower()}.json"
    
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            data = json.load(f)
            list_peserta = data.get('nama_tim', [])
            n = len(list_peserta)
            
            if n > 0:
                # Logika yang sama dengan bagan.py: cari pangkat 2 terdekat
                power = math.ceil(math.log2(n))
                num_slots = 2**power
                return jsonify({"babak": f"R{num_slots}"})
                
    return jsonify({"babak": ""}) # Kembalikan kosong jika file tidak ada

# ==========================================================
# FITUR KLIK-SWAP LANGSUNG DI BAGAN
# ==========================================================
@app.route('/api/save-swap-bracket', methods=['POST'])
def save_swap_bracket():
    data = request.json
    kategori = data.get('kategori').replace(' ', '_').lower()
    new_order = data.get('teams')
    
    try:
        # 1. Update file teams_?.json dengan urutan baru
        with open(f"teams_{kategori}.json", 'w') as f:
            json.dump({"nama_tim": new_order}, f, indent=4)
        
        # 2. Jalankan ulang generator bagan dan jadwal
        subprocess.run(["python3", "bagan.py"], check=True)
        subprocess.run(["python3", "generate_main.py"], check=True)
        
        return jsonify({"status": "success", "message": "Berhasil ditukar!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/print-buku')
def print_buku():
    # Ambil daftar kategori unik dari file yang ada
    categories = get_categories()
    return render_template('print_buku.html', categories=categories)

@app.route('/export-schedule', methods=['GET'])
def export_schedule():
    try:
        # Membaca hasil jadwal yang sudah digenerate oleh jadwal.py
        schedule_file = 'schedule.json'
        
        if not os.path.exists(schedule_file):
            return jsonify({"message": "File jadwal belum dibuat. Silakan klik Simpan & Update dulu."}), 404
            
        with open(schedule_file, 'r') as f:
            data = json.load(f)
            
        if not data:
            return jsonify({"message": "Data jadwal kosong."}), 400
            
        # Konversi JSON ke DataFrame Excel
        df = pd.DataFrame(data)
        
        # Mengatur urutan kolom agar rapi saat dibuka di Excel
        column_order = ['tanggal', 'jam', 'venue', 'court', 'kategori', 'partai', 'status']
        df = df.reindex(columns=[col for col in column_order if col in df.columns])
        
        output_path = "jadwal_pertandingan_badminton.xlsx"
        df.to_excel(output_path, index=False)
        
        return send_file(output_path, as_attachment=True)
        
    except Exception as e:
        return jsonify({"message": f"Gagal mengekspor: {str(e)}"}), 500
    
@app.route('/api/get-full-schedule')
def get_full_schedule():
    if not os.path.exists('schedule.json'):
        return jsonify([])
    
    # 1. Ambil data Jadwal
    with open('schedule.json', 'r') as f:
        schedules = json.load(f)

    # 2. Ambil data Skor dari Database
    conn = sqlite3.connect('skor.db')
    conn.row_factory = sqlite3.Row
    skor_rows = conn.execute('SELECT * FROM tabel_skor').fetchall()
    conn.close()

    # Buat dictionary skor untuk mempercepat pencarian
    # Key: KATEGORI_MATCHID
    skor_map = {f"{row['kategori'].upper()}_{row['match_id']}": row for row in skor_rows}

    # 3. Gabungkan
    for s in schedules:
        key = f"{s['kategori'].upper()}_{s['match_id']}"
        if key in skor_map:
            res = skor_map[key]
            s['skor'] = f"{res['skor_p1']} - {res['skor_p2']}"
            s['winner'] = res['winner']
            s['status_label'] = "SELESAI"
        else:
            s['skor'] = "-"
            s['winner'] = ""
            s['status_label'] = "MENUNGGU"

    return jsonify(schedules)

if __name__ == '__main__':
    init_skor_db()  # <--- Baris ini WAJIB ada di sini
    app.run(host='0.0.0.0', port=5000, debug=True)
