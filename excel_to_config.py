from datetime import datetime, timedelta
import json
import re
import pandas as pd

MONTH_MAP = {
    "JANUARI": 1,
    "JAN": 1,
    "FEBRUARI": 2,
    "FEB": 2,
    "MARET": 3,
    "MAR": 3,
    "APRIL": 4,
    "APR": 4,
    "MEI": 5,
    "MAY": 5,
    "JUNI": 6,
    "JUN": 6,
    "JULI": 7,
    "JUL": 7,
    "AGUSTUS": 8,
    "AUG": 8,
    "SEPTEMBER": 9,
    "SEP": 9,
    "OKTOBER": 10,
    "OCT": 10,
    "NOVEMBER": 11,
    "NOV": 11,
    "DESEMBER": 12,
    "DEC": 12,
}


def get_jam_selesai(jam_mulai_str, duration_hours=1):
  """Menhitung jam_selesai dengan menambah durasi waktu (default: +1 jam)."""
  h, m = map(int, jam_mulai_str.split(":"))
  dt = datetime(2026, 1, 1, h, m) + timedelta(hours=duration_hours)
  return dt.strftime("%H:%M")


def load_json(filepath):
  with open(filepath, "r", encoding="utf-8") as f:
    return json.load(f)


def build_config(
    excel_file="JADWAL PERTANDINGAN.xls",
    categories_file="categories.json",
    matches_file="matches.json",
    output_file="config.json",
    default_venue="GOR NAGA MAS TARAKAN",
):
  categories_data = load_json(categories_file).get("categories", [])
  matches_ref = load_json(matches_file)

  # 1. Pemetaan presisi dari matches.json: (match_id, kategori) -> babak
  match_babak_map = {}
  for item in matches_ref:
    m_id = item.get("id")
    kat = str(item.get("kategori", "")).strip()
    babak = item.get("babak")
    if m_id is not None and kat and babak:
      match_babak_map[(m_id, kat)] = str(babak).strip()

  xls = pd.ExcelFile(excel_file)
  config_output = []

  # 2. Parsing Excel
  for sheet_name in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet_name)
    current_date = None

    for _, row in df.iterrows():
      vals = [str(cell).strip() for cell in row.values if pd.notna(cell)]
      if not vals:
        continue

      row_str = " ".join(vals)

      # Extract Tanggal (misal: JUMAT, 21 AGUSTUS 2026)
      date_match = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", row_str)
      if date_match:
        day, month_str, year = date_match.groups()
        month_num = MONTH_MAP.get(month_str.upper())
        if month_num:
          current_date = f"{year}-{month_num:02d}-{int(day):02d}"
          continue

      # Extract Jam
      time_match = re.search(r"\b(\d{1,2}[\.:]\d{2})\b", row_str)
      if time_match and current_date:
        jam_mulai = time_match.group(1).replace(".", ":")
        if len(jam_mulai.split(":")[0]) == 1:
          jam_mulai = f"0{jam_mulai}"

        jam_selesai = get_jam_selesai(jam_mulai)

        # Match Kategori dari categories.json
        matched_cat = None
        for cat in categories_data:
          if re.search(rf"\b{re.escape(cat)}\b", row_str, re.IGNORECASE):
            matched_cat = cat
            break

        # Extract Match IDs dari baris
        match_ids = []
        for v in vals:
          try:
            num = float(v)
            if num.is_integer() and num > 0:
              match_ids.append(int(num))
          except ValueError:
            pass

        # Susun config item per sesi waktu
        if matched_cat and match_ids:
          # Ambil babak dari matches.json atau dari teks baris
          exact_babak = None
          for m_id in match_ids:
            if (m_id, matched_cat) in match_babak_map:
              exact_babak = match_babak_map[(m_id, matched_cat)]
              break

          row_upper = row_str.upper()
          if (
              "FINAL" in row_upper
              and "SEMI" not in row_upper
              and "PEREMPAT" not in row_upper
              and "QF" not in row_upper
          ):
            exact_babak = "FINAL"
          elif "SEMI" in row_upper:
            exact_babak = "SEMI FINAL"
          elif "PEREMPAT" in row_upper or "QF" in row_upper:
            exact_babak = "PEREMPAT FINAL"

          # Buat list lapangan berdasarkan jumlah pertandingan pada baris tersebut
          lapangan_list = [f"Court-{i+1}" for i in range(len(match_ids))]

          config_output.append({
              "kategori": matched_cat,
              "tanggal": current_date,
              "jam_mulai": jam_mulai,
              "jam_selesai": jam_selesai,
              "babak": exact_babak,
              "venue": default_venue,
              "lapangan": lapangan_list,
          })

  # 3. Simpan ke config.json
  with open(output_file, "w", encoding="utf-8") as f:
    json.dump(config_output, f, indent=2, ensure_ascii=False)

  print(f"Berhasil menyimpan {len(config_output)} item ke {output_file}.")


if __name__ == "__main__":
  build_config()