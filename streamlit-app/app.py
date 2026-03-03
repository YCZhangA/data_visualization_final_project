import streamlit as st
import pandas as pd
import altair as alt
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.ticker as mticker
import io
from pathlib import Path

ROOT = Path(__file__).parent.parent

st.set_page_config(
    page_title="Chicago Rent Policy Dashboard",
    page_icon="🏙️",
    layout="wide"
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    h1 { font-size: 1.8rem !important; }
    h2 { font-size: 1.2rem !important; color: #e45756; }
    .metric-card {
        background: #1e1e2e; border-radius: 8px;
        padding: 12px 16px; margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ── Data loading ─────────────────────────────────────────────────────────────
@st.cache_data
def load_acs():
    return pd.read_csv(ROOT / "data/derived-data/acs_clean.csv")

@st.cache_data
def load_zillow():
    df = pd.read_csv(ROOT / "data/derived-data/zillow_clean.csv")
    df["date"] = pd.to_datetime(df["date"])
    return df

@st.cache_data
def load_geo():
    gdf = gpd.read_file(ROOT / "data/raw-data/tiger_tract/tl_2024_17_tract.shp")
    cook = gdf[gdf["COUNTYFP"] == "031"].copy()
    cook["geo_id"] = "1400000US" + cook["GEOID"]
    return cook.to_crs(epsg=3435)

acs    = load_acs()
zillow = load_zillow()
geo    = load_geo()

# ── Header ───────────────────────────────────────────────────────────────────
st.title("🏙️ Chicago Rent Policy Dashboard")
st.caption("Housing rental trends and affordability · Cook County, Chicago Metro Area")
st.divider()

# ── Top KPI row ───────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Median Rent (2024)", f"${acs['median_rent'].median():,.0f}/mo")
k2.metric("Median Rent-to-Income", f"{acs['rent_to_income'].median():.1f}%")
k3.metric("Cost-Burdened Tracts (>50%)",
          f"{(acs['pct_burdened'] > 50).sum()} / {len(acs)}")
k4.metric("Chicago ZIP Codes Tracked", str(zillow['zip_code'].nunique()))

st.divider()

# ════════════════════════════════════════════════════════════════════════════
# TAB LAYOUT
# ════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3 = st.tabs([
    "Rent Trends Over Time",
    "Choropleth Map",
    "Affordability Distribution",
])

# ────────────────────────────────────────────────────────────────────────────
# TAB 1 · Time Series
# ────────────────────────────────────────────────────────────────────────────
with tab1:
    st.subheader("Zillow Observed Rent Index (ZORI) · Chicago Metro")

    col_ctrl, col_chart = st.columns([1, 3])

    with col_ctrl:
        all_cities = sorted(zillow["city"].dropna().unique())
        cities = st.multiselect("Filter by City", all_cities,
                                default=["Chicago"])

        available_zips = sorted(
            zillow[zillow["city"].isin(cities)]["zip_code"].astype(str).unique()
        )
        selected_zips = st.multiselect(
            "Select ZIP Codes (leave empty = all)",
            available_zips, default=[]
        )

        year_min = int(zillow["date"].dt.year.min())
        year_max = int(zillow["date"].dt.year.max())
        year_range = st.slider("Year Range", year_min, year_max,
                               (2018, year_max))

        show_policy = st.checkbox("Show policy events", value=True)

    with col_chart:
        df_ts = zillow[zillow["city"].isin(cities)].copy()
        if selected_zips:
            df_ts = df_ts[df_ts["zip_code"].astype(str).isin(selected_zips)]
        df_ts = df_ts[
            (df_ts["date"].dt.year >= year_range[0]) &
            (df_ts["date"].dt.year <= year_range[1])
        ]
        df_ts["zip_code"] = df_ts["zip_code"].astype(str)

        if df_ts.empty:
            st.warning("No data for selected filters.")
        else:
            line = alt.Chart(df_ts).mark_line(opacity=0.8, strokeWidth=1.8).encode(
                x=alt.X("date:T", title="Date"),
                y=alt.Y("zori:Q", title="Monthly Rent Index (USD)",
                        scale=alt.Scale(zero=False)),
                color=alt.Color("zip_code:N",
                    legend=alt.Legend(title="ZIP Code", columns=2,
                                      orient="right")),
                tooltip=["zip_code:N", "city:N",
                         alt.Tooltip("date:T", title="Date"),
                         alt.Tooltip("zori:Q", format="$,.0f", title="ZORI")]
            )

            layers = [line]

            if show_policy:
                events = pd.DataFrame([
                    {"date": "2020-03-01", "event": "COVID-19 / Eviction Moratorium"},
                    {"date": "2022-09-01", "event": "Moratorium Ends"},
                ])
                events["date"] = pd.to_datetime(events["date"])
                rules = alt.Chart(events).mark_rule(
                    color="gray", strokeDash=[6, 3], opacity=0.6
                ).encode(x="date:T")
                txt = alt.Chart(events).mark_text(
                    angle=270, align="right", baseline="bottom",
                    dy=-5, fontSize=10, color="gray"
                ).encode(x="date:T", text="event:N")
                layers += [rules, txt]

            chart = alt.layer(*layers).properties(
                height=420,
                title=alt.TitleParams(
                    f"Rent Trends · {', '.join(cities)}",
                    fontSize=14
                )
            ).interactive()

            st.altair_chart(chart, use_container_width=True)

        # Summary stats table
        if not df_ts.empty:
            with st.expander("Summary statistics by ZIP code"):
                summary = (df_ts.groupby("zip_code")["zori"]
                           .agg(["mean","min","max","count"])
                           .rename(columns={"mean":"Avg ZORI","min":"Min","max":"Max","count":"Months"})
                           .round(0).astype(int).reset_index())
                summary.columns = ["ZIP Code","Avg Rent ($)","Min ($)","Max ($)","Months"]
                st.dataframe(summary, use_container_width=True, hide_index=True)

# ────────────────────────────────────────────────────────────────────────────
# TAB 2 · Choropleth Map
# ────────────────────────────────────────────────────────────────────────────
with tab2:
    st.subheader("Cook County · Census Tract Level (2024 ACS)")

    map_col, ctrl_col = st.columns([3, 1])

    with ctrl_col:
        map_var = st.radio("Variable to map", [
            "Median Rent",
            "Rent-to-Income Ratio (%)",
            "% Cost-Burdened (>30%)",
        ])
        cmap_choice = st.selectbox("Color scheme",
            ["YlOrRd", "RdPu", "Blues", "viridis", "plasma"])

        col_map = {
            "Median Rent": ("median_rent", "${x:,.0f}", "Monthly Rent (USD)"),
            "Rent-to-Income Ratio (%)": ("rent_to_income", "{x:.1f}%", "RTI (%)"),
            "% Cost-Burdened (>30%)": ("pct_burdened", "{x:.1f}%", "% Burdened"),
        }[map_var]
        var_col, fmt_str, cbar_label = col_map

    with map_col:
        merged = geo.merge(
            acs[["geo_id", "median_rent", "rent_to_income", "pct_burdened"]],
            on="geo_id", how="left"
        )
        data_rows = merged.dropna(subset=[var_col])
        nodata     = merged[merged[var_col].isna()]
        vmin = data_rows[var_col].quantile(0.02)
        vmax = data_rows[var_col].quantile(0.98)

        fig, ax = plt.subplots(figsize=(8, 8))
        fig.patch.set_facecolor("#1a1a2e")
        ax.set_facecolor("#1a1a2e")

        nodata.plot(ax=ax, color="#3a3a4a", linewidth=0)
        data_rows.plot(ax=ax, column=var_col, cmap=cmap_choice,
                       vmin=vmin, vmax=vmax,
                       linewidth=0.05, edgecolor="#888", legend=False)

        sm = plt.cm.ScalarMappable(
            cmap=cmap_choice,
            norm=mcolors.Normalize(vmin=vmin, vmax=vmax)
        )
        sm.set_array([])
        cb = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02, shrink=0.7)
        cb.set_label(cbar_label, color="white", fontsize=10)
        cb.ax.yaxis.set_tick_params(color="white")
        cb.outline.set_edgecolor("white")
        plt.setp(cb.ax.yaxis.get_ticklabels(), color="white")

        if "$" in fmt_str:
            cb.ax.yaxis.set_major_formatter(
                mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
        else:
            cb.ax.yaxis.set_major_formatter(
                mticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))

        ax.set_title(f"{map_var} · Cook County Census Tracts",
                     color="white", fontsize=12, pad=8)
        ax.axis("off")
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=130,
                    bbox_inches="tight", facecolor=fig.get_facecolor())
        buf.seek(0)
        st.image(buf, use_container_width=True)
        plt.close()

    with st.expander("Top 10 most cost-burdened tracts"):
        top10 = (acs.nlargest(10, "pct_burdened")
                 [["tract","county","median_rent","median_income","rent_to_income","pct_burdened"]]
                 .rename(columns={
                     "tract":"Tract","county":"County",
                     "median_rent":"Median Rent ($)",
                     "median_income":"Median Income ($)",
                     "rent_to_income":"RTI (%)",
                     "pct_burdened":"% Burdened"
                 }))
        st.dataframe(top10, use_container_width=True, hide_index=True)

