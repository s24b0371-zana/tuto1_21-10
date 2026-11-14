import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Malaysia Demographic & Income Gaps", layout="wide")

# ==========================================
# 1. LOAD & MERGE DATA
# ==========================================
@st.cache_data
def load_and_prepare_data():
    # Load datasets from DOSM
    df_life = pd.read_parquet('https://storage.dosm.gov.my/demography/life_expectancy_state_ethnic.parquet')
    df_wages = pd.read_parquet('https://storage.dosm.gov.my/labour/wages_ethnicity.parquet')

    # Ensure date columns are in datetime format
    df_life['date'] = pd.to_datetime(df_life['date'])
    df_wages['date'] = pd.to_datetime(df_wages['date'])

    # Perform inner join on specified columns
    df_merged_obj2 = pd.merge(df_life, df_wages, on=['date', 'sex', 'ethnicity'], how='inner')

    # Calculate annual median income
    df_merged_obj2['annual_median_income'] = df_merged_obj2['wages_median'] * 12

    # Filter for specific gender and ethnicity groups
    df_merged_obj2 = df_merged_obj2[
        (df_merged_obj2['sex'].isin(['male', 'female'])) &
        (df_merged_obj2['ethnicity'].isin(['bumi', 'chinese', 'indian']))
    ]

    return df_merged_obj2


# ==========================================
# 2. APP UI & VISUALIZATION
# ==========================================
st.title("Gender & Ethnic Gaps in Life Expectancy and Income in Malaysia")

df_merged_obj2 = load_and_prepare_data()

# Prepare average data from df_merged_obj2
df_plot = df_merged_obj2.copy()
df_plot['year'] = pd.to_datetime(df_plot['date']).dt.year

# Aggregate average life expectancy across states
life_avg = (
    df_plot.groupby(['ethnicity', 'sex'], as_index=False)['life_expectancy']
    .mean()
    .pivot(index='ethnicity', columns='sex', values='life_expectancy')
)

# Drop duplicate state rows before averaging national annual income
wages_unique = df_plot[['year', 'ethnicity', 'sex', 'annual_median_income']].drop_duplicates()
inc_avg = (
    wages_unique.groupby(['ethnicity', 'sex'], as_index=False)['annual_median_income']
    .mean()
    .pivot(index='ethnicity', columns='sex', values='annual_median_income')
)

ethnic_order = ['bumi', 'chinese', 'indian']
ethnic_labels = ['Bumiputera', 'Chinese', 'Indian']
life_avg = life_avg.loc[ethnic_order]
inc_avg = inc_avg.loc[ethnic_order]

# Configure figure and styling
sns.set_theme(style="whitegrid")
fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))
fig.suptitle(
    'Gender & Ethnic Gaps in Life Expectancy and Annual Median Income in Malaysia (2022–2025)',
    fontsize=13, fontweight='bold', y=1.02
)

y_pos = range(len(ethnic_order))

# Left Panel: Life Expectancy Gap (Female vs Male)
axes[0].hlines(y=y_pos, xmin=life_avg['male'], xmax=life_avg['female'], color='gray', alpha=0.6, linewidth=3)
axes[0].scatter(life_avg['male'], y_pos, color='#2b5c8f', s=130, label='Male', zorder=3)
axes[0].scatter(life_avg['female'], y_pos, color='#e06d53', s=130, label='Female', zorder=3)

for i, eth in enumerate(ethnic_order):
    m_val, f_val = life_avg.loc[eth, 'male'], life_avg.loc[eth, 'female']
    gap = f_val - m_val
    axes[0].text(m_val - 0.35, i, f'{m_val:.1f}', va='center', ha='right', fontweight='bold', color='#2b5c8f', fontsize=10)
    axes[0].text(f_val + 0.35, i, f'{f_val:.1f}', va='center', ha='left', fontweight='bold', color='#e06d53', fontsize=10)
    axes[0].text((m_val + f_val) / 2, i + 0.16, f'Gap: +{gap:.1f} yrs', ha='center', fontsize=9, fontweight='bold', color='#333333')

axes[0].set_yticks(y_pos)
axes[0].set_yticklabels(ethnic_labels, fontweight='bold')
axes[0].set_xlabel('Average Life Expectancy (Years)', fontweight='bold')
axes[0].set_title('Life Expectancy Gap (Female vs Male)', fontsize=11.5, fontweight='bold')
axes[0].set_xlim(65, 82)
axes[0].set_ylim(-0.5, 2.55)
axes[0].legend(loc='lower right')

# Right Panel: Annual Median Income Gap (Male vs Female)
axes[1].hlines(y=y_pos, xmin=inc_avg['female'], xmax=inc_avg['male'], color='gray', alpha=0.6, linewidth=3)
axes[1].scatter(inc_avg['male'], y_pos, color='#2b5c8f', s=130, label='Male', zorder=3)
axes[1].scatter(inc_avg['female'], y_pos, color='#e06d53', s=130, label='Female', zorder=3)

for i, eth in enumerate(ethnic_order):
    m_inc, f_inc = inc_avg.loc[eth, 'male'], inc_avg.loc[eth, 'female']
    inc_gap = m_inc - f_inc
    left_val, right_val = min(m_inc, f_inc), max(m_inc, f_inc)
    axes[1].text(left_val - 800, i, f'RM {left_val:,.0f}', va='center', ha='right', fontweight='bold',
                 color='#e06d53' if f_inc < m_inc else '#2b5c8f', fontsize=10)
    axes[1].text(right_val + 800, i, f'RM {right_val:,.0f}', va='center', ha='left', fontweight='bold',
                 color='#2b5c8f' if m_inc >= f_inc else '#e06d53', fontsize=10)
    axes[1].text((m_inc + f_inc) / 2, i + 0.16, f'Gap: RM {abs(inc_gap):,.0f}', ha='center', fontsize=9, fontweight='bold', color='#333333')

axes[1].set_yticks(y_pos)
axes[1].set_yticklabels(ethnic_labels, fontweight='bold')
axes[1].set_xlabel('Average Annual Median Income (RM)', fontweight='bold')
axes[1].set_title('Annual Median Income Gap (Male vs Female)', fontsize=11.5, fontweight='bold')
axes[1].set_xlim(inc_avg.min().min() * 0.75, inc_avg.max().max() * 1.18)
axes[1].set_ylim(-0.5, 2.55)
axes[1].legend(loc='lower right')

plt.tight_layout()
st.pyplot(fig)
