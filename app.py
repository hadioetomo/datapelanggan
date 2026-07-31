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
    initial_sidebar_state="collapsed"
)

# 2. Styling CSS Custom
st.markdown("""
    <style>
        /* Force App Background & Base Font */
        .stApp {
            background-color: #F8FAFC !important;
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
        }
        
        /* Main Header Styling */
        .main-header {
            font-size: 26px;
            font-weight: 800;
            background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 2px;
        }
        .sub-header {
            font-size: 14px;
            color: #475569 !important;
            margin-bottom: 20px;
            font-weight: 500;
        }

        /* Form Container untuk Card Login */
        div[data-testid="stForm"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            padding: 24px !important;
            border-radius: 16px !important;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08) !important;
        }

        /* Force Label & Text Color Compatibility */
        label p, .stMarkdown p, h1, h2, h3, h4, h5, h6 {
            color: #0F172A !important;
        }

        /* Input Custom Styling */
        .stTextInput input {
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            border-radius: 8px !important;
            border: 1px solid #CBD5E1 !important;
        }
        .stTextInput input:focus {
            border-color: #3B82F6 !important;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2) !important;
        }

        /* Metric Styling Custom */
        div[data-testid="stMetric"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-left: 5px solid #3B82F6 !important;
            padding: 14px !important;
            border-radius: 12px !important;
        }
        div[data-testid="stMetricLabel"] p {
            font-size: 13px !important;
            color: #64748B !important;
            font-weight: 600 !important;
        }
        div[data-testid="stMetricValue"] div {
            font-size: 22px !important;
            color: #0F172A !important;
            font-weight: 700 !important;
        }

        /* Freeze Header Tabel Dataframe */
        div[data-testid="stDataFrame"] div[role="columnheader"] {
            position: sticky !important;
            top: 0 !important;
            z-index: 10 !important;
            background-color: #F1F5F9 !important;
            color: #0F172A !important;
            font-weight: 700 !important;
        }

        /* General Buttons */
        .stButton>button {
            border-radius: 8px !important;
            font-weight: 600 !important;
            background-color: #1E3A8A !important;
            color: #FFFFFF !important;
            border: none !important;
        }
        .stButton>button:hover {
            background-color: #2563EB !important;
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

# 5. Fungsi Caching Query Dropdown
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
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Form Login
        with st.form("login_form"):
            st.markdown("### 💎 Portal Akses Eksekutif")
            st.markdown("<p style='color: #64748B; font-size: 13px; margin-bottom: 15px;'>Autentikasi dua langkah aman via WhatsApp Gateway.</p>", unsafe_allow_html=True)
            
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

        # Form OTP (Muncul setelah OTP Terkirim)
        if st.session_state["otp_sent"]:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.form("otp_form"):
                st.markdown("##### 🔑 Verifikasi Kode OTP")
                otp_input = st.text_input("Masukkan 6 Digit Kode OTP:", max_chars=6)
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
    # Sidebar Informasi Akun
    st.sidebar.markdown("### 🛡️ Keamanan Sesi")
    st.sidebar.info(f"Pengguna: `{mask_phone_number(st.session_state['target_phone'])}`")
    
    if st.sidebar.button("🚪 Keluar (Logout)", use_container_width=True):
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

    # Pemetaaan Sampel Kolom Database Wilayah Pertama untuk Deteksi Nama Kolom
    sample_region = available_regions[0]
    valid_db_sample = [f for f in DB_PARTS_MAPPING[sample_region] if os.path.exists(f)]
    sample_conn = sqlite3.connect(valid_db_sample[0])
    sample_df = pd.read_sql(f"SELECT * FROM [{sample_region}] LIMIT 1", sample_conn)
    all_columns = [col.strip() for col in sample_df.columns]
    sample_conn.close()

    def find_col(keywords):
        for col in all_columns:
            if any(k in col.lower() for k in keywords):
                return col
        return None

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

    # --- PILIHAN WILAYAH & FILTER NAMA LOKASI DI BAGIAN ATAS ---
    top_col1, top_col2 = st.columns(2)
    
    with top_col1:
        selected_region = st.selectbox("📂 Pilih Wilayah Database Utama:", available_regions)
    
    valid_db_files = [f for f in DB_PARTS_MAPPING[selected_region] if os.path.exists(f)]

    pilih_cluster = "Semua Lokasi / Cluster"
    with top_col2:
        if c_cluster:
            daftar_cluster = ['Semua Lokasi / Cluster'] + get_distinct_values(tuple(valid_db_files), selected_region, c_cluster)
            pilih_cluster = st.selectbox("🏡 Filter Nama Lokasi (Cluster):", daftar_cluster)

    # Pencarian Kata Kunci Cepat
    keyword_search = st.text_input("🔎 Cari Berdasarkan ID, Akun, Jalan, atau Paket:", "", placeholder="Ketik kata kunci pencarian untuk menampilkan data...")

    # Cek apakah pengguna sudah memasukkan input pencarian/filter
    is_search_active = bool(keyword_search.strip()) or (pilih_cluster != "Semua Lokasi / Cluster")

    # Hitung total Keseluruhan Data
    total_db_rows = 0
    for db_f in valid_db_files:
        conn = sqlite3.connect(db_f)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM [{selected_region}]")
        total_db_rows += cursor.fetchone()[0]
        conn.close()

    # --- JIKA BELUM MENGISI SEARCH/FILTER, TAMPILKAN INSTRUKSI (DATA KOSONG) ---
    if not is_search_active:
        m1, m2, m3 = st.columns(3)
        m1.metric("📊 Filter Ditemukan", "0 baris")
        m2.metric("📋 Total Keseluruhan Data", f"{total_db_rows:,} baris")
        m3.metric("📌 Wilayah Database", selected_region)
        st.markdown("---")
        st.info("💡 Silakan isi kata kunci pencarian di atas atau pilih **Nama Lokasi (Cluster)** untuk menampilkan data pelanggan.")

    # --- JIKA SUDAH MENGISI SEARCH/FILTER, PROSES DATA ---
    else:
        conditions = []
        if pilih_cluster != 'Semua Lokasi / Cluster' and c_cluster:
            conditions.append(f"[{c_cluster}] = '{pilih_cluster}'")

        if keyword_search:
            search_conditions = []
            search_targets = [t for t in [c_homepass, c_cluster, c_contract, c_package, c_street] if t is not None]
            for target in search_targets:
                search_conditions.append(f"[{target}] LIKE '%{keyword_search}%'")
            if search_conditions:
                conditions.append(f"(" + " OR ".join(search_conditions) + ")")

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

        # Hitung Jumlah Baris Terfilter
        total_matching_rows = 0
        for db_f in valid_db_files:
            conn = sqlite3.connect(db_f)
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM [{selected_region}]" + where_clause)
            total_matching_rows += cursor.fetchone()[0]
            conn.close()

        # Tampilkan semua data dalam 1 halaman
        filtered_dfs = []
        for db_f in valid_db_files:
            conn = sqlite3.connect(db_f)
            query = f"SELECT * FROM [{selected_region}]" + where_clause + " LIMIT 100000"
            part_df = pd.read_sql(query, conn)
            filtered_dfs.append(part_df)
            conn.close()

        df_filtered = pd.concat(filtered_dfs, ignore_index=True) if filtered_dfs else pd.DataFrame()

        # Metrik Ringkas
        m1, m2, m3 = st.columns(3)
        m1.metric("📊 Filter Ditemukan", f"{total_matching_rows:,} baris")
        m2.metric("📋 Total Keseluruhan Data", f"{total_db_rows:,} baris")
        m3.metric("📌 Wilayah Database", selected_region)
        st.markdown("---")

        if not df_filtered.empty:
            # --- PENGGABUNGAN ALAMAT: Nama Lokasi, Blok, House No, RT, RW ---
            def format_full_address(row):
                parts = []
                cluster_val = str(row[c_cluster]).strip() if c_cluster and pd.notna(row[c_cluster]) else ""
                block_val = str(row[c_block]).strip() if c_block and pd.notna(row[c_block]) else ""
                house_val = str(row[c_house]).strip() if c_house and pd.notna(row[c_house]) else ""
                rt_val = str(row[c_rt]).strip() if c_rt and pd.notna(row[c_rt]) else ""
                rw_val = str(row[c_rw]).strip() if c_rw and pd.notna(row[c_rw]) else ""

                if cluster_val:
                    parts.append(f"[{cluster_val}]")
                if block_val:
                    parts.append(f"Blok {block_val}")
                if house_val:
                    parts.append(f"No. {house_val}")
                if rt_val or rw_val:
                    parts.append(f"RT/RW: {rt_val or '-'}/{rw_val or '-'}")

                return " ".join(parts) if parts else "-"

            df_filtered["Alamat / Lokasi Pelanggan"] = df_filtered.apply(format_full_address, axis=1)

            # Pemetaan Kolom Tampilan (Alamat / Lokasi Pelanggan ditaruh pertama, baru Homepass ID)
            col_mapping_target = {
                "Alamat / Lokasi Pelanggan": "Alamat / Lokasi Pelanggan",
                "Homepass ID": c_homepass,
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

            display_df = df_filtered[active_db_columns].copy()
            display_df.columns = active_display_labels

            # Header Tabel Hasil
            st.markdown(f"### 📋 Hasil Direktori Pelanggan — **{selected_region}**")
            
            event = st.dataframe(
                display_df, 
                use_container_width=True, 
                height=550,
                selection_mode="single-row",
                on_select="rerun"
            )

            # Pop-up Detail Informasi
            selected_rows = event.selection.get("rows", [])
            if selected_rows:
                row_idx = selected_rows[0]
                selected_data = df_filtered.iloc[row_idx]

                @st.dialog("💎 Detail Informasi Pelanggan")
                def show_detail_dialog(data):
                    st.markdown("#### Informasi Alamat & Identitas")
                    st.write(f"**Alamat Lengkap:** {data.get('Alamat / Lokasi Pelanggan', 'N/A')}")
                    st.write(f"**Homepass ID:** `{data.get(c_homepass, 'N/A')}`")
                    st.markdown("---")
                    st.markdown("#### Informasi Layanan & Kontrak")
                    st.write(f"**Status Homepass:** `{data.get(c_status, 'N/A')}`")
                    st.write(f"**Nomor Kontrak:** `{data.get(c_contract, 'N/A')}`")
                    st.write(f"**Paket Layanan:** {data.get(c_package, 'N/A')}")
                    st.write(f"**Tipe Jaringan:** {data.get(c_network, 'N/A')}")
                    st.write(f"**Kelas:** {data.get(c_class, 'N/A')}")

                show_detail_dialog(selected_data)

        else:
            st.info("ℹ️ Tidak ada data yang sesuai dengan kata kunci pencarian Anda.")