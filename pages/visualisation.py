import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==========================================
# 1. TITLE & DESCRIPTION
# ==========================================
st.title("📊 Trends in Live Births & Crude Birth Rate in Malaysia")
st.markdown(
    "Data Source: **Department of Statistics Malaysia (DOSM / OpenDOSM)** — `birth.parquet`"
)
st.divider()

# ==========================================
# 2. LOAD DATA (WITH CACHING)
# ==========================================
@st.cache_data
def load_birth_data():
    url = "https://storage.dosm.gov.my/demography/birth.parquet"
    df = pd.read_parquet(url)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df["year"] = df["date"].dt.year
    df = df.sort_values("year").reset_index(drop=True)
    # Calculate Year-over-Year (% YoY) changes for interactive tooltips
    df["abs_yoy_pct"] = df["abs"].pct_change() * 100
    df["rate_yoy_diff"] = df["rate"].diff()
    return df

df_birth = load_birth_data()

# ==========================================
# 3. INTERACTIVE SIDEBAR CONTROLS
# ==========================================
min_year = int(df_birth["year"].min())
max_year = int(df_birth["year"].max())

st.sidebar.header("⚙️ Interactive Controls")

# Quick time-period presets
preset = st.sidebar.radio(
    "Quick Period Selection:",
    options=["All Years", "Last 20 Years", "Last 10 Years", "Custom Range"],
    index=0
)

if preset == "Last 20 Years":
    default_range = (max(min_year, max_year - 19), max_year)
elif preset == "Last 10 Years":
    default_range = (max(min_year, max_year - 9), max_year)
else:
    default_range = (min_year, max_year)

selected_years = st.sidebar.slider(
    "Select Year Range:",
    min_value=min_year,
    max_value=max_year,
    value=default_range
)

chart_mode = st.sidebar.radio(
    "Chart View Mode:",
    options=["Dual-Axis (Live Births & Birth Rate)", "Year-over-Year Growth (% YoY)"],
    index=0
)

show_labels = st.sidebar.checkbox("Show Value Labels on Chart", value=False)
highlight_extremes = st.sidebar.checkbox("Highlight Peak & Lowest Years", value=True)

df_plot = df_birth[
    (df_birth["year"] >= selected_years[0]) &
    (df_birth["year"] <= selected_years[1])
].sort_values("year").copy()

# ==========================================
# 4. SUMMARY KPI METRIC CARDS
# ==========================================
if not df_plot.empty:
    latest_row = df_plot.iloc[-1]
    prev_row = df_plot.iloc[-2] if len(df_plot) > 1 else latest_row
    peak_row = df_plot.loc[df_plot["abs"].idxmax()]

    delta_abs = int(latest_row["abs"] - prev_row["abs"])
    delta_rate = round(float(latest_row["rate"] - prev_row["rate"]), 2)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="Latest Selected Year",
            value=f"{int(latest_row['year'])}",
            delta=f"Range: {selected_years[0]}–{selected_years[1]}",
            delta_color="off"
        )
    with col2:
        st.metric(
            label="Total Live Births",
            value=f"{int(latest_row['abs']):,}",
            delta=f"{delta_abs:+,} vs. previous year"
        )
    with col3:
        st.metric(
            label="Crude Birth Rate",
            value=f"{latest_row['rate']:.1f} / 1k",
            delta=f"{delta_rate:+.1f} vs. previous year"
        )
    with col4:
        st.metric(
            label=f"Peak Births ({int(peak_row['year'])})",
            value=f"{int(peak_row['abs']):,}",
            delta=f"Rate: {peak_row['rate']:.1f} / 1k",
            delta_color="off"
        )

st.write("")

