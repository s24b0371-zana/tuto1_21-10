import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Malaysia Demographic & Income Gaps",
    page_icon="🇲🇾",
    layout="wide"
)

# ==========================================
# 1. LOAD & MERGE DATA
# ==========================================
@st.cache_data
def load_and_prepare_data():
    df_life = pd.read_parquet('https://storage.dosm.gov.my/demography/life_expectancy_state_ethnic.parquet')
    df_wages = pd.read_parquet('https://storage.dosm.gov.my/labour/wages_ethnicity.parquet')

    df_life['date'] = pd.to_datetime(df_life['date'])
    df_wages['date'] = pd.to_datetime(df_wages['date'])

    # Inner join on date, sex, and ethnicity
    df_merged = pd.merge(df_life, df_wages, on=['date', 'sex', 'ethnicity'], how='inner')

    # Calculate annual median income
    df_merged['annual_median_income'] = df_merged['wages_median'] * 12
    df_merged['year'] = df_merged['date'].dt.year

    # Filter for standard gender and ethnic groups
    df_merged = df_merged[
        (df_merged['sex'].isin(['male', 'female'])) &
        (df_merged['ethnicity'].isin(['bumi', 'chinese', 'indian']))
    ]

    return df_merged


df_raw = load_and_prepare_data()

# ==========================================
# 2. SIDEBAR INTERACTIVE FILTERS
# ==========================================
st.sidebar.header("Filter Options")

# Year filter
available_years = sorted(df_raw['year'].unique())
selected_years = st.sidebar.multiselect(
    "Select Year(s)",
    options=available_years,
    default=available_years
)

# State filter (if 'state' column exists in life expectancy dataset)
has_state = 'state' in df_raw.columns
if has_state:
    available_states = sorted(df_raw['state'].dropna().unique())
    selected_states = st.sidebar.multiselect(
        "Select State(s) (Life Expectancy)",
        options=available_states,
        default=available_states,
        help="Life expectancy is tracked by state; national median wages apply across states."
    )

# Ethnicity filter
ethnic_map = {'bumi': 'Bumiputera', 'chinese': 'Chinese', 'indian': 'Indian'}
selected_ethnicities = st.sidebar.multiselect(
    "Select Ethnic Group(s)",
    options=list(ethnic_map.keys()),
    default=list(ethnic_map.keys()),
    format_func=lambda x: ethnic_map[x]
)

# Prevent empty selections
if not selected_years or not selected_ethnicities or (has_state and not selected_states):
    st.warning("Please select at least one option in every sidebar filter to display the charts.")
    st.stop()

# Apply filters
df_filtered = df_raw[
    (df_raw['year'].isin(selected_years)) &
    (df_raw['ethnicity'].isin(selected_ethnicities))
]
if has_state:
    df_filtered = df_filtered[df_filtered['state'].isin(selected_states)]

# ==========================================
# 3. AGGREGATE DATA FOR PLOTTING
# ==========================================
life_avg = (
    df_filtered.groupby(['ethnicity', 'sex'], as_index=False)['life_expectancy']
    .mean()
    .pivot(index='ethnicity', columns='sex', values='life_expectancy')
)

wages_unique = df_filtered[['year', 'ethnicity', 'sex', 'annual_median_income']].drop_duplicates()
inc_avg = (
    wages_unique.groupby(['ethnicity', 'sex'], as_index=False)['annual_median_income']
    .mean()
    .pivot(index='ethnicity', columns='sex', values='annual_median_income')
)

# Preserve logical display order
ethnic_order = [e for e in ['bumi', 'chinese', 'indian'] if e in selected_ethnicities]
ethnic_labels = [ethnic_map[e] for e in ethnic_order]
life_avg = life_avg.loc[ethnic_order]
inc_avg = inc_avg.loc[ethnic_order]

# ==========================================
# 4. HEADER & KPI METRIC CARDS
# ==========================================
st.title("Gender & Ethnic Gaps in Life Expectancy and Income in Malaysia")
year_label = f"{min(selected_years)}–{max(selected_years)}" if len(selected_years) > 1 else f"{selected_years[0]}"
st.caption(f"Interactive DOSM Dashboard | Selected Period: **{year_label}**")

avg_life_gap = (life_avg['female'] - life_avg['male']).mean()
avg_inc_gap = (inc_avg['male'] - inc_avg['female']).mean()
highest_life_eth = ethnic_map[(life_avg.mean(axis=1)).idxmax()]
highest_inc_eth = ethnic_map[(inc_avg.mean(axis=1)).idxmax()]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Avg Female–Male Life Gap", f"+{avg_life_gap:.1f} yrs", "Women live longer")
col2.metric("Avg Male–Female Income Gap", f"RM {avg_inc_gap:,.0f} / yr", "Annual median difference")
col3.metric("Highest Avg Life Expectancy", highest_life_eth)
col4.metric("Highest Avg Median Income", highest_inc_eth)

