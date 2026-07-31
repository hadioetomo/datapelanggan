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
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Styling Tambahan agar Tampilan Lebih Menarik & Profesional
st.markdown("""
    <style>
        .main-header {
            font-size: 28px;
            font-weight: 700;
            color: #1E3A8A;
            margin-bottom: 0px;
        }
        .sub-header {
            font-size: 14px;
            color: #64748B;
            margin-bottom: 20px;
        }
        .metric-card {
            background-color: #F8FAFC;
            border: 1px solid #E2E8F0;
            padding: 15px;
            border-radius: 8px;
        }
    </style>
""", unsafe_allow_html=True)

# Durasi Sesi Login (30 Menit dalam detik)
SESSION_TIMEOUT = 30 * 60 

# Inisialisasi Session State untuk Sesi, Login, & OTP
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "login_time" not in st.session_state:
    st.session_state["login_time"] = 0
if "otp_sent" not in st.session_state:
    st.session_state["otp_sent"] = False
if "generated_otp" not in st.session_state:
    st.session_state["generated_otp"] = ""
if "target_phone" not in st.session_state:
    st.session_state["target_phone"] = ""

# Cek Kedaluwarsa Sesi (30 Menit)
if st.session_state["authenticated"]:
    if time.time() - st.session_state["login_time"] > SESSION_TIMEOUT:
        st.session_state["authenticated"] = False
        st.warning("⏱️ Sesi login Anda telah habis (30 menit). Silakan login kembali.")
        st.rerun()

def send_whatsapp_otp(phone, otp_code):
    payload = {
        "api_key": WHATSAPP_API_KEY,
        "number_key": WHATSAPP_NUMBER_KEY,
        "phone_no": phone,
        "message": f"Kode OTP Login Portal Data Pelanggan Anda adalah: *{otp_code}*. Berlaku selama 30 menit."
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
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("### 🔐 Autentikasi Masuk Portal")
        st.markdown("Masukkan nomor WhatsApp yang terdaftar untuk menerima kode verifikasi OTP.")

        with st.form("login_form"):
            phone_input = st.text_input("Nomor WhatsApp (Contoh: 62812345678):")
            submit_phone = st.form_submit_button("📩 Kirim Kode OTP", use_container_width=True)

            if submit_phone:
                if phone_input in ALLOWED_PHONE_NUMBERS:
                    otp = str(random.randint(100000, 999999))
                    st.session_state["generated_otp"] = otp
                    st.session_state["target_phone"] = phone_input
                    
                    send_whatsapp_otp(phone_input, otp)
                    st.session_state["otp_sent"] = True
                    st.success(f"Kode OTP terkirim ke WhatsApp {phone_input}!")
                else:
                    st.error("❌ Nomor WhatsApp tidak terdaftar dalam sistem.")

        if st.session_state["otp_sent"]:
            with st.form("otp_form"):
                otp_input = st.text_input("Masukkan 6 Digit Kode OTP:", max_chars=6)
                verify_otp = st.form_submit_button("✨ Verifikasi & Masuk", use_container_width=True)

                if verify_otp:
                    if otp_input == st.session_state["generated_otp"]:
                        st.session_state["authenticated"] = True
                        st.session_state["login_time"] = time.time()  # Catat waktu mulai sesi
                        st.success("Login berhasil!")
                        st.rerun()
                    else:
                        st.error("❌ Kode OTP salah. Silakan coba lagi.")

# --- HALAMAN UTAMA APLIKASI (SETELAH LOGIN) ---
else:
    # Sidebar Navigasi & Logout
    st.sidebar.markdown("### 👤 Akun Terautentikasi")
    st.sidebar.info(f"Login via: `{st.session_state['target_phone']}`")
    
    if st.sidebar.button("🚪 Keluar (Logout)", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["otp_sent"] = False
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.header("📂 Navigasi Wilayah")
    
    available_regions = [reg for reg, parts in DB_PARTS_MAPPING.items() if os.path.exists(parts[0])]
    if not available_regions:
        st.error("⚠️ Tidak ditemukan file database pecahan part di direktori server.")
        st.stop()

    selected_region = st.sidebar.selectbox("Pilih Wilayah (Database):", available_regions)
    valid_db_files = [f for f in DB_PARTS_MAPPING[selected_region] if os.path.exists(f)]

    # Ambil sampel kolom dari part pertama database
    sample_conn = sqlite3.connect(valid_db_files[0])
    sample_df = pd.read_sql(f"SELECT * FROM [{selected_region}] LIMIT 5", sample_conn)
    all_columns = [col.strip() for col in sample_df.columns]
    sample_conn.close()

    # Mapping nama kolom fleksibel di database
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

    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Filter Data Utama")

    # 1. Pilihan Kota (Surabaya, Gresik, Sidoarjo)
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
        pilih_kota = st.sidebar.selectbox("Pilih Kota:", daftar_kota)

    # 2. Pilihan Jenis Perumahan berdasarkan building_type
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
        pilih_building = st.sidebar.selectbox("Jenis Perumahan (Building Type):", daftar_building)

    # 3. Pilihan Berdasarkan Area (district)
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
        pilih_district = st.sidebar.selectbox("Pilih Area (District):", daftar_district)

    # Header Utama Web
    st.markdown('<p class="main-header">🏢 Portal Informasi & Direktori Data Pelanggan</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-header">Menampilkan data terintegrasi untuk wilayah: <b>{selected_region}</b> (Sesi aktif selama 30 menit)</p>', unsafe_allow_html=True)
    st.markdown("---")

    # Eksekusi Query Penggabungan Multi-Part Database Berdasarkan Filter
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

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        part_df = pd.read_sql(query, conn)
        filtered_dfs.append(part_df)
        conn.close()

    df_filtered = pd.concat(filtered_dfs, ignore_index=True)

    # Tampilan Metrik Atas (Dashboard Cards)
    m1, m2, m3 = st.columns(3)
    m1.metric("📊 Data Sesuai Filter", f"{len(df_filtered):,} baris")
    m2.metric("📋 Total Keseluruhan Data", f"{total_rows_all:,} baris")
    m3.metric("📂 Wilayah Aktif", selected_region)
    st.markdown("---")

    # Menentukan Kolom Khusus yang Diminta untuk Ditampilkan:
    # Homepass ID, Nama Lokasi (cluster_name), Home Pass Status, Class, Contract Account, Package, Network Type
    target_display_cols = []
    
    # Mapping kolom secara aman berdasarkan ketersediaan di database
    col_mapping_target = {
        "Homepass ID": c_homepass,
        "Nama Lokasi (Cluster)": c_cluster,
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

    # Jika kolom spesifik ditemukan, tampilkan tabelnya dengan format rapi
    if active_db_columns:
        display_df = df_filtered[active_db_columns].copy()
        display_df.columns = active_display_labels  # Ubah nama header tabel agar sesuai permintaan
        
        st.markdown(f"### 📋 Hasil Data Pelanggan ({selected_region})")
        st.dataframe(display_df, use_container_width=True, height=580)
    else:
        st.warning("⚠️ Kolom spesifik (Homepass ID, Cluster, Status, dll) tidak terdeteksi secara otomatis di struktur database ini. Menampilkan seluruh kolom tersedia:")
        st.dataframe(df_filtered, use_container_width=True, height=580)
