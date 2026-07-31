import streamlit as st
import pandas as pd
import random
import requests
from config import WHATSAPP_API_URL, WHATSAPP_TOKEN, ALLOWED_PHONE_NUMBERS, EXCEL_FILE_PATH

# Konfigurasi Halaman Web
st.set_page_config(
    page_title="Portal Data Perumahan",
    page_icon="🏢",
    layout="wide"
)

# Inisialisasi Session State untuk Session Login & OTP
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "otp_sent" not in st.session_state:
    st.session_state["otp_sent"] = False
if "generated_otp" not in st.session_state:
    st.session_state["generated_otp"] = ""
if "target_phone" not in st.session_state:
    st.session_state["target_phone"] = ""


# Fungsi untuk mengirim OTP via WhatsApp API
def send_whatsapp_otp(phone, otp_code):
    payload = {
        "target": phone,
        "message": f"Kode OTP Login Portal Perumahan Anda adalah: *{otp_code}*. Jangan berikan kode ini kepada siapa pun.",
    }
    headers = {
        "Authorization": WHATSAPP_TOKEN
    }
    try:
        response = requests.post(WHATSAPP_API_URL, data=payload, headers=headers)
        return response.status_code == 200
    except Exception as e:
        print(f"Error WA API: {e}")
        return False


# --- HALAMAN LOGIN & OTP ---
if not st.session_state["authenticated"]:
    st.title("🔐 Login Portal Data Perumahan")
    st.markdown("Silakan masukkan nomor WhatsApp terdaftar untuk menerima kode OTP.")

    with st.form("login_form"):
        phone_input = st.text_input("Nomor WhatsApp (Contoh: 62812345678):")
        submit_phone = st.form_submit_button("Kirim Kode OTP")

        if submit_phone:
            # Validasi apakah nomor terdaftar di config
            if phone_input in ALLOWED_PHONE_NUMBERS:
                otp = str(random.randint(100000, 999999))
                st.session_state["generated_otp"] = otp
                st.session_state["target_phone"] = phone_input
                
                # Kirim OTP
                success = send_whatsapp_otp(phone_input, otp)
                
                # Untuk mode testing lokal jika API belum aktif, kode OTP dimunculkan di terminal/info
                st.session_state["otp_sent"] = True
                st.success(f"Kode OTP telah dikirim ke WhatsApp {phone_input}!")
                # (Catatan dev: Untuk testing tanpa API aktif, Anda bisa lihat terminal atau matikan sementara)
            else:
                st.error("Nomor WhatsApp tidak terdaftar dalam sistem.")

    if st.session_state["otp_sent"]:
        with st.form("otp_form"):
            otp_input = st.text_input("Masukkan 6 Digit Kode OTP:", max_chars=6)
            verify_otp = st.form_submit_button("Verifikasi & Masuk")

            if verify_otp:
                if otp_input == st.session_state["generated_otp"]:
                    st.session_state["authenticated"] = True
                    st.success("Login berhasil! Memuat aplikasi...")
                    st.rerun()
                else:
                    st.error("Kode OTP salah. Silakan coba lagi.")

# --- HALAMAN UTAMA APLIKASI (SETELAH LOGIN) ---
else:
    # Tombol Logout di Sidebar
    if st.sidebar.button("🚪 Keluar / Logout"):
        st.session_state["authenticated"] = False
        st.session_state["otp_sent"] = False
        st.rerun()

    st.title("🏢 Portal Informasi & Pencarian Data Perumahan")
    st.markdown("---")

    # Memuat file Excel secara otomatis dari server/repository
    try:
        excel_file = pd.ExcelFile(EXCEL_FILE_PATH)
        sheet_names = excel_file.sheet_names

        # 1. Navigasi Pilihan Sheet
        st.sidebar.header("📂 Navigasi Data")
        selected_sheet = st.sidebar.selectbox("Pilih Sheet Data:", sheet_names)

        # Membaca sheet aktif
        df = pd.read_excel(EXCEL_FILE_PATH, sheet_name=selected_sheet)
        df.columns = df.columns.str.strip() # Bersihkan spasi header

        # 2. Fitur Kustomisasi Kolom / Header yang Ditampilkan
        st.sidebar.markdown("---")
        st.sidebar.subheader("👁️ Kustomisasi Kolom")
        all_columns = df.columns.tolist()
        
        # Default mencentang semua kolom atau sebagian
        selected_columns = st.sidebar.multiselect(
            "Pilih Kolom yang Ingin Ditampilkan:",
            options=all_columns,
            default=all_columns[:min(5, len(all_columns))] # Default menampilkan 5 kolom pertama
        )

        if not selected_columns:
            st.warning("⚠️ Harap pilih minimal 1 kolom untuk ditampilkan.")
            selected_columns = all_columns

        # 3. Deteksi Otomatis Kolom Pencarian Utama (Kota & Perumahan)
        kota_col = next((col for col in df.columns if 'kota' in col.lower() or 'kabupaten' in col.lower()), None)
        perumahan_col = next((col for col in df.columns if 'perumahan' in col.lower() or 'nama' in col.lower()), None)

        st.sidebar.markdown("---")
        st.sidebar.subheader("🔍 Filter Pencarian")

        filtered_df = df.copy()

        # Filter berdasarkan Kota (Jika kolom kota ditemukan)
        if kota_col:
            daftar_kota = ['Semua Kota'] + sorted(df[kota_col].dropna().astype(str).unique().tolist())
            pilih_kota = st.sidebar.selectbox(f"Filter Berdasarkan {kota_col}:", daftar_kota)
            if pilih_kota != 'Semua Kota':
                filtered_df = filtered_df[filtered_df[kota_col].astype(str) == pilih_kota]

        # Filter berdasarkan Nama Perumahan (Jika kolom perumahan ditemukan)
        if perumahan_col:
            cari_perumahan = st.sidebar.text_input(f"Cari Berdasarkan {perumahan_col}:", "")
            if cari_perumahan:
                filtered_df = filtered_df[filtered_df[perumahan_col].astype(str).str.contains(cari_perumahan, case=False, na=False)]

        # --- TAMPILAN DASHBOARD UTAMA ---
        col1, col2 = st.columns(2)
        col1.metric("📊 Total Data Sesuai Filter", f"{len(filtered_df):,} baris")
        col2.metric("📋 Total Seluruh Data Sheet", f"{len(df):,} baris")

        st.markdown(f"### 📋 Menampilkan Data dari Sheet: `{selected_sheet}`")
        
        # Tampilkan tabel hanya berdasarkan kolom yang dipilih pengguna (Tanpa fitur download/ekspor)
        st.dataframe(filtered_df[selected_columns], use_container_width=True, height=550)

    except FileNotFoundError:
        st.error(f"❌ File database `{EXCEL_FILE_PATH}` tidak ditemukan di direktori server. Harap pastikan file Excel sudah di-upload ke repository GitHub.")
    except Exception as e:
        st.error(f"Terjadi kesalahan sistem saat memuat data: {e}")
