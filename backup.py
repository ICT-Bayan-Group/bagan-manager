import os
import glob
import zipfile
import sqlite3
import shutil
import subprocess
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def copy_sqlite_safe(source_path, target_path):
    if os.path.exists(source_path):
        with sqlite3.connect(source_path) as src, sqlite3.connect(target_path) as dst:
            src.backup(dst)

def create_backup():
    """Hanya berjalan saat tombol 'Download Backup' diklik di web GUI"""
    backup_dir = os.path.join(BASE_DIR, 'backups')
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = f"backup_bagan_{timestamp}.zip"
    zip_filepath = os.path.join(backup_dir, zip_filename)

    temp_db_path = os.path.join(backup_dir, 'skor_temp.db')
    copy_sqlite_safe(os.path.join(BASE_DIR, 'skor.db'), temp_db_path)

    file_map = {
        'skor.db': temp_db_path,
        'matches.json': os.path.join(BASE_DIR, 'matches.json'),
        'config.json': os.path.join(BASE_DIR, 'config.json'),
        'schedule.json': os.path.join(BASE_DIR, 'schedule.json'),
        'categories.json': os.path.join(BASE_DIR, 'categories.json')
    }

    for tf in glob.glob(os.path.join(BASE_DIR, 'teams_*.json')):
        file_map[os.path.basename(tf)] = tf

    with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for arcname, filepath in file_map.items():
            if os.path.exists(filepath):
                zipf.write(filepath, arcname=arcname)

    if os.path.exists(temp_db_path):
        os.remove(temp_db_path)

    return zip_filepath, zip_filename


def restore_backup(file_storage):
    """Mengekstrak data restore, lalu meregenerasi bagan & jadwal TANPA membuat backup baru"""
    temp_extract_dir = os.path.join(BASE_DIR, 'backups', 'temp_restore')
    if os.path.exists(temp_extract_dir):
        shutil.rmtree(temp_extract_dir)
    os.makedirs(temp_extract_dir, exist_ok=True)

    zip_path = os.path.join(temp_extract_dir, 'uploaded_restore.zip')
    file_storage.save(zip_path)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_extract_dir)

    # Overwrite file utama
    for item in os.listdir(temp_extract_dir):
        if item == 'uploaded_restore.zip':
            continue
        src_file = os.path.join(temp_extract_dir, item)
        dst_file = os.path.join(BASE_DIR, item)
        if os.path.isfile(src_file):
            shutil.copy2(src_file, dst_file)

    # Bersihkan sisa temp ekstraksi
    shutil.rmtree(temp_extract_dir)

    # Murni jalankan pembaruan jadwal/bagan saja (Tanpa Backup)
    subprocess.run(["python3", "bagan.py"], check=False)
    subprocess.run(["python3", "generate_main.py"], check=False)

    return True