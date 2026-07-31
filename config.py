# --- KONFIGURASI WATZAP API & OTENTIKASI ---
WHATSAPP_API_URL = "https://api.watzap.id/v1/send_message"
WHATSAPP_API_KEY = "V3ELWOCBWBWHDEMX"
WHATSAPP_NUMBER_KEY = "4Kpb4E1ohwAcU7XT"

ALLOWED_PHONE_NUMBERS = [
    "6282139934994",
    "6282131229933",
"6282244722287"
]

# Pemetaan file database terpecah berdasarkan wilayah (< 20MB per file)
DB_PARTS_MAPPING = {
    "SURABAYA": [f"surabaya_part{i}.db" for i in range(1, 10)],
    "SIDOARJO": [f"sidoarjo_part{i}.db" for i in range(1, 10)],
    "GRESIK": [f"gresik_part{i}.db" for i in range(1, 10)]
}