st.divider()

# ==========================================
# 5. INTERACTIVE PLOTLY DUMBBELL CHARTS
# ==========================================
fig = make_subplots(
    rows=1, cols=2,
    subplot_titles=(
        "Life Expectancy Gap (Female vs Male)",
        "Annual Median Income Gap (Male vs Female)"
    ),
    horizontal_spacing=0.14
)

# --- Panel 1: Life Expectancy ---
for eth, label in zip(ethnic_order, ethnic_labels):
    m_val = life_avg.loc[eth, 'male']
    f_val = life_avg.loc[eth, 'female']
    fig.add_trace(
        go.Scatter(
            x=[m_val, f_val],
            y=[label, label],
            mode='lines',
            line=dict(color='rgba(130, 130, 130, 0.5)', width=4),
            showlegend=False,
            hoverinfo='skip'
        ),
        row=1, col=1
    )

fig.add_trace(
    go.Scatter(
        x=life_avg['male'],
        y=ethnic_labels,
        mode='markers+text',
        name='Male',
        marker=dict(color='#2b5c8f', size=14),
        text=[f"{v:.1f}" for v in life_avg['male']],
        textposition="middle left",
        hovertemplate="<b>%{y} (Male)</b><br>Life Expectancy: %{x:.2f} years<extra></extra>"
    ),
    row=1, col=1
)

fig.add_trace(
    go.Scatter(
        x=life_avg['female'],
        y=ethnic_labels,
        mode='markers+text',
        name='Female',
        marker=dict(color='#e06d53', size=14),
        text=[f"{v:.1f}" for v in life_avg['female']],
        textposition="middle right",
        hovertemplate="<b>%{y} (Female)</b><br>Life Expectancy: %{x:.2f} years<extra></extra>"
    ),
    row=1, col=1
)

# --- Panel 2: Annual Median Income ---
for eth, label in zip(ethnic_order, ethnic_labels):
    m_inc = inc_avg.loc[eth, 'male']
    f_inc = inc_avg.loc[eth, 'female']
    fig.add_trace(
        go.Scatter(
            x=[f_inc, m_inc],
            y=[label, label],
            mode='lines',
            line=dict(color='rgba(130, 130, 130, 0.5)', width=4),
            showlegend=False,
            hoverinfo='skip'
        ),
        row=1, col=2
    )

fig.add_trace(
    go.Scatter(
        x=inc_avg['male'],
        y=ethnic_labels,
        mode='markers+text',
        name='Male',
        showlegend=False,
        marker=dict(color='#2b5c8f', size=14),
        text=[f"RM {v:,.0f}" for v in inc_avg['male']],
        textposition="top center",
        hovertemplate="<b>%{y} (Male)</b><br>Annual Income: RM %{x:,.0f}<extra></extra>"
    ),
    row=1, col=2
)

fig.add_trace(
    go.Scatter(
        x=inc_avg['female'],
        y=ethnic_labels,
        mode='markers+text',
        name='Female',
        showlegend=False,
        marker=dict(color='#e06d53', size=14),
        text=[f"RM {v:,.0f}" for v in inc_avg['female']],
        textposition="bottom center",
        hovertemplate="<b>%{y} (Female)</b><br>Annual Income: RM %{x:,.0f}<extra></extra>"
    ),
    row=1, col=2
)

fig.update_layout(
    height=460,
    template="plotly_white",
    legend=dict(orientation="h", yanchor="bottom", y=1.08, xanchor="right", x=1),
    margin=dict(l=40, r=40, t=70, b=40)
)
fig.update_xaxes(title_text="Average Life Expectancy (Years)", range=[65, 83], row=1, col=1)
fig.update_xaxes(
    title_text="Average Annual Median Income (RM)",
    range=[inc_avg.min().min() * 0.80, inc_avg.max().max() * 1.15],
    row=1, col=2
)

st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 6. DATA TABLE & CSV DOWNLOAD
# ==========================================
with st.expander("View Summary & Filtered Data"):
    tab1, tab2 = st.tabs(["Aggregated Summary", "Raw Filtered Records"])

    with tab1:
        summary_df = pd.DataFrame({
            "Ethnicity": ethnic_labels,
            "Male Life Exp (Yrs)": life_avg['male'].round(2).values,
            "Female Life Exp (Yrs)": life_avg['female'].round(2).values,
            "Life Exp Gap (F - M)": (life_avg['female'] - life_avg['male']).round(2).values,
            "Male Income (RM)": inc_avg['male'].round(0).values,
            "Female Income (RM)": inc_avg['female'].round(0).values,
            "Income Gap (M - F)": (inc_avg['male'] - inc_avg['female']).round(0).values,
        })
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

    with tab2:
        st.dataframe(df_filtered, use_container_width=True, hide_index=True)
        csv = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Filtered Data as CSV",
            data=csv,
            file_name="malaysia_demographic_income_gaps.csv",
            mime="text/csv"
        )