# ────────────────────────────────────────────────────────────────────────────
# TAB 3 · Distribution
# ────────────────────────────────────────────────────────────────────────────
with tab3:
    st.subheader("Rent Affordability Distribution · Cook County Census Tracts")

    d_col1, d_col2 = st.columns(2)

    with d_col1:
        st.markdown("**Rent-to-Income Ratio Histogram**")
        rti_max = st.slider("Cap RTI at (%)", 50, 120, 80)
        df_rti = acs[acs["rent_to_income"] <= rti_max].copy()
        df_rti["burden_group"] = pd.cut(
            df_rti["pct_burdened"],
            bins=[0, 30, 50, 70, 101],
            labels=["Low (<30%)", "Moderate (30–50%)", "High (50–70%)", "Severe (>70%)"]
        )

        hist = alt.Chart(df_rti).mark_bar(opacity=0.8).encode(
            x=alt.X("rent_to_income:Q",
                    bin=alt.Bin(maxbins=45),
                    title="Rent-to-Income Ratio (%)"),
            y=alt.Y("count():Q", title="Number of Tracts"),
            color=alt.Color("burden_group:N",
                scale=alt.Scale(
                    domain=["Low (<30%)","Moderate (30–50%)","High (50–70%)","Severe (>70%)"],
                    range=["#4daf4a","#ff7f00","#e41a1c","#984ea3"]
                ),
                legend=alt.Legend(title="Cost-Burden Rate", orient="top-right")
            ),
            tooltip=["burden_group:N",
                     alt.Tooltip("count():Q", title="Tracts")]
        )
        rule30 = alt.Chart(pd.DataFrame({"x":[30]})).mark_rule(
            color="white", strokeDash=[5,3], opacity=0.6
        ).encode(x="x:Q")
        lbl30 = alt.Chart(pd.DataFrame({"x":[30],"t":["30% threshold"]})).mark_text(
            align="left", dx=4, dy=-100, color="white", fontSize=10
        ).encode(x="x:Q", text="t:N")

        st.altair_chart((hist + rule30 + lbl30).properties(height=350).interactive(),
                        use_container_width=True)

    with d_col2:
        st.markdown("**Cost-Burden Rate · Cumulative Distribution**")
        df_ecdf = acs.dropna(subset=["pct_burdened"]).sort_values("pct_burdened").reset_index(drop=True)
        df_ecdf["ecdf"] = (df_ecdf.index + 1) / len(df_ecdf) * 100

        area = alt.Chart(df_ecdf).mark_area(
            line={"color":"#e45756","strokeWidth":2},
            color=alt.Gradient(
                gradient="linear",
                stops=[
                    alt.GradientStop(color="#e4575650", offset=0),
                    alt.GradientStop(color="#e4575600", offset=1),
                ],
                x1=1, x2=1, y1=1, y2=0
            )
        ).encode(
            x=alt.X("pct_burdened:Q", title="% Renters Cost-Burdened"),
            y=alt.Y("ecdf:Q", title="Cumulative % of Tracts"),
            tooltip=[
                alt.Tooltip("pct_burdened:Q", format=".1f", title="% Burdened"),
                alt.Tooltip("ecdf:Q", format=".1f", title="Cumulative %")
            ]
        )
        ref = alt.Chart(pd.DataFrame({"y":[50]})).mark_rule(
            color="gray", strokeDash=[4,3], opacity=0.6
        ).encode(y="y:Q")
        ref_lbl = alt.Chart(pd.DataFrame({"y":[50],"x":[95],"t":["Median tract"]})).mark_text(
            align="right", color="gray", fontSize=10
        ).encode(x="x:Q", y="y:Q", text="t:N")

        st.altair_chart((area + ref + ref_lbl).properties(height=350).interactive(),
                        use_container_width=True)

    # Scatter: median_rent vs pct_burdened
    st.markdown("**Scatter: Median Rent vs. Cost-Burden Rate**")
    df_sc = acs.dropna(subset=["median_rent","pct_burdened","rent_to_income"])
    scatter = alt.Chart(df_sc).mark_circle(opacity=0.5, size=30).encode(
        x=alt.X("median_rent:Q", title="Median Monthly Rent (USD)"),
        y=alt.Y("pct_burdened:Q", title="% Renters Cost-Burdened"),
        color=alt.Color("rent_to_income:Q",
            scale=alt.Scale(scheme="reds"),
            legend=alt.Legend(title="RTI (%)")
        ),
        tooltip=[
            alt.Tooltip("tract:N", title="Tract"),
            alt.Tooltip("median_rent:Q", format="$,.0f", title="Median Rent"),
            alt.Tooltip("pct_burdened:Q", format=".1f", title="% Burdened"),
            alt.Tooltip("rent_to_income:Q", format=".1f", title="RTI (%)"),
        ]
    ).properties(height=320).interactive()

    st.altair_chart(scatter, use_container_width=True)
