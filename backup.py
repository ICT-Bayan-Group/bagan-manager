import os
import sys
import glob
import zipfile
import sqlite3
import shutil
import subprocess
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def copy_sqlite_safe(source_path, target_path):
    """Menyalin database SQLite secara aman meskipun aplikasi sedang berjalan"""
    if os.path.exists(source_path):
        with sqlite3.connect(source_path) as src, sqlite3.connect(target_path) as dst:
            src.backup(dst)

def create_backup():
    """Membuat arsip file backup (.zip) dari database dan file JSON"""
    backup_dir = os.path.join(BASE_DIR, 'backups')
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = f"backup_bagan_{timestamp}.zip"
    zip_filepath = os.path.join(backup_dir, zip_filename)

    temp_db_path = os.path.join(backup_dir, 'skor_temp.db')
    
    try:
        # Salin DB secara aman ke file sementara
        copy_sqlite_safe(os.path.join(BASE_DIR, 'skor.db'), temp_db_path)

        file_map = {
            'skor.db': temp_db_path,
            'matches.json': os.path.join(BASE_DIR, 'matches.json'),
            'config.json': os.path.join(BASE_DIR, 'config.json'),
            'schedule.json': os.path.join(BASE_DIR, 'schedule.json'),
            'categories.json': os.path.join(BASE_DIR, 'categories.json')
        }

        # Masukkan semua file tim (teams_*.json) jika ada
        for tf in glob.glob(os.path.join(BASE_DIR, 'teams_*.json')):
            file_map[os.path.basename(tf)] = tf

        # Masukkan file-file tersebut ke dalam file ZIP
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for arcname, filepath in file_map.items():
                if os.path.exists(filepath):
                    zipf.write(filepath, arcname=arcname)

        return zip_filepath, zip_filename
    finally:
        # Pastikan file database sementara selalu dibersihkan
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)


def restore_backup(file_storage):
    """Mengekstrak file ZIP restore dan memperbarui data utama"""
    temp_extract_dir = os.path.join(BASE_DIR, 'backups', 'temp_restore')
    if os.path.exists(temp_extract_dir):
        shutil.rmtree(temp_extract_dir)
    os.makedirs(temp_extract_dir, exist_ok=True)

    zip_path = os.path.join(temp_extract_dir, 'uploaded_restore.zip')
    file_storage.save(zip_path)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # Proteksi Keamanan: Mencegah celah Zip Slip (Path Traversal)
        for member in zip_ref.infolist():
            target_path = os.path.abspath(os.path.join(temp_extract_dir, member.filename))
            if not target_path.startswith(os.path.abspath(temp_extract_dir)):
                raise ValueError("Error Keamanan: File ZIP berisi jalur file yang mencurigakan.")
        zip_ref.extractall(temp_extract_dir)

    # Timpa file data utama dengan data hasil ekstraksi
    for item in os.listdir(temp_extract_dir):
        if item == 'uploaded_restore.zip':
            continue
        src_file = os.path.join(temp_extract_dir, item)
        dst_file = os.path.join(BASE_DIR, item)
        
        if os.path.isfile(src_file):
            if item == 'skor.db':
                copy_sqlite_safe(src_file, dst_file)
            else:
                shutil.copy2(src_file, dst_file)

    # Bersihkan folder ekstraksi sementara
    shutil.rmtree(temp_extract_dir)

    # Jalankan ulang skrip pembaharuan bagan dan jadwal (kompatibel untuk Windows/Linux/macOS)
    subprocess.run([sys.executable, os.path.join(BASE_DIR, "bagan.py")], check=False)
    subprocess.run([sys.executable, os.path.join(BASE_DIR, "generate_main.py")], check=False)

    return True