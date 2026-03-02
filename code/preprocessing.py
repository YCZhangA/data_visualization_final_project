import pandas as pd
from pathlib import Path

RAW = Path("data/raw-data")
DERIVED = Path("data/derived-data")
DERIVED.mkdir(parents=True, exist_ok=True)


def process_acs():
    """Merge ACS rent, income, and rent-burden tables into one tract-level file."""

    # --- Median gross rent (B25064) ---
    rent = pd.read_csv(RAW / "acs_B25064_2024tract_median_rent.csv", skiprows=1)
    rent = rent[["Geography", "Geographic Area Name", "Estimate!!Median gross rent"]].copy()
    rent.columns = ["geo_id", "name", "median_rent"]
    rent["median_rent"] = pd.to_numeric(rent["median_rent"], errors="coerce")

    # --- Median household income (B19013) ---
    # skiprows=[1] skips the human-label row; row 0 (code names) stays as header
    income = pd.read_csv(RAW / "ACSDT5Y2024.B19013-Data.csv", skiprows=[1])
    income = income[["GEO_ID", "B19013_001E"]].copy()
    income.columns = ["geo_id", "median_income"]
    income["median_income"] = pd.to_numeric(income["median_income"], errors="coerce")

    # --- Rent burden (B25070): % of renters paying 30%+ of income on rent ---
    burden = pd.read_csv(RAW / "ACSDT5Y2024.B25070-Data.csv", skiprows=[1])
    # Total renters, cost-burdened (30-34.9%), (35-39.9%), (40-49.9%), (50%+)
    burden = burden[["GEO_ID", "B25070_001E", "B25070_007E",
                     "B25070_008E", "B25070_009E", "B25070_010E"]].copy()
    burden.columns = ["geo_id", "total_renters",
                      "burden_30_34", "burden_35_39", "burden_40_49", "burden_50plus"]
    for col in burden.columns[1:]:
        burden[col] = pd.to_numeric(burden[col], errors="coerce")
    burden["burdened_renters"] = (
        burden["burden_30_34"] + burden["burden_35_39"] +
        burden["burden_40_49"] + burden["burden_50plus"]
    )
    burden["pct_burdened"] = (
        burden["burdened_renters"] / burden["total_renters"] * 100
    ).round(1)

    # --- Merge all three on geo_id ---
    df = rent.merge(income, on="geo_id", how="inner")
    df = df.merge(burden[["geo_id", "total_renters", "pct_burdened"]], on="geo_id", how="left")

    # --- Extract tract ID and county from name ---
    df["tract"] = df["name"].str.extract(r"Census Tract ([^;]+)")
    df["county"] = df["name"].str.extract(r";\s*([^;]+County)")

    # --- Compute rent-to-income ratio (annual rent / annual income) ---
    df["rent_to_income"] = (df["median_rent"] * 12 / df["median_income"] * 100).round(1)

    df = df.dropna(subset=["median_rent", "median_income"])

    out = DERIVED / "acs_clean.csv"
    df.to_csv(out, index=False)
    print(f"[done] ACS data: {len(df)} tracts → {out}")
    return df


def process_zillow():
    """Filter Zillow ZORI to Chicago metro and reshape wide → long."""

    df = pd.read_csv(RAW / "Zip_zori_uc_sfrcondomfr_sm_sa_month.csv")

    # Filter to Chicago-Naperville-Elgin metro
    chi = df[df["Metro"].str.contains("Chicago", na=False)].copy()

    # Date columns: everything after CountyName
    meta_cols = ["RegionID", "SizeRank", "RegionName", "RegionType",
                 "StateName", "State", "City", "Metro", "CountyName"]
    date_cols = [c for c in chi.columns if c not in meta_cols]

    # Melt wide → long
    long = chi.melt(
        id_vars=meta_cols,
        value_vars=date_cols,
        var_name="date",
        value_name="zori"
    )
    long["date"] = pd.to_datetime(long["date"])
    long = long.dropna(subset=["zori"])
    long = long.sort_values(["RegionName", "date"]).reset_index(drop=True)

    # Rename for clarity
    long = long.rename(columns={
        "RegionName": "zip_code",
        "City": "city",
        "CountyName": "county"
    })

    out = DERIVED / "zillow_clean.csv"
    long.to_csv(out, index=False)
    print(f"[done] Zillow data: {len(long)} rows ({chi['RegionName'].nunique()} ZIP codes) → {out}")
    return long


if __name__ == "__main__":
    process_acs()
    process_zillow()
