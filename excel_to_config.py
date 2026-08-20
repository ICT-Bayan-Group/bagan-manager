import json
import re
from datetime import datetime
import pandas as pd

# Pemetaan Bulan Bahasa Indonesia ke Angka
MONTH_MAP = {
    'JANUARI': '01',
    'FEBRUARI': '02',
    'MARET': '03',
    'APRIL': '04',
    'MEI': '05',
    'JUNI': '06',
    'JULI': '07',
    'AGUSTUS': '08',
    'SEPTEMBER': '09',
    'OKTOBER': '10',
    'NOVEMBER': '11',
    'DESEMBER': '12',
}

# Pemetaan Kode Kategori (Sesuaikan jika ada singkatan)
CATEGORY_MAP = {
    'GANDA TUNGGAL IPA': 'GTI',
    'GANDA TUNGGAL IPS': 'GTS',
    'GDI': 'GDI',
    'GANDA PUTRA OPEN': 'GPO',
    'GANDA CAMPURAN OPEN': 'GCO',
    'GANDA VETERAN OPEN': 'GVO',
}


def parse_date(text):
  """Mencari tanggal dalam format 'HARI, DD BULAN YYYY'"""
  if not isinstance(text, str):
    return None
  match = re.search(
      r'([A-ZA-Za-z]+),\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', text, re.IGNORECASE
  )
  if match:
    _, day, month, year = match.groups()
    month_code = MONTH_MAP.get(month.upper(), '01')
    return f'{year}-{month_code}-{int(day):02d}'
  return None


def parse_court_count(text):
  """Mencari jumlah lapangan (contoh: '1 - 4 Lapangan' -> ['Court-1', 'Court-2', 'Court-3', 'Court-4'])"""
  if not isinstance(text, str):
    return ['Court-1']
  match = re.search(r'(\d+)\s*-\s*(\d+)\s*Lapangan', text, re.IGNORECASE)
  if match:
    start_c, end_c = int(match.group(1)), int(match.group(2))
    return [f'Court-{i}' for i in range(start_c, end_c + 1)]
  match_single = re.search(r'(\d+)\s*Lapangan', text, re.IGNORECASE)
  if match_single:
    return [f'Court-{i}' for i in range(1, int(match_single.group(1)) + 1)]
  return ['Court-1']


def convert_excel_to_config(
    excel_path='JADWAL PERTANDINGAN.xls', output_json='config.json'
):
  xls = pd.ExcelFile(excel_path)
  config_results = []

  for sheet_name in xls.sheet_names:
    df = pd.read_excel(excel_path, sheet_name=sheet_name)

    current_date = None
    current_venue = 'GOR NAGA MAS TARAKAN'  # Default venue dari header Excel
    current_courts = ['Court-1', 'Court-2', 'Court-3', 'Court-4']

    for idx, row in df.iterrows():
      row_str = ' '.join([str(cell) for cell in row.values if pd.notna(cell)])

      # 1. Cek Header Tanggal
      found_date = parse_date(row_str)
      if found_date:
        current_date = found_date
        continue

      # 2. Cek Header Lapangan
      if 'Lapangan' in row_str:
        current_courts = parse_court_count(row_str)
        continue

      # 3. Cek Header Venue / GOR
      if 'GOR' in row_str or 'DOME' in row_str:
        match_venue = re.search(
            r'(GOR\s+[A-Za-z0-9\s]+|DOME|HEVINDO ARENA|TENNIS INDOOR)',
            row_str,
            re.IGNORECASE,
        )
        if match_venue:
          current_venue = match_venue.group(1).strip().upper()

      # 4. Deteksi Baris Jadwal Pertandingan
      # Memeriksa keberadaan Waktu/Jam (contoh: '14.00' atau '19.00')
      time_match = re.search(r'(\d{1,2})[\.:](\d{2})', row_str)
      if time_match and current_date:
        jam_start_h = int(time_match.group(1))
        jam_start_m = int(time_match.group(2))
        jam_mulai = f'{jam_start_h:02d}:{jam_start_m:02d}'

        # Jam selesai diestimasi (+2 jam atau sesuai slot)
        jam_selesai = f'{(jam_start_h + 2) % 24:02d}:{jam_start_m:02d}'

        # Ambil Kategori & Babak
        kategori = None
        babak = 'R16'  # Default

        # Cek keterangan babak di akhir (QF, SEMI FINAL, FINAL, dll)
        if 'FINAL' in row_str.upper() and 'SEMI' not in row_str.upper():
          babak = 'FINAL'
        elif 'SEMI FINAL' in row_str.upper() or 'SF' in row_str.upper():
          babak = 'SEMI FINAL'
        elif 'QF' in row_str.upper() or 'PEREMPAT' in row_str.upper():
          babak = 'PEREMPAT FINAL'

        # Ekstrak Kategori
        for cell in row.values:
          if pd.notna(cell) and isinstance(cell, str):
            cell_clean = cell.strip()
            if cell_clean in CATEGORY_MAP:
              kategori = CATEGORY_MAP[cell_clean]
              break
            elif cell_clean in CATEGORY_MAP.values():
              kategori = cell_clean
              break

        if kategori:
          config_entry = {
              'kategori': kategori,
              'tanggal': current_date,
              'jam_mulai': jam_mulai,
              'jam_selesai': jam_selesai,
              'babak': babak,
              'venue': current_venue,
              'lapangan': current_courts,
          }
          config_results.append(config_entry)

  # Simpan ke config.json
  with open(output_json, 'w', encoding='utf-8') as f:
    json.dump(config_results, f, indent=4, ensure_ascii=False)

  print(
      f'✅ Berhasil mengonversi {len(config_results)} slot jadwal dari Excel ke'
      f' {output_json}'
  )


if __name__ == '__main__':
  convert_excel_to_config()