import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import io

# ==========================================
# 0. STREAMLIT PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Objective 3: Malaysia Demographic & Socioeconomic Analysis",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Objective 3: Malaysia's Live Births, Life Expectancy & Annual Income (2022–2025)")
st.markdown("Multivariate demographic and socioeconomic analysis powered by open data from the **Department of Statistics Malaysia (DOSM)**.")

# ==========================================
# 1. FETCH & CACHE DATA FROM DOSM
# ==========================================
@st.cache_data(ttl=86400)  # Cache data for 24 hours for fast performance
def load_and_process_data():
    url_birth = 'https://storage.dosm.gov.my/demography/birth.parquet'
    url_life = 'https://storage.dosm.gov.my/demography/life_expectancy_state_ethnic.parquet'
    # Note: Ensure the wages URL below matches your original Colab dataset URL
    url_wages = 'https://storage.dosm.gov.my/labour/wages_annual_sex_ethnic.parquet'

    df_birth = pd.read_parquet(url_birth)
    df_life = pd.read_parquet(url_life)
    df_wages = pd.read_parquet(url_wages)

    # Extract year from the date column
    for df in [df_birth, df_life, df_wages]:
        if 'date' in df.columns:
            df['year'] = pd.to_datetime(df['date']).dt.year

    # Aggregate life expectancy across all 16 states to national average
    le_nat = (
        df_life.groupby(['year', 'sex', 'ethnicity'], as_index=False)['life_expectancy']
        .mean()
        .rename(columns={'life_expectancy': 'avg_life_expectancy'})
    )

    # Calculate annual income (Monthly Wage x 12)
    df_wages['annual_income_median'] = df_wages['wages_median'] * 12
    df_wages['annual_income_mean'] = df_wages['wages_mean'] * 12

    # Merge all three datasets
    merged_df = (
        pd.merge(df_wages, le_nat, on=['year', 'sex', 'ethnicity'], how='inner')
        .merge(df_birth[['year', 'abs', 'rate']], on='year', how='inner')
        .rename(columns={'abs': 'live_births', 'rate': 'birth_rate_per_1k'})
    )
    
    return merged_df

with st.spinner("Fetching and processing datasets from DOSM servers..."):
    try:
        merged_df = load_and_process_data()
    except Exception as e:
        st.error(f"Error loading datasets: {e}")
        st.info("Tip: Double-check your `url_wages` link or internet connection.")
        st.stop()

# ==========================================
# 2. SIDEBAR FILTERS (INTERACTIVE CONTROLS)
# ==========================================
st.sidebar.header("⚙️ Display Settings")

sex_options = {'both': 'Both Sexes', 'male': 'Male', 'female': 'Female'}
selected_sex = st.sidebar.selectbox(
    "Select Sex:",
    options=list(sex_options.keys()),
    format_func=lambda x: sex_options[x],
    index=0
)

available_ethnicities = ['bumi', 'chinese', 'indian', 'overall']
selected_ethnicities = st.sidebar.multiselect(
    "Select Ethnic Groups (Panel A):",
    options=available_ethnicities,
    default=available_ethnicities
)

if not selected_ethnicities:
    st.warning("Please select at least one ethnic group from the sidebar.")
    st.stop()

# Filter data based on user selections
plot_df = merged_df[
    (merged_df['sex'] == selected_sex) &
    (merged_df['ethnicity'].isin(selected_ethnicities))
].sort_values(['ethnicity', 'year'])

overall_df = merged_df[
    (merged_df['sex'] == selected_sex) &
    (merged_df['ethnicity'] == 'overall')
].sort_values('year')

# ==========================================
# 3. TWO-PANEL MULTIVARIATE VISUALIZATION
# ==========================================
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#CCCCCC'
plt.rcParams['axes.linewidth'] = 0.8

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6.5), gridspec_kw={'width_ratios': [1.25, 1]})
fig.patch.set_facecolor('white')

palette = {
    'chinese': ('#1f77b4', 'Chinese'),
    'bumi': ('#2ca02c', 'Bumiputera'),
    'indian': ('#d62728', 'Indian'),
    'overall': ('#333333', 'Malaysia Overall')
}

# --- PANEL A: Connected Multivariate Bubble Trajectory ---
for eth in selected_ethnicities:
    color, label = palette[eth]
    sub = plot_df[plot_df['ethnicity'] == eth].sort_values('year')
    
    if sub.empty:
        continue
        
    x = sub['annual_income_median'].values
    y = sub['avg_life_expectancy'].values
    sizes = ((sub['live_births'] - 380000) / 1000) * 6 + 140
    
    ax1.plot(x, y, color=color, linewidth=2, alpha=0.75, zorder=2)
    if len(x) >= 2:
        ax1.annotate(
            '', xy=(x[-1], y[-1]), xytext=(x[-2], y[-2]),
            arrowprops=dict(arrowstyle='->', color=color, lw=2.2), zorder=3
        )
    
    ax1.scatter(
        x, y, s=sizes, color=color, alpha=0.82,
        edgecolors='white', linewidth=1.5, label=label, zorder=4
    )
    
    min_yr, max_yr = sub['year'].min(), sub['year'].max()
    for yr, xi, yi in zip(sub['year'], x, y):
        if yr in [min_yr, max_yr]:
            offset_y = 0.18 if yr == max_yr else -0.26
            ax1.text(
                xi, yi + offset_y, f"{yr}", fontsize=8.5, fontweight='bold',
                color=color, ha='center', va='center', zorder=5
            )

