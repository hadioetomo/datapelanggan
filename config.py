# --- KONFIGURASI WHATSAPP API & OTENTIKASI ---
# Ganti dengan kredensial WhatsApp Gateway Anda (Contoh menggunakan format umum API Gateway)
WHATSAPP_API_URL = "https://api.fonnte.com/send"  # Contoh: Fonnte, Wablas, dll.
WHATSAPP_TOKEN = "MASUKKAN_TOKEN_API_ANDA_DI_SINI"

# Daftar nomor WhatsApp yang diizinkan untuk login (Format: 628xxxxxxxxxx)
# Jika ingin dinamis dari database/file, bisa disesuaikan nanti.
ALLOWED_PHONE_NUMBERS = [
    "6281234567890",
    "6289876543210"
]

# Nama file Excel sumber data (Pastikan file ini ada di satu folder dengan app.py)
EXCEL_FILE_PATH = "data_perumahan.xlsx"