# ==========================================
# 5. INTERACTIVE PLOTLY CHARTS
# ==========================================
if not df_plot.empty:
    if chart_mode == "Dual-Axis (Live Births & Birth Rate)":
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Bar colors: highlight peak & lowest years if toggled on
        max_idx = df_plot["abs"].idxmax()
        min_idx = df_plot["abs"].idxmin()
        bar_colors = []
        for idx in df_plot.index:
            if highlight_extremes and idx == max_idx:
                bar_colors.append("#1b7837")  # Green for highest
            elif highlight_extremes and idx == min_idx:
                bar_colors.append("#b2182b")  # Dark red for lowest
            else:
                bar_colors.append("#2b5c8f")

        # Bar trace: Total Live Births
        fig.add_trace(
            go.Bar(
                x=df_plot["year"],
                y=df_plot["abs"],
                name="Total Live Births (abs)",
                marker_color=bar_colors,
                opacity=0.85,
                text=[f"{v/1000:.0f}k" if show_labels else "" for v in df_plot["abs"]],
                textposition="outside",
                customdata=df_plot["abs_yoy_pct"].fillna(0),
                hovertemplate=(
                    "<b>Year %{x}</b><br>"
                    "Total Live Births: <b>%{y:,}</b><br>"
                    "YoY Change: <b>%{customdata:+.2f}%</b>"
                    "<extra></extra>"
                )
            ),
            secondary_y=False
        )

        # Line trace: Crude Birth Rate
        line_mode = "lines+markers+text" if show_labels else "lines+markers"
        fig.add_trace(
            go.Scatter(
                x=df_plot["year"],
                y=df_plot["rate"],
                name="Crude Birth Rate (per 1,000 population)",
                mode=line_mode,
                line=dict(color="#d95f02", width=3),
                marker=dict(size=7, color="#d95f02"),
                text=[f"{r:.1f}" for r in df_plot["rate"]],
                textposition="top center",
                textfont=dict(size=10, color="#d95f02"),
                customdata=df_plot["rate_yoy_diff"].fillna(0),
                hovertemplate=(
                    "<b>Year %{x}</b><br>"
                    "Crude Birth Rate: <b>%{y:.2f}</b> per 1,000 pop.<br>"
                    "YoY Change: <b>%{customdata:+.2f}</b>"
                    "<extra></extra>"
                )
            ),
            secondary_y=True
        )

        fig.update_layout(
            title=f"Trends in Live Births & Crude Birth Rate in Malaysia ({selected_years[0]}–{selected_years[1]})",
            xaxis=dict(title="Year", tickmode="linear", dtick=2 if len(df_plot) > 15 else 1, gridcolor="#EEEEEE"),
            plot_bgcolor="white",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=540,
            margin=dict(t=80, b=50, l=60, r=60)
        )
        fig.update_yaxes(
            title_text="Total Live Births (abs)",
            title_font=dict(color="#2b5c8f"),
            range=[0, df_plot["abs"].max() * 1.18],
            gridcolor="#EEEEEE",
            secondary_y=False
        )
        fig.update_yaxes(
            title_text="Crude Birth Rate (per 1,000 population)",
            title_font=dict(color="#d95f02"),
            range=[0, df_plot["rate"].max() * 1.18],
            showgrid=False,
            secondary_y=True
        )

        st.plotly_chart(fig, use_container_width=True)

        if highlight_extremes:
            st.caption("🟢 Green Bar = Highest Live Births in selected range | 🔴 Red Bar = Lowest Live Births in selected range")

    else:
        # Mode 2: Year-over-Year Percentage Growth (% YoY) Chart
        yoy_df = df_plot.dropna(subset=["abs_yoy_pct"])
        yoy_colors = ["#1b7837" if val >= 0 else "#b2182b" for val in yoy_df["abs_yoy_pct"]]

        fig_yoy = go.Figure()
        fig_yoy.add_trace(
            go.Bar(
                x=yoy_df["year"],
                y=yoy_df["abs_yoy_pct"],
                marker_color=yoy_colors,
                text=[f"{v:+.1f}%" if show_labels else "" for v in yoy_df["abs_yoy_pct"]],
                textposition="outside",
                hovertemplate=(
                    "<b>Year %{x}</b><br>"
                    "Live Births Growth (YoY): <b>%{y:+.2f}%</b>"
                    "<extra></extra>"
                )
            )
        )
        fig_yoy.add_hline(y=0, line_dash="dash", line_color="#666666")
        fig_yoy.update_layout(
            title=f"Annual Growth Rate (% YoY) of Live Births ({selected_years[0]}–{selected_years[1]})",
            xaxis=dict(title="Year", tickmode="linear", dtick=2 if len(yoy_df) > 15 else 1, gridcolor="#EEEEEE"),
            yaxis=dict(title="Year-over-Year Change (%)", gridcolor="#EEEEEE"),
            plot_bgcolor="white",
            height=500
        )
        st.plotly_chart(fig_yoy, use_container_width=True)

# ==========================================
# 6. DATA TABLE & CSV DOWNLOAD
# ==========================================
with st.expander("📋 View Detailed Data Table & Summary Statistics"):
    s1, s2, s3 = st.columns(3)
    s1.write(f"**Average Live Births:** {df_plot['abs'].mean():,.0f}")
    s2.write(f"**Average Crude Birth Rate:** {df_plot['rate'].mean():.2f} / 1,000")
    s3.write(f"**Years Displayed:** {len(df_plot)} years")

    display_df = df_plot[["year", "abs", "abs_yoy_pct", "rate", "rate_yoy_diff"]].sort_values("year", ascending=False).copy()
    display_df.columns = ["Year", "Live Births (abs)", "Births Growth (% YoY)", "Crude Birth Rate (/1k)", "Rate Change (YoY)"]

    st.dataframe(
        display_df.style.format({
            "Live Births (abs)": "{:,.0f}",
            "Births Growth (% YoY)": "{:+.2f}%",
            "Crude Birth Rate (/1k)": "{:.1f}",
            "Rate Change (YoY)": "{:+.2f}"
        }, na_rep="-"),
        use_container_width=True,
        hide_index=True
    )

    csv_bytes = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download Filtered Data (CSV)",
        data=csv_bytes,
        file_name=f"malaysia_live_births_{selected_years[0]}_{selected_years[1]}.csv",
        mime="text/csv"
    )
