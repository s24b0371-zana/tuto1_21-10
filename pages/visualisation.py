import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ==========================================
# 1. PASTE YOUR DATA LOADING CODE HERE
# (Whatever code creates `df_birth` in your Colab notebook)
# ==========================================
# Example:
# df_birth = pd.read_csv("your_data.csv")
# OR if you downloaded it from a URL:
# df_birth = pd.read_parquet("https://...")
# If not already installed, do: pip install pandas fastparquet
import pandas as pd

URL_DATA = 'https://storage.dosm.gov.my/demography/birth.parquet'

df_birth = pd.read_parquet(URL_DATA)
if 'date' in df_birth.columns: df_birth['date'] = pd.to_datetime(df_birth['date'])

print(df_birth)

# ==========================================
# 2. YOUR VISUALIZATION CODE
# ==========================================
df_plot = df_birth.copy()
df_plot['date'] = pd.to_datetime(df_plot['date'])
df_plot['year'] = df_plot['date'].dt.year

sns.set_theme(style="whitegrid")
fig, ax1 = plt.subplots(figsize=(13, 6))

bars = ax1.bar(
    df_plot['year'], df_plot['abs'],
    color='#2b5c8f', alpha=0.85, width=0.6,
    label='Total Live Births (abs)'
)
ax1.set_title('Trends in Live Births and Crude Birth Rate in Malaysia (2000–2025)', fontsize=13, fontweight='bold', pad=15)
ax1.set_xlabel('Year', fontweight='bold')
ax1.set_ylabel('Total Live Births (abs)', color='#2b5c8f', fontweight='bold')
ax1.set_xticks(df_plot['year'])
ax1.tick_params(axis='x', rotation=45)
ax1.set_ylim(0, df_plot['abs'].max() * 1.15)

ax2 = ax1.twinx()
ax2.plot(
    df_plot['year'], df_plot['rate'],
    color='#d95f02', marker='o', linewidth=2.5,
    label='Crude Birth Rate (per 1,000 population)'
)
ax2.set_ylabel('Crude Birth Rate', color='#d95f02', fontweight='bold')
ax2.set_ylim(0, df_plot['rate'].max() * 1.15)
ax2.grid(False)

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

plt.tight_layout()

# ==========================================
# 3. DISPLAY IN STREAMLIT (Replaces plt.show())
# ==========================================
st.pyplot(fig)
