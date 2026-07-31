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

# 1. Konfigurasi Halaman Web
st.set_page_config(
    page_title="Portal Data Pelanggan Eksekutif",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Styling CSS Custom Modern & Elegan
st.markdown("""
    <style>
        /* Modern Clean Background */
        .stApp {
            background-color: #F8FAFC;
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
        }
        
        /* Main Header Styling */
        .main-header {
            font-size: 28px;
            font-weight: 800;
            background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 2px;
            letter-spacing: -0.5px;
        }
        .sub-header {
            font-size: 14px;
            color: #64748B;
            margin-bottom: 24px;
            font-weight: 500;
        }

        /* Filter Panel Container */
        .filter-container {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-top: 4px solid #3B82F6;
            padding: 24px;
            border-radius: 16px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.03), 0 4px 6px -2px rgba(0, 0, 0, 0.02);
            margin-bottom: 24px;
        }

        /* Login Card Container */
        .login-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            padding: 32px;
            border-radius: 20px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05), 0 10px 10px -5px rgba(0, 0, 0, 0.02);
        }

        /* Metric Styling Custom */
        div[data-testid="stMetric"] {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-left: 5px solid #3B82F6;
            padding: 16px;
            border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }
        div[data-testid="stMetricLabel"] {
            font-size: 13px !important;
            color: #64748B !important;
            font-weight: 600 !important;
        }
        div[data-testid="stMetricValue"] {
            font-size: 22px !important;
            color: #0F172A !important;
            font-weight: 700 !important;
        }

        /* Input Custom Styling */
        .stTextInput > div > div > input {
            border-radius: 8px !important;
            border: 1px solid #CBD5E1 !important;
        }
        .stTextInput > div > div > input:focus {
            border-color: #3B82F6 !important;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15) !important;
        }
        
        /* General Buttons */
        .stButton>button {
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
        }
        .stButton>button:hover {
            transform: translateY(-1px);
        }
    </style>
""", unsafe_allow_html=True)

# Konstanta Waktu (dalam detik)
SESSION_TIMEOUT = 30 * 60   # 30 Menit
OTP_TIMEOUT = 2 * 60        # 2 Menit
OTP_COOLDOWN = 60           # 60 Detik Jeda Kirim Ulang OTP

# 3. Inisialisasi Session State
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "login_time" not in st.session_state:
    st.session_state["login_time"] = 0
if "otp_sent" not in st.session_state:
    st.session_state["otp_sent"] = False
if "otp_time" not in st.session_state:
    st.session_state["otp_time"] = 0
if "last_otp_request_time" not in st.session_state:
    st.session_state["last_otp_request_time"] = 0
if "generated_otp" not in st.session_state:
    st.session_state["generated_otp"] = ""
if "target_phone" not in st.session_state:
    st.session_state["target_phone"] = ""
if "current_page" not in st.session_state:
    st.session_state["current_page"] = 1

# Cek Kedaluwarsa Sesi Login (30 Menit)
if st.session_state["authenticated"]:
    if time.time() - st.session_state["login_time"] > SESSION_TIMEOUT:
        st.session_state["authenticated"] = False
        st.warning("⏱️ Sesi login Anda telah berakhir (30 menit). Silakan login kembali.")
        st.rerun()

# 4. Fungsi Kirim OTP via WhatsApp
def send_whatsapp_otp(phone, otp_code):
    payload = {
        "api_key": WHATSAPP_API_KEY,
        "number_key": WHATSAPP_NUMBER_KEY,
        "phone_no": phone,
        "message": f"Kode OTP Login Portal Data Pelanggan Anda adalah: *{otp_code}*. Berlaku selama 2 menit."
    }
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(WHATSAPP_API_URL, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            res_data = response.json()
            return res_data.get("status") == 200 or res_data.get("code") == 200 or "success" in str(res_data).lower()
        return False
    except Exception as e:
        print(f"Error Watzap API: {e}")
        return False

# 5. Fungsi Caching Query Dropdown (Mengoptimalkan RAM & Kecepatan Database)
@st.cache_data(ttl=3600)
def get_distinct_values(db_files, region, column_name):
    if not column_name:
        return []
    distinct_set = set()
    for db_f in db_files:
        if os.path.exists(db_f):
            conn = sqlite3.connect(db_f)
            curs = conn.cursor()
            try:
                curs.execute(f"SELECT DISTINCT [{column_name}] FROM [{region}] WHERE [{column_name}] IS NOT NULL AND [{column_name}] != ''")
                for r in curs.fetchall():
                    distinct_set.add(str(r[0]))
            except Exception:
                pass
            conn.close()
    return sorted(list(distinct_set))

def mask_phone_number(phone):
    if len(phone) > 7:
        return phone[:4] + "****" + phone[-4:]
    return phone

# --- HALAMAN LOGIN & OTP ---
if not st.session_state["authenticated"]:
    _, col2, _ = st.columns([1, 1.8, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("### 💎 Portal Akses Eksekutif")
        st.markdown("<p style='color: #64748B; font-size: 14px;'>Autentikasi dua langkah aman via WhatsApp Gateway.</p>", unsafe_allow_html=True)
        st.markdown("---")

        with st.form("login_form"):
            phone_input = st.text_input("📱 Nomor WhatsApp (Contoh: 62812345678):")
            submit_phone = st.form_submit_button("🚀 Kirim Kode OTP", use_container_width=True)

            if submit_phone:
                time_since_last = time.time() - st.session_state["last_otp_request_time"]
                if time_since_last < OTP_COOLDOWN:
                    sisa_waktu = int(OTP_COOLDOWN - time_since_last)
                    st.warning(f"⏳ Mohon tunggu {sisa_waktu} detik sebelum meminta OTP kembali.")
                elif phone_input in ALLOWED_PHONE_NUMBERS:
                    otp = str(random.randint(100000, 999999))
                    st.session_state["generated_otp"] = otp
                    st.session_state["target_phone"] = phone_input
                    st.session_state["otp_time"] = time.time()
                    st.session_state["last_otp_request_time"] = time.time()

                    send_whatsapp_otp(phone_input, otp)
                    st.session_state["otp_sent"] = True
                    st.success(f"✅ OTP terkirim ke {phone_input} (Berlaku 2 Menit)!")
                else:
                    st.error("❌ Nomor WhatsApp tidak terdaftar dalam sistem.")

        if st.session_state["otp_sent"]:
            st.markdown("<br>", unsafe_allow_html=True)
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
        st.markdown('</div>', unsafe_allow_html=True)

# --- HALAMAN UTAMA APLIKASI (SETELAH LOGIN) ---
else:
    # Sidebar Informasi Akun & Sesi
    st.sidebar.markdown("### 🛡️ Keamanan Sesi")
    st.sidebar.info(f"Pengguna: `{mask_phone_number(st.session_state['target_phone'])}`")
    
    if st.sidebar.button("🚪 Keluar (Logout)", use_container_width=True, type="secondary"):
        st.session_state["authenticated"] = False
        st.session_state["otp_sent"] = False
        st.rerun()

    available_regions = [reg for reg, parts in DB_PARTS_MAPPING.items() if os.path.exists(parts[0])]
    if not available_regions:
        st.error("⚠️ Tidak ditemukan file database pecahan part di direktori server.")
        st.stop()

    # Header Utama Portal
    st.markdown('<p class="main-header">💎 Portal Informasi & Direktori Pelanggan</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Sistem pencarian data responsif, cepat, dan terintegrasi per wilayah</p>', unsafe_allow_html=True)

    # Pemilihan Database Utama Wilayah
    selected_region = st.selectbox("📂 Pilih Wilayah Database Utama:", available_regions)
    valid_db_files = [f for f in DB_PARTS_MAPPING[selected_region] if os.path.exists(f)]

    # Pemetaan Sampel Kolom Database
    sample_conn = sqlite3.connect(valid_db_files[0])
    sample_df = pd.read_sql(f"SELECT * FROM [{selected_region}] LIMIT 1", sample_conn)
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

    # --- PANEL FILTER & PENCARIAN ---
    st.markdown('<div class="filter-container">', unsafe_allow_html=True)
    st.markdown("##### 🔍 Panel Filter & Pencarian Cepat")

    keyword_search = st.text_input("🔎 Cari Berdasarkan ID, Nama Lokasi, Akun, atau Jalan:", "", placeholder="Ketik kata kunci pencarian...")

    col_f1, col_f2, col_f3 = st.columns(3)

    pilih_kota = "Semua Kota"
    if c_kota:
        daftar_kota = ['Semua Kota'] + get_distinct_values(tuple(valid_db_files), selected_region, c_kota)
        with col_f1:
            pilih_kota = st.selectbox("📍 Pilih Kota:", daftar_kota)

    pilih_building = "Semua Jenis"
    if c_building:
        daftar_building = ['Semua Jenis'] + get_distinct_values(tuple(valid_db_files), selected_region, c_building)
        with col_f2:
            pilih_building = st.selectbox("🏢 Jenis Perumahan:", daftar_building)

    pilih_district = "Semua Area"
    if c_district:
        daftar_district = ['Semua Area'] + get_distinct_values(tuple(valid_db_files), selected_region, c_district)
        with col_f3:
            pilih_district = st.selectbox("📍 Pilih Area (District):", daftar_district)

    st.markdown('</div>', unsafe_allow_html=True)

    # --- KONSTRUKSI QUERY SQL MULTI-PART ---
    conditions = []
    if pilih_kota != 'Semua Kota' and c_kota:
        conditions.append(f"[{c_kota}] = '{pilih_kota}'")
    if pilih_building != 'Semua Jenis' and c_building:
        conditions.append(f"[{c_building}] = '{pilih_building}'")
    if pilih_district != 'Semua Area' and c_district:
        conditions.append(f"[{c_district}] = '{pilih_district}'")

    if keyword_search:
        search_conditions = []
        search_targets = [t for t in [c_homepass, c_cluster, c_contract, c_package, c_street] if t is not None]
        for target in search_targets:
            search_conditions.append(f"[{target}] LIKE '%{keyword_search}%'")
        if search_conditions:
            conditions.append(f"(" + " OR ".join(search_conditions) + ")")

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    # Hitung Jumlah Baris (Count Queries)
    total_matching_rows = 0
    total_db_rows = 0

    for db_f in valid_db_files:
        conn = sqlite3.connect(db_f)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM [{selected_region}]")
        total_db_rows += cursor.fetchone()[0]

        cursor.execute(f"SELECT COUNT(*) FROM [{selected_region}]" + where_clause)
        total_matching_rows += cursor.fetchone()[0]
        conn.close()

    # --- PENGATURAN PAGINATION SERVER-SIDE ---
    rows_per_page = 50
    total_pages = max(1, (total_matching_rows + rows_per_page - 1) // rows_per_page)
    
    col_p1, col_p2, col_p3 = st.columns([2, 3, 2])
    with col_p2:
        page_number = st.number_input(f"📄 Halaman (Total {total_pages} Halaman):", min_value=1, max_value=total_pages, value=1, step=1)
    
    offset = (page_number - 1) * rows_per_page

    # Eksekusi Query Ambil Data Terbatas (Limit & Offset)
    filtered_dfs = []
    accumulated = 0
    rows_needed = rows_per_page
    current_offset = offset

    for db_f in valid_db_files:
        if rows_needed <= 0:
            break
            
        conn = sqlite3.connect(db_f)
        cursor = conn.cursor()
        
        # Hitung baris yang cocok di part file ini
        cursor.execute(f"SELECT COUNT(*) FROM [{selected_region}]" + where_clause)
        part_matches = cursor.fetchone()[0]

        if current_offset >= part_matches:
            current_offset -= part_matches
            conn.close()
            continue

        query = f"SELECT * FROM [{selected_region}]" + where_clause + f" LIMIT {rows_needed} OFFSET {current_offset}"
        part_df = pd.read_sql(query, conn)
        filtered_dfs.append(part_df)

        fetched = len(part_df)
        rows_needed -= fetched
        current_offset = 0  # Offset hanya berlaku untuk part pertama yang match
        conn.close()

    df_filtered = pd.concat(filtered_dfs, ignore_index=True) if filtered_dfs else pd.DataFrame()

    # Tampilan Metrik Ringkas
    m1, m2, m3 = st.columns(3)
    m1.metric("📊 Filter Ditemukan", f"{total_matching_rows:,} baris")
    m2.metric("📋 Total Keseluruhan Data", f"{total_db_rows:,} baris")
    m3.metric("📌 Wilayah Database", selected_region)
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

    if not df_filtered.empty and active_db_columns:
        display_df = df_filtered[active_db_columns].copy()
        display_df.columns = active_display_labels

        st.markdown(f"### 📋 Hasil Direktori Pelanggan — **{selected_region}** *(Menampilkan max {rows_per_page} baris/halaman)*")
        
        # Event Interaktif Pilihan Baris (Row Selection)
        event = st.dataframe(
            display_df, 
            use_container_width=True, 
            height=500,
            selection_mode="single-row",
            on_select="rerun"
        )
        
        # --- FITUR MODAL POP-UP DETAIL DATA ---
        selected_rows = event.selection.get("rows", [])
        if selected_rows:
            row_idx = selected_rows[0]
            selected_data = df_filtered.iloc[row_idx]

            @st.dialog("💎 Detail Informasi Pelanggan")
            def show_detail_dialog(data):
                st.markdown("#### Informasi Alamat & Identitas")
                st.write(f"**Homepass ID:** `{data.get(c_homepass, 'N/A')}`")
                st.write(f"**Nama Lokasi (Cluster):** {data.get(c_cluster, 'N/A')}")
                st.write(f"**Jalan:** {data.get(c_street, 'N/A')} No. {data.get(c_house, '-')} (Blok {data.get(c_block, '-')})")
                st.write(f"**RT/RW:** {data.get(c_rt, '-')}/{data.get(c_rw, '-')}")
                st.markdown("---")
                st.markdown("#### Informasi Layanan & Kontrak")
                st.write(f"**Status Homepass:** `{data.get(c_status, 'N/A')}`")
                st.write(f"**Nomor Kontrak:** `{data.get(c_contract, 'N/A')}`")
                st.write(f"**Paket Layanan:** {data.get(c_package, 'N/A')}")
                st.write(f"**Tipe Jaringan:** {data.get(c_network, 'N/A')}")
                st.write(f"**Kelas:** {data.get(c_class, 'N/A')}")

            show_detail_dialog(selected_data)

    elif not df_filtered.empty:
        st.warning("⚠️ Kolom spesifik tidak terdeteksi otomatis. Menampilkan seluruh kolom tersedia:")
        st.dataframe(df_filtered, use_container_width=True, height=500)
    else:
        st.info("ℹ️ Tidak ada data yang sesuai dengan kombinasi filter dan pencarian Anda.")