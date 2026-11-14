import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ==========================================
# 1. TETAPAN HALAMAN & TAJUK
# ==========================================
st.set_page_config(
    page_title="Visualisasi Kelahiran Hidup Malaysia",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Trend Kelahiran Hidup & Kadar Kelahiran Kasar di Malaysia")
st.markdown(
    "Sumber data: **Jabatan Perangkaan Malaysia (DOSM / OpenDOSM)** — `birth.parquet`"
)
st.divider()

# ==========================================
# 2. MUAT TURUN DATA (DENGAN CACHE)
# ==========================================
@st.cache_data
def load_birth_data():
    url = "https://storage.dosm.gov.my/demography/birth.parquet"
    df = pd.read_parquet(url)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df["year"] = df["date"].dt.year
    return df

df_birth = load_birth_data()

# ==========================================
# 3. PENAPIS INTERAKTIF (SIDEBAR / ATAS)
# ==========================================
min_year = int(df_birth["year"].min())
max_year = int(df_birth["year"].max())

selected_years = st.slider(
    "Pilih Julat Tahun:",
    min_value=min_year,
    max_value=max_year,
    value=(min_year, max_year)
)

df_plot = df_birth[
    (df_birth["year"] >= selected_years[0]) & 
    (df_birth["year"] <= selected_years[1])
].copy()

# ==========================================
# 4. KAD METRIK RINGKASAN (KPI)
# ==========================================
if not df_plot.empty:
    latest_row = df_plot.sort_values("year").iloc[-1]
    prev_row = df_plot.sort_values("year").iloc[-2] if len(df_plot) > 1 else latest_row

    delta_abs = int(latest_row["abs"] - prev_row["abs"])
    delta_rate = round(float(latest_row["rate"] - prev_row["rate"]), 2)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label=f"Tahun Terkini Dipilih",
            value=f"{int(latest_row['year'])}"
        )
    with col2:
        st.metric(
            label="Jumlah Kelahiran Hidup (abs)",
            value=f"{int(latest_row['abs']):,}",
            delta=f"{delta_abs:,} berbanding tahun sebelumnya"
        )
    with col3:
        st.metric(
            label="Kadar Kelahiran Kasar (per 1,000 penduduk)",
            value=f"{latest_row['rate']:.1f}",
            delta=f"{delta_rate:+.1f} berbanding tahun sebelumnya"
        )

st.write("")

# ==========================================
# 5. GRAF DWI-PAKSI (MATPLOTLIB + SEABORN)
# ==========================================
sns.set_theme(style="whitegrid")
fig, ax1 = plt.subplots(figsize=(13, 6))

# Bar untuk Jumlah Kelahiran Hidup
ax1.bar(
    df_plot["year"], df_plot["abs"],
    color="#2b5c8f", alpha=0.85, width=0.6,
    label="Total Live Births (abs)"
)
ax1.set_title(
    f"Trends in Live Births and Crude Birth Rate in Malaysia ({selected_years[0]}–{selected_years[1]})",
    fontsize=13, fontweight="bold", pad=15
)
ax1.set_xlabel("Year", fontweight="bold")
ax1.set_ylabel("Total Live Births (abs)", color="#2b5c8f", fontweight
