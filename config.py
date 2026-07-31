# --- KONFIGURASI WHATSAPP API & OTENTIKASI ---
WHATSAPP_API_URL = "https://api.fonnte.com/send"
WHATSAPP_TOKEN = "MASUKKAN_TOKEN_API_ANDA_DISINI"

ALLOWED_PHONE_NUMBERS = [
    "6281234567890",
    "6289876543210"
]

# Pemetaan file database terpecah berdasarkan wilayah (< 20MB per file)
DB_PARTS_MAPPING = {
    "SURABAYA": [f"surabaya_part{i}.db" for i in range(1, 10)],
    "SIDOARJO": [f"sidoarjo_part{i}.db" for i in range(1, 10)],
    "GRESIK": [f"gresik_part{i}.db" for i in range(1, 10)]
}
