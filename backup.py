import os
import glob
import zipfile
import sqlite3
import shutil
import subprocess
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def copy_sqlite_safe(source_path, target_path):
    """Menyalin skor.db secara aman tanpa risiko ter-lock."""
    if os.path.exists(source_path):
        with sqlite3.connect(source_path) as src, sqlite3.connect(target_path) as dst:
            src.backup(dst)

def create_backup():
    """Membuat file zip berisi seluruh data sistem."""
    backup_dir = os.path.join(BASE_DIR, 'backups')
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = f"backup_bagan_{timestamp}.zip"
    zip_filepath = os.path.join(backup_dir, zip_filename)

    # 1. Salin skor.db sementara
    temp_db_path = os.path.join(backup_dir, 'skor_temp.db')
    copy_sqlite_safe(os.path.join(BASE_DIR, 'skor.db'), temp_db_path)

    file_map = {
        'skor.db': temp_db_path,
        'matches.json': os.path.join(BASE_DIR, 'matches.json'),
        'config.json': os.path.join(BASE_DIR, 'config.json'),
        'schedule.json': os.path.join(BASE_DIR, 'schedule.json'),
        'categories.json': os.path.join(BASE_DIR, 'categories.json')
    }

    # Masukkan seluruh teams_*.json
    for tf in glob.glob(os.path.join(BASE_DIR, 'teams_*.json')):
        file_map[os.path.basename(tf)] = tf

    # 2. Kompresi ke ZIP
    with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for arcname, filepath in file_map.items():
            if os.path.exists(filepath):
                zipf.write(filepath, arcname=arcname)

    if os.path.exists(temp_db_path):
        os.remove(temp_db_path)

    return zip_filepath, zip_filename


def restore_backup(file_storage):
    """Mengekstrak file zip dan menimpa data lama."""
    temp_extract_dir = os.path.join(BASE_DIR, 'backups', 'temp_restore')
    if os.path.exists(temp_extract_dir):
        shutil.rmtree(temp_extract_dir)
    os.makedirs(temp_extract_dir, exist_ok=True)

    # Simpan stream file dari Flask
    zip_path = os.path.join(temp_extract_dir, 'uploaded_restore.zip')
    file_storage.save(zip_path)

    # Ekstrak
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_extract_dir)

    # Timpa file utama
    for item in os.listdir(temp_extract_dir):
        if item == 'uploaded_restore.zip':
            continue
        src_file = os.path.join(temp_extract_dir, item)
        dst_file = os.path.join(BASE_DIR, item)
        if os.path.isfile(src_file):
            shutil.copy2(src_file, dst_file)

    shutil.rmtree(temp_extract_dir)

    # Re-generate bagan & jadwal
    try:
        subprocess.run(["python3", "bagan.py"], check=False)
        subprocess.run(["python3", "generate_main.py"], check=False)
    except Exception as e:
        print(f"[WARN] Error re-generate setelah restore: {e}")

    return True