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
MAX_OTP_ATTEMPTS = 3        # Maks percobaan OTP salah
OTP_BLOCK_DURATION = 5 * 60 # Blokir 5 menit jika gagal 3x

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
if "otp_attempts" not in st.session_state:
    st.session_state["otp_attempts"] = 0
if "otp_blocked_until" not in st.session_state:
    st.session_state["otp_blocked_until"] = 0

# Cek Kedaluwarsa Sesi Login (30 Menit)
if st.session_state["authenticated"]:
    if time.time() - st.session_state["login_time"] > SESSION_TIMEOUT:
        st.session_state["authenticated"] = False
        st.warning("⏱️ Sesi login Anda telah berakhir (30 menit). Silakan login kembali.")
        st.rerun()

def send_whatsapp_otp(phone, otp_code):
    """Mengirim OTP melalui API WhatsApp. Return True jika berhasil."""
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
            # Sesuaikan dengan format respon API Anda
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

        # Cek apakah sedang diblokir karena banyak percobaan OTP salah
        if st.session_state["otp_blocked_until"] > time.time():
            remaining_block = int(st.session_state["otp_blocked_until"] - time.time())
            st.error(f"⛔ Terlalu banyak percobaan OTP. Silakan coba lagi dalam {remaining_block} detik.")
            st.stop()

        with st.form("login_form"):
            phone_input = st.text_input("📱 Nomor WhatsApp (Contoh: 62812345678):")
            submit_phone = st.form_submit_button("🚀 Kirim Kode OTP", use_container_width=True)

            if submit_phone:
                # Normalisasi nomor
                clean_phone = phone_input.strip().replace("+", "").replace(" ", "")
                if clean_phone in ALLOWED_PHONE_NUMBERS:
                    otp = str(random.randint(100000, 999999))
                    st.session_state["generated_otp"] = otp
                    st.session_state["target_phone"] = clean_phone
                    st.session_state["otp_time"] = time.time()
                    st.session_state["otp_attempts"] = 0  # reset percobaan

                    # Kirim OTP hanya jika berhasil
                    if send_whatsapp_otp(clean_phone, otp):
                        st.session_state["otp_sent"] = True
                        st.success(f"✅ OTP terkirim ke {clean_phone} (Berlaku 2 Menit)!")
                    else:
                        st.error("❌ Gagal mengirim OTP. Silakan coba lagi atau periksa koneksi.")
                        st.session_state["otp_sent"] = False
                else:
                    st.error("❌ Nomor WhatsApp tidak terdaftar dalam sistem.")
                    st.session_state["otp_sent"] = False

        if st.session_state["otp_sent"]:
            with st.form("otp_form"):
                otp_input = st.text_input("🔑 Masukkan 6 Digit Kode OTP:", max_chars=6)
                verify_otp = st.form_submit_button("✨ Verifikasi & Masuk", use_container_width=True)

                if verify_otp:
                    # Cek kedaluwarsa OTP
                    if time.time() - st.session_state["otp_time"] > OTP_TIMEOUT:
                        st.error("❌ Kode OTP telah kedaluwarsa. Silakan kirim ulang.")
                        st.session_state["otp_sent"] = False
                    else:
                        # Verifikasi OTP
                        if otp_input == st.session_state["generated_otp"]:
                            st.session_state["authenticated"] = True
                            st.session_state["login_time"] = time.time()
                            st.success("🎉 Login berhasil! Memuat data...")
                            st.rerun()
                        else:
                            st.session_state["otp_attempts"] += 1
                            remaining = MAX_OTP_ATTEMPTS - st.session_state["otp_attempts"]
                            if remaining > 0:
                                st.error(f"❌ Kode OTP salah. Anda memiliki {remaining} percobaan lagi.")
                            else:
                                # Blokir sementara
                                st.session_state["otp_blocked_until"] = time.time() + OTP_BLOCK_DURATION
                                st.session_state["otp_sent"] = False
                                st.error("⛔ Terlalu banyak percobaan. Anda diblokir selama 5 menit.")
                                st.rerun()

