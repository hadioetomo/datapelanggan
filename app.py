import streamlit as st
import pandas as pd
import sqlite3
import os
import random
import requests
from config import WHATSAPP_API_URL, WHATSAPP_TOKEN, ALLOWED_PHONE_NUMBERS, DB_PARTS_MAPPING

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
        st.sidebar.header("📂 Navigasi Wilayah")
        # Hanya tampilkan wilayah yang file part 1 nya benar-benar ada
        available_regions = [reg for reg, parts in DB_PARTS_MAPPING.items() if os.path.exists(parts[0])]

        if not available_regions:
            st.error("⚠️ Tidak ditemukan file database pecahan part di direktori server.")
            st.stop()

        selected_region = st.sidebar.selectbox("Pilih Wilayah:", available_regions)
        
        # Ambil daftar file part yang benar-benar ada di disk
        valid_db_files = [f for f in DB_PARTS_MAPPING[selected_region] if os.path.exists(f)]

        # Ambil struktur kolom dari part pertama
        sample_conn = sqlite3.connect(valid_db_files[0])
        sample_df = pd.read_sql(f"SELECT * FROM [{selected_region}] LIMIT 5", sample_conn)
        all_columns = sample_df.columns.tolist()
        sample_conn.close()

        # Kustomisasi Kolom Tampilan
        st.sidebar.markdown("---")
        st.sidebar.subheader("👁️ Kustomisasi Kolom")
        selected_columns = st.sidebar.multiselect(
            "Pilih Kolom yang Ditampilkan:",
            options=all_columns,
            default=all_columns[:min(5, len(all_columns))]
        )
        if not selected_columns:
            selected_columns = all_columns

        # Deteksi Kolom (Kota & Nama Pelanggan)
        kota_col = next((col for col in all_columns if 'kota' in col.lower() or 'kabupaten' in col.lower()), None)
        pelanggan_col = next((col for col in all_columns if 'nama' in col.lower() or 'pelanggan' in col.lower() or 'customer' in col.lower()), None)

        st.sidebar.markdown("---")
        st.sidebar.subheader("🔍 Filter Pencarian")

        pilih_kota = "Semua Kota"
        if kota_col:
            # Ambil daftar kota unik dari seluruh part database wilayah tersebut
            all_cities = set()
            for db_f in valid_db_files:
                c_conn = sqlite3.connect(db_f)
                c_curs = c_conn.cursor()
                c_curs.execute(f"SELECT DISTINCT [{kota_col}] FROM [{selected_region}] WHERE [{kota_col}] IS NOT NULL")
                for r in c_curs.fetchall():
                    all_cities.add(str(r[0]))
                c_conn.close()
            daftar_kota = ['Semua Kota'] + sorted(list(all_cities))
            pilih_kota = st.sidebar.selectbox(f"Filter Berdasarkan {kota_col}:", daftar_kota)

        cari_pelanggan = ""
        if pelanggan_col:
            cari_pelanggan = st.sidebar.text_input(f"Cari Berdasarkan {pelanggan_col}:", "")

        # Gabungkan pencarian dari semua file part database wilayah tersebut
        filtered_dfs = []
        total_rows_all = 0

        for db_f in valid_db_files:
            conn = sqlite3.connect(db_f)
            cursor = conn.cursor()
            
            # Hitung total baris keseluruhan per part
            cursor.execute(f"SELECT COUNT(*) FROM [{selected_region}]")
            total_rows_all += cursor.fetchone()[0]

            query = f"SELECT * FROM [{selected_region}]"
            conditions = []
            if pilih_kota != 'Semua Kota' and kota_col:
                conditions.append(f"[{kota_col}] = '{pilih_kota}'")
            if cari_pelanggan and pelanggan_col:
                conditions.append(f"[{pelanggan_col}] LIKE '%{cari_pelanggan}%'")
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            part_df = pd.read_sql(query, conn)
            filtered_dfs.append(part_df)
            conn.close()

        # Gabungkan hasil filter dari semua part
        df_filtered = pd.concat(filtered_dfs, ignore_index=True)

        # Dashboard Tampilan Utama
        col1, col2 = st.columns(2)
        col1.metric("📊 Data Pelanggan Ditemukan", f"{len(df_filtered):,} baris")
        col2.metric(f"📋 Total Seluruh Pelanggan {selected_region}", f"{total_rows_all:,} baris")

        st.markdown(f"### 📋 Menampilkan Data Pelanggan Wilayah: `{selected_region}`")
        st.dataframe(df_filtered[selected_columns], use_container_width=True, height=550)

    except Exception as e:
        st.error(f"Terjadi kesalahan saat memuat data: {e}")
