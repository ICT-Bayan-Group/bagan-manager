import glob
import json
import os


def reset_system():
    print(
        "⚠️  PERINGATAN: Tindakan ini akan menghapus seluruh data peserta, jadwal, dan database skor!"
    )
    konfirmasi = input("Ketik 'RESET' untuk melanjutkan: ")

    if konfirmasi != "RESET":
        print("❌ Reset dibatalkan.")
        return

    print("\n--- Memulai Proses Reset ---")

    # 1. Hapus semua file teams_*.json
    team_files = glob.glob("teams_*.json")
    for file in team_files:
        try:
            os.remove(file)
            print(f"✅ Dihapus: {file}")
        except Exception as e:
            print(f"❌ Gagal menghapus {file}: {e}")

    # 2. Hapus skor.db dan file temporary SQLite (-wal / -shm) jika ada
    db_files = ["skor.db", "skor.db-wal", "skor.db-shm"]
    for db_file in db_files:
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
                print(f"✅ Dihapus: {db_file}")
            except Exception as e:
                print(f"❌ Gagal menghapus {db_file}: {e}")

    # 3. Definisikan reset untuk file JSON utama
    files_to_reset = {
        "categories.json": {"categories": []},
        "matches.json": [],
        "config.json": [],
        "schedule.json": [],
    }

    # 4. Eksekusi reset isi file JSON
    for filename, content in files_to_reset.items():
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=4)
            print(f"✅ Di-reset: {filename}")
        except Exception as e:
            print(f"❌ Gagal reset {filename}: {e}")

    print("\n--- 🏁 Reset Selesai! Sistem Kembali Bersih ---")


if __name__ == "__main__":
    reset_system()