import glob
import json
import os
import sys
import pandas as pd


def clean_category_name(sheet_name):
    name = (
        sheet_name.replace("-Main Draw", "")
        .replace("Main Draw", "")
        .strip()
        .lower()
    )
    return name.replace(" ", "_")


def format_double_entry(p1, c1, p2, c2):
    """Format gabungan nama pasangan ganda dengan klub di akhir"""
    players_str = f"{p1} / {p2}" if p2 else p1

    # Olah nama klub agar tidak berulang jika dari klub yang sama
    clubs = []
    if c1 and c1.lower() != "nan" and not c1.isdigit():
        clubs.append(c1)
    if c2 and c2.lower() != "nan" and not c2.isdigit() and c2 != c1:
        clubs.append(c2)

    if clubs:
        club_str = " / ".join(clubs)
        return f"{players_str} ({club_str})"

    return players_str


def format_single_entry(p, c):
    """Format pemain tunggal"""
    if c and c.lower() != "nan" and not c.isdigit():
        return f"{p} ({c})"
    return p


def convert_excel_to_teams_json(excel_path):
    if not os.path.exists(excel_path):
        print(f"❌ File '{excel_path}' tidak ditemukan!")
        return

    print(f"📖 Membaca & memproses file: {excel_path}...")

    try:
        xls = pd.ExcelFile(excel_path)
        processed_count = 0
        categories_names = []

        for sheet_name in xls.sheet_names:
            if "Main Draw" not in sheet_name:
                continue

            df = pd.read_excel(excel_path, sheet_name=sheet_name)

            # Cari baris header "Round 1"
            header_row_idx = None
            for idx, row in df.iterrows():
                row_str = [str(cell) for cell in row.values if pd.notna(cell)]
                if any("Round 1" in cell for cell in row_str):
                    header_row_idx = idx
                    break

            if header_row_idx is None:
                continue

            category_clean = sheet_name.replace("-Main Draw", "").strip()
            is_ganda = category_clean.startswith("G")

            cleaned_players = []

            for idx in range(header_row_idx + 1, len(df)):
                row = df.iloc[idx]
                pos_val = row.iloc[0]

                try:
                    pos_num = int(pos_val)
                except (ValueError, TypeError):
                    continue

                # --- KATEGORI GANDA ---
                if is_ganda:
                    r_p1 = df.iloc[idx - 1] if idx - 1 >= 0 else None
                    club_1 = (
                        str(r_p1.iloc[2]).strip()
                        if r_p1 is not None and pd.notna(r_p1.iloc[2])
                        else ""
                    )
                    player_1 = (
                        str(r_p1.iloc[3]).strip()
                        if r_p1 is not None and pd.notna(r_p1.iloc[3])
                        else ""
                    )

                    club_2 = (
                        str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
                    )
                    player_2 = (
                        str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ""
                    )

                    player_2_upper = player_2.upper()

                    if (
                        not player_2
                        or player_2 == "nan"
                        or "BYE" in player_2_upper
                    ):
                        cleaned_players.append("BYE")
                    else:
                        entry = format_double_entry(
                            player_1, club_1, player_2, club_2
                        )
                        cleaned_players.append(entry)

                # --- KATEGORI TUNGGAL ---
                else:
                    club_val = (
                        str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
                    )
                    player_val = (
                        str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ""
                    )

                    player_upper = player_val.upper()

                    if (
                        not player_val
                        or player_val == "nan"
                        or "BYE" in player_upper
                    ):
                        cleaned_players.append("BYE")
                    else:
                        entry = format_single_entry(player_val, club_val)
                        cleaned_players.append(entry)

            # SIMPAN KE JSON
            if cleaned_players:
                category_key = clean_category_name(sheet_name)
                output_json = f"teams_{category_key}.json"

                with open(output_json, "w", encoding="utf-8") as f:
                    json.dump(
                        {"nama_tim": cleaned_players},
                        f,
                        indent=4,
                        ensure_ascii=False,
                    )

                display_name = sheet_name.replace("-Main Draw", "").strip()
                categories_names.append(display_name)

                print(
                    f"  ├─ ✅ Berhasil: {output_json} ({len(cleaned_players)} slot)"
                )
                processed_count += 1

        if categories_names:
            with open("categories.json", "w", encoding="utf-8") as f:
                json.dump(
                    {"categories": categories_names},
                    f,
                    indent=4,
                    ensure_ascii=False,
                )
            print("  ├─ ✅ Berhasil membuat file: categories.json")

        print(
            f"\n✨ Selesai! {processed_count} kategori & file categories.json berhasil dibuat."
        )

    except Exception as e:
        print(f"❌ Terjadi kesalahan: {e}")


if __name__ == "__main__":
    target_file = sys.argv[1] if len(sys.argv) > 1 else None
    if not target_file:
        files = glob.glob("*.XLSX") + glob.glob("*.xlsx")
        files = [f for f in files if "Cleaned" not in f]
        target_file = files[0] if files else None

    if target_file:
        convert_excel_to_teams_json(target_file)
    else:
        print("❌ Tidak ditemukan file .xlsx di direktori ini.")