ax1.set_title('A. Income vs. Life Expectancy Trajectory by Ethnicity\n(Bubble Size = National Live Births, 2022–2025)',
              fontsize=11.5, fontweight='bold', pad=12, color='#111111')
ax1.set_xlabel('Annual Median Income (RM)', fontsize=10.5, fontweight='bold', labelpad=8)
ax1.set_ylabel('Average Life Expectancy (Years)', fontsize=10.5, fontweight='bold', labelpad=8)
ax1.xaxis.set_major_formatter(ticker.StrMethodFormatter('RM {x:,.0f}'))
ax1.xaxis.set_major_locator(ticker.MultipleLocator(4000))
ax1.grid(True, linestyle='--', alpha=0.4, color='#BBBBBB')
ax1.legend(loc='lower right', frameon=True, facecolor='#F9F9F9', title='Group (Start → End)', fontsize=9)

# --- PANEL B: Malaysia Macro Demographic Transition (Dual-Axis) ---
years = overall_df['year'].astype(str)
ax2_twin = ax2.twinx()

bars = ax2.bar(years, overall_df['live_births'] / 1000, color='#A6CEE3', width=0.48, alpha=0.85, label='Live Births (Thousands)')
ax2.set_ylabel('Live Births (Thousands)', fontsize=10.5, fontweight='bold', color='#1F78B4', labelpad=8)
ax2.set_ylim(340, 500)
ax2.tick_params(axis='y', labelcolor='#1F78B4')

for bar in bars:
    h = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2, h + 4, f"{h:.1f}k", ha='center', va='bottom', fontsize=8.5, color='#1F78B4', fontweight='bold')

ax2_twin.plot(years, overall_df['annual_income_median'] / 1000, color='#E31A1C', marker='o', linewidth=2.5, markersize=7, label="Annual Median Income (RM '000)")
ax2_twin.set_ylabel("Annual Median Income (RM '000)", fontsize=10.5, fontweight='bold', color='#E31A1C', labelpad=8)
ax2_twin.set_ylim(22, 35)
ax2_twin.tick_params(axis='y', labelcolor='#E31A1C')

for idx, (inc, le_val) in enumerate(zip(overall_df['annual_income_median']/1000, overall_df['avg_life_expectancy'])):
    ax2_twin.text(idx, inc + 0.55, f"RM {inc:.1f}k\n({le_val:.1f} yrs)", ha='center', va='bottom', fontsize=8, color='#B2182B', fontweight='bold')

ax2.set_title('B. Malaysia Macro Demographic Transition\n(Births Declining as Income & Life Expectancy Rise)',
              fontsize=11.5, fontweight='bold', pad=12, color='#111111')
ax2.set_xlabel('Year', fontsize=10.5, fontweight='bold', labelpad=8)
ax2.grid(True, linestyle='--', alpha=0.35, color='#BBBBBB')

lines1, labels1 = ax2.get_legend_handles_labels()
lines2, labels2 = ax2_twin.get_legend_handles_labels()
ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper right', frameon=True, facecolor='#F9F9F9', fontsize=8.5)

plt.suptitle(f"Objective 3: Malaysia's Live Births, Life Expectancy & Annual Income ({sex_options[selected_sex]})",
             fontsize=13.5, fontweight='bold', y=0.99)
plt.tight_layout(rect=[0, 0, 1, 0.94])

# Display chart in Streamlit
st.pyplot(fig)

# ==========================================
# 4. DOWNLOAD BUTTONS & DATA TABLE
# ==========================================
st.divider()
col1, col2 = st.columns(2)

# Save chart into memory buffer for PNG download
img_buffer = io.BytesIO()
fig.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
img_buffer.seek(0)

with col1:
    st.download_button(
        label="📥 Download Chart (PNG - 300 DPI)",
        data=img_buffer,
        file_name="objective3_malaysia_demographic_socioeconomic.png",
        mime="image/png"
    )

with col2:
    csv_data = merged_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Merged Dataset (CSV)",
        data=csv_data,
        file_name="merged_objective3_malaysia.csv",
        mime="text/csv"
    )

with st.expander("📋 View Merged Dataset Table"):
    st.dataframe(plot_df, use_container_width=True)
