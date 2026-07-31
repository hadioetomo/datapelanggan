import streamlit as st
import pandas as pd
import sqlite3
import os
import random
import time
import requests
from config import (
    WHATSAPP_API_URL, 
    WHATSAPP_API_KEY, 
    WHATSAPP_NUMBER_KEY, 
    ALLOWED_PHONE_NUMBERS, 
    DB_PARTS_MAPPING
)

# Konfigurasi Halaman Web
st.set_page_config(
    page_title="Portal Data Pelanggan",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- STYLING CSS CUSTOM & BERWARNA ---
st.markdown("""
    <style>
        .stApp {
            background-color: #F4F6F9;
        }
        .main-header {
            font-size: 26px;
            font-weight: 800;
            background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0px;
        }
        .sub-header {
            font-size: 13px;
            color: #64748B;
            margin-bottom: 20px;
            font-weight: 500;
        }
        .filter-container {
            background: #FFFFFF;
            border-top: 4px solid #3B82F6;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            margin-bottom: 20px;
        }
    </style>
""", unsafe_allow_html=True)

# Konstanta Waktu (dalam detik)
SESSION_TIMEOUT = 30 * 60   # Sesi Login bertahan maksimal 30 Menit
OTP_TIMEOUT = 2 * 60        # Kode OTP kedaluwarsa dalam 2 Menit

# Inisialisasi Session State
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "login_time" not in st.session_state:
    st.session_state["login_time"] = 0
if "otp_sent" not in st.session_state:
    st.session_state["otp_sent"] = False
if "otp_time" not in st.session_state:
    st.session_state["otp_time"] = 0
if "generated_otp" not in st.session_state:
    st.session_state["generated_otp"] = ""
if "target_phone" not in st.session_state:
    st.session_state["target_phone"] = ""

# Cek Kedaluwarsa Sesi Login (30 Menit)
if st.session_state["authenticated"]:
    if time.time() - st.session_state["login_time"] > SESSION_TIMEOUT:
        st.session_state["authenticated"] = False
        st.warning("⏱️ Sesi login Anda telah berakhir (30 menit). Silakan login kembali.")
        st.rerun()

def send_whatsapp_otp(phone, otp_code):
    payload = {
        "api_key": WHATSAPP_API_KEY,
        "number_key": WHATSAPP_NUMBER_KEY,
        "phone_no": phone,
        "message": f"Kode OTP Login Portal Data Pelanggan Anda adalah: *{otp_code}*. Berlaku selama 2 menit."
    }
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(WHATSAPP_API_URL, json=payload, headers=headers)
        if response.status_code == 200:
            res_data = response.json()
            return res_data.get("status") == 200 or res_data.get("code") == 200 or "success" in str(res_data).lower()
        return False
    except Exception as e:
        print(f"Error Watzap API: {e}")
        return False

# --- HALAMAN LOGIN & OTP ---
if not st.session_state["authenticated"]:
    col1, col2, col3 = st.columns([1, 2.2, 1])
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 💎 Portal Akses Pelanggan Eksekutif")
        st.markdown("Autentikasi aman via WhatsApp Gateway.")

        with st.form("login_form"):
            phone_input = st.text_input("📱 Nomor WhatsApp (Contoh: 62812345678):")
            submit_phone = st.form_submit_button("🚀 Kirim Kode OTP", use_container_width=True)

            if submit_phone:
                if phone_input in ALLOWED_PHONE_NUMBERS:
                    otp = str(random.randint(100000, 999999))
                    st.session_state["generated_otp"] = otp
                    st.session_state["target_phone"] = phone_input
                    st.session_state["otp_time"] = time.time()

                    send_whatsapp_otp(phone_input, otp)
                    st.session_state["otp_sent"] = True
                    st.success(f"✅ OTP terkirim ke {phone_input} (Berlaku 2 Menit)!")
                else:
                    st.error("❌ Nomor WhatsApp tidak terdaftar dalam sistem.")

        if st.session_state["otp_sent"]:
            with st.form("otp_form"):
                otp_input = st.text_input("🔑 Masukkan 6 Digit Kode OTP:", max_chars=6)
                verify_otp = st.form_submit_button("✨ Verifikasi & Masuk", use_container_width=True)

                if verify_otp:
                    if time.time() - st.session_state["otp_time"] > OTP_TIMEOUT:
                        st.error("❌ Kode OTP telah kedaluwarsa. Silakan kirim ulang.")
                        st.session_state["otp_sent"] = False
                    elif otp_input == st.session_state["generated_otp"]:
                        st.session_state["authenticated"] = True
                        st.session_state["login_time"] = time.time()
                        st.success("🎉 Login berhasil! Memuat data...")
                        st.rerun()
                    else:
                        st.error("❌ Kode OTP salah.")

# --- HALAMAN UTAMA APLIKASI (SETELAH LOGIN) ---
else:
    # Sidebar Informasi & Logout
    st.sidebar.markdown("### 🛡️ Keamanan Akun")
    st.sidebar.success(f"Aktif: `{st.session_state['target_phone']}`")
    if st.sidebar.button("🚪 Keluar (Logout)", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["otp_sent"] = False
        st.rerun()

    available_regions = [reg for reg, parts in DB_PARTS_MAPPING.items() if os.path.exists(parts[0])]
    if not available_regions:
        st.error("⚠️ Tidak ditemukan file database pecahan part di direktori server.")
        st.stop()

    # Header Utama Web
    st.markdown('<p class="main-header">💎 Portal Informasi & Direktori Pelanggan</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Sistem pencarian data cepat, responsif, dan terintegrasi per wilayah</p>', unsafe_allow_html=True)

    # Pilih Wilayah (Database) di Atas
    selected_region = st.selectbox("📂 Pilih Wilayah Database Utama:", available_regions)
    valid_db_files = [f for f in DB_PARTS_MAPPING[selected_region] if os.path.exists(f)]

    # Ambil sampel kolom dari part pertama database
    sample_conn = sqlite3.connect(valid_db_files[0])
    sample_df = pd.read_sql(f"SELECT * FROM [{selected_region}] LIMIT 5", sample_conn)
    all_columns = [col.strip() for col in sample_df.columns]
    sample_conn.close()

    def find_col(keywords):
        for col in all_columns:
            if any(k in col.lower() for k in keywords):
                return col
        return None

    c_kota = find_col(['kota', 'kabupaten'])
    c_building = find_col(['building_type', 'tipe_bangunan', 'jenis_bangunan'])
    c_district = find_col(['district', 'kecamatan', 'area'])
    c_cluster = find_col(['cluster_name', 'cluster', 'nama_lokasi'])
    c_homepass = find_col(['homepass_id', 'homepass', 'id_homepass'])
    c_status = find_col(['home_pass_status', 'status'])
    c_class = find_col(['class', 'kelas'])
    c_contract = find_col(['contract_account', 'account', 'contract'])
    c_package = find_col(['package', 'paket'])
    c_network = find_col(['network_type', 'network'])

    c_street = find_col(['street_name', 'street', 'nama_jalan', 'jalan'])
    c_house = find_col(['house_number', 'house_no', 'nomor_rumah', 'no_rumah'])
    c_block = find_col(['block', 'blok'])
    c_rt = find_col(['rt'])
    c_rw = find_col(['rw'])

    # --- KOTAK FILTER & PENCARIAN DI HALAMAN UTAMA ---
    st.markdown("### 🔍 Panel Filter & Pencarian Cepat")

    with st.container():
        st.markdown('<div class="filter-container">', unsafe_allow_html=True)

        keyword_search = st.text_input("🔎 Cari Berdasarkan ID, Nama Lokasi, Akun, atau Jalan:", "", placeholder="Ketik kata kunci pencarian...")

        col_f1, col_f2, col_f3 = st.columns(3)

        pilih_kota = "Semua Kota"
        if c_kota:
            all_cities = set()
            for db_f in valid_db_files:
                c_conn = sqlite3.connect(db_f)
                c_curs = c_conn.cursor()
                c_curs.execute(f"SELECT DISTINCT [{c_kota}] FROM [{selected_region}] WHERE [{c_kota}] IS NOT NULL")
                for r in c_curs.fetchall():
                    all_cities.add(str(r[0]))
                c_conn.close()
            daftar_kota = ['Semua Kota'] + sorted(list(all_cities))
            with col_f1:
                pilih_kota = st.selectbox("📍 Pilih Kota:", daftar_kota)

        pilih_building = "Semua Jenis"
        if c_building:
            all_buildings = set()
            for db_f in valid_db_files:
                c_conn = sqlite3.connect(db_f)
                c_curs = c_conn.cursor()
                c_curs.execute(f"SELECT DISTINCT [{c_building}] FROM [{selected_region}] WHERE [{c_building}] IS NOT NULL")
                for r in c_curs.fetchall():
                    all_buildings.add(str(r[0]))
                c_conn.close()
            daftar_building = ['Semua Jenis'] + sorted(list(all_buildings))
            with col_f2:
                pilih_building = st.selectbox("🏢 Jenis Perumahan:", daftar_building)

        pilih_district = "Semua Area"
        if c_district:
            all_districts = set()
            for db_f in valid_db_files:
                c_conn = sqlite3.connect(db_f)
                c_curs = c_conn.cursor()
                c_curs.execute(f"SELECT DISTINCT [{c_district}] FROM [{selected_region}] WHERE [{c_district}] IS NOT NULL")
                for r in c_curs.fetchall():
                    all_districts.add(str(r[0]))
                c_conn.close()
            daftar_district = ['Semua Area'] + sorted(list(all_districts))
            with col_f3:
                pilih_district = st.selectbox("📍 Pilih Area (District):", daftar_district)

        st.markdown('</div>', unsafe_allow_html=True)

    # Eksekusi Query Multi-Part Database
    filtered_dfs = []
    total_rows_all = 0

    for db_f in valid_db_files:
        conn = sqlite3.connect(db_f)
        cursor = conn.cursor()

        cursor.execute(f"SELECT COUNT(*) FROM [{selected_region}]")
        total_rows_all += cursor.fetchone()[0]

        query = f"SELECT * FROM [{selected_region}]"
        conditions = []

        if pilih_kota != 'Semua Kota' and c_kota:
            conditions.append(f"[{c_kota}] = '{pilih_kota}'")
        if pilih_building != 'Semua Jenis' and c_building:
            conditions.append(f"[{c_building}] = '{pilih_building}'")
        if pilih_district != 'Semua Area' and c_district:
            conditions.append(f"[{c_district}] = '{pilih_district}'")

        if keyword_search:
            search_conditions = []
            search_targets = [c_homepass, c_cluster, c_contract, c_package, c_street]
            search_targets = [t for t in search_targets if t is not None]

            for target in search_targets:
                search_conditions.append(f"[{target}] LIKE '%{keyword_search}%'")

            if search_conditions:
                conditions.append(f"(" + " OR ".join(search_conditions) + ")")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        part_df = pd.read_sql(query, conn)
        filtered_dfs.append(part_df)
        conn.close()

    df_filtered = pd.concat(filtered_dfs, ignore_index=True)

    # Tampilan Metrik Berwarna di Atas Tabel
    m1, m2, m3 = st.columns(3)
    m1.metric("📊 Data Ditemukan", f"{len(df_filtered):,} baris")
    m2.metric("📋 Total Keseluruhan Data", f"{total_rows_all:,} baris")
    m3.metric("📌 Wilayah Aktif", selected_region)
    st.markdown("---")

    # Kolom Hasil Tampilan Tabel
    col_mapping_target = {
        "Homepass ID": c_homepass,
        "Nama Lokasi (Cluster)": c_cluster,
        "Street Name": c_street,
        "House No": c_house,
        "Block": c_block,
        "RT": c_rt,
        "RW": c_rw,
        "Home Pass Status": c_status,
        "Class": c_class,
        "Contract Account": c_contract,
        "Package": c_package,
        "Network Type": c_network
    }

    active_display_labels = []
    active_db_columns = []

    for label, col_name in col_mapping_target.items():
        if col_name and col_name in df_filtered.columns:
            active_display_labels.append(label)
            active_db_columns.append(col_name)

    if active_db_columns:
        display_df = df_filtered[active_db_columns].copy()
        display_df.columns = active_display_labels

        st.markdown(f"### 📋 Hasil Direktori Pelanggan — **{selected_region}**")
        # Menggunakan sorting bawaan tabel Streamlit (cukup klik header kolom di tabel)
        st.dataframe(display_df, use_container_width=True, height=580)
    else:
        st.warning("⚠️ Kolom spesifik tidak terdeteksi otomatis. Menampilkan seluruh kolom tersedia:")
        st.dataframe(df_filtered, use_container_width=True, height=580)