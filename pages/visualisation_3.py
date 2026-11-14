import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# ==========================================
# 0. PAGE CONFIG
# ==========================================
st.set_page_config(
    page_title="Malaysia Demographic & Socioeconomic Analysis",
    layout="wide"
)

st.title("Malaysia's Live Births, Life Expectancy & Annual Income (2022–2025)")
st.markdown("Multivariate analysis examining demographic transition across ethnic groups in Malaysia.")

# ==========================================
# 1. LOAD & PREPROCESS DATA (CACHED)
# ==========================================
@st.cache_data
def load_and_prepare_data():
    # Option A: Load directly from OpenDOSM / DOSM official storage
    # (Replace these URLs with pd.read_csv('your_local_file.csv') if using local files)
    url_birth = "https://storage.dosm.gov.my/demography/birth.parquet"
    url_life = "https://storage.dosm.gov.my/demography/life_expectancy.parquet"
    url_wages = "https://storage.dosm.gov.my/labour/wages_annual.parquet"  # Adjust if using quarterly/monthly

    try:
        birth = pd.read_parquet(url_birth)
        life = pd.read_parquet(url_life)
        wages = pd.read_parquet(url_wages)
    except Exception:
        # Option B: Fallback to local CSV files in your project folder
        birth = pd.read_csv("df_birth.csv")
        life = pd.read_csv("df_life.csv")
        wages = pd.read_csv("df_wages.csv")

    # Extract year from date column
    for df in [birth, life, wages]:
        df['year'] = pd.to_datetime(df['date']).dt.year

    # Aggregate birth data to annual if the dataset is monthly/quarterly
    if birth.duplicated(subset=['year']).any():
        birth = (
            birth.groupby('year', as_index=False)
            .agg({'abs': 'sum', 'rate': 'mean'})
        )

    # Aggregate life expectancy across all states to national average
    le_nat = (
        life.groupby(['year', 'sex', 'ethnicity'], as_index=False)['life_expectancy']
        .mean()
        .rename(columns={'life_expectancy': 'avg_life_expectancy'})
    )

    # Calculate annual income (Monthly Wage x 12)
    wages['annual_income_median'] = wages['wages_median'] * 12
    wages['annual_income_mean'] = wages['wages_mean'] * 12

    # Merge all three datasets
    merged_df = (
        pd.merge(wages, le_nat, on=['year', 'sex', 'ethnicity'], how='inner')
        .merge(birth[['year', 'abs', 'rate']], on='year', how='inner')
        .rename(columns={'abs': 'live_births', 'rate': 'birth_rate_per_1k'})
    )

    return merged_df

try:
    merged_df = load_and_prepare_data()
except Exception as e:
    st.error(f"Could not load datasets. Ensure your CSV/Parquet files are in the same directory or check internet access. Error: {e}")
    st.stop()

# ==========================================
# 2. SIDEBAR INTERACTIVE CONTROLS
# ==========================================
st.sidebar.header("Dashboard Controls")

income_metric = st.sidebar.radio(
    "Income Metric:",
    options=["Median Annual Income", "Mean Annual Income"],
    index=0
)
income_col = "annual_income_median" if income_metric == "Median Annual Income" else "annual_income_mean"

available_ethnicities = ['chinese', 'bumi', 'indian', 'overall']
selected_ethnicities = st.sidebar.multiselect(
    "Select Ethnic Groups (Panel A):",
    options=available_ethnicities,
    default=available_ethnicities,
    format_func=lambda x: "Malaysia Overall" if x == "overall" else ("Bumiputera" if x == "bumi" else x.capitalize())
)

show_data = st.sidebar.checkbox("Show Merged Data Table", value=False)

# Filter for combined sex ('both') and selected ethnic groups
plot_df = merged_df[
    (merged_df['sex'] == 'both') &
    (merged_df['ethnicity'].isin(selected_ethnicities))
].sort_values(['ethnicity', 'year'])

