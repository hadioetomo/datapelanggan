import streamlit as st
import pandas as pd
import sqlite3
import random
import requests
from config import WHATSAPP_API_URL, WHATSAPP_TOKEN, ALLOWED_PHONE_NUMBERS, DB_MAPPING

# Konfigurasi Halaman Web
st.set_page_config(
    page_title="Portal Data Pelanggan",
    page_icon="👥",
    layout="wide"
)

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "otp_sent" not in st.session_state:
    st.session_state["otp_sent"] = False
if "generated_otp" not in st.session_state:
    st.session_state["generated_otp"] = ""
if "target_phone" not in st.session_state:
    st.session_state["target_phone"] = ""

def send_whatsapp_otp(phone, otp_code):
    payload = {
        "target": phone,
        "message": f"Kode OTP Login Portal Data Pelanggan Anda adalah: *{otp_code}*. Jangan berikan kepada siapapun.",
    }
    headers = {"Authorization": WHATSAPP_TOKEN}
    try:
        response = requests.post(WHATSAPP_API_URL, data=payload, headers=headers)
        return response.status_code == 200
    except:
        return False

# --- HALAMAN LOGIN ---
if not st.session_state["authenticated"]:
    st.title("🔐 Login Portal Data Pelanggan")
    with st.form("login_form"):
        phone_input = st.text_input("Nomor WhatsApp (Contoh: 62812345678):")
        submit_phone = st.form_submit_button("Kirim Kode OTP")

        if submit_phone:
            if phone_input in ALLOWED_PHONE_NUMBERS:
                otp = str(random.randint(100000, 999999))
                st.session_state["generated_otp"] = otp
                st.session_state["target_phone"] = phone_input
                send_whatsapp_otp(phone_input, otp)
                st.session_state["otp_sent"] = True
                st.success(f"Kode OTP dikirim ke {phone_input}!")
            else:
                st.error("Nomor WhatsApp tidak terdaftar.")

    if st.session_state["otp_sent"]:
        with st.form("otp_form"):
            otp_input = st.text_input("Masukkan 6 Digit Kode OTP:", max_chars=6)
            verify_otp = st.form_submit_button("Verifikasi & Masuk")
            if verify_otp:
                if otp_input == st.session_state["generated_otp"]:
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("Kode OTP salah.")

# --- HALAMAN UTAMA ---
else:
    if st.sidebar.button("🚪 Keluar / Logout"):
        st.session_state["authenticated"] = False
        st.session_state["otp_sent"] = False
        st.rerun()

    st.title("👥 Portal Informasi & Pencarian Data Pelanggan")
    st.markdown("---")

    try:
        # 1. Navigasi Wilayah berdasarkan database terpisah
        st.sidebar.header("📂 Navigasi Wilayah")
        selected_region = st.sidebar.selectbox("Pilih Wilayah:", list(DB_MAPPING.keys()))
        
        db_file = DB_MAPPING[selected_region]
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            st.error(f"⚠️ Tabel data untuk wilayah {selected_region} tidak ditemukan.")
            st.stop()
        
        active_table = tables[0]

        # Ambil sampel kolom
        sample_df = pd.read_sql(f"SELECT * FROM [{active_table}] LIMIT 5", conn)
        all_columns = sample_df.columns.tolist()

        # 2. Kustomisasi Kolom Tampilan
        st.sidebar.markdown("---")
        st.sidebar.subheader("👁️ Kustomisasi Kolom")
        selected_columns = st.sidebar.multiselect(
            "Pilih Kolom yang Ditampilkan:",
            options=all_columns,
            default=all_columns[:min(5, len(all_columns))]
        )

        if not selected_columns:
            selected_columns = all_columns

        # 3. Deteksi Kolom (Kota & Nama Pelanggan)
        kota_col = next((col for col in all_columns if 'kota' in col.lower() or 'kabupaten' in col.lower()), None)
        pelanggan_col = next((col for col in all_columns if 'nama' in col.lower() or 'pelanggan' in col.lower() or 'customer' in col.lower()), None)

        st.sidebar.markdown("---")
        st.sidebar.subheader("🔍 Filter Pencarian")

        query = f"SELECT * FROM [{active_table}]"
        conditions = []

        if kota_col:
            cursor.execute(f"SELECT DISTINCT [{kota_col}] FROM [{active_table}] WHERE [{kota_col}] IS NOT NULL")
            daftar_kota = ['Semua Kota'] + sorted([str(r[0]) for r in cursor.fetchall()])
            pilih_kota = st.sidebar.selectbox(f"Filter Berdasarkan {kota_col}:", daftar_kota)
            if pilih_kota != 'Semua Kota':
                conditions.append(f"[{kota_col}] = '{pilih_kota}'")

        if pelanggan_col:
            cari_pelanggan = st.sidebar.text_input(f"Cari Berdasarkan {pelanggan_col}:", "")
            if cari_pelanggan:
                conditions.append(f"[{pelanggan_col}] LIKE '%{cari_pelanggan}%'")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        df_filtered = pd.read_sql(query, conn)
        
        cursor.execute(f"SELECT COUNT(*) FROM [{active_table}]")
        total_rows = cursor.fetchone()[0]
        conn.close()

        # Dashboard Tampilan Utama
        col1, col2 = st.columns(2)
        col1.metric("📊 Data Pelanggan Ditemukan", f"{len(df_filtered):,} baris")
        col2.metric(f"📋 Total Seluruh Pelanggan {selected_region}", f"{total_rows:,} baris")

        st.markdown(f"### 📋 Menampilkan Data Pelanggan Wilayah: `{selected_region}`")
        st.dataframe(df_filtered[selected_columns], use_container_width=True, height=550)

    except Exception as e:
        st.error(f"Terjadi kesalahan saat memuat data: {e}")