# --- HALAMAN UTAMA APLIKASI (SETELAH LOGIN) ---
else:
    # Sidebar Informasi & Logout
    with st.sidebar:
        st.markdown("### 🛡️ Keamanan Akun")
        st.success(f"Aktif: `{st.session_state['target_phone']}`")

        # Tampilkan sisa waktu sesi
        time_left = SESSION_TIMEOUT - (time.time() - st.session_state["login_time"])
        if time_left > 0:
            mins = int(time_left // 60)
            secs = int(time_left % 60)
            st.info(f"⏳ Sisa sesi: {mins} menit {secs} detik")
        else:
            st.warning("Sesi hampir berakhir")

        if st.button("🚪 Keluar (Logout)", use_container_width=True):
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

    # Deteksi kolom yang tersedia (dari part pertama)
    try:
        with sqlite3.connect(valid_db_files[0]) as sample_conn:
            sample_df = pd.read_sql(f"SELECT * FROM [{selected_region}] LIMIT 1", sample_conn)
            all_columns = [col.strip() for col in sample_df.columns]
    except Exception as e:
        st.error(f"Gagal membaca database sampel: {e}")
        st.stop()

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

    # Kolom yang akan ditampilkan (hanya yang ada)
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
        if col_name and col_name in all_columns:
            active_display_labels.append(label)
            active_db_columns.append(col_name)

    if not active_db_columns:
        st.warning("⚠️ Tidak ada kolom standar yang terdeteksi. Menampilkan seluruh kolom.")
        active_db_columns = all_columns
        active_display_labels = all_columns

    # --- CACHING Distinct Values untuk Filter (refresh setiap 10 menit) ---
    @st.cache_data(ttl=600)
    def get_distinct_values(region, column_name, db_files):
        values = set()
        for db_f in db_files:
            try:
                with sqlite3.connect(db_f) as conn:
                    # Gunakan parameterized query untuk keamanan
                    query = f"SELECT DISTINCT [{column_name}] FROM [{region}] WHERE [{column_name}] IS NOT NULL"
                    cursor = conn.execute(query)
                    for row in cursor:
                        values.add(str(row[0]))
            except Exception:
                continue
        return sorted(list(values))

    # --- KOTAK FILTER & PENCARIAN ---
    st.markdown("### 🔍 Panel Filter & Pencarian Cepat")

    with st.container():
        st.markdown('<div class="filter-container">', unsafe_allow_html=True)

        # Input keyword dengan session state agar bisa direset
        if "keyword_search" not in st.session_state:
            st.session_state["keyword_search"] = ""
        keyword_search = st.text_input(
            "🔎 Cari Berdasarkan ID, Nama Lokasi, Akun, atau Jalan:",
            value=st.session_state["keyword_search"],
            placeholder="Ketik kata kunci pencarian..."
        )
        # Update session state setiap kali berubah
        st.session_state["keyword_search"] = keyword_search

        col_f1, col_f2, col_f3 = st.columns(3)

        # Inisialisasi pilihan default di session state jika belum ada
        if "pilih_kota" not in st.session_state:
            st.session_state["pilih_kota"] = "Semua Kota"
        if "pilih_building" not in st.session_state:
            st.session_state["pilih_building"] = "Semua Jenis"
        if "pilih_district" not in st.session_state:
            st.session_state["pilih_district"] = "Semua Area"

        pilih_kota = st.session_state["pilih_kota"]
        pilih_building = st.session_state["pilih_building"]
        pilih_district = st.session_state["pilih_district"]

        if c_kota:
            daftar_kota = ["Semua Kota"] + get_distinct_values(selected_region, c_kota, valid_db_files)
            with col_f1:
                pilih_kota = st.selectbox("📍 Pilih Kota:", daftar_kota,
                                          index=daftar_kota.index(st.session_state["pilih_kota"]) if st.session_state["pilih_kota"] in daftar_kota else 0)

        if c_building:
            daftar_building = ["Semua Jenis"] + get_distinct_values(selected_region, c_building, valid_db_files)
            with col_f2:
                pilih_building = st.selectbox("🏢 Jenis Perumahan:", daftar_building,
                                             index=daftar_building.index(st.session_state["pilih_building"]) if st.session_state["pilih_building"] in daftar_building else 0)

        if c_district:
            daftar_district = ["Semua Area"] + get_distinct_values(selected_region, c_district, valid_db_files)
            with col_f3:
                pilih_district = st.selectbox("📍 Pilih Area (District):", daftar_district,
                                              index=daftar_district.index(st.session_state["pilih_district"]) if st.session_state["pilih_district"] in daftar_district else 0)

        # Tombol Reset Filter
        col_btn1, col_btn2 = st.columns([1, 5])
        with col_btn1:
            if st.button("🔄 Reset Filter", use_container_width=True):
                # Reset session state ke default
                st.session_state["keyword_search"] = ""
                st.session_state["pilih_kota"] = "Semua Kota"
                st.session_state["pilih_building"] = "Semua Jenis"
                st.session_state["pilih_district"] = "Semua Area"
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # --- EKSEKUSI QUERY MULTI-PART DATABASE DENGAN PARAMETERIZED ---
    filtered_dfs = []
    total_rows_all = 0
    progress_bar = st.progress(0)
    total_parts = len(valid_db_files)

    with st.spinner("Memuat data..."):
        for idx, db_f in enumerate(valid_db_files):
            try:
                with sqlite3.connect(db_f) as conn:
                    # Hitung total data di part ini (tanpa filter)
                    count_query = f"SELECT COUNT(*) FROM [{selected_region}]"
                    total_rows_all += conn.execute(count_query).fetchone()[0]

                    # Bangun query SELECT dengan kolom yang sudah ditentukan
                    selected_cols = ", ".join([f"[{col}]" for col in active_db_columns])
                    query = f"SELECT {selected_cols} FROM [{selected_region}]"
                    conditions = []
                    params = []

                    if pilih_kota != 'Semua Kota' and c_kota:
                        conditions.append(f"[{c_kota}] = ?")
                        params.append(pilih_kota)
                    if pilih_building != 'Semua Jenis' and c_building:
                        conditions.append(f"[{c_building}] = ?")
                        params.append(pilih_building)
                    if pilih_district != 'Semua Area' and c_district:
                        conditions.append(f"[{c_district}] = ?")
                        params.append(pilih_district)

                    if keyword_search:
                        search_conditions = []
                        # Kolom yang bisa dicari dengan LIKE
                        search_targets = [c_homepass, c_cluster, c_contract, c_package, c_street]
                        search_targets = [t for t in search_targets if t is not None]
                        for target in search_targets:
                            search_conditions.append(f"[{target}] LIKE ?")
                            params.append(f"%{keyword_search}%")
                        if search_conditions:
                            conditions.append("(" + " OR ".join(search_conditions) + ")")

                    if conditions:
                        query += " WHERE " + " AND ".join(conditions)

                    # Eksekusi query dengan parameter
                    part_df = pd.read_sql_query(query, conn, params=params)
                    filtered_dfs.append(part_df)

            except Exception as e:
                st.error(f"Error membaca {db_f}: {e}")

            # Update progress bar
            progress_bar.progress((idx + 1) / total_parts)

        progress_bar.empty()  # Selesai, hilangkan progress bar

    if filtered_dfs:
        df_filtered = pd.concat(filtered_dfs, ignore_index=True)
    else:
        df_filtered = pd.DataFrame(columns=active_db_columns)

    # --- METRIK & TAMPILAN HASIL ---
    m1, m2, m3 = st.columns(3)
    m1.metric("📊 Data Ditemukan", f"{len(df_filtered):,} baris")
    m2.metric("📋 Total Keseluruhan Data", f"{total_rows_all:,} baris")
    m3.metric("📌 Wilayah Aktif", selected_region)
    st.markdown("---")

    if df_filtered.empty:
        st.info("🔍 Tidak ada data yang sesuai dengan filter. Silakan ubah kriteria pencarian.")
    else:
        # Ganti nama kolom untuk tampilan
        display_df = df_filtered.copy()
        display_df.columns = active_display_labels

        st.markdown(f"### 📋 Hasil Direktori Pelanggan — **{selected_region}**")
        st.dataframe(display_df, use_container_width=True, height=580)