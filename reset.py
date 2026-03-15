import os
import glob
import json

def reset_system():
    print("⚠️  PERINGATAN: Tindakan ini akan menghapus seluruh data peserta dan jadwal!")
    konfirmasi = input("Ketik 'RESET' untuk melanjutkan: ")

    if konfirmasi != "RESET":
        print("❌ Reset dibatalkan.")
        return

    print("\n--- Memulai Proses Reset ---")

    # 1. Hapus semua file teams_*.json
    team_files = glob.glob('teams_*.json')
    for file in team_files:
        try:
            os.remove(file)
            print(f"✅ Dihapus: {file}")
        except Exception as e:
            print(f"❌ Gagal menghapus {file}: {e}")

    # 2. Definisikan reset untuk file JSON utama
    files_to_reset = {
        'categories.json': {"categories": []},
        'matches.json': [],
        'config.json': [],
        'schedule.json': []
    }

    # 3. Eksekusi reset isi file
    for filename, content in files_to_reset.items():
        try:
            with open(filename, 'w') as f:
                json.dump(content, f, indent=4)
            print(f"✅ Di-reset: {filename}")
        except Exception as e:
            print(f"❌ Gagal reset {filename}: {e}")

    print("\n--- 🏁 Reset Selesai! Sistem Kembali Bersih ---")

if __name__ == "__main__":
    reset_system()