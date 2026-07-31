import streamlit as st
import pandas as pd

# Konfigurasi halaman web
st.set_page_config(
    page_title="Pencarian Data Perumahan",
    page_icon="🏠",
    layout="wide"
)

st.title("🏠 Portal Informasi & Pencarian Data Perumahan")
st.markdown("---")

# 1. Upload File Excel oleh User
uploaded_file = st.file_uploader("📂 Upload file Excel Anda (.xlsx / .xls)", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        # Membaca semua nama sheet yang ada di file excel
        excel_file = pd.ExcelFile(uploaded_file)
        sheet_names = excel_file.sheet_names

        st.sidebar.header("⚙️ Pengaturan Tampilan")
        selected_sheet = st.sidebar.selectbox("Pilih Sheet Data:", sheet_names)

        # Memuat data dari sheet yang dipilih
        df = pd.read_excel(uploaded_file, sheet_name=selected_sheet)

        # Membersihkan nama kolom (menghilangkan spasi berlebih jika ada)
        df.columns = df.columns.str.strip()

        st.success(f"Berhasil memuat sheet: **{selected_sheet}** ({len(df):,} baris data)")

        # Pastikan kolom yang dicari ada di dalam dataframe
        # Sesuaikan 'Kota' dan 'Nama Perumahan' dengan nama kolom asli di Excel Anda
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔍 Filter Pencarian")

        # Cek kolom yang tersedia untuk pencarian
        columns_lower = [col.lower() for col in df.columns]
        
        # Deteksi otomatis atau manual kolom Kota dan Perumahan
        kota_col = next((col for col in df.columns if 'kota' in col.lower() or 'kabupaten' in col.lower()), None)
        perumahan_col = next((col for col in df.columns if 'perumahan' in col.lower() or 'nama' in col.lower()), None)

        if not kota_col or not perumahan_col:
            st.warning("⚠️ Sistem tidak mendeteksi nama kolom 'Kota' atau 'Nama Perumahan' secara otomatis. Silakan pilih manual di bawah:")
            kota_col = st.sidebar.selectbox("Pilih Kolom Kota:", df.columns)
            perumahan_col = st.sidebar.selectbox("Pilih Kolom Nama Perumahan:", df.columns)
        else:
            st.sidebar.info(f"Kolom terdeteksi otomatis:\n- Kota: `{kota_col}`\n- Perumahan: `{perumahan_col}`")

        # Filter berdasarkan Kota
        daftar_kota = ['Semua Kota'] + sorted(df[kota_col].dropna().astype(str).unique().tolist())
        pilih_kota = st.sidebar.selectbox("Pilih Kota:", daftar_kota)

        # Filter berdasarkan Nama Perumahan (Text Search)
        cari_perumahan = st.sidebar.text_input("Cari Nama Perumahan (Kata Kunci):", "")

        # Terapkan Filter ke DataFrame
        filtered_df = df.copy()

        if pilih_kota != 'Semua Kota':
            filtered_df = filtered_df[filtered_df[kota_col].astype(str) == pilih_kota]

        if cari_perumahan:
            filtered_df = filtered_df[filtered_df[perumahan_col].astype(str).str.contains(cari_perumahan, case=False, na=False)]

        # --- TAMPILAN UTAMA ---
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Data Ditampilkan", f"{len(filtered_df):,} baris")
        col2.metric("Total Seluruh Data", f"{len(df):,} baris")
        col3.metric("Jumlah Sheet", len(sheet_names))

        st.markdown("### 📊 Hasil Data")
        st.dataframe(filtered_df, use_container_width=True, height=500)

        # Tombol Download Data Hasil Filter
        csv_data = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Hasil Filter (CSV)",
            data=csv_data,
            file_name=f"data_filter_{selected_sheet}.csv",
            mime="text/csv",
        )

    except Exception as e:
        st.error(f"Terjadi kesalahan saat membaca file Excel: {e}")
else:
    st.info("👋 Silakan upload file Excel Anda melalui panel atau tombol di atas untuk memulai.")
    
    # Contoh panduan format kolom
    with st.expander("ℹ️ Tips & Panduan Format Excel"):
        st.write("""
        - Pastikan baris pertama pada setiap sheet di Excel adalah **header kolom** (judul kolom).
        - Aplikasi ini fleksibel dan mendukung banyak sheet. Anda bisa berpindah sheet melalui menu di sidebar kiri setelah file di-upload.
        - Fitur pencarian akan otomatis mendeteksi kolom yang mengandung kata 'kota' dan 'perumahan', atau Anda bisa memilihnya manual.
        """)