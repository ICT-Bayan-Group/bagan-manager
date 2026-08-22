import json
import os
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
    p1 = "" if str(p1).lower() in ["nan", "0", "none"] else str(p1).strip()
    p2 = "" if str(p2).lower() in ["nan", "0", "none"] else str(p2).strip()

    if p1 and p2 and p1 != p2:
        players_str = f"{p1} / {p2}"
    else:
        players_str = p1 or p2

    clubs = []
    for c in [c1, c2]:
        c_str = str(c).strip() if pd.notna(c) else ""
        if (
            c_str
            and c_str.lower() not in ["nan", "0", "none"]
            and not c_str.isdigit()
        ):
            if c_str not in clubs:
                clubs.append(c_str)

    if clubs:
        return f"{players_str} ({' / '.join(clubs)})"

    return players_str


def format_single_entry(p, c):
    """Format pemain/tim tunggal"""
    p_str = str(p).strip() if pd.notna(p) else ""
    c_str = str(c).strip() if pd.notna(c) else ""

    if (
        c_str
        and c_str.lower() not in ["nan", "0", "none"]
        and not c_str.isdigit()
    ):
        return f"{p_str} ({c_str})"
    return p_str


def convert_excel_to_teams_json(excel_path):
    if not os.path.exists(excel_path):
        print(f"❌ File '{excel_path}' tidak ditemukan!")
        return []

    print(f"📖 Membaca & memproses file: {excel_path}...")
    categories_names = []

    try:
        xls = pd.ExcelFile(excel_path)
        processed_count = 0

        for sheet_name in xls.sheet_names:
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
            is_beregu = "BEREGU" in category_clean.upper()

            header_row = df.iloc[header_row_idx]
            pos_col_idx = 0
            club_col_idx = 1
            player_col_idx = 2

            for c_idx, cell_val in enumerate(header_row):
                cell_str = (
                    str(cell_val).strip().upper() if pd.notna(cell_val) else ""
                )
                if cell_str == "NO":
                    pos_col_idx = c_idx
                elif "ROUND 1" in cell_str:
                    player_col_idx = c_idx
                    club_col_idx = max(0, c_idx - 1)

            cleaned_players = []

            idx = header_row_idx + 1
            while idx < len(df):
                row = df.iloc[idx]
                pos_val = row.iloc[pos_col_idx]

                # Validasi baris angka/posisi
                try:
                    pos_num = int(pos_val)
                except (ValueError, TypeError):
                    idx += 1
                    continue

                # --- KATEGORI BEREGU ---
                if is_beregu:
                    c_val = (
                        str(row.iloc[club_col_idx]).strip()
                        if pd.notna(row.iloc[club_col_idx])
                        else ""
                    )
                    p_val = (
                        str(row.iloc[player_col_idx]).strip()
                        if pd.notna(row.iloc[player_col_idx])
                        else ""
                    )

                    team_name = ""
                    for candidate in [p_val, c_val]:
                        if (
                            candidate
                            and candidate.lower() not in ["0", "nan", "none"]
                            and not candidate.isdigit()
                        ):
                            team_name = candidate
                            break

                    if not team_name or "BYE" in team_name.upper():
                        cleaned_players.append("BYE")
                    else:
                        cleaned_players.append(team_name)

                    idx += 1  # Lanjut ke baris berikutnya

                # --- KATEGORI PERORANGAN (GANDA & TUNGGAL) ---
                else:
                    p1 = (
                        str(row.iloc[player_col_idx]).strip()
                        if pd.notna(row.iloc[player_col_idx])
                        else ""
                    )
                    c1 = (
                        str(row.iloc[club_col_idx]).strip()
                        if pd.notna(row.iloc[club_col_idx])
                        else ""
                    )

                    # Jika Pemain 1 adalah BYE langsung tandai BYE
                    if "BYE" in p1.upper() or not p1:
                        cleaned_players.append("BYE")
                        idx += 1
                        continue

                    # Intip baris berikutnya untuk Pemain 2 (Ganda)
                    p2, c2 = "", ""
                    has_p2_row = False

                    if idx + 1 < len(df):
                        r_next = df.iloc[idx + 1]
                        next_pos = r_next.iloc[pos_col_idx]

                        # Pasangan ganda biasanya berada di baris tanpa NO (pos_val kosong/NaN)
                        if pd.isna(next_pos) or str(next_pos).strip() in [
                            "",
                            "nan",
                        ]:
                            p2 = (
                                str(r_next.iloc[player_col_idx]).strip()
                                if pd.notna(r_next.iloc[player_col_idx])
                                else ""
                            )
                            c2 = (
                                str(r_next.iloc[club_col_idx]).strip()
                                if pd.notna(r_next.iloc[club_col_idx])
                                else ""
                            )
                            if p2 and p2.lower() not in ["0", "nan", "none"]:
                                has_p2_row = True

                    # Pemrosesan entri ganda vs tunggal
                    if has_p2_row and "BYE" not in p2.upper():
                        entry = format_double_entry(p1, c1, p2, c2)
                        cleaned_players.append(entry)
                        idx += 2  # Lewati 2 baris (Pemain 1 & Pemain 2)
                    else:
                        entry = format_single_entry(p1, c1)
                        cleaned_players.append(entry)
                        idx += 1  # Lewati 1 baris (Pemain Tunggal)

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

        print(
            f"✨ Selesai! {processed_count} kategori diproses dari file ini."
        )

    except Exception as e:
        print(f"❌ Terjadi kesalahan saat memproses '{excel_path}': {e}")

    return categories_names


if __name__ == "__main__":
    target_files = [
        "Draws BAYAN OPEN Sirkuit Nasional C 2026.XLSX",
        "BAGAN PERTANDINGAN-open.xlsx",
    ]

    all_categories = []

    print("🚀 Memulai konversi bagan Excel ke JSON...\n")
    for file_path in target_files:
        if os.path.exists(file_path):
            cats = convert_excel_to_teams_json(file_path)
            for c in cats:
                if c not in all_categories:
                    all_categories.append(c)
            print("=" * 60)
        else:
            print(f"⚠️ File '{file_path}' tidak ditemukan, melewati...\n")

    if all_categories:
        with open("categories.json", "w", encoding="utf-8") as f:
            json.dump(
                {"categories": all_categories},
                f,
                indent=4,
                ensure_ascii=False,
            )
        print(
            f"🎉 Total {len(all_categories)} kategori berhasil digabungkan ke 'categories.json'."
        )