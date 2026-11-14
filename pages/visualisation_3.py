import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Note: st.set_page_config() is omitted here so it won't conflict with your main.py page config.
st.title("Malaysia's Live Births, Life Expectancy & Annual Income")
st.markdown("Interactive multivariate analysis examining Malaysia's demographic and socioeconomic transition.")

# ==========================================
# 1. LOAD & PREPROCESS DATA (CACHED)
# ==========================================
@st.cache_data
def load_and_prepare_data():
    # Official OpenDOSM storage URLs (with fallback to local CSVs in root repo)
    url_birth = "https://storage.dosm.gov.my/demography/births_annual.parquet"
    url_life = "https://storage.dosm.gov.my/demography/life_expectancy.parquet"
    url_wages = "https://storage.dosm.gov.my/labour/wages_annual.parquet"

    try:
        birth = pd.read_parquet(url_birth)
        life = pd.read_parquet(url_life)
        wages = pd.read_parquet(url_wages)
    except Exception:
        birth = pd.read_csv("df_birth.csv")
        life = pd.read_csv("df_life.csv")
        wages = pd.read_csv("df_wages.csv")

    # Extract year from date column
    for df in [birth, life, wages]:
        df['year'] = pd.to_datetime(df['date']).dt.year

    # Aggregate birth data to annual if monthly/quarterly
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

    # Ensure wages are annual per (year, sex, ethnicity)
    if wages.duplicated(subset=['year', 'sex', 'ethnicity']).any():
        wages = (
            wages.groupby(['year', 'sex', 'ethnicity'], as_index=False)[['wages_median', 'wages_mean']]
            .mean()
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
    st.error(
        "Could not load datasets. Upload `df_birth.csv`, `df_life.csv`, and `df_wages.csv` "
        f"to the root folder of your GitHub repository. Details: {e}"
    )
    st.stop()

# ==========================================
# 2. SIDEBAR INTERACTIVE CONTROLS
# ==========================================
st.sidebar.header("Interactive Filters")

# 1. Year Range Slider
min_yr = int(merged_df['year'].min())
max_yr = int(merged_df['year'].max())
year_range = st.sidebar.slider(
    "Select Year Range:",
    min_value=min_yr,
    max_value=max_yr,
    value=(min_yr, max_yr),
    step=1
)

# 2. Sex Selector
sex_options = [s for s in ['both', 'male', 'female'] if s in merged_df['sex'].unique()]
selected_sex = st.sidebar.selectbox(
    "Sex Category:",
    options=sex_options,
    index=0,
    format_func=lambda x: "Both Sexes" if x == "both" else x.capitalize()
)

# 3. Income Metric Toggle
income_metric = st.sidebar.radio(
    "Income Metric:",
    options=["Median Annual Income", "Mean Annual Income"],
    index=0
)
income_col = "annual_income_median" if income_metric == "Median Annual Income" else "annual_income_mean"

# 4. Ethnic Group Multiselect
eth_map = {
    'chinese': ('#1f77b4', 'Chinese'),
    'bumi': ('#2ca02c', 'Bumiputera'),
    'indian': ('#d62728', 'Indian'),
    'overall': ('#333333', 'Malaysia Overall')
}
available_ethnicities = [e for e in ['chinese', 'bumi', 'indian', 'overall'] if e in merged_df['ethnicity'].unique()]
selected_ethnicities = st.sidebar.multiselect(
    "Select Ethnic Groups (Panel A):",
    options=available_ethnicities,
    default=available_ethnicities,
    format_func=lambda x: eth_map[x][1]
)

# 5. Panel B Focus Group
panel_b_group = st.sidebar.selectbox(
    "Panel B Focus Group:",
    options=available_ethnicities,
    index=available_ethnicities.index('overall') if 'overall' in available_ethnicities else 0,
    format_func=lambda x: eth_map[x][1]
)

show_labels = st.sidebar.checkbox("Show Year Labels on Trajectory", value=True)
show_data = st.sidebar.checkbox("Show Filtered Data Table", value=False)

# Filter datasets
filtered_df = merged_df[
    (merged_df['year'] >= year_range[0]) &
    (merged_df['year'] <= year_range[1]) &
    (merged_df['sex'] == selected_sex)
].sort_values(['ethnicity', 'year'])

plot_df = filtered_df[filtered_df['ethnicity'].isin(selected_ethnicities)]
macro_df = filtered_df[filtered_df['ethnicity'] == panel_b_group].sort_values('year')

# ==========================================
# 3. TOP KPI SUMMARY CARDS (DYNAMIC)
# ==========================================
if len(macro_df) >= 2:
    start_row = macro_df.iloc[0]
    end_row = macro_df.iloc[-1]
    yr_span = f"{int(start_row['year'])} → {int(end_row['year'])}"

    col1, col2, col3 = st.columns(3)
    with col1:
        birth_diff = int(end_row['live_births'] - start_row['live_births'])
        st.metric(
            label=f"National Live Births ({int(end_row['year'])})",
            value=f"{int(end_row['live_births']):,}",
            delta=f"{birth_diff:+,} since {int(start_row['year'])}"
        )
    with col2:
        inc_diff = end_row[income_col] - start_row[income_col]
        st.metric(
            label=f"{eth_map[panel_b_group][1]} {income_metric}",
            value=f"RM {end_row[income_col]:,.0f}",
            delta=f"RM {inc_diff:+,.0f} ({yr_span})"
        )
    with col3:
        le_diff = end_row['avg_life_expectancy'] - start_row['avg_life_expectancy']
        st.metric(
            label=f"{eth_map[panel_b_group][1]} Life Expectancy",
            value=f"{end_row['avg_life_expectancy']:.2f} yrs",
            delta=f"{le_diff:+.2f} yrs ({yr_span})"
        )

st.divider()

# ==========================================
# 4. INTERACTIVE PLOTLY CHARTS (2 TABS / PANELS)
# ==========================================
tab1, tab2 = st.tabs(["Side-by-Side Overview", "Animated Year-by-Year Trajectory"])

with tab1:
    col_left, col_right = st.columns([1.2, 1])

    # --- PANEL A: Interactive Multivariate Bubble Trajectory ---
    with col_left:
        fig_a = go.Figure()

        if not plot_df.empty:
            for eth in selected_ethnicities:
                color, label = eth_map[eth]
                sub = plot_df[plot_df['ethnicity'] == eth].sort_values('year')
                if sub.empty:
                    continue

                # Scale bubble diameter cleanly for Plotly
                bubble_sizes = ((sub['live_births'] - 380000) / 1000).clip(lower=10) * 0.45 + 16
                text_labels = [str(int(y)) if show_labels else "" for y in sub['year']]

                fig_a.add_trace(go.Scatter(
                    x=sub[income_col],
                    y=sub['avg_life_expectancy'],
                    mode='lines+markers+text',
                    name=label,
                    text=text_labels,
                    textposition='top center',
                    textfont=dict(size=10, color=color),
                    line=dict(color=color, width=2.5),
                    marker=dict(
                        size=bubble_sizes,
                        color=color,
                        opacity=0.82,
                        line=dict(width=1.5, color='white')
                    ),
                    customdata=np.stack(
                        (sub['year'], sub['live_births'], sub['birth_rate_per_1k']),
                        axis=-1
                    ),
                    hovertemplate=(
                        f"<b>{label} (%{{customdata[0]:.0f}})</b><br>"
                        f"{income_metric}: <b>RM %{{x:,.0f}}</b><br>"
                        "Avg Life Expectancy: <b>%{y:.2f} yrs</b><br>"
                        "National Live Births: <b>%{customdata[1]:,.0f}</b><br>"
                        "Crude Birth Rate: <b>%{customdata[2]:.1f} / 1k</b>"
                        "<extra></extra>"
                    )
                ))

                # Add directional arrowhead on final segment
                if len(sub) >= 2:
                    fig_a.add_annotation(
                        x=sub[income_col].iloc[-1],
                        y=sub['avg_life_expectancy'].iloc[-1],
                        ax=sub[income_col].iloc[-2],
                        ay=sub['avg_life_expectancy'].iloc[-2],
                        xref="x", yref="y", axref="x", ayref="y",
                        showarrow=True,
                        arrowhead=3,
                        arrowsize=1.3,
                        arrowwidth=2,
                        arrowcolor=color
                    )

        fig_a.update_layout(
            title=f"A. {income_metric} vs. Life Expectancy by Ethnicity<br><sup>Bubble size = National live births ({year_range[0]}–{year_range[1]})</sup>",
            xaxis_title=f"{income_metric} (RM)",
            yaxis_title="Average Life Expectancy (Years)",
            xaxis=dict(tickprefix="RM ", tickformat=",.0f", gridcolor="#EEEEEE"),
            yaxis=dict(gridcolor="#EEEEEE"),
            plot_bgcolor="white",
            hovermode="closest",
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
            height=540,
            margin=dict(t=70, b=80, l=50, r=20)
        )
        st.plotly_chart(fig_a, use_container_width=True)

    # --- PANEL B: Interactive Dual-Axis Demographic Transition ---
    with col_right:
        fig_b = make_subplots(specs=[[{"secondary_y": True}]])

        if not macro_df.empty:
            years_str = macro_df['year'].astype(str)

            # Bar trace: Live Births
            fig_b.add_trace(
                go.Bar(
                    x=years_str,
                    y=macro_df['live_births'] / 1000,
                    name="Live Births ('000)",
                    marker_color="#A6CEE3",
                    opacity=0.85,
                    text=[f"{v/1000:.1f}k" for v in macro_df['live_births']],
                    textposition="inside",
                    hovertemplate="<b>Year %{x}</b><br>Live Births: <b>%{y:.1f}k</b><extra></extra>"
                ),
                secondary_y=False
            )

            # Line trace: Annual Income (with Life Expectancy in hover)
            fig_b.add_trace(
                go.Scatter(
                    x=years_str,
                    y=macro_df[income_col] / 1000,
                    name=f"{income_metric} (RM '000)",
                    mode="lines+markers+text",
                    line=dict(color="#E31A1C", width=3),
                    marker=dict(size=9, color="#E31A1C"),
                    text=[f"RM {inc/1000:.1f}k" for inc in macro_df[income_col]],
                    textposition="top center",
                    textfont=dict(size=10, color="#B2182B"),
                    customdata=macro_df['avg_life_expectancy'],
                    hovertemplate=(
                        "<b>Year %{x}</b><br>"
                        f"{income_metric}: <b>RM %{{y:.2f}}k</b><br>"
                        "Avg Life Expectancy: <b>%{customdata:.2f} yrs</b>"
                        "<extra></extra>"
                    )
                ),
                secondary_y=True
            )

        fig_b.update_layout(
            title=f"B. Macro Transition ({eth_map[panel_b_group][1]})<br><sup>Live births vs. annual income & life expectancy</sup>",
            xaxis_title="Year",
            plot_bgcolor="white",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
            height=540,
            margin=dict(t=70, b=80, l=50, r=50)
        )
        fig_b.update_yaxes(title_text="Live Births (Thousands)", title_font=dict(color="#1F78B4"), secondary_y=False, gridcolor="#EEEEEE")
        fig_b.update_yaxes(title_text=f"{income_metric} (RM '000)", title_font=dict(color="#E31A1C"), secondary_y=True, showgrid=False)

        st.plotly_chart(fig_b, use_container_width=True)

# --- TAB 2: Animated Play/Pause Bubble Chart ---
with tab2:
    if not plot_df.empty:
        import plotly.express as px
        anim_df = plot_df.copy()
        anim_df['Ethnicity'] = anim_df['ethnicity'].map(lambda x: eth_map[x][1])

        fig_anim = px.scatter(
            anim_df,
            x=income_col,
            y="avg_life_expectancy",
            animation_frame="year",
            animation_group="Ethnicity",
            size="live_births",
            color="Ethnicity",
            color_discrete_map={
                "Chinese": "#1f77b4",
                "Bumiputera": "#2ca02c",
                "Indian": "#d62728",
                "Malaysia Overall": "#333333"
            },
            size_max=45,
            range_x=[anim_df[income_col].min() * 0.92, anim_df[income_col].max() * 1.08],
            range_y=[anim_df['avg_life_expectancy'].min() - 0.8, anim_df['avg_life_expectancy'].max() + 0.8],
            labels={
                income_col: f"{income_metric} (RM)",
                "avg_life_expectancy": "Average Life Expectancy (Years)",
                "live_births": "National Live Births"
            },
            title="Press Play (▶) to Watch Ethnic Groups Move Across Years"
        )
        fig_anim.update_layout(plot_bgcolor="white", height=520)
        fig_anim.update_xaxes(tickprefix="RM ", tickformat=",.0f", gridcolor="#EEEEEE")
        fig_anim.update_yaxes(gridcolor="#EEEEEE")
        st.plotly_chart(fig_anim, use_container_width=True)

# ==========================================
# 5. OPTIONAL DATA TABLE & CSV DOWNLOAD
# ==========================================
if show_data:
    st.subheader("Filtered Merged Dataset")
    st.dataframe(filtered_df, use_container_width=True)

csv_data = filtered_df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Download Filtered Dataset (CSV)",
    data=csv_data,
    file_name="merged_objective3_malaysia.csv",
    mime="text/csv"
)