overall_df = merged_df[
    (merged_df['sex'] == 'both') &
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
if not plot_df.empty:
    min_year, max_year = int(plot_df['year'].min()), int(plot_df['year'].max())

    for eth in selected_ethnicities:
        color, label = palette[eth]
        sub = plot_df[plot_df['ethnicity'] == eth].sort_values('year')
        if sub.empty:
            continue

        x = sub[income_col].values
        y = sub['avg_life_expectancy'].values
        sizes = ((sub['live_births'] - 380000) / 1000).clip(lower=10) * 6 + 140

        # Trajectory line
        ax1.plot(x, y, color=color, linewidth=2, alpha=0.75, zorder=2)

        # Directional arrow if at least 2 years exist
        if len(x) >= 2:
            ax1.annotate(
                '', xy=(x[-1], y[-1]), xytext=(x[-2], y[-2]),
                arrowprops=dict(arrowstyle='->', color=color, lw=2.2), zorder=3
            )

        # Plot bubbles
        ax1.scatter(
            x, y, s=sizes, color=color, alpha=0.82,
            edgecolors='white', linewidth=1.5, label=label, zorder=4
        )

        # Annotate start and end years
        for yr, xi, yi in zip(sub['year'], x, y):
            if yr in [min_year, max_year]:
                offset_y = 0.18 if yr == max_year else -0.26
                ax1.text(
                    xi, yi + offset_y, f"{yr}", fontsize=8.5, fontweight='bold',
                    color=color, ha='center', va='center', zorder=5
                )

    ax1.set_title(
        f'A. {income_metric} vs. Life Expectancy by Ethnicity\n(Bubble Size = National Live Births, {min_year}–{max_year})',
        fontsize=11.5, fontweight='bold', pad=12, color='#111111'
    )
    ax1.set_xlabel(f'{income_metric} (RM)', fontsize=10.5, fontweight='bold', labelpad=8)
    ax1.set_ylabel('Average Life Expectancy (Years)', fontsize=10.5, fontweight='bold', labelpad=8)
    ax1.xaxis.set_major_formatter(ticker.StrMethodFormatter('RM {x:,.0f}'))
    ax1.xaxis.set_major_locator(ticker.MultipleLocator(4000))
    ax1.margins(x=0.12, y=0.15)  # Dynamic padding instead of hardcoded limits
    ax1.grid(True, linestyle='--', alpha=0.4, color='#BBBBBB')
    ax1.legend(loc='lower right', frameon=True, facecolor='#F9F9F9', title=f'Group ({min_year} → {max_year})', fontsize=9)
else:
    ax1.text(0.5, 0.5, "Select at least one ethnic group in the sidebar.", ha='center', va='center')

# --- PANEL B: Malaysia Macro Demographic Transition (Dual-Axis) ---
if not overall_df.empty:
    years = overall_df['year'].astype(str)
    ax2_twin = ax2.twinx()

    # Bar chart for Live Births
    bars = ax2.bar(years, overall_df['live_births'] / 1000, color='#A6CEE3', width=0.48, alpha=0.85, label='Live Births (Thousands)')
    ax2.set_ylabel('Live Births (Thousands)', fontsize=10.5, fontweight='bold', color='#1F78B4', labelpad=8)
    ax2.set_ylim(0, (overall_df['live_births'].max() / 1000) * 1.25)
    ax2.tick_params(axis='y', labelcolor='#1F78B4')

    for bar in bars:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, h + 6, f"{h:.1f}k", ha='center', va='bottom', fontsize=8.5, color='#1F78B4', fontweight='bold')

    # Line chart for Annual Income + Life Expectancy labels
    inc_k = overall_df[income_col] / 1000
    ax2_twin.plot(years, inc_k, color='#E31A1C', marker='o', linewidth=2.5, markersize=7, label=f"{income_metric} (RM '000)")
    ax2_twin.set_ylabel(f"{income_metric} (RM '000)", fontsize=10.5, fontweight='bold', color='#E31A1C', labelpad=8)
    ax2_twin.set_ylim(inc_k.min() * 0.85, inc_k.max() * 1.18)
    ax2_twin.tick_params(axis='y', labelcolor='#E31A1C')

    for idx, (inc, le_val) in enumerate(zip(inc_k, overall_df['avg_life_expectancy'])):
        ax2_twin.text(idx, inc + (inc_k.max() * 0.02), f"RM {inc:.1f}k\n({le_val:.1f} yrs)", ha='center', va='bottom', fontsize=8, color='#B2182B', fontweight='bold')

    ax2.set_title('B. Malaysia Macro Demographic Transition\n(Births vs. Income & Life Expectancy)',
                  fontsize=11.5, fontweight='bold', pad=12, color='#111111')
    ax2.set_xlabel('Year', fontsize=10.5, fontweight='bold', labelpad=8)
    ax2.grid(True, linestyle='--', alpha=0.35, color='#BBBBBB')

    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper right', frameon=True, facecolor='#F9F9F9', fontsize=8.5)

plt.suptitle("Objective 3: Malaysia's Live Births, Life Expectancy & Annual Income",
             fontsize=13.5, fontweight='bold', y=0.99)
plt.tight_layout(rect=[0, 0, 1, 0.94])

# Render chart in Streamlit
st.pyplot(fig)

# ==========================================
# 4. OPTIONAL DATA TABLE & CSV DOWNLOAD
# ==========================================
if show_data:
    st.subheader("Merged Dataset")
    st.dataframe(merged_df, use_container_width=True)

csv_data = merged_df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Download Merged Dataset (CSV)",
    data=csv_data,
    file_name="merged_objective3_malaysia.csv",
    mime="text/csv"
)
