import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

st.title("Trends in Live Births and Crude Birth Rate in Malaysia")

# 1. Load the dataset directly (cached so it loads fast)
@st.cache_data
def load_data():
    # Option A: Load directly from DOSM / OpenDOSM official Parquet URL
    url = "https://storage.dosm.gov.my/demography/births_annual.parquet"
    return pd.read_parquet(url)
    
    # Option B: If you uploaded a CSV file to your GitHub repo instead, 
    # comment out the 2 lines above and uncomment the line below:
    # return pd.read_csv("births_annual.csv")

df_birth = load_data()

# 2. Prepare the data
df_plot = df_birth.copy()
df_plot['date'] = pd.to_datetime(df_plot['date'])
df_plot['year'] = df_plot['date'].dt.year

# Optional interactive year filter in Streamlit
min_year, max_year = int(df_plot['year'].min()), int(df_plot['year'].max())
selected_years = st.slider(
    "Select Year Range",
    min_value=min_year,
    max_value=max_year,
    value=(min_year, max_year)
)
df_plot = df_plot[(df_plot['year'] >= selected_years[0]) & (df_plot['year'] <= selected_years[1])]

# 3. Create the dual-axis visualization
sns.set_theme(style="whitegrid")
fig, ax1 = plt.subplots(figsize=(13, 6))

bars = ax1.bar(
    df_plot['year'], df_plot['abs'],
    color='#2b5c8f', alpha=0.85, width=0.6,
    label='Total Live Births (abs)'
)
ax1.set_title(
    f"Trends in Live Births and Crude Birth Rate in Malaysia ({selected_years[0]}–{selected_years[1]})",
    fontsize=13, fontweight='bold', pad=15
)
ax1.set_xlabel('Year', fontweight='bold')
ax1.set_ylabel('Total Live Births (abs)', color='#2b5c8f', fontweight='bold')
ax1.set_xticks(df_plot['year'])
ax1.tick_params(axis='x', rotation=45)
ax1.set_ylim(0, df_plot['abs'].max() * 1.15)

# Secondary Y-axis for Crude Birth Rate
ax2 = ax1.twinx()
ax2.plot(
    df_plot['year'], df_plot['rate'],
    color='#d95f02', marker='o', linewidth=2.5,
    label='Crude Birth Rate (per 1,000 population)'
)
ax2.set_ylabel('Crude Birth Rate', color='#d95f02', fontweight='bold')
ax2.set_ylim(0, df_plot['rate'].max() * 1.15)
ax2.grid(False)

# Combine legends from both axes
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

plt.tight_layout()

# 4. Display the chart in Streamlit (replaces plt.show())
st.pyplot(fig)
