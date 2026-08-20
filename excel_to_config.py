import json
import re
import pandas as pd

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


def load_category_map(categories_file='categories.json'):
  """Membaca file categories.json dan membuat pemetaan kategori."""
  try:
    with open(categories_file, 'r', encoding='utf-8') as f:
      data = json.load(f)
      categories = data.get('categories', [])

      # Membuat dictionary mapping (misal: {'GTI': 'GTI', 'GPA': 'GPA', ...})
      category_map = {cat.strip(): cat.strip() for cat in categories}

      # Tambahkan pemetaan deskripsi panjang ke kode jika diperlukan
      custom_aliases = {
          'GANDA PUTRA OPEN': 'GPA',
          'GANDA CAMPURAN OPEN': 'GRC',
          'GANDA DEWASA INTENSIF': 'GDI',
      }
      category_map.update(custom_aliases)

      return category_map
  except FileNotFoundError:
    print(
        f'⚠️ File {categories_file} tidak ditemukan. Menggunakan fallback'
        ' default.'
    )
    return {}


def convert_excel_to_config(
    excel_path='JADWAL PERTANDINGAN.xls',
    categories_path='categories.json',
    output_json='config.json',
):
  category_map = load_category_map(categories_path)
  xls = pd.ExcelFile(excel_path)
  config_results = []

  for sheet_name in xls.sheet_names:
    df = pd.read_excel(excel_path, sheet_name=sheet_name)
    current_date = None
    current_venue = 'GOR NAGA MAS TARAKAN'

    for idx, row in df.iterrows():
      row_vals = [cell for cell in row.values if pd.notna(cell)]
      row_str = ' '.join([str(c) for c in row_vals])

      # 1. Deteksi Tanggal
      match_date = re.search(
          r'([A-Za-z]+),\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})',
          row_str,
          re.IGNORECASE,
      )
      if match_date:
        _, day, month, year = match_date.groups()
        m_code = MONTH_MAP.get(month.upper(), '01')
        current_date = f'{year}-{m_code}-{int(day):02d}'
        continue

      # 2. Deteksi Waktu / Jam
      time_match = re.search(r'(\d{1,2})[\.:](\d{2})', row_str)
      if time_match and current_date:
        jam_h = int(time_match.group(1))
        jam_m = int(time_match.group(2))
        jam_mulai = f'{jam_h:02d}:{jam_m:02d}'
        jam_selesai = f'{(jam_h + 1) % 24:02d}:{jam_m:02d}'

        # Ambil Kategori dari category_map yang dimuat
        kategori = None
        for cell in row_vals:
          c_clean = str(cell).strip()
          if c_clean in category_map:
            kategori = category_map[c_clean]
            break

        # Hitung berapa nomor pertandingan yang ada di baris ini
        match_numbers = []
        for val in row.values:
          if isinstance(val, (int, float)) and not pd.isna(val):
            if val == int(val) and int(val) > 0:
              match_numbers.append(int(val))

        # Tentukan babak
        babak = 'R16'
        if 'FINAL' in row_str.upper() and 'SEMI' not in row_str.upper():
          babak = 'FINAL'
        elif 'SEMI FINAL' in row_str.upper():
          babak = 'SEMI FINAL'
        elif 'QF' in row_str.upper():
          babak = 'PEREMPAT FINAL'

        # Jika ada kategori & pertandingan di baris tersebut
        if kategori and match_numbers:
          lapangan_list = [f'Court-{i+1}' for i in range(len(match_numbers))]

          config_results.append({
              'kategori': kategori,
              'tanggal': current_date,
              'jam_mulai': jam_mulai,
              'jam_selesai': jam_selesai,
              'babak': babak,
              'venue': current_venue,
              'lapangan': lapangan_list,
          })

  # Simpan ke config.json
  with open(output_json, 'w', encoding='utf-8') as f:
    json.dump(config_results, f, indent=4, ensure_ascii=False)

  print(
      f'✅ Berhasil membuat {output_json} dengan total {len(config_results)}'
      ' slot jadwal.'
  )


if __name__ == '__main__':
  convert_excel_to_config()