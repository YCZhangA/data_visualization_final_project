from pathlib import Path
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.dates as mdates

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived-data"
RAW = ROOT / "data" / "raw-data"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

def plot_time_series():
    z = pd.read_csv(DERIVED / "zillow_clean.csv")
    z["date"] = pd.to_datetime(z["date"])

    z = z[z["city"] == "Chicago"].copy()

    base_date = pd.Timestamp("2019-01-01")
    if base_date not in set(z["date"].unique()):
        base_date = z["date"].min()

    base = (z[z["date"] == base_date]
            .dropna(subset=["zori"])
            .groupby("zip_code", as_index=False)["zori"].mean()
            .rename(columns={"zori": "base_zori"}))

    z = z.merge(base, on="zip_code", how="inner")

    q1 = z["base_zori"].quantile(1/3)
    q2 = z["base_zori"].quantile(2/3)

    def tier(v):
        if v <= q1:
            return "Low-rent"
        elif v <= q2:
            return "Mid-rent"
        return "High-rent"

    z["tier"] = z["base_zori"].apply(tier)

    keep_per_tier = 5
    keep = (base.assign(tier=base["base_zori"].apply(tier))
            .sort_values(["tier", "base_zori"], ascending=[True, False])
            .groupby("tier")
            .head(keep_per_tier)["zip_code"]
            .astype(str)
            .tolist())

    z["zip_code"] = z["zip_code"].astype(str)
    z = z[z["zip_code"].isin([str(k) for k in keep])].copy()

    fig, ax = plt.subplots(figsize=(12, 5))

    linestyle_map = {"Low-rent": "--", "Mid-rent": "-", "High-rent": "-."}

    for (zipc, t), df in z.groupby(["zip_code", "tier"]):
        df = df.sort_values("date")
        ax.plot(df["date"], df["zori"],
                linewidth=1.6,
                linestyle=linestyle_map.get(t, "-"),
                label=f"{zipc}")

    ax.axvline(pd.Timestamp("2020-03-01"), linestyle="--", linewidth=1, color="gray")
    ax.text(pd.Timestamp("2020-03-01"), ax.get_ylim()[0], "COVID / Moratorium",
            rotation=90, va="bottom", ha="right", color="gray", fontsize=9)

    ax.axvline(pd.Timestamp("2022-09-01"), linestyle="--", linewidth=1, color="gray")
    ax.text(pd.Timestamp("2022-09-01"), ax.get_ylim()[0], "Moratorium Ends",
            rotation=90, va="bottom", ha="right", color="gray", fontsize=9)

    ax.set_title("Chicago ZIP Code Rent Trends (ZORI) · selected ZIPs")
    ax.set_xlabel("Date")
    ax.set_ylabel("Monthly Rent Index (USD)")

    ax.xaxis.set_major_locator(mdates.YearLocator(base=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    ax.legend(title="ZIP Code", ncol=2, fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "static_zori_selected_zips.png", dpi=200)
    plt.close(fig)

def plot_choropleth():
    acs = pd.read_csv(DERIVED / "acs_clean.csv")

    gdf = gpd.read_file(RAW / "tiger_tract" / "tl_2024_17_tract.shp")
    cook = gdf[gdf["COUNTYFP"] == "031"].copy()
    cook["geo_id"] = "1400000US" + cook["GEOID"]
    cook = cook.to_crs(epsg=3435)

    merged = cook.merge(
        acs[["geo_id", "median_rent"]],
        on="geo_id", how="left"
    )

    data_rows = merged.dropna(subset=["median_rent"])
    nodata = merged[merged["median_rent"].isna()]
    vmin = data_rows["median_rent"].quantile(0.02)
    vmax = data_rows["median_rent"].quantile(0.98)

    fig, ax = plt.subplots(figsize=(7, 7))
    nodata.plot(ax=ax, color="lightgray", linewidth=0)
    data_rows.plot(
        ax=ax, column="median_rent", cmap="YlOrRd",
        vmin=vmin, vmax=vmax, linewidth=0.05, edgecolor="white"
    )

    sm = plt.cm.ScalarMappable(
        cmap="YlOrRd", norm=mcolors.Normalize(vmin=vmin, vmax=vmax)
    )
    sm.set_array([])
    cb = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("Median Rent (USD)")

    ax.set_title("Median Rent by Census Tract (Cook County, 2024)")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(FIG / "static_choropleth_median_rent.png", dpi=200)
    plt.close(fig)

if __name__ == "__main__":
    plot_time_series()
    plot_choropleth()
    print("Saved static plots to:", FIG